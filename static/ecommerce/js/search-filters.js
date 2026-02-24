/**
 * Tony Store - Search & Filter Functionality
 * ============================================
 * Advanced search with filters for Egypt market
 */

// =============================================
// SEARCH STATE
// =============================================
const searchState = {
    query: '',
    category: null,
    brand: null,
    priceMin: null,
    priceMax: null,
    rating: null,
    inStock: null,
    sortBy: 'relevance',
    page: 1,
    loading: false,
    hasMore: true
};

// =============================================
// INSTANT SEARCH
// =============================================
class InstantSearch {
    constructor(inputSelector, options = {}) {
        this.input = document.querySelector(inputSelector);
        this.resultsContainer = null;
        this.debounceTimer = null;
        this.minChars = options.minChars || 2;
        this.debounceMs = options.debounceMs || 300;
        this.maxResults = options.maxResults || 8;
        this.onSelect = options.onSelect || (() => {});
        
        if (this.input) {
            this.init();
        }
    }
    
    init() {
        // Create results container
        this.createResultsContainer();
        
        // Input events
        this.input.addEventListener('input', () => this.handleInput());
        this.input.addEventListener('focus', () => this.handleFocus());
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        
        // Close on click outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                this.hideResults();
            }
        });
    }
    
    createResultsContainer() {
        this.resultsContainer = document.createElement('div');
        this.resultsContainer.className = 'instant-search-results';
        this.input.parentElement.appendChild(this.resultsContainer);
    }
    
    handleInput() {
        clearTimeout(this.debounceTimer);
        
        const query = this.input.value.trim();
        
        if (query.length < this.minChars) {
            this.hideResults();
            return;
        }
        
        this.debounceTimer = setTimeout(() => {
            this.search(query);
        }, this.debounceMs);
    }
    
    handleFocus() {
        if (this.input.value.length >= this.minChars && this.resultsContainer.innerHTML) {
            this.showResults();
        }
    }
    
    handleKeydown(e) {
        const items = this.resultsContainer.querySelectorAll('.search-result-item');
        const activeItem = this.resultsContainer.querySelector('.search-result-item.active');
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navigateResults('down', items, activeItem);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateResults('up', items, activeItem);
                break;
            case 'Enter':
                if (activeItem) {
                    e.preventDefault();
                    activeItem.click();
                } else {
                    this.submitSearch();
                }
                break;
            case 'Escape':
                this.hideResults();
                break;
        }
    }
    
    navigateResults(direction, items, activeItem) {
        if (items.length === 0) return;
        
        let index = Array.from(items).indexOf(activeItem);
        
        if (direction === 'down') {
            index = (index + 1) % items.length;
        } else {
            index = index <= 0 ? items.length - 1 : index - 1;
        }
        
        items.forEach(item => item.classList.remove('active'));
        items[index].classList.add('active');
        items[index].scrollIntoView({ block: 'nearest' });
    }
    
    async search(query) {
        searchState.query = query;
        
        // Show loading
        this.resultsContainer.innerHTML = `
            <div class="search-loading">
                <div class="spinner"></div>
                <span>جاري البحث...</span>
            </div>
        `;
        this.showResults();
        
        try {
            const response = await fetch(`/ecommerce/api/products/search/?q=${encodeURIComponent(query)}&limit=${this.maxResults}`);
            
            if (response.ok) {
                const data = await response.json();
                this.renderResults(data);
            }
        } catch (error) {
            this.resultsContainer.innerHTML = `
                <div class="search-error">حدث خطأ في البحث</div>
            `;
        }
    }
    
    renderResults(data) {
        const products = data.results || data.products || data;
        const suggestions = data.suggestions || [];
        const categories = data.categories || [];
        
        if (products.length === 0 && suggestions.length === 0) {
            this.resultsContainer.innerHTML = `
                <div class="no-results">
                    <div class="no-results-icon">🔍</div>
                    <p>لا توجد نتائج لـ "${searchState.query}"</p>
                    <p class="no-results-hint">جرب كلمات مختلفة أو تصفح الأقسام</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        
        // Search suggestions
        if (suggestions.length > 0) {
            html += `
                <div class="search-section">
                    <div class="search-section-title">اقتراحات</div>
                    ${suggestions.map(s => `
                        <div class="search-suggestion" onclick="instantSearch.setSuggestion('${s}')">
                            🔍 ${s}
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        // Categories
        if (categories.length > 0) {
            html += `
                <div class="search-section">
                    <div class="search-section-title">الأقسام</div>
                    ${categories.map(c => `
                        <a href="/ecommerce/category/${c.slug}/" class="search-category-item">
                            📁 ${c.name}
                            <span class="count">(${c.product_count})</span>
                        </a>
                    `).join('')}
                </div>
            `;
        }
        
        // Products
        if (products.length > 0) {
            html += `
                <div class="search-section">
                    <div class="search-section-title">المنتجات</div>
                    ${products.map(product => `
                        <a href="/ecommerce/product/${product.id}/" class="search-result-item">
                            <img src="${product.image || '/static/ecommerce/images/placeholder.png'}" 
                                 alt="${product.name}" class="search-result-image">
                            <div class="search-result-info">
                                <div class="search-result-name">${this.highlightMatch(product.name)}</div>
                                <div class="search-result-category">${product.category_name || ''}</div>
                                <div class="search-result-price">${formatPrice(product.price)} ج.م</div>
                            </div>
                            ${product.discount ? `
                                <span class="search-result-badge">-${product.discount}%</span>
                            ` : ''}
                        </a>
                    `).join('')}
                </div>
            `;
            
            // Show all results link
            html += `
                <a href="/ecommerce/search/?q=${encodeURIComponent(searchState.query)}" class="search-view-all">
                    عرض كل النتائج ←
                </a>
            `;
        }
        
        this.resultsContainer.innerHTML = html;
    }
    
    highlightMatch(text) {
        const regex = new RegExp(`(${searchState.query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }
    
    setSuggestion(text) {
        this.input.value = text;
        this.search(text);
    }
    
    submitSearch() {
        const query = this.input.value.trim();
        if (query) {
            window.location.href = `/ecommerce/search/?q=${encodeURIComponent(query)}`;
        }
    }
    
    showResults() {
        this.resultsContainer.classList.add('active');
    }
    
    hideResults() {
        this.resultsContainer.classList.remove('active');
    }
}

// Global instance
let instantSearch;

// =============================================
// FILTERS
// =============================================
class ProductFilters {
    constructor(container) {
        this.container = container;
        this.filters = {};
        this.onFilter = () => {};
        
        if (this.container) {
            this.init();
        }
    }
    
    init() {
        // Category filter
        this.container.querySelectorAll('[data-filter="category"]').forEach(el => {
            el.addEventListener('change', () => {
                this.filters.category = el.value || null;
                this.applyFilters();
            });
        });
        
        // Brand filter
        this.container.querySelectorAll('.brand-checkbox').forEach(el => {
            el.addEventListener('change', () => {
                this.filters.brands = Array.from(
                    this.container.querySelectorAll('.brand-checkbox:checked')
                ).map(cb => cb.value);
                this.applyFilters();
            });
        });
        
        // Price range
        this.initPriceRange();
        
        // Rating filter
        this.container.querySelectorAll('[data-filter="rating"]').forEach(el => {
            el.addEventListener('click', () => {
                this.filters.rating = parseInt(el.dataset.value);
                this.container.querySelectorAll('[data-filter="rating"]').forEach(r => {
                    r.classList.toggle('active', parseInt(r.dataset.value) === this.filters.rating);
                });
                this.applyFilters();
            });
        });
        
        // In stock filter
        const stockFilter = this.container.querySelector('[data-filter="in-stock"]');
        if (stockFilter) {
            stockFilter.addEventListener('change', () => {
                this.filters.inStock = stockFilter.checked;
                this.applyFilters();
            });
        }
        
        // Clear filters
        const clearBtn = this.container.querySelector('.clear-filters-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFilters());
        }
    }
    
    initPriceRange() {
        const minInput = this.container.querySelector('[name="price_min"]');
        const maxInput = this.container.querySelector('[name="price_max"]');
        const rangeSlider = this.container.querySelector('.price-range-slider');
        
        if (minInput && maxInput) {
            const applyPrice = () => {
                this.filters.priceMin = minInput.value ? parseFloat(minInput.value) : null;
                this.filters.priceMax = maxInput.value ? parseFloat(maxInput.value) : null;
                this.applyFilters();
            };
            
            minInput.addEventListener('change', applyPrice);
            maxInput.addEventListener('change', applyPrice);
        }
        
        // Range slider (if using noUiSlider or similar)
        if (rangeSlider && typeof noUiSlider !== 'undefined') {
            noUiSlider.create(rangeSlider, {
                start: [0, 10000],
                connect: true,
                range: {
                    'min': 0,
                    'max': 10000
                },
                format: {
                    to: value => Math.round(value),
                    from: value => Number(value)
                }
            });
            
            rangeSlider.noUiSlider.on('change', (values) => {
                this.filters.priceMin = values[0];
                this.filters.priceMax = values[1];
                
                if (minInput) minInput.value = values[0];
                if (maxInput) maxInput.value = values[1];
                
                this.applyFilters();
            });
        }
    }
    
    applyFilters() {
        searchState.page = 1;
        searchState.hasMore = true;
        
        Object.assign(searchState, this.filters);
        
        this.onFilter(this.filters);
        this.updateURL();
        this.updateActiveCount();
    }
    
    clearFilters() {
        this.filters = {};
        
        // Reset UI
        this.container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        this.container.querySelectorAll('input[type="number"]').forEach(input => {
            input.value = '';
        });
        
        this.container.querySelectorAll('select').forEach(select => {
            select.selectedIndex = 0;
        });
        
        this.container.querySelectorAll('[data-filter="rating"]').forEach(el => {
            el.classList.remove('active');
        });
        
        this.applyFilters();
        showToast('تم مسح جميع الفلاتر', 'info');
    }
    
    updateURL() {
        const params = new URLSearchParams(window.location.search);
        
        // Update params based on filters
        Object.entries(this.filters).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                if (Array.isArray(value)) {
                    params.set(key, value.join(','));
                } else {
                    params.set(key, value);
                }
            } else {
                params.delete(key);
            }
        });
        
        const newURL = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState(null, '', newURL);
    }
    
    updateActiveCount() {
        const count = Object.values(this.filters).filter(v => 
            v !== null && v !== undefined && v !== '' && 
            (!Array.isArray(v) || v.length > 0)
        ).length;
        
        const badge = document.querySelector('.filter-count-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'flex' : 'none';
        }
    }
    
    loadFromURL() {
        const params = new URLSearchParams(window.location.search);
        
        params.forEach((value, key) => {
            this.filters[key] = value.includes(',') ? value.split(',') : value;
            
            // Update UI
            const element = this.container.querySelector(`[name="${key}"], [data-filter="${key}"]`);
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = value === 'true';
                } else if (element.type === 'select-one') {
                    element.value = value;
                }
            }
        });
        
        this.updateActiveCount();
    }
}

