# 🏢 نظام إدارة الفروع والمعارض المتقدم

## 🎯 الهدف
نظام شامل لإدارة المعارض بجميع أنواعها (مملوكة، مستأجرة، مؤقتة) مع ربط كامل بنظام المحاسبة والأصول وإدارة العمالة المؤقتة.

## ✨ الميزات الرئيسية

### 1. إدارة أنواع الملكية
- ✅ **معارض مملوكة**: تُسجل كأصول ثابتة
- ✅ **معارض مستأجرة**: مع دفعات إيجار شهرية
- ✅ **معارض مؤقتة**: لفترات محددة (أيام أو أسابيع)

### 2. إدارة العقود
- 📄 رفع وحفظ عقود الشراء/الإيجار
- 📅 تتبع تواريخ البداية والنهاية
- ⚠️ تنبيهات تلقائية لقرب انتهاء العقود
- 💰 تسجيل قيمة المعرض أو الإيجار

### 3. نظام دفعات الإيجار
- 📊 إنشاء دفعات شهرية تلقائياً
- ✅ تتبع حالة الدفع (معلق/مدفوع/متأخر)
- 🔔 كشف تلقائي للدفعات المتأخرة
- 💳 ربط مباشر بالقيود المحاسبية

### 4. إدارة العمالة المؤقتة
- 👷 عمال يوميين/بالساعة/عقود مؤقتة
- 💵 حساب الأجور تلقائياً
- 📅 تتبع فترات العمل
- 🧾 ربط بنظام المحاسبة

### 5. الربط المحاسبي الكامل
- 🏦 قيود تلقائية عند شراء معرض (أصل ثابت)
- 💸 قيود تلقائية عند سداد الإيجار
- 👨‍🔧 قيود تلقائية عند سداد أجور العمالة
- 📊 تقارير شاملة للتكاليف

## 🚀 البدء السريع

### التثبيت
```bash
# تطبيق الترحيلات
cd /var/www/tony_erp
python3 manage.py migrate showrooms

# التحقق من النظام
python3 manage.py check
```

### إنشاء الحسابات الأساسية
```python
from accounting.models import Account

# حساب الأصول الثابتة
Asset.objects.create(
    code='1200',
    name='أصول ثابتة - معارض',
    account_type='asset'
)

# حساب مصروفات الإيجار
Account.objects.create(
    code='5100',
    name='مصروفات إيجار المعارض',
    account_type='expense'
)

# حساب مصروفات العمالة
Account.objects.create(
    code='5200',
    name='مصروفات عمالة مؤقتة',
    account_type='expense'
)
```

### مثال بسيط
```python
from showrooms.models import Showroom
from showrooms.accounting_helpers import auto_create_monthly_rent_payments

# إنشاء معرض مستأجر
showroom = Showroom.objects.create(
    code='SH-001',
    name='Main Showroom',
    name_ar='المعرض الرئيسي',
    property_type='rented',
    monthly_rent=20000,
    contract_start_date='2026-01-01',
    contract_end_date='2026-12-31'
)

# إنشاء دفعات السنة
payments = auto_create_monthly_rent_payments(showroom, 12)
```

## 📚 الوثائق

### الدليل الكامل
📖 [SHOWROOM_PROPERTY_MANAGEMENT_GUIDE.md](SHOWROOM_PROPERTY_MANAGEMENT_GUIDE.md)
- شرح تفصيلي لجميع الميزات
- أمثلة عملية
- التقارير والاستعلامات
- API Documentation

### ملخص التحديثات
📋 [SHOWROOM_ENHANCEMENTS_SUMMARY.md](SHOWROOM_ENHANCEMENTS_SUMMARY.md)
- قائمة بجميع التحديثات
- الحقول والنماذج الجديدة
- الدوال المساعدة

### أمثلة عملية
💻 [showrooms/examples.py](showrooms/examples.py)
- 5 أمثلة عملية كاملة
- يمكن تشغيلها مباشرة

## 🔧 الدوال المساعدة

### accounting_helpers.py

