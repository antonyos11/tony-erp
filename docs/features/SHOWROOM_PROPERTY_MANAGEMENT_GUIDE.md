# دليل إدارة الفروع والمعارض - الملكية والعقود والعمالة المؤقتة

## نظرة عامة

تم تطوير نظام إدارة الفروع والمعارض ليشمل إدارة شاملة لجميع جوانب المعرض من حيث:
- نوع الملكية (تمليك / إيجار / مؤقت)
- تفاصيل العقود والمستندات
- إدارة دفعات الإيجار
- العمالة المؤقتة والموسمية
- الربط التلقائي بنظام المحاسبة والأصول

---

## 1. إضافة معرض جديد

### الخطوات:
1. انتقل إلى **Admin Panel** → **Showrooms** → **إضافة معرض**
2. املأ المعلومات الأساسية:
   - الكود (Code)
   - الاسم بالإنجليزي والعربي
   - نوع الفرع (معرض / مصنع / مستودع / فرع)

### بيانات الملكية والعقد:

#### أ) معرض مملوك (تمليك):
```
- نوع الملكية: تمليك
- قيمة المعرض: 1,000,000 جنيه (مثلاً)
- تاريخ بداية العقد: تاريخ الشراء
- عقد الشراء: رفع ملف PDF للعقد
- حساب الأصول: اختيار حساب الأصول الثابتة
```

**الربط المحاسبي:**
- سيتم إضافة قيمة المعرض كأصل ثابت
- سيتم إنشاء قيد محاسبي تلقائي:
  * مدين: حساب الأصول الثابتة
  * دائن: رأس المال أو البنك

#### ب) معرض مستأجر (إيجار):
```
- نوع الملكية: إيجار
- الإيجار الشهري: 10,000 جنيه
- تاريخ بداية العقد: 01/01/2026
- تاريخ نهاية العقد: 31/12/2026
- عقد الإيجار: رفع ملف PDF للعقد
- حساب مصروفات الإيجار: اختيار الحساب المناسب
```

**الربط المحاسبي:**
- سيتم إنشاء دفعات إيجار شهرية تلقائياً
- عند السداد، يتم إنشاء قيد:
  * مدين: مصروفات الإيجار
  * دائن: النقدية/البنك

#### ج) معرض مؤقت:
```
- نوع الملكية: مؤقت
- الإيجار الشهري: 5,000 جنيه (أو يومي حسب الاتفاق)
- تاريخ بداية العقد: 01/03/2026
- تاريخ نهاية العقد: 15/03/2026 (15 يوم)
- ملاحظات العقد: "معرض موسمي لمناسبة..."
```

---

## 2. إدارة دفعات الإيجار

### إنشاء دفعات تلقائية:

من لوحة التحكم أو باستخدام Python:

```python
from showrooms.models import Showroom
from showrooms.accounting_helpers import auto_create_monthly_rent_payments

# اختيار المعرض
showroom = Showroom.objects.get(code='SH001')

# إنشاء 12 دفعة شهرية
payments = auto_create_monthly_rent_payments(showroom, months=12)
```

### سداد دفعة إيجار:

من **Admin Panel**:
1. اذهب إلى **Showroom Rent Payments**
2. اختر الدفعة المطلوبة
3. غيّر الحالة إلى **مدفوع**
4. أدخل تاريخ الدفع الفعلي ومرجع السداد
5. سيتم إنشاء القيد المحاسبي تلقائياً

أو برمجياً:
```python
from showrooms.models import ShowroomRentPayment
from showrooms.accounting_helpers import create_rent_payment_entry

payment = ShowroomRentPayment.objects.get(id=1)
payment.mark_as_paid(user=request.user, payment_ref='CHQ-12345')

# إنشاء القيد المحاسبي
entry = create_rent_payment_entry(payment, user=request.user)
```

### التنبيهات التلقائية:

- **الدفعات المتأخرة:** تتحول الحالة تلقائياً من "معلق" إلى "متأخر"
- **قرب انتهاء العقد:** خاصية `is_contract_expiring_soon` تُظهر المعارض التي ستنتهي عقودها خلال 30 يوم

تشغيل فحص الدفعات المتأخرة يدوياً:
```bash
python3 manage.py check_overdue_rent
```

---

## 3. إدارة العمالة المؤقتة

### إضافة عامل مؤقت:

من **Admin Panel** → **Temporary Workers** → **إضافة**:

