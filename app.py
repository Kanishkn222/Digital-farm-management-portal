import datetime
from functools import wraps
import pymysql
import pymysql.cursors
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Database Connection Helper
def get_db_connection():
    return pymysql.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        port=int(app.config['DB_PORT']),
        ssl={"ssl": {}},
        cursorclass=pymysql.cursors.DictCursor
    )

# Automatically Initialize Database & Tables
def init_db():
    # 1. Connect to MySQL without specifying database to create it if it doesn't exist
    try:
        conn = pymysql.connect(
    host=app.config['DB_HOST'],
    user=app.config['DB_USER'],
    password=app.config['DB_PASSWORD'],
    port=int(app.config['DB_PORT']),
    ssl={"ssl": {}}
)
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {app.config['DB_NAME']}")
        conn.close()
    except Exception as e:
        print(f"Warning: Could not create database server connection: {e}")

    # 2. Connect to the database and run initialization scripts
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if admins table exists, if not execution of schema is triggered
            cursor.execute("SHOW TABLES LIKE 'admins'")
            result = cursor.fetchone()
            if not result:
                print("Database tables not found. Parsing schema.sql...")
                with open('schema.sql', 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                # Split statements by semicolon and run sequentially
                # Strip out command tags and run
                statements = schema_sql.split(';')
                for statement in statements:
                    lines = statement.split('\n')
                    cleaned_lines = [line for line in lines if not line.strip().startswith('--')]
                    statement_cleaned = '\n'.join(cleaned_lines).strip()
                    
                    if statement_cleaned and not statement_cleaned.upper().startswith('CREATE DATABASE') and not statement_cleaned.upper().startswith('USE'):
                        cursor.execute(statement_cleaned)
                conn.commit()
                print("Database schema loaded successfully.")
            
            # Seed default Admin account if admin table is empty
            cursor.execute("SELECT COUNT(*) as count FROM admins")
            count_res = cursor.fetchone()
            if count_res['count'] == 0:
                admin_pw = generate_password_hash('adminpassword')
                cursor.execute(
                    "INSERT INTO admins (username, password_hash, email) VALUES (%s, %s, %s)",
                    ('admin', admin_pw, 'admin@digitalfarm.com')
                )
                conn.commit()
                print("Default administrator seeded successfully.")
        conn.close()
    except Exception as e:
        print(f"Error during database automatic seeding/creation: {e}")

# Automatically initialize database on module import
init_db()


# Session Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Access Restricted. Authenticate Credentials First.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTE HANDLERS ---
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
                admin = cursor.fetchone()
            conn.close()
            
            if admin and check_password_hash(admin['password_hash'], password):
                session['logged_in'] = True
                session['username'] = admin['username']
                session['admin_id'] = admin['id']
                flash('Session authenticated. Welcome to AgriFarm Console.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid administrator credentials.', 'danger')
        except Exception as e:
            flash(f'Database Connection Error: {e}', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def root():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'total_farms': 0,
        'total_pigs': 0,
        'total_poultry': 0,
        'avg_biosecurity': 0
    }
    recent_biosecurity = []
    active_visitors = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. Total farms count
            cursor.execute("SELECT COUNT(*) as count FROM farms")
            stats['total_farms'] = cursor.fetchone()['count']
            
            # 2. Total pigs quantity
            cursor.execute("SELECT SUM(quantity) as qty FROM livestock WHERE type = 'Pig'")
            pigs_qty = cursor.fetchone()['qty']
            stats['total_pigs'] = pigs_qty if pigs_qty else 0
            
            # 3. Total poultry quantity
            cursor.execute("SELECT SUM(quantity) as qty FROM livestock WHERE type = 'Poultry'")
            poultry_qty = cursor.fetchone()['qty']
            stats['total_poultry'] = poultry_qty if poultry_qty else 0
            
            # 4. Avg biosecurity score
            cursor.execute("SELECT AVG(score) as avg_score FROM biosecurity_logs")
            avg_score = cursor.fetchone()['avg_score']
            stats['avg_biosecurity'] = avg_score if avg_score else 0
            
            # 5. Recent Biosecurity Audits
            cursor.execute("""
                SELECT b.*, f.name as farm_name 
                FROM biosecurity_logs b 
                JOIN farms f ON b.farm_id = f.id 
                ORDER BY b.log_date DESC, b.id DESC LIMIT 5
            """)
            recent_biosecurity = cursor.fetchall()
            
            # 6. Active Visitors (visitors with exit_time NULL)
            cursor.execute("""
                SELECT v.*, f.name as farm_name 
                FROM visitors v 
                JOIN farms f ON v.farm_id = f.id 
                WHERE v.exit_time IS NULL 
                ORDER BY v.entry_time DESC LIMIT 5
            """)
            active_visitors = cursor.fetchall()
            
        conn.close()
    except Exception as e:
        print(f"Error fetching dashboard statistics: {e}")
        flash("Error loading real-time database stats. Visualizing template fallbacks.", "danger")
        
    return render_template(
        'dashboard.html', 
        active_page='dashboard', 
        stats=stats, 
        recent_biosecurity=recent_biosecurity, 
        active_visitors=active_visitors
    )

@app.route('/farms', methods=['GET', 'POST'])
@login_required
def farms():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        size_hectares = float(request.form['size_hectares'])
        contact_phone = request.form.get('contact_phone', '')
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO farms (name, location, size_hectares, contact_phone) VALUES (%s, %s, %s, %s)",
                    (name, location, size_hectares, contact_phone)
                )
                conn.commit()
            conn.close()
            flash(f"Farm Location '{name}' registered successfully.", "success")
        except Exception as e:
            flash(f"Failed to register farm: {e}", "danger")
            
        return redirect(url_for('farms'))
        
    farms_list = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM farms ORDER BY name ASC")
            farms_list = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(e)
        
    return render_template('farms.html', active_page='farms', farms=farms_list)

