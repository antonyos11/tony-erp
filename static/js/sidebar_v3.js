/**
 * Sidebar v3 – Smart Features
 * ============================
 * Global search, live badges, state persistence, mini-sidebar toggle,
 * mobile open/close, Ctrl+K keyboard shortcut.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var sidebar = document.getElementById('appSidebar');
    if (!sidebar || !sidebar.classList.contains('app-sidebar-v3')) return;

    var STORAGE_KEY = 'sidebar_v3_state';
    var COLLAPSED_KEY = 'sidebar_collapsed';
    var VERSION_KEY = 'sidebar_v3_version';
    var CURRENT_VERSION = '2';  // Bump to reset saved state

    // Reset saved state when version changes (forces expand-all on upgrade)
    try {
      if (localStorage.getItem(VERSION_KEY) !== CURRENT_VERSION) {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.setItem(VERSION_KEY, CURRENT_VERSION);
      }
    } catch (e) { /* noop */ }

    // ─── Helpers ───────────────────────────────────
    function loadState() {
      try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch (e) { return {}; }
    }
    function saveState(state) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) { /* noop */ }
    }

    // ─── Restore Collapse States ──────────────────
    function restoreCollapseStates() {
      var state = loadState();
      var hasAnySavedState = Object.keys(state).length > 0;

      sidebar.querySelectorAll('.sidebar-parent-group').forEach(function (group) {
        var id = group.dataset.group;
        var collapseEl = group.querySelector('.collapse');
        var btn = group.querySelector('.sidebar-parent-btn');
        if (!collapseEl || !btn) return;

        var hasActive = btn.classList.contains('active');
        var saved = state[id];

        // First visit (no saved state yet) → expand all groups by default
        if (hasActive || saved === true || !hasAnySavedState) {
          collapseEl.classList.add('show');
          btn.setAttribute('aria-expanded', 'true');
        } else if (saved === false) {
          collapseEl.classList.remove('show');
          btn.setAttribute('aria-expanded', 'false');
        }
      });
    }

    // Listen for Bootstrap collapse events to persist state
    sidebar.addEventListener('shown.bs.collapse', function (e) {
      var g = e.target.closest('.sidebar-parent-group');
      if (g) { var s = loadState(); s[g.dataset.group] = true; saveState(s); }
    });
    sidebar.addEventListener('hidden.bs.collapse', function (e) {
      var g = e.target.closest('.sidebar-parent-group');
      if (g) { var s = loadState(); s[g.dataset.group] = false; saveState(s); }
    });
    restoreCollapseStates();

    // ─── Scroll Active Item Into View ─────────────
    setTimeout(function () {
      var activeLink = sidebar.querySelector('.sidebar-item-link.active');
      if (activeLink) {
        activeLink.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    }, 300);

    // ─── Global Search ────────────────────────────
    var searchInput = document.getElementById('sidebarGlobalSearch');
    var searchResults = document.getElementById('sidebarSearchResults');
    var searchItems = [];
    var highlightedIndex = -1;

    // Load search data from json_script tag
    try {
      var dataEl = document.getElementById('sidebarSearchData');
      if (dataEl) searchItems = JSON.parse(dataEl.textContent);
    } catch (e) { /* noop */ }

    if (searchInput && searchResults && searchItems.length) {
      var debounceTimer;

      searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        var query = this.value.trim().toLowerCase();

        if (query.length < 2) {
          searchResults.hidden = true;
          searchResults.innerHTML = '';
          highlightedIndex = -1;
          return;
        }

        debounceTimer = setTimeout(function () {
          var results = searchItems.filter(function (item) {
            return item.label.toLowerCase().indexOf(query) !== -1 ||
                   item.section.toLowerCase().indexOf(query) !== -1 ||
                   item.group.toLowerCase().indexOf(query) !== -1;
          }).slice(0, 10);

          if (results.length === 0) {
            searchResults.innerHTML = '<div class="search-no-results">لا توجد نتائج</div>';
          } else {
            searchResults.innerHTML = results.map(function (item, i) {
              return '<a href="' + _escHtml(item.url) + '" class="search-result-item' +
                     (i === 0 ? ' highlighted' : '') + '">' +
                     '<i class="' + _escHtml(item.icon) + '"></i>' +
                     '<div><div>' + _escHtml(item.label) + '</div>' +
                     '<div class="search-result-section">' + _escHtml(item.section) + ' › ' + _escHtml(item.group) + '</div></div>' +
                     '</a>';
            }).join('');
            highlightedIndex = 0;
          }
          searchResults.hidden = false;
        }, 150);
      });

      // Keyboard nav in search results
      searchInput.addEventListener('keydown', function (e) {
        var items = searchResults.querySelectorAll('.search-result-item');
        if (!items.length) return;
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          highlightedIndex = Math.min(highlightedIndex + 1, items.length - 1);
          _hlItems(items);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          highlightedIndex = Math.max(highlightedIndex - 1, 0);
          _hlItems(items);
        } else if (e.key === 'Enter' && highlightedIndex >= 0) {
          e.preventDefault();
          items[highlightedIndex].click();
        } else if (e.key === 'Escape') {
          searchResults.hidden = true;
          searchInput.blur();
        }
      });

      function _hlItems(items) {
        items.forEach(function (el, i) { el.classList.toggle('highlighted', i === highlightedIndex); });
        if (items[highlightedIndex]) items[highlightedIndex].scrollIntoView({ block: 'nearest' });
      }

      // Close on outside click
      document.addEventListener('click', function (e) {
        if (!e.target.closest('.sidebar-v3-search')) searchResults.hidden = true;
      });
    }

    // Ctrl+K / Cmd+K keyboard shortcut for search
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        e.stopPropagation();
        if (searchInput) {
          // On mobile, open sidebar first
          if (window.innerWidth < 992 && !document.body.classList.contains('sidebar-open')) {
            openSidebarMobile();
          }
          searchInput.focus();
          searchInput.select();
        }
      }
    });

    // ─── Live Badges ──────────────────────────────
    function updateBadges() {
      var badges = sidebar.querySelectorAll('.sidebar-live-badge[data-source]');
      if (!badges.length) return;
      var sources = [];
      badges.forEach(function (b) {
        if (sources.indexOf(b.dataset.source) === -1) sources.push(b.dataset.source);
      });

      var csrfEl = document.querySelector('[name=csrfmiddlewaretoken]');
      fetch('/dashboard/api/sidebar-badges/?sources=' + encodeURIComponent(sources.join(',')), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
      })
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (data) {
        badges.forEach(function (badge) {
          var count = data[badge.dataset.source] || 0;
          if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.add('has-count');
          } else {
            badge.textContent = '';
            badge.classList.remove('has-count');
          }
        });
      })
      .catch(function () { /* silent */ });
    }
    // Initial + interval
    updateBadges();
    setInterval(updateBadges, 60000);

    // ─── Expand / Collapse All Groups ─────────────
    var expandAllBtn = document.getElementById('sidebarExpandAll');
    if (expandAllBtn) {
      expandAllBtn.addEventListener('click', function () {
        var allGroups = sidebar.querySelectorAll('.sidebar-parent-group');
        var anyCollapsed = false;
        allGroups.forEach(function (g) {
          var c = g.querySelector('.collapse');
          if (c && !c.classList.contains('show')) anyCollapsed = true;
        });

        var newState = loadState();
        allGroups.forEach(function (g) {
          var id = g.dataset.group;
          var collapseEl = g.querySelector('.collapse');
          var btn = g.querySelector('.sidebar-parent-btn');
          if (!collapseEl || !btn) return;

          if (anyCollapsed) {
            collapseEl.classList.add('show');
            btn.setAttribute('aria-expanded', 'true');
            newState[id] = true;
          } else {
            collapseEl.classList.remove('show');
            btn.setAttribute('aria-expanded', 'false');
            newState[id] = false;
          }
        });
        saveState(newState);

        // Toggle icon
        var icon = expandAllBtn.querySelector('i');
        if (icon) {
          icon.className = anyCollapsed ? 'bi bi-arrows-collapse' : 'bi bi-arrows-expand';
        }
      });
    }

    // ─── Mini-Sidebar Toggle (Desktop) ────────────
    var collapseToggle = document.getElementById('sidebarCollapseToggle');
    if (collapseToggle) {
      try {
        if (localStorage.getItem(COLLAPSED_KEY) === 'true' && window.innerWidth >= 992) {
          document.body.classList.add('sidebar-collapsed');
        }
      } catch (e) { /* noop */ }

      collapseToggle.addEventListener('click', function () {
        document.body.classList.toggle('sidebar-collapsed');
        try {
          localStorage.setItem(COLLAPSED_KEY, document.body.classList.contains('sidebar-collapsed'));
        } catch (e) { /* noop */ }
      });
    }

    // ─── Mobile Open / Close ──────────────────────
    var closeBtn = document.getElementById('sidebarCloseBtn');
    var backdrop = document.getElementById('sidebarMobileBackdrop');

    function openSidebarMobile() {
      document.body.classList.add('sidebar-open');
      if (backdrop) backdrop.hidden = false;
    }

    function closeSidebarMobile() {
      document.body.classList.remove('sidebar-open');
      if (backdrop) setTimeout(function () { backdrop.hidden = true; }, 300);
    }

    if (closeBtn) closeBtn.addEventListener('click', closeSidebarMobile);
    if (backdrop) backdrop.addEventListener('click', closeSidebarMobile);

    // Expose globally for the topbar hamburger button
    window.openSidebarV3 = openSidebarMobile;
    window.closeSidebarV3 = closeSidebarMobile;

    // Hook into existing sidebarToggle button
    var sidebarToggleBtn = document.getElementById('sidebarToggle');
    if (sidebarToggleBtn) {
      sidebarToggleBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (document.body.classList.contains('sidebar-open')) {
          closeSidebarMobile();
        } else {
          openSidebarMobile();
        }
      });
    }

    // Expose for backward compat with app_layout.js
    if (typeof window.openSidebar === 'undefined') {
      window.openSidebar = openSidebarMobile;
    }
    if (typeof window.closeSidebar === 'undefined') {
      window.closeSidebar = closeSidebarMobile;
    }

    // ─── Tooltips on Collapsed Mode ───────────────
    sidebar.querySelectorAll('.sidebar-parent-btn').forEach(function (btn) {
      var label = btn.querySelector('.parent-label');
      if (label) btn.setAttribute('title', label.textContent.trim());
    });

    // ─── Escape helper ────────────────────────────
    function _escHtml(str) {
      if (!str) return '';
      var div = document.createElement('div');
      div.appendChild(document.createTextNode(str));
      return div.innerHTML;
    }
  });
})();
