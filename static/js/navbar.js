document.addEventListener('DOMContentLoaded', function() {
    const nav = document.querySelector('nav');
    if (!nav) return;

    const closeAll = () => {
        nav.querySelectorAll('details[open]').forEach(d => d.removeAttribute('open'));
    };

    // Close when clicking/tapping outside any open details (use pointerdown to run before toggle)
    document.addEventListener('pointerdown', function(event) {
        const openDetails = Array.from(nav.querySelectorAll('details[open]'));
        if (openDetails.length === 0) return;

        // If the pointer event is inside any open details, do nothing
        if (openDetails.some(d => d.contains(event.target))) return;

        // Otherwise close all open details
        closeAll();
    }, true);

    // Ensure only one details is open at a time
    nav.querySelectorAll('details').forEach(details => {
        details.addEventListener('toggle', function() {
            if (this.open) {
                nav.querySelectorAll('details[open]').forEach(other => {
                    if (other !== this) other.removeAttribute('open');
                });
            }
        });
    });

    // Close on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeAll();
    });
});