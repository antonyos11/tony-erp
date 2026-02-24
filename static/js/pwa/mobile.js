/**
 * PWA Mobile JavaScript - Tony ERP
 * يدير وظائف الجوال والـ Progressive Web App
 */
(function () {
    'use strict';

    const PWAManager = {

        init() {
            this.registerServiceWorker();
            this.setupInstallPrompt();
            this.setupOfflineDetection();
            this.setupMobileOptimizations();
        },

        async registerServiceWorker() {
            if (!('serviceWorker' in navigator)) return;
            try {
                const reg = await navigator.serviceWorker.register(
                    '/static/js/pwa/service-worker.js', { scope: '/' }
                );
                reg.addEventListener('updatefound', () => {
                    const worker = reg.installing;
                    worker.addEventListener('statechange', () => {
                        if (worker.state === 'installed' && navigator.serviceWorker.controller) {
                            this.showUpdateBanner();
                        }
                    });
                });
            } catch (e) {
                console.warn('Service Worker registration failed:', e);
            }
        },

        setupInstallPrompt() {
            let deferredPrompt = null;
            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                deferredPrompt = e;
                const btn = document.getElementById('pwa-install-btn');
                if (btn) {
                    btn.style.display = 'inline-flex';
                    btn.addEventListener('click', async () => {
                        deferredPrompt.prompt();
                        await deferredPrompt.userChoice;
                        btn.style.display = 'none';
                        deferredPrompt = null;
                    });
                }
            });
        },

        setupOfflineDetection() {
            const update = () => {
                document.body.classList.toggle('is-offline', !navigator.onLine);
                const banner = document.getElementById('offline-banner');
                if (banner) banner.style.display = navigator.onLine ? 'none' : 'block';
            };
            window.addEventListener('online', update);
            window.addEventListener('offline', update);
            update();
        },

        showUpdateBanner() {
            const banner = document.createElement('div');
            banner.className = 'alert alert-info d-flex align-items-center justify-content-between';
            banner.style.cssText = 'position:sticky;top:0;z-index:9999;margin:0;border-radius:0;';
            banner.innerHTML = `
                <span>🔄 يوجد تحديث جديد للتطبيق</span>
                <button class="btn btn-sm btn-primary" onclick="window.location.reload()">تحديث الآن</button>
            `;
            document.body.prepend(banner);
        },

        setupMobileOptimizations() {
            // منع تكبير iOS عند التركيز على input
            if (/iPhone|iPad|iPod/i.test(navigator.userAgent)) {
                document.querySelectorAll('input, select, textarea').forEach(el => {
                    if (parseFloat(getComputedStyle(el).fontSize) < 16) {
                        el.style.fontSize = '16px';
                    }
                });
            }
            if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
                document.body.classList.add('mobile-device');
            }
        }
    };

    document.addEventListener('DOMContentLoaded', () => PWAManager.init());
    window.PWAManager = PWAManager;
})();
