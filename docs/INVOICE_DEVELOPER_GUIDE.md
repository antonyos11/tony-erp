# 👨‍💻 دليل المطور - صفحة الفاتورة المحسّنة

## البنية التقنية

### الملفات الأساسية

```
tony_erp/
├── templates/sales/
│   └── invoice_form_enhanced.html     # القالب الرئيسي
├── static/js/
│   └── invoice_enhanced.js            # JavaScript المتقدم
├── sales/
│   ├── urls.py                        # URLs
│   └── views.py                       # Views
└── docs/
    ├── INVOICE_ENHANCED_GUIDE.md      # دليل المستخدم
    ├── INVOICE_ENHANCED_SUMMARY.md    # ملخص التطوير
    ├── INVOICE_QUICK_START.md         # البدء السريع
    └── INVOICE_COMPARISON.md          # المقارنة
```

---

## 🔧 التثبيت والإعداد

### المتطلبات:
```python
# requirements.txt
Django>=3.2
djangorestframework
```

### مكتبات JavaScript (CDN):
```html
<!-- Bootstrap 5 RTL -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">

<!-- Select2 -->
<link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css">

<!-- Font Awesome -->
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<!-- jQuery -->
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>

<!-- Select2 JS -->
<script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
```

---

## 📁 هيكل القالب

### الأقسام الرئيسية:

```html
<!DOCTYPE html>
<html dir="rtl">
<head>
    <!-- CSS Libraries -->
</head>
<body>
    <!-- 1. Header -->
    <div class="page-header">...</div>
    
    <!-- 2. Form Container -->
    <div class="container-fluid">
        <form id="invoiceForm">
            
            <!-- 3. Barcode Scanner -->
            <div class="barcode-section">...</div>
            
            <!-- 4. Invoice Data -->
            <div class="form-card">...</div>
            
            <!-- 5. Products Table -->
            <div class="form-card">
                <table id="productsTable">...</table>
            </div>
            
            <!-- 6. Totals Box -->
            <div class="totals-box">...</div>
            
        </form>
    </div>
    
    <!-- 7. Add Item Modal -->
    <div class="modal" id="addItemModal">...</div>
    
    <!-- 8. JavaScript -->
    <script src="invoice_enhanced.js"></script>
</body>
</html>
```

---

## 🎯 الوظائف الرئيسية

### JavaScript Functions:

#### 1. initializeSelect2()
```javascript
function initializeSelect2() {
    $('.select2-customer').select2({
        theme: 'bootstrap-5',
        dir: 'rtl',
        language: 'ar',
        placeholder: '--- ابحث عن عميل ---',
        allowClear: true,
        width: '100%'
    });
}
```

#### 2. addByBarcode()
```javascript
function addByBarcode() {
    const barcode = $('#barcodeInput').val().trim();
    // AJAX call to search product
    $.ajax({
        url: '/api/products/search-barcode/',
        data: { barcode: barcode },
        success: function(product) {
            addItemDirectly(product);
        }
    });
}
```

#### 3. calculateModalTotal()
```javascript
function calculateModalTotal() {
    const quantity = parseFloat($('#modalQuantity').val());
    const price = parseFloat($('#modalPrice').val());
    const discount = parseFloat($('#modalDiscount').val());
    
    const subtotal = quantity * price;
    const discountAmount = subtotal * (discount / 100);
    const total = subtotal - discountAmount;
    
    $('#modalTotal').val(total.toFixed(2) + ' ج.م');
}
```

#### 4. updateTotals()
```javascript
function updateTotals() {
    const subtotal = items.reduce((sum, item) => sum + item.total, 0);
    const additionalDiscount = parseFloat($('#additionalDiscount').val());
    const taxAmount = items.reduce((sum, item) => sum + item.tax, 0);
    const grandTotal = subtotal - additionalDiscount + taxAmount;
    
    $('#grandTotal').text(grandTotal.toFixed(2) + ' ج.م');
}
```

#### 5. saveDraftToLocalStorage()
```javascript
function saveDraftToLocalStorage() {
    const draft = {
        customer: $('#customerSelect').val(),
        date: $('#invoiceDate').val(),
        items: items,
        timestamp: new Date().toISOString()
    };
    
    localStorage.setItem('invoice_draft', JSON.stringify(draft));
}
```

---

## 🔌 API Endpoints المطلوبة

### يجب إنشاء هذه الـ Endpoints:

