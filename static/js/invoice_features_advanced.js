/**
 * الميزات المحسنة للفواتير
 * Enhanced Invoice Features
 * Version: 3.0
 * Date: 2026-01-08
 */

// ============================================
// 1. الحفظ التلقائي (Auto-Save)
// ============================================

let autoSaveInterval = null;
let formChanged = false;
let lastSaveTime = null;

/**
 * تهيئة الحفظ التلقائي
 */
function initAutoSave() {
    console.log('🔄 تفعيل الحفظ التلقائي...');
    
    // مراقبة التغييرات في النموذج
    $('form input, form select, form textarea').on('change input', function() {
        formChanged = true;
    });
    
    // الحفظ كل 30 ثانية
    autoSaveInterval = setInterval(autoSaveForm, 30000);
    
    // الحفظ عند مغادرة الصفحة
    $(window).on('beforeunload', function() {
        if (formChanged) {
            autoSaveForm();
        }
    });
}

/**
 * حفظ النموذج تلقائياً
 */
function autoSaveForm() {
    if (!formChanged) {
        return;
    }
    
    const formData = {
        customer_id: $('#id_customer').val(),
        due_date: $('#id_due_date').val(),
        discount: $('#id_discount').val() || 0,
        payment_method: $('#id_payment_method').val(),
        payment_reference: $('#id_payment_reference').val(),
        is_tax_inclusive: $('#id_is_tax_inclusive').is(':checked'),
        items: items || []
    };
    
    $.ajax({
        url: '/sales/api/autosave/',
        method: 'POST',
        data: JSON.stringify({
            session_key: 'invoice_draft_' + Date.now(),
            form_data: formData
        }),
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        success: function(response) {
            if (response.success) {
                lastSaveTime = new Date();
                formChanged = false;
                showAutoSaveNotification();
            }
        },
        error: function() {
            console.error('فشل الحفظ التلقائي');
        }
    });
}

/**
 * إظهار إشعار الحفظ التلقائي
 */
function showAutoSaveNotification() {
    const notification = $(`
        <div class="autosave-notification">
            <i class="fas fa-check-circle text-success"></i>
            تم الحفظ تلقائياً
            <small class="ms-2">${new Date().toLocaleTimeString('ar-EG')}</small>
        </div>
    `);
    
    $('body').append(notification);
    
    setTimeout(() => {
        notification.fadeOut(500, function() {
            $(this).remove();
        });
    }, 3000);
}

// ============================================
// 2. نماذج الفواتير الجاهزة (Templates)
// ============================================

let invoiceTemplates = [];

/**
 * تحميل نماذج الفواتير
 */
function loadInvoiceTemplates() {
    $.ajax({
        url: '/sales/api/templates/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                invoiceTemplates = response.templates;
                renderTemplatesDropdown();
            }
        }
    });
}

/**
 * عرض قائمة النماذج
 */
function renderTemplatesDropdown() {
    if (invoiceTemplates.length === 0) {
        return;
    }
    
    const dropdown = $(`
        <div class="template-selector mb-3">
            <label class="form-label">
                <i class="fas fa-file-invoice text-primary"></i>
                استخدام نموذج جاهز
            </label>
            <select class="form-select" id="templateSelect">
                <option value="">-- اختر نموذج --</option>
            </select>
        </div>
    `);
    
    invoiceTemplates.forEach(template => {
        dropdown.find('select').append(
            `<option value="${template.id}">${template.name} - ${template.customer_name}</option>`
        );
    });
    
    dropdown.find('select').on('change', function() {
        const templateId = $(this).val();
        if (templateId) {
            loadTemplate(templateId);
        }
    });
    
    $('.invoice-form-container').prepend(dropdown);
}

/**
 * تحميل نموذج معين
 */
function loadTemplate(templateId) {
    const template = invoiceTemplates.find(t => t.id == templateId);
    
    if (!template) {
        return;
    }
    
    // ملء البيانات من النموذج
    $('#id_customer').val(template.customer_id).trigger('change');
    $('#id_payment_method').val(template.payment_method_id).trigger('change');
    $('#id_discount').val(template.discount);
    $('#id_is_tax_inclusive').prop('checked', template.is_tax_inclusive);
    
    // تحميل الأصناف
    items = template.items_data || [];
    updateTable();
    
    showNotification(`تم تحميل النموذج: ${template.name}`, 'success');
    
    // زيادة عداد الاستخدام
    $.post('/sales/api/templates/' + templateId + '/increment/');
}

