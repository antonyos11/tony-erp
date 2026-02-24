/**
 * Service Worker - الشامل ERP PWA
 * يوفر دعم العمل بدون اتصال وتحسين الأداء
 */

const CACHE_NAME = 'alshamel-erp-v1';
const OFFLINE_URL = '/offline/';

// الملفات الأساسية للتخزين المؤقت
const STATIC_CACHE = [
  '/',
  '/static/css/design_system.css',
  '/static/css/ui_v2.css',
  '/static/js/app_layout.js',
  '/static/js/theme.js',
  '/static/manifest.json',
  '/static/img/icons/icon-192x192.png',
  '/static/img/icons/icon-512x512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js'
];

// تثبيت Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_CACHE);
      })
      .catch((error) => {
        console.log('[SW] Cache failed:', error);
      })
  );
  // تفعيل فوري بدون انتظار
  self.skipWaiting();
});

// تفعيل Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('[SW] Clearing old cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
  // السيطرة على جميع الصفحات فوراً
  self.clients.claim();
});

// استراتيجية الشبكة أولاً مع التراجع للكاش
self.addEventListener('fetch', (event) => {
  const request = event.request;
  
  // تجاهل الطلبات غير GET
  if (request.method !== 'GET') {
    return;
  }
  
  // تجاهل طلبات API والـ admin
  if (request.url.includes('/api/') || request.url.includes('/admin/')) {
    return;
  }
  
  event.respondWith(
    // محاولة الشبكة أولاً
    fetch(request)
      .then((response) => {
        // حفظ نسخة في الكاش
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME)
            .then((cache) => {
              cache.put(request, responseClone);
            });
        }
        return response;
      })
      .catch(() => {
        // التراجع للكاش
        return caches.match(request)
          .then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // إذا كان HTML، عرض صفحة offline
            if (request.headers.get('accept').includes('text/html')) {
              return caches.match(OFFLINE_URL);
            }
          });
      })
  );
});

// استقبال الرسائل من الصفحة
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Push Notifications (للمستقبل)
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body || 'لديك إشعار جديد',
      icon: '/static/img/icons/icon-192x192.png',
      badge: '/static/img/icons/icon-72x72.png',
      vibrate: [100, 50, 100],
      data: {
        url: data.url || '/'
      },
      dir: 'rtl',
      lang: 'ar'
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title || 'الشامل ERP', options)
    );
  }
});

// النقر على الإشعار
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});
