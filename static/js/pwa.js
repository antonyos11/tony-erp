// PWA Installation and Management
class PWAManager {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.isOnline = navigator.onLine;
        
        this.init();
    }
    
    init() {
        // تسجيل Service Worker
        this.registerServiceWorker();
        
        // مراقبة حالة الاتصال
        this.setupNetworkListeners();
        
        // مراقبة حدث التثبيت
        this.setupInstallPrompt();
        
        // التحقق من التثبيت
        this.checkIfInstalled();
        
        // تهيئة الإشعارات
        this.setupNotifications();
    }
    
    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/static/sw.js', {
                    scope: '/'
                });
                
                console.log('ServiceWorker registered:', registration.scope);
                
                // التحقق من التحديثات
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            this.showUpdateNotification();
                        }
                    });
                });
                
            } catch (error) {
                console.error('ServiceWorker registration failed:', error);
            }
        }
    }
    
    setupNetworkListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.showToast('تم استعادة الاتصال بالإنترنت', 'success');
            this.syncPendingData();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showToast('أنت غير متصل بالإنترنت. بعض الميزات قد لا تعمل.', 'warning');
        });
    }
    
    setupInstallPrompt() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallButton();
        });
        
        window.addEventListener('appinstalled', () => {
            this.isInstalled = true;
            this.hideInstallButton();
            this.showToast('تم تثبيت التطبيق بنجاح!', 'success');
        });
    }
    
    checkIfInstalled() {
        if (window.matchMedia('(display-mode: standalone)').matches) {
            this.isInstalled = true;
        }
        
        if (window.navigator.standalone === true) {
            this.isInstalled = true;
        }
    }
    
    async installApp() {
        if (!this.deferredPrompt) {
            console.log('Install prompt not available');
            return false;
        }
        
        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;
        
        console.log('User response:', outcome);
        this.deferredPrompt = null;
        
        return outcome === 'accepted';
    }
    
    showInstallButton() {
        const btn = document.getElementById('installAppBtn');
        if (btn) {
            btn.style.display = 'block';
            btn.addEventListener('click', () => this.installApp());
        }
        
        // إظهار بانر التثبيت
        this.showInstallBanner();
    }
    
    hideInstallButton() {
        const btn = document.getElementById('installAppBtn');
        if (btn) {
            btn.style.display = 'none';
        }
        
        const banner = document.getElementById('installBanner');
        if (banner) {
            banner.remove();
        }
    }
    
    showInstallBanner() {
        // التحقق من عدم عرض البانر مسبقاً
        if (localStorage.getItem('installBannerDismissed')) {
            return;
        }
        
        const banner = document.createElement('div');
        banner.id = 'installBanner';
        banner.className = 'install-banner';
        banner.innerHTML = `
            <div class="install-banner-content">
                <img src="/static/icons/icon-72x72.png" alt="App Icon" class="install-banner-icon">
                <div class="install-banner-text">
                    <strong>تثبيت Tony ERP</strong>
                    <p>أضف التطبيق إلى شاشتك الرئيسية للوصول السريع</p>
                </div>
                <button class="btn btn-primary btn-sm install-btn">تثبيت</button>
                <button class="btn-close dismiss-btn" aria-label="إغلاق"></button>
            </div>
        `;
        
        document.body.appendChild(banner);
        
        banner.querySelector('.install-btn').addEventListener('click', () => {
            this.installApp();
        });
        
        banner.querySelector('.dismiss-btn').addEventListener('click', () => {
            banner.remove();
            localStorage.setItem('installBannerDismissed', 'true');
        });
    }
    
    showUpdateNotification() {
        const toast = this.showToast(
            'يتوفر تحديث جديد. هل تريد التحديث الآن؟',
            'info',
            0  // لا يختفي تلقائياً
        );
        
        const updateBtn = document.createElement('button');
        updateBtn.className = 'btn btn-sm btn-primary ms-2';
        updateBtn.textContent = 'تحديث';
        updateBtn.onclick = () => {
            this.applyUpdate();
        };
        
        toast.querySelector('.toast-body').appendChild(updateBtn);
    }
    
    applyUpdate() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then((registration) => {
                if (registration.waiting) {
                    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                }
            });
            
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                window.location.reload();
            });
        }
    }
    
    async setupNotifications() {
        if (!('Notification' in window)) {
            console.log('Notifications not supported');
            return;
        }
        
        if (Notification.permission === 'default') {
            // سنطلب الإذن لاحقاً عند الحاجة
        }
    }
    
    async requestNotificationPermission() {
        if (!('Notification' in window)) {
            return false;
        }
        
        const permission = await Notification.requestPermission();
        return permission === 'granted';
    }
    
    async subscribeToPushNotifications() {
        try {
            const registration = await navigator.serviceWorker.ready;
            
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
            });
            
            // إرسال الاشتراك إلى الخادم
            await fetch('/api/push/subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(subscription)
            });
            
            return true;
        } catch (error) {
            console.error('Push subscription failed:', error);
            return false;
        }
    }
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
    
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    async syncPendingData() {
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('sync-pending-data');
        }
    }
    
    showToast(message, type = 'info', duration = 5000) {
        const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast show bg-${type === 'success' ? 'success' : type === 'warning' ? 'warning' : type === 'error' ? 'danger' : 'info'} text-white`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="toast-body d-flex align-items-center">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close btn-close-white ms-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        toast.querySelector('.btn-close').addEventListener('click', () => toast.remove());
        
        if (duration > 0) {
            setTimeout(() => toast.remove(), duration);
        }
        
        return toast;
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }
}

// CSS للبانر
const style = document.createElement('style');
style.textContent = `
    .install-banner {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        z-index: 9999;
        animation: slideUp 0.3s ease;
    }
    
    @keyframes slideUp {
        from { transform: translateY(100%); }
        to { transform: translateY(0); }
    }
    
    .install-banner-content {
        display: flex;
        align-items: center;
        gap: 1rem;
        max-width: 600px;
        margin: 0 auto;
    }
    
    .install-banner-icon {
        width: 48px;
        height: 48px;
        border-radius: 10px;
    }
    
    .install-banner-text {
        flex: 1;
    }
    
    .install-banner-text p {
        margin: 0;
        font-size: 0.875rem;
        opacity: 0.9;
    }
    
    .install-banner .dismiss-btn {
        filter: invert(1);
    }
`;
document.head.appendChild(style);

// تهيئة PWA
const pwaManager = new PWAManager();
window.pwaManager = pwaManager;