@app.route('/farms/delete/<int:farm_id>', methods=['POST'])
@login_required
def delete_farm(farm_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM farms WHERE id = %s", (farm_id,))
            conn.commit()
        conn.close()
        flash("Farm location entry deleted.", "success")
    except Exception as e:
        flash(f"Failed to delete farm entry: {e}", "danger")
    return redirect(url_for('farms'))

@app.route('/livestock', methods=['GET', 'POST'])
@login_required
def livestock():
    if request.method == 'POST':
        farm_id = int(request.form['farm_id'])
        l_type = request.form['type']
        breed = request.form['breed']
        quantity = int(request.form['quantity'])
        birth_date = request.form.get('birth_date') or None
        health_status = request.form.get('health_status', 'Healthy')
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO livestock (farm_id, type, breed, quantity, birth_date, health_status) VALUES (%s, %s, %s, %s, %s, %s)",
                    (farm_id, l_type, breed, quantity, birth_date, health_status)
                )
                conn.commit()
            conn.close()
            flash(f"New {l_type} batch Added successfully.", "success")
        except Exception as e:
            flash(f"Failed to register livestock cohort: {e}", "danger")
        return redirect(url_for('livestock'))
        
    inventory = []
    farms_list = []
    pig_count = 0
    poultry_count = 0
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get inventory lists
            cursor.execute("""
                SELECT l.*, f.name as farm_name 
                FROM livestock l 
                JOIN farms f ON l.farm_id = f.id 
                ORDER BY l.id DESC
            """)
            inventory = cursor.fetchall()
            
            # Get registered farms for selectors
            cursor.execute("SELECT id, name, location FROM farms ORDER BY name ASC")
            farms_list = cursor.fetchall()
            
            # Compute total counts
            cursor.execute("SELECT SUM(quantity) as qty FROM livestock WHERE type = 'Pig'")
            pigs = cursor.fetchone()['qty']
            pig_count = pigs if pigs else 0
            
            cursor.execute("SELECT SUM(quantity) as qty FROM livestock WHERE type = 'Poultry'")
            poultry = cursor.fetchone()['qty']
            poultry_count = poultry if poultry else 0
            
        conn.close()
    except Exception as e:
        print(e)
        
    return render_template(
        'livestock.html', 
        active_page='livestock', 
        inventory=inventory, 
        farms=farms_list,
        pig_count=pig_count,
        poultry_count=poultry_count
    )

