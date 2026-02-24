# دليل تطوير نظام المشتريات المتقدم

## 📁 هيكل الملفات

```
purchases/
├── models.py                    # النماذج الأساسية (PurchaseBill, PurchaseOrder)
├── models_advanced.py           # النماذج المتقدمة (PR, RFQ, Quotation, Shipment)
├── views.py                     # العروض الأساسية
├── views_advanced.py            # العروض المتقدمة
├── admin.py                     # واجهة الإدارة الكاملة
├── urls.py                      # جميع الروابط
├── migrations/
│   ├── 0001_initial.py
│   ├── 0002_purchase_order.py
│   └── 0003_advanced_purchasing.py  # الهجرة الجديدة
└── templates/
    └── purchases/
        ├── pr/                  # قوالب طلبات الشراء
        ├── rfq/                 # قوالب RFQ
        ├── quotation/           # قوالب العروض
        ├── shipment/            # قوالب الشحنات
        ├── receipt/             # قوالب الاستلام
        └── reports/             # قوالب التقارير
```

---

## 🚀 البدء السريع

### 1. تطبيق الهجرة
```bash
python manage.py migrate purchases
```

### 2. إنشاء بيانات تجريبية (اختياري)
```python
from purchases.models_advanced import *
from partners.models import Supplier
from inventory.models import Product

# إنشاء طلب شراء
pr = PurchaseRequest.objects.create(
    department="المخازن",
    requested_by=user,
    priority="normal"
)

# إضافة بنود
PurchaseRequestItem.objects.create(
    request=pr,
    product=Product.objects.first(),
    quantity=100,
    estimated_price=50
)
```

---

## 🔧 الاستخدام البرمجي

### طلبات الشراء

```python
from purchases.models_advanced import PurchaseRequest, PurchaseRequestItem

# إنشاء طلب
pr = PurchaseRequest.objects.create(
    department="الإنتاج",
    requested_by=user,
    required_date=date.today() + timedelta(days=7),
    priority="urgent",
    justification="نفاد المخزون"
)

# إضافة بنود
for product, qty in items:
    PurchaseRequestItem.objects.create(
        request=pr,
        product=product,
        quantity=qty,
        estimated_price=product.cost
    )

# تغيير الحالة لقيد المراجعة
pr.status = 'pending'
pr.save()
```

### طلب عروض الأسعار

```python
from purchases.models_advanced import RFQ, RFQItem, RFQSupplier

# إنشاء RFQ
rfq = RFQ.objects.create(
    title="طلب عروض لمواد التعبئة",
    date=date.today(),
    deadline=date.today() + timedelta(days=10),
    created_by=user
)

# إضافة بنود من طلب الشراء
for pr_item in pr.items.all():
    RFQItem.objects.create(
        rfq=rfq,
        product=pr_item.product,
        quantity=pr_item.quantity,
        specifications=pr_item.specifications,
        target_price=pr_item.estimated_price
    )

# دعوة موردين
for supplier in Supplier.objects.filter(is_active=True):
    RFQSupplier.objects.create(
        rfq=rfq,
        supplier=supplier
    )

rfq.status = 'sent'
rfq.save()
```

### عروض الموردين

```python
from purchases.models_advanced import SupplierQuotation, QuotationItem

# إنشاء عرض سعر
quotation = SupplierQuotation.objects.create(
    rfq=rfq,
    supplier=supplier,
    quotation_date=date.today(),
    valid_until=date.today() + timedelta(days=30),
    delivery_time=15,
    shipping_cost=500
)

# إضافة بنود
for rfq_item in rfq.items.all():
    QuotationItem.objects.create(
        quotation=quotation,
        rfq_item=rfq_item,
        product=rfq_item.product,
        quantity=rfq_item.quantity,
        unit_price=calculate_price(rfq_item.product)
    )

quotation.status = 'submitted'
quotation.save()
```

### مقارنة العروض

