/**
 * Tony Store - E-commerce JavaScript
 * ====================================
 * Mobile-first, PWA-ready, Egypt market optimized
 * Week 2 Phase 1 - January 2026
 */

// =============================================
// PWA INSTALLATION
// =============================================
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBanner();
});

function showInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
        setTimeout(() => {
            banner.classList.add('show');
        }, 3000);
    }
}

function installPWA() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                showToast('تم تثبيت التطبيق بنجاح! 🎉', 'success');
            }
            deferredPrompt = null;
            hideInstallBanner();
        });
    }
}

function hideInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
        banner.classList.remove('show');
    }
}

// =============================================
// SERVICE WORKER REGISTRATION
// =============================================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/static/ecommerce/sw.js', {
                scope: '/ecommerce/'
            });
            console.log('Service Worker registered:', registration.scope);
            
            // Check for updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        showUpdateNotification();
                    }
                });
            });
        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    });
}

function showUpdateNotification() {
    showToast('يوجد تحديث جديد! انقر هنا للتحديث', 'info', () => {
        window.location.reload();
    });
}

// =============================================
// TOAST NOTIFICATIONS
// =============================================
function showToast(message, type = 'info', onClick = null) {
    const container = getOrCreateToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${getToastIcon(type)}</span>
        <span>${message}</span>
    `;
    
    if (onClick) {
        toast.style.cursor = 'pointer';
        toast.addEventListener('click', onClick);
    }
    
    container.appendChild(toast);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'toast-out 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getOrCreateToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    return container;
}

function getToastIcon(type) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    return icons[type] || icons.info;
}

// =============================================
// CART MANAGEMENT
// =============================================
class Cart {
    constructor() {
        this.items = this.loadFromStorage();
        this.listeners = [];
        this.syncWithServer();
    }
    
    loadFromStorage() {
        try {
            return JSON.parse(localStorage.getItem('tony_cart')) || [];
        } catch {
            return [];
        }
    }
    
    saveToStorage() {
        localStorage.setItem('tony_cart', JSON.stringify(this.items));
        this.notifyListeners();
        this.scheduleSync();
    }
    
    add(product, quantity = 1) {
        const existing = this.items.find(item => item.id === product.id);
        
        if (existing) {
            existing.quantity += quantity;
        } else {
            this.items.push({
                id: product.id,
                name: product.name,
                price: product.price,
                image: product.image,
                quantity: quantity
            });
        }
        
        this.saveToStorage();
        showToast(`تمت إضافة "${product.name}" إلى السلة`, 'success');
        this.animateCartIcon();
    }
    
    remove(productId) {
        this.items = this.items.filter(item => item.id !== productId);
        this.saveToStorage();
        showToast('تم حذف المنتج من السلة', 'info');
    }
    
    updateQuantity(productId, quantity) {
        const item = this.items.find(item => item.id === productId);
        if (item) {
            if (quantity <= 0) {
                this.remove(productId);
            } else {
                item.quantity = quantity;
                this.saveToStorage();
            }
        }
    }
    
    clear() {
        this.items = [];
        this.saveToStorage();
    }
    
    getTotal() {
        return this.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    }
    
    getCount() {
        return this.items.reduce((sum, item) => sum + item.quantity, 0);
    }
    
    onUpdate(callback) {
        this.listeners.push(callback);
    }
    
    notifyListeners() {
        this.listeners.forEach(callback => callback(this));
    }
    
    animateCartIcon() {
        const cartIcons = document.querySelectorAll('.cart-icon, .header-action .fa-shopping-cart');
        cartIcons.forEach(icon => {
            icon.classList.add('bounce');
            setTimeout(() => icon.classList.remove('bounce'), 500);
        });
    }
    
    scheduleSync() {
        if ('serviceWorker' in navigator && 'sync' in window.SyncManager) {
            navigator.serviceWorker.ready.then(registration => {
                registration.sync.register('sync-cart');
            });
        }
    }
    
    async syncWithServer() {
        if (!navigator.onLine) return;
        
        try {
            const response = await fetch('/ecommerce/api/cart/', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (response.ok) {
                const serverCart = await response.json();
                // Merge logic if needed
            }
        } catch (error) {
            console.log('Cart sync deferred (offline or not logged in)');
        }
    }
}

// Global cart instance
const cart = new Cart();

// =============================================
// WISHLIST MANAGEMENT
// =============================================
class Wishlist {
    constructor() {
        this.items = this.loadFromStorage();
    }
    
    loadFromStorage() {
        try {
            return JSON.parse(localStorage.getItem('tony_wishlist')) || [];
        } catch {
            return [];
        }
    }
    
    saveToStorage() {
        localStorage.setItem('tony_wishlist', JSON.stringify(this.items));
    }
    
    toggle(productId) {
        if (this.has(productId)) {
            this.remove(productId);
            return false;
        } else {
            this.add(productId);
            return true;
        }
    }
    
    add(productId) {
        if (!this.has(productId)) {
            this.items.push(productId);
            this.saveToStorage();
            showToast('تمت الإضافة إلى المفضلة ❤️', 'success');
        }
    }
    
    remove(productId) {
        this.items = this.items.filter(id => id !== productId);
        this.saveToStorage();
        showToast('تم الحذف من المفضلة', 'info');
    }
    
    has(productId) {
        return this.items.includes(productId);
    }
    
    getCount() {
        return this.items.length;
    }
}

const wishlist = new Wishlist();

// =============================================
// MINI CART FUNCTIONALITY
// =============================================
function openMiniCart() {
    const overlay = document.querySelector('.mini-cart-overlay');
    const miniCart = document.querySelector('.mini-cart');
    
    if (overlay && miniCart) {
        overlay.classList.add('active');
        miniCart.classList.add('active');
        document.body.style.overflow = 'hidden';
        renderMiniCartItems();
    }
}

function closeMiniCart() {
    const overlay = document.querySelector('.mini-cart-overlay');
    const miniCart = document.querySelector('.mini-cart');
    
    if (overlay && miniCart) {
        overlay.classList.remove('active');
        miniCart.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function renderMiniCartItems() {
    const container = document.querySelector('.mini-cart-items');
    const totalElement = document.querySelector('.mini-cart-total-value');
    
    if (!container) return;
    
    if (cart.items.length === 0) {
        container.innerHTML = `
            <div class="empty-cart">
                <div class="empty-cart-icon">🛒</div>
                <p>السلة فارغة</p>
                <a href="/ecommerce/products/" class="continue-shopping">تسوق الآن</a>
            </div>
        `;
    } else {
        container.innerHTML = cart.items.map(item => `
            <div class="mini-cart-item" data-id="${item.id}">
                <img src="${item.image}" alt="${item.name}" class="mini-cart-item-image">
                <div class="mini-cart-item-info">
                    <div class="mini-cart-item-title">${item.name}</div>
                    <div class="mini-cart-item-price">${formatPrice(item.price)} ج.م</div>
                    <div class="mini-cart-item-quantity">
                        <button class="quantity-btn minus" onclick="updateCartItemQuantity(${item.id}, ${item.quantity - 1})">-</button>
                        <span class="quantity-value">${item.quantity}</span>
                        <button class="quantity-btn plus" onclick="updateCartItemQuantity(${item.id}, ${item.quantity + 1})">+</button>
                    </div>
                </div>
                <button class="mini-cart-item-remove" onclick="removeFromCart(${item.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');
    }
    
    if (totalElement) {
        totalElement.textContent = formatPrice(cart.getTotal()) + ' ج.م';
    }
    
    updateCartCount();
}