#### 1. البحث بالباركود
```python
# sales/api_views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def search_barcode(request):
    barcode = request.GET.get('barcode')
    
    try:
        product = Product.objects.get(sku=barcode)
        
        return Response({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'stock': get_product_stock(product)
            }
        })
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'message': 'المنتج غير موجود'
        })
```

#### 2. التحقق من المخزون
```python
@api_view(['GET'])
def check_stock(request):
    product_id = request.GET.get('product_id')
    location_id = request.GET.get('location_id')
    
    try:
        stock = Stock.objects.get(
            product_id=product_id,
            location_id=location_id
        )
        
        return Response({
            'success': True,
            'stock': float(stock.quantity)
        })
    except Stock.DoesNotExist:
        return Response({
            'success': True,
            'stock': 0
        })
```

#### 3. رصيد العميل
```python
@api_view(['GET'])
def customer_balance(request):
    customer_id = request.GET.get('customer_id')
    
    customer = Customer.objects.get(id=customer_id)
    
    return Response({
        'success': True,
        'balance': float(customer.balance or 0),
        'credit_limit': float(customer.credit_limit or 0)
    })
```

#### 4. آخر فاتورة
```python
@api_view(['GET'])
def last_invoice(request):
    invoice = Invoice.objects.filter(
        customer__isnull=False
    ).order_by('-id').first()
    
    if not invoice:
        return Response({'success': False})
    
    items = [{
        'product_id': item.product.id,
        'product_name': item.product.name,
        'location_id': item.location.id,
        'location_name': item.location.name,
        'quantity': float(item.quantity),
        'price': float(item.price),
        'discount': float(item.discount or 0),
        'tax': float(item.tax or 0),
        'total': float(item.total)
    } for item in invoice.items.all()]
    
    return Response({
        'success': True,
        'invoice': {
            'customer_id': invoice.customer.id,
            'payment_method_id': invoice.payment_method.id if invoice.payment_method else None,
            'discount': float(invoice.discount),
            'notes': invoice.notes,
            'items': items
        }
    })
```

---

## 🔗 إضافة URLs للـ API

```python
# sales/urls.py
from .api_views import search_barcode, check_stock, customer_balance, last_invoice

urlpatterns = [
    # ... existing urls ...
    
    # Enhanced Invoice APIs
    path('api/products/search-barcode/', search_barcode, name='api_search_barcode'),
    path('api/inventory/check-stock/', check_stock, name='api_check_stock'),
    path('api/customers/balance/', customer_balance, name='api_customer_balance'),
    path('api/sales/last-invoice/', last_invoice, name='api_last_invoice'),
]
```

---

## 🎨 تخصيص التصميم

### الألوان الرئيسية:

```css
:root {
    --primary: #1e3a5f;
    --secondary: #2d5a87;
    --success: #28a745;
    --danger: #dc3545;
    --warning: #ffc107;
    --info: #17a2b8;
    --purple: #6f42c1;
}
```

### تغيير الألوان:

```css
/* Header */
.page-header {
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
}

/* Barcode Section */
.barcode-section {
    background: linear-gradient(135deg, var(--success) 0%, #20c997 100%);
}

/* Totals Box */
.totals-box {
    background: linear-gradient(135deg, var(--purple) 0%, #8b5cf6 100%);
}
```

---

## 🔄 دورة حياة البيانات

### 1. تحميل الصفحة:
```
User → Page Load → Initialize Select2 → Load Draft (if exists)
```

### 2. إضافة صنف:
```
User → Select Product → Auto-fill Price → Enter Quantity → Calculate Total → Add to Array
```

### 3. الحفظ التلقائي:
```
setInterval(30s) → Collect Form Data → Save to LocalStorage → Show Indicator
```

### 4. الإرسال:
```
Submit Form → Validate Data → POST to Server → Clear Draft → Redirect
```

---

## 🧪 الاختبار

### اختبار وحدات (Unit Tests):

```python
# tests/test_invoice_enhanced.py
from django.test import TestCase
from django.urls import reverse

class InvoiceEnhancedTest(TestCase):
    
    def test_page_loads(self):
        response = self.client.get(reverse('sales:invoice_create_enhanced'))
        self.assertEqual(response.status_code, 200)
    
    def test_search_barcode_api(self):
        # Create test product
        product = Product.objects.create(
            name='Test Product',
            sku='12345',
            price=100
        )
        
        response = self.client.get('/api/products/search-barcode/', {
            'barcode': '12345'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['product']['name'], 'Test Product')
```

### اختبار تكامل (Integration Tests):

