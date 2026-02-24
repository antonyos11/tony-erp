/**
 * Tony Store - Product Detail Page JavaScript
 * =============================================
 * Enhanced product experience for Egypt market
 */

// =============================================
// IMAGE GALLERY
// =============================================
class ProductGallery {
    constructor(container) {
        this.container = container;
        this.mainImage = container.querySelector('.main-image');
        this.thumbnails = container.querySelectorAll('.thumbnail');
        this.images = [];
        this.currentIndex = 0;
        
        this.init();
    }
    
    init() {
        // Collect all images
        this.thumbnails.forEach((thumb, index) => {
            this.images.push(thumb.querySelector('img').src);
            
            thumb.addEventListener('click', () => {
                this.goTo(index);
            });
        });
        
        // Main image click for zoom
        if (this.mainImage) {
            this.mainImage.addEventListener('click', () => {
                this.openZoom();
            });
        }
        
        // Touch/swipe support
        this.initSwipe();
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') this.next();
            if (e.key === 'ArrowRight') this.prev();
            if (e.key === 'Escape') this.closeZoom();
        });
    }
    
    goTo(index) {
        this.currentIndex = index;
        
        // Update main image
        if (this.mainImage) {
            this.mainImage.src = this.images[index];
        }
        
        // Update active thumbnail
        this.thumbnails.forEach((thumb, i) => {
            thumb.classList.toggle('active', i === index);
        });
    }
    
    next() {
        const nextIndex = (this.currentIndex + 1) % this.images.length;
        this.goTo(nextIndex);
    }
    
    prev() {
        const prevIndex = (this.currentIndex - 1 + this.images.length) % this.images.length;
        this.goTo(prevIndex);
    }
    
    initSwipe() {
        let startX = 0;
        let startY = 0;
        
        this.container.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });
        
        this.container.addEventListener('touchend', (e) => {
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            
            const diffX = endX - startX;
            const diffY = Math.abs(endY - startY);
            
            // Only horizontal swipe
            if (Math.abs(diffX) > 50 && diffY < 50) {
                if (diffX > 0) {
                    this.prev(); // RTL: swipe right = previous
                } else {
                    this.next(); // RTL: swipe left = next
                }
            }
        }, { passive: true });
    }
    
    openZoom() {
        // Create zoom overlay
        let overlay = document.querySelector('.image-zoom-overlay');
        
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'image-zoom-overlay';
            overlay.innerHTML = `
                <button class="zoom-close" onclick="productGallery.closeZoom()">✕</button>
                <img src="${this.images[this.currentIndex]}" class="zoom-image" alt="صورة مكبرة">
                <button class="zoom-nav zoom-prev" onclick="productGallery.prev()">‹</button>
                <button class="zoom-nav zoom-next" onclick="productGallery.next()">›</button>
            `;
            document.body.appendChild(overlay);
        } else {
            overlay.querySelector('.zoom-image').src = this.images[this.currentIndex];
        }
        
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    closeZoom() {
        const overlay = document.querySelector('.image-zoom-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
}

// Global gallery instance
let productGallery;

// =============================================
// QUANTITY SELECTOR
// =============================================
class QuantitySelector {
    constructor(container, options = {}) {
        this.container = container;
        this.minBtn = container.querySelector('.qty-btn.minus, [data-action="decrease"]');
        this.maxBtn = container.querySelector('.qty-btn.plus, [data-action="increase"]');
        this.input = container.querySelector('.qty-input');
        this.min = options.min || 1;
        this.max = options.max || 99;
        this.onChange = options.onChange || (() => {});
        
        this.init();
    }
    
    init() {
        if (this.minBtn) {
            this.minBtn.addEventListener('click', () => this.decrease());
        }
        
        if (this.maxBtn) {
            this.maxBtn.addEventListener('click', () => this.increase());
        }
        
        if (this.input) {
            this.input.addEventListener('change', () => this.validate());
            this.input.addEventListener('blur', () => this.validate());
        }
        
        this.updateButtons();
    }
    
    getValue() {
        return parseInt(this.input?.value) || this.min;
    }
    
    setValue(value) {
        const newValue = Math.max(this.min, Math.min(this.max, value));
        if (this.input) {
            this.input.value = newValue;
        }
        this.updateButtons();
        this.onChange(newValue);
    }
    
    increase() {
        this.setValue(this.getValue() + 1);
    }
    
    decrease() {
        this.setValue(this.getValue() - 1);
    }
    
    validate() {
        this.setValue(this.getValue());
    }
    
    updateButtons() {
        const value = this.getValue();
        
        if (this.minBtn) {
            this.minBtn.disabled = value <= this.min;
        }
        
        if (this.maxBtn) {
            this.maxBtn.disabled = value >= this.max;
        }
    }
}

// =============================================
// PRODUCT TABS
// =============================================
function initProductTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // Update buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Update content
            tabContents.forEach(content => {
                content.classList.toggle('active', content.id === tabId);
            });
        });
    });
}

