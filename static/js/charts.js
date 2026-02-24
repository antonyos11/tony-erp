/**
 * نظام الرسوم البيانية المتقدم
 * Advanced Charts System
 * Version: 2.0.0
 */

(function() {
  'use strict';

  // =============================================================================
  // Configuration
  // =============================================================================
  
  const CHART_COLORS = {
    primary: '#1e3a5f',
    accent: '#00d4aa',
    accentLight: '#00f5c4',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',
    purple: '#8b5cf6',
    pink: '#ec4899',
    gray: '#6b7280',
    lightGray: '#e5e7eb',
    
    // Gradients
    gradientAccent: ['rgba(0, 212, 170, 0.8)', 'rgba(0, 245, 196, 0.2)'],
    gradientPrimary: ['rgba(30, 58, 95, 0.8)', 'rgba(30, 58, 95, 0.1)'],
    gradientSuccess: ['rgba(16, 185, 129, 0.8)', 'rgba(16, 185, 129, 0.1)'],
  };

  const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 750,
      easing: 'easeOutQuart',
    },
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          padding: 20,
          usePointStyle: true,
          font: { size: 12 },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#fff',
        bodyColor: '#e2e8f0',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        displayColors: true,
        intersect: false,
        mode: 'index',
      },
    },
  };

  // =============================================================================
  // Chart Factory
  // =============================================================================
  
  class ChartFactory {
    constructor() {
      this.charts = new Map();
    }

    /**
     * إنشاء رسم بياني جديد
     */
    create(canvasId, type, data, options = {}) {
      const canvas = document.getElementById(canvasId);
      if (!canvas) {
        console.warn(`Canvas not found: ${canvasId}`);
        return null;
      }

      // تدمير الرسم القديم إن وُجد
      if (this.charts.has(canvasId)) {
        this.charts.get(canvasId).destroy();
      }

      const ctx = canvas.getContext('2d');
      const mergedOptions = this.mergeOptions(CHART_DEFAULTS, options);

      const chart = new Chart(ctx, {
        type,
        data,
        options: mergedOptions,
      });

      this.charts.set(canvasId, chart);
      return chart;
    }

    /**
     * دمج الخيارات
     */
    mergeOptions(defaults, custom) {
      return {
        ...defaults,
        ...custom,
        plugins: {
          ...defaults.plugins,
          ...(custom.plugins || {}),
        },
      };
    }

    /**
     * تحديث بيانات الرسم
     */
    update(canvasId, data) {
      const chart = this.charts.get(canvasId);
      if (chart) {
        chart.data = data;
        chart.update('active');
      }
    }

    /**
     * تدمير رسم
     */
    destroy(canvasId) {
      const chart = this.charts.get(canvasId);
      if (chart) {
        chart.destroy();
        this.charts.delete(canvasId);
      }
    }

    /**
     * تدمير جميع الرسوم
     */
    destroyAll() {
      this.charts.forEach(chart => chart.destroy());
      this.charts.clear();
    }
  }

  // =============================================================================
  // Chart Presets
  // =============================================================================
  
  const ChartPresets = {
    /**
     * رسم بياني خطي للمبيعات
     */
    salesLine(canvasId, labels, data, options = {}) {
      return chartFactory.create(canvasId, 'line', {
        labels,
        datasets: [{
          label: 'المبيعات',
          data,
          borderColor: CHART_COLORS.accent,
          backgroundColor: createGradient(canvasId, CHART_COLORS.gradientAccent),
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: CHART_COLORS.accent,
        }],
      }, {
        scales: {
          x: {
            grid: { display: false },
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(0, 0, 0, 0.05)' },
          },
        },
        ...options,
      });
    },

    /**
     * رسم بياني دائري
     */
    doughnut(canvasId, labels, data, colors = null, options = {}) {
      const defaultColors = [
        CHART_COLORS.accent,
        CHART_COLORS.primary,
        CHART_COLORS.warning,
        CHART_COLORS.danger,
        CHART_COLORS.purple,
        CHART_COLORS.info,
      ];

      return chartFactory.create(canvasId, 'doughnut', {
        labels,
        datasets: [{
          data,
          backgroundColor: colors || defaultColors.slice(0, data.length),
          borderWidth: 0,
          hoverOffset: 10,
        }],
      }, {
        cutout: '65%',
        plugins: {
          legend: {
            position: 'right',
          },
        },
        ...options,
      });
    },

    /**
     * رسم بياني عمودي
     */
    bar(canvasId, labels, datasets, options = {}) {
      return chartFactory.create(canvasId, 'bar', {
        labels,
        datasets: datasets.map((ds, i) => ({
          label: ds.label,
          data: ds.data,
          backgroundColor: ds.color || [CHART_COLORS.accent, CHART_COLORS.primary][i % 2],
          borderRadius: 6,
          maxBarThickness: 50,
        })),
      }, {
        scales: {
          x: {
            grid: { display: false },
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(0, 0, 0, 0.05)' },
          },
        },
        ...options,
      });
    },

    /**
     * مقارنة المبيعات والمشتريات
     */
    salesVsPurchases(canvasId, labels, salesData, purchasesData, options = {}) {
      return chartFactory.create(canvasId, 'bar', {
        labels,
        datasets: [
          {
            label: 'المبيعات',
            data: salesData,
            backgroundColor: CHART_COLORS.accent,
            borderRadius: 6,
          },
          {
            label: 'المشتريات',
            data: purchasesData,
            backgroundColor: CHART_COLORS.primary,
            borderRadius: 6,
          },
        ],
      }, {
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true },
        },
        ...options,
      });
    },

    /**
     * رسم بياني للتدفق النقدي
     */
    cashFlow(canvasId, labels, inflow, outflow, options = {}) {
      return chartFactory.create(canvasId, 'line', {
        labels,
        datasets: [
          {
            label: 'الإيرادات',
            data: inflow,
            borderColor: CHART_COLORS.success,
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.4,
          },
          {
            label: 'المصروفات',
            data: outflow,
            borderColor: CHART_COLORS.danger,
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.4,
          },
        ],
      }, options);
    },

    /**
     * مؤشرات الأداء
     */
    gauge(canvasId, value, max = 100, options = {}) {
      return chartFactory.create(canvasId, 'doughnut', {
        labels: ['القيمة', 'المتبقي'],
        datasets: [{
          data: [value, max - value],
          backgroundColor: [
            CHART_COLORS.accent,
            CHART_COLORS.lightGray,
          ],
          borderWidth: 0,
        }],
      }, {
        rotation: -90,
        circumference: 180,
        cutout: '75%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false },
        },
        ...options,
      });
    },
  };

  // =============================================================================
  // Utility Functions
  // =============================================================================
  
  /**
   * إنشاء تدرج لوني
   */
  function createGradient(canvasId, colors) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return colors[0];

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, colors[0]);
    gradient.addColorStop(1, colors[1]);
    return gradient;
  }

  /**
   * تنسيق الأرقام للعرض
   */
  function formatNumber(value, decimals = 0) {
    return new Intl.NumberFormat('ar-SA', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  }

  /**
   * تنسيق العملة
   */
  function formatCurrency(value, currency = 'EGP') {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency,
    }).format(value);
  }

  // =============================================================================
  // Real-time Updates
  // =============================================================================
  
  class ChartUpdater {
    constructor(chartId, fetchUrl, interval = 30000) {
      this.chartId = chartId;
      this.fetchUrl = fetchUrl;
      this.interval = interval;
      this.timer = null;
    }

    start() {
      this.fetchAndUpdate();
      this.timer = setInterval(() => this.fetchAndUpdate(), this.interval);
    }

    stop() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    }

    async fetchAndUpdate() {
      try {
        const response = await fetch(this.fetchUrl, {
          headers: { 'Accept': 'application/json' },
        });
        
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        chartFactory.update(this.chartId, data);
      } catch (error) {
        console.warn(`Failed to update chart ${this.chartId}:`, error);
      }
    }
  }

  // =============================================================================
  // Initialize
  // =============================================================================
  
  const chartFactory = new ChartFactory();

  // Expose to global
  window.ERPCharts = {
    factory: chartFactory,
    presets: ChartPresets,
    colors: CHART_COLORS,
    updater: ChartUpdater,
    formatNumber,
    formatCurrency,
  };

  console.log('[ERP Charts] System initialized');

})();
