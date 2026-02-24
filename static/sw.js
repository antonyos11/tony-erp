// Service Worker for Tony ERP PWA
const CACHE_NAME = 'tony-erp-v1.0.0';
const OFFLINE_URL = '/offline/';

// الملفات المراد تخزينها مسبقاً
const PRECACHE_ASSETS = [
    '/',
    '/offline/',
    '/static/css/main.css',
    '/static/js/main.js',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
];

// API endpoints للتخزين المؤقت
const API_CACHE_PATTERNS = [
    /\/api\/dashboard\//,
    /\/api\/notifications\//,
    /\/api\/quick-access\//,
];

// التثبيت
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Install');
    
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[ServiceWorker] Pre-caching assets');
            return cache.addAll(PRECACHE_ASSETS);
        })
    );
    
    self.skipWaiting();
});

// التفعيل
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activate');
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((cacheName) => cacheName !== CACHE_NAME)
                    .map((cacheName) => {
                        console.log('[ServiceWorker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    })
            );
        })
    );
    
    self.clients.claim();
});

// استراتيجيات التخزين المؤقت
const strategies = {
    // الشبكة أولاً مع النسخ الاحتياطي للكاش
    networkFirst: async (request) => {
        try {
            const networkResponse = await fetch(request);
            if (networkResponse.ok) {
                const cache = await caches.open(CACHE_NAME);
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        } catch (error) {
            const cachedResponse = await caches.match(request);
            return cachedResponse || caches.match(OFFLINE_URL);
        }
    },
    
    // الكاش أولاً مع تحديث الخلفية
    cacheFirst: async (request) => {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            // تحديث الكاش في الخلفية
            fetch(request).then((response) => {
                if (response.ok) {
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, response);
                    });
                }
            });
            return cachedResponse;
        }
        return fetch(request);
    },
    
    // الشبكة فقط
    networkOnly: async (request) => {
        return fetch(request);
    },
    
    // الكاش فقط
    cacheOnly: async (request) => {
        return caches.match(request);
    },
};

// معالجة الطلبات
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // تجاهل الطلبات غير HTTP
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    // الملفات الثابتة - كاش أولاً
    if (url.pathname.startsWith('/static/') || 
        url.pathname.startsWith('/media/') ||
        request.destination === 'style' ||
        request.destination === 'script' ||
        request.destination === 'image') {
        event.respondWith(strategies.cacheFirst(request));
        return;
    }
    
    // API - شبكة أولاً
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(strategies.networkFirst(request));
        return;
    }
    
    // الصفحات - شبكة أولاً
    if (request.mode === 'navigate') {
        event.respondWith(strategies.networkFirst(request));
        return;
    }
    
    // الباقي - شبكة أولاً
    event.respondWith(strategies.networkFirst(request));
});

// الإشعارات الدفعية
self.addEventListener('push', (event) => {
    console.log('[ServiceWorker] Push received');
    
    let data = { title: 'Tony ERP', body: 'لديك إشعار جديد' };
    
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    const options = {
        body: data.body,
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            url: data.url || '/',
            dateOfArrival: Date.now(),
        },
        actions: data.actions || [
            { action: 'open', title: 'فتح' },
            { action: 'close', title: 'إغلاق' },
        ],
        dir: 'rtl',
        lang: 'ar',
        requireInteraction: data.requireInteraction || false,
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// النقر على الإشعار
self.addEventListener('notificationclick', (event) => {
    console.log('[ServiceWorker] Notification clicked');
    
    event.notification.close();
    
    if (event.action === 'close') {
        return;
    }
    
    const urlToOpen = event.notification.data?.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((windowClients) => {
                // البحث عن نافذة مفتوحة
                for (const client of windowClients) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // فتح نافذة جديدة
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// المزامنة في الخلفية
self.addEventListener('sync', (event) => {
    console.log('[ServiceWorker] Sync:', event.tag);
    
    if (event.tag === 'sync-pending-data') {
        event.waitUntil(syncPendingData());
    }
});

// مزامنة البيانات المعلقة
async function syncPendingData() {
    try {
        // الحصول على البيانات المعلقة من IndexedDB
        const pendingData = await getPendingDataFromIndexedDB();
        
        for (const item of pendingData) {
            try {
                const response = await fetch(item.url, {
                    method: item.method,
                    headers: item.headers,
                    body: item.body,
                });
                
                if (response.ok) {
                    await removePendingDataFromIndexedDB(item.id);
                }
            } catch (error) {
                console.error('[ServiceWorker] Sync failed for item:', item.id);
            }
        }
    } catch (error) {
        console.error('[ServiceWorker] Sync error:', error);
    }
}

// دوال IndexedDB المساعدة
async function getPendingDataFromIndexedDB() {
    // سيتم تنفيذها لاحقاً
    return [];
}

async function removePendingDataFromIndexedDB(id) {
    // سيتم تنفيذها لاحقاً
}

// رسالة من الصفحة
self.addEventListener('message', (event) => {
    console.log('[ServiceWorker] Message received:', event.data);
    
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data.type === 'CLEAR_CACHE') {
        caches.delete(CACHE_NAME);
    }
});