/**
 * حفظ كنموذج جديد
 */
function saveAsTemplate() {
    const templateName = prompt('أدخل اسم النموذج:');
    
    if (!templateName) {
        return;
    }
    
    const templateData = {
        name: templateName,
        customer_id: $('#id_customer').val(),
        payment_method_id: $('#id_payment_method').val(),
        discount: $('#id_discount').val() || 0,
        is_tax_inclusive: $('#id_is_tax_inclusive').is(':checked'),
        items_data: items || []
    };
    
    $.ajax({
        url: '/sales/api/templates/',
        method: 'POST',
        data: JSON.stringify(templateData),
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        success: function(response) {
            if (response.success) {
                showNotification('تم حفظ النموذج بنجاح', 'success');
                loadInvoiceTemplates();
            }
        }
    });
}

// ============================================
// 3. الحساب التلقائي للضريبة
// ============================================

/**
 * حساب الضريبة تلقائياً
 */
function calculateTaxAutomatically() {
    const subtotal = calculateSubtotal();
    const taxRate = 0.15; // 15% VAT
    const taxAmount = subtotal * taxRate;
    const total = subtotal + taxAmount;
    
    // عرض التفاصيل
    const taxDisplay = $(`
        <div class="tax-breakdown mt-3">
            <div class="row">
                <div class="col-4">
                    <div class="tax-item">
                        <small>المبلغ قبل الضريبة</small>
                        <h5>${formatCurrency(subtotal)}</h5>
                    </div>
                </div>
                <div class="col-4">
                    <div class="tax-item">
                        <small>ضريبة القيمة المضافة (15%)</small>
                        <h5 class="text-warning">${formatCurrency(taxAmount)}</h5>
                    </div>
                </div>
                <div class="col-4">
                    <div class="tax-item">
                        <small>الإجمالي شامل الضريبة</small>
                        <h5 class="text-success">${formatCurrency(total)}</h5>
                    </div>
                </div>
            </div>
        </div>
    `);
    
    $('#taxBreakdown').html(taxDisplay);
}

// ============================================
// 4. البحث الذكي للعملاء
// ============================================

/**
 * تهيئة البحث الذكي
 */
function initSmartCustomerSearch() {
    $('#id_customer').select2({
        theme: 'bootstrap-5',
        language: 'ar',
        placeholder: 'ابحث عن عميل...',
        allowClear: true,
        ajax: {
            url: '/api/customers/search/',
            dataType: 'json',
            delay: 250,
            data: function(params) {
                return {
                    q: params.term,
                    page: params.page || 1
                };
            },
            processResults: function(data) {
                // ✅ FIX: التحقق من نجاح الطلب ومعالجة الأخطاء
                if (!data.success) {
                    console.error('❌ خطأ في البحث عن العملاء:', data.message || 'Unknown error');
                    return {
                        results: [],
                        pagination: {more: false}
                    };
                }
                
                // ✅ FIX: API يعيد 'customers' وليس 'results'
                const customers = data.customers || [];
                
                return {
                    results: customers.map(customer => ({
                        id: customer.id,
                        text: customer.name,
                        balance: customer.balance || 0,
                        phone: customer.phone || '',
                        lastInvoice: customer.last_invoice_date,
                        customer: customer  // ✅ حفظ البيانات الكاملة
                    })),
                    pagination: {
                        more: (data.count > 20)  // ✅ FIX: استخدام count بدلاً من has_more
                    }
                };
            }
        },
        templateResult: formatCustomerResult,
        templateSelection: formatCustomerSelection
    });
    
    // عرض تفاصيل العميل عند الاختيار
    $('#id_customer').on('select2:select', function(e) {
        const customer = e.params.data;
        showCustomerInfo(customer);
    });
}

/**
 * تنسيق نتيجة بحث العميل
 */
function formatCustomerResult(customer) {
    if (!customer.id) {
        return customer.text;
    }
    
    const $result = $(`
        <div class="customer-search-result">
            <div class="customer-name">${customer.text}</div>
            <div class="customer-details">
                <span class="badge bg-info">${customer.phone || 'لا يوجد هاتف'}</span>
                <span class="badge bg-${customer.balance > 0 ? 'danger' : 'success'}">
                    الرصيد: ${formatCurrency(customer.balance || 0)}
                </span>
            </div>
        </div>
    `);
    
    return $result;
}

