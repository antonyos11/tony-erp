/**
 * Tony Store - Checkout Flow JavaScript
 * =======================================
 * Multi-step checkout for Egypt market
 */

// =============================================
// CHECKOUT STATE
// =============================================
const checkoutState = {
    step: 1,
    shippingAddress: null,
    billingAddress: null,
    shippingMethod: null,
    paymentMethod: null,
    couponCode: null,
    couponDiscount: 0,
    installmentPlan: null
};

// =============================================
// EGYPT GOVERNORATES DATA
// =============================================
const egyptGovernorates = [
    { id: 'cairo', name: 'القاهرة', shippingDays: 1, shippingCost: 30 },
    { id: 'giza', name: 'الجيزة', shippingDays: 1, shippingCost: 35 },
    { id: 'alexandria', name: 'الإسكندرية', shippingDays: 2, shippingCost: 40 },
    { id: 'dakahlia', name: 'الدقهلية', shippingDays: 2, shippingCost: 45 },
    { id: 'sharqia', name: 'الشرقية', shippingDays: 2, shippingCost: 45 },
    { id: 'qalyubia', name: 'القليوبية', shippingDays: 1, shippingCost: 35 },
    { id: 'gharbia', name: 'الغربية', shippingDays: 2, shippingCost: 45 },
    { id: 'monufia', name: 'المنوفية', shippingDays: 2, shippingCost: 45 },
    { id: 'beheira', name: 'البحيرة', shippingDays: 2, shippingCost: 45 },
    { id: 'kafr_el_sheikh', name: 'كفر الشيخ', shippingDays: 3, shippingCost: 50 },
    { id: 'damietta', name: 'دمياط', shippingDays: 2, shippingCost: 45 },
    { id: 'port_said', name: 'بور سعيد', shippingDays: 2, shippingCost: 45 },
    { id: 'ismailia', name: 'الإسماعيلية', shippingDays: 2, shippingCost: 45 },
    { id: 'suez', name: 'السويس', shippingDays: 2, shippingCost: 45 },
    { id: 'north_sinai', name: 'شمال سيناء', shippingDays: 4, shippingCost: 70 },
    { id: 'south_sinai', name: 'جنوب سيناء', shippingDays: 4, shippingCost: 70 },
    { id: 'red_sea', name: 'البحر الأحمر', shippingDays: 4, shippingCost: 65 },
    { id: 'fayoum', name: 'الفيوم', shippingDays: 2, shippingCost: 45 },
    { id: 'beni_suef', name: 'بني سويف', shippingDays: 2, shippingCost: 45 },
    { id: 'minya', name: 'المنيا', shippingDays: 3, shippingCost: 50 },
    { id: 'asyut', name: 'أسيوط', shippingDays: 3, shippingCost: 55 },
    { id: 'sohag', name: 'سوهاج', shippingDays: 3, shippingCost: 55 },
    { id: 'qena', name: 'قنا', shippingDays: 3, shippingCost: 55 },
    { id: 'luxor', name: 'الأقصر', shippingDays: 3, shippingCost: 55 },
    { id: 'aswan', name: 'أسوان', shippingDays: 4, shippingCost: 60 },
    { id: 'new_valley', name: 'الوادي الجديد', shippingDays: 5, shippingCost: 80 },
    { id: 'matrouh', name: 'مطروح', shippingDays: 4, shippingCost: 70 }
];

// =============================================
// STEP NAVIGATION
// =============================================
function goToStep(step) {
    // Validate current step before moving forward
    if (step > checkoutState.step && !validateStep(checkoutState.step)) {
        return false;
    }
    
    checkoutState.step = step;
    updateStepUI();
    scrollToTop();
    
    return true;
}

function nextStep() {
    if (checkoutState.step < 4) {
        goToStep(checkoutState.step + 1);
    }
}

function prevStep() {
    if (checkoutState.step > 1) {
        goToStep(checkoutState.step - 1);
    }
}

function validateStep(step) {
    switch (step) {
        case 1:
            return validateShippingAddress();
        case 2:
            return validateShippingMethod();
        case 3:
            return validatePaymentMethod();
        default:
            return true;
    }
}

