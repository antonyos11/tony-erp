/**
 * RITA ERP — charts.js
 * دوال مشتركة لرسم Charts باستخدام Chart.js
 * Sprint 16
 */

'use strict';

// ألوان موحدة
const RITA_COLORS = {
  blue:   'rgba(26, 115, 232, 0.85)',
  green:  'rgba(46, 125, 50, 0.85)',
  red:    'rgba(211, 47, 47, 0.85)',
  orange: 'rgba(245, 124, 0, 0.85)',
  purple: 'rgba(106, 27, 154, 0.85)',
  teal:   'rgba(0, 137, 123, 0.85)',
  blues: [
    'rgba(26,115,232,0.85)','rgba(66,133,244,0.85)','rgba(100,181,246,0.85)',
    'rgba(144,202,249,0.85)','rgba(187,222,251,0.85)',
  ],
  multiColors: [
    'rgba(26,115,232,0.85)','rgba(46,125,50,0.85)','rgba(211,47,47,0.85)',
    'rgba(245,124,0,0.85)','rgba(106,27,154,0.85)','rgba(0,137,123,0.85)',
    'rgba(183,28,28,0.85)','rgba(74,20,140,0.85)','rgba(1,87,155,0.85)','rgba(27,94,32,0.85)',
  ],
};

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', rtl: true },
    tooltip: {
      callbacks: {
        label: ctx => {
          const val = ctx.parsed.y ?? ctx.parsed;
          return typeof val === 'number'
            ? ` ${val.toLocaleString('ar-EG', { minimumFractionDigits: 0 })} ج.م`
            : val;
        },
      },
    },
  },
};

/**
 * 1. رسم خط (Line Chart) — مبيعات يومية
 * @param {string} canvasId - id عنصر canvas
 * @param {string[]} labels
 * @param {number[]} salesData
 * @param {string} title
 */
function drawSalesTrendChart(canvasId, labels, salesData, title = 'مبيعات آخر 30 يوم') {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: title,
        data: salesData,
        borderColor: RITA_COLORS.blue,
        backgroundColor: 'rgba(26,115,232,0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 6,
      }],
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => v.toLocaleString('ar-EG') } },
        x: { ticks: { maxTicksLimit: 10 } },
      },
    },
  });
}

/**
 * 2. Doughnut Chart — توزيع المبيعات حسب القناة/الفئة
 * @param {string} canvasId
 * @param {string[]} labels
 * @param {number[]} data
 */
function drawDoughnutChart(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: RITA_COLORS.multiColors,
        borderWidth: 2,
        borderColor: '#fff',
      }],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          callbacks: {
            label: ctx => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
              return ` ${ctx.label}: ${ctx.parsed.toLocaleString('ar-EG')} (${pct}%)`;
            },
          },
        },
      },
    },
  });
}

/**
 * 3. Bar Chart — أفضل المنتجات
 * @param {string} canvasId
 * @param {string[]} labels
 * @param {number[]} revenueData
 * @param {number[]} profitData - اختياري
 */
function drawTopProductsChart(canvasId, labels, revenueData, profitData = null) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const datasets = [{
    label: 'الإيراد',
    data: revenueData,
    backgroundColor: RITA_COLORS.blue,
  }];

  if (profitData && profitData.length) {
    datasets.push({
      label: 'الربح',
      data: profitData,
      backgroundColor: RITA_COLORS.green,
    });
  }

  new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => v.toLocaleString('ar-EG') } },
        x: { ticks: { maxTicksLimit: 12 } },
      },
    },
  });
}

/**
 * 4. Horizontal Bar Chart — مقارنة الفروع
 * @param {string} canvasId
 * @param {string[]} labels - أسماء الفروع
 * @param {number[]} salesData
 * @param {number[]} profitData - اختياري
 */
function drawBranchComparisonChart(canvasId, labels, salesData, profitData = null) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const datasets = [{
    label: 'المبيعات',
    data: salesData,
    backgroundColor: RITA_COLORS.blue,
  }];

  if (profitData && profitData.length) {
    datasets.push({
      label: 'الربح',
      data: profitData,
      backgroundColor: RITA_COLORS.green,
    });
  }

  new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      ...CHART_DEFAULTS,
      indexAxis: 'y',
      scales: {
        x: { beginAtZero: true, ticks: { callback: v => v.toLocaleString('ar-EG') } },
      },
    },
  });
}

/**
 * 5. Line Chart — اتجاه الإنتاج
 * @param {string} canvasId
 * @param {string[]} labels
 * @param {number[]} plannedData
 * @param {number[]} actualData
 */
function drawProductionTrendChart(canvasId, labels, plannedData, actualData) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'مخطط',
          data: plannedData,
          borderColor: RITA_COLORS.blue,
          backgroundColor: 'transparent',
          borderDash: [5, 5],
          tension: 0.3,
        },
        {
          label: 'فعلي',
          data: actualData,
          borderColor: RITA_COLORS.green,
          backgroundColor: 'rgba(46,125,50,0.1)',
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => v.toLocaleString('ar-EG') } },
      },
    },
  });
}

/**
 * 6. Grouped Bar Chart — ميزانية vs فعلي (مصروفات)
 * @param {string} canvasId
 * @param {string[]} labels - أسماء فئات المصروفات
 * @param {number[]} budgetData
 * @param {number[]} actualData
 */
function drawBudgetVsActualChart(canvasId, labels, budgetData, actualData) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'الميزانية',
          data: budgetData,
          backgroundColor: RITA_COLORS.blue,
        },
        {
          label: 'الفعلي',
          data: actualData,
          backgroundColor: actualData.map((v, i) => v > budgetData[i] ? RITA_COLORS.red : RITA_COLORS.green),
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => v.toLocaleString('ar-EG') } },
      },
    },
  });
}

// ---- تهيئة تلقائية من data attributes ----
document.addEventListener('DOMContentLoaded', () => {
  // كل canvas بدا بـ data-chart-type يُرسم تلقائياً
  document.querySelectorAll('canvas[data-chart-type]').forEach(canvas => {
    const type = canvas.dataset.chartType;
    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const data1 = JSON.parse(canvas.dataset.data1 || '[]');
    const data2 = JSON.parse(canvas.dataset.data2 || '[]');

    switch (type) {
      case 'sales-trend':
        drawSalesTrendChart(canvas.id, labels, data1);
        break;
      case 'doughnut':
        drawDoughnutChart(canvas.id, labels, data1);
        break;
      case 'top-products':
        drawTopProductsChart(canvas.id, labels, data1, data2.length ? data2 : null);
        break;
      case 'branch-comparison':
        drawBranchComparisonChart(canvas.id, labels, data1, data2.length ? data2 : null);
        break;
      case 'production-trend':
        drawProductionTrendChart(canvas.id, labels, data1, data2);
        break;
      case 'budget-vs-actual':
        drawBudgetVsActualChart(canvas.id, labels, data1, data2);
        break;
    }
  });
});
