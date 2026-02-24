/**
 * Enhanced Invoice Form - Advanced Features
 * Version: 2.0
 * Last Updated: 2026-01-08
 * 
 * Features:
 * - Barcode scanning with AJAX lookup
 * - Stock verification
 * - Auto-save drafts
 * - Keyboard shortcuts
 * - Real-time calculations
 */

// ===== API Endpoints =====
const API_ENDPOINTS = {
    searchBarcode: '/sales/lookup/barcode/',
    checkStock: '/api/inventory/check-stock/',
    getCustomerBalance: '/api/customers/balance/',
    getLastInvoice: '/sales/api/last-invoice/',
    getTemplates: '/api/sales/templates/',
    saveInvoice: '/sales/new/',
};

// ===== Barcode Scanner with AJAX =====
function addByBarcode() {
    const barcode = $('#barcodeInput').val().trim();
    
    if (!barcode) {
        showNotification('الرجاء إدخال رمز المنتج أو مسح الباركود', 'warning');
        return;
    }
    
    // Show loading
    $('#loadingSpinner').addClass('show');
    
    // AJAX Call to find product by barcode
    $.ajax({
        url: API_ENDPOINTS.searchBarcode,
        method: 'GET',
        data: { barcode: barcode },
        success: function(response) {
            if (response.success && response.product) {
                const product = response.product;
                
                // Get default location
                const defaultLocation = $('#modalLocation option:first').val();
                
                if (!defaultLocation) {
                    showNotification('الرجاء إضافة مخزن واحد على الأقل', 'error');
                    return;
                }
                
                // Add item directly
                addItemDirectly(product, defaultLocation);
                
                // Clear barcode input
                $('#barcodeInput').val('').focus();
                
                showNotification(`تم إضافة: ${product.name}`, 'success');
            } else {
                showNotification('المنتج غير موجود. الرجاء التحقق من الرمز', 'error');
                $('#barcodeInput').select();
            }
        },
        error: function() {
            showNotification('خطأ في الاتصال بالسيرفر', 'error');
        },
        complete: function() {
            $('#loadingSpinner').removeClass('show');
        }
    });
}

// ===== Add Item Directly (for barcode) =====
function addItemDirectly(product, locationId) {
    const quantity = 1; // Default quantity for barcode scan
    const price = parseFloat(product.price) || 0;
    const discount = 0; // No discount by default
    
    const subtotal = quantity * price;
    const total = subtotal;
    const taxAmount = total * 0.15; // 15% VAT
    
    itemCounter++;
    const item = {
        id: itemCounter,
        product_id: product.id,
        product_name: product.name,
        location_id: locationId,
        location_name: getLocationName(locationId),
        quantity: quantity,
        price: price,
        discount: discount,
        tax: taxAmount,
        total: total,
        available_stock: product.stock || 0
    };
    
    items.push(item);
    updateTable();
    updateTotals();
}

// ===== Get Location Name by ID =====
function getLocationName(locationId) {
    const option = $('#modalLocation').find(`option[value="${locationId}"]`);
    return option.length ? option.text() : 'مخزن افتراضي';
}

// ===== Enhanced Stock Check with AJAX =====
function checkStockAjax() {
    const productId = $('#modalProduct').val();
    const locationId = $('#modalLocation').val();
    
    if (!productId || !locationId) {
        $('#stockInfo').hide();
        return;
    }
    
    // AJAX Call to get real stock
    $.ajax({
        url: API_ENDPOINTS.checkStock,
        method: 'GET',
        data: {
            product_id: productId,
            location_id: locationId
        },
        success: function(response) {
            if (response.success) {
                const stock = response.stock || 0;
                const requestedQty = parseFloat($('#modalQuantity').val()) || 0;
                
                $('#stockInfoText').html(`الكمية المتاحة في المخزن: <strong>${stock}</strong> قطعة`);
                $('#stockInfo').show().removeClass('alert-danger alert-warning').addClass('alert-info');
                
                if (requestedQty > stock) {
                    $('#stockInfo').removeClass('alert-info').addClass('alert-danger');
                    $('#stockInfoText').html(`⚠️ تحذير: الكمية المطلوبة (${requestedQty}) أكبر من المتاح (${stock})`);
                } else if (requestedQty > stock * 0.8) {
                    $('#stockInfo').removeClass('alert-info').addClass('alert-warning');
                    $('#stockInfoText').html(`⚠️ ملاحظة: المخزون منخفض. متبقي ${stock} قطعة فقط`);
                }
                
                // Store stock value for later use
                $('#modalProduct').data('available-stock', stock);
            }
        },
        error: function() {
            $('#stockInfoText').text('تعذر التحقق من المخزون');
            $('#stockInfo').show().removeClass('alert-info').addClass('alert-warning');
        }
    });
}

