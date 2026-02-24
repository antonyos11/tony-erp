# دليل البدء السريع - نظام الباركود والموارد البشرية
## Quick Start Guide

---

## ⚡ البدء خلال 10 دقائق

### 1️⃣ تثبيت المكتبات (دقيقتان)

```powershell
cd h:\برمجة\الشامل\الشامل\الشامل\app
.\.venv\Scripts\Activate.ps1
pip install python-zpl python-escpos PyJWT pywin32
```

### 2️⃣ تطبيق Migrations (دقيقة)

```powershell
python manage.py makemigrations inventory hr
python manage.py migrate
```

### 3️⃣ الإعدادات الأساسية (5 دقائق)

#### أ. إنشاء سياسة الغياب
```powershell
python manage.py shell
```

```python
from hr.models import AbsencePolicy
AbsencePolicy.objects.create(
    name="السياسة الافتراضية",
    deduct_from_leave_first=True,
    salary_deduction_percentage=10,
    unauthorized_absence_multiplier=2.0,
    is_default=True,
    is_active=True
)
exit()
```

#### ب. إعداد أيام العمل
```python
python manage.py shell
```

```python
from hr.models import WeekendDay
WeekendDay.objects.create(day_of_week=4, is_working_day=False)  # الجمعة
WeekendDay.objects.create(day_of_week=5, is_working_day=False)  # السبت
exit()
```

#### ج. إعداد طابعة Zebra
```powershell
python manage.py createsuperuser  # إذا لم يكن موجود
python manage.py runserver
```

افتح المتصفح: `http://localhost:8000/admin/`
- اذهب إلى **Inventory > Printer Configurations**
- اضغط **Add Printer Configuration**
- املأ البيانات:
  ```
  اسم الطابعة: Zebra ZD420
  نوع الطابعة: zebra
  نوع المستند: barcode
  نوع الاتصال: network
  عنوان IP: 192.168.1.100  # غيّره لعنوان طابعتك
  المنفذ: 9100
  عرض الليبل: 100
  ارتفاع الليبل: 100
  DPI: 203
  ☑ افتراضية
  ☑ نشطة
  ```
- احفظ

### 4️⃣ اختبار النظام (دقيقتان)

#### اختبار الطباعة:
```python
python manage.py shell
```

```python
from inventory.models import PrinterConfiguration
from inventory.barcode_utils import send_to_zebra_printer

printer = PrinterConfiguration.objects.get(printer_type='zebra', is_default=True)

zpl = """
^XA
^FO50,50^A0N,50,50^FDTEST PRINT^FS
^FO50,120^BCN,100,Y,N,N^FD123456789012^FS
^XZ
"""

success, message = send_to_zebra_printer(zpl, printer)
print(f"النتيجة: {message}")
exit()
```

إذا ظهر "تمت الطباعة بنجاح" وطبعت الطابعة → النظام يعمل! ✅

---

## 🚀 الاستخدام اليومي

### للموظف: طلب إجازة

1. ادخل للنظام: `http://localhost:8000/hr/employee-portal/`
2. اضغط "طلب إجازة جديد"
3. املأ البيانات واضغط "تقديم"

### للمسؤول: الموافقة على الإجازات

1. افتح: `http://localhost:8000/hr/leave-approval/`
2. اضغط "موافقة" أو "رفض"

### لمشرف الإنتاج: طباعة باركود

1. أنشئ أمر إنتاج
2. عند الانتهاء، غيّر الحالة إلى "مكتمل"
3. سيطبع الباركود تلقائياً ✨

### للموارد البشرية: إنشاء بطاقة هوية

1. افتح صفحة الموظف
2. اضغط "إنشاء بطاقة هوية"
3. اطبع البطاقة

---

## 🔧 الإعدادات المتقدمة (اختياري)

### إعداد طابعة xprinter (للإيصالات)

في Admin > Printer Configurations:
```
اسم الطابعة: Xprinter XP-80
نوع الطابعة: xprinter
نوع المستند: receipt
نوع الاتصال: network
عنوان IP: 192.168.1.101
المنفذ: 9100
☑ افتراضية
☑ نشطة
```

### إعداد طابعة HP (للفواتير)

في Admin > Printer Configurations:
```
اسم الطابعة: HP LaserJet P1102
نوع الطابعة: hp_laserjet
نوع المستند: invoice
نوع الاتصال: shared
اسم الطابعة المشاركة: HP_P1102
☑ افتراضية
☑ نشطة
```

### إعداد المهمة اليومية للغياب

**Windows Task Scheduler**:

1. أنشئ ملف `check_absences.bat`:
```batch
@echo off
cd h:\برمجة\الشامل\الشامل\الشامل\app
call .venv\Scripts\activate.bat
python manage.py shell -c "from hr.hr_utils import check_and_process_daily_absences; print(check_and_process_daily_absences())"
```

2. افتح Task Scheduler
3. Create Basic Task:
   - الاسم: "Check Employee Absences"
   - Trigger: Daily at 12:01 AM
   - Action: Start a program → `check_absences.bat`

---

## 📋 قائمة فحص سريعة

قبل البدء في الاستخدام الفعلي، تأكد من:

- [x] تثبيت المكتبات الجديدة
- [x] تطبيق Migrations
- [x] إنشاء سياسة غياب افتراضية
- [x] إعداد أيام العمل (Weekend Days)
- [x] إعداد طابعة Zebra
- [x] اختبار الطباعة
- [ ] إعداد طابعة xprinter (اختياري)
- [ ] إعداد طابعة HP (اختياري)
- [ ] إعداد المهمة اليومية للغياب (اختياري)

---

## 🆘 مشاكل شائعة وحلولها

### ❌ خطأ: "لم يتم العثور على طابعة Zebra افتراضية"

**الحل**: تأكد من إنشاء طابعة في Admin وتفعيل خيار "افتراضية"

### ❌ خطأ: "رفضت الطابعة الاتصال"

**الحل**: 
1. تأكد من تشغيل الطابعة
2. تأكد من عنوان IP صحيح:
   ```powershell
   Test-NetConnection -ComputerName 192.168.1.100 -Port 9100
   ```

### ❌ خطأ: "الموظف ليس لديه ملف مرتبط"

**الحل**: في Admin > Employees > اختر الموظف > ربطه بـ User

### ❌ خطأ: "رصيد الإجازات غير كافي"

**الحل**: في Admin > Leave Types > زد من `days_per_year`

---

## 📞 للمزيد من المساعدة

راجع الملف الشامل: `docs/BARCODE_AND_HR_SYSTEM.md`

---

**جاهز للانطلاق! 🚀**
