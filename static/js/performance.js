/**
 * نظام تحسين الأداء الشامل
 * Advanced Performance Enhancement System
 * Version: 2.0.0
 */

(function() {
  'use strict';

  // =============================================================================
  // Configuration
  // =============================================================================
  const CONFIG = {
    lazyLoadOffset: 200,
    debounceDelay: 250,
    animationObserverThreshold: 0.1,
    cachePrefix: 'erp_cache_',
    cacheExpiry: 5 * 60 * 1000, // 5 minutes
  };

  // =============================================================================
  // Utility Functions
  // =============================================================================
  
  /**
   * Debounce function to limit rapid executions
   */
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * Throttle function to limit function calls
   */
  function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }

  /**
   * Safe localStorage with fallback
   */
  const safeStorage = {
    get(key) {
      try {
        const item = localStorage.getItem(CONFIG.cachePrefix + key);
        if (!item) return null;
        const parsed = JSON.parse(item);
        if (parsed.expiry && Date.now() > parsed.expiry) {
          this.remove(key);
          return null;
        }
        return parsed.value;
      } catch (e) {
        return null;
      }
    },
    set(key, value, expiry = CONFIG.cacheExpiry) {
      try {
        const item = {
          value,
          expiry: expiry ? Date.now() + expiry : null
        };
        localStorage.setItem(CONFIG.cachePrefix + key, JSON.stringify(item));
      } catch (e) {
        // Storage full or not available
      }
    },
    remove(key) {
      try {
        localStorage.removeItem(CONFIG.cachePrefix + key);
      } catch (e) {}
    }
  };

  // =============================================================================
  // Lazy Loading System
  // =============================================================================
  
  class LazyLoader {
    constructor() {
      this.observer = null;
      this.init();
    }

    init() {
      if ('IntersectionObserver' in window) {
        this.observer = new IntersectionObserver(
          (entries) => this.handleIntersection(entries),
          {
            rootMargin: `${CONFIG.lazyLoadOffset}px`,
            threshold: 0
          }
        );

        this.observeElements();
      } else {
        // Fallback for older browsers
        this.loadAllImages();
      }
    }

    observeElements() {
      document.querySelectorAll('[data-lazy-src], [data-lazy-bg]').forEach(el => {
        this.observer.observe(el);
      });
    }

    handleIntersection(entries) {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          this.loadElement(entry.target);
          this.observer.unobserve(entry.target);
        }
      });
    }

    loadElement(el) {
      const lazySrc = el.getAttribute('data-lazy-src');
      const lazyBg = el.getAttribute('data-lazy-bg');

      if (lazySrc) {
        el.src = lazySrc;
        el.removeAttribute('data-lazy-src');
      }

      if (lazyBg) {
        el.style.backgroundImage = `url('${lazyBg}')`;
        el.removeAttribute('data-lazy-bg');
      }

      el.classList.add('lazy-loaded');
    }

    loadAllImages() {
      document.querySelectorAll('[data-lazy-src]').forEach(el => this.loadElement(el));
    }
  }

  // =============================================================================
  // Scroll Performance
  // =============================================================================
  
  class ScrollOptimizer {
    constructor() {
      this.scrollY = 0;
      this.ticking = false;
      this.init();
    }

    init() {
      window.addEventListener('scroll', () => {
        this.scrollY = window.scrollY;
        this.requestTick();
      }, { passive: true });
    }

    requestTick() {
      if (!this.ticking) {
        requestAnimationFrame(() => this.update());
      }
      this.ticking = true;
    }

    update() {
      this.ticking = false;
      
      // Parallax effects
      document.querySelectorAll('[data-parallax]').forEach(el => {
        const speed = parseFloat(el.getAttribute('data-parallax')) || 0.5;
        el.style.transform = `translateY(${this.scrollY * speed}px)`;
      });

      // Show/hide based on scroll
      const scrollThreshold = 300;
      document.querySelectorAll('[data-show-on-scroll]').forEach(el => {
        if (this.scrollY > scrollThreshold) {
          el.classList.add('visible');
        } else {
          el.classList.remove('visible');
        }
      });

      // Back to top button
      const backToTop = document.getElementById('backToTop');
      if (backToTop) {
        backToTop.style.opacity = this.scrollY > 500 ? '1' : '0';
        backToTop.style.pointerEvents = this.scrollY > 500 ? 'auto' : 'none';
      }
    }
  }

  // =============================================================================
  // Animation on Scroll
  // =============================================================================
  
  class ScrollAnimator {
    constructor() {
      this.observer = null;
      this.init();
    }

    init() {
      if ('IntersectionObserver' in window) {
        this.observer = new IntersectionObserver(
          (entries) => this.handleIntersection(entries),
          {
            threshold: CONFIG.animationObserverThreshold,
            rootMargin: '0px 0px -50px 0px'
          }
        );

        this.observeElements();
      }
    }

    observeElements() {
      document.querySelectorAll('[data-animate]').forEach(el => {
        el.style.opacity = '0';
        this.observer.observe(el);
      });
    }

    handleIntersection(entries) {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const animation = el.getAttribute('data-animate') || 'fadeInUp';
          const delay = el.getAttribute('data-animate-delay') || '0';
          
          el.style.animationDelay = `${delay}ms`;
          el.classList.add(animation, 'animated');
          el.style.opacity = '1';
          
          this.observer.unobserve(el);
        }
      });
    }
  }

  // =============================================================================
  // Form Auto-save
  // =============================================================================
  
  class FormAutoSave {
    constructor() {
      this.forms = new Map();
      this.init();
    }

    init() {
      document.querySelectorAll('[data-autosave]').forEach(form => {
        const key = form.getAttribute('data-autosave') || form.id || 'form_' + Date.now();
        this.forms.set(form, key);
        
        // Restore saved data
        this.restore(form, key);
        
        // Listen for changes
        form.addEventListener('input', debounce(() => this.save(form, key), 1000));
        form.addEventListener('change', () => this.save(form, key));
        
        // Clear on successful submit
        form.addEventListener('submit', () => {
          safeStorage.remove('autosave_' + key);
        });
      });
    }

    save(form, key) {
      const data = new FormData(form);
      const obj = {};
      data.forEach((value, field) => {
        if (field !== 'csrfmiddlewaretoken') {
          obj[field] = value;
        }
      });
      safeStorage.set('autosave_' + key, obj, 24 * 60 * 60 * 1000); // 24 hours
    }

    restore(form, key) {
      const saved = safeStorage.get('autosave_' + key);
      if (!saved) return;

      Object.entries(saved).forEach(([field, value]) => {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
          if (input.type === 'checkbox' || input.type === 'radio') {
            input.checked = value === input.value || value === true;
          } else {
            input.value = value;
          }
        }
      });

      // Show notification
      this.showRestoreNotification(form);
    }

    showRestoreNotification(form) {
      const notification = document.createElement('div');
      notification.className = 'alert alert-info alert-dismissible fade show';
      notification.innerHTML = `
        <i class="bi bi-info-circle me-2"></i>
        تم استعادة البيانات المحفوظة تلقائياً
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      `;
      form.insertBefore(notification, form.firstChild);
      
      setTimeout(() => notification.remove(), 5000);
    }
  }

  // =============================================================================
  // Table Enhancements
  // =============================================================================
  
  class TableEnhancer {
    constructor() {
      this.init();
    }

    init() {
      document.querySelectorAll('.table-enhanced').forEach(table => {
        this.addSorting(table);
        this.addSearch(table);
        this.addRowSelection(table);
      });
    }

    addSorting(table) {
      const headers = table.querySelectorAll('th[data-sortable]');
      headers.forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => this.sortTable(table, th));
      });
    }

    sortTable(table, th) {
      const index = Array.from(th.parentNode.children).indexOf(th);
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const isAsc = th.classList.contains('sorted-asc');
      
      // Reset all headers
      table.querySelectorAll('th').forEach(h => {
        h.classList.remove('sorted-asc', 'sorted-desc');
      });

      rows.sort((a, b) => {
        const aVal = a.children[index]?.textContent.trim() || '';
        const bVal = b.children[index]?.textContent.trim() || '';
        
        const aNum = parseFloat(aVal.replace(/[^\d.-]/g, ''));
        const bNum = parseFloat(bVal.replace(/[^\d.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
          return isAsc ? bNum - aNum : aNum - bNum;
        }
        return isAsc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      });

      th.classList.add(isAsc ? 'sorted-desc' : 'sorted-asc');
      tbody.innerHTML = '';
      rows.forEach(row => tbody.appendChild(row));
    }

    addSearch(table) {
      const wrapper = table.closest('.table-wrapper');
      if (!wrapper) return;

      const searchInput = wrapper.querySelector('[data-table-search]');
      if (!searchInput) return;

      searchInput.addEventListener('input', debounce((e) => {
        const query = e.target.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query) ? '' : 'none';
        });
      }, CONFIG.debounceDelay));
    }

    addRowSelection(table) {
      const rows = table.querySelectorAll('tbody tr');
      rows.forEach(row => {
        row.addEventListener('click', (e) => {
          if (e.target.closest('a, button, input')) return;
          row.classList.toggle('selected');
          this.updateSelectionCount(table);
        });
      });
    }

    updateSelectionCount(table) {
      const selected = table.querySelectorAll('tbody tr.selected').length;
      const counter = table.closest('.table-wrapper')?.querySelector('[data-selection-count]');
      if (counter) {
        counter.textContent = selected;
        counter.closest('.selection-info').style.display = selected > 0 ? '' : 'none';
      }
    }
  }

  // =============================================================================
  // Network Status Handler
  // =============================================================================
  
  class NetworkHandler {
    constructor() {
      this.isOnline = navigator.onLine;
      this.init();
    }

    init() {
      window.addEventListener('online', () => this.handleOnline());
      window.addEventListener('offline', () => this.handleOffline());
    }

    handleOnline() {
      this.isOnline = true;
      this.showNotification('تم استعادة الاتصال بالإنترنت', 'success');
      document.body.classList.remove('offline-mode');
    }

    handleOffline() {
      this.isOnline = false;
      this.showNotification('أنت غير متصل بالإنترنت', 'warning');
      document.body.classList.add('offline-mode');
    }

    showNotification(message, type) {
      if (window.showToast) {
        window.showToast(message, type);
      }
    }
  }

  // =============================================================================
  // Keyboard Shortcuts
  // =============================================================================
  
  class KeyboardShortcuts {
    constructor() {
      this.shortcuts = new Map();
      this.init();
    }

    init() {
      // Default shortcuts
      this.register('ctrl+k', () => {
        const searchBtn = document.getElementById('commandPaletteBtn');
        if (searchBtn) searchBtn.click();
      });

      this.register('ctrl+s', (e) => {
        e.preventDefault();
        const form = document.querySelector('form:not([data-no-shortcut-save])');
        if (form) {
          const submitBtn = form.querySelector('[type="submit"]');
          if (submitBtn) submitBtn.click();
        }
      });

      this.register('escape', () => {
        // Close modals
        const modal = document.querySelector('.modal.show');
        if (modal) {
          const closeBtn = modal.querySelector('[data-bs-dismiss="modal"]');
          if (closeBtn) closeBtn.click();
        }
        // Close sidebar on mobile
        if (document.body.classList.contains('sidebar-open')) {
          document.body.classList.remove('sidebar-open');
        }
      });

      document.addEventListener('keydown', (e) => this.handleKeydown(e));
    }

    register(shortcut, callback) {
      this.shortcuts.set(shortcut.toLowerCase(), callback);
    }

    handleKeydown(e) {
      const key = this.getShortcutKey(e);
      const handler = this.shortcuts.get(key);
      if (handler) {
        handler(e);
      }
    }

    getShortcutKey(e) {
      const parts = [];
      if (e.ctrlKey || e.metaKey) parts.push('ctrl');
      if (e.shiftKey) parts.push('shift');
      if (e.altKey) parts.push('alt');
      parts.push(e.key.toLowerCase());
      return parts.join('+');
    }
  }

  // =============================================================================
  // Preload Manager
  // =============================================================================
  
  class PreloadManager {
    constructor() {
      this.preloaded = new Set();
      this.init();
    }

    init() {
      // Preload on link hover
      document.addEventListener('mouseover', (e) => {
        const link = e.target.closest('a[href^="/"]');
        if (link && !this.preloaded.has(link.href)) {
          this.preloadLink(link.href);
        }
      });
    }

    preloadLink(url) {
      if (this.preloaded.has(url)) return;
      this.preloaded.add(url);

      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = url;
      document.head.appendChild(link);
    }
  }

  // =============================================================================
  // Image Optimization
  // =============================================================================
  
  class ImageOptimizer {
    constructor() {
      this.init();
    }

    init() {
      // Add loading="lazy" to all images
      document.querySelectorAll('img:not([loading])').forEach(img => {
        img.loading = 'lazy';
      });

      // Add decoding="async" for better performance
      document.querySelectorAll('img:not([decoding])').forEach(img => {
        img.decoding = 'async';
      });

      // Handle broken images
      document.querySelectorAll('img').forEach(img => {
        img.addEventListener('error', () => this.handleBrokenImage(img));
      });
    }

    handleBrokenImage(img) {
      img.src = '/static/img/placeholder.svg';
      img.alt = 'صورة غير متوفرة';
      img.classList.add('broken-image');
    }
  }

  // =============================================================================
  // Initialize All Systems
  // =============================================================================
  
  function initPerformanceEnhancements() {
    new LazyLoader();
    new ScrollOptimizer();
    new ScrollAnimator();
    new FormAutoSave();
    new TableEnhancer();
    new NetworkHandler();
    new KeyboardShortcuts();
    new PreloadManager();
    new ImageOptimizer();

    console.log('[ERP Performance] All enhancements initialized');
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPerformanceEnhancements);
  } else {
    initPerformanceEnhancements();
  }

  // Expose utilities globally
  window.ERPPerformance = {
    debounce,
    throttle,
    safeStorage,
  };

})();
