// Digital Farm Management Portal - Main JavaScript Functions

document.addEventListener('DOMContentLoaded', function() {
    // 1. Mobile Sidebar Toggle
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('show');
        });
        
        // Close sidebar if user clicks outside of it on mobile
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 992 && !sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }

    // 2. Alert Autoclose
    const alertBanners = document.querySelectorAll('.alert-banner');
    alertBanners.forEach(banner => {
        // Auto fadeout after 5 seconds
        setTimeout(() => {
            banner.style.opacity = '0';
            banner.style.transition = 'opacity 0.5s ease';
            setTimeout(() => {
                banner.remove();
            }, 500);
        }, 5000);

        // Manual close button
        const closeBtn = banner.querySelector('.alert-banner-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                banner.remove();
            });
        }
    });

    // 3. Search and Filtering for Tables
    const searchInputs = document.querySelectorAll('.table-search');
    searchInputs.forEach(input => {
        const tableId = input.dataset.target;
        const table = document.getElementById(tableId);
        if (!table) return;

        input.addEventListener('keyup', function() {
            const filter = input.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                let match = false;
                const cells = row.querySelectorAll('td');
                cells.forEach(cell => {
                    if (cell.textContent.toLowerCase().indexOf(filter) > -1) {
                        match = true;
                    }
                });
                if (match) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });

    // 4. Biosecurity Checklist Scoring Logic
    const checklistContainer = document.querySelector('.checklist-container');
    if (checklistContainer) {
        const checkboxes = checklistContainer.querySelectorAll('input[type="checkbox"]');
        const scoreDisplay = document.getElementById('biosecurity-score');
        const scoreInput = document.getElementById('biosecurity-score-input');
        
        function calculateScore() {
            const total = checkboxes.length;
            if (total === 0) return;
            
            let checked = 0;
            checkboxes.forEach(cb => {
                if (cb.checked) checked++;
            });
            
            const score = Math.round((checked / total) * 100);
            
            if (scoreDisplay) scoreDisplay.textContent = score + '%';
            if (scoreInput) scoreInput.value = score;
            
            // Adjust visual colors depending on score tier
            if (scoreDisplay) {
                if (score >= 80) {
                    scoreDisplay.style.color = 'var(--color-success)';
                } else if (score >= 50) {
                    scoreDisplay.style.color = 'var(--color-warning)';
                } else {
                    scoreDisplay.style.color = 'var(--color-danger)';
                }
            }
        }
        
        checkboxes.forEach(cb => {
            cb.addEventListener('change', calculateScore);
        });
        
        // Initial run
        calculateScore();
    }
});

// 5. Modal Controllers
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        // Trigger reflow for transition
        void modal.offsetWidth;
        modal.classList.add('show');
        document.body.style.overflow = 'hidden'; // Lock background scroll
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto'; // Unlock background scroll
        }, 300);
    }
}

// Close modals when clicking on background overlay
window.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        closeModal(e.target.id);
    }
});