function updateCartItemQuantity(productId, quantity) {
    cart.updateQuantity(productId, quantity);
    renderMiniCartItems();
}

function removeFromCart(productId) {
    cart.remove(productId);
    renderMiniCartItems();
}

function updateCartCount() {
    const countElements = document.querySelectorAll('.cart-count');
    const count = cart.getCount();
    
    countElements.forEach(el => {
        el.textContent = count;
        el.style.display = count > 0 ? 'flex' : 'none';
    });
}

// =============================================
// ADD TO CART HANDLING
// =============================================
function addToCart(productId) {
    const productElement = document.querySelector(`[data-product-id="${productId}"]`);
    
    if (productElement) {
        const product = {
            id: productId,
            name: productElement.dataset.productName,
            price: parseFloat(productElement.dataset.productPrice),
            image: productElement.dataset.productImage
        };
        
        cart.add(product);
    } else {
        // Fetch product data from API
        fetchProductAndAdd(productId);
    }
}

async function fetchProductAndAdd(productId) {
    try {
        const response = await fetch(`/ecommerce/api/products/${productId}/`);
        if (response.ok) {
            const product = await response.json();
            cart.add({
                id: product.id,
                name: product.name,
                price: product.price,
                image: product.image
            });
        }
    } catch (error) {
        showToast('حدث خطأ أثناء إضافة المنتج', 'error');
    }
}

