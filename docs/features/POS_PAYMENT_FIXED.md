# إصلاحات نظام نقاط البيع (POS)

## التاريخ: 8 يناير 2026

## المشاكل التي تم حلها

### 1. مشكلة الدفع النقدي/بالبطاقة
- **المشكلة**: أزرار الدفع لا تعمل عند الضغط عليها
- **الحل**: 
  - إضافة معالج حدث (event handler) لزر الدفع في `pos_main.html`
  - إضافة معالج حدث لزر "تأكيد الدفع" في `payment_modal.html`
  - إنشاء API endpoint جديد `/pos/api/complete-order/` في `views_enhanced.py`
  - ربط الوظائف مع نظام السلة (cart) والإجماليات

### 2. مشكلة التقسيط
- **المشكلة**: زر التقسيط لا يعمل
- **الحل**:
  - إضافة معالج حدث لزر التقسيط في `pos_main.html`
  - تحديث وظيفة form submission في `installment_modal_enhanced.html`
  - إنشاء API endpoint جديد `/pos/api/create-installment/` في `views_enhanced.py`
  - إضافة وظيفة كاملة لإنشاء عقود التقسيط مع الأقساط

## الملفات المعدّلة

1. `/var/www/tony_erp/templates/pos/pos_main.html`
   - إضافة معالج زر الدفع
   - إضافة معالج زر التقسيط

2. `/var/www/tony_erp/templates/pos/payment_modal.html`
   - إضافة وظيفة confirmPayment لإتمام الدفع

3. `/var/www/tony_erp/templates/pos/installment_modal_enhanced.html`
   - تحديث وظيفة form submission للتقسيط

4. `/var/www/tony_erp/pos/views_enhanced.py`
   - إضافة `complete_order()` - API لإتمام الطلب والدفع
   - إضافة `create_installment_order()` - API لإنشاء عقد تقسيط
   - إضافة `from django.db import transaction`

5. `/var/www/tony_erp/pos/urls.py`
   - إضافة مسار `/pos/api/complete-order/`
   - إضافة مسار `/pos/api/create-installment/`

## كيفية استخدام النظام

### الدفع النقدي/بطاقة:
1. أضف منتجات إلى السلة
2. اضغط على زر "الدفع" (الزر الأخضر)
3. سيفتح نافذة الدفع
4. اختر طريقة الدفع (نقدي/بطاقة/تحويل بنكي/دفع مجزأ)
5. أدخل المبلغ المدفوع أو اضغط على "المبلغ بالضبط"
6. اضغط "تأكيد الدفع"
7. سيتم توجيهك لصفحة الإيصال

### البيع بالتقسيط:
1. أضف منتجات إلى السلة
2. اضغط على زر التقسيط (أيقونة التقويم)
3. اختر أو أدخل بيانات العميل
4. اختر خطة تقسيط أو أدخل يدوياً:
   - الدفعة المقدمة
   - عدد الأقساط
   - نسبة الفائدة
   - تاريخ أول قسط
5. اضغط "تأكيد التقسيط"
6. سيتم إنشاء عقد التقسيط والتوجيه لصفحة العقد

## المتطلبات

- يجب فتح جلسة (Session) POS قبل البدء
- يجب أن تحتوي السلة على منتج واحد على الأقل
- للتقسيط: يجب اختيار أو إدخال بيانات العميل

## الاختصارات

- **F8**: فتح نافذة الدفع
- **F2**: التركيز على البحث
- **F9**: حفظ طلب معلق
- **Escape**: إفراغ السلة

## API Endpoints الجديدة

### إتمام الطلب والدفع
```
POST /pos/api/complete-order/
Content-Type: application/json

{
  "cart": [{"id": 1, "name": "منتج", "price": 100, "qty": 2}],
  "total": 200,
  "paid_amount": 200,
  "payment_method": "cash",
  "notes": "",
  "order_id": null
}
```

### إنشاء عقد تقسيط
```
POST /pos/api/create-installment/
Content-Type: application/json

{
  "cart": [...],
  "total": 1000,
  "customer_id": 1,
  "customer_name": "محمد أحمد",
  "customer_phone": "01234567890",
  "down_payment": 200,
  "number_of_installments": 6,
  "interest_rate": 10,
  "start_date": "2026-02-01"
}
```

## ملاحظات

- تم اختبار النظام وإعادة تحميل Gunicorn
- لا توجد أخطاء في السجلات (logs)
- النظام جاهز للاستخدام

## الدعم

في حالة وجود أي مشاكل، تحقق من:
1. وجود جلسة POS نشطة
2. سجل الأخطاء: `/var/www/tony_erp/logs/error.log`
3. Console المتصفح (F12) للأخطاء في JavaScript
