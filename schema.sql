-- Digital Farm Management Portal Database Schema
CREATE DATABASE IF NOT EXISTS digital_farm_db;
USE digital_farm_db;

-- 1. Admins Table
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Farms Table
CREATE TABLE IF NOT EXISTS farms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(255) NOT NULL,
    size_hectares DECIMAL(10, 2) NOT NULL,
    contact_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Livestock Table (Pigs & Poultry Management)
CREATE TABLE IF NOT EXISTS livestock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    farm_id INT NOT NULL,
    type ENUM('Pig', 'Poultry') NOT NULL,
    breed VARCHAR(100) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    birth_date DATE,
    health_status ENUM('Healthy', 'Sick', 'Quarantined', 'Treatment') NOT NULL DEFAULT 'Healthy',
    status_last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Biosecurity Logs Table
CREATE TABLE IF NOT EXISTS biosecurity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    farm_id INT NOT NULL,
    log_date DATE NOT NULL,
    score INT NOT NULL, -- Out of 100
    inspector_name VARCHAR(100) NOT NULL,
    checklist_json TEXT NOT NULL, -- Stores details of checklist inputs
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Vaccinations Table
CREATE TABLE IF NOT EXISTS vaccinations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    livestock_id INT NOT NULL,
    vaccine_name VARCHAR(100) NOT NULL,
    administered_date DATE,
    next_due_date DATE,
    administered_by VARCHAR(100),
    status ENUM('Scheduled', 'Administered', 'Overdue') NOT NULL DEFAULT 'Scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (livestock_id) REFERENCES livestock(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Disease Reports Table
CREATE TABLE IF NOT EXISTS disease_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    farm_id INT NOT NULL,
    livestock_id INT NULL,
    disease_name VARCHAR(100) NOT NULL,
    cases_count INT NOT NULL DEFAULT 0,
    report_date DATE NOT NULL,
    symptoms TEXT,
    status ENUM('Reported', 'Under Investigation', 'Resolved', 'Quarantined') NOT NULL DEFAULT 'Reported',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
    FOREIGN KEY (livestock_id) REFERENCES livestock(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Visitors Table
CREATE TABLE IF NOT EXISTS visitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    farm_id INT NOT NULL,
    visitor_name VARCHAR(100) NOT NULL,
    organization VARCHAR(100),
    visit_purpose VARCHAR(255) NOT NULL,
    entry_time DATETIME NOT NULL,
    exit_time DATETIME NULL,
    contact_number VARCHAR(20) NOT NULL,
    signed_biosecurity_declaration BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