// =============================================
// WISHLIST HANDLING
// =============================================
function toggleWishlist(productId, button) {
    const added = wishlist.toggle(productId);
    
    if (button) {
        button.classList.toggle('active', added);
    }
    
    updateWishlistCount();
}

function updateWishlistCount() {
    const countElements = document.querySelectorAll('.wishlist-count');
    const count = wishlist.getCount();
    
    countElements.forEach(el => {
        el.textContent = count;
        el.style.display = count > 0 ? 'flex' : 'none';
    });
}

// =============================================
// SEARCH FUNCTIONALITY
// =============================================
const searchInput = document.querySelector('.search-input');
let searchTimeout;

if (searchInput) {
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        
        if (query.length >= 2) {
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300);
        } else {
            hideSearchResults();
        }
    });
}

async function performSearch(query) {
    try {
        const response = await fetch(`/ecommerce/api/products/?search=${encodeURIComponent(query)}&limit=5`);
        if (response.ok) {
            const data = await response.json();
            displaySearchResults(data.results || data);
        }
    } catch (error) {
        console.error('Search error:', error);
    }
}

function displaySearchResults(products) {
    let resultsContainer = document.querySelector('.search-results');
    
    if (!resultsContainer) {
        resultsContainer = document.createElement('div');
        resultsContainer.className = 'search-results';
        document.querySelector('.search-container').appendChild(resultsContainer);
    }
    
    if (products.length === 0) {
        resultsContainer.innerHTML = '<div class="no-results">لا توجد نتائج</div>';
    } else {
        resultsContainer.innerHTML = products.map(product => `
            <a href="/ecommerce/product/${product.id}/" class="search-result-item">
                <img src="${product.image || '/static/ecommerce/images/placeholder.png'}" alt="${product.name}">
                <div class="search-result-info">
                    <div class="search-result-name">${product.name}</div>
                    <div class="search-result-price">${formatPrice(product.price)} ج.م</div>
                </div>
            </a>
        `).join('');
    }
    
    resultsContainer.classList.add('active');
}

function hideSearchResults() {
    const resultsContainer = document.querySelector('.search-results');
    if (resultsContainer) {
        resultsContainer.classList.remove('active');
    }
}

// Close search results on click outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
        hideSearchResults();
    }
});

// =============================================
// LAZY LOADING IMAGES
// =============================================
function initLazyLoading() {
    const lazyImages = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px 0px'
        });
        
        lazyImages.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for older browsers
        lazyImages.forEach(img => {
            img.src = img.dataset.src;
        });
    }
}

// =============================================
// INFINITE SCROLL
// =============================================
let currentPage = 1;
let isLoading = false;
let hasMore = true;

function initInfiniteScroll() {
    const productsGrid = document.querySelector('.products-grid');
    if (!productsGrid) return;
    
    window.addEventListener('scroll', () => {
        if (isLoading || !hasMore) return;
        
        const scrollPosition = window.innerHeight + window.scrollY;
        const pageHeight = document.documentElement.scrollHeight;
        
        if (scrollPosition >= pageHeight - 500) {
            loadMoreProducts();
        }
    });
}

async function loadMoreProducts() {
    isLoading = true;
    currentPage++;
    
    const grid = document.querySelector('.products-grid');
    
    // Show loading indicator
    const loader = document.createElement('div');
    loader.className = 'loading-indicator';
    loader.innerHTML = '<div class="spinner"></div>';
    grid.appendChild(loader);
    
    try {
        const response = await fetch(`/ecommerce/api/products/?page=${currentPage}`);
        if (response.ok) {
            const data = await response.json();
            const products = data.results || data;
            
            if (products.length === 0) {
                hasMore = false;
            } else {
                products.forEach(product => {
                    grid.appendChild(createProductCard(product));
                });
                initLazyLoading();
            }
        }
    } catch (error) {
        console.error('Error loading products:', error);
        currentPage--;
    } finally {
        loader.remove();
        isLoading = false;
    }
}