// ===== Load Customer Balance with AJAX =====
function loadCustomerBalance(customerId) {
    if (!customerId) return;
    
    $.ajax({
        url: API_ENDPOINTS.getCustomerBalance,
        method: 'GET',
        data: { customer_id: customerId },
        success: function(response) {
            if (response.success) {
                const balance = parseFloat(response.balance) || 0;
                const creditLimit = parseFloat(response.credit_limit) || 0;
                const available = creditLimit - balance;
                
                $('#customerBalance').text(balance.toFixed(2) + ' ج.م');
                $('#customerCreditLimit').text(creditLimit.toFixed(2) + ' ج.م');
                
                // Add available credit info
                const availableHtml = `
                    <div class="info-row">
                        <span class="label">المتاح للشراء:</span>
                        <span class="value ${available < 0 ? 'text-danger' : 'text-success'}">
                            ${available.toFixed(2)} ج.م
                        </span>
                    </div>
                `;
                
                $('#customerInfoBadge').find('.info-row').last().after(availableHtml);
                $('#customerInfoBadge').addClass('show');
            }
        }
    });
}

// ===== Load Last Invoice =====
function loadLastInvoice() {
    if (!confirm('هل تريد تحميل بيانات آخر فاتورة؟ سيتم استبدال البيانات الحالية.')) {
        return;
    }
    
    $('#loadingSpinner').addClass('show');
    
    $.ajax({
        url: API_ENDPOINTS.getLastInvoice,
        method: 'GET',
        success: function(response) {
            if (response.success && response.invoice) {
                const invoice = response.invoice;
                
                // Fill form data
                $('#customerSelect').val(invoice.customer_id).trigger('change');
                $('#paymentMethod').val(invoice.payment_method_id);
                $('#additionalDiscount').val(invoice.discount || 0);
                $('#invoiceNotes').val(invoice.notes || '');
                
                // Clear current items
                items = [];
                itemCounter = 0;
                
                // Add invoice items
                if (invoice.items && invoice.items.length > 0) {
                    invoice.items.forEach(item => {
                        itemCounter++;
                        items.push({
                            id: itemCounter,
                            product_id: item.product_id,
                            product_name: item.product_name,
                            location_id: item.location_id,
                            location_name: item.location_name,
                            quantity: parseFloat(item.quantity),
                            price: parseFloat(item.price),
                            discount: parseFloat(item.discount || 0),
                            tax: parseFloat(item.tax || 0),
                            total: parseFloat(item.total),
                            available_stock: item.available_stock || 0
                        });
                    });
                }
                
                updateTable();
                updateTotals();
                
                showNotification('تم تحميل بيانات آخر فاتورة بنجاح', 'success');
            } else {
                showNotification('لا توجد فواتير سابقة', 'info');
            }
        },
        error: function() {
            showNotification('خطأ في تحميل الفاتورة', 'error');
        },
        complete: function() {
            $('#loadingSpinner').removeClass('show');
        }
    });
}

// ===== Load Template =====
function loadTemplate() {
    // Show templates modal (to be created)
    showNotification('جاري تطوير ميزة القوالب...', 'info');
    
    // In future implementation:
    // $.ajax({
    //     url: API_ENDPOINTS.getTemplates,
    //     success: function(templates) {
    //         // Show templates selection modal
    //     }
    // });
}

