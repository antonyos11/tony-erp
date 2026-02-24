/**
 * Tony ERP — Theme JavaScript
 * Vanilla JS (no jQuery required).
 * Features:
 *  1. Dark mode toggle (localStorage + prefers-color-scheme)
 *  2. Sidebar collapse / expand (localStorage state)
 *  3. Global search (debounced, delegates to existing #globalSearch)
 *  4. Back-to-top button visibility on scroll
 *  5. Mobile sidebar off-canvas + backdrop
 *  6. Bootstrap tooltips & popovers initialisation
 */

(function () {
  'use strict';

  /* =========================================================================
     UTILITIES
     ========================================================================= */

  /**
   * Debounce: returns a function that delays `fn` by `delay` ms.
   * @param {Function} fn
   * @param {number} delay
   */
  function debounce(fn, delay) {
    var timer;
    return function () {
      var ctx  = this;
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, delay);
    };
  }

  /**
   * Safe localStorage get with a fallback value.
   * @param {string} key
   * @param {string} fallback
   */
  function lsGet(key, fallback) {
    try { return localStorage.getItem(key) || fallback; } catch (e) { return fallback; }
  }

  /**
   * Safe localStorage set.
   * @param {string} key
   * @param {string} value
   */
  function lsSet(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* quota exceeded — ignore */ }
  }

  /* =========================================================================
     1. DARK MODE
     ========================================================================= */
  var THEME_KEY     = 'theme';
  var DARK_VALUE    = 'dark';
  var LIGHT_VALUE   = 'light';
  var ICON_DARK     = 'bi-moon-stars-fill';   /* shown in light mode */
  var ICON_LIGHT    = 'bi-sun-fill';           /* shown in dark mode  */

  /**
   * Apply a theme value ('dark' or 'light') to the document root
   * and update any toggle button icons.
   * @param {string} theme
   */
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.classList.toggle('theme-dark', theme === DARK_VALUE);
    lsSet(THEME_KEY, theme);

    /* Update all toggle button icons */
    document.querySelectorAll('[data-theme-toggle], #darkModeToggle, #themeToggle').forEach(function (btn) {
      var icon = btn.querySelector('i, .bi');
      if (icon) {
        if (theme === DARK_VALUE) {
          icon.classList.remove(ICON_DARK);
          icon.classList.add(ICON_LIGHT);
        } else {
          icon.classList.remove(ICON_LIGHT);
          icon.classList.add(ICON_DARK);
        }
      }
      /* Legacy: id="themeIcon" pattern from old theme.js */
      var themeIcon = document.getElementById('themeIcon');
      if (themeIcon) {
        themeIcon.className = theme === DARK_VALUE ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
      }
      btn.setAttribute('aria-label', theme === DARK_VALUE ? 'تفعيل الوضع الفاتح' : 'تفعيل الوضع الداكن');
      btn.setAttribute('title',      theme === DARK_VALUE ? 'الوضع الفاتح' : 'الوضع الداكن');
    });

    /* Dispatch custom event so other scripts can react */
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: theme } }));
  }

  /** Toggle between dark and light. */
  function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme') || LIGHT_VALUE;
    applyTheme(current === DARK_VALUE ? LIGHT_VALUE : DARK_VALUE);
  }

  /** Initialise dark mode from localStorage / OS preference. */
  function initDarkMode() {
    var saved = lsGet(THEME_KEY, null);
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches;
    var theme = saved || (prefersDark ? DARK_VALUE : LIGHT_VALUE);
    applyTheme(theme);

    /* Attach click to any toggle button */
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-theme-toggle], #darkModeToggle, #themeToggle');
      if (btn) toggleTheme();
    });

    /* React to OS-level preference changes (only if user hasn't saved a preference) */
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme:dark)').addEventListener('change', function (mq) {
        if (!lsGet(THEME_KEY, null)) {
          applyTheme(mq.matches ? DARK_VALUE : LIGHT_VALUE);
        }
      });
    }
  }

  /* =========================================================================
     2. SIDEBAR COLLAPSE / EXPAND
     ========================================================================= */
  var SIDEBAR_KEY         = 'sidebarCollapsed';
  var COLLAPSED_CLASS     = 'collapsed';
  var SIDEBAR_OPEN_CLASS  = 'sidebar-open';   /* mobile */

  var _sidebar  = null;
  var _wrapper  = null;
  var _backdrop = null;

  /** Return sidebar element (lazy). */
  function getSidebar() {
    if (!_sidebar) _sidebar = document.querySelector('.app-sidebar, #appSidebar');
    return _sidebar;
  }

  /** Return mobile backdrop element (lazy). */
  function getBackdrop() {
    if (!_backdrop) _backdrop = document.getElementById('sidebarMobileBackdrop');
    return _backdrop;
  }

  /** Returns true if the viewport is considered "mobile" (< 992px). */
  function isMobile() { return window.innerWidth < 992; }

  /* ── Desktop collapse ── */

  /**
   * Collapse or expand the desktop sidebar.
   * @param {boolean} collapse
   */
  function setDesktopCollapsed(collapse) {
    var sidebar = getSidebar();
    if (!sidebar) return;
    if (collapse) {
      sidebar.classList.add(COLLAPSED_CLASS);
    } else {
      sidebar.classList.remove(COLLAPSED_CLASS);
    }
    lsSet(SIDEBAR_KEY, collapse ? '1' : '0');
    document.dispatchEvent(new CustomEvent('sidebarchange', { detail: { collapsed: collapse } }));
  }

  /** Toggle desktop sidebar collapse state. */
  function toggleDesktopSidebar() {
    var sidebar = getSidebar();
    if (!sidebar) return;
    var isCollapsed = sidebar.classList.contains(COLLAPSED_CLASS);
    setDesktopCollapsed(!isCollapsed);
  }

  /* ── Mobile off-canvas ── */

  /** Open mobile sidebar (slide in from edge). */
  function openMobileSidebar() {
    var sidebar  = getSidebar();
    var backdrop = getBackdrop();
    if (!sidebar) return;

    sidebar.classList.add(SIDEBAR_OPEN_CLASS);
    sidebar.style.visibility = '';
    sidebar.style.transform  = '';
    sidebar.style.pointerEvents = '';

    if (backdrop) {
      backdrop.removeAttribute('hidden');
      /* Force reflow before adding visible class for CSS transition */
      void backdrop.offsetWidth;
      backdrop.classList.add('visible');
    }

    document.body.style.overflow = 'hidden';
  }

  /** Close mobile sidebar. */
  function closeMobileSidebar() {
    var sidebar  = getSidebar();
    var backdrop = getBackdrop();
    if (!sidebar) return;

    sidebar.classList.remove(SIDEBAR_OPEN_CLASS);

    if (backdrop) {
      backdrop.classList.remove('visible');
      backdrop.setAttribute('hidden', '');
    }

    document.body.style.overflow = '';
  }

  /** Handle the sidebarToggle button (top-bar hamburger). */
  function handleSidebarToggle() {
    if (isMobile()) {
      var sidebar = getSidebar();
      if (sidebar && sidebar.classList.contains(SIDEBAR_OPEN_CLASS)) {
        closeMobileSidebar();
      } else {
        openMobileSidebar();
      }
    } else {
      toggleDesktopSidebar();
    }
  }

  /** Initialise sidebar behaviour. */
  function initSidebar() {
    /* Restore desktop collapse state */
    if (!isMobile() && lsGet(SIDEBAR_KEY, '0') === '1') {
      setDesktopCollapsed(true);
    }

    /* Desktop collapse toggle — also triggers on any [data-sidebar-toggle] */
    document.addEventListener('click', function (e) {
      if (e.target.closest('#sidebarToggle, [data-sidebar-toggle]')) {
        handleSidebarToggle();
      }
    });

    /* Backdrop closes mobile sidebar */
    var backdrop = getBackdrop();
    if (backdrop) {
      backdrop.addEventListener('click', closeMobileSidebar);
    }

    /* ESC key closes mobile sidebar */
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isMobile()) closeMobileSidebar();
    });

    /* Close mobile sidebar when a nav link is tapped */
    document.addEventListener('click', function (e) {
      if (!isMobile()) return;
      var sidebar = getSidebar();
      if (!sidebar) return;
      var link = e.target.closest('.sidebar-link, .nav-link');
      if (link && sidebar.contains(link)) {
        closeMobileSidebar();
      }
    });

    /* Resize: sync state between mobile / desktop */
    window.addEventListener('resize', debounce(function () {
      if (!isMobile()) {
        closeMobileSidebar(); /* ensure no mobile state leaks into desktop */
        if (lsGet(SIDEBAR_KEY, '0') === '1') {
          setDesktopCollapsed(true);
        }
      }
    }, 200));
  }

  /* =========================================================================
     3. GLOBAL SEARCH
     ========================================================================= */
  var SEARCH_DEBOUNCE = 280; /* ms */

  /**
   * Perform the search — delegates to existing global_search.js logic
   * by dispatching an 'input' event on the #globalSearch field so the
   * existing handler fires. Falls back to a simple menu-item filter if
   * the existing handler is not present.
   * @param {string} query
   */
  function performSearch(query) {
    var input = document.getElementById('globalSearch');
    if (!input) return;

    if (input.value !== query) input.value = query;

    /* Fire native input event (global_search.js listens for this) */
    var ev = new Event('input', { bubbles: true, cancelable: true });
    input.dispatchEvent(ev);

    /* Fallback: hide/show sidebar nav links by text match */
    if (!query.trim()) return;
    var lower = query.trim().toLowerCase();
    document.querySelectorAll('.sidebar-link').forEach(function (link) {
      var text = (link.textContent || '').toLowerCase();
      link.style.display = text.includes(lower) ? '' : 'none';
    });
  }

  /** Reset sidebar link visibility after search is cleared. */
  function clearSearchFilter() {
    document.querySelectorAll('.sidebar-link').forEach(function (link) {
      link.style.display = '';
    });
  }

  /** Initialise global search integration. */
  function initSearch() {
    var input = document.getElementById('globalSearch');
    if (!input) return;

    var debouncedSearch = debounce(function () {
      var q = input.value.trim();
      if (q) {
        performSearch(q);
      } else {
        clearSearchFilter();
      }
    }, SEARCH_DEBOUNCE);

    input.addEventListener('input', debouncedSearch);

    /* Clear filter on Escape */
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        input.value = '';
        clearSearchFilter();
        input.blur();
        var results = document.getElementById('globalSearchResults');
        if (results) results.classList.add('d-none');
      }
    });
  }

  /* =========================================================================
     4. BACK TO TOP
     ========================================================================= */
  var SCROLL_THRESHOLD = 300; /* px before button appears */

  /** Update back-to-top button visibility based on scroll position. */
  function updateBackToTop() {
    var btn = document.getElementById('backToTop');
    if (!btn) return;
    var visible = window.scrollY > SCROLL_THRESHOLD;
    btn.style.opacity        = visible ? '1'    : '0';
    btn.style.pointerEvents  = visible ? 'auto' : 'none';
    btn.setAttribute('aria-hidden', visible ? 'false' : 'true');
  }

  /** Initialise back-to-top behaviour. */
  function initBackToTop() {
    var btn = document.getElementById('backToTop');
    if (!btn) return;

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    window.addEventListener('scroll', debounce(updateBackToTop, 60), { passive: true });
    updateBackToTop(); /* initial state */
  }

  /* =========================================================================
     5. BOOTSTRAP TOOLTIPS & POPOVERS
     ========================================================================= */

  /** Initialise Bootstrap tooltips. */
  function initTooltips() {
    if (typeof bootstrap === 'undefined') return;
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
      if (bootstrap.Tooltip.getInstance(el)) return;
      try { new bootstrap.Tooltip(el, { trigger: 'hover focus' }); } catch (err) { /* ignore */ }
    });
  }

  /** Initialise Bootstrap popovers. */
  function initPopovers() {
    if (typeof bootstrap === 'undefined') return;
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
      if (bootstrap.Popover.getInstance(el)) return;
      try { new bootstrap.Popover(el); } catch (err) { /* ignore */ }
    });
  }

  /* =========================================================================
     6. KEYBOARD SHORTCUTS
     ========================================================================= */

  function initKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
      /* Alt + D : toggle dark mode */
      if (e.altKey && e.key === 'd') {
        e.preventDefault();
        toggleTheme();
        return;
      }

      /* Alt + S : toggle sidebar */
      if (e.altKey && e.key === 's') {
        e.preventDefault();
        handleSidebarToggle();
        return;
      }

      /* Alt + T : scroll back to top */
      if (e.altKey && e.key === 't') {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }
    });
  }

  /* =========================================================================
     7. MUTATION OBSERVER — re-init tooltips for dynamically added elements
     ========================================================================= */

  function initDynamicTooltips() {
    if (!window.MutationObserver) return;
    var observer = new MutationObserver(debounce(function () {
      initTooltips();
      initPopovers();
    }, 400));
    observer.observe(document.body, { childList: true, subtree: true });
  }

  /* =========================================================================
     8. ACTIVE SIDEBAR LINK
     ========================================================================= */

  function highlightActiveSidebarLink() {
    var path = window.location.pathname;
    var bestMatch = null;
    var bestLen   = 0;

    document.querySelectorAll('.sidebar-link[href]').forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href || href === '#') return;
      if (path.startsWith(href) && href.length > bestLen) {
        bestLen   = href.length;
        bestMatch = link;
      }
    });

    if (bestMatch) {
      bestMatch.classList.add('active');
      var parent = bestMatch.closest('.collapse');
      if (parent) {
        parent.classList.add('show');
        var trigger = document.querySelector('[data-bs-target="#' + parent.id + '"]');
        if (trigger) trigger.setAttribute('aria-expanded', 'true');
      }
    }
  }

  /* =========================================================================
     9. THEME-AWARE META (PWA theme-color)
     ========================================================================= */

  function syncThemeColor(theme) {
    var meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) return;
    meta.setAttribute('content', theme === DARK_VALUE ? '#0F172A' : '#4F46E5');
  }

  /* =========================================================================
     INIT
     ========================================================================= */

  function init() {
    initDarkMode();
    initSidebar();
    initSearch();
    initBackToTop();
    initKeyboardShortcuts();
    initTooltips();
    initPopovers();
    initDynamicTooltips();
    highlightActiveSidebarLink();

    syncThemeColor(document.documentElement.getAttribute('data-theme') || LIGHT_VALUE);
    document.addEventListener('themechange', function (e) {
      syncThemeColor(e.detail.theme);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* =========================================================================
     PUBLIC API
     ========================================================================= */
  window.TonyTheme = {
    toggleTheme:            toggleTheme,
    applyTheme:             applyTheme,
    toggleDesktopSidebar:   toggleDesktopSidebar,
    openMobileSidebar:      openMobileSidebar,
    closeMobileSidebar:     closeMobileSidebar,
    initTooltips:           initTooltips,
    initPopovers:           initPopovers,
  };

}());