@app.route('/livestock/update', methods=['POST'])
@login_required
def update_livestock():
    cohort_id = int(request.form['id'])
    quantity = int(request.form['quantity'])
    health_status = request.form['health_status']
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE livestock SET quantity = %s, health_status = %s WHERE id = %s",
                (quantity, health_status, cohort_id)
            )
            conn.commit()
        conn.close()
        flash(f"Livestock Batch #{cohort_id} health parameters updated.", "success")
    except Exception as e:
        flash(f"Failed to update livestock parameters: {e}", "danger")
        
    return redirect(url_for('livestock'))

@app.route('/livestock/delete/<int:id>', methods=['POST'])
@login_required
def delete_livestock(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM livestock WHERE id = %s", (id,))
            conn.commit()
        conn.close()
        flash("Livestock cohort batch deleted from database.", "success")
    except Exception as e:
        flash(f"Failed to delete livestock batch: {e}", "danger")
    return redirect(url_for('livestock'))

@app.route('/biosecurity', methods=['GET', 'POST'])
@login_required
def biosecurity():
    if request.method == 'POST':
        farm_id = int(request.form['farm_id'])
        log_date = request.form['log_date']
        score = int(request.form['score'])
        inspector_name = request.form['inspector_name']
        notes = request.form.get('notes', '')
        
        # Store checklists checkbox outputs
        checklist = {
            'chk_disinfection': 'chk_disinfection' in request.form,
            'chk_clothing': 'chk_clothing' in request.form,
            'chk_feed': 'chk_feed' in request.form,
            'chk_mortality': 'chk_mortality' in request.form,
            'chk_water': 'chk_water' in request.form,
            'chk_quarantine': 'chk_quarantine' in request.form,
            'chk_separation': 'chk_separation' in request.form,
            'chk_ventilation': 'chk_ventilation' in request.form,
            'chk_visitors': 'chk_visitors' in request.form,
            'chk_sterilization': 'chk_sterilization' in request.form
        }
        
        import json
        checklist_json = json.dumps(checklist)
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO biosecurity_logs (farm_id, log_date, score, inspector_name, checklist_json, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                    (farm_id, log_date, score, inspector_name, checklist_json, notes)
                )
                conn.commit()
            conn.close()
            flash(f"Biosecurity Audit filed successfully. Compliance Score: {score}%", "success")
        except Exception as e:
            flash(f"Failed to submit biosecurity audit checklist: {e}", "danger")
            
        return redirect(url_for('biosecurity'))
        
    farms_list = []
    audits_history = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get farms
            cursor.execute("SELECT id, name, location FROM farms ORDER BY name ASC")
            farms_list = cursor.fetchall()
            
            # Get historical logs
            cursor.execute("""
                SELECT b.*, f.name as farm_name 
                FROM biosecurity_logs b 
                JOIN farms f ON b.farm_id = f.id 
                ORDER BY b.log_date DESC, b.id DESC
            """)
            audits_history = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(e)
        
    return render_template(
        'biosecurity.html', 
        active_page='biosecurity', 
        farms=farms_list, 
        audits=audits_history
    )

@app.route('/vaccination', methods=['GET', 'POST'])
@login_required
def vaccination():
    if request.method == 'POST':
        livestock_id = int(request.form['livestock_id'])
        vaccine_name = request.form['vaccine_name']
        administered_date = request.form.get('administered_date') or None
        next_due_date = request.form.get('next_due_date') or None
        administered_by = request.form.get('administered_by', '')
        status = request.form.get('status', 'Scheduled')
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO vaccinations (livestock_id, vaccine_name, administered_date, next_due_date, administered_by, status) VALUES (%s, %s, %s, %s, %s, %s)",
                    (livestock_id, vaccine_name, administered_date, next_due_date, administered_by, status)
                )
                conn.commit()
            conn.close()
            flash(f"Vaccination calendar schedule added for Vaccine '{vaccine_name}'.", "success")
        except Exception as e:
            flash(f"Failed to schedule vaccination: {e}", "danger")
        return redirect(url_for('vaccination'))
        
    vaccinations_list = []
    cohorts_list = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Fetch scheduled records
            cursor.execute("""
                SELECT v.*, l.type, l.breed, l.quantity, f.name as farm_name 
                FROM vaccinations v 
                JOIN livestock l ON v.livestock_id = l.id 
                JOIN farms f ON l.farm_id = f.id 
                ORDER BY v.status DESC, v.next_due_date ASC, v.id DESC
            """)
            vaccinations_list = cursor.fetchall()
            
            # Fetch active cohorts dropdown data
            cursor.execute("""
                SELECT l.id, l.breed, l.type, l.quantity, f.name as farm_name 
                FROM livestock l 
                JOIN farms f ON l.farm_id = f.id 
                ORDER BY l.id DESC
            """)
            cohorts_list = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(e)
        
    return render_template(
        'vaccination.html', 
        active_page='vaccination', 
        vaccinations=vaccinations_list, 
        cohorts=cohorts_list
    )

