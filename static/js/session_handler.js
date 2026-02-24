/**
 * Session Timeout Handler for Tony ERP
 * Handles JWT token expiration and session timeout with auto-redirect
 */

(function() {
    'use strict';

    // Configuration
    const SESSION_CHECK_INTERVAL = 60000; // Check every 60 seconds
    const SESSION_WARNING_TIME = 5 * 60 * 1000; // Warn 5 minutes before expiry
    const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000; // Refresh token 5 minutes before expiry

    // Session state
    let lastActivityTime = Date.now();
    let sessionWarningShown = false;
    let tokenRefreshTimer = null;

    /**
     * Initialize session handler
     */
    function initSessionHandler() {
        // Track user activity
        trackUserActivity();

        // Set up axios/fetch interceptors
        setupRequestInterceptors();

        // Start session monitoring
        startSessionMonitoring();

        console.log('[Session Handler] Initialized');
    }

    /**
     * Track user activity to reset idle timer
     */
    function trackUserActivity() {
        const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
        
        events.forEach(event => {
            document.addEventListener(event, function() {
                lastActivityTime = Date.now();
                sessionWarningShown = false;
            }, true);
        });
    }

    /**
     * Setup request interceptors for handling 401/403/440 responses
     */
    function setupRequestInterceptors() {
        // Intercept fetch requests
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            return originalFetch.apply(this, args)
                .then(response => {
                    handleResponseStatus(response.status, response.url);
                    return response;
                })
                .catch(error => {
                    console.error('[Session Handler] Fetch error:', error);
                    throw error;
                });
        };

        // Intercept XMLHttpRequest
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            this._url = url;
            return originalOpen.apply(this, [method, url, ...rest]);
        };

        XMLHttpRequest.prototype.send = function(...args) {
            this.addEventListener('load', function() {
                handleResponseStatus(this.status, this._url);
            });
            return originalSend.apply(this, args);
        };

        // Setup axios interceptor if axios is available
        if (window.axios) {
            window.axios.interceptors.response.use(
                response => {
                    return response;
                },
                error => {
                    if (error.response) {
                        handleResponseStatus(error.response.status, error.config.url);
                    }
                    return Promise.reject(error);
                }
            );
        }
    }

    /**
     * Handle HTTP response status codes
     */
    function handleResponseStatus(status, url) {
        // Ignore non-API requests
        if (!url || (!url.includes('/api/') && !url.includes('/dashboard/'))) {
            return;
        }

        if (status === 401) {
            // Unauthorized - JWT token expired or invalid
            handleSessionExpired('انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.');
        } else if (status === 403) {
            // Forbidden - Access denied
            handleAccessDenied();
        } else if (status === 440) {
            // Session timeout (custom status code)
            handleSessionExpired('انتهت مدة الجلسة بسبب عدم النشاط.');
        }
    }

    /**
     * Handle session expiration
     */
    function handleSessionExpired(message) {
        // Clear any stored tokens
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        sessionStorage.clear();

        // Show message to user
        showSessionMessage(message, 'warning');

        // Redirect to login after a short delay
        setTimeout(() => {
            const currentPath = window.location.pathname;
            const loginUrl = `/login/?timeout=expired&next=${encodeURIComponent(currentPath)}`;
            window.location.href = loginUrl;
        }, 2000);
    }

    /**
     * Handle access denied
     */
    function handleAccessDenied() {
        showSessionMessage('غير مصرح لك بالوصول إلى هذا المحتوى.', 'error');
    }

    /**
     * Show session message to user
     */
    function showSessionMessage(message, type = 'info') {
        // Check if there's a toast/notification system
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: type === 'error' ? 'error' : type === 'warning' ? 'warning' : 'info',
                title: type === 'error' ? 'خطأ' : type === 'warning' ? 'تحذير' : 'معلومة',
                text: message,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
        } else if (typeof toastr !== 'undefined') {
            toastr[type](message);
        } else {
            // Fallback to alert
            alert(message);
        }
    }

    /**
     * Monitor session and show warnings
     */
    function startSessionMonitoring() {
        setInterval(() => {
            const idleTime = Date.now() - lastActivityTime;
            const sessionTimeout = 30 * 60 * 1000; // 30 minutes (matching backend)

            // Show warning before session expires
            if (idleTime > (sessionTimeout - SESSION_WARNING_TIME) && !sessionWarningShown) {
                sessionWarningShown = true;
                showSessionWarning();
            }

            // Auto-logout if session expired
            if (idleTime > sessionTimeout) {
                handleSessionExpired('انتهت مدة الجلسة بسبب عدم النشاط.');
            }
        }, SESSION_CHECK_INTERVAL);
    }

    /**
     * Show session warning
     */
    function showSessionWarning() {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                title: 'تنبيه الجلسة',
                text: 'ستنتهي جلستك قريباً بسبب عدم النشاط. قم بأي إجراء للحفاظ على جلستك نشطة.',
                toast: true,
                position: 'top-end',
                showConfirmButton: true,
                confirmButtonText: 'فهمت',
                timer: 10000,
                timerProgressBar: true
            });
        }
    }

    /**
     * Refresh JWT token before expiry
     */
    function refreshToken() {
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (!refreshToken) {
            console.log('[Session Handler] No refresh token available');
            return;
        }

        fetch('/api/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken })
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Token refresh failed');
        })
        .then(data => {
            if (data.access) {
                localStorage.setItem('access_token', data.access);
                console.log('[Session Handler] Token refreshed successfully');
                
                // Schedule next refresh
                scheduleTokenRefresh();
            }
        })
        .catch(error => {
            console.error('[Session Handler] Token refresh error:', error);
            // Token refresh failed - probably expired
            handleSessionExpired('انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.');
        });
    }

    /**
     * Schedule automatic token refresh
     */
    function scheduleTokenRefresh() {
        // Clear existing timer
        if (tokenRefreshTimer) {
            clearTimeout(tokenRefreshTimer);
        }

        // JWT tokens expire in 60 minutes (from settings)
        // Refresh 5 minutes before expiry
        const refreshTime = (60 - 5) * 60 * 1000; // 55 minutes

        tokenRefreshTimer = setTimeout(() => {
            refreshToken();
        }, refreshTime);
    }

    /**
     * Check if JWT tokens are being used
     */
    function checkJWTUsage() {
        const accessToken = localStorage.getItem('access_token');
        if (accessToken) {
            console.log('[Session Handler] JWT mode detected');
            scheduleTokenRefresh();
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initSessionHandler();
            checkJWTUsage();
        });
    } else {
        initSessionHandler();
        checkJWTUsage();
    }

})();
