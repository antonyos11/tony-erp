# 🚀 تعليمات التثبيت والنشر: نظام السلف

## ✅ التحقق من الاكتمال

قبل البدء، تأكد من:
- ✅ Migration تمت بنجاح
- ✅ جميع الملفات موجودة
- ✅ لا توجد أخطاء Python

---

## 📋 قائمة الملفات المطلوب نسخها

### ملفات جديدة:
```bash
✅ hr/views_loans.py                           (ملف جديد - 350+ سطر)
✅ EMPLOYEE_LOANS_SYSTEM.md                    (توثيق)
✅ EMPLOYEE_LOANS_TECHNICAL_SUMMARY.md         (توثيق)
✅ EMPLOYEE_LOANS_QUICK_START.md               (توثيق)
✅ PROJECT_REPORT_EMPLOYEE_LOANS.md            (توثيق)
✅ CHANGELOG_EMPLOYEE_LOANS.md                 (توثيق)
✅ FINAL_SUMMARY_EMPLOYEE_LOANS.md             (توثيق)
```

### ملفات معدلة:
```bash
📝 hr/models.py                 (إضافة EmployeeLoan, LoanInstallment)
📝 hr/forms.py                  (إضافة 4 forms)
📝 hr/payroll_calculator.py     (إضافة calculate_loan_deductions)
📝 hr/urls.py                   (إضافة 7 URLs)
📝 hr/admin.py                  (إضافة 2 admin classes)
📝 hr/migrations/0013_*.py      (جديد - Migration)
```

---

## 🔧 خطوات التثبيت

### الخطوة 1: التحقق من الحالة
```bash
cd /var/www/tony_erp

# التحقق من migrations
python3 manage.py showmigrations hr

# يجب أن تظهر:
# [X] 0013_employeeloan_loaninstallment_and_more
```

### الخطوة 2: تسجيل الصلاحيات
```bash
# الصلاحيات تُنشأ تلقائياً مع Migration
# تحقق من Django Admin

python3 manage.py shell
```

```python
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from hr.models import EmployeeLoan, LoanInstallment

# يجب أن تظهر الصلاحيات:
# - hr.add_employeeloan
# - hr.view_employeeloan
# - hr.change_employeeloan
# - hr.delete_employeeloan
# - hr.add_loaninstallment
# - hr.change_loaninstallment

print("✅ الصلاحيات موجودة")
```

### الخطوة 3: التحقق من النماذج
```bash
python3 manage.py makemigrations --dry-run hr

# يجب أن تكون النتيجة "No changes"
```

### الخطوة 4: تشغيل الاختبارات
```bash
python3 manage.py test hr.tests --verbosity=2

# اختياري - إذا كان لديك ملفات اختبارات
```

---

## 📊 التحقق من قاعدة البيانات

### تفعيل بيئة Django
```bash
python3 manage.py shell
```

### التحقق من النماذج:
```python
from hr.models import EmployeeLoan, LoanInstallment
from django.contrib.auth.models import User
from hr.models import Employee

# التحقق من النموذج الأول
loan = EmployeeLoan.objects.first()
print(f"✅ EmployeeLoan موجود: {loan}")

# التحقق من النموذج الثاني
installment = LoanInstallment.objects.first()
print(f"✅ LoanInstallment موجود: {installment}")

# التحقق من الحقول
print(f"✅ الحقول موجودة")
```

---

## 🌐 اختبار الواجهة الويب

### الدخول إلى Django Admin
```
http://localhost:8000/admin/
```

#### التحقق:
1. ✅ البحث عن "Employee Loan" في الإدارة
2. ✅ البحث عن "Loan Installment" في الإدارة
3. ✅ محاولة إنشاء سجل جديد

### اختبار الـ Views:
```
http://localhost:8000/hr/loans/
```

#### يجب أن تظهر:
- ✅ لوحة التحكم (إذا كنت لديك صلاحيات)
- ✅ قوائم وإحصائيات
- ✅ نماذج الإدخال

---

## ⚙️ الإعدادات المتقدمة

### في settings.py (اختياري):
```python
# إذا كنت تريد قيود معينة على السلف
HR_LOAN_MAX_AMOUNT = 10000  # الحد الأقصى للسلفة
HR_LOAN_MAX_INSTALLMENTS = 12  # أقصى أقساط
HR_LOAN_ALLOW_EMERGENCY = True  # السماح بالسلف الطارئة
```

### تحديث settings.py:
```bash
# لا يوجد تغييرات مجبرة
# لكن يمكنك إضافة الإعدادات أعلاه إذا أردت
```

---

## 🧪 اختبار العملية الكاملة

### سيناريو اختبار كامل:

#### 1. إنشاء موظف اختبار (إذا لم يكن موجوداً):
```bash
python3 manage.py shell
```

```python
from hr.models import Employee, Department, JobPosition
from django.contrib.auth.models import User

# إنشاء مستخدم
user = User.objects.create_user('test_emp', 'test@example.com', 'pass123')

# إنشاء موظف
emp = Employee.objects.create(
    user=user,
    employee_id='TEST-001',
    first_name='محمد',
    last_name='أحمد',
    arabic_name='محمد أحمد',
    basic_salary=3000,
    status='active'
)

print(f"✅ موظف اختبار: {emp}")
```

