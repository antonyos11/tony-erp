
document.addEventListener('DOMContentLoaded', function () {
    // Inject Modal HTML
    const modalHTML = `
    <div id="command-palette-backdrop" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:9999; backdrop-filter:blur(2px);">
        <div style="position:relative; width:600px; max-width:90%; margin:80px auto; background:var(--bs-body-bg, #fff); border-radius:12px; box-shadow:0 25px 50px -12px rgba(0,0,0,0.25); overflow:hidden; border:1px solid var(--bs-border-color);">
            <div style="padding:16px; border-bottom:1px solid var(--bs-border-color);">
                <div style="display:flex; align-items:center; gap:12px;">
                    <i class="bi bi-search" style="color:#64748b; font-size:1.2rem;"></i>
                    <input type="text" id="command-palette-input" placeholder="Type to search..." style="width:100%; border:none; outline:none; font-size:1.1rem; background:transparent; color:var(--bs-body-color);">
                    <span style="font-size:0.8rem; color:#94a3b8; border:1px solid #cbd5e1; padding:2px 6px; border-radius:4px;">ESC</span>
                </div>
            </div>
            <div id="command-palette-results" style="max-height:400px; overflow-y:auto; padding:8px 0;">
                <div style="padding:32px; text-align:center; color:#94a3b8;">
                    Type to search for Pages, Products, Customers, or Invoices...
                </div>
            </div>
            <div style="padding:8px 16px; font-size:0.8rem; color:#94a3b8; background:var(--bs-tertiary-bg); border-top:1px solid var(--bs-border-color); display:flex; justify-content:space-between;">
                <span>Navigate <i class="bi bi-arrow-down-short"></i> <i class="bi bi-arrow-up-short"></i></span>
                <span>Select <i class="bi bi-arrow-return-left"></i></span>
            </div>
        </div>
    </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    const backdrop = document.getElementById('command-palette-backdrop');
    const input = document.getElementById('command-palette-input');
    const resultsContainer = document.getElementById('command-palette-results');

    let debounceTimer;
    let selectedIndex = -1;

    // Toggle Modal
    function togglePalette() {
        if (backdrop.style.display === 'none') {
            backdrop.style.display = 'block';
            input.value = '';
            resultsContainer.innerHTML = '<div style="padding:32px; text-align:center; color:#94a3b8;">Type to search...</div>';
            input.focus();
        } else {
            backdrop.style.display = 'none';
        }
    }

    // Shortcut Ctrl+K or Cmd+K
    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            togglePalette();
        }
        if (e.key === 'Escape' && backdrop.style.display !== 'none') {
            togglePalette();
        }
    });

    // Close on click outside
    backdrop.addEventListener('click', function (e) {
        if (e.target === backdrop) togglePalette();
    });

    // Search Logic
    input.addEventListener('input', function (e) {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();

        if (query.length === 0) {
            resultsContainer.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/core/api/global-search/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    renderResults(data.results);
                });
        }, 300);
    });

    function renderResults(results) {
        if (results.length === 0) {
            resultsContainer.innerHTML = '<div style="padding:16px; text-align:center; color:#94a3b8;">No results found.</div>';
            return;
        }

        let html = '';
        let currentCategory = '';

        // Group simply by category here implicitly if sorted, or just render
        results.forEach((item, index) => {
            if (item.category !== currentCategory) {
                currentCategory = item.category;
                html += `<div style="padding:8px 16px; font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; background:var(--bs-tertiary-bg);">${currentCategory}</div>`;
            }
            html += `
            <div class="palette-item" data-url="${item.url}" style="padding:10px 16px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; border-left:3px solid transparent;">
                <div>
                    <div style="font-weight:500; color:var(--bs-body-color);">${item.name}</div>
                    ${item.meta ? `<div style="font-size:0.8rem; color:#94a3b8;">${item.meta}</div>` : ''}
                </div>
                <i class="bi bi-chevron-right" style="color:#d1d5db; font-size:0.9rem;"></i>
            </div>
            `;
        });

        resultsContainer.innerHTML = html;

        // Add hover/click events
        const items = resultsContainer.querySelectorAll('.palette-item');
        items.forEach(el => {
            el.addEventListener('click', () => {
                window.location.href = el.dataset.url;
            });
            el.addEventListener('mouseenter', function () {
                items.forEach(i => {
                    i.style.background = 'transparent';
                    i.style.borderLeftColor = 'transparent';
                });
                this.style.background = 'var(--bs-tertiary-bg)';
                this.style.borderLeftColor = 'var(--bs-primary)';
            });
        });
    }
});
