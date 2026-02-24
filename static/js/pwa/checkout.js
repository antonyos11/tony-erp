/**
 * PWA Checkout JavaScript - Tony ERP
 * يدير سلة التسوق وعملية الدفع على الجوال
 */
(function () {
    'use strict';

    const CheckoutManager = {
        cart: [],
        total: 0,

        init() {
            this._loadCart();
            this._setupListeners();
            this._renderCart();
            this._updateBadge();
        },

        // ---- إدارة السلة ----

        _loadCart() {
            try {
                this.cart = JSON.parse(localStorage.getItem('erp_cart') || '[]');
            } catch (e) {
                this.cart = [];
            }
            this._calcTotal();
        },

        _saveCart() {
            localStorage.setItem('erp_cart', JSON.stringify(this.cart));
        },

        _calcTotal() {
            this.total = this.cart.reduce((s, i) => s + i.price * i.qty, 0);
        },

        addItem(id, name, price, qty = 1) {
            const existing = this.cart.find(i => i.id === id);
            if (existing) {
                existing.qty += qty;
            } else {
                this.cart.push({ id, name, price: parseFloat(price), qty });
            }
            this._calcTotal();
            this._saveCart();
            this._renderCart();
            this._updateBadge();
            this._toast(`تمت إضافة "${name}" للسلة ✓`);
        },

        removeItem(id) {
            this.cart = this.cart.filter(i => i.id !== id);
            this._calcTotal();
            this._saveCart();
            this._renderCart();
            this._updateBadge();
        },

        updateQty(id, qty) {
            qty = parseInt(qty);
            if (qty <= 0) return this.removeItem(id);
            const item = this.cart.find(i => i.id === id);
            if (item) {
                item.qty = qty;
                this._calcTotal();
                this._saveCart();
                this._renderCart();
            }
        },

        clearCart() {
            if (!confirm('هل تريد مسح السلة؟')) return;
            this.cart = [];
            this.total = 0;
            this._saveCart();
            this._renderCart();
            this._updateBadge();
        },

        // ---- الواجهة ----

        _renderCart() {
            const container = document.getElementById('cart-items');
            const totalEl = document.getElementById('cart-total');
            const countEl = document.getElementById('cart-count');

            if (container) {
                if (!this.cart.length) {
                    container.innerHTML = `
                        <div class="text-center py-5 text-muted">
                            <i class="fas fa-shopping-cart fa-3x mb-3"></i>
                            <p>السلة فارغة</p>
                            <a href="/products/" class="btn btn-primary btn-sm">تصفح المنتجات</a>
                        </div>`;
                } else {
                    container.innerHTML = this.cart.map(item => `
                        <div class="d-flex align-items-center gap-2 p-2 border-bottom">
                            <div class="flex-grow-1">
                                <div class="fw-semibold">${item.name}</div>
                                <div class="text-primary">${(item.price * item.qty).toFixed(2)} ر.س</div>
                            </div>
                            <div class="d-flex align-items-center gap-1">
                                <button class="btn btn-sm btn-outline-secondary px-2"
                                    onclick="CheckoutManager.updateQty('${item.id}', ${item.qty - 1})">−</button>
                                <span class="fw-bold mx-1">${item.qty}</span>
                                <button class="btn btn-sm btn-outline-secondary px-2"
                                    onclick="CheckoutManager.updateQty('${item.id}', ${item.qty + 1})">+</button>
                            </div>
                            <button class="btn btn-sm btn-outline-danger"
                                onclick="CheckoutManager.removeItem('${item.id}')">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>`).join('');
                }
            }
            if (totalEl) totalEl.textContent = this.total.toFixed(2) + ' ر.س';
            if (countEl) countEl.textContent = this.cart.reduce((s, i) => s + i.qty, 0);
        },

        _updateBadge() {
            const badge = document.getElementById('cart-badge');
            if (!badge) return;
            const count = this.cart.reduce((s, i) => s + i.qty, 0);
            badge.textContent = count;
            badge.style.display = count ? 'inline-block' : 'none';
        },

        _toast(msg) {
            const el = document.createElement('div');
            el.className = 'alert alert-success';
            el.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);z-index:9999;white-space:nowrap;min-width:220px;text-align:center;';
            el.textContent = msg;
            document.body.appendChild(el);
            setTimeout(() => el.remove(), 2500);
        },

        // ---- الدفع ----

        _setupListeners() {
            const btn = document.getElementById('checkout-btn');
            if (btn) btn.addEventListener('click', () => this.processCheckout());

            document.addEventListener('click', e => {
                const addBtn = e.target.closest('[data-add-to-cart]');
                if (addBtn) {
                    e.preventDefault();
                    const { productId, name, price } = addBtn.dataset;
                    this.addItem(productId, name, price);
                }
            });
        },

        async processCheckout() {
            if (!this.cart.length) return alert('السلة فارغة!');

            const btn = document.getElementById('checkout-btn');
            if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> جاري المعالجة...'; }

            try {
                const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
                const res = await fetch('/api/orders/create/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                    body: JSON.stringify({ items: this.cart, total: this.total })
                });

                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const data = await res.json();
                this.cart = []; this._saveCart();
                window.location.href = `/orders/${data.order_id}/success/`;
            } catch (e) {
                console.error('Checkout error:', e);
                alert('حدث خطأ أثناء معالجة الطلب. يرجى المحاولة مرة أخرى.');
                if (btn) { btn.disabled = false; btn.textContent = 'إتمام الطلب'; }
            }
        }
    };

    document.addEventListener('DOMContentLoaded', () => CheckoutManager.init());
    window.CheckoutManager = CheckoutManager;
})();
