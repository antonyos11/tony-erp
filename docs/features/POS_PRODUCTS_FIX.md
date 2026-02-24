# إصلاح مشكلة عدم ظهور المنتجات وعدم إضافتها للسلة في نقطة البيع (POS)

## المشاكل المكتشفة

### 1. عدم ظهور جميع المنتجات
كانت نقطة البيع تعرض فقط 100 منتج كحد أقصى، مما أدى إلى عدم ظهور المنتجات الموجودة في المخزن إذا كان عددها أكثر من 100.

### 2. عدم إضافة المنتجات للسلة
عند الضغط على المنتجات، لم تكن تُضاف للسلة بسبب استخدام حقل `quantity` الذي لا يوجد في موديل Product. الحقل الصحيح هو property اسمه `current_stock`.

## الحلول المطبقة

### 1. إصلاح حد عرض المنتجات
**الملف**: `/var/www/tony_erp/pos/views.py` في دالة `pay_order`

```python
# الكود القديم - كان يحد من عرض 100 منتج فقط
products = Product.objects.all().select_related('category')[:100]
```

**الكود الجديد**:
```python
from django.db.models import Sum, Q
from inventory.models import Stock

# الحصول على المنتجات التي لديها مخزون
product_ids_with_stock = Stock.objects.filter(
    quantity__gt=0
).values_list('product_id', flat=True).distinct()

# جلب المنتجات النشطة التي لديها مخزون أو جميع المنتجات للسوبر يوزر
if request.user.is_superuser or request.user.is_staff:
    # عرض جميع المنتجات للأدمن (بحد أقصى معقول)
    products = Product.objects.all().select_related('category').order_by('-id')[:500]
else:
    # عرض المنتجات التي لها مخزون فقط
    products = Product.objects.filter(
        id__in=product_ids_with_stock
    ).select_related('category').order_by('-id')
```

### 2. إصلاح استخدام حقل المخزون في القالب
**الملف**: `/var/www/tony_erp/templates/pos/pos_main.html`

تم تغيير جميع مراجع `product.quantity` إلى `product.current_stock`:

```html
<!-- القديم -->
data-stock="{{ product.quantity|default:0 }}"
<span>{% trans 'متوفر:' %} {{ product.quantity|default:0 }}</span>

<!-- الجديد -->
data-stock="{{ product.current_stock|default:0 }}"
<span>{% trans 'متوفر:' %} {{ product.current_stock|default:0 }}</span>
```

### 3. إصلاح API المفضلة والأكثر مبيعاً
**الملف**: `/var/www/tony_erp/pos/views_enhanced.py`

تم إصلاح دالة `list_favorites` ودالة `recent_products`:

```python
# تغيير في list_favorites
'stock': f.product.current_stock or 0,  # بدلاً من quantity

# تغيير في recent_products
'stock': prod.current_stock or 0,  # بدلاً من quantity
```

## المزايا الجديدة

✅ **عرض جميع المنتجات المتاحة**: لم يعد هناك حد 100 منتج للمستخدمين العاديين
✅ **فلترة ذكية**: يعرض فقط المنتجات التي لها مخزون متاح (quantity > 0)
✅ **صلاحيات للأدمن**: المدراء والسوبر يوزر يمكنهم رؤية حتى 500 منتج
✅ **أداء محسّن**: استخدام `select_related` لتقليل استعلامات قاعدة البيانات
✅ **ترتيب واضح**: المنتجات مرتبة من الأحدث إلى الأقدم
✅ **إضافة للسلة تعمل**: المنتجات الآن يمكن إضافتها للسلة بنقرة واحدة
✅ **عرض المخزون الصحيح**: يعرض الكمية الفعلية من جدول Stock

## الملفات المعدلة

1. `/var/www/tony_erp/pos/views.py` - دالة `pay_order`
2. `/var/www/tony_erp/templates/pos/pos_main.html` - HTML template
3. `/var/www/tony_erp/pos/views_enhanced.py` - دالتي `list_favorites` و `recent_products`

## الاختبار

بعد التطبيق:
1. ✅ قم بفتح نقطة البيع
2. ✅ تحقق من ظهور جميع المنتجات التي لديها مخزون
3. ✅ اضغط على منتج للتأكد من إضافته للسلة
4. ✅ جرب البحث والفلترة حسب الفئات
5. ✅ تأكد من أن المنتجات بدون مخزون لا تظهر للمستخدمين العاديين
6. ✅ جرب المفضلة والأكثر مبيعاً

## تاريخ الإصلاح
- **التاريخ**: 16 يناير 2026
- **الوقت**: بعد الظهر

## ملاحظات تقنية
- موديل `Product` يستخدم property اسمه `current_stock` الذي يحسب المخزون من جدول `Stock`
- موديل `Product` يستخدم property اسمه `sale_price` الذي يعيد قيمة حقل `price`
- يمكن زيادة حد 500 منتج للأدمن إذا لزم الأمر
- المنتجات بدون مخزون لن تظهر للمستخدمين العاديين
- السوبر يوزر يرى جميع المنتجات بغض النظر عن المخزون