function updateStepUI() {
    // Update progress indicators
    document.querySelectorAll('.progress-step').forEach((el, index) => {
        const stepNum = index + 1;
        el.classList.remove('active', 'completed');
        
        if (stepNum === checkoutState.step) {
            el.classList.add('active');
        } else if (stepNum < checkoutState.step) {
            el.classList.add('completed');
        }
    });
    
    document.querySelectorAll('.progress-connector').forEach((el, index) => {
        el.classList.toggle('completed', index < checkoutState.step - 1);
    });
    
    // Show/hide step content
    document.querySelectorAll('.checkout-step').forEach((el, index) => {
        el.style.display = (index + 1 === checkoutState.step) ? 'block' : 'none';
    });
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// =============================================
// ADDRESS MANAGEMENT
// =============================================
function validateShippingAddress() {
    const form = document.getElementById('shipping-address-form');
    if (!form) return false;
    
    const requiredFields = ['first_name', 'last_name', 'phone', 'governorate', 'city', 'address'];
    let isValid = true;
    
    requiredFields.forEach(field => {
        const input = form.querySelector(`[name="${field}"]`);
        if (!input || !input.value.trim()) {
            showFieldError(input, 'هذا الحقل مطلوب');
            isValid = false;
        } else {
            clearFieldError(input);
        }
    });
    
    // Validate Egypt phone number
    const phoneInput = form.querySelector('[name="phone"]');
    if (phoneInput && !validateEgyptPhone(phoneInput.value)) {
        showFieldError(phoneInput, 'رقم الهاتف غير صحيح');
        isValid = false;
    }
    
    if (isValid) {
        checkoutState.shippingAddress = {
            first_name: form.querySelector('[name="first_name"]').value,
            last_name: form.querySelector('[name="last_name"]').value,
            phone: form.querySelector('[name="phone"]').value,
            governorate: form.querySelector('[name="governorate"]').value,
            city: form.querySelector('[name="city"]').value,
            address: form.querySelector('[name="address"]').value,
            postal_code: form.querySelector('[name="postal_code"]')?.value || '',
            notes: form.querySelector('[name="notes"]')?.value || ''
        };
    }
    
    return isValid;
}

function validateEgyptPhone(phone) {
    // Remove spaces and leading zeros
    const cleaned = phone.replace(/\s/g, '').replace(/^0+/, '');
    
    // Egypt phone patterns: 10, 11, 12, 15 followed by 8 digits
    const pattern = /^(10|11|12|15)\d{8}$/;
    return pattern.test(cleaned);
}

function showFieldError(input, message) {
    if (!input) return;
    
    input.classList.add('error');
    
    let errorEl = input.parentElement.querySelector('.error-message');
    if (!errorEl) {
        errorEl = document.createElement('span');
        errorEl.className = 'error-message';
        input.parentElement.appendChild(errorEl);
    }
    errorEl.textContent = message;
}

function clearFieldError(input) {
    if (!input) return;
    
    input.classList.remove('error');
    
    const errorEl = input.parentElement.querySelector('.error-message');
    if (errorEl) {
        errorEl.remove();
    }
}

function populateGovernorates() {
    const select = document.querySelector('[name="governorate"]');
    if (!select) return;
    
    select.innerHTML = '<option value="">اختر المحافظة</option>';
    
    egyptGovernorates.forEach(gov => {
        const option = document.createElement('option');
        option.value = gov.id;
        option.textContent = gov.name;
        select.appendChild(option);
    });
    
    // Update shipping cost when governorate changes
    select.addEventListener('change', () => {
        updateShippingOptions();
    });
}

function selectSavedAddress(addressId) {
    document.querySelectorAll('.address-card').forEach(card => {
        card.classList.toggle('selected', card.dataset.id === addressId);
    });
    
    // TODO: Load address data
}

// =============================================
// SHIPPING METHODS
// =============================================
function validateShippingMethod() {
    if (!checkoutState.shippingMethod) {
        showToast('يرجى اختيار طريقة الشحن', 'warning');
        return false;
    }
    return true;
}

function selectShippingMethod(method) {
    checkoutState.shippingMethod = method;
    
    document.querySelectorAll('.shipping-option').forEach(el => {
        el.classList.toggle('selected', el.dataset.method === method);
    });
    
    updateOrderSummary();
}

function updateShippingOptions() {
    const governorate = document.querySelector('[name="governorate"]')?.value;
    if (!governorate) return;
    
    const govData = egyptGovernorates.find(g => g.id === governorate);
    if (!govData) return;
    
    // Update shipping options with governorate-specific data
    const standardOption = document.querySelector('[data-method="standard"]');
    if (standardOption) {
        const priceEl = standardOption.querySelector('.shipping-price');
        const descEl = standardOption.querySelector('.shipping-description');
        
        if (priceEl) {
            priceEl.textContent = govData.shippingCost === 0 ? 
                'مجاني' : 
                `${govData.shippingCost} ج.م`;
            priceEl.classList.toggle('free', govData.shippingCost === 0);
        }
        
        if (descEl) {
            descEl.textContent = `التوصيل خلال ${govData.shippingDays} ${govData.shippingDays === 1 ? 'يوم' : 'أيام'}`;
        }
    }
}

// =============================================
// PAYMENT METHODS
// =============================================
function validatePaymentMethod() {
    if (!checkoutState.paymentMethod) {
        showToast('يرجى اختيار طريقة الدفع', 'warning');
        return false;
    }
    return true;
}

function selectPaymentMethod(method) {
    checkoutState.paymentMethod = method;
    
    document.querySelectorAll('.payment-method').forEach(el => {
        el.classList.toggle('selected', el.dataset.method === method);
    });
    
    // Show/hide installment options
    const installmentSection = document.querySelector('.installment-options');
    if (installmentSection) {
        installmentSection.style.display = 
            (method === 'valu' || method === 'souhoola') ? 'block' : 'none';
    }
    
    // Show COD notice
    const codNotice = document.querySelector('.cod-notice');
    if (codNotice) {
        codNotice.style.display = method === 'cod' ? 'flex' : 'none';
    }
    
    updateOrderSummary();
}

function selectInstallmentPlan(months) {
    checkoutState.installmentPlan = months;
    
    document.querySelectorAll('.installment-plan').forEach(el => {
        el.classList.toggle('selected', parseInt(el.dataset.months) === months);
    });
    
    updateInstallmentAmount();
}

function updateInstallmentAmount() {
    const total = getCartTotal() + getShippingCost() - checkoutState.couponDiscount;
    const months = checkoutState.installmentPlan || 6;
    const monthlyAmount = total / months;
    
    document.querySelectorAll('.installment-plan').forEach(el => {
        const m = parseInt(el.dataset.months);
        const amountEl = el.querySelector('.installment-amount');
        if (amountEl) {
            amountEl.textContent = `${formatPrice(total / m)} ج.م/شهر`;
        }
    });
}

// =============================================
// COUPON CODE
// =============================================
async function applyCoupon() {
    const input = document.querySelector('.coupon-input');
    const code = input?.value.trim();
    
    if (!code) {
        showToast('أدخل كود الخصم', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/ecommerce/api/coupons/validate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ code })
        });
        
        if (response.ok) {
            const data = await response.json();
            checkoutState.couponCode = code;
            checkoutState.couponDiscount = data.discount;
            
            showCouponApplied(code, data.discount);
            updateOrderSummary();
            showToast(`تم تطبيق كود الخصم! وفرت ${formatPrice(data.discount)} ج.م 🎉`, 'success');
        } else {
            const error = await response.json();
            showToast(error.message || 'كود الخصم غير صالح', 'error');
        }
    } catch (error) {
        showToast('حدث خطأ في التحقق من الكود', 'error');
    }
}

