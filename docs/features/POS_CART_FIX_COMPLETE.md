# 🛒 إصلاح مزامنة سلة نقطة البيع

## المشكلة
كانت العناصر لا تُحذف من السلة عند الضغط على زر الحذف.

## السبب
كانت السلة تعمل محلياً فقط (JavaScript) بدون مزامنة مع قاعدة البيانات.

## الحلول المطبقة

### 1. تحميل العناصر من قاعدة البيانات
```javascript
{% for line in lines %}
cart.push({
    id: '{{ line.product.id }}',
    lineId: {{ line.id }},  // معرف البند في قاعدة البيانات
    name: '{{ line.product.name|escapejs }}',
    price: {{ line.price|default:line.product.price }},
    qty: {{ line.quantity }},
    isFromDB: true  // علامة أن هذا من قاعدة البيانات
});
{% endfor %}
```

### 2. دالة الحذف (removeItem)
- تحولت إلى `async function`
- تتحقق إذا كان العنصر من قاعدة البيانات (`isFromDB`)
- تستدعي API `/pos/order/{id}/line/{lineId}/delete/`
- تحذف من المصفوفة المحلية فقط بعد نجاح الحذف من الخادم

### 3. دالة تحديث الكمية (updateQty)
- تحولت إلى `async function`
- تستدعي API `/pos/order/{id}/line/{lineId}/update-qty/`
- تحديث محلي فقط بعد نجاح التحديث في الخادم

### 4. دالة الإضافة (addToCart)
- تحولت إلى `async function`
- تستدعي API `/pos/order/{id}/add-line/`
- تعيد تحميل الصفحة لجلب العنصر الجديد مع معرفه

### 5. دالة إفراغ السلة (clearCart)
- تحولت إلى `async function`
- تحذف جميع العناصر من قاعدة البيانات واحداً تلو الآخر
- ثم تفرغ المصفوفة المحلية

## الـ APIs المستخدمة

| العملية | URL | Method |
|---------|-----|--------|
| إضافة | `/pos/order/{order_id}/add-line/` | POST |
| حذف | `/pos/order/{order_id}/line/{line_id}/delete/` | POST |
| تحديث كمية | `/pos/order/{order_id}/line/{line_id}/update-qty/` | POST |

## الملفات المعدلة

1. `templates/pos/pos_main.html` - القالب الرئيسي
2. `pos/views.py` - إضافة `update_line_qty`
3. `pos/urls.py` - إضافة URL للتحديث

## اختبار النظام

1. افتح صفحة `/pos/order/{id}/pay/`
2. أضف منتجات للسلة
3. جرب زيادة/تقليل الكمية
4. جرب حذف عنصر
5. جرب إفراغ السلة

## تاريخ الإصلاح
- التاريخ: {{ date }}
- الإصدار: 2.1
