/**
 * Tony ERP - Dashboard Stats Auto-Refresh v1.0
 * تحديث تلقائي لبيانات لوحة التحكم لضمان تطابق الأرقام
 *
 * يعتمد على data attributes في HTML:
 *   data-stat="sales-total"
 *   data-stat="purchases-total"
 *   data-stat="net-total"
 *   data-stat="collections"
 *   data-stat="expenses"
 *   data-stat="month-sales"
 *   data-stat="month-purchases"
 *
 * أضف في dashboard template:
 * <script src="{% static 'js/dashboard_stats.js' %}"></script>
 */
;(function(window, document) {
    'use strict';

    var STATS_URL = '/api/dashboard/stats/';
    var REFRESH_INTERVAL = 60000; // دقيقة

    function getCookie(name) {
        var value = '; ' + document.cookie;
        var parts = value.split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    function formatNumber(num) {
        if (typeof num !== 'number') num = parseFloat(num) || 0;
        return num.toLocaleString('ar-SA', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        });
    }

    function updateElements(selector, value) {
        var els = document.querySelectorAll(selector);
        for (var i = 0; i < els.length; i++) {
            els[i].textContent = value;
        }
    }

    function refreshStats() {
        var xhr = new XMLHttpRequest();
        xhr.timeout = 15000;

        xhr.onload = function() {
            if (xhr.status === 200) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    applyStats(data);
                } catch (e) {
                    // ignore parse errors
                }
            }
        };

        xhr.onerror = function() {};

        try {
            xhr.open('GET', STATS_URL + '?_=' + Date.now(), true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            var csrf = getCookie('csrftoken');
            if (csrf) {
                xhr.setRequestHeader('X-CSRFToken', csrf);
            }
            xhr.send();
        } catch (e) {
            // ignore
        }
    }

    function applyStats(data) {
        if (!data || !data.today) return;
        var t = data.today;

        if (t.sales) {
            updateElements('[data-stat="sales-total"]', formatNumber(t.sales.total));
            updateElements('[data-stat="sales-count"]', t.sales.count);
        }
        if (t.purchases) {
            updateElements('[data-stat="purchases-total"]', formatNumber(t.purchases.total));
            updateElements('[data-stat="purchases-count"]', t.purchases.count);
        }
        if (t.net !== undefined) {
            var netEls = document.querySelectorAll('[data-stat="net-total"]');
            for (var i = 0; i < netEls.length; i++) {
                netEls[i].textContent = formatNumber(t.net);
                netEls[i].classList.toggle('text-danger', t.net < 0);
                netEls[i].classList.toggle('text-success', t.net >= 0);
            }
        }
        updateElements('[data-stat="collections"]', formatNumber(t.collections || 0));
        updateElements('[data-stat="expenses"]', formatNumber(t.expenses || 0));

        if (data.month) {
            updateElements('[data-stat="month-sales"]', formatNumber(data.month.sales || 0));
            updateElements('[data-stat="month-purchases"]', formatNumber(data.month.purchases || 0));
        }
    }

    function init() {
        // Only active on dashboard page
        if (!document.querySelector('[data-stat]')) return;
        setTimeout(refreshStats, 3000);
        setInterval(refreshStats, REFRESH_INTERVAL);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.TonyERP = window.TonyERP || {};
    window.TonyERP.dashboardStats = { refresh: refreshStats };

})(window, document);