function showCouponApplied(code, discount) {
    const section = document.querySelector('.coupon-section');
    if (!section) return;
    
    section.innerHTML = `
        <div class="coupon-applied">
            <div>
                <span class="coupon-code">🎟️ ${code}</span>
                <span> - خصم ${formatPrice(discount)} ج.م</span>
            </div>
            <button class="coupon-remove" onclick="removeCoupon()">إزالة</button>
        </div>
    `;
}

function removeCoupon() {
    checkoutState.couponCode = null;
    checkoutState.couponDiscount = 0;
    
    const section = document.querySelector('.coupon-section');
    if (section) {
        section.innerHTML = `
            <div class="coupon-input-group">
                <input type="text" class="coupon-input" placeholder="كود الخصم">
                <button class="coupon-btn" onclick="applyCoupon()">تطبيق</button>
            </div>
        `;
    }
    
    updateOrderSummary();
    showToast('تم إزالة كود الخصم', 'info');
}

// =============================================
// ORDER SUMMARY
// =============================================
function updateOrderSummary() {
    const subtotal = getCartTotal();
    const shipping = getShippingCost();
    const discount = checkoutState.couponDiscount;
    const vat = (subtotal - discount) * 0.14; // Egypt VAT
    const total = subtotal + shipping - discount + vat;
    
    // Update summary display
    updateElement('.summary-subtotal', formatPrice(subtotal) + ' ج.م');
    updateElement('.summary-shipping', shipping === 0 ? 'مجاني' : formatPrice(shipping) + ' ج.م');
    updateElement('.summary-discount', discount > 0 ? `-${formatPrice(discount)} ج.م` : '0 ج.م');
    updateElement('.summary-vat', formatPrice(vat) + ' ج.م');
    updateElement('.summary-total-value', formatPrice(total) + ' ج.م');
    
    // Show/hide discount line
    const discountLine = document.querySelector('.summary-line.discount');
    if (discountLine) {
        discountLine.style.display = discount > 0 ? 'flex' : 'none';
    }
    
    // Update installment amounts
    updateInstallmentAmount();
}

function updateElement(selector, value) {
    const el = document.querySelector(selector);
    if (el) el.textContent = value;
}