```python
from django.db.models import Sum, F

# الحصول على جميع العروض لـ RFQ
quotations = rfq.quotations.all()

# حساب الإجماليات
for quotation in quotations:
    total = quotation.items.aggregate(
        subtotal=Sum(F('quantity') * F('unit_price'))
    )['subtotal']
    
    final_total = total + quotation.shipping_cost + quotation.tax_amount - quotation.discount
    
    print(f"{quotation.supplier.name}: {final_total}")

# اختيار الأفضل (حسب السعر)
best_quotation = min(quotations, key=lambda q: q.total)
best_quotation.status = 'accepted'
best_quotation.save()
```

### تحويل لأمر شراء

```python
from purchases.models import PurchaseOrder, PurchaseOrderItem

# تحويل PR المعتمد لأمر شراء
def convert_pr_to_po(pr, supplier, location):
    po = PurchaseOrder.objects.create(
        supplier=supplier,
        date=date.today(),
        expected_date=pr.required_date,
        notes=f"محوّل من {pr.number}",
        created_by=pr.requested_by
    )
    
    for item in pr.items.all():
        PurchaseOrderItem.objects.create(
            order=po,
            product=item.product,
            location=location,
            quantity=int(item.quantity),
            cost=item.estimated_price
        )
    
    pr.status = 'converted'
    pr.purchase_order = po
    pr.save()
    
    return po
```

### الشحنات

```python
from purchases.models_advanced import Shipment

# إنشاء شحنة
shipment = Shipment.objects.create(
    purchase_order=po,
    supplier=po.supplier,
    tracking_number="TRK123456",
    awb_bl_number="BL-001",
    shipped_date=date.today(),
    estimated_arrival=date.today() + timedelta(days=20),
    shipping_cost=2000
)

# تحديث الحالة
shipment.status = 'in_transit'
shipment.save()

# فحص التأخير
if shipment.is_delayed:
    send_alert(f"الشحنة {shipment.number} متأخرة")
```

### استلام الواردات

```python
from purchases.models_advanced import GoodsReceipt, GoodsReceiptItem

# إنشاء سند استلام
receipt = GoodsReceipt.objects.create(
    purchase_order=po,
    shipment=shipment,
    location=warehouse,
    received_by=user
)

# إضافة بنود مع فحص الكمية
for po_item in po.items.all():
    actual_received = get_actual_quantity(po_item)
    
    GoodsReceiptItem.objects.create(
        receipt=receipt,
        purchase_order_item=po_item,
        product=po_item.product,
        ordered_quantity=po_item.quantity,
        received_quantity=actual_received,
        accepted_quantity=actual_received * 0.98,  # 2% مرفوض
        rejected_quantity=actual_received * 0.02,
        quality_grade='good'
    )

receipt.status = 'completed'
receipt.save()
```

---

## 📊 الاستعلامات المفيدة

### طلبات الشراء المعلقة
```python
pending_prs = PurchaseRequest.objects.filter(
    status='pending'
).select_related('requested_by').order_by('-priority', 'date')
```

### RFQs النشطة
```python
active_rfqs = RFQ.objects.filter(
    status__in=['sent', 'received'],
    deadline__gte=date.today()
).select_related('created_by')
```

### أفضل العروض لكل RFQ
```python
from django.db.models import Min

best_quotes = SupplierQuotation.objects.values('rfq').annotate(
    min_total=Min('total')
)
```

### الشحنات المتأخرة
```python
delayed_shipments = Shipment.objects.filter(
    estimated_arrival__lt=date.today(),
    actual_arrival__isnull=True
).exclude(status__in=['received', 'cancelled'])
```

### سندات الاستلام مع اختلافات
```python
receipts_with_variance = GoodsReceipt.objects.filter(
    items__received_quantity__lt=F('items__ordered_quantity')
).distinct()
```

### السجل التاريخي للأسعار
```python
price_history = ProductPriceHistory.objects.filter(
    product=product,
    date__gte=date.today() - timedelta(days=365)
).select_related('supplier').order_by('-date')
```