// ===== Notification System =====
function showNotification(message, type = 'info') {
    // Types: success, error, warning, info
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        warning: '#ffc107',
        info: '#17a2b8'
    };
    
    const notification = $(`
        <div class="custom-notification" style="
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 15px 25px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 300px;
            animation: slideInRight 0.3s ease;
        ">
            <i class="fas ${icons[type]}" style="color: ${colors[type]}; font-size: 20px;"></i>
            <span style="font-size: 14px; color: #333;">${message}</span>
        </div>
    `);
    
    $('body').append(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.fadeOut(300, function() {
            $(this).remove();
        });
    }, 3000);
}

// ===== Enhanced Form Validation =====
function validateInvoiceForm() {
    const errors = [];
    
    // Check customer
    if (!$('#customerSelect').val()) {
        errors.push('الرجاء اختيار عميل');
    }
    
    // Check items
    if (items.length === 0) {
        errors.push('الرجاء إضافة صنف واحد على الأقل');
    }
    
    // Check date
    if (!$('#invoiceDate').val()) {
        errors.push('الرجاء تحديد تاريخ الفاتورة');
    }
    
    // Check quantities
    const negativeQty = items.some(item => item.quantity <= 0);
    if (negativeQty) {
        errors.push('يوجد أصناف بكميات غير صحيحة');
    }
    
    // Check stock availability
    const outOfStock = items.filter(item => item.quantity > item.available_stock);
    if (outOfStock.length > 0) {
        const names = outOfStock.map(item => item.product_name).join('، ');
        errors.push(`تحذير: الأصناف التالية غير متوفرة بالكمية المطلوبة: ${names}`);
    }
    
    return errors;
}

// ===== Export Invoice Data =====
function exportInvoiceData() {
    const data = {
        customer_id: $('#customerSelect').val(),
        date: $('#invoiceDate').val(),
        due_date: $('#dueDate').val(),
        payment_method_id: $('#paymentMethod').val(),
        discount: parseFloat($('#additionalDiscount').val()) || 0,
        notes: $('#invoiceNotes').val(),
        items: items.map(item => ({
            product_id: item.product_id,
            location_id: item.location_id,
            quantity: item.quantity,
            price: item.price,
            discount: item.discount
        }))
    };
    
    return data;
}

// ===== Print Preview =====
function showPrintPreview() {
    const data = exportInvoiceData();
    const errors = validateInvoiceForm();
    
    if (errors.length > 0) {
        alert('الرجاء إكمال البيانات التالية:\n\n' + errors.join('\n'));
        return;
    }
    
    // Open print preview in new window
    const printWindow = window.open('', '_blank', 'width=800,height=600');
    
    // Generate print HTML
    const printHtml = generatePrintHTML(data);
    
    printWindow.document.write(printHtml);
    printWindow.document.close();
    printWindow.focus();
}