function getCartTotal() {
    if (window.TonyStore && window.TonyStore.cart) {
        return window.TonyStore.cart.getTotal();
    }
    // Fallback: read from DOM
    const totalEl = document.querySelector('[data-cart-total]');
    return parseFloat(totalEl?.dataset.cartTotal) || 0;
}

function getShippingCost() {
    if (!checkoutState.shippingAddress?.governorate) return 0;
    
    const govData = egyptGovernorates.find(g => g.id === checkoutState.shippingAddress.governorate);
    
    // Free shipping for orders over 500 EGP
    const subtotal = getCartTotal();
    if (subtotal >= 500) return 0;
    
    return govData?.shippingCost || 45;
}

// =============================================
// PLACE ORDER
// =============================================
async function placeOrder() {
    // Final validation
    if (!validateStep(1) || !validateStep(2) || !validateStep(3)) {
        showToast('يرجى إكمال جميع البيانات المطلوبة', 'error');
        return;
    }
    
    const orderBtn = document.querySelector('.place-order-btn');
    if (orderBtn) {
        orderBtn.disabled = true;
        orderBtn.classList.add('loading');
        orderBtn.innerHTML = '<div class="spinner"></div> جاري تأكيد الطلب...';
    }
    
    try {
        const orderData = {
            shipping_address: checkoutState.shippingAddress,
            shipping_method: checkoutState.shippingMethod,
            payment_method: checkoutState.paymentMethod,
            coupon_code: checkoutState.couponCode,
            installment_plan: checkoutState.installmentPlan,
            notes: document.querySelector('[name="order_notes"]')?.value || ''
        };
        
        const response = await fetch('/ecommerce/api/orders/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(orderData)
        });
        
        if (response.ok) {
            const order = await response.json();
            
            // Clear cart
            if (window.TonyStore && window.TonyStore.cart) {
                window.TonyStore.cart.clear();
            }
            
            // Handle payment redirect if needed
            if (order.payment_url) {
                window.location.href = order.payment_url;
            } else {
                // Show confirmation
                showOrderConfirmation(order);
            }
        } else {
            const error = await response.json();
            showToast(error.message || 'حدث خطأ أثناء إتمام الطلب', 'error');
        }
    } catch (error) {
        showToast('حدث خطأ في الاتصال', 'error');
    } finally {
        if (orderBtn) {
            orderBtn.disabled = false;
            orderBtn.classList.remove('loading');
            orderBtn.innerHTML = '🛒 تأكيد الطلب';
        }
    }
}

function showOrderConfirmation(order) {
    const main = document.querySelector('.checkout-main');
    if (!main) return;
    
    main.innerHTML = `
        <div class="order-confirmation">
            <div class="confirmation-icon">✓</div>
            <h2 class="confirmation-title">تم استلام طلبك بنجاح! 🎉</h2>
            <p class="confirmation-message">
                شكراً لك! سنقوم بإرسال رسالة تأكيد إلى بريدك الإلكتروني.
            </p>
            <div class="order-number">
                رقم الطلب: ${order.order_number}
            </div>
            <div class="confirmation-actions">
                <a href="/ecommerce/orders/${order.id}/" class="confirmation-btn primary">
                    تتبع الطلب
                </a>
                <a href="/ecommerce/" class="confirmation-btn secondary">
                    متابعة التسوق
                </a>
            </div>
        </div>
    `;
    
    // Hide sidebar
    const sidebar = document.querySelector('.checkout-sidebar');
    if (sidebar) {
        sidebar.style.display = 'none';
    }
    
    // Hide progress
    const progress = document.querySelector('.checkout-progress');
    if (progress) {
        progress.style.display = 'none';
    }
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
    // Initialize governorates dropdown
    populateGovernorates();
    
    // Initialize step UI
    updateStepUI();
    
    // Initialize order summary
    updateOrderSummary();
    
    // Phone input formatting
    const phoneInput = document.querySelector('[name="phone"]');
    if (phoneInput) {
        phoneInput.addEventListener('input', (e) => {
            // Format as user types
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 11) value = value.slice(0, 11);
            
            // Add spaces for readability
            if (value.length > 3) {
                value = value.slice(0, 3) + ' ' + value.slice(3);
            }
            if (value.length > 8) {
                value = value.slice(0, 8) + ' ' + value.slice(8);
            }
            
            e.target.value = value;
        });
    }
    
    console.log('💳 Checkout initialized');
});

// =============================================
// EXPORTS
// =============================================
window.Checkout = {
    goToStep,
    nextStep,
    prevStep,
    selectShippingMethod,
    selectPaymentMethod,
    selectInstallmentPlan,
    applyCoupon,
    removeCoupon,
    placeOrder,
    egyptGovernorates
};