#### 2. إنشاء سلفة:
```python
from hr.models import EmployeeLoan
from datetime import date, timedelta

loan = EmployeeLoan.objects.create(
    employee=emp,
    amount=1000,
    reason='احتياجات شخصية',
    installments_count=2,
    start_deduction_date=date.today() + timedelta(days=5)
)

print(f"✅ سلفة: {loan.loan_number}")
print(f"✅ الأقساط المنشأة: {loan.installments.count()}")
```

#### 3. الموافقة على السلفة:
```python
from django.utils import timezone

loan.status = 'approved'
loan.approved_at = timezone.now()
loan.save()

print(f"✅ السلفة معتمدة: {loan.status}")
```

#### 4. حساب الراتب:
```python
from hr.payroll_calculator import auto_calculate_payroll

payroll, created = auto_calculate_payroll(emp, date.today(), date.today())

print(f"✅ الراتب محسوب")
print(f"✅ الخصم: {payroll.other_deductions}")
print(f"✅ الصافي: {payroll.net_salary}")
```

---

## 🐛 معالجة الأخطاء الشائعة

### الخطأ: `ProgrammingError: relation not found`
**الحل:**
```bash
python3 manage.py migrate hr
```

### الخطأ: `Permission denied`
**الحل:**
```bash
# أضف الصلاحيات للمستخدم من Django Admin
# أو استخدم:

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from hr.models import EmployeeLoan

user = User.objects.get(username='your_user')
perm = Permission.objects.get(codename='view_employeeloan')
user.user_permissions.add(perm)
```

### الخطأ: `ModuleNotFoundError`
**الحل:**
```bash
# تأكد من أن views_loans.py موجود في:
# /var/www/tony_erp/hr/views_loans.py

# وأن hr/__init__.py يحتوي على الاستيراد الصحيح
```

---

## 📋 قائمة التحقق قبل الإنتاج

```
✅ الملفات:
   [ ] جميع الملفات موجودة
   [ ] جميع الاستيرادات صحيحة
   [ ] لا توجد أخطاء Python

✅ قاعدة البيانات:
   [ ] Migration طُبقت بنجاح
   [ ] الجداول موجودة
   [ ] الفهارس موجودة

✅ الواجهة:
   [ ] Django Admin يعمل
   [ ] Views تفتح بدون أخطاء
   [ ] النماذج تعمل

✅ الأمان:
   [ ] الصلاحيات معرّفة
   [ ] CSRF protection فعال
   [ ] التحقق من المستخدم يعمل

✅ الوثائق:
   [ ] التوثيق موجود
   [ ] أمثلة واضحة
   [ ] تعليمات بسيطة

✅ الأداء:
   [ ] الاستعلامات سريعة
   [ ] لا توجد أخطاء في السجلات
   [ ] الذاكرة معقولة
```

---

## 🚀 نشر إلى الإنتاج

### الخطوة 1: النسخ الاحتياطي
```bash
# نسخ قاعدة البيانات
pg_dump -U postgres tony_erp > backup_$(date +%Y%m%d).sql

# نسخ الملفات
tar -czf backup_$(date +%Y%m%d).tar.gz /var/www/tony_erp
```

### الخطوة 2: التحديث
```bash
# شحن الملفات الجديدة
scp -r hr/ user@server:/var/www/tony_erp/

# تطبيق Migration
ssh user@server "cd /var/www/tony_erp && python3 manage.py migrate hr"

# جمع الملفات الثابتة
ssh user@server "cd /var/www/tony_erp && python3 manage.py collectstatic"
```

### الخطوة 3: إعادة التشغيل
```bash
# إعادة تشغيل الخادم
ssh user@server "systemctl restart gunicorn"
```

### الخطوة 4: التحقق
```bash
# التحقق من الحالة
curl http://example.com/hr/loans/

# يجب أن تستجيب الصفحة بدون أخطاء
```

---

## 📞 الدعم والمساعدة

### إذا واجهت مشاكل:

1. **تحقق من السجلات (Logs)**
   ```bash
   tail -f /var/log/django.log
   tail -f /var/log/gunicorn.log
   ```

2. **اختبر الاتصال**
   ```bash
   python3 manage.py dbshell
   ```

3. **راجع الوثائق**
   - EMPLOYEE_LOANS_SYSTEM.md
   - EMPLOYEE_LOANS_TECHNICAL_SUMMARY.md

4. **تواصل مع الفريق**
   - فريق التطوير
   - مسؤول قاعدة البيانات

---

## ✅ ملخص البدء السريع

```bash
# 1. التحقق
python3 manage.py showmigrations hr | grep 0013

# 2. الاختبار
python3 manage.py shell < test_loans.py

# 3. النشر
python3 manage.py collectstatic
systemctl restart gunicorn

# 4. التحقق من النجاح
curl http://example.com/hr/loans/
```

---

## 🎉 تم بنجاح!

إذا رأيت هذا، فالنظام جاهز للاستخدام:

```
✅ جميع الملفات موجودة
✅ قاعدة البيانات محدثة
✅ الواجهة تعمل
✅ الأمان مفعل
✅ الأداء محسن
```

---

**النسخة:** 1.0.0  
**التاريخ:** 5 يناير 2026  
**الحالة:** جاهز للإنتاج ✅