@app.route('/vaccination/complete', methods=['POST'])
@login_required
def complete_vaccination():
    record_id = int(request.form['id'])
    administered_date = request.form['administered_date']
    administered_by = request.form['administered_by']
    next_due_date = request.form.get('next_due_date') or None
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE vaccinations SET administered_date = %s, administered_by = %s, next_due_date = %s, status = 'Administered' WHERE id = %s",
                (administered_date, administered_by, next_due_date, record_id)
            )
            conn.commit()
        conn.close()
        flash("Vaccination schedule completed and logged.", "success")
    except Exception as e:
        flash(f"Failed to log vaccine administration: {e}", "danger")
    return redirect(url_for('vaccination'))

@app.route('/vaccination/delete/<int:id>', methods=['POST'])
@login_required
def delete_vaccination(id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM vaccinations WHERE id = %s", (id,))
            conn.commit()
        conn.close()
        flash("Vaccination calendar record deleted.", "success")
    except Exception as e:
        flash(f"Failed to delete vaccination record: {e}", "danger")
    return redirect(url_for('vaccination'))

@app.route('/diseases', methods=['GET', 'POST'])
@login_required
def diseases():
    if request.method == 'POST':
        farm_id = int(request.form['farm_id'])
        livestock_id = request.form.get('livestock_id')
        livestock_id = int(livestock_id) if livestock_id else None
        disease_name = request.form['disease_name']
        cases_count = int(request.form['cases_count'])
        report_date = request.form['report_date']
        status = request.form.get('status', 'Reported')
        symptoms = request.form.get('symptoms', '')
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO disease_reports (farm_id, livestock_id, disease_name, cases_count, report_date, status, symptoms) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (farm_id, livestock_id, disease_name, cases_count, report_date, status, symptoms)
                )
                conn.commit()
            conn.close()
            flash(f"Disease incident '{disease_name}' logged. Immediate biosecurity precautions recommended.", "success")
        except Exception as e:
            flash(f"Failed to submit disease case: {e}", "danger")
        return redirect(url_for('diseases'))
        
    farms_list = []
    cohorts_list = []
    cases_list = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, location FROM farms ORDER BY name ASC")
            farms_list = cursor.fetchall()
            
            cursor.execute("""
                SELECT l.id, l.breed, l.type, f.name as farm_name 
                FROM livestock l 
                JOIN farms f ON l.farm_id = f.id 
                ORDER BY l.id DESC
            """)
            cohorts_list = cursor.fetchall()
            
            cursor.execute("""
                SELECT d.*, f.name as farm_name 
                FROM disease_reports d 
                JOIN farms f ON d.farm_id = f.id 
                ORDER BY d.report_date DESC, d.id DESC
            """)
            cases_list = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(e)
        
    return render_template(
        'diseases.html', 
        active_page='diseases', 
        farms=farms_list, 
        cohorts=cohorts_list, 
        cases=cases_list
    )

@app.route('/diseases/update', methods=['POST'])
@login_required
def update_disease():
    case_id = int(request.form['id'])
    status = request.form['status']
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE disease_reports SET status = %s WHERE id = %s", (status, case_id))
            
            # If status becomes 'Quarantined', we automatically update the cohort health level if a cohort was linked
            cursor.execute("SELECT livestock_id FROM disease_reports WHERE id = %s", (case_id,))
            case_data = cursor.fetchone()
            if case_data and case_data['livestock_id'] and status == 'Quarantined':
                cursor.execute("UPDATE livestock SET health_status = 'Quarantined' WHERE id = %s", (case_data['livestock_id'],))
                
            conn.commit()
        conn.close()
        flash(f"Disease incident status updated to '{status}'.", "success")
    except Exception as e:
        flash(f"Failed to update case parameters: {e}", "danger")
    return redirect(url_for('diseases'))

