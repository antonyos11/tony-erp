# 💰 دليل إدارة الموردين والأسعار

## 📋 المحتويات
1. [كيف يعمل النظام](#كيف-يعمل-النظام)
2. [إضافة مورد جديد](#إضافة-مورد-جديد)
3. [ربط المورد بالمنتجات](#ربط-المورد-بالمنتجات)
4. [تحديث الأسعار](#تحديث-الأسعار)
5. [أمثلة عملية](#أمثلة-عملية)

---

## 🎯 كيف يعمل النظام

### المفهوم الأساسي

```
مورد واحد ← يورد ← عدة منتجات
كل منتج ← يمكن شراؤه من ← عدة موردين
كل مورد ← له سعر خاص ← لكل منتج
```

### مثال: الإسفنج D18

```
إسفنج D18
├── المورد أ: 3,120 ج/م³ ⭐ (مفضل)
├── المورد ب: 3,200 ج/م³
└── المورد ج: 3,050 ج/م³
```

**النظام يختار:** المورد المفضل (⭐) عند حساب التكلفة

---

## 👥 إضافة مورد جديد

### الطريقة 1: من الواجهة

1. افتح: http://72.62.176.249/admin/partners/supplier/
2. اضغط "إضافة مورد"
3. املأ البيانات:
   ```
   الاسم: شركة الإسفنج المصري
   الكود: FOAM-SUP-EGY
   الهاتف: 01012345678
   نوع التوريد: خامات
   المادة الخام: إسفنج
   ```
4. احفظ

### الطريقة 2: من السكريبت

```python
from partners.models import Supplier

supplier = Supplier.objects.create(
    name='شركة الإسفنج المصري',
    code='FOAM-SUP-EGY',
    phone='01012345678',
    email='info@foam-egy.com',
    address='القاهرة',
    supply_type='raw_materials',
    raw_material='إسفنج',
)
```

---

## 🔗 ربط المورد بالمنتجات

### الطريقة 1: من الواجهة

#### أ) من صفحة المورد
1. افتح المورد
2. في قسم "منتجات المورد" اضغط "إضافة"
3. اختر المنتج
4. أدخل السعر
5. حدد إذا كان مفضل ⭐
6. احفظ

#### ب) من صفحة منتجات الموردين
1. افتح: http://72.62.176.249/admin/partners/supplierproduct/
2. اضغط "إضافة منتج مورد"
3. اختر المورد والمنتج
4. أدخل البيانات
5. احفظ

### الطريقة 2: من السكريبت

```python
from partners.models import Supplier, SupplierProduct
from inventory.models import Product
from decimal import Decimal

# الحصول على المورد والمنتج
supplier = Supplier.objects.get(code='FOAM-SUP-EGY')
product = Product.objects.get(sku='FOAM-D18')

# ربطهم
SupplierProduct.objects.create(
    supplier=supplier,
    product=product,
    supplier_sku='EGY-D18',  # كود المنتج عند المورد
    price=Decimal('3120'),   # السعر
    currency='EGP',
    minimum_order_quantity=Decimal('5'),  # 5 متر مكعب حد أدنى
    lead_time_days=3,        # 3 أيام توريد
    is_preferred=True,       # مورد مفضل ⭐
    is_active=True,
)
```

---

## 💰 تحديث الأسعار

### السيناريو: المورد رفع السعر

```
المورد أ اتصل وقال:
"سعر الإسفنج D18 بقى 3,200 ج بدل 3,120 ج"
```

### الطريقة 1: من الواجهة

1. افتح: http://72.62.176.249/admin/partners/supplierproduct/
2. ابحث عن: المورد أ + إسفنج D18
3. افتح السجل
4. غيّر السعر من 3,120 إلى 3,200
5. احفظ

✅ **إذا كان المورد مفضل:** تكلفة المنتج تتحدث تلقائياً!

### الطريقة 2: من السكريبت

```python
# افتح ملف: update_supplier_prices.py
# عدّل القائمة:

PRICE_UPDATES = [
    {
        'supplier_code': 'FOAM-SUP-A',
        'product_sku': 'FOAM-D18',
        'new_price': Decimal('3200'),  # ← السعر الجديد
    },
]

# ثم شغل:
# python manage.py shell < update_supplier_prices.py
```

---

## 📊 أمثلة عملية

### مثال 1: إضافة إسفنج من مورد جديد

```python
from partners.models import Supplier, SupplierProduct
from inventory.models import Product
from decimal import Decimal

# 1. إنشاء المورد
supplier = Supplier.objects.create(
    name='مصنع الإسفنج الحديث',
    code='FOAM-MODERN',
    phone='01098765432',
    supply_type='raw_materials',
    raw_material='إسفنج',
)

# 2. ربط المنتجات
foams = [
    ('FOAM-D18', Decimal('3100')),
    ('FOAM-D30', Decimal('4050')),
    ('FOAM-D35-SS', Decimal('4500')),
]

for sku, price in foams:
    product = Product.objects.get(sku=sku)
    SupplierProduct.objects.create(
        supplier=supplier,
        product=product,
        price=price,
        is_active=True,
    )

print(f"✅ تم ربط {len(foams)} منتج بالمورد {supplier.name}")
```

### مثال 2: تغيير المورد المفضل

```python
from partners.models import SupplierProduct
from inventory.models import Product

# المنتج
product = Product.objects.get(sku='FOAM-D18')

# إلغاء التفضيل من الجميع
SupplierProduct.objects.filter(
    product=product,
    is_preferred=True
).update(is_preferred=False)

# تفضيل مورد جديد (الأرخص مثلاً)
best = SupplierProduct.objects.filter(
    product=product,
    is_active=True
).order_by('price').first()

best.is_preferred = True
best.save()

# تحديث تكلفة المنتج
product.cost = best.price
product.save()

print(f"✅ المورد المفضل الآن: {best.supplier.name} بسعر {best.price} ج")
```

### مثال 3: مقارنة أسعار الموردين

```python
from partners.models import SupplierProduct
from inventory.models import Product

product = Product.objects.get(sku='FOAM-D18')

print(f"\n📊 أسعار {product.name} من الموردين:")
print("-" * 60)

suppliers = SupplierProduct.objects.filter(
    product=product,
    is_active=True
).order_by('price')

for sp in suppliers:
    preferred = "⭐ مفضل" if sp.is_preferred else ""
    print(f"   {sp.supplier.name}: {sp.price} ج/م³ {preferred}")
    if sp.lead_time_days:
        print(f"      مدة التوريد: {sp.lead_time_days} يوم")
```

---

## 🎯 الخلاصة

### ✅ المميزات

1. **مرونة**: نفس المنتج من عدة موردين
2. **سهولة**: تحديث الأسعار بسرعة
3. **تلقائي**: تحديث التكلفة عند تغيير سعر المورد المفضل
4. **تتبع**: معرفة آخر سعر شراء وتاريخه

### 📝 أفضل الممارسات

1. ✅ **حدد مورد مفضل** لكل منتج
2. ✅ **حدّث الأسعار** عند تغييرها في السوق
3. ✅ **سجل معلومات التوريد** (الحد الأدنى، مدة التوريد)
4. ✅ **قارن الأسعار** بين الموردين بانتظام

---

## 🔧 الملفات المساعدة

| الملف | الاستخدام |
|-------|-----------|
| `setup_foam_with_suppliers.py` | إعداد الإسفنج مع موردين |
| `update_supplier_prices.py` | تحديث الأسعار بسهولة |
| `SUPPLIER_PRICING_GUIDE.md` | هذا الدليل |

---

**💡 نصيحة:**
عند استلام عرض سعر جديد من مورد:
1. افتح `update_supplier_prices.py`
2. أضف الأسعار الجديدة
3. شغل السكريبت
4. ✅ تم!