// =============================================
// REVIEWS
// =============================================
class ReviewsManager {
    constructor(productId) {
        this.productId = productId;
        this.page = 1;
        this.loading = false;
        this.hasMore = true;
    }
    
    async loadReviews() {
        if (this.loading || !this.hasMore) return;
        
        this.loading = true;
        
        try {
            const response = await fetch(`/ecommerce/api/products/${this.productId}/reviews/?page=${this.page}`);
            if (response.ok) {
                const data = await response.json();
                this.renderReviews(data.results || data);
                this.hasMore = !!data.next;
                this.page++;
            }
        } catch (error) {
            console.error('Error loading reviews:', error);
        } finally {
            this.loading = false;
        }
    }
    
    renderReviews(reviews) {
        const container = document.querySelector('.reviews-list');
        if (!container) return;
        
        reviews.forEach(review => {
            const reviewElement = document.createElement('div');
            reviewElement.className = 'review-card';
            reviewElement.innerHTML = `
                <div class="review-header">
                    <div class="reviewer-avatar">${review.user_name?.charAt(0) || 'م'}</div>
                    <div class="reviewer-info">
                        <div class="reviewer-name">${review.user_name || 'عميل'}</div>
                        <div class="review-date">${this.formatDate(review.created_at)}</div>
                    </div>
                    <div class="review-rating">${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}</div>
                </div>
                <div class="review-content">${review.comment}</div>
                ${review.images?.length ? `
                    <div class="review-images">
                        ${review.images.map(img => `
                            <img src="${img}" alt="صورة المراجعة" class="review-image" onclick="openImageZoom('${img}')">
                        `).join('')}
                    </div>
                ` : ''}
            `;
            container.appendChild(reviewElement);
        });
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ar-EG', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
    
    async submitReview(formData) {
        try {
            const response = await fetch(`/ecommerce/api/products/${this.productId}/reviews/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                showToast('تم إضافة مراجعتك بنجاح! شكراً لك ⭐', 'success');
                this.page = 1;
                this.hasMore = true;
                document.querySelector('.reviews-list').innerHTML = '';
                this.loadReviews();
                return true;
            } else {
                const error = await response.json();
                showToast(error.message || 'حدث خطأ أثناء إضافة المراجعة', 'error');
                return false;
            }
        } catch (error) {
            showToast('حدث خطأ في الاتصال', 'error');
            return false;
        }
    }
}

// =============================================
// VARIANT SELECTOR
// =============================================
class VariantSelector {
    constructor(container, variants) {
        this.container = container;
        this.variants = variants;
        this.selected = {};
        this.onSelect = () => {};
        
        this.init();
    }
    
    init() {
        this.container.querySelectorAll('.variant-option').forEach(option => {
            option.addEventListener('click', () => {
                const type = option.dataset.type;
                const value = option.dataset.value;
                
                // Update selection
                this.selected[type] = value;
                
                // Update UI
                this.container.querySelectorAll(`[data-type="${type}"]`).forEach(opt => {
                    opt.classList.toggle('selected', opt.dataset.value === value);
                });
                
                // Find matching variant
                this.findVariant();
            });
        });
    }
    
    findVariant() {
        const matchingVariant = this.variants.find(v => {
            return Object.keys(this.selected).every(key => v[key] === this.selected[key]);
        });
        
        if (matchingVariant) {
            this.onSelect(matchingVariant);
        }
    }
}

// =============================================
// STICKY ADD TO CART
// =============================================
function initStickyAddToCart() {
    const productActions = document.querySelector('.product-actions-section');
    const stickyBar = document.querySelector('.sticky-add-to-cart');
    
    if (!productActions || !stickyBar) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            stickyBar.classList.toggle('show', !entry.isIntersecting);
        });
    }, {
        rootMargin: '-100px 0px 0px 0px'
    });
    
    observer.observe(productActions);
}

// =============================================
// RECENTLY VIEWED
// =============================================
class RecentlyViewed {
    constructor(maxItems = 10) {
        this.maxItems = maxItems;
        this.storageKey = 'tony_recently_viewed';
    }
    
    getItems() {
        try {
            return JSON.parse(localStorage.getItem(this.storageKey)) || [];
        } catch {
            return [];
        }
    }
    
    addItem(product) {
        let items = this.getItems();
        
        // Remove if already exists
        items = items.filter(item => item.id !== product.id);
        
        // Add to beginning
        items.unshift({
            id: product.id,
            name: product.name,
            image: product.image,
            price: product.price,
            viewedAt: Date.now()
        });
        
        // Limit items
        items = items.slice(0, this.maxItems);
        
        localStorage.setItem(this.storageKey, JSON.stringify(items));
    }
    
    render(container) {
        const items = this.getItems().slice(0, 5);
        
        if (items.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.innerHTML = `
            <h3 class="section-title">شاهدت مؤخراً</h3>
            <div class="recently-viewed-scroll">
                ${items.map(item => `
                    <a href="/ecommerce/product/${item.id}/" class="recently-viewed-item">
                        <img src="${item.image}" alt="${item.name}">
                        <div class="recently-viewed-price">${formatPrice(item.price)} ج.م</div>
                    </a>
                `).join('')}
            </div>
        `;
    }
}

const recentlyViewed = new RecentlyViewed();

// =============================================
// SHARE PRODUCT
// =============================================
async function shareProduct(product) {
    const shareData = {
        title: product.name,
        text: `شاهد ${product.name} على متجر Tony`,
        url: window.location.href
    };
    
    if (navigator.share) {
        try {
            await navigator.share(shareData);
        } catch (error) {
            // User cancelled or error
            console.log('Share cancelled');
        }
    } else {
        // Fallback: copy link
        copyToClipboard(window.location.href);
        showToast('تم نسخ الرابط!', 'success');
    }
}

function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
}

// =============================================
// PRODUCT AVAILABILITY CHECK
// =============================================
async function checkAvailability(productId, governorate) {
    try {
        const response = await fetch(`/ecommerce/api/products/${productId}/availability/?governorate=${governorate}`);
        if (response.ok) {
            const data = await response.json();
            return data;
        }
    } catch (error) {
        console.error('Availability check failed:', error);
    }
    return null;
}

// =============================================
// PRICE ALERTS
// =============================================
async function setPriceAlert(productId, targetPrice) {
    try {
        const response = await fetch('/ecommerce/api/price-alerts/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                product_id: productId,
                target_price: targetPrice
            })
        });
        
        if (response.ok) {
            showToast('سنرسل لك إشعار عندما ينخفض السعر 🔔', 'success');
            return true;
        }
    } catch (error) {
        showToast('حدث خطأ أثناء إعداد التنبيه', 'error');
    }
    return false;
}

// =============================================
// HELPERS
// =============================================
function formatPrice(price) {
    return new Intl.NumberFormat('ar-EG', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    }).format(price);
}

function getCsrfToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

function showToast(message, type = 'info') {
    if (window.TonyStore && window.TonyStore.showToast) {
        window.TonyStore.showToast(message, type);
    } else {
        alert(message);
    }
}

// =============================================
// INITIALIZATION
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize gallery
    const galleryContainer = document.querySelector('.product-gallery');
    if (galleryContainer) {
        productGallery = new ProductGallery(galleryContainer);
    }
    
    // Initialize quantity selectors
    document.querySelectorAll('.quantity-selector').forEach(container => {
        new QuantitySelector(container, {
            min: 1,
            max: parseInt(container.dataset.max) || 99
        });
    });
    
    // Initialize tabs
    initProductTabs();
    
    // Initialize sticky add to cart
    initStickyAddToCart();
    
    // Track product view
    const productData = document.querySelector('[data-product-json]');
    if (productData) {
        try {
            const product = JSON.parse(productData.dataset.productJson);
            recentlyViewed.addItem(product);
        } catch (error) {
            console.error('Error tracking product view:', error);
        }
    }
    
    // Render recently viewed
    const recentlyViewedContainer = document.querySelector('.recently-viewed-section');
    if (recentlyViewedContainer) {
        recentlyViewed.render(recentlyViewedContainer);
    }
    
    console.log('📦 Product Detail initialized');
});

// =============================================
// EXPORTS
// =============================================
window.ProductDetail = {
    ProductGallery,
    QuantitySelector,
    VariantSelector,
    ReviewsManager,
    RecentlyViewed,
    shareProduct,
    checkAvailability,
    setPriceAlert
};