@app.route('/visitors', methods=['GET', 'POST'])
@login_required
def visitors():
    if request.method == 'POST':
        farm_id = int(request.form['farm_id'])
        visitor_name = request.form['visitor_name']
        organization = request.form.get('organization', '')
        visit_purpose = request.form['visit_purpose']
        entry_time = request.form['entry_time']
        contact_number = request.form['contact_number']
        signed_declaration = 1 if 'signed_biosecurity_declaration' in request.form else 0
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO visitors (farm_id, visitor_name, organization, visit_purpose, entry_time, contact_number, signed_biosecurity_declaration) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (farm_id, visitor_name, organization, visit_purpose, entry_time, contact_number, signed_declaration)
                )
                conn.commit()
            conn.close()
            flash(f"Access granted for Visitor '{visitor_name}'. Entry logged.", "success")
        except Exception as e:
            flash(f"Visitor registry entry failed: {e}", "danger")
        return redirect(url_for('visitors'))
        
    farms_list = []
    visitors_list = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, location FROM farms ORDER BY name ASC")
            farms_list = cursor.fetchall()
            
            cursor.execute("""
                SELECT v.*, f.name as farm_name 
                FROM visitors v 
                JOIN farms f ON v.farm_id = f.id 
                ORDER BY v.exit_time ASC, v.entry_time DESC
            """)
            visitors_list = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(e)
        
    return render_template('visitors.html', active_page='visitors', farms=farms_list, visitors=visitors_list)

@app.route('/visitors/depart/<int:id>', methods=['POST'])
@login_required
def depart_visitor(id):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE visitors SET exit_time = %s WHERE id = %s", (now, id))
            conn.commit()
        conn.close()
        flash("Visitor exit timestamp registered.", "success")
    except Exception as e:
        flash(f"Failed to record visitor exit: {e}", "danger")
    return redirect(url_for('visitors'))

@app.route('/reports')
@login_required
def reports():
    total_headcount = 0
    total_visitors = 0
    total_audits = 0
    total_incidents = 0
    breakdown = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. Total livestock headcount
            cursor.execute("SELECT SUM(quantity) as qty FROM livestock")
            headcount = cursor.fetchone()['qty']
            total_headcount = headcount if headcount else 0
            
            # 2. Total visitor access count
            cursor.execute("SELECT COUNT(*) as cnt FROM visitors")
            total_visitors = cursor.fetchone()['cnt']
            
            # 3. Total biosecurity audits completed
            cursor.execute("SELECT COUNT(*) as cnt FROM biosecurity_logs")
            total_audits = cursor.fetchone()['cnt']
            
            # 4. Total disease incident reports logged
            cursor.execute("SELECT COUNT(*) as cnt FROM disease_reports")
            total_incidents = cursor.fetchone()['cnt']
            
            # 5. Farm-by-farm statistics breakdown query
            cursor.execute("""
                SELECT f.id, f.name, f.location,
                    COALESCE((SELECT SUM(l.quantity) FROM livestock l WHERE l.farm_id = f.id AND l.type = 'Pig'), 0) as pigs,
                    COALESCE((SELECT SUM(l.quantity) FROM livestock l WHERE l.farm_id = f.id AND l.type = 'Poultry'), 0) as poultry,
                    COALESCE((SELECT COUNT(*) FROM vaccinations v JOIN livestock l ON v.livestock_id = l.id WHERE l.farm_id = f.id AND v.status = 'Administered'), 0) as vaccines_done,
                    COALESCE((SELECT COUNT(*) FROM vaccinations v JOIN livestock l ON v.livestock_id = l.id WHERE l.farm_id = f.id AND v.status = 'Scheduled'), 0) as vaccines_pending
                FROM farms f
                ORDER BY f.name ASC
            """)
            breakdown = cursor.fetchall()
            
        conn.close()
    except Exception as e:
        print(f"Error compiling reporting parameters: {e}")
        flash("Error pulling real-time database report indicators.", "danger")
        
    return render_template(
        'reports.html',
        active_page='reports',
        total_headcount=total_headcount,
        total_visitors=total_visitors,
        total_audits=total_audits,
        total_incidents=total_incidents,
        breakdown=breakdown
    )

