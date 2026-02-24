/**
 * Tony ERP Print Agent Client v3.5
 * يتصل بالـ Agent المحلي فقط (localhost) - الطابعات على جهاز المستخدم
 * يدعم: Zebra ZE220 | XPrinter (حراري) | أي طابعة A4
 * + keepalive ping كل 15 ثانية
 */
const TonyPrint = (function() {
    'use strict';

    let _ws = null;
    let _connected = false;
    let _printers = {};
    let _defaultPrinter = null;
    let _reconnectTimer = null;
    let _pendingRequests = {};
    let _requestId = 0;
    const _port = 9876;
    const _reconnectInterval = 5000;
    let _currentHost = null;
    let _logEl = null;
    let _connectAttempt = 0;
    let _fullRetryCount = 0;
    const _maxFullRetries = 3;

    let _keepaliveTimer = null;

    // Only connect to LOCAL agent - printers are on user's machine, not the server
    function _getHosts() {
        return ['localhost', '127.0.0.1'];
    }

    function _startKeepalive() {
        _stopKeepalive();
        _keepaliveTimer = setInterval(function() {
            if (_ws && _ws.readyState === WebSocket.OPEN) {
                try {
                    _ws.send(JSON.stringify({action: 'ping', request_id: 'keepalive_' + Date.now()}));
                } catch(e) {
                    _connected = false;
                    _updateStatusUI('غير متصل ✗', 'danger');
                }
            } else if (_connected) {
                _connected = false;
                _updateStatusUI('غير متصل ✗', 'danger');
            }
        }, 15000);
    }

    function _stopKeepalive() {
        if (_keepaliveTimer) {
            clearInterval(_keepaliveTimer);
            _keepaliveTimer = null;
        }
    }

    function _log(msg) {
        var ts = new Date().toLocaleTimeString('ar-EG');
        console.log('[TonyPrint ' + ts + '] ' + msg);
        if (!_logEl) _logEl = document.getElementById('print-agent-log');
        if (_logEl) {
            _logEl.innerHTML += '<div>[' + ts + '] ' + msg + '</div>';
            _logEl.scrollTop = _logEl.scrollHeight;
        }
    }

    // ═══════════════════════════════════════════
    // Connection - tries localhost first, then server
    // ═══════════════════════════════════════════

    function connect(host, port) {
        var wsPort = port || _port;

        if (host) {
            // Explicit host provided - connect directly
            _connectToHost(host, wsPort);
            return;
        }

        // Auto-discovery: try each host in sequence
        var hosts = _getHosts();
        _connectAttempt = 0;
        _tryNextHost(hosts, wsPort);
    }

    function _tryNextHost(hosts, wsPort) {
        if (_connected) return; // Already connected
        if (_connectAttempt >= hosts.length) {
            _fullRetryCount++;
            // All hosts failed
            if (_fullRetryCount >= _maxFullRetries) {
                _log('✗ Print Agent غير متوفر - توقف عن المحاولة (يمكنك إعادة المحاولة يدوياً)');
                _updateStatusUI('غير متصل ✗', 'danger');
                return;
            }
            _log('✗ لم يتم العثور على Print Agent المحلي - محاولة ' + _fullRetryCount + '/' + _maxFullRetries);
            _updateStatusUI('غير متصل ✗', 'danger');
            _reconnectTimer = setTimeout(function() {
                _connectAttempt = 0;
                _tryNextHost(hosts, wsPort);
            }, _reconnectInterval);
            return;
        }

        var host = hosts[_connectAttempt];
        _connectAttempt++;

        _log('محاولة الاتصال بـ ' + host + ':' + wsPort + ' ...');

        try {
            // Close any existing connection attempt
            if (_ws) {
                try { _ws.onclose = null; _ws.onerror = null; _ws.close(); } catch(e) {}
                _ws = null;
            }

            var wsUrl = 'ws://' + host + ':' + wsPort;
            _ws = new WebSocket(wsUrl);

            // Give this host 2 seconds to connect before trying next
            var connectTimeout = setTimeout(function() {
                if (!_connected && _ws && _ws.readyState !== WebSocket.OPEN) {
                    _log('✗ ' + host + ' لم يستجب');
                    try { _ws.onclose = null; _ws.onerror = null; _ws.close(); } catch(e) {}
                    _ws = null;
                    _tryNextHost(hosts, wsPort);
                }
            }, 2000);

            _ws.onopen = function() {
                clearTimeout(connectTimeout);
                _connected = true;
                _currentHost = host;
                var label = (host === 'localhost' || host === '127.0.0.1') ? 'محلي' : 'سيرفر';
                _log('✅ متصل بـ Print Agent (' + label + ': ' + host + ')');
                _updateStatusUI('متصل ✓ (' + label + ')', 'success');
                _startKeepalive();
                if (_reconnectTimer) {
                    clearTimeout(_reconnectTimer);
                    _reconnectTimer = null;
                }
            };

            _ws.onmessage = function(event) {
                try {
                    var data = JSON.parse(event.data);

                    if (data.type === 'connected') {
                        _printers = data.printers || {};
                        _defaultPrinter = data.default_printer || null;
                        var total = (_printers.all || []).length;
                        _log('🖨️ تم اكتشاف ' + total + ' طابعة');
                        document.dispatchEvent(new CustomEvent('printAgentConnected', {detail: _printers}));
                        return;
                    }

                    var reqId = data.request_id;
                    if (reqId && _pendingRequests[reqId]) {
                        _pendingRequests[reqId].resolve(data);
                        delete _pendingRequests[reqId];
                    }
                } catch (e) {
                    console.warn('Print Agent: parse error', e);
                }
            };

            _ws.onclose = function() {
                clearTimeout(connectTimeout);
                _stopKeepalive();
                if (_connected) {
                    // Was connected, now disconnected - reconnect to same host first
                    _connected = false;
                    _updateStatusUI('غير متصل ✗', 'danger');
                    _log('✗ انقطع الاتصال بـ ' + host + ' - إعادة المحاولة...');
                    _reconnectTimer = setTimeout(function() {
                        _connectAttempt = 0;
                        _tryNextHost(hosts, wsPort);
                    }, _reconnectInterval);
                }
                // If not yet connected, connectTimeout will handle trying next host
            };

            _ws.onerror = function() {
                // Silently handled by onclose/timeout
            };

        } catch (e) {
            _tryNextHost(hosts, wsPort);
        }
    }

    function _connectToHost(host, wsPort) {
        // Direct connection to a specific host
        _currentHost = host;
        try {
            if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) {
                return;
            }
            var wsUrl = 'ws://' + host + ':' + wsPort;
            _log('الاتصال بـ ' + host + ':' + wsPort);
            _ws = new WebSocket(wsUrl);

            _ws.onopen = function() {
                _connected = true;
                _log('✅ متصل');
                _updateStatusUI('متصل ✓', 'success');
                _startKeepalive();
            };
            _ws.onmessage = function(event) {
                try {
                    var data = JSON.parse(event.data);
                    if (data.type === 'connected') {
                        _printers = data.printers || {};
                        _defaultPrinter = data.default_printer || null;
                        document.dispatchEvent(new CustomEvent('printAgentConnected', {detail: _printers}));
                        return;
                    }
                    var reqId = data.request_id;
                    if (reqId && _pendingRequests[reqId]) {
                        _pendingRequests[reqId].resolve(data);
                        delete _pendingRequests[reqId];
                    }
                } catch(e) {}
            };
            _ws.onclose = function() {
                _connected = false;
                _stopKeepalive();
                _updateStatusUI('غير متصل ✗', 'danger');
                _reconnectTimer = setTimeout(function() { _connectToHost(host, wsPort); }, _reconnectInterval);
            };
            _ws.onerror = function() {};
        } catch(e) {}
    }

    function disconnect() {
        _stopKeepalive();
        if (_reconnectTimer) {
            clearTimeout(_reconnectTimer);
            _reconnectTimer = null;
        }
        if (_ws) {
            _ws.close();
            _ws = null;
        }
        _connected = false;
    }

    function _send(data) {
        return new Promise(function(resolve, reject) {
            if (!_connected || !_ws || _ws.readyState !== WebSocket.OPEN) {
                reject(new Error('غير متصل بـ Print Agent. تأكد من تشغيل البرنامج على جهازك.'));
                return;
            }

            _requestId++;
            var reqId = 'req_' + _requestId;
            data.request_id = reqId;

            _pendingRequests[reqId] = {resolve: resolve};
            _ws.send(JSON.stringify(data));

            // Timeout 30 ثانية
            setTimeout(function() {
                if (_pendingRequests[reqId]) {
                    _pendingRequests[reqId].resolve({success: false, error: 'انتهت مهلة الانتظار (30 ثانية)'});
                    delete _pendingRequests[reqId];
                }
            }, 30000);
        });
    }

    // ═══════════════════════════════════════════
    // UI Status
    // ═══════════════════════════════════════════

    function _updateStatusUI(text, type) {
        var el = document.getElementById('print-agent-status');
        if (el) {
            el.textContent = text;
            el.className = 'badge bg-' + type;
        }
    }

    function _showToast(message, type) {
        type = type || 'info';
        // SweetAlert2
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                toast: true,
                position: 'top-end',
                icon: type === 'success' ? 'success' : (type === 'danger' ? 'error' : 'info'),
                title: message,
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
        }
        // Bootstrap Toast fallback
        else if (typeof bootstrap !== 'undefined') {
            var container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.className = 'position-fixed top-0 end-0 p-3';
                container.style.zIndex = '99999';
                document.body.appendChild(container);
            }
            var id = 'toast-' + Date.now();
            var bgClass = type === 'success' ? 'bg-success' : (type === 'danger' ? 'bg-danger' : 'bg-info');
            container.insertAdjacentHTML('beforeend',
                '<div id="' + id + '" class="toast ' + bgClass + ' text-white" role="alert">' +
                '<div class="toast-body">' + message + '</div></div>'
            );
            var toastEl = document.getElementById(id);
            var toast = new bootstrap.Toast(toastEl, {delay: 3000});
            toast.show();
            toastEl.addEventListener('hidden.bs.toast', function() { toastEl.remove(); });
        }
        else {
            console.log('[Print] ' + message);
        }
    }

    // ═══════════════════════════════════════════
    // 1. Zebra (Barcode Labels)
    // ═══════════════════════════════════════════

    /**
     * طباعة ملصق باركود على Zebra مع تحديد المقاس
     * @param {Object} options
     * @param {string} options.barcode - رقم الباركود (مطلوب)
     * @param {string} [options.product_name] - اسم المنتج
     * @param {string} [options.price] - السعر
     * @param {string} [options.size_text] - نص المقاس
     * @param {number} [options.label_width_mm=50] - عرض الملصق بالمم
     * @param {number} [options.label_height_mm=30] - ارتفاع الملصق بالمم
     * @param {number} [options.dpi=203] - دقة الطابعة
     * @param {number} [options.copies=1] - عدد النسخ
     * @param {string} [options.printer_name] - اسم الطابعة (اختياري)
     * @param {string} [options.ip] - عنوان IP (للطباعة عبر الشبكة)
     * @param {number} [options.port=9100] - منفذ الشبكة
     */
    async function printBarcodeLabel(options) {
        options = options || {};
        var data = {
            action: 'print_zebra_label',
            barcode: options.barcode || '',
            product_name: options.product_name || '',
            price: options.price || '',
            size_text: options.size_text || '',
            label_width_mm: options.label_width_mm || 50,
            label_height_mm: options.label_height_mm || 30,
            dpi: options.dpi || 203,
            copies: options.copies || 1,
            manufacture_date: options.manufacture_date || '',
            expiry_date: options.expiry_date || '',
            printer_name: options.printer_name || '',
            ip: options.ip || '',
            port: options.port || 9100
        };

        try {
            var result = await _send(data);
            if (result.success) {
                _showToast('✅ تم طباعة الملصق (' + (result.label_size || '') + ')', 'success');
            } else {
                _showToast('❌ ' + (result.error || 'فشل الطباعة'), 'danger');
            }
            return result;
        } catch (e) {
            _showToast('❌ ' + e.message, 'danger');
            return {success: false, error: e.message};
        }
    }

    /**
     * إرسال أوامر ZPL مباشرة
     */
    async function printZPL(zplCommands, printerName, ip, port) {
        return _send({
            action: 'print_zebra_zpl',
            zpl: zplCommands,
            printer_name: printerName || '',
            ip: ip || '',
            port: port || 9100
        });
    }

    // ═══════════════════════════════════════════
    // 2. XPrinter (Thermal Receipts)
    // ═══════════════════════════════════════════

    /**
     * طباعة إيصال نصي على XPrinter
     */
    async function printReceipt(content, options) {
        options = options || {};
        try {
            var result = await _send({
                action: 'print_thermal_receipt',
                content: content,
                printer_name: options.printer_name || '',
                open_drawer: options.open_drawer || false,
                cut_paper: options.cut_paper !== false
            });
            if (result.success) {
                _showToast('✅ تم طباعة الإيصال', 'success');
            } else {
                _showToast('❌ ' + (result.error || 'فشل الطباعة'), 'danger');
            }
            return result;
        } catch (e) {
            _showToast('❌ ' + e.message, 'danger');
            return {success: false, error: e.message};
        }
    }

    /**
     * طباعة إيصال HTML على XPrinter
     */
    async function printReceiptHTML(html, options) {
        options = options || {};
        return _send({
            action: 'print_thermal_receipt',
            html: html,
            printer_name: options.printer_name || '',
            open_drawer: options.open_drawer || false,
            cut_paper: options.cut_paper !== false
        });
    }

    /**
     * طباعة بيانات ESC/POS خام (base64) من السيرفر
     */
    async function printReceiptRaw(base64Data, options) {
        options = options || {};
        try {
            var result = await _send({
                action: 'print_thermal_receipt',
                raw_base64: base64Data,
                printer_name: options.printer_name || '',
                open_drawer: options.open_drawer || false,
                cut_paper: options.cut_paper !== false
            });
            if (result.success) {
                _showToast('✅ تم طباعة الإيصال', 'success');
            }
            return result;
        } catch (e) {
            return {success: false, error: e.message};
        }
    }

    /**
     * طباعة صورة (base64 PNG) على XPrinter - مثل الإيصالات العربية
     */
    async function printReceiptImage(imageBase64, options) {
        options = options || {};
        return _send({
            action: 'print_thermal_image',
            image_base64: imageBase64,
            printer_name: options.printer_name || '',
            width: options.width || 384
        });
    }

    /**
     * طلب بيانات الإيصال من السيرفر ثم طباعتها مباشرة
     * هذه هي الطريقة الموصى بها لطباعة الإيصالات من POS
     */
    async function printOrderReceipt(orderId, options) {
        options = options || {};
        try {
            // جلب بيانات الإيصال من السيرفر
            _log('جاري جلب بيانات الإيصال #' + orderId + '...');
            var response = await fetch('/pos/api/receipt-data/' + orderId + '/');
            
            if (!response.ok) {
                var errMsg = 'خطأ من السيرفر: HTTP ' + response.status;
                _showToast('❌ ' + errMsg, 'danger');
                return {success: false, error: errMsg};
            }
            
            var serverData;
            try {
                serverData = await response.json();
            } catch (jsonErr) {
                var errMsg2 = 'رد السيرفر ليس JSON صالح';
                _showToast('❌ ' + errMsg2, 'danger');
                return {success: false, error: errMsg2};
            }

            if (!serverData.success) {
                var errMsg3 = serverData.error || 'فشل توليد بيانات الإيصال';
                _showToast('❌ ' + errMsg3, 'danger');
                return {success: false, error: errMsg3};
            }

            if (!serverData.data) {
                _showToast('❌ لم يتم إرجاع بيانات الطباعة من السيرفر', 'danger');
                return {success: false, error: 'لم يتم إرجاع بيانات الطباعة'};
            }

            // إرسال للطابعة المحلية
            _log('جاري إرسال البيانات للطابعة...');
            var result = await printReceiptRaw(serverData.data, {
                open_drawer: options.open_drawer !== false,
                cut_paper: true
            });
            
            if (result.success) {
                _log('✅ تمت طباعة الإيصال #' + orderId);
            } else {
                _log('❌ فشلت طباعة الإيصال: ' + (result.error || 'خطأ غير معروف'));
            }
            return result;
        } catch (e) {
            var errMsg4 = e.message || 'خطأ غير معروف';
            _showToast('❌ ' + errMsg4, 'danger');
            _log('❌ خطأ: ' + errMsg4);
            return {success: false, error: errMsg4};
        }
    }

    // ═══════════════════════════════════════════
    // 3. A4 (Invoices & Reports)
    // ═══════════════════════════════════════════

    /**
     * طباعة PDF (base64) على طابعة A4
     */
    async function printPDF(pdfBase64, options) {
        options = options || {};
        try {
            var result = await _send({
                action: 'print_a4',
                pdf_base64: pdfBase64,
                printer_name: options.printer_name || '',
                copies: options.copies || 1
            });
            if (result.success) {
                _showToast('✅ تم طباعة المستند', 'success');
            } else {
                _showToast('❌ ' + (result.error || 'فشل الطباعة'), 'danger');
            }
            return result;
        } catch (e) {
            _showToast('❌ ' + e.message, 'danger');
            return {success: false, error: e.message};
        }
    }

    /**
     * طباعة PDF من رابط على طابعة A4
     */
    async function printPDFUrl(url, options) {
        options = options || {};
        try {
            var result = await _send({
                action: 'print_a4',
                pdf_url: url,
                printer_name: options.printer_name || '',
                copies: options.copies || 1
            });
            if (result.success) {
                _showToast('✅ تم إرسال المستند للطباعة', 'success');
            } else {
                _showToast('❌ ' + (result.error || 'فشل الطباعة'), 'danger');
            }
            return result;
        } catch (e) {
            _showToast('❌ ' + e.message, 'danger');
            return {success: false, error: e.message};
        }
    }

    /**
     * طباعة HTML على A4
     */
    async function printA4HTML(html, options) {
        options = options || {};
        return _send({
            action: 'print_a4',
            html: html,
            printer_name: options.printer_name || '',
            copies: options.copies || 1
        });
    }

    // ═══════════════════════════════════════════
    // Utilities
    // ═══════════════════════════════════════════

    /** قائمة الطابعات */
    async function getPrinters() {
        try {
            return await _send({action: 'get_printers'});
        } catch (e) {
            return {success: false, error: e.message, printers: {}};
        }
    }

    /** طباعة اختبارية */
    async function testPrint(printerType) {
        try {
            var result = await _send({action: 'test_print', printer_type: printerType || 'all'});
            _showToast('🧪 تم إرسال الاختبار', 'info');
            return result;
        } catch (e) {
            _showToast('❌ ' + e.message, 'danger');
            return {success: false, error: e.message};
        }
    }

    /** هل المتصفح متصل بالـ Agent? */
    function isConnected() {
        return _connected;
    }

    /** الطابعات المكتشفة */
    function getCachedPrinters() {
        return _printers;
    }

    // اتصال تلقائي عند تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() { connect(); });
    } else {
        // Small delay to let page render first
        setTimeout(function() { connect(); }, 500);
    }

    // Public API
    return {
        connect: connect,
        disconnect: disconnect,
        isConnected: isConnected,
        getPrinters: getPrinters,
        getCachedPrinters: getCachedPrinters,
        testPrint: testPrint,

        // Zebra
        printBarcodeLabel: printBarcodeLabel,
        printZPL: printZPL,

        // XPrinter (Thermal)
        printReceipt: printReceipt,
        printReceiptHTML: printReceiptHTML,
        printReceiptRaw: printReceiptRaw,
        printReceiptImage: printReceiptImage,
        printOrderReceipt: printOrderReceipt,

        // A4
        printPDF: printPDF,
        printPDFUrl: printPDFUrl,
        printA4HTML: printA4HTML
    };
})();

// Alias for backward compatibility
window.TonyPrintAgent = TonyPrint;