// ===== Generate Print HTML =====
function generatePrintHTML(data) {
    const customerName = $('#customerSelect option:selected').text();
    const subtotal = items.reduce((sum, item) => sum + item.total, 0);
    const taxTotal = items.reduce((sum, item) => sum + item.tax, 0);
    const grandTotal = subtotal + taxTotal - data.discount;
    
    let itemsHtml = '';
    items.forEach((item, index) => {
        itemsHtml += `
            <tr>
                <td>${index + 1}</td>
                <td>${item.product_name}</td>
                <td>${item.quantity}</td>
                <td>${item.price.toFixed(2)}</td>
                <td>${(item.quantity * item.price).toFixed(2)}</td>
            </tr>
        `;
    });
    
    return `
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>معاينة الفاتورة</title>
            <style>
                body { font-family: 'Cairo', Arial, sans-serif; padding: 20px; }
                .invoice-header { text-align: center; margin-bottom: 30px; }
                table { width: 100%; border-collapse: collapse; }
                th, td { border: 1px solid #ddd; padding: 10px; text-align: center; }
                th { background: #1e3a5f; color: white; }
                .totals { margin-top: 20px; text-align: left; }
                .totals div { margin: 5px 0; }
                @media print {
                    .no-print { display: none; }
                }
            </style>
        </head>
        <body>
            <div class="invoice-header">
                <h1>فاتورة مبيعات</h1>
                <p>التاريخ: ${data.date}</p>
                <p>العميل: ${customerName}</p>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>الصنف</th>
                        <th>الكمية</th>
                        <th>السعر</th>
                        <th>الإجمالي</th>
                    </tr>
                </thead>
                <tbody>
                    ${itemsHtml}
                </tbody>
            </table>
            
            <div class="totals">
                <div><strong>المجموع الفرعي:</strong> ${subtotal.toFixed(2)} ج.م</div>
                <div><strong>الضريبة:</strong> ${taxTotal.toFixed(2)} ج.م</div>
                <div><strong>الخصم:</strong> ${data.discount.toFixed(2)} ج.م</div>
                <div style="font-size: 20px; margin-top: 10px;">
                    <strong>الإجمالي النهائي:</strong> ${grandTotal.toFixed(2)} ج.م
                </div>
            </div>
            
            <div class="no-print" style="text-align: center; margin-top: 30px;">
                <button onclick="window.print()" style="padding: 10px 30px; font-size: 16px;">
                    طباعة
                </button>
                <button onclick="window.close()" style="padding: 10px 30px; font-size: 16px; margin-right: 10px;">
                    إغلاق
                </button>
            </div>
        </body>
        </html>
    `;
}

// ===== Duplicate Item =====
function duplicateItem(itemId) {
    const item = items.find(i => i.id === itemId);
    if (!item) return;
    
    itemCounter++;
    const newItem = { ...item, id: itemCounter };
    items.push(newItem);
    
    updateTable();
    updateTotals();
    
    showNotification('تم تكرار الصنف بنجاح', 'success');
}

// ===== Edit Item Inline =====
function editItemInline(itemId) {
    const item = items.find(i => i.id === itemId);
    if (!item) return;
    
    // Populate modal with item data
    $('#modalProduct').val(item.product_id).trigger('change');
    $('#modalLocation').val(item.location_id);
    $('#modalQuantity').val(item.quantity);
    $('#modalPrice').val(item.price);
    $('#modalDiscount').val(item.discount);
    
    // Remove old item
    items = items.filter(i => i.id !== itemId);
    updateTable();
    
    // Open modal
    $('#addItemModal').modal('show');
}

// ===== Bulk Add Items =====
function bulkAddItems() {
    // Feature for adding multiple items at once
    // To be implemented with a special modal
    showNotification('جاري تطوير ميزة الإضافة المجمعة...', 'info');
}

// ===== Export to Excel =====
function exportToExcel() {
    const data = exportInvoiceData();
    
    // Simple CSV export
    let csv = 'الصنف,الكمية,السعر,الخصم,الإجمالي\n';
    
    items.forEach(item => {
        csv += `"${item.product_name}",${item.quantity},${item.price},${item.discount},${item.total}\n`;
    });
    
    // Create download link
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `invoice_${Date.now()}.csv`;
    link.click();
    
    showNotification('تم تصدير البيانات بنجاح', 'success');
}

// ===== Initialize Advanced Features =====
$(document).ready(function() {
    // Override stock check to use AJAX
    window.checkStock = checkStockAjax;
    
    // Enhanced customer selection
    $('#customerSelect').on('change', function() {
        const customerId = $(this).val();
        if (customerId) {
            loadCustomerBalance(customerId);
        }
    });
    
    // Add print preview button
    $('.action-buttons').prepend(`
        <button type="button" class="btn btn-outline-info" onclick="showPrintPreview()">
            <i class="fas fa-print me-2"></i>
            معاينة الطباعة
        </button>
    `);
});

// Make functions globally accessible
window.addByBarcode = addByBarcode;
window.loadLastInvoice = loadLastInvoice;
window.loadTemplate = loadTemplate;
window.showPrintPreview = showPrintPreview;
window.duplicateItem = duplicateItem;
window.editItemInline = editItemInline;
window.bulkAddItems = bulkAddItems;
window.exportToExcel = exportToExcel;
