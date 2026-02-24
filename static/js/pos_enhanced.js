/**
 * POS Enhanced Features - الميزات المحسنة لنقطة البيع
 * - اختصارات لوحة المفاتيح
 * - الطلبات المعلقة
 * - المنتجات المفضلة
 * - الأكثر مبيعاً
 * - ماسح الباركود المحسن
 * - الدفع السريع
 */

class POSEnhanced {
    constructor(options = {}) {
        this.orderId = options.orderId;
        this.cart = [];
        this.selectedItemIndex = -1;
        this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        this.barcodeBuffer = '';
        this.barcodeTimeout = null;
        
        this.init();
    }

    init() {
        this.setupKeyboardShortcuts();
        this.setupBarcodeScanner();
        this.setupQuickPayButtons();
        this.loadFavorites();
        this.loadHeldOrders();
        this.setupCartItemActions();
        this.setupSoundNotifications();
    }

    // =========== اختصارات لوحة المفاتيح ===========
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // تجاهل إذا كنا داخل حقل إدخال (إلا للمفاتيح الخاصة)
            const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName);
            
            switch(e.key) {
                case 'F2':
                    e.preventDefault();
                    this.focusSearch();
                    break;
                case 'F3':
                    e.preventDefault();
                    this.newOrder();
                    break;
                case 'F8':
                    e.preventDefault();
                    this.openPaymentModal();
                    break;
                case 'F9':
                    e.preventDefault();
                    this.holdCurrentOrder();
                    break;
                case 'F10':
                    e.preventDefault();
                    this.showHeldOrdersModal();
                    break;
                case 'Escape':
                    if (!isInput) {
                        e.preventDefault();
                        this.clearCart();
                    }
                    break;
                case '+':
                case '=':
                    if (!isInput && this.selectedItemIndex >= 0) {
                        e.preventDefault();
                        this.changeSelectedQuantity(1);
                    }
                    break;
                case '-':
                    if (!isInput && this.selectedItemIndex >= 0) {
                        e.preventDefault();
                        this.changeSelectedQuantity(-1);
                    }
                    break;
                case 'Delete':
                    if (!isInput && this.selectedItemIndex >= 0) {
                        e.preventDefault();
                        this.deleteSelectedItem();
                    }
                    break;
                case 'F1':
                    e.preventDefault();
                    this.selectCategory(0);
                    break;
                case 'F4':
                    e.preventDefault();
                    this.selectCategory(1);
                    break;
                case 'F5':
                    e.preventDefault();
                    this.selectCategory(2);
                    break;
                case 'F6':
                    e.preventDefault();
                    this.selectCategory(3);
                    break;
                case 'F7':
                    e.preventDefault();
                    this.selectCategory(4);
                    break;
            }

            // Ctrl shortcuts
            if (e.ctrlKey) {
                switch(e.key.toLowerCase()) {
                    case 'p':
                        e.preventDefault();
                        this.printReceipt();
                        break;
                    case 'd':
                        e.preventDefault();
                        this.openDiscountModal();
                        break;
                    case 'f':
                        e.preventDefault();
                        this.toggleFavoriteProduct();
                        break;
                }
            }
        });
    }

    // =========== ماسح الباركود المحسن ===========
    setupBarcodeScanner() {
        // ماسح الباركود يرسل الأحرف بسرعة ثم Enter
        document.addEventListener('keypress', (e) => {
            if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
            
            if (e.key === 'Enter') {
                if (this.barcodeBuffer.length >= 3) {
                    this.handleBarcodeScan(this.barcodeBuffer);
                }
                this.barcodeBuffer = '';
                clearTimeout(this.barcodeTimeout);
                return;
            }

            this.barcodeBuffer += e.key;
            
            // مسح البافر بعد 100ms من عدم الكتابة
            clearTimeout(this.barcodeTimeout);
            this.barcodeTimeout = setTimeout(() => {
                this.barcodeBuffer = '';
            }, 100);
        });
    }

    handleBarcodeScan(barcode) {
        console.log('Barcode scanned:', barcode);
        
        fetch(`/pos/api/product-lookup/?q=${encodeURIComponent(barcode)}`)
            .then(r => r.json())
            .then(data => {
                if (data.results && data.results.length > 0) {
                    const product = data.results[0];
                    this.addToCart(product);
                    this.playSound('add');
                    this.showNotification(`✅ ${product.name}`, 'success');
                } else {
                    this.playSound('error');
                    this.showNotification('❌ منتج غير موجود', 'error');
                }
            })
            .catch(err => {
                this.playSound('error');
                console.error('Barcode lookup error:', err);
            });
    }

    // =========== الطلبات المعلقة ===========
    async holdCurrentOrder() {
        if (this.cart.length === 0) {
            this.showNotification('السلة فارغة!', 'warning');
            return;
        }

        const note = prompt('ملاحظة للطلب المعلق (اختياري):');
        const customerName = prompt('اسم العميل (اختياري):');

        try {
            const response = await fetch('/pos/api/hold-order/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    items: this.cart,
                    customer_name: customerName || '',
                    note: note || '',
                    total: this.calculateTotal()
                })
            });

            const data = await response.json();
            if (data.success) {
                this.showNotification('✅ تم حفظ الطلب المعلق', 'success');
                this.playSound('hold');
                this.clearCart();
                this.loadHeldOrders();
            } else {
                this.showNotification(data.error || 'خطأ', 'error');
            }
        } catch (err) {
            console.error('Hold order error:', err);
            this.showNotification('خطأ في حفظ الطلب', 'error');
        }
    }

    async loadHeldOrders() {
        try {
            const response = await fetch('/pos/api/held-orders/');
            const data = await response.json();
            
            const container = document.getElementById('heldOrdersList');
            if (!container) return;

            if (data.orders && data.orders.length > 0) {
                container.innerHTML = data.orders.map(order => `
                    <div class="held-order-item" data-id="${order.id}">
                        <div class="held-order-info">
                            <strong>${order.customer_name}</strong>
                            <span class="text-muted small">${order.items_count} منتج</span>
                            <span class="badge bg-primary">${order.total.toFixed(2)}</span>
                        </div>
                        <div class="held-order-time small text-muted">${order.created_at}</div>
                        <div class="held-order-actions">
                            <button class="btn btn-sm btn-success restore-held" data-id="${order.id}">
                                <i class="bi bi-arrow-clockwise"></i>
                            </button>
                            <button class="btn btn-sm btn-danger delete-held" data-id="${order.id}">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                `).join('');

                // إضافة أحداث الأزرار
                container.querySelectorAll('.restore-held').forEach(btn => {
                    btn.addEventListener('click', () => this.restoreHeldOrder(btn.dataset.id));
                });
                container.querySelectorAll('.delete-held').forEach(btn => {
                    btn.addEventListener('click', () => this.deleteHeldOrder(btn.dataset.id));
                });
            } else {
                container.innerHTML = '<div class="text-center text-muted py-3">لا توجد طلبات معلقة</div>';
            }
            
            // تحديث العداد
            const badge = document.getElementById('heldOrdersBadge');
            if (badge) {
                badge.textContent = data.orders?.length || 0;
                badge.style.display = data.orders?.length > 0 ? 'inline-block' : 'none';
            }
        } catch (err) {
            console.error('Load held orders error:', err);
        }
    }

    async restoreHeldOrder(holdId) {
        try {
            const response = await fetch(`/pos/api/held-order/${holdId}/restore/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            const data = await response.json();
            if (data.success) {
                this.cart = data.items;
                this.renderCart();
                this.showNotification('✅ تم استعادة الطلب', 'success');
                this.playSound('restore');
                this.loadHeldOrders();
                
                // إغلاق المودال
                const modal = bootstrap.Modal.getInstance(document.getElementById('heldOrdersModal'));
                if (modal) modal.hide();
            }
        } catch (err) {
            console.error('Restore held order error:', err);
        }
    }

    async deleteHeldOrder(holdId) {
        if (!confirm('هل تريد حذف هذا الطلب المعلق؟')) return;

        try {
            const response = await fetch(`/pos/api/held-order/${holdId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            const data = await response.json();
            if (data.success) {
                this.showNotification('🗑️ تم حذف الطلب', 'info');
                this.loadHeldOrders();
            }
        } catch (err) {
            console.error('Delete held order error:', err);
        }
    }

    showHeldOrdersModal() {
        const modal = document.getElementById('heldOrdersModal');
        if (modal) {
            new bootstrap.Modal(modal).show();
        }
    }

    // =========== المنتجات المفضلة ===========
    async loadFavorites() {
        try {
            const response = await fetch('/pos/api/favorites/');
            const data = await response.json();
            
            const container = document.getElementById('favoritesGrid');
            if (!container) return;

            if (data.products && data.products.length > 0) {
                container.innerHTML = data.products.map(p => this.renderProductCard(p, true)).join('');
                this.bindProductCards(container);
            } else {
                container.innerHTML = '<div class="text-center text-muted py-3">لا توجد مفضلات. اضغط Ctrl+F لإضافة منتج.</div>';
            }
        } catch (err) {
            console.error('Load favorites error:', err);
        }
    }

    async toggleFavoriteProduct(productId = null) {
        const id = productId || this.getSelectedProductId();
        if (!id) {
            this.showNotification('اختر منتجاً أولاً', 'warning');
            return;
        }

        try {
            const response = await fetch('/pos/api/toggle-favorite/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ product_id: id })
            });

            const data = await response.json();
            if (data.success) {
                const icon = data.is_favorite ? '⭐' : '☆';
                this.showNotification(`${icon} ${data.message}`, 'success');
                this.loadFavorites();
            }
        } catch (err) {
            console.error('Toggle favorite error:', err);
        }
    }

    // =========== الدفع السريع ===========
    async setupQuickPayButtons() {
        try {
            const response = await fetch('/pos/api/quick-amounts/');
            const data = await response.json();
            
            const container = document.getElementById('quickPayButtons');
            if (!container || !data.buttons) return;

            container.innerHTML = data.buttons.map(btn => `
                <button class="btn btn-outline-success quick-pay-btn" data-amount="${btn.amount}">
                    ${btn.label}
                </button>
            `).join('');

            container.querySelectorAll('.quick-pay-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const input = document.getElementById('paymentAmount');
                    if (input) {
                        const current = parseFloat(input.value) || 0;
                        input.value = (current + parseFloat(btn.dataset.amount)).toFixed(2);
                        this.updateChange();
                    }
                });
            });
        } catch (err) {
            console.error('Load quick amounts error:', err);
        }
    }

    updateChange() {
        const payInput = document.getElementById('paymentAmount');
        const changeDisplay = document.getElementById('changeAmount');
        const total = this.calculateTotal();
        
        if (payInput && changeDisplay) {
            const paid = parseFloat(payInput.value) || 0;
            const change = paid - total;
            changeDisplay.textContent = change >= 0 ? change.toFixed(2) : '0.00';
            changeDisplay.classList.toggle('text-danger', change < 0);
        }
    }

    // =========== تعديلات السلة السريعة ===========
    setupCartItemActions() {
        document.addEventListener('click', (e) => {
            const cartItem = e.target.closest('.cart-item');
            if (cartItem) {
                // تحديد العنصر
                document.querySelectorAll('.cart-item').forEach(item => {
                    item.classList.remove('selected');
                });
                cartItem.classList.add('selected');
                this.selectedItemIndex = parseInt(cartItem.dataset.index);
            }
        });

        // زر تعديل السعر
        document.addEventListener('click', async (e) => {
            if (e.target.closest('.edit-price-btn')) {
                const item = e.target.closest('.cart-item');
                const index = parseInt(item.dataset.index);
                const currentPrice = this.cart[index].price;
                const newPrice = prompt('أدخل السعر الجديد:', currentPrice);
                
                if (newPrice !== null && !isNaN(parseFloat(newPrice))) {
                    this.cart[index].price = parseFloat(newPrice);
                    this.renderCart();
                    this.showNotification('تم تحديث السعر', 'success');
                }
            }
        });

        // زر خصم سريع
        document.addEventListener('click', async (e) => {
            if (e.target.closest('.quick-discount-btn')) {
                const item = e.target.closest('.cart-item');
                const index = parseInt(item.dataset.index);
                const discountPercent = prompt('نسبة الخصم %:', '10');
                
                if (discountPercent !== null && !isNaN(parseFloat(discountPercent))) {
                    const discount = parseFloat(discountPercent) / 100;
                    this.cart[index].price *= (1 - discount);
                    this.renderCart();
                    this.showNotification(`تم تطبيق خصم ${discountPercent}%`, 'success');
                }
            }
        });
    }

    // =========== الأصوات ===========
    setupSoundNotifications() {
        this.sounds = {
            add: '/static/sounds/pos-add.mp3',
            error: '/static/sounds/pos-error.mp3',
            success: '/static/sounds/pos-success.mp3',
            hold: '/static/sounds/pos-hold.mp3',
            restore: '/static/sounds/pos-restore.mp3',
        };
    }

    playSound(type) {
        const soundUrl = this.sounds[type];
        if (soundUrl) {
            const audio = new Audio(soundUrl);
            audio.volume = 0.3;
            audio.play().catch(() => {});
        }
    }

    // =========== الإشعارات ===========
    showNotification(message, type = 'info') {
        // إنشاء toast notification
        const container = document.getElementById('posNotifications') || this.createNotificationContainer();
        
        const toast = document.createElement('div');
        toast.className = `pos-toast pos-toast-${type}`;
        toast.innerHTML = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'posNotifications';
        container.className = 'pos-notifications';
        document.body.appendChild(container);
        return container;
    }

    // =========== مساعدات ===========
    focusSearch() {
        const searchInput = document.getElementById('productSearch');
        if (searchInput) searchInput.focus();
    }

    newOrder() {
        window.location.href = '/pos/order/new/';
    }

    openPaymentModal() {
        const modal = document.getElementById('paymentModal');
        if (modal) new bootstrap.Modal(modal).show();
    }

    openDiscountModal() {
        const modal = document.getElementById('discountModal');
        if (modal) new bootstrap.Modal(modal).show();
    }

    clearCart() {
        if (this.cart.length === 0) return;
        if (confirm('هل تريد إفراغ السلة؟')) {
            this.cart = [];
            this.renderCart();
        }
    }

    selectCategory(index) {
        const tabs = document.querySelectorAll('.category-tab');
        if (tabs[index]) tabs[index].click();
    }

    printReceipt() {
        if (this.orderId) {
            window.open(`/pos/order/${this.orderId}/receipt/?auto=1`, '_blank');
        }
    }

    changeSelectedQuantity(delta) {
        if (this.selectedItemIndex >= 0 && this.cart[this.selectedItemIndex]) {
            this.cart[this.selectedItemIndex].qty += delta;
            if (this.cart[this.selectedItemIndex].qty <= 0) {
                this.cart.splice(this.selectedItemIndex, 1);
                this.selectedItemIndex = -1;
            }
            this.renderCart();
        }
    }

    deleteSelectedItem() {
        if (this.selectedItemIndex >= 0) {
            this.cart.splice(this.selectedItemIndex, 1);
            this.selectedItemIndex = -1;
            this.renderCart();
        }
    }

    getSelectedProductId() {
        const selected = document.querySelector('.product-card.selected');
        return selected ? selected.dataset.id : null;
    }

    async addToCart(product) {
        const productId = String(product.id);
        const price = parseFloat(product.price) || 0;
        const name = product.name || '';
        
        console.log('POSEnhanced addToCart:', { id: productId, name: name, price: price });
        
        const existing = this.cart.find(item => String(item.id) === productId);
        if (existing) {
            // زيادة الكمية - إذا كان له lineId أرسل للخادم
            if (existing.lineId) {
                try {
                    const response = await fetch(`/pos/order/${this.orderId}/line/${existing.lineId}/update-qty/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.csrfToken || window.csrfToken
                        },
                        body: JSON.stringify({ quantity: existing.qty + 1 })
                    });
                    const data = await response.json();
                    if (data.ok) {
                        existing.qty++;
                        this.showNotification('تم زيادة الكمية ✨', 'success');
                    } else {
                        this.showNotification(data.error || 'خطأ', 'error');
                        return;
                    }
                } catch (err) {
                    console.error('Update qty error:', err);
                    this.showNotification('خطأ في الاتصال', 'error');
                    return;
                }
            } else {
                existing.qty++;
            }
        } else {
            // إضافة منتج جديد - أرسل للخادم
            try {
                const response = await fetch(`/pos/order/${this.orderId}/add-line/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': this.csrfToken || window.csrfToken
                    },
                    body: `code=${encodeURIComponent(productId)}&qty=1`
                });
                const data = await response.json();
                console.log('Add line response:', data);
                
                if (response.ok && data.ok) {
                    this.cart.push({
                        id: productId,
                        lineId: data.line_id,
                        name: name,
                        price: price,
                        qty: 1,
                        isFromDB: true
                    });
                    this.showNotification('تم إضافة ' + name + ' ✨', 'success');
                } else {
                    this.showNotification(data.error || 'خطأ في الإضافة', 'error');
                    return;
                }
            } catch (err) {
                console.error('Add line error:', err);
                this.showNotification('خطأ في الاتصال بالخادم', 'error');
                return;
            }
        }
        this.renderCart();
    }

    calculateTotal() {
        return this.cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    }

    renderProductCard(product, isFavorite = false) {
        return `
            <div class="product-card ${isFavorite ? 'favorite' : ''}" 
                 data-id="${product.id}" 
                 data-name="${product.name}" 
                 data-price="${product.price}">
                ${product.image ? `<img src="${product.image}" alt="${product.name}">` : 
                  '<div class="d-flex align-items-center justify-content-center" style="height:60px;"><i class="bi bi-box-seam fs-1 text-muted"></i></div>'}
                <div class="name" title="${product.name}">${product.name}</div>
                <div class="price">${product.price.toFixed(2)}</div>
                ${isFavorite ? '<i class="bi bi-star-fill text-warning favorite-star"></i>' : ''}
            </div>
        `;
    }

    bindProductCards(container) {
        container.querySelectorAll('.product-card').forEach(card => {
            card.addEventListener('click', () => {
                this.addToCart({
                    id: card.dataset.id,
                    name: card.dataset.name,
                    price: parseFloat(card.dataset.price)
                });
                this.playSound('add');
            });
        });
    }

    renderCart() {
        const container = document.getElementById('cartItems');
        const emptyMsg = document.getElementById('emptyCart');
        
        if (!container) return;

        if (this.cart.length === 0) {
            if (emptyMsg) emptyMsg.style.display = 'block';
            container.innerHTML = '';
            if (emptyMsg) container.appendChild(emptyMsg);
        } else {
            if (emptyMsg) emptyMsg.style.display = 'none';
            container.innerHTML = this.cart.map((item, index) => `
                <div class="cart-item ${index === this.selectedItemIndex ? 'selected' : ''}" data-index="${index}">
                    <div class="info">
                        <div class="name">${item.name}</div>
                        <div class="price">${item.price.toFixed(2)} × ${item.qty}</div>
                    </div>
                    <div class="qty-controls">
                        <button class="qty-btn minus" onclick="posEnhanced.changeItemQty(${index}, -1)">-</button>
                        <span>${item.qty}</span>
                        <button class="qty-btn plus" onclick="posEnhanced.changeItemQty(${index}, 1)">+</button>
                    </div>
                    <div class="item-actions">
                        <button class="btn btn-sm btn-link edit-price-btn" title="تعديل السعر">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-link quick-discount-btn" title="خصم سريع">
                            <i class="bi bi-percent"></i>
                        </button>
                    </div>
                    <span class="fw-bold">${(item.price * item.qty).toFixed(2)}</span>
                </div>
            `).join('');
        }
        this.updateTotals();
    }

    changeItemQty(index, delta) {
        this.cart[index].qty += delta;
        if (this.cart[index].qty <= 0) {
            this.cart.splice(index, 1);
        }
        this.renderCart();
    }

    updateTotals() {
        const subtotal = this.calculateTotal();
        const taxRate = 0.15;
        const tax = subtotal * taxRate;
        const total = subtotal + tax;

        const subtotalEl = document.getElementById('subtotal');
        const taxEl = document.getElementById('tax');
        const totalEl = document.getElementById('grandTotal');

        if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
        if (taxEl) taxEl.textContent = tax.toFixed(2);
        if (totalEl) totalEl.textContent = total.toFixed(2);

        // تمكين/تعطيل أزرار الدفع
        const payBtn = document.getElementById('payBtn');
        if (payBtn) payBtn.disabled = this.cart.length === 0;

        window.posTotal = total;
    }
}

