// Enhanced Invoice Form JavaScript
class InvoiceFormManager {
    constructor() {
        this.form = document.getElementById('invoiceForm');
        this.customerSelect = document.getElementById('customer');
        this.paymentMethodSelect = document.getElementById('payment_method');
        this.paymentReferenceSection = document.getElementById('payment_reference_section');
        this.previewElements = this.getPreviewElements();

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupFormValidation();
        this.setupAutoComplete();
        this.setupKeyboardShortcuts();
        this.loadDraftData();
        this.setDefaultValues();
        this.updatePreview();
    }

    getPreviewElements() {
        return {
            customer: document.getElementById('previewCustomer'),
            dueDate: document.getElementById('previewDueDate'),
            discount: document.getElementById('previewDiscount'),
            paymentMethod: document.getElementById('previewPaymentMethod'),
            reference: document.getElementById('previewReference'),
            referenceRow: document.getElementById('previewReferenceRow'),
            taxInclusive: document.getElementById('previewTaxInclusive'),
            withholding: document.getElementById('previewWithholding')
        };
    }

    setupEventListeners() {
        // Form input listeners
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('change', () => this.updatePreview());
            input.addEventListener('input', () => this.debounceUpdate());
        });

        // Payment method change handler
        this.paymentMethodSelect.addEventListener('change', () => this.handlePaymentMethodChange());

        // Customer selection handler
        this.customerSelect.addEventListener('change', () => this.handleCustomerChange());

        // Form submission handler
        this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));
    }

    setupFormValidation() {
        // Real-time validation
        const requiredFields = this.form.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('blur', () => this.validateField(field));
            field.addEventListener('input', () => this.clearFieldError(field));
        });
    }

    validateField(field) {
        const isValid = field.checkValidity();
        const errorDiv = field.parentNode.querySelector('.field-error');

        if (!isValid) {
            field.classList.add('is-invalid');
            if (!errorDiv) {
                const error = document.createElement('div');
                error.className = 'field-error text-danger small mt-1';
                error.textContent = field.validationMessage;
                field.parentNode.appendChild(error);
            }
        } else {
            this.clearFieldError(field);
        }

        return isValid;
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.field-error');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    setupAutoComplete() {
        // Enhanced customer search
        this.customerSelect.addEventListener('keyup', (e) => {
            if (e.key === 'Enter' && this.customerSelect.value === '') {
                document.querySelector('[data-bs-target="#quickCustomerModal"]').click();
            }
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + S to save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.quickSave();
            }

            // Ctrl/Cmd + Enter to save and continue
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.saveAndContinue();
            }

            // Escape to cancel
            if (e.key === 'Escape') {
                this.confirmCancel();
            }
        });
    }

    setDefaultValues() {
        // Set default due date to 30 days from now
        const dueDateInput = document.getElementById('due_date');
        if (dueDateInput && !dueDateInput.value) {
            const defaultDate = new Date();
            defaultDate.setDate(defaultDate.getDate() + 30);
            dueDateInput.value = defaultDate.toISOString().split('T')[0];
        }
    }

    debounceUpdate() {
        clearTimeout(this.updateTimer);
        this.updateTimer = setTimeout(() => this.updatePreview(), 300);
    }

    updatePreview() {
        this.updateCustomerPreview();
        this.updateDueDatePreview();
        this.updateDiscountPreview();
        this.updatePaymentMethodPreview();
        this.updateReferencePreview();
        this.updateTaxPreview();
        this.saveDraftData();
    }

    updateCustomerPreview() {
        const selectedOption = this.customerSelect.options[this.customerSelect.selectedIndex];
        const customerName = selectedOption.text !== 'اختر العميل...' ? selectedOption.text : 'لم يتم الاختيار';

        this.previewElements.customer.textContent = customerName;
        this.previewElements.customer.className = selectedOption.value ? 'text-dark fw-semibold' : 'text-muted';
    }

    updateDueDatePreview() {
        const dueDateInput = document.getElementById('due_date');
        if (dueDateInput.value) {
            const date = new Date(dueDateInput.value);
            this.previewElements.dueDate.textContent = date.toLocaleDateString('ar-EG');
            this.previewElements.dueDate.className = 'text-dark';
        } else {
            this.previewElements.dueDate.textContent = 'غير محدد';
            this.previewElements.dueDate.className = 'text-muted';
        }
    }

    updateDiscountPreview() {
        const discountInput = document.getElementById('discount');
        const discountValue = parseFloat(discountInput.value) || 0;
        this.previewElements.discount.textContent = `${discountValue.toFixed(2)} ${this.getCurrencySymbol()}`;
    }

    updatePaymentMethodPreview() {
        const selectedOption = this.paymentMethodSelect.options[this.paymentMethodSelect.selectedIndex];
        const methodName = selectedOption.text !== 'اختر طريقة الدفع...' ? selectedOption.text : 'غير محددة';

        this.previewElements.paymentMethod.textContent = methodName;
        this.previewElements.paymentMethod.className = selectedOption.value ? 'text-dark' : 'text-muted';
    }

    updateReferencePreview() {
        const referenceInput = document.getElementById('payment_reference');
        if (referenceInput.value) {
            this.previewElements.reference.textContent = referenceInput.value;
            this.previewElements.referenceRow.style.display = 'flex';
        } else {
            this.previewElements.referenceRow.style.display = 'none';
        }
    }

    updateTaxPreview() {
        const taxInclusiveInput = document.getElementById('is_tax_inclusive');
        const withholdingInput = document.getElementById('is_withholding_applied');

        this.previewElements.taxInclusive.textContent = taxInclusiveInput.checked ? 'نعم' : 'لا';
        this.previewElements.taxInclusive.className = taxInclusiveInput.checked ? 'text-success' : 'text-muted';

        this.previewElements.withholding.textContent = withholdingInput.checked ? 'نعم' : 'لا';
        this.previewElements.withholding.className = withholdingInput.checked ? 'text-warning' : 'text-muted';
    }

    handlePaymentMethodChange() {
        const selectedOption = this.paymentMethodSelect.options[this.paymentMethodSelect.selectedIndex];
        const paymentType = selectedOption.dataset.type;
        const referenceInput = document.getElementById('payment_reference');

        // Show/hide reference field based on payment type
        const requiresReference = ['check', 'bank_transfer', 'instapay', 'wallet'].includes(paymentType);

        if (requiresReference) {
            this.paymentReferenceSection.style.display = 'block';
            referenceInput.required = ['check', 'bank_transfer'].includes(paymentType);

            // Update placeholder based on type
            const placeholders = {
                'check': 'رقم الشيك',
                'bank_transfer': 'رقم التحويل أو المرجع',
                'instapay': 'رقم العملية',
                'wallet': 'رقم المحفظة أو المرجع'
            };
            referenceInput.placeholder = placeholders[paymentType] || 'مرجع الدفع';

            // Animate the field appearance
            this.animateFieldEntry(this.paymentReferenceSection);
        } else {
            this.paymentReferenceSection.style.display = 'none';
            referenceInput.required = false;
            referenceInput.value = '';
        }

        this.updatePreview();
    }

    handleCustomerChange() {
        const customerId = this.customerSelect.value;
        if (customerId) {
            // Potentially load customer-specific defaults
            this.loadCustomerDefaults(customerId);
        }
        this.updatePreview();
    }

    async loadCustomerDefaults(customerId) {
        // This could load customer-specific payment methods, terms, etc.
        // Implementation depends on backend API availability
        try {
            // Example: load customer's preferred payment method
            // const response = await fetch(`/api/customers/${customerId}/defaults/`);
            // const data = await response.json();
            // if (data.preferred_payment_method) {
            //     this.paymentMethodSelect.value = data.preferred_payment_method;
            //     this.handlePaymentMethodChange();
            // }
        } catch (error) {
            console.log('Could not load customer defaults:', error);
        }
    }

    animateFieldEntry(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(-10px)';

        requestAnimationFrame(() => {
            element.style.transition = 'all 0.3s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        });
    }

    async handleFormSubmit(e) {
        e.preventDefault();

        if (!this.validateForm()) {
            this.showValidationErrors();
            return;
        }

        const submitBtn = e.submitter || this.form.querySelector('button[type="submit"]');
        const action = submitBtn.value || 'save';

        this.setFormLoading(true, submitBtn);

        try {
            await this.submitForm(action);
        } catch (error) {
            this.handleSubmitError(error);
        } finally {
            this.setFormLoading(false, submitBtn);
        }
    }

    validateForm() {
        const requiredFields = this.form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    showValidationErrors() {
        Swal.fire({
            icon: 'warning',
            title: 'بيانات ناقصة',
            text: 'يرجى ملء جميع الحقول المطلوبة وتصحيح الأخطاء',
            confirmButtonColor: '#667eea'
        });

        // Scroll to first error
        const firstError = this.form.querySelector('.is-invalid');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            firstError.focus();
        }
    }

    async submitForm(action) {
        // Add action to form data
        const actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action';
        actionInput.value = action;
        this.form.appendChild(actionInput);

        // Clear draft data on successful submission
        this.clearDraftData();

        // Submit the form
        this.form.submit();
    }

    handleSubmitError(error) {
        Swal.fire({
            icon: 'error',
            title: 'خطأ في الحفظ',
            text: error.message || 'حدث خطأ غير متوقع أثناء حفظ الفاتورة',
            confirmButtonColor: '#667eea'
        });
    }

    setFormLoading(loading, button) {
        if (loading) {
            button.classList.add('loading');
            button.disabled = true;
            this.form.style.pointerEvents = 'none';
            this.form.style.opacity = '0.7';
        } else {
            button.classList.remove('loading');
            button.disabled = false;
            this.form.style.pointerEvents = 'auto';
            this.form.style.opacity = '1';
        }
    }

    // Quick action methods
    quickSave() {
        const saveBtn = this.form.querySelector('button[value="save"]');
        if (saveBtn) {
            saveBtn.click();
        }
    }

    saveAndContinue() {
        const continueBtn = this.form.querySelector('button[value="save_and_continue"]');
        if (continueBtn) {
            continueBtn.click();
        }
    }

    confirmCancel() {
        if (this.hasUnsavedChanges()) {
            Swal.fire({
                title: 'هل أنت متأكد؟',
                text: 'سيتم فقدان التغييرات غير المحفوظة',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#667eea',
                confirmButtonText: 'نعم، إلغاء',
                cancelButtonText: 'البقاء هنا'
            }).then((result) => {
                if (result.isConfirmed) {
                    this.clearDraftData();
                    window.location.href = this.form.querySelector('a[href*="invoice_list"]').href;
                }
            });
        } else {
            window.location.href = this.form.querySelector('a[href*="invoice_list"]').href;
        }
    }

    // Draft data management
    saveDraftData() {
        if (!this.hasUnsavedChanges()) return;

        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData.entries());
        localStorage.setItem('invoice_form_draft', JSON.stringify(data));
    }

    loadDraftData() {
        const draftData = localStorage.getItem('invoice_form_draft');
        if (!draftData) return;

        try {
            const data = JSON.parse(draftData);
            Object.entries(data).forEach(([name, value]) => {
                const element = this.form.querySelector(`[name="${name}"]`);
                if (element) {
                    if (element.type === 'checkbox') {
                        element.checked = value === 'on' || value === true;
                    } else {
                        element.value = value;
                    }
                }
            });

            // Show draft restoration notification
            this.showDraftRestored();
        } catch (error) {
            console.log('Error loading draft data:', error);
            localStorage.removeItem('invoice_form_draft');
        }
    }

    clearDraftData() {
        localStorage.removeItem('invoice_form_draft');
    }

    hasUnsavedChanges() {
        const inputs = this.form.querySelectorAll('input, select, textarea');
        return Array.from(inputs).some(input => {
            if (input.type === 'checkbox') {
                return input.checked !== input.defaultChecked;
            }
            return input.value !== input.defaultValue;
        });
    }

    showDraftRestored() {
        const toast = document.createElement('div');
        toast.className = 'position-fixed top-0 end-0 p-3';
        toast.style.zIndex = '1060';
        toast.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-header">
                    <i class="bi bi-save text-success me-2"></i>
                    <strong class="me-auto">تم استعادة المسودة</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    تم استعادة البيانات المحفوظة مسبقاً
                </div>
            </div>
        `;

        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    getCurrencySymbol() {
        // This should match the currency_symbol from Django template tag
        return 'ج.م'; // Default to Egyptian Pound
    }
}

// Customer management class
class CustomerManager {
    constructor() {
        this.modal = document.getElementById('quickCustomerModal');
        this.form = document.getElementById('quickCustomerForm');
        this.saveBtn = document.getElementById('saveQuickCustomer');
        this.feedback = document.getElementById('quickCustomerFeedback');
        this.customerSelect = document.getElementById('customer');
        this.refreshBtn = document.getElementById('refreshCustomers');

        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        if (this.saveBtn) {
            this.saveBtn.addEventListener('click', () => this.saveCustomer());
        }

        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', () => this.refreshCustomers());
        }

        // Reset form when modal is hidden
        if (this.modal) {
            this.modal.addEventListener('hidden.bs.modal', () => {
                this.form.reset();
                this.clearFeedback();
            });
        }
    }

    async saveCustomer() {
        this.clearFeedback();

        if (!this.form.reportValidity()) return;

        const formData = new FormData(this.form);
        this.setLoading(true);

        try {
            const response = await this.submitCustomer(formData);
            const result = await response.json();

            if (response.ok && result.success && result.id) {
                this.addCustomerToSelect(result);
                this.closeModal();
                this.showSuccessMessage(result.name);
            } else {
                throw new Error(result.message || 'فشل في إضافة العميل');
            }
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.setLoading(false);
        }
    }

    async submitCustomer(formData) {
        const csrf = this.getCSRFToken();

        return fetch(this.getCustomerCreateURL(), {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrf
            },
            body: formData
        });
    }

    addCustomerToSelect(customer) {
        const option = document.createElement('option');
        option.value = customer.id;
        option.textContent = customer.name;
        this.customerSelect.appendChild(option);
        this.customerSelect.value = customer.id;

        // Trigger change event to update preview
        this.customerSelect.dispatchEvent(new Event('change'));
    }

    closeModal() {
        const modal = bootstrap.Modal.getInstance(this.modal);
        modal.hide();
        this.form.reset();
    }

    showSuccessMessage(customerName) {
        Swal.fire({
            icon: 'success',
            title: 'تم بنجاح!',
            text: `تم إضافة العميل "${customerName}" بنجاح`,
            timer: 2000,
            showConfirmButton: false,
            confirmButtonColor: '#667eea'
        });
    }

    showError(message) {
        this.feedback.textContent = message;
        this.feedback.classList.remove('d-none');
    }

    clearFeedback() {
        this.feedback.classList.add('d-none');
        this.feedback.textContent = '';
    }

    setLoading(loading) {
        if (loading) {
            this.saveBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>جاري الحفظ...';
            this.saveBtn.disabled = true;
        } else {
            this.saveBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>حفظ العميل';
            this.saveBtn.disabled = false;
        }
    }

    refreshCustomers() {
        this.refreshBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>جاري التحديث...';
        this.refreshBtn.disabled = true;

        setTimeout(() => {
            window.location.reload();
        }, 500);
    }

    getCSRFToken() {
        return document.querySelector('input[name=csrfmiddlewaretoken]')?.value ||
            (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] ||
            document.querySelector('meta[name=csrf-token]')?.content;
    }

    getCustomerCreateURL() {
        // This should be dynamically generated or configured
        return '/partners/create/'; // Adjust based on your URL structure
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    const invoiceManager = new InvoiceFormManager();
    const customerManager = new CustomerManager();

    // Add some nice loading effects
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);

    // Add form interaction animations
    const inputs = document.querySelectorAll('.floating-label input, .floating-label select');
    inputs.forEach(input => {
        input.addEventListener('focus', function () {
            this.parentNode.classList.add('focused');
        });

        input.addEventListener('blur', function () {
            this.parentNode.classList.remove('focused');
        });
    });
});