// =============================================
// SORT OPTIONS
// =============================================
function initSortOptions() {
    const sortSelect = document.querySelector('.sort-select');
    if (!sortSelect) return;
    
    sortSelect.addEventListener('change', () => {
        searchState.sortBy = sortSelect.value;
        searchState.page = 1;
        loadProducts();
        
        // Update URL
        const params = new URLSearchParams(window.location.search);
        params.set('sort', sortSelect.value);
        window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
    });
}

// =============================================
// LOAD PRODUCTS
// =============================================
async function loadProducts(append = false) {
    if (searchState.loading) return;
    
    searchState.loading = true;
    
    const grid = document.querySelector('.products-grid');
    if (!grid) return;
    
    // Build query params
    const params = new URLSearchParams();
    
    if (searchState.query) params.set('q', searchState.query);
    if (searchState.category) params.set('category', searchState.category);
    if (searchState.brands?.length) params.set('brands', searchState.brands.join(','));
    if (searchState.priceMin) params.set('price_min', searchState.priceMin);
    if (searchState.priceMax) params.set('price_max', searchState.priceMax);
    if (searchState.rating) params.set('rating', searchState.rating);
    if (searchState.inStock) params.set('in_stock', 'true');
    if (searchState.sortBy) params.set('sort', searchState.sortBy);
    params.set('page', searchState.page);
    
    // Show loading
    if (!append) {
        grid.innerHTML = `
            <div class="loading-products">
                <div class="spinner"></div>
                <span>جاري تحميل المنتجات...</span>
            </div>
        `;
    } else {
        // Add loader at bottom
        const loader = document.createElement('div');
        loader.className = 'loading-more';
        loader.innerHTML = '<div class="spinner"></div>';
        grid.appendChild(loader);
    }
    
    try {
        const response = await fetch(`/ecommerce/api/products/?${params.toString()}`);
        
        if (response.ok) {
            const data = await response.json();
            const products = data.results || data;
            
            searchState.hasMore = !!data.next;
            
            if (!append) {
                grid.innerHTML = '';
            } else {
                // Remove loader
                grid.querySelector('.loading-more')?.remove();
            }
            
            if (products.length === 0 && !append) {
                grid.innerHTML = `
                    <div class="no-products">
                        <div class="no-products-icon">📦</div>
                        <h3>لا توجد منتجات</h3>
                        <p>جرب تغيير الفلاتر أو البحث عن شيء آخر</p>
                    </div>
                `;
            } else {
                products.forEach(product => {
                    grid.appendChild(createProductCard(product));
                });
                
                // Initialize lazy loading for new images
                if (typeof initLazyLoading === 'function') {
                    initLazyLoading();
                }
            }
            
            // Update results count
            updateResultsCount(data.count || products.length);
        }
    } catch (error) {
        console.error('Error loading products:', error);
        if (!append) {
            grid.innerHTML = `
                <div class="error-message">
                    <p>حدث خطأ في تحميل المنتجات</p>
                    <button onclick="loadProducts()" class="retry-btn">حاول مرة أخرى</button>
                </div>
            `;
        }
    } finally {
        searchState.loading = false;
    }
}