```javascript
// tests/test_invoice_enhanced.js
describe('Invoice Enhanced', function() {
    
    it('should initialize Select2', function() {
        expect($('.select2-customer').hasClass('select2-hidden-accessible')).toBe(true);
    });
    
    it('should add item to invoice', function() {
        const initialCount = items.length;
        addItemToInvoice();
        expect(items.length).toBe(initialCount + 1);
    });
    
    it('should calculate totals correctly', function() {
        items = [{
            quantity: 2,
            price: 100,
            discount: 0,
            tax: 30,
            total: 200
        }];
        updateTotals();
        expect($('#grandTotal').text()).toBe('230.00 ج.م');
    });
});
```

---

## 🐛 تتبع الأخطاء (Debugging)

### تفعيل Console Logs:

```javascript
// في أعلى invoice_enhanced.js
const DEBUG = true;

function log(message, data) {
    if (DEBUG) {
        console.log(`[Invoice Enhanced] ${message}`, data);
    }
}

// الاستخدام:
function addItemToInvoice() {
    log('Adding item', { product: productId, quantity: quantity });
    // ... code ...
}
```

### تتبع الأخطاء في الـ Backend:

```python
# في views.py
import logging

logger = logging.getLogger(__name__)

def invoice_create(request, template=None):
    logger.info(f'Invoice create accessed with template: {template}')
    
    try:
        # ... code ...
    except Exception as e:
        logger.error(f'Error creating invoice: {str(e)}', exc_info=True)
        messages.error(request, 'حدث خطأ غير متوقع')
```

---

## 📈 تحسين الأداء

### 1. تحميل كسول (Lazy Loading):

```javascript
// تحميل Select2 فقط عند الحاجة
function lazyLoadSelect2() {
    if (!$('.select2-customer').hasClass('select2-hidden-accessible')) {
        initializeSelect2();
    }
}
```

### 2. Debouncing للبحث:

```javascript
// تأخير البحث لتقليل الطلبات
let searchTimeout;
$('#searchInput').on('input', function() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        performSearch($(this).val());
    }, 300); // 300ms delay
});
```

### 3. تخزين مؤقت (Caching):

```javascript
// تخزين نتائج البحث المتكررة
const searchCache = {};

function searchProduct(query) {
    if (searchCache[query]) {
        return Promise.resolve(searchCache[query]);
    }
    
    return $.ajax({...}).then(result => {
        searchCache[query] = result;
        return result;
    });
}
```

---

## 🔐 الأمان

### 1. CSRF Protection:

```html
<form method="post" id="invoiceForm">
    {% csrf_token %}
    <!-- ... -->
</form>
```

### 2. XSS Prevention:

```javascript
// تنظيف المدخلات
function sanitizeInput(input) {
    return $('<div>').text(input).html();
}

// الاستخدام:
const safeName = sanitizeInput(productName);
```

### 3. Validation:

```javascript
function validateInvoiceForm() {
    const errors = [];
    
    // التحقق من العميل
    if (!$('#customerSelect').val()) {
        errors.push('الرجاء اختيار عميل');
    }
    
    // التحقق من الأصناف
    if (items.length === 0) {
        errors.push('الرجاء إضافة صنف واحد على الأقل');
    }
    
    // التحقق من الكميات
    if (items.some(item => item.quantity <= 0)) {
        errors.push('يوجد أصناف بكميات غير صحيحة');
    }
    
    return errors;
}
```

---

## 📚 موارد إضافية

### المكتبات المستخدمة:
- [Select2 Documentation](https://select2.org/)
- [Bootstrap 5 RTL](https://getbootstrap.com/)
- [Font Awesome Icons](https://fontawesome.com/)

### مراجع Django:
- [Django Forms](https://docs.djangoproject.com/en/stable/topics/forms/)
- [Django REST Framework](https://www.django-rest-framework.org/)

---

## 🤝 المساهمة

### إضافة ميزة جديدة:

1. Fork المشروع
2. إنشاء branch جديد
3. إضافة الميزة
4. اختبارها
5. إنشاء Pull Request

### الإبلاغ عن مشكلة:

1. GitHub Issues
2. وصف واضح للمشكلة
3. خطوات إعادة الإنتاج
4. لقطات شاشة (إن أمكن)

---

## 📞 الدعم الفني

- 📧 Email: dev@example.com
- 💬 Slack: #dev-team
- 📖 Wiki: wiki.example.com

---

**سعيد بالتطوير معك! 👨‍💻**

*آخر تحديث: 8 يناير 2026*
