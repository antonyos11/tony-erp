/**
 * Tony ERP - Unified Print Status Manager v3.2
 *
 * Bridges the TonyPrint WebSocket client (tony_print_agent.js) to ALL
 * status badges across every page: POS payment modal, Settings, Production,
 * Navbar heartbeat, etc.
 *
 * The ONLY source of truth is TonyPrint.isConnected() — i.e. can the
 * browser reach ws://127.0.0.1:9876 (local agent on the user's machine).
 *
 * This script does NOT duplicate the WebSocket connection — it piggybacks
 * on TonyPrint's existing connection and events.
 */
;(function(window, document) {
    'use strict';

    // ════════════════════════════════════════════════════
    // Configuration
    // ════════════════════════════════════════════════════

    var POLL_FAST_INTERVAL = 2000;    // 2s during first 20s
    var POLL_FAST_COUNT    = 10;      // 10 fast polls = 20s
    var POLL_NORMAL_INTERVAL = 6000;  // 6s afterwards
    var _fastCount = 0;
    var _fastTimer = null;
    var _normalTimer = null;
    var _lastState = null;

    // ════════════════════════════════════════════════════
    // Core: Check Connection State
    // ════════════════════════════════════════════════════

    function getState() {
        if (typeof TonyPrint === 'undefined') return 'offline';
        return TonyPrint.isConnected() ? 'online' : 'offline';
    }

    function getPrinters() {
        if (typeof TonyPrint === 'undefined') return {};
        return TonyPrint.getCachedPrinters() || {};
    }

    function getTotalPrinterCount() {
        var p = getPrinters();
        return (p.all || []).length;
    }

    // ════════════════════════════════════════════════════
    // UI Updates — updates EVERY status element on the page
    // ════════════════════════════════════════════════════

    function updateAllUI(state) {
        if (state === _lastState) return; // Skip if no change
        _lastState = state;

        var isOnline = (state === 'online');
        var count = getTotalPrinterCount();
        var printers = getPrinters();

        // ── 1. Navbar heartbeat element ──
        _updateNavbar(isOnline, count);

        // ── 2. POS payment modal elements ──
        _updatePOSModal(isOnline, count);

        // ── 3. Settings page elements ──
        _updateSettingsPage(isOnline, count, printers);

        // ── 4. Any element with data-print-status attribute ──
        _updateDataAttributes(isOnline, count);

        // ── 5. Production / packaging badges ──
        _updateGenericBadges(isOnline, count);

        // ── 6. Fire event for custom listeners ──
        _fireEvent(isOnline, count, printers);
    }

    // ── Navbar Heartbeat ──
    function _updateNavbar(isOnline, count) {
        var heartbeat = document.getElementById('print-agent-heartbeat');
        if (!heartbeat) return;

        var dot = heartbeat.querySelector('.pah-dot');
        var text = heartbeat.querySelector('.pah-text');

        if (isOnline) {
            heartbeat.className = 'print-heartbeat online';
            if (dot) dot.style.background = '#28a745';
            if (text) text.textContent = '🖨️ متصل' + (count ? ' (' + count + ')' : '');
        } else {
            heartbeat.className = 'print-heartbeat offline';
            if (dot) dot.style.background = '#dc3545';
            if (text) text.textContent = '🖨️ غير متصل';
        }
    }

    // ── POS Payment Modal ──
    function _updatePOSModal(isOnline, count) {
        var statusEl = document.getElementById('printerStatus');
        var card = document.getElementById('xprinterCard');
        var checkbox = document.getElementById('autoPrintXPrinter');

        if (statusEl) {
            if (isOnline) {
                statusEl.innerHTML = '🟢 متصل' + (count ? ' (' + count + ' طابعة)' : '');
                statusEl.className = 'badge bg-light text-success';
            } else {
                statusEl.innerHTML = '🔴 غير متصل';
                statusEl.className = 'badge bg-light text-danger';
            }
        }

        if (card) {
            card.className = isOnline
                ? 'card bg-success text-white'
                : 'card bg-secondary text-white';
        }

        // Don't disable the checkbox — user might want to leave it checked for when agent comes back
    }

    // ── Settings Page ──
    function _updateSettingsPage(isOnline, count, printers) {
        // Agent status dot
        var dot = document.getElementById('settings-agent-dot');
        var text = document.getElementById('settings-agent-text');

        if (dot) dot.style.background = isOnline ? '#28a745' : '#dc3545';
        if (text) {
            text.textContent = isOnline ? '● متصل' : '● غير متصل';
            text.style.color = isOnline ? '#28a745' : '#dc3545';
        }

        // Agent info card
        var infoCard = document.getElementById('agent-info-card');
        if (infoCard) {
            infoCard.style.display = isOnline ? 'block' : 'none';
        }

        // Update discovered printers list
        var discoveredList = document.getElementById('discovered-printers-list');
        if (discoveredList && isOnline) {
            var allPrinters = printers.all || [];
            if (allPrinters.length === 0) {
                discoveredList.innerHTML = '<p class="text-warning">لم يتم اكتشاف أي طابعات.</p>';
            } else {
                var html = '<div class="row g-2">';
                for (var i = 0; i < allPrinters.length; i++) {
                    var p = allPrinters[i];
                    var icon = {zebra: '🏷️', thermal: '🧾', a4: '📄'}[p.type] || '🖨️';
                    var color = {zebra: 'warning', thermal: 'success', a4: 'primary'}[p.type] || 'secondary';
                    var def = p.is_default ? ' <span class="badge bg-info">Default</span>' : '';
                    html += '<div class="col-md-4 col-lg-3"><div class="card h-100"><div class="card-body py-2">'
                        + '<div class="d-flex align-items-center gap-2">'
                        + '<span style="font-size:1.3rem;">' + icon + '</span>'
                        + '<div><strong style="font-size:0.85rem;">' + p.name + '</strong><br>'
                        + '<span class="badge bg-' + color + '" style="font-size:0.65rem;">' + (p.type || '').toUpperCase() + '</span>'
                        + def + '</div></div></div></div></div>';
                }
                html += '</div>';
                discoveredList.innerHTML = html;
            }
        }

        // Update configured printer live statuses
        var liveBadges = document.querySelectorAll('.printer-live-status');
        if (liveBadges.length) {
            var agentNames = (printers.all || []).map(function(p) { return p.name.toLowerCase(); });
            for (var j = 0; j < liveBadges.length; j++) {
                var badge = liveBadges[j];
                var configName = (badge.getAttribute('data-printer-name') || '').toLowerCase();
                if (!isOnline) {
                    badge.className = 'badge bg-secondary printer-live-status';
                    badge.textContent = '❓ الوكيل غير متصل';
                    continue;
                }
                var found = false;
                for (var k = 0; k < agentNames.length; k++) {
                    if (agentNames[k].indexOf(configName) !== -1 || configName.indexOf(agentNames[k]) !== -1) {
                        found = true;
                        break;
                    }
                }
                badge.className = 'badge ' + (found ? 'bg-success' : 'bg-danger') + ' printer-live-status';
                badge.textContent = found ? '● متصلة' : '● غير موجودة';
            }
        }
    }

    // ── Data Attributes ──
    function _updateDataAttributes(isOnline, count) {
        var els = document.querySelectorAll('[data-print-status]');
        for (var i = 0; i < els.length; i++) {
            els[i].setAttribute('data-print-status', isOnline ? 'online' : 'offline');
        }

        els = document.querySelectorAll('[data-connection-status]');
        for (var i = 0; i < els.length; i++) {
            var el = els[i];
            el.setAttribute('data-connection-status', isOnline ? 'online' : 'offline');
            // Also update visible text
            el.classList.remove('bg-success', 'bg-danger', 'bg-secondary', 'text-success', 'text-danger');
            if (isOnline) {
                el.classList.add('bg-success');
                el.textContent = '● متصل' + (count ? ' (' + count + ')' : '');
                el.style.color = '#fff';
            } else {
                el.classList.add('bg-danger');
                el.textContent = '● غير متصل';
                el.style.color = '#fff';
            }
        }
    }

    // ── Generic Badges ──
    function _updateGenericBadges(isOnline, count) {
        var selectors = [
            '.print-status-badge',
            '.xprinter-status-badge',
            '.printer-connection-badge',
        ];
        var els = document.querySelectorAll(selectors.join(','));
        for (var i = 0; i < els.length; i++) {
            var el = els[i];
            el.classList.remove('bg-success', 'bg-danger', 'bg-secondary');
            if (isOnline) {
                el.classList.add('bg-success');
                el.textContent = '● متصل';
            } else {
                el.classList.add('bg-danger');
                el.textContent = '● غير متصل';
            }
        }
    }

    // ── Custom Event ──
    function _fireEvent(isOnline, count, printers) {
        try {
            document.dispatchEvent(new CustomEvent('printStatusChanged', {
                detail: {
                    connected: isOnline,
                    printerCount: count,
                    printers: printers,
                }
            }));
        } catch(e) {}
    }

    // ════════════════════════════════════════════════════
    // Polling Logic
    // ════════════════════════════════════════════════════

    function poll() {
        updateAllUI(getState());
    }

    function startPolling() {
        // Fast polling for first 20 seconds (agent may still be connecting)
        _fastTimer = setInterval(function() {
            poll();
            _fastCount++;
            if (_fastCount >= POLL_FAST_COUNT) {
                clearInterval(_fastTimer);
                _fastTimer = null;
                // Switch to normal polling
                _normalTimer = setInterval(poll, POLL_NORMAL_INTERVAL);
            }
        }, POLL_FAST_INTERVAL);
    }

    // ════════════════════════════════════════════════════
    // Event Listeners
    // ════════════════════════════════════════════════════

    function init() {
        // Initial check
        poll();

        // Start polling
        startPolling();

        // Listen for TonyPrint connection event (fires when agent sends 'connected' message)
        document.addEventListener('printAgentConnected', function() {
            _lastState = null; // Force UI update
            poll();
        });

        // Listen for modal open - recheck immediately
        var paymentModal = document.getElementById('paymentModal');
        if (paymentModal) {
            paymentModal.addEventListener('show.bs.modal', function() {
                _lastState = null; // Force UI update
                poll();
                // If not connected, try to reconnect TonyPrint
                if (typeof TonyPrint !== 'undefined' && !TonyPrint.isConnected()) {
                    TonyPrint.connect();
                }
            });
        }

        // MutationObserver for dynamically inserted elements (modals, HTMX, etc.)
        if (window.MutationObserver) {
            var observer = new MutationObserver(function(mutations) {
                var shouldUpdate = false;
                for (var i = 0; i < mutations.length; i++) {
                    var nodes = mutations[i].addedNodes;
                    for (var j = 0; j < nodes.length; j++) {
                        var n = nodes[j];
                        if (n.nodeType !== 1) continue;
                        if (n.id === 'paymentModal' || n.id === 'printerStatus' ||
                            n.id === 'xprinterCard' || n.id === 'print-agent-heartbeat' ||
                            (n.querySelector && n.querySelector(
                                '#printerStatus, #xprinterCard, [data-print-status], [data-connection-status], .printer-live-status'
                            ))) {
                            shouldUpdate = true;
                            break;
                        }
                    }
                    if (shouldUpdate) break;
                }
                if (shouldUpdate) {
                    _lastState = null;
                    poll();
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    }

    // ════════════════════════════════════════════════════
    // Public API — window.PrintStatus
    // ════════════════════════════════════════════════════

    window.PrintStatus = {
        /** Is the local agent connected? */
        get connected() { return getState() === 'online'; },

        /** Get discovered printers */
        get printers() { return getPrinters(); },

        /** Force a status refresh */
        refresh: function() {
            _lastState = null;
            poll();
        },

        /** Force TonyPrint reconnect */
        reconnect: function() {
            if (typeof TonyPrint !== 'undefined') {
                TonyPrint.connect();
            }
            setTimeout(function() {
                _lastState = null;
                poll();
            }, 3000);
        },

        /** Send test print (delegates to TonyPrint) */
        testPrint: function(printerType) {
            if (typeof TonyPrint !== 'undefined' && TonyPrint.isConnected()) {
                return TonyPrint.testPrint(printerType);
            }
            return Promise.reject(new Error('Agent not connected'));
        },

        /** Get full status */
        getStatus: function() {
            return {
                connected: getState() === 'online',
                printers: getPrinters(),
                printerCount: getTotalPrinterCount(),
            };
        },
    };

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // Small delay to let TonyPrint initialize first (it has 500ms delay)
        setTimeout(init, 800);
    }

})(window, document);