---

## 🎯 أفضل الممارسات

### 1. استخدام Transactions
```python
from django.db import transaction

@transaction.atomic
def create_rfq_with_items(data):
    rfq = RFQ.objects.create(**data['rfq_data'])
    
    for item_data in data['items']:
        RFQItem.objects.create(rfq=rfq, **item_data)
    
    for supplier_id in data['supplier_ids']:
        RFQSupplier.objects.create(
            rfq=rfq,
            supplier_id=supplier_id
        )
    
    return rfq
```

### 2. التحميل المسبق
```python
# جيد
quotations = SupplierQuotation.objects.select_related(
    'rfq', 'supplier', 'evaluated_by'
).prefetch_related('items__product')

# سيئ
quotations = SupplierQuotation.objects.all()
for q in quotations:
    print(q.supplier.name)  # N+1 query
```

### 3. التجميعات بدلاً من الحلقات
```python
# جيد
total = quotation.items.aggregate(
    total=Sum(F('quantity') * F('unit_price'))
)['total']

# سيئ
total = sum(item.quantity * item.unit_price for item in quotation.items.all())
```

### 4. استخدام الفهارس
```python
# الفهارس موجودة بالفعل على:
# - status + date
# - supplier + product
# - tracking_number
# استخدمها في الاستعلامات
```

---

## 🧪 الاختبار

### اختبار طلب الشراء
```python
from django.test import TestCase
from purchases.models_advanced import PurchaseRequest

class PurchaseRequestTests(TestCase):
    def test_create_pr(self):
        pr = PurchaseRequest.objects.create(
            department="Test",
            requested_by=self.user,
            priority="normal"
        )
        self.assertEqual(pr.status, 'draft')
        self.assertTrue(pr.number.startswith('PR-'))
    
    def test_approve_pr(self):
        pr = PurchaseRequest.objects.create(
            department="Test",
            requested_by=self.user,
            status='pending'
        )
        pr.status = 'approved'
        pr.approved_by = self.manager
        pr.save()
        self.assertIsNotNone(pr.approved_at)
```

---

## 🔍 التصحيح والمراقبة

### تفعيل السجلات
```python
import logging

logger = logging.getLogger('purchases')

# في الكود
logger.info(f"PR {pr.number} created by {user}")
logger.warning(f"Shipment {shipment.number} is delayed")
logger.error(f"Failed to create quotation: {e}")
```

### مراقبة الأداء
```python
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def check_queries():
    quotations = SupplierQuotation.objects.select_related(
        'rfq', 'supplier'
    ).prefetch_related('items')[:10]
    
    list(quotations)  # تنفيذ الاستعلام
    print(f"Number of queries: {len(connection.queries)}")
```

---

## 🐛 حل المشاكل الشائعة

### مشكلة: الهجرة لا تعمل
```bash
python manage.py migrate purchases --fake-initial
python manage.py migrate purchases
```

### مشكلة: استيراد دائري
النماذج المتقدمة في ملف منفصل (`models_advanced.py`) لتجنب الاستيراد الدائري.

### مشكلة: بطء الاستعلامات
استخدم `select_related` و `prefetch_related`:
```python
# بطيء
for receipt in GoodsReceipt.objects.all():
    print(receipt.purchase_order.supplier.name)

# سريع
receipts = GoodsReceipt.objects.select_related(
    'purchase_order__supplier'
)
for receipt in receipts:
    print(receipt.purchase_order.supplier.name)
```

---

## 📚 الموارد الإضافية

- [توثيق النظام الكامل](./توثيق_نظام_المشتريات_المتقدم.md)
- [توثيق Django Models](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [توثيق Django QuerySets](https://docs.djangoproject.com/en/stable/ref/models/querysets/)

---

**ملاحظة**: هذا النظام قابل للتوسع. يمكنك إضافة ميزات جديدة حسب احتياجاتك.
