![صلخ](image.png)# إصلاح مشكلة "خطأ في الاتصال" في نقطة البيع

## المشكلة
عند محاولة إضافة منتج إلى السلة في صفحة نقطة البيع، يظهر خطأ "خطأ في الاتصال" ولا تتم إضافة المنتج.

## الأسباب المحتملة
1. **مشكلة في CSRF Token** - عدم إرسال رمز الأمان بشكل صحيح
2. **مشكلة في الصلاحيات** - المستخدم ليس لديه صلاحية إضافة منتجات
3. **مشكلة في الاتصال بالخادم** - انقطاع الإنترنت أو مشكلة في الخادم
4. **خطأ في قاعدة البيانات** - مشكلة في جدول المنتجات أو الطلبات

## التحسينات التي تم تطبيقها

### 1. تحسين معالجة الأخطاء في JavaScript
- ✅ إضافة رسائل خطأ واضحة ومفصلة
- ✅ التحقق من وجود CSRF Token قبل إرسال الطلب
- ✅ معالجة أخطاء الشبكة بشكل أفضل
- ✅ إضافة معلومات تشخيصية في console المتصفح

### 2. تحسين رسائل الخطأ في Backend
- ✅ رسائل خطأ أكثر وضوحاً في `add_line`, `delete_line`, `update_line_qty`
- ✅ السماح للسوبر يوزر بتجاوز فحص الصلاحيات
- ✅ إضافة logging للأخطاء

### 3. إضافة آلية استرجاع CSRF Token
- ✅ محاولة الحصول على التوكن من الصفحة إذا لم يكن متاحاً
- ✅ محاولة الحصول على التوكن من الكوكيز
- ✅ عرض تحذير للمستخدم إذا كان التوكن مفقوداً

## كيفية التشخيص

### 1. افتح Console المتصفح
اضغط `F12` في المتصفح وانتقل إلى تبويب **Console**

### 2. ابحث عن الرسائل التالية عند تحميل الصفحة:
```
🚀 POS Page Loaded - DOMContentLoaded fired
📍 Order ID will be: [رقم الطلب]
✅ ORDER_ID set to: [رقم الطلب]
🔑 CSRF Token: [جزء من التوكن]...
```

### 3. عند النقر على منتج، ابحث عن:
```
🔵 Product card clicked!
📦 Product: {id: ..., name: ..., price: ..., stock: ...}
🚀 Calling addToCart...
✅ addToCart called with: {id: ..., name: ..., price: ...}
```

### 4. رسائل الخطأ المحتملة

#### إذا ظهر: `❌ CSRF Token is missing!`
**الحل:**
```bash
# تأكد من أن الصفحة تحتوي على CSRF token
# افتح ملف pos_main.html وتأكد من وجود:
window.csrfToken = '{{ csrf_token }}';
```

#### إذا ظهر: `❌ غير مسموح - ليس لديك صلاحية إضافة منتجات`
**الحل:**
```python
# امنح المستخدم صلاحية POS
from django.contrib.auth.models import User
user = User.objects.get(username='USERNAME')
user.is_staff = True
user.save()

# أو اجعله superuser
user.is_superuser = True
user.save()
```

#### إذا ظهر: `❌ خطأ في الاتصال بالخادم. تحقق من الإنترنت`
**الحل:**
1. تحقق من اتصال الإنترنت
2. تأكد من أن الخادم يعمل: `sudo systemctl status nginx`
3. تحقق من logs: `sudo tail -f /var/log/nginx/error.log`

#### إذا ظهر: `❌ المنتج غير موجود`
**الحل:**
```python
# تأكد من أن المنتج موجود في قاعدة البيانات
from inventory.models import Product
Product.objects.filter(id=PRODUCT_ID).exists()
```

## كيفية الاختبار

### 1. أعد تحميل الصفحة
اضغط `Ctrl+F5` لإعادة تحميل الصفحة بالكامل (تجاهل الكاش)

### 2. افتح Console وراقب الرسائل

### 3. جرب إضافة منتج
- انقر على أي بطاقة منتج
- راقب الرسائل في Console
- يجب أن تظهر رسالة نجاح: `✅ تم إضافة [اسم المنتج] إلى السلة`

### 4. اختبر تحديث الكمية
- اضغط على `+` أو `-` في السلة
- يجب أن تظهر: `✅ تم تحديث الكمية`

### 5. اختبر حذف منتج
- اضغط على أيقونة 🗑️ بجانب المنتج
- يجب أن تظهر: `🗑️ تم حذف [اسم المنتج]`

## استكشاف الأخطاء المتقدم

### فحص الطلبات في Network Tab

1. افتح **Network Tab** في Developer Tools
2. قم بإضافة منتج
3. ابحث عن طلب `/pos/order/[ID]/add-line/`
4. اضغط عليه وافحص:
   - **Headers**: تأكد من وجود `X-CSRFToken`
   - **Payload**: تأكد من إرسال `code` و `qty`
   - **Response**: انظر إلى رد الخادم

### فحص السجلات (Logs)

```bash
# Django logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# إذا كنت تستخدم supervisor
sudo supervisorctl tail -f tony_erp

# أو مباشرة من Django
python manage.py runserver
```

## الحل النهائي

إذا استمرت المشكلة بعد كل ما سبق:

1. **أعد تشغيل الخادم:**
```bash
sudo systemctl restart nginx
sudo systemctl restart tony_erp  # أو gunicorn/uwsgi
```

2. **امسح الكاش:**
```bash
# في Django
python manage.py collectstatic --noinput --clear
```

3. **تحقق من قاعدة البيانات:**
```bash
python manage.py dbshell
SELECT * FROM pos_posorder WHERE id = [ORDER_ID];
SELECT * FROM pos_posorderline WHERE order_id = [ORDER_ID];
```

4. **أعد إنشاء الطلب:**
- اذهب إلى `/pos/order/new/` لإنشاء طلب جديد
- جرب إضافة منتج مرة أخرى

## نصائح إضافية

### للسوبر يوزر
- السوبر يوزر لديه صلاحيات كاملة ويتجاوز جميع فحوصات الصلاحيات
- استخدم حساب superuser للاختبار: `python manage.py createsuperuser`

### للمطورين
- استخدم `console.log()` لمتابعة تدفق الكود
- استخدم breakpoints في Chrome DevTools للتوقف عند نقاط محددة
- راجع ملف `pos/views.py` للتأكد من المنطق الصحيح

## التحديثات

### التاريخ: 2026-01-17

✅ تحسين معالجة الأخطاء في addToCart
✅ تحسين معالجة الأخطاء في updateQty
✅ تحسين معالجة الأخطاء في removeItem
✅ إضافة رسائل خطأ واضحة في Backend
✅ السماح للسوبر يوزر بتجاوز فحص الصلاحيات
✅ إضافة آلية استرجاع CSRF Token التلقائية
✅ تحسين رسائل console للتشخيص

## اتصل بنا

إذا استمرت المشكلة، يرجى إرسال:
1. لقطة شاشة من Console
2. لقطة شاشة من Network Tab
3. معلومات المستخدم (username, is_staff, is_superuser)
4. رقم الطلب (Order ID)

---
**ملاحظة:** جميع التحسينات تم تطبيقها تلقائياً. فقط أعد تحميل الصفحة لرؤية التحسينات.
