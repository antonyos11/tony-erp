# نظرة عامة على وحدة المحاسبة

## الهدف
توفر هذه الوحدة بنية محاسبية أساسية (دليل حسابات، قيود يومية، مراكز تكلفة، سنوات مالية، قروض، شيكات، إعدادات VAT) مع تحسينات لأداء وسلامة البيانات.

## المكونات الرئيسية
- Account / شجرة الحسابات (حقول: code, name, account_type, path, level, is_group, can_post)
- JournalEntry / JournalEntryItem (القيود وبنودها، مع منع تعديل البنود بعد الترحيل)
- FiscalYear (سنة مالية مع إغلاق ومنع ترحيل قيود داخل سنة مغلقة)
- CostCenter + CostCenterBudget
- Loan / LoanPayment (قيود تحقق: الفائدة <= 100%، أجزاء الدفعة تساوي الإجمالي)
- Cheque (حافظة الشيكات)
- AccountingSettings (حسابات افتراضية و VAT)
- CashFlowAccountMapping (تصنيف التدفقات النقدية يدويًا)

## الضمانات والقيود المضافة
- منع ترحيل أو حفظ قيد مرحل غير متوازن.
- منع إضافة/تعديل بنود في قيد مرحل (يجب عمل قيد عكسي).
- تحقق السنة المالية قبل ترحيل القيد (وجود سنة + عدم الإغلاق).
- فهارس محسّنة: `je_date_posted_idx`, `jei_account_entry_idx` لتسريع الاستعلامات.
- دقة القسط الشهري للقروض باستخدام Decimal.
- Check Constraints: معدل فائدة القرض <= 100%، تجزئة دفعة القرض = مجموع الأصل + الفوائد.

## الصلاحيات (Permissions)
مضافة على نموذج القيود وبنودها:
- `accounting.view_journal_reports` عرض التقارير.
- `accounting.post_journal_entry` ترحيل قيود.
- `accounting.unpost_journal_entry` (محجوز مستقبلًا لقيد عكسي).
- `accounting.create_journal_entry` إنشاء قيد يدوي.
- `accounting.edit_posted_entry_items` (غير مستحسن – معطل افتراضيًا بالتحقق). 

تم ربط بعض الواجهات بديكور `require_perm`:
- إنشاء حساب: add_account
- تعديل حساب: change_account
- إنشاء قيد: create_journal_entry
- ترحيل قيد: post_journal_entry

## تحسينات مقترحة مستقبلية
1. توليد أرقام قيود عبر Sequence مستقل أو جدول داخلي لمنع سباقات.
2. تفعيل صلاحيات متقدمة للقيد العكسي (منفصلة) وتوثيق سجل التدقيق لكل عملية عكس.
3. توسيع Service Layer (عمليات إضافية: قيد تسوية، قيد تجميع، batch posting).
4. كاش مركزي لإحصاءات لوحة القيادة (Redis) بدلاً من in-process.
5. تقليل الضجيج التحليلي بإضافة type hints و stubs للعلاقات العكسية.
6. تحسين صفحات التقارير باستخدام prefetch/select_related الموجه.

## القيد العكسي (Reversal)
تمت إضافة دعم قيد عكسي عبر:
- خدمة: `JournalService.reverse(entry, user)`
- واجهة: `reverse_journal_entry` (مسار: `/accounting/journal-entries/<id>/reverse/`)

السلوك:
- يتطلب أن يكون القيد الأصلي مرحلاً.
- ينشئ قيدًا جديدًا بنوع `reversal` مع بنود معكوسة (قلب المدين/الدائن).
- لا يحذف أو يعدل القيد الأصلي (حفاظًا على الأثر المحاسبي والأثر التدقيقي).
- المرجع (reference) يأخذ شكل `REV-<number>` لسهولة التتبع.

مستقبلاً يمكن إضافة:
- ربط ثنائي (حقل أصل/عكس) لسهولة التتبع في التقارير.
- تفعيل صلاحية مستقلة مثل: `accounting.reverse_journal_entry`.
- خيار تنفيذ العكس بتاريخ فترة لاحقة (closing adjustments).

## طبقة الخدمة الحالية
انظر `accounting/services/__init__.py` (حساب أرصدة، كشف مورد، ترحيل قيد، إعدادات كاش). مستقبلًا يمكن إضافة:
```python
class JournalService:
    @staticmethod
    def create_balanced(entry_data, items, auto_post=True):
        # validate + create + (optional post)
        ...
```

## ملاحظات تشغيل
- تأكد من تشغيل `makemigrations` ثم `migrate` بعد سحب التغييرات.
- راجع صلاحيات المجموعات (Groups) وأضف الأذونات للمستخدمين المناسبين.
- أي تعديل على بنود قيد مرحل يجب أن يتم بقيد تسوية جديد، لا تعديل مباشر.

## اختبار سريع
```bash
python manage.py check
python manage.py shell -c "from accounting.models import JournalEntry;print(JournalEntry.objects.count())"
```

## دعم
لتحسينات إضافية افتح بطاقة عمل (ticket) موضحاً: السيناريو، التأثير، الأولوية.
