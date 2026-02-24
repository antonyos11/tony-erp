# دليل التدقيق (Audit) في Tony ERB

يوفر النظام سجل تدقيق شامل لكل عمليات الإنشاء/التعديل/الحذف، مع تتبّع المستخدم والوقت وعنوان IP والوكيل (User-Agent)، إضافةً لفروقات الحقول مع إخفاء الحقول الحساسة.

## ما الذي يتم تسجيله؟
- إنشاء/تعديل/حذف لكل النماذج الأساسية.
- تسجيل دخول/خروج المستخدمين.
- عنوان IP، المتصفح، وملخص الكائن.
- فروقات الحقول Field-level diff (old/new) مع إخفاء الحساس منها.

## الوصول للسجلات
- واجهة الويب: من قائمة النظام > سجلات التدقيق، أو بالرابط: `/audit-logs/`.
- API للقراءة فقط: `/api/audit-logs/` (بحث/ترشيح/ترقيم).

## الصلاحيات
- يلزم امتلاك صلاحية Django: `core.view_auditlog`.
- يوجد مجموعة جاهزة باسم: `auditors`؛ أضِف المستخدمين إليها أو امنحهم الصلاحية مباشرة.

خطوات سريعة (لوحة الإدارة):
1) ادخل إلى `/admin/` بحساب مشرف.
2) Users > اختر المستخدم.
3) Permissions > ابحث عن `Audit log | Can view audit log` أو أضِفه لمجموعة `auditors`.

## إخفاء الحقول الحساسة
- من صفحة إعدادات الشركة: الحقل “Audit sensitive fields”.
- أو من إعدادات Django: `AUDITLOG_SENSITIVE_FIELDS = ["tax_id", "phone", ...]`.
- عند الإنشاء: تُسجّل القيم الحساسة كـ `***`.
- عند التحديث: تُحسَب الفروقات بشكل دقيق ثم تُخفى القيم في السجل النهائي.

## التصدير والطباعة
- CSV: من صفحة السجلات اختر “تصدير CSV” أو استخدم `?format=csv`.
- XLSX: `?format=xlsx` (يتطلب openpyxl إن توفّر؛ خلاف ذلك يعود إلى CSV).
- طباعة: `?format=print`.

## الاحتفاظ والتنبيه
- إعداد مدة الاحتفاظ (أيام): من إعدادات الشركة `audit_retention_days` (مهمة تنظيف مجدولة).
- قواعد التنبيه: `audit_alert_rules` (حقول/نماذج/إجراءات مع شروط). تُرسل المهام إشعارًا عند التطابق.

## نصائح الأداء
- مفاتيح فهارس مضافة على الحقول الشائعة (created_at, action, app_label, model_name, user).
- استخدم الترشيح قبل التصدير لتقليل الحجم.

## أوامر الإدارة (Management Commands)
تمت إضافة أوامر لمساعدتك في الصيانة والتحليل:

### 1) explain_queries
تحليل خطط الاستعلام (EXPLAIN) بسرعة.

أمثلة:
```
python manage.py explain_queries --model core.AuditLog --limit 10
python manage.py explain_queries --sql "SELECT * FROM core_auditlog WHERE action='create' LIMIT 5"
python manage.py explain_queries --path /audit-logs/?page=2
```
خيارات:
- `--model app.Model` : تشغيل EXPLAIN لــ QuerySet بسيط.
- `--sql "SELECT ..."` : EXPLAIN لاستعلام محدد (SELECT فقط).
- `--path /url/` : تشغيل العرض والتقاط الاستعلامات الناتجة وشرحها.
- `--format json` : إخراج JSON بدلاً من نص.

### 2) archive_audit_logs
أرشفة سجلات التدقيق الأقدم من مدة محددة إلى ملف JSONL داخل `backups/audit_archives/` مع خيار حذفها بعد الأرشفة.

أمثلة:
```
python manage.py archive_audit_logs --days 120
python manage.py archive_audit_logs --days 180 --delete
```
خيارات:
- `--days N` : العمر بالأيام (إن لم يُحدّد يُستخدم `audit_retention_days`).
- `--delete` : حذف السجلات بعد الأرشفة.
- `--batch 5000` : حجم الدُفعة أثناء التكرار.

ملاحظات:
- الأرشفة تنتج ملف JSONL سهل الضغط والتحليل (`gzip` / `jq`).
- استخدم `--delete` فقط بعد التحقق من سلامة الملف الناتج.
- يفضل دمج الأمر في مهمة مجدولة (Celery Beat) بدون `--delete` ثم تشغيل تنظيف منفصل لاحقاً.

---
إن أردت تخصيصًا أوسع (تجاهل نماذج/تطبيقات أو حقول إضافية)، راجع ملف `core/signals.py` و`core/models.py`.
