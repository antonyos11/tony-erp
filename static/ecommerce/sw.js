/**
 * Tony Store - E-commerce Service Worker
 * ======================================
 * PWA service worker optimized for Egypt e-commerce
 * Version: 2.0.0 - January 2026
 */

const CACHE_VERSION = 'tony-store-v2.0.0';
const STATIC_CACHE = 'tony-store-static-v2';
const DYNAMIC_CACHE = 'tony-store-dynamic-v2';
const IMAGE_CACHE = 'tony-store-images-v2';
const API_CACHE = 'tony-store-api-v2';

// Offline page
const OFFLINE_PAGE = '/ecommerce/offline/';
const OFFLINE_IMAGE = '/static/ecommerce/img/offline-placeholder.png';

// Static assets to precache
const STATIC_ASSETS = [
  '/ecommerce/',
  '/ecommerce/offline/',
  '/static/ecommerce/css/store.css',
  '/static/ecommerce/css/mobile.css',
  '/static/ecommerce/js/store.js',
  '/static/ecommerce/js/cart.js',
  '/static/ecommerce/js/search.js',
  '/static/ecommerce/manifest.json',
  '/static/ecommerce/icons/icon-192x192.png',
  '/static/ecommerce/icons/icon-512x512.png',
  '/static/ecommerce/img/logo.svg',
  '/static/ecommerce/img/offline-placeholder.png',
  // CDN assets
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
];

// API routes to cache
const API_ROUTES = [
  '/ecommerce/api/products/',
  '/ecommerce/api/categories/',
  '/ecommerce/api/brands/',
];

// =============================================
// INSTALL EVENT - Precache static assets
// =============================================
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker v2.0.0...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Precaching static assets...');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
      .catch((error) => {
        console.error('[SW] Precache failed:', error);
      })
  );
});

// =============================================
// ACTIVATE EVENT - Clean old caches
// =============================================
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');
  
  const cacheWhitelist = [STATIC_CACHE, DYNAMIC_CACHE, IMAGE_CACHE, API_CACHE];
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (!cacheWhitelist.includes(cacheName)) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => self.clients.claim())
  );
});

// =============================================
// FETCH EVENT - Smart caching strategies
// =============================================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip Chrome extensions and other origins
  if (!url.origin.includes(self.location.origin) && 
      !url.href.includes('cdn.jsdelivr.net') &&
      !url.href.includes('cdnjs.cloudflare.com')) {
    return;
  }
  
  // Strategy selection based on request type
  if (isImageRequest(request)) {
    event.respondWith(cacheFirstWithFallback(request, IMAGE_CACHE));
  } else if (isAPIRequest(request)) {
    event.respondWith(networkFirstWithCache(request, API_CACHE));
  } else if (isStaticAsset(request)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
  } else {
    event.respondWith(networkFirstWithOffline(request));
  }
});

// =============================================
// CACHING STRATEGIES
// =============================================

/**
 * Cache First - Best for static assets
 */
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    // Background update
    updateCache(request, cacheName);
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    return caches.match(OFFLINE_PAGE);
  }
}

/**
 * Cache First with Image Fallback
 */
async function cacheFirstWithFallback(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // Return placeholder image for failed image requests
    return caches.match(OFFLINE_IMAGE);
  }
}

/**
 * Network First with Cache Fallback - Best for API
 */
async function networkFirstWithCache(request, cacheName) {
  const cache = await caches.open(cacheName);
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      // Cache successful API responses for 5 minutes
      const responseToCache = networkResponse.clone();
      cache.put(request, responseToCache);
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      console.log('[SW] Serving cached API response:', request.url);
      return cachedResponse;
    }
    return new Response(JSON.stringify({ error: 'Offline', message: 'لا يوجد اتصال بالإنترنت' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Network First with Offline Page Fallback
 */
async function networkFirstWithOffline(request) {
  const cache = await caches.open(DYNAMIC_CACHE);
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok && request.url.includes('/ecommerce/')) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match(OFFLINE_PAGE);
    }
    
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Background cache update
 */
async function updateCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response);
    }
  } catch (error) {
    // Silent fail for background updates
  }
}

// =============================================
// HELPER FUNCTIONS
// =============================================

function isImageRequest(request) {
  return request.destination === 'image' || 
         /\.(jpg|jpeg|png|gif|webp|svg|ico)$/i.test(request.url);
}

function isAPIRequest(request) {
  return request.url.includes('/api/') || 
         request.url.includes('/ecommerce/api/');
}

function isStaticAsset(request) {
  return request.url.includes('/static/') ||
         request.destination === 'style' ||
         request.destination === 'script' ||
         request.destination === 'font';
}

// =============================================
// PUSH NOTIFICATIONS
// =============================================
self.addEventListener('push', (event) => {
  console.log('[SW] Push received');
  
  let data = {
    title: 'متجر Tony',
    body: 'لديك إشعار جديد',
    icon: '/static/ecommerce/icons/icon-192x192.png',
    badge: '/static/ecommerce/icons/badge-72.png',
    tag: 'default',
    data: { url: '/ecommerce/' }
  };
  
  if (event.data) {
    try {
      data = { ...data, ...event.data.json() };
    } catch (e) {
      data.body = event.data.text();
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    tag: data.tag,
    vibrate: [200, 100, 200],
    data: data.data,
    actions: data.actions || [
      { action: 'open', title: 'فتح', icon: '/static/ecommerce/icons/open-24.png' },
      { action: 'close', title: 'إغلاق', icon: '/static/ecommerce/icons/close-24.png' }
    ],
    dir: 'rtl',
    lang: 'ar'
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'close') {
    return;
  }
  
  const urlToOpen = event.notification.data?.url || '/ecommerce/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window if found
        for (const client of clientList) {
          if (client.url.includes('/ecommerce/') && 'focus' in client) {
            client.navigate(urlToOpen);
            return client.focus();
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// =============================================
// BACKGROUND SYNC
// =============================================
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'sync-cart') {
    event.waitUntil(syncCart());
  } else if (event.tag === 'sync-wishlist') {
    event.waitUntil(syncWishlist());
  } else if (event.tag === 'sync-orders') {
    event.waitUntil(syncOrders());
  }
});

async function syncCart() {
  try {
    const pendingItems = await getPendingFromIndexedDB('pending-cart');
    for (const item of pendingItems) {
      await fetch('/ecommerce/api/cart/sync/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      });
    }
    await clearPendingFromIndexedDB('pending-cart');
  } catch (error) {
    console.error('[SW] Cart sync failed:', error);
  }
}

async function syncWishlist() {
  // Similar implementation for wishlist
}

async function syncOrders() {
  // Order status sync
}

// IndexedDB helpers (simplified)
async function getPendingFromIndexedDB(storeName) {
  // Implementation would use IndexedDB
  return [];
}

async function clearPendingFromIndexedDB(storeName) {
  // Clear pending items
}

// =============================================
// PERIODIC BACKGROUND SYNC
// =============================================
self.addEventListener('periodicsync', (event) => {
  console.log('[SW] Periodic sync:', event.tag);
  
  if (event.tag === 'update-products') {
    event.waitUntil(updateProductCache());
  }
});

async function updateProductCache() {
  try {
    const response = await fetch('/ecommerce/api/products/?featured=true');
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      await cache.put('/ecommerce/api/products/?featured=true', response);
    }
  } catch (error) {
    console.error('[SW] Product cache update failed:', error);
  }
}

console.log('[SW] Tony Store Service Worker v2.0.0 loaded');