function createProductCard(product) {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.dataset.productId = product.id;
    card.dataset.productName = product.name;
    card.dataset.productPrice = product.price;
    card.dataset.productImage = product.image;
    
    card.innerHTML = `
        <div class="product-image-container">
            <img data-src="${product.image || '/static/ecommerce/images/placeholder.png'}" 
                 alt="${product.name}" 
                 class="product-image">
            ${product.discount ? `<span class="badge badge-sale">-${product.discount}%</span>` : ''}
            <button class="product-wishlist ${wishlist.has(product.id) ? 'active' : ''}" 
                    onclick="toggleWishlist(${product.id}, this)">
                ❤️
            </button>
        </div>
        <div class="product-info">
            <div class="product-category">${product.category_name || ''}</div>
            <h3 class="product-title">${product.name}</h3>
            <div class="product-rating">
                <span class="stars">${'★'.repeat(Math.round(product.rating || 0))}${'☆'.repeat(5 - Math.round(product.rating || 0))}</span>
                <span class="rating-count">(${product.reviews_count || 0})</span>
            </div>
            <div class="product-price">
                <span class="current-price">${formatPrice(product.price)} ج.م</span>
                ${product.original_price ? `<span class="original-price">${formatPrice(product.original_price)} ج.م</span>` : ''}
            </div>
        </div>
        <div class="product-actions">
            <button class="add-to-cart-btn" onclick="addToCart(${product.id})" ${product.in_stock === false ? 'disabled' : ''}>
                ${product.in_stock === false ? 'غير متوفر' : '🛒 أضف للسلة'}
            </button>
        </div>
    `;
    
    return card;
}

// =============================================
// PRICE FORMATTING
// =============================================
function formatPrice(price) {
    return new Intl.NumberFormat('ar-EG', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    }).format(price);
}

// =============================================
// BOTTOM NAVIGATION ACTIVE STATE
// =============================================
function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.bottom-nav-item');
    
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (currentPath.includes(href) || (href === '/ecommerce/' && currentPath === '/ecommerce/')) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// =============================================
// NETWORK STATUS
// =============================================
function initNetworkStatus() {
    function updateOnlineStatus() {
        if (navigator.onLine) {
            showToast('تم استعادة الاتصال بالإنترنت ✅', 'success');
        } else {
            showToast('أنت الآن غير متصل بالإنترنت 📵', 'warning');
        }
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
}

// =============================================
// PUSH NOTIFICATIONS
// =============================================
async function requestNotificationPermission() {
    if (!('Notification' in window)) {
        console.log('Notifications not supported');
        return false;
    }
    
    if (Notification.permission === 'granted') {
        return true;
    }
    
    if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission();
        return permission === 'granted';
    }
    
    return false;
}

async function subscribeToNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        return;
    }
    
    const hasPermission = await requestNotificationPermission();
    if (!hasPermission) return;
    
    try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(window.VAPID_PUBLIC_KEY)
        });
        
        // Send subscription to server
        await fetch('/ecommerce/api/push-subscription/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(subscription)
        });
        
        showToast('تم تفعيل الإشعارات بنجاح 🔔', 'success');
    } catch (error) {
        console.error('Push subscription failed:', error);
    }
}

function urlBase64ToUint8Array(base64String) {
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

// =============================================
// CSRF TOKEN
// =============================================
function getCsrfToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

// =============================================
// INITIALIZATION
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize all components
    initLazyLoading();
    initInfiniteScroll();
    setActiveNavItem();
    initNetworkStatus();
    updateCartCount();
    updateWishlistCount();
    
    // Update cart on changes
    cart.onUpdate(() => {
        updateCartCount();
    });
    
    // Mini cart overlay click to close
    const overlay = document.querySelector('.mini-cart-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeMiniCart);
    }
    
    // Check wishlist buttons initial state
    document.querySelectorAll('.product-wishlist').forEach(btn => {
        const productId = parseInt(btn.closest('.product-card')?.dataset.productId);
        if (productId && wishlist.has(productId)) {
            btn.classList.add('active');
        }
    });
    
    console.log('🚀 Tony Store initialized');
});

// =============================================
// EXPORTS FOR GLOBAL ACCESS
// =============================================
window.TonyStore = {
    cart,
    wishlist,
    addToCart,
    toggleWishlist,
    openMiniCart,
    closeMiniCart,
    showToast,
    installPWA,
    subscribeToNotifications
};