/**
 * عرض معلومات العميل المختار
 */
function showCustomerInfo(customer) {
    // جلب آخر 3 معاملات
    $.ajax({
        url: `/api/customers/${customer.id}/last-transactions/`,
        method: 'GET',
        success: function(response) {
            const infoBox = $(`
                <div class="customer-info-box alert alert-info mt-2">
                    <h6><i class="fas fa-user-circle"></i> معلومات العميل</h6>
                    <div class="row">
                        <div class="col-md-4">
                            <strong>الرصيد الحالي:</strong>
                            <span class="text-${response.balance > 0 ? 'danger' : 'success'}">
                                ${formatCurrency(response.balance)}
                            </span>
                        </div>
                        <div class="col-md-4">
                            <strong>آخر فاتورة:</strong>
                            ${response.last_invoice_date || 'لا يوجد'}
                        </div>
                        <div class="col-md-4">
                            <strong>عدد الفواتير:</strong>
                            ${response.invoice_count}
                        </div>
                    </div>
                    <div class="mt-2">
                        <strong>آخر 3 معاملات:</strong>
                        <ul class="list-unstyled mt-1">
                            ${response.last_transactions.map(t => `
                                <li>
                                    <small>
                                        ${t.number} - ${t.date} - ${formatCurrency(t.total)}
                                        <span class="badge bg-${t.status === 'paid' ? 'success' : 'warning'}">
                                            ${t.status === 'paid' ? 'مدفوع' : 'معلق'}
                                        </span>
                                    </small>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
            `);
            
            $('.customer-info-container').html(infoBox);
        }
    });
}

// ============================================
// 5. اختصارات لوحة المفاتيح
// ============================================

/**
 * تهيئة اختصارات لوحة المفاتيح
 */
function initKeyboardShortcuts() {
    $(document).on('keydown', function(e) {
        // Ctrl + S = حفظ
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            $('form').submit();
            return false;
        }
        
        // Ctrl + Enter = حفظ وإضافة جديد
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            $('#saveAndNew').click();
            return false;
        }
        
        // F2 = إضافة صنف
        if (e.key === 'F2') {
            e.preventDefault();
            $('#addItemBtn').click();
            return false;
        }
        
        // F3 = بحث عميل
        if (e.key === 'F3') {
            e.preventDefault();
            $('#id_customer').select2('open');
            return false;
        }
        
        // Esc = إلغاء
        if (e.key === 'Escape') {
            if ($('.modal').hasClass('show')) {
                $('.modal').modal('hide');
            } else {
                window.history.back();
            }
            return false;
        }
    });
    
    // عرض دليل الاختصارات
    showKeyboardShortcutsGuide();
}

/**
 * عرض دليل اختصارات المفاتيح
 */
function showKeyboardShortcutsGuide() {
    const guide = $(`
        <div class="keyboard-shortcuts-guide">
            <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="popover" 
                    data-bs-placement="bottom" data-bs-html="true"
                    data-bs-content="
                        <table class='table table-sm'>
                            <tr><td><kbd>Ctrl + S</kbd></td><td>حفظ</td></tr>
                            <tr><td><kbd>Ctrl + Enter</kbd></td><td>حفظ وإضافة جديد</td></tr>
                            <tr><td><kbd>F2</kbd></td><td>إضافة صنف</td></tr>
                            <tr><td><kbd>F3</kbd></td><td>بحث عميل</td></tr>
                            <tr><td><kbd>Esc</kbd></td><td>إلغاء</td></tr>
                        </table>
                    ">
                <i class="fas fa-keyboard"></i> اختصارات المفاتيح
            </button>
        </div>
    `);
    
    $('.page-header .container').append(guide);
    
    // تفعيل popover
    $('[data-bs-toggle="popover"]').popover();
}

// ============================================
// 6. نسخ من فاتورة سابقة
// ============================================

/**
 * نسخ بيانات من فاتورة سابقة
 */
function copyFromInvoice() {
    const invoiceNumber = prompt('أدخل رقم الفاتورة المراد نسخها:');
    
    if (!invoiceNumber) {
        return;
    }
    
    $.ajax({
        url: `/sales/api/invoice/${invoiceNumber}/details/`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const invoice = response.invoice;
                
                // تأكيد النسخ
                if (!confirm(`هل تريد نسخ بيانات الفاتورة ${invoice.number}؟`)) {
                    return;
                }
                
                // ملء البيانات
                $('#id_customer').val(invoice.customer_id).trigger('change');
                $('#id_payment_method').val(invoice.payment_method_id).trigger('change');
                $('#id_discount').val(invoice.discount);
                $('#id_is_tax_inclusive').prop('checked', invoice.is_tax_inclusive);
                
                // نسخ الأصناف
                items = invoice.items || [];
                updateTable();
                
                showNotification(`تم نسخ بيانات الفاتورة ${invoice.number}`, 'success');
            } else {
                showNotification('الفاتورة غير موجودة', 'error');
            }
        },
        error: function() {
            showNotification('خطأ في جلب بيانات الفاتورة', 'error');
        }
    });
}

// ============================================
// 7. حسابات سريعة في الحقول
// ============================================

/**
 * تفعيل الحسابات السريعة
 */
function enableQuickCalculations() {
    $('.calculator-field').on('blur', function() {
        const expression = $(this).val().trim();
        
        // إذا كان الحقل يحتوي على عملية حسابية
        if (expression.match(/[\+\-\*\/]/)) {
            try {
                // حساب النتيجة بشكل آمن
                const result = evaluateSafeExpression(expression);
                $(this).val(result);
                
                // إظهار إشعار صغير
                showCalculationResult(result);
            } catch (error) {
                console.error('خطأ في العملية الحسابية:', error);
            }
        }
    });
}

/**
 * تقييم تعبير رياضي بشكل آمن
 */
function evaluateSafeExpression(expr) {
    // إزالة أي أحرف غير آمنة
    const cleaned = expr.replace(/[^0-9+\-*/().\s]/g, '');
    
    // حساب النتيجة
    try {
        return Function('"use strict"; return (' + cleaned + ')')();
    } catch (e) {
        throw new Error('تعبير رياضي غير صالح');
    }
}

/**
 * عرض نتيجة الحساب
 */
function showCalculationResult(result) {
    const notification = $(`
        <div class="calculation-result-tooltip">
            <i class="fas fa-calculator"></i>
            النتيجة: ${result}
        </div>
    `);
    
    $('body').append(notification);
    
    setTimeout(() => {
        notification.fadeOut(300, function() {
            $(this).remove();
        });
    }, 2000);
}

// ============================================
// 8. تذكيرات ذكية
// ============================================

/**
 * عرض تذكيرات ذكية
 */
function showSmartReminders() {
    const reminders = [];
    
    // التحقق من الحقول الفارغة المهمة
    if (!$('#id_customer').val()) {
        reminders.push({
            type: 'warning',
            message: 'لم تقم باختيار عميل بعد',
            action: () => $('#id_customer').select2('open')
        });
    }
    
    if (items.length === 0) {
        reminders.push({
            type: 'warning',
            message: 'لم تقم بإضافة أي أصناف',
            action: () => $('#addItemBtn').click()
        });
    }
    
    if (!$('#id_payment_method').val()) {
        reminders.push({
            type: 'info',
            message: 'يفضل تحديد طريقة الدفع',
            action: () => $('#id_payment_method').focus()
        });
    }
    
    // عرض التذكيرات
    if (reminders.length > 0) {
        const reminderBox = $('<div class="smart-reminders"></div>');
        
        reminders.forEach(reminder => {
            const item = $(`
                <div class="alert alert-${reminder.type} alert-dismissible fade show" role="alert">
                    <i class="fas fa-lightbulb"></i>
                    ${reminder.message}
                    ${reminder.action ? '<button class="btn btn-sm btn-light ms-2 reminder-action">إصلاح</button>' : ''}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `);
            
            if (reminder.action) {
                item.find('.reminder-action').on('click', reminder.action);
            }
            
            reminderBox.append(item);
        });
        
        $('.invoice-form-container').prepend(reminderBox);
    }
}

// ============================================
// 9. مرفقات سريعة (سحب وإفلات)
// ============================================

/**
 * تفعيل رفع الملفات بالسحب والإفلات
 */
function enableDragDropAttachments() {
    const dropZone = $(`
        <div class="attachment-dropzone">
            <div class="dropzone-inner">
                <i class="fas fa-cloud-upload-alt fa-3x text-muted mb-3"></i>
                <h5>اسحب الملفات هنا</h5>
                <p>أو انقر لاختيار الملفات</p>
                <input type="file" id="attachmentInput" multiple hidden>
            </div>
            <div class="attachment-list mt-3"></div>
        </div>
    `);
    
    $('.attachments-section').html(dropZone);
    
    // منع السلوك الافتراضي
    dropZone.on('drag dragstart dragend dragover dragenter dragleave drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
    });
    
    // تغيير المظهر عند السحب
    dropZone.on('dragover dragenter', function() {
        $(this).addClass('dragover');
    });
    
    dropZone.on('dragleave dragend drop', function() {
        $(this).removeClass('dragover');
    });
    
    // معالجة الإفلات
    dropZone.on('drop', function(e) {
        const files = e.originalEvent.dataTransfer.files;
        handleFiles(files);
    });
    
    // معالجة النقر
    dropZone.find('.dropzone-inner').on('click', function() {
        $('#attachmentInput').click();
    });
    
    $('#attachmentInput').on('change', function() {
        handleFiles(this.files);
    });
}

/**
 * معالجة الملفات المرفوعة
 */
function handleFiles(files) {
    const attachmentList = $('.attachment-list');
    
    Array.from(files).forEach(file => {
        // التحقق من حجم الملف (5 MB max)
        if (file.size > 5 * 1024 * 1024) {
            showNotification(`الملف ${file.name} كبير جداً (أكثر من 5 MB)`, 'error');
            return;
        }
        
        const fileItem = $(`
            <div class="attachment-item">
                <div class="attachment-icon">
                    <i class="fas fa-${getFileIcon(file.type)}"></i>
                </div>
                <div class="attachment-info">
                    <div class="attachment-name">${file.name}</div>
                    <div class="attachment-size">${formatFileSize(file.size)}</div>
                </div>
                <button class="btn btn-sm btn-danger remove-attachment">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `);
        
        fileItem.find('.remove-attachment').on('click', function() {
            fileItem.remove();
        });
        
        attachmentList.append(fileItem);
        
        // رفع الملف
        uploadAttachment(file);
    });
}

/**
 * رفع مرفق
 */
function uploadAttachment(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    $.ajax({
        url: '/sales/api/attachments/upload/',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        success: function(response) {
            if (response.success) {
                showNotification(`تم رفع ${file.name}`, 'success');
            }
        },
        error: function() {
            showNotification(`فشل رفع ${file.name}`, 'error');
        }
    });
}

// ============================================
// 10. تصدير وطباعة سريعة
// ============================================

/**
 * تصدير الفاتورة كـ PDF
 */
function exportToPDF() {
    const invoiceId = getInvoiceId();
    
    if (!invoiceId) {
        showNotification('يجب حفظ الفاتورة أولاً', 'warning');
        return;
    }
    
    window.open(`/sales/invoice/${invoiceId}/pdf/`, '_blank');
}

/**
 * إرسال الفاتورة بالبريد الإلكتروني
 */
function sendByEmail() {
    const invoiceId = getInvoiceId();
    
    if (!invoiceId) {
        showNotification('يجب حفظ الفاتورة أولاً', 'warning');
        return;
    }
    
    const email = prompt('أدخل البريد الإلكتروني:');
    
    if (!email) {
        return;
    }
    
    $.ajax({
        url: `/sales/invoice/${invoiceId}/send-email/`,
        method: 'POST',
        data: {
            email: email
        },
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        success: function(response) {
            if (response.success) {
                showNotification('تم إرسال الفاتورة بنجاح', 'success');
            } else {
                showNotification('فشل الإرسال', 'error');
            }
        }
    });
}

/**
 * طباعة الفاتورة
 */
function printInvoice() {
    const invoiceId = getInvoiceId();
    
    if (!invoiceId) {
        showNotification('يجب حفظ الفاتورة أولاً', 'warning');
        return;
    }
    
    window.open(`/sales/invoice/${invoiceId}/print/`, '_blank');
}

// ============================================
// 11. تنبيهات الأرصدة والائتمان
// ============================================

/**
 * التحقق من حد الائتمان
 */
function checkCreditLimit() {
    const customerId = $('#id_customer').val();
    
    if (!customerId) {
        return;
    }
    
    const total = calculateTotal();
    
    $.ajax({
        url: `/api/customers/${customerId}/credit-check/`,
        method: 'POST',
        data: {
            amount: total
        },
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        success: function(response) {
            if (response.over_limit) {
                showCreditWarning(response);
            }
            
            if (response.overdue_invoices > 0) {
                showOverdueWarning(response);
            }
        }
    });
}

/**
 * عرض تحذير تجاوز حد الائتمان
 */
function showCreditWarning(data) {
    const warning = $(`
        <div class="alert alert-danger credit-warning">
            <h6><i class="fas fa-exclamation-triangle"></i> تحذير: تجاوز حد الائتمان</h6>
            <p>
                حد الائتمان: ${formatCurrency(data.credit_limit)}<br>
                الرصيد الحالي: ${formatCurrency(data.current_balance)}<br>
                المبلغ الجديد: ${formatCurrency(data.new_balance)}<br>
                <strong>التجاوز: ${formatCurrency(data.over_amount)}</strong>
            </p>
            <p class="mb-0">
                <small>يتطلب موافقة المدير لإتمام العملية</small>
            </p>
        </div>
    `);
    
    $('.invoice-form-container').prepend(warning);
}

/**
 * عرض تحذير الفواتير المستحقة
 */
function showOverdueWarning(data) {
    const warning = $(`
        <div class="alert alert-warning overdue-warning">
            <h6><i class="fas fa-clock"></i> تنبيه: فواتير متأخرة</h6>
            <p>
                لدى العميل ${data.overdue_invoices} فاتورة متأخرة<br>
                إجمالي المتأخرات: ${formatCurrency(data.overdue_amount)}
            </p>
            <button class="btn btn-sm btn-warning" onclick="viewOverdueInvoices(${data.customer_id})">
                عرض الفواتير المتأخرة
            </button>
        </div>
    `);
    
    $('.invoice-form-container').prepend(warning);
}

// ============================================
// دوال مساعدة
// ============================================

/**
 * تنسيق العملة
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('ar-EG', {
        style: 'currency',
        currency: 'EGP'
    }).format(amount);
}

/**
 * تنسيق حجم الملف
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * الحصول على أيقونة الملف
 */
function getFileIcon(mimeType) {
    if (mimeType.startsWith('image/')) return 'file-image';
    if (mimeType.includes('pdf')) return 'file-pdf';
    if (mimeType.includes('word')) return 'file-word';
    if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'file-excel';
    return 'file';
}

/**
 * الحصول على Cookie
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * إظهار إشعار
 */
function showNotification(message, type = 'info') {
    const notification = $(`
        <div class="notification notification-${type}">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : 'info-circle'}"></i>
            ${message}
        </div>
    `);
    
    $('body').append(notification);
    
    setTimeout(() => {
        notification.addClass('show');
    }, 100);
    
    setTimeout(() => {
        notification.removeClass('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ============================================
// تهيئة عند تحميل الصفحة
// ============================================

$(document).ready(function() {
    console.log('🚀 تحميل الميزات المحسنة...');
    
    // تفعيل جميع الميزات
    initAutoSave();
    loadInvoiceTemplates();
    initSmartCustomerSearch();
    initKeyboardShortcuts();
    enableQuickCalculations();
    enableDragDropAttachments();
    
    // عرض التذكيرات بعد 3 ثواني
    setTimeout(showSmartReminders, 3000);
    
    // التحقق من حد الائتمان عند تغيير العميل
    $('#id_customer').on('change', function() {
        checkCreditLimit();
    });
    
    // إضافة أزرار إضافية للأدوات
    addToolbarButtons();
    
    console.log('✅ تم تحميل جميع الميزات بنجاح');
});

/**
 * إضافة أزرار شريط الأدوات
 */
function addToolbarButtons() {
    const toolbar = $(`
        <div class="invoice-toolbar mb-3">
            <button type="button" class="btn btn-outline-primary" onclick="saveAsTemplate()">
                <i class="fas fa-save"></i> حفظ كنموذج
            </button>
            <button type="button" class="btn btn-outline-secondary" onclick="copyFromInvoice()">
                <i class="fas fa-copy"></i> نسخ من فاتورة
            </button>
            <button type="button" class="btn btn-outline-info" onclick="exportToPDF()">
                <i class="fas fa-file-pdf"></i> تصدير PDF
            </button>
            <button type="button" class="btn btn-outline-success" onclick="printInvoice()">
                <i class="fas fa-print"></i> طباعة
            </button>
            <button type="button" class="btn btn-outline-warning" onclick="sendByEmail()">
                <i class="fas fa-envelope"></i> إرسال بريد
            </button>
        </div>
    `);
    
    $('.invoice-form-container').prepend(toolbar);
}
