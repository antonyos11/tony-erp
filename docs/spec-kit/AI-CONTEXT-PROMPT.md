# 🤖 AI Context Prompt - السياق للذكاء الاصطناعي

> **الغرض:** نص سياق يمكن إعطاؤه لأي AI Agent جديد ليفهم النظام فوراً

---

## 📋 نسخ هذا السياق للـ AI

```
أنت تعمل على نظام Tony ERP، نظام إدارة موارد المؤسسات متكامل مبني على Django.

## معلومات النظام:
- الإطار: Django 5.2.x
- اللغة: Python 3.11+
- قاعدة البيانات: PostgreSQL
- Cache: Redis
- Task Queue: Celery
- API: Django REST Framework
- المسار: /var/www/tony_erp

## الأرقام الأساسية:
- 79-86 تطبيق (app)
- 629 موديل
- 5,839 URL
- 349 migration

## التطبيقات الأساسية:
- inventory: المخزون والمنتجات
- sales: المبيعات والفواتير
- purchases: المشتريات
- accounting: المحاسبة
- hr: الموارد البشرية
- crm: علاقات العملاء
- pos: نقاط البيع
- partners: العملاء والموردين
- users: الصلاحيات
- branches: الفروع
- core: الأدوات المشتركة

## القواعد المهمة:
1. لا تحذف migrations أبداً
2. لا تغير أسماء الحقول الموجودة
3. استخدم verbose_name بالعربية
4. استخدم DecimalField للأموال
5. اتبع الأنماط الموجودة في الكود
6. اختبر بـ python manage.py check قبل التعديل

## هيكل كل تطبيق:
app/
├── models.py      ← الموديلات
├── views.py       ← العرض
├── urls.py        ← المسارات
├── admin.py       ← لوحة الإدارة
├── forms.py       ← النماذج
├── serializers.py ← API
└── templates/app/ ← القوالب

## الملفات الأساسية:
- accountant_pro/settings.py ← الإعدادات
- accountant_pro/urls.py ← URLs الرئيسية
- templates/base.html ← القالب الأساسي

## أوامر مفيدة:
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py runserver

## التوثيق:
docs/spec-kit/AI-AGENT-GUIDE.md ← الدليل الكامل
docs/spec-kit/AI-NAVIGATION-MAP.md ← خريطة التنقل
docs/spec-kit/AI-RULES.md ← القواعد
docs/spec-kit/AI-QUICK-REFERENCE.md ← مرجع سريع
```

---

## 🎯 سياق مختصر (للنوافذ الصغيرة)

```
Tony ERP: Django 5.2, Python 3.11+, PostgreSQL, Redis, Celery, DRF
79 apps, 629 models, 5839 URLs
المسار: /var/www/tony_erp
الإعدادات: accountant_pro/settings.py

التطبيقات: inventory, sales, purchases, accounting, hr, crm, pos, partners, users, branches

القواعد:
- لا تحذف migrations
- verbose_name بالعربية
- DecimalField للأموال
- python manage.py check قبل التعديل

التوثيق: docs/spec-kit/AI-*.md
```

---

## 🔧 سياق للمهام المحددة

### للعمل على المخزون
```
أنت تعمل على وحدة المخزون في Tony ERP.

الموديلات الرئيسية:
- inventory.Product: المنتجات
- inventory.Category: الفئات
- inventory.Stock: المخزون
- inventory.Location: المواقع
- inventory.StockTransfer: تحويلات المخزون

الملفات:
- inventory/models.py
- inventory/views.py
- inventory/urls.py
- inventory/templates/inventory/

العلاقات:
Product → Category (FK)
Stock → Product (FK)
Stock → Location (FK)
```

### للعمل على المبيعات
```
أنت تعمل على وحدة المبيعات في Tony ERP.

الموديلات:
- sales.Invoice: فاتورة المبيعات
- sales.InvoiceItem: بنود الفاتورة
- sales.SaleOrder: أمر البيع
- sales.SaleOrderItem: بنود أمر البيع
- sales.SalesReturn: مرتجع مبيعات

الملفات:
- sales/models.py
- sales/views.py

العلاقات:
Invoice → Customer (FK from partners)
InvoiceItem → Invoice (FK)
InvoiceItem → Product (FK from inventory)
```

### للعمل على المحاسبة
```
أنت تعمل على وحدة المحاسبة في Tony ERP.

الموديلات:
- accounting.Account: الحسابات
- accounting.JournalEntry: القيود اليومية
- accounting.JournalEntryItem: بنود القيد
- accounting.FiscalYear: السنة المالية
- accounting.CostCenter: مراكز التكلفة

أنواع الحسابات:
- asset: أصول
- liability: خصوم
- equity: حقوق ملكية
- revenue: إيرادات
- expense: مصروفات

قاعدة: مجموع المدين = مجموع الدائن في كل قيد
```

### للعمل على الموارد البشرية
```
أنت تعمل على وحدة الموارد البشرية في Tony ERP.

الموديلات:
- hr.Employee: الموظفين
- hr.Department: الأقسام
- hr.JobPosition: المناصب
- hr.AttendanceRecord: سجلات الحضور
- hr.LeaveRequest: طلبات الإجازة
- hr.PayrollSlip: كشف الراتب

العلاقات:
Employee → Department (FK)
Employee → JobPosition (FK)
Employee → User (OneToOne)
```

### للعمل على نقاط البيع
```
أنت تعمل على وحدة نقاط البيع (POS) في Tony ERP.

الموديلات:
- pos.POSSession: جلسة البيع
- pos.POSOrder: الطلب
- pos.POSOrderLine: بند الطلب
- pos.POSPayment: الدفع
- pos.POSTable: الطاولات (للمطاعم)

سير العمل:
1. فتح جلسة (POSSession)
2. إنشاء طلبات (POSOrder)
3. إضافة بنود (POSOrderLine)
4. استلام الدفع (POSPayment)
5. إغلاق الجلسة
```

---

## 📝 قالب طلب مهمة

```
## المهمة
[وصف المهمة]

## الملفات المعنية
- [قائمة الملفات]

## المتطلبات
- [ ] متطلب 1
- [ ] متطلب 2

## ملاحظات
- اتبع الأنماط الموجودة
- اختبر قبل التطبيق
- راجع docs/spec-kit/AI-RULES.md
```

---

## ✅ قائمة تحقق للـ AI

```
قبل البدء:
□ هل قرأت AI-AGENT-GUIDE.md؟
□ هل فهمت هيكل المشروع؟
□ هل حددت الملفات المعنية؟

أثناء العمل:
□ هل أتبع الأنماط الموجودة؟
□ هل أضفت verbose_name بالعربية؟
□ هل استخدمت الموديلات الموجودة؟

بعد الانتهاء:
□ python manage.py check
□ اختبار الوظيفة
□ التحقق من عدم كسر شيء موجود
```

---

*آخر تحديث: يناير 2026*
