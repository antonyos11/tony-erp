# واجهة برمجية لوحدة الأسطول

تم إنشاء مجموعة REST API للوحدة عبر `djangorestframework`.

## المسارات الأساسية (مسبوقة بـ /api/fleet/)
- GET /vehicles/ — قائمة المركبات
- POST /vehicles/ — إنشاء مركبة
- GET /vehicles/{id}/ — تفاصيل مركبة
- PATCH/PUT /vehicles/{id}/ — تعديل
- DELETE /vehicles/{id}/ — حذف

نفس النمط للسائقين /drivers/، الرحلات /trips/، المصروفات /expenses/، المستندات /documents/.

## أمثلة معاملات الاستعلام
- /api/fleet/expenses/?vehicle=3&category=fuel
- /api/fleet/trips/?ordering=-start_time
- /api/fleet/vehicles/?search=ABC123

## الحقول
VehicleExpense يعيد journal_entry (id) إن وُجد القيد.
Trip يعيد duration_hours للقراءة.
Vehicle يعيد total_expenses (محسوب).

## المصادقة
تُطبق إعدادات المشروع العامة (JWT أو Session) حسب تهيئة REST_FRAMEWORK.

## ملاحظات
- تأكد من ضبط حسابات إعدادات محاسبة الأسطول إذا أردت القيد التلقائي.
- يمكن توسيع الصلاحيات لاحقاً بإذن مخصص لكل إجراء.