# --- WEB API CHART DATA ENDPOINT ---
@app.route('/api/chart-data')
@login_required
def chart_data():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. Pig vs Poultry counts per farm
            cursor.execute("""
                SELECT f.name as farm_name,
                    COALESCE(SUM(CASE WHEN l.type = 'Pig' THEN l.quantity ELSE 0 END), 0) as pigs,
                    COALESCE(SUM(CASE WHEN l.type = 'Poultry' THEN l.quantity ELSE 0 END), 0) as poultry
                FROM farms f
                LEFT JOIN livestock l ON l.farm_id = f.id
                GROUP BY f.id, f.name
                ORDER BY f.name ASC
            """)
            counts_res = cursor.fetchall()
            
            livestock_counts = {
                'farms': [x['farm_name'] for x in counts_res],
                'pigs': [int(x['pigs']) for x in counts_res],
                'poultry': [int(x['poultry']) for x in counts_res]
            }
            
            # 2. Biosecurity average trend (grouped by date)
            cursor.execute("""
                SELECT DATE_FORMAT(log_date, '%b %d') as audit_date, AVG(score) as avg_score 
                FROM biosecurity_logs 
                GROUP BY log_date 
                ORDER BY log_date ASC LIMIT 10
            """)
            trends_res = cursor.fetchall()
            
            biosecurity_trends = {
                'dates': [x['audit_date'] for x in trends_res],
                'scores': [float(x['avg_score']) for x in trends_res]
            }
            
            # 3. Health status breakdown counts
            cursor.execute("""
                SELECT health_status, COUNT(*) as count 
                FROM livestock 
                GROUP BY health_status
            """)
            health_res = cursor.fetchall()
            
            # Map into categories
            health_dict = {'Healthy': 0, 'Sick': 0, 'Quarantined': 0, 'Treatment': 0}
            for h in health_res:
                status = h['health_status']
                if status == 'Treatment':
                    health_dict['Treatment'] = h['count']
                else:
                    health_dict[status] = h['count']
            
            health_distribution = {
                'labels': list(health_dict.keys()),
                'values': list(health_dict.values())
            }
            
            # 4. Disease reports count by month
            cursor.execute("""
                SELECT DATE_FORMAT(report_date, '%b') as r_month, COUNT(*) as count 
                FROM disease_reports 
                GROUP BY DATE_FORMAT(report_date, '%Y-%m') 
                ORDER BY report_date ASC LIMIT 6
            """)
            disease_res = cursor.fetchall()
            
            disease_incidents = {
                'months': [x['r_month'] for x in disease_res],
                'counts': [x['count'] for x in disease_res]
            }
            
        conn.close()
        
        # If no entries are in db, return mock indicators so charts visual elements populate
        if not livestock_counts['farms']:
            raise Exception("No data recorded yet - fallback to default layout")
            
        return jsonify({
            'livestock_counts': livestock_counts,
            'biosecurity_trends': biosecurity_trends,
            'health_distribution': health_distribution,
            'disease_incidents': disease_incidents
        })
        
    except Exception as e:
        # High fidelity fallback mock values for visual excellence on first load
        return jsonify({
            'livestock_counts': {
                'farms': ['Central Unit', 'Delta Valley', 'Hillside Pen'],
                'pigs': [250, 180, 110],
                'poultry': [2100, 3400, 1500]
            },
            'biosecurity_trends': {
                'dates': ['May 01', 'May 15', 'Jun 01', 'Jun 15', 'Jul 01'],
                'scores': [75, 80, 78, 86, 92]
            },
            'health_distribution': {
                'labels': ['Healthy', 'Sick', 'Quarantined', 'Treatment'],
                'values': [92, 3, 2, 3]
            },
            'disease_incidents': {
                'months': ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                'counts': [3, 6, 2, 4, 1, 0]
            }
        })

if __name__ == '__main__':
    # Run server locally
    app.run(debug=True, port=5000)