// CSS للميزات المحسنة
const posEnhancedStyles = `
<style>
.pos-notifications {
    position: fixed;
    top: 80px;
    left: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.pos-toast {
    padding: 12px 20px;
    border-radius: 8px;
    background: #333;
    color: white;
    font-size: 14px;
    animation: slideIn 0.3s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.pos-toast-success { background: #28a745; }
.pos-toast-error { background: #dc3545; }
.pos-toast-warning { background: #ffc107; color: #333; }
.pos-toast-info { background: #17a2b8; }

.pos-toast.fade-out {
    animation: slideOut 0.3s ease forwards;
}

@keyframes slideIn {
    from { transform: translateX(-100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

@keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(-100%); opacity: 0; }
}

.cart-item.selected {
    border: 2px solid var(--pos-primary, #667eea) !important;
    background: #f0f4ff !important;
}

.cart-item .item-actions {
    display: none;
}

.cart-item:hover .item-actions {
    display: flex;
    gap: 4px;
}

.product-card.favorite .favorite-star {
    position: absolute;
    top: 5px;
    left: 5px;
}

.product-card {
    position: relative;
}

.held-order-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px;
    border-bottom: 1px solid #eee;
}

.held-order-item:last-child {
    border-bottom: none;
}

.held-order-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.quick-pay-btn {
    padding: 8px 16px;
    font-size: 14px;
    margin: 2px;
}

#quickPayButtons {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 10px;
}

/* اختصارات لوحة المفاتيح */
.keyboard-shortcuts {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    font-size: 13px;
}

.shortcut-item {
    display: flex;
    justify-content: space-between;
    padding: 4px 8px;
    background: #f8f9fa;
    border-radius: 4px;
}

.shortcut-key {
    background: #667eea;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: monospace;
}
</style>
`;

// إضافة الأنماط للصفحة
document.head.insertAdjacentHTML('beforeend', posEnhancedStyles);

// تهيئة عند تحميل الصفحة
let posEnhanced;
document.addEventListener('DOMContentLoaded', function() {
    posEnhanced = new POSEnhanced({
        orderId: window.posOrderId
    });
    window.posEnhanced = posEnhanced;
});