```
معلومات العامل:
- اسم العامل: محمد أحمد
- رقم الهاتف: 0123456789
- رقم الهوية: 12345678901234
- المعرض: SH001
- المسمى الوظيفي: حامل / عامل تنظيف / موزع دعاية

نوع العمل:
- نوع العمل: يومي / بالساعة / عقد مؤقت
- الأجر اليومي: 150 جنيه
- أو الأجر بالساعة: 20 جنيه

الفترة:
- تاريخ البداية: 01/03/2026
- تاريخ النهاية: 15/03/2026
- أيام العمل: 15 يوم
- ساعات العمل: 0 (إذا كان يومي)

المبلغ المستحق:
- سيتم حسابه تلقائياً: 150 × 15 = 2,250 جنيه
```

### سداد أجر العامل:

```python
from showrooms.models import TemporaryWorker
from showrooms.accounting_helpers import create_temporary_worker_payment_entry

worker = TemporaryWorker.objects.get(id=1)

# تحديد كمدفوع
worker.is_paid = True
worker.payment_date = timezone.now().date()
worker.payment_reference = 'CASH-001'
worker.save()

# إنشاء القيد المحاسبي
entry = create_temporary_worker_payment_entry(worker, user=request.user)
```

**القيد المحاسبي:**
- مدين: مصروفات العمالة المؤقتة
- دائن: النقدية

---

## 4. الربط بنظام المحاسبة

### إعداد الحسابات:

قبل استخدام النظام، تأكد من إنشاء الحسابات التالية:

```python
from accounting.models import Account

# 1. حساب الأصول الثابتة (للمعارض المملوكة)
asset_account = Account.objects.create(
    code='1200',
    name='أصول ثابتة - معارض',
    account_type='asset'
)

# 2. حساب مصروفات الإيجار
rent_expense = Account.objects.create(
    code='5100',
    name='مصروفات إيجار المعارض',
    account_type='expense'
)

# 3. حساب مصروفات العمالة المؤقتة
labor_expense = Account.objects.create(
    code='5200',
    name='مصروفات عمالة مؤقتة',
    account_type='expense'
)

# 4. حساب النقدية
cash_account = Account.objects.create(
    code='1010',
    name='النقدية في الصندوق',
    account_type='asset'
)
```

### ربط الحسابات بالمعارض:

```python
showroom = Showroom.objects.get(code='SH001')

# للمعارض المملوكة
if showroom.is_owned:
    showroom.asset_account = asset_account
    showroom.save()

# للمعارض المستأجرة
if showroom.is_rented:
    showroom.rent_expense_account = rent_expense
    showroom.save()
```

---

## 5. التقارير والاستعلامات

### المعارض القريبة من انتهاء العقد:

```python
from showrooms.models import Showroom

expiring_soon = Showroom.objects.filter(
    property_type__in=['rented', 'temporary'],
    is_active=True
)

for showroom in expiring_soon:
    if showroom.is_contract_expiring_soon:
        days = showroom.contract_days_remaining
        print(f'{showroom.name} - باقي {days} يوم على انتهاء العقد')
```

### الدفعات المتأخرة:

```python
from showrooms.models import ShowroomRentPayment

overdue = ShowroomRentPayment.objects.filter(
    status='overdue'
)

for payment in overdue:
    print(f'{payment.showroom.name} - متأخر {payment.days_overdue} يوم - {payment.amount} جنيه')
```

### العمالة المؤقتة النشطة:

```python
from showrooms.models import TemporaryWorker
from django.utils import timezone

active_workers = TemporaryWorker.objects.filter(
    is_active=True,
    start_date__lte=timezone.now().date(),
    end_date__gte=timezone.now().date()
)

total_cost = sum(w.total_amount for w in active_workers)
print(f'عدد العمال النشطين: {active_workers.count()}')
print(f'التكلفة الإجمالية: {total_cost} جنيه')
```

### تقرير تكاليف المعرض الشاملة:

```python
def get_showroom_cost_report(showroom, month, year):
    from decimal import Decimal
    
    # تكلفة الإيجار
    rent_cost = Decimal('0')
    if showroom.is_rented:
        rent_payments = showroom.rent_payments.filter(
            payment_date__month=month,
            payment_date__year=year,
            status='paid'
        )
        rent_cost = sum(p.amount for p in rent_payments)
    
    # تكلفة العمالة المؤقتة
    workers = showroom.temporary_workers.filter(
        start_date__month=month,
        start_date__year=year,
        is_paid=True
    )
    labor_cost = sum(w.total_amount for w in workers)
    
    # تكاليف أخرى
    expenses = showroom.expenses.filter(
        created_at__month=month,
        created_at__year=year,
        status='approved'
    )
    other_costs = sum(e.amount for e in expenses)
    
    return {
        'showroom': showroom.name,
        'rent': rent_cost,
        'labor': labor_cost,
        'other': other_costs,
        'total': rent_cost + labor_cost + other_costs
    }
```

---

## 6. أمثلة عملية

### مثال 1: معرض موسمي (15 يوم)