function loadMoreProducts() {
    if (!searchState.hasMore || searchState.loading) return;
    
    searchState.page++;
    loadProducts(true);
}

function updateResultsCount(count) {
    const countEl = document.querySelector('.results-count');
    if (countEl) {
        countEl.textContent = `${count} منتج`;
    }
}

// =============================================
// PRODUCT CARD CREATION
// =============================================
function createProductCard(product) {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.dataset.productId = product.id;
    card.dataset.productName = product.name;
    card.dataset.productPrice = product.price;
    card.dataset.productImage = product.image;
    
    const wishlistActive = window.wishlist?.has(product.id) ? 'active' : '';
    
    card.innerHTML = `
        <div class="product-image-container">
            <a href="/ecommerce/product/${product.id}/">
                <img data-src="${product.image || '/static/ecommerce/images/placeholder.png'}" 
                     alt="${product.name}" 
                     class="product-image">
            </a>
            <div class="product-badges">
                ${product.discount ? `<span class="badge badge-sale">-${product.discount}%</span>` : ''}
                ${product.is_new ? `<span class="badge badge-new">جديد</span>` : ''}
            </div>
            <button class="product-wishlist ${wishlistActive}" 
                    onclick="toggleWishlist(${product.id}, this)">
                ❤️
            </button>
        </div>
        <div class="product-info">
            <div class="product-category">${product.category_name || ''}</div>
            <a href="/ecommerce/product/${product.id}/" class="product-title">${product.name}</a>
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
// MOBILE FILTERS
// =============================================
function openMobileFilters() {
    const sidebar = document.querySelector('.filters-sidebar');
    const overlay = document.querySelector('.filters-overlay');
    
    if (sidebar) {
        sidebar.classList.add('active');
    }
    if (overlay) {
        overlay.classList.add('active');
    }
    document.body.style.overflow = 'hidden';
}

function closeMobileFilters() {
    const sidebar = document.querySelector('.filters-sidebar');
    const overlay = document.querySelector('.filters-overlay');
    
    if (sidebar) {
        sidebar.classList.remove('active');
    }
    if (overlay) {
        overlay.classList.remove('active');
    }
    document.body.style.overflow = '';
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

function showToast(message, type = 'info') {
    if (window.TonyStore && window.TonyStore.showToast) {
        window.TonyStore.showToast(message, type);
    }
}

// =============================================
// INFINITE SCROLL FOR SEARCH RESULTS
// =============================================
function initInfiniteScroll() {
    window.addEventListener('scroll', () => {
        if (searchState.loading || !searchState.hasMore) return;
        
        const scrollPosition = window.innerHeight + window.scrollY;
        const pageHeight = document.documentElement.scrollHeight;
        
        if (scrollPosition >= pageHeight - 500) {
            loadMoreProducts();
        }
    });
}

// =============================================
// INITIALIZATION
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize instant search
    instantSearch = new InstantSearch('.search-input', {
        minChars: 2,
        debounceMs: 300,
        maxResults: 8
    });
    
    // Initialize filters
    const filtersContainer = document.querySelector('.filters-sidebar');
    if (filtersContainer) {
        const productFilters = new ProductFilters(filtersContainer);
        productFilters.loadFromURL();
        productFilters.onFilter = () => loadProducts();
    }
    
    // Initialize sort options
    initSortOptions();
    
    // Initialize infinite scroll
    initInfiniteScroll();
    
    // Mobile filter overlay click to close
    const overlay = document.querySelector('.filters-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeMobileFilters);
    }
    
    console.log('🔍 Search & Filters initialized');
});

// =============================================
// EXPORTS
// =============================================
window.Search = {
    InstantSearch,
    ProductFilters,
    loadProducts,
    openMobileFilters,
    closeMobileFilters,
    searchState
};
