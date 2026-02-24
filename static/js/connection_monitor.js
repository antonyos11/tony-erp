/**
 * Tony ERP - Connection Monitor v1.0
 * يراقب اتصال السيرفر ويحدث حالة الاتصال
 *
 * أضف في base template:
 * <script src="{% static 'js/connection_monitor.js' %}"></script>
 */
;(function(window, document) {
    'use strict';

    var HEARTBEAT_URL = '/heartbeat/';
    var CHECK_INTERVAL = 30000;   // 30 ثانية
    var RETRY_INTERVAL = 5000;    // 5 ثوان
    var MAX_RETRIES = 3;
    var retryCount = 0;
    var isOnline = true;

    function checkConnection() {
        var xhr = new XMLHttpRequest();
        xhr.timeout = 10000;

        xhr.onload = function() {
            if (xhr.status === 200) {
                if (!isOnline) {
                    isOnline = true;
                    retryCount = 0;
                    fireEvent('server-online');
                }
                scheduleNext(CHECK_INTERVAL);
            } else {
                handleError();
            }
        };

        xhr.onerror = function() { handleError(); };
        xhr.ontimeout = function() { handleError(); };

        try {
            xhr.open('GET', HEARTBEAT_URL + '?_=' + Date.now(), true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.send();
        } catch (e) {
            handleError();
        }
    }

    function handleError() {
        retryCount++;
        if (isOnline) {
            isOnline = false;
            fireEvent('server-offline');
        }

        if (retryCount <= MAX_RETRIES) {
            scheduleNext(RETRY_INTERVAL);
        } else {
            scheduleNext(CHECK_INTERVAL * 2);
            retryCount = 0;
        }
    }

    function scheduleNext(interval) {
        setTimeout(checkConnection, interval);
    }

    function fireEvent(name) {
        try {
            var ev = new CustomEvent(name, { detail: { online: isOnline } });
            document.dispatchEvent(ev);
        } catch (e) {
            // IE11 fallback
        }
    }

    // Start after page load
    function init() {
        setTimeout(checkConnection, 2000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Browser events
    window.addEventListener('online', function() {
        retryCount = 0;
        checkConnection();
    });

    window.addEventListener('offline', function() {
        isOnline = false;
        fireEvent('server-offline');
    });

    // Public API
    window.TonyERP = window.TonyERP || {};
    window.TonyERP.connectionMonitor = {
        check: checkConnection,
        isOnline: function() { return isOnline; }
    };

})(window, document);