```python
# إنشاء المعرض
showroom = Showroom.objects.create(
    code='TEMP-001',
    name='معرض رمضان 2026',
    name_ar='معرض رمضان 2026',
    showroom_type='showroom',
    property_type='temporary',
    monthly_rent=15000,  # إجمالي المدة
    contract_start_date='2026-03-01',
    contract_end_date='2026-03-15',
    location=my_location,
    is_active=True
)

# إضافة 3 عمال للمعرض
workers_data = [
    {'name': 'أحمد محمد', 'job': 'حامل', 'daily_wage': 150},
    {'name': 'محمود علي', 'job': 'منظف', 'daily_wage': 120},
    {'name': 'خالد حسن', 'job': 'موزع دعاية', 'daily_wage': 100},
]

for data in workers_data:
    TemporaryWorker.objects.create(
        showroom=showroom,
        worker_name=data['name'],
        job_title=data['job'],
        worker_type='daily',
        daily_wage=data['daily_wage'],
        start_date='2026-03-01',
        end_date='2026-03-15',
        days_worked=15
    )

# التكلفة الإجمالية:
# إيجار: 15,000 جنيه
# عمالة: (150+120+100) × 15 = 5,550 جنيه
# الإجمالي: 20,550 جنيه
```

### مثال 2: معرض دائم مستأجر

```python
showroom = Showroom.objects.create(
    code='SH-002',
    name='معرض التجمع الخامس',
    showroom_type='showroom',
    property_type='rented',
    monthly_rent=25000,
    contract_start_date='2026-01-01',
    contract_end_date='2026-12-31',
    location=my_location
)

# ربط بالحسابات
showroom.rent_expense_account = rent_expense_account
showroom.save()

# إنشاء دفعات السنة كاملة
payments = auto_create_monthly_rent_payments(showroom, months=12)

# التكلفة السنوية: 25,000 × 12 = 300,000 جنيه
```

---

## 7. الصيانة والمراقبة

### جدولة فحص الدفعات المتأخرة:

أضف إلى crontab:
```bash
# كل يوم الساعة 9 صباحاً
0 9 * * * cd /var/www/tony_erp && python3 manage.py check_overdue_rent
```

### التنبيهات:

يمكن إضافة نظام تنبيهات عبر البريد الإلكتروني أو Slack:

```python
from django.core.mail import send_mail

def notify_expiring_contracts():
    expiring = Showroom.objects.filter(is_active=True)
    
    for showroom in expiring:
        if showroom.is_contract_expiring_soon:
            days = showroom.contract_days_remaining
            send_mail(
                subject=f'تنبيه: عقد {showroom.name} سينتهي قريباً',
                message=f'العقد سينتهي بعد {days} يوم',
                from_email='system@company.com',
                recipient_list=['manager@company.com'],
            )
```

---

## 8. API Endpoints

تم إضافة الـ Serializers للنماذج الجديدة:

### المعارض (Showrooms):
```
GET /api/showrooms/
POST /api/showrooms/

الحقول الجديدة في Response:
- property_type, property_type_display
- property_value, monthly_rent
- contract_start_date, contract_end_date
- is_temporary, is_rented, is_owned
- contract_days_remaining
- is_contract_expiring_soon
```

### العمالة المؤقتة:
```
GET /api/temporary-workers/
POST /api/temporary-workers/
GET /api/temporary-workers/{id}/

الحقول:
- showroom, worker_name, job_title
- worker_type, daily_wage, hourly_wage
- start_date, end_date
- total_amount, is_paid
- duration_days, is_finished
```

### دفعات الإيجار:
```
GET /api/rent-payments/
POST /api/rent-payments/
GET /api/rent-payments/{id}/

الحقول:
- showroom, payment_date, amount
- status, days_overdue
- actual_payment_date, payment_reference
```

---

## ملخص الميزات

✅ إدارة ثلاثة أنواع من المعارض (تمليك / إيجار / مؤقت)  
✅ رفع وحفظ عقود الشراء والإيجار  
✅ إدارة دفعات الإيجار الشهرية  
✅ تتبع الدفعات المتأخرة تلقائياً  
✅ تنبيهات لقرب انتهاء العقود  
✅ إدارة العمالة المؤقتة والموسمية  
✅ حساب الأجور تلقائياً (يومي / بالساعة)  
✅ الربط التلقائي بنظام المحاسبة  
✅ إنشاء قيود محاسبية تلقائياً للإيجار والعمالة  
✅ إضافة المعارض المملوكة كأصول ثابتة  
✅ تقارير شاملة للتكاليف  

---

## الدعم الفني

للاستفسارات والدعم، يرجى التواصل مع فريق التطوير.

تاريخ التحديث: 9 يناير 2026
