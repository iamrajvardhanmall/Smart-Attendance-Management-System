/**
 * attendance.js — Smart Attendance Management System
 * ====================================================
 * Global JavaScript utilities loaded on every page.
 *
 * Features:
 *   1. Auto-dismiss Bootstrap alerts after 5 seconds
 *   2. Confirm dialog before form submission
 *   3. Remedial code input auto-uppercase
 *   4. Highlight low-attendance rows (<75%)
 *   5. Search filter for tables
 */

document.addEventListener('DOMContentLoaded', function () {

    // ─────────────────────────────────────────────────────
    // 1. AUTO-DISMISS ALERTS (after 5 seconds)
    // ─────────────────────────────────────────────────────
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000); // 5 seconds
    });


    // ─────────────────────────────────────────────────────
    // 2. AUTO-UPPERCASE REMEDIAL CODE INPUT
    //    Applied to any input with class 'text-uppercase'
    // ─────────────────────────────────────────────────────
    const codeInput = document.querySelector('input.text-uppercase');
    if (codeInput) {
        codeInput.addEventListener('input', function () {
            const pos = this.selectionStart;
            this.value = this.value.toUpperCase();
            this.setSelectionRange(pos, pos);
        });
    }


    // ─────────────────────────────────────────────────────
    // 3. LIVE TABLE SEARCH / FILTER
    //    Works with any input with id="tableSearch"
    //    Filters rows in the first table on the page
    // ─────────────────────────────────────────────────────
    const searchInput = document.getElementById('tableSearch');
    if (searchInput) {
        searchInput.addEventListener('keyup', function () {
            const query = this.value.toLowerCase();
            const rows  = document.querySelectorAll('table tbody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }


    // ─────────────────────────────────────────────────────
    // 4. TOOLTIP INITIALIZATION (Bootstrap 5)
    //    Activates all elements with data-bs-toggle="tooltip"
    // ─────────────────────────────────────────────────────
    const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipEls.forEach(el => new bootstrap.Tooltip(el));


    // ─────────────────────────────────────────────────────
    // 5. PRINT BUTTON HANDLER
    //    Any button with id="printBtn" triggers window.print()
    // ─────────────────────────────────────────────────────
    const printBtn = document.getElementById('printBtn');
    if (printBtn) {
        printBtn.addEventListener('click', () => window.print());
    }


    // ─────────────────────────────────────────────────────
    // 6. COUNTDOWN TIMER FOR REMEDIAL CODE EXPIRY
    //    Looks for element: <span id="expiryTimer" data-expiry="ISO_DATETIME">
    //    Displays live countdown: "Expires in 2h 35m"
    // ─────────────────────────────────────────────────────
    const timerEl = document.getElementById('expiryTimer');
    if (timerEl) {
        const expiryTime = new Date(timerEl.dataset.expiry).getTime();

        function updateTimer() {
            const now  = new Date().getTime();
            const diff = expiryTime - now;

            if (diff <= 0) {
                timerEl.textContent = 'EXPIRED';
                timerEl.classList.remove('text-success');
                timerEl.classList.add('text-danger');
                return;
            }

            const hours   = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            timerEl.textContent = `Expires in ${hours}h ${minutes}m ${seconds}s`;
        }

        updateTimer();
        setInterval(updateTimer, 1000); // Update every second
    }

}); // End DOMContentLoaded