```python
from showrooms.accounting_helpers import (
    create_rent_payment_entry,              # قيد دفعة إيجار
    create_temporary_worker_payment_entry,  # قيد أجر عامل
    create_showroom_asset_entry,            # قيد شراء معرض
    auto_create_monthly_rent_payments,      # دفعات تلقائية
    check_and_mark_overdue_payments         # فحص المتأخرات
)
```

## 🎛️ Admin Panel

الوصول من:
```
/admin/showrooms/
```

### الصفحات المتاحة:
- ✅ **Showrooms** - إدارة المعارض (مع الحقول الجديدة)
- ✅ **Temporary Workers** - إدارة العمالة المؤقتة
- ✅ **Showroom Rent Payments** - إدارة دفعات الإيجار
- ✅ إجراءات سريعة (تحديد كمدفوع، فحص المتأخر)

## 🔄 Management Commands

### فحص الدفعات المتأخرة
```bash
python3 manage.py check_overdue_rent
```

يمكن جدولتها في crontab:
```bash
# كل يوم الساعة 9 صباحاً
0 9 * * * cd /var/www/tony_erp && python3 manage.py check_overdue_rent
```

## 📊 النماذج (Models)

### Showroom
```python
property_type = 'owned' | 'rented' | 'temporary'
property_value = Decimal  # للمملوك
monthly_rent = Decimal    # للمستأجر/المؤقت
contract_start_date = Date
contract_end_date = Date
contract_document = FileField
asset_account = ForeignKey
rent_expense_account = ForeignKey
```

### TemporaryWorker
```python
worker_name = CharField
job_title = CharField
worker_type = 'daily' | 'hourly' | 'contract'
daily_wage = Decimal
hourly_wage = Decimal
days_worked = Integer
total_amount = Decimal  # محسوب تلقائياً
is_paid = Boolean
```

### ShowroomRentPayment
```python
showroom = ForeignKey
payment_date = Date
amount = Decimal
status = 'pending' | 'paid' | 'overdue'
journal_entry = ForeignKey  # القيد المحاسبي
```

## 📱 API Endpoints

```
GET  /api/showrooms/
POST /api/showrooms/

GET  /api/temporary-workers/
POST /api/temporary-workers/

GET  /api/rent-payments/
POST /api/rent-payments/
```

## 🧪 الاختبار

### تشغيل الأمثلة
```bash
cd /var/www/tony_erp
python3 manage.py shell < showrooms/examples.py
```

## 🎓 حالات الاستخدام

### 1. معرض موسمي (15 يوم)
- إيجار: 15,000 جنيه
- 4 عمال × 150 جنيه × 15 يوم
- التكلفة الإجمالية: 24,000 جنيه

### 2. معرض دائم مستأجر
- إيجار شهري: 25,000 جنيه
- دفعات سنوية: 300,000 جنيه
- تتبع تلقائي للدفعات

### 3. معرض مملوك
- قيمة: 1,500,000 جنيه
- تسجيل كأصل ثابت
- قيد محاسبي تلقائي

## 🔍 التقارير

### المعارض المنتهية قريباً
```python
[s for s in Showroom.objects.filter(is_active=True) 
 if s.is_contract_expiring_soon]
```

### الدفعات المتأخرة
```python
ShowroomRentPayment.objects.filter(status='overdue')
```

### تكلفة معرض محددة
```python
from showrooms.examples import get_showroom_cost_report
report = get_showroom_cost_report(showroom, month=3, year=2026)
```

## ✅ الميزات المكتملة

- [x] إدارة أنواع الملكية
- [x] رفع العقود والمستندات
- [x] نظام دفعات الإيجار
- [x] العمالة المؤقتة
- [x] الربط بالمحاسبة
- [x] القيود التلقائية
- [x] التنبيهات والإشعارات
- [x] Admin Panel
- [x] API
- [x] Documentation
- [x] Examples

## 📞 الدعم

للاستفسارات والدعم، راجع:
- [الدليل الكامل](SHOWROOM_PROPERTY_MANAGEMENT_GUIDE.md)
- [ملخص التحديثات](SHOWROOM_ENHANCEMENTS_SUMMARY.md)
- [الأمثلة العملية](showrooms/examples.py)

---

**تاريخ التحديث:** 9 يناير 2026  
**الإصدار:** 2.0  
**الحالة:** ✅ جاهز للإنتاج
