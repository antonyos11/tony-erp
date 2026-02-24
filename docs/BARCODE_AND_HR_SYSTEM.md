# نظام الباركود التلقائي والموارد البشرية المتقدم
## Barcode & Advanced HR System Documentation

**التاريخ**: 7 ديسمبر 2025  
**الإصدار**: 1.0  
**الحالة**: تم التطبيق ✅

---

## 📋 جدول المحتويات

1. [نظام الباركود التلقائي للمنتجات التامة](#1-نظام-الباركود-التلقائي)
2. [نظام إدارة الإجازات المتقدم](#2-نظام-إدارة-الإجازات-المتقدم)
3. [نظام الخصم التلقائي للغياب](#3-نظام-الخصم-التلقائي-للغياب)
4. [نظام الطباعة متعدد الطابعات](#4-نظام-الطباعة-متعدد-الطابعات)
5. [نظام بطاقات الهوية مع QR Code](#5-نظام-بطاقات-الهوية)
6. [إعداد النظام](#6-إعداد-النظام)
7. [دليل الاستخدام](#7-دليل-الاستخدام)

---

## 1. نظام الباركود التلقائي

### 🎯 الهدف
عند اكتمال أمر الإنتاج، يتم تلقائياً:
- توليد باركود فريد لكل وحدة منتج تام
- الباركود يحتوي على: رقم أمر الإنتاج + رقم تسلسلي الوحدة
- طباعة تلقائية على طابعة Zebra
- تخزين معلومات: تاريخ التصنيع، تاريخ الانتهاء، المقاس

### 📂 الملفات المعدلة

#### 1. `production/signals.py`
```python
# عند تغيير حالة أمر الإنتاج إلى "مكتمل"
- إنشاء FinishedGoodUnit لكل قطعة منتجة
- توليد باركود فريد بصيغة: POID(6 أرقام) + Serial(4 أرقام) = 10-12 رقم
- حساب تاريخ الانتهاء من ProductManufacturingProfile
- طباعة تلقائية عبر print_finished_unit_label_auto()
```

#### 2. `inventory/barcode_utils.py` (جديد)
**دوال جديدة**:
- `generate_zpl_label()` - توليد أوامر ZPL لطابعة Zebra
- `send_to_zebra_printer()` - إرسال أوامر ZPL عبر socket/USB
- `print_finished_unit_label_auto()` - طباعة ليبل لوحدة منتج تام
- `send_to_thermal_printer()` - طباعة على xprinter
- `send_to_laser_printer()` - طباعة على HP LaserJet

#### 3. `inventory/models.py`
**موديل جديد**: `PrinterConfiguration`
```python
printer_type: zebra | xprinter | hp_laserjet | generic
document_type: barcode | invoice | receipt | report | id_card | label
connection_type: network | usb | shared
ip_address, port, usb_device_path, shared_printer_name
label_width_mm, label_height_mm, dpi
```

### 🔧 كيفية العمل

1. **إنشاء أمر إنتاج**: من شاشة الإنتاج
2. **تغيير الحالة إلى "مكتمل"**: يدوياً من قبل المستخدم
3. **توليد تلقائي**:
   - إنشاء `FinishedGoodUnit` بعدد القطع المنتجة
   - باركود فريد لكل وحدة
   - تخزين تاريخ التصنيع والانتهاء
4. **طباعة تلقائية**: إرسال ZPL للطابعة Zebra الافتراضية

### 📊 مثال على الباركود

```
أمر إنتاج رقم: 123
قطع منتجة: 50
الباركود الناتج:
- الوحدة 1: 000123000100
- الوحدة 2: 000123000200
- ...
- الوحدة 50: 000123005000
```

### ⚙️ إعداد طابعة Zebra

```python
# في Django Admin > Inventory > Printer Configurations
اسم الطابعة: Zebra ZD420
نوع الطابعة: zebra
نوع المستند: barcode
نوع الاتصال: network
عنوان IP: 192.168.1.100
المنفذ: 9100
عرض الليبل: 100 ملم
ارتفاع الليبل: 100 ملم
DPI: 203
افتراضية: نعم
```

---

## 2. نظام إدارة الإجازات المتقدم

### 🎯 الهدف
- السماح للموظفين بتقديم طلبات إجازة من المنزل
- نظام موافقة/رفض من قبل المسؤول
- حساب تلقائي لرصيد الإجازات
- فحص صلاحية الطلب قبل الموافقة

### 📂 الملفات الجديدة

#### 1. `hr/hr_utils.py` (جديد)
**دوال رئيسية**:
- `calculate_employee_leave_balance()` - حساب رصيد الإجازات
- `process_unauthorized_absence()` - معالجة الغياب بدون عذر
- `check_and_process_daily_absences()` - مهمة يومية للفحص

#### 2. `hr/leave_utils.py` (جديد)
**دوال مساعدة**:
- `calculate_working_days()` - حساب أيام العمل بين تاريخين
- `is_working_day()` - فحص إذا كان يوم عمل
- `get_next_working_day()` - الحصول على يوم العمل التالي

#### 3. `hr/views.py`
**Views جديدة**:
- `employee_portal()` - بوابة الموظف
- `employee_submit_leave_request()` - تقديم طلب إجازة
- `leave_approval_dashboard()` - لوحة الموافقات
- `approve_leave_request()` - الموافقة على طلب
- `reject_leave_request()` - رفض طلب

### 🔐 الصلاحيات

- **الموظف العادي**: يمكنه تقديم طلبات إجازة فقط
- **المسؤول (is_staff=True)**: يمكنه الموافقة/الرفض

### 📱 سير العمل

1. **الموظف يدخل للنظام**: `/hr/employee-portal/`
2. **يختار "طلب إجازة جديد"**
3. **يملأ البيانات**:
   - نوع الإجازة (سنوية، مرضية، إلخ)
   - تاريخ البداية والنهاية
   - السبب
4. **النظام يفحص الرصيد تلقائياً**
5. **إذا كان الرصيد كافي**: يُنشأ طلب بحالة "معلق"
6. **المسؤول يستلم إشعار** (يمكن إضافة notifications)
7. **المسؤول يدخل لوحة الموافقات**: `/hr/leave-approval/`
8. **الموافقة أو الرفض**:
   - موافقة → الحالة تتغير إلى "approved"
   - رفض → الحالة "rejected" + سبب الرفض

### 🔢 حساب الرصيد

```python
رصيد سنوي = 21 يوم (من LeaveType.days_per_year)
المستخدم هذا العام = 5 أيام
المخصوم من الغياب = 2 يوم
الرصيد المتبقي = 21 - 5 - 2 = 14 يوم
```

---

## 3. نظام الخصم التلقائي للغياب

### 🎯 الهدف
- تتبع غياب الموظفين تلقائياً
- الخصم من رصيد الإجازات أولاً
- إذا نفذ الرصيد، الخصم من الراتب
- عقوبة مضاعفة للغياب بدون عذر

### 📂 الموديلات الجديدة

#### 1. `AbsencePolicy`
سياسة الخصم:
```python
deduct_from_leave_first: bool = True  # خصم من الإجازات أولاً
salary_deduction_per_day: Decimal  # خصم ثابت يومي
salary_deduction_percentage: Decimal  # نسبة من الراتب اليومي
unauthorized_absence_multiplier: Decimal = 2.0  # مضاعف للغياب بدون عذر
```

#### 2. `EmployeeAbsence`
سجل الغياب:
```python
employee, absence_date, absence_type
deducted_from_leave: bool
leave_days_deducted: Decimal
deducted_from_salary: bool
salary_deduction_amount: Decimal
is_processed: bool
```

### ⚙️ سير العمل التلقائي

**مهمة يومية** (Cron Job أو Celery):
```python
# يتم تشغيلها يومياً الساعة 12 منتصف الليل
check_and_process_daily_absences()
```

**الخطوات**:
1. فحص إذا كان اليوم السابق يوم عمل
2. الحصول على جميع الموظفين النشطين
3. لكل موظف:
   - فحص إذا كان لديه `AttendanceRecord` لليوم السابق
   - إذا لم يكن موجود → موظف غائب
   - فحص إذا كان لديه `LeaveRequest` معتمدة
   - إذا لم يكن لديه → غياب بدون عذر
   - معالجة الغياب عبر `process_unauthorized_absence()`

**معالجة الخصم**:
```python
if policy.deduct_from_leave_first:
    if رصيد_الإجازات >= 1:
        خصم_من_الإجازات(1 يوم)
    else:
        خصم_من_الراتب(حسب_السياسة)
else:
    خصم_من_الراتب_مباشرة()

if absence_type == 'unauthorized':
    الخصم *= unauthorized_absence_multiplier  # مضاعفة العقوبة
```

### 📊 مثال عملي

**الموظف**: أحمد  
**الراتب الأساسي**: 6000 جنيه  
**رصيد الإجازات**: 3 أيام  
**السياسة**: خصم 10% من الراتب اليومي

**اليوم الأول (غياب بعذر)**:
- خصم من الإجازات: 1 يوم
- الرصيد المتبقي: 2 يوم
- الخصم المالي: 0

**اليوم الثاني (غياب بدون عذر)**:
- خصم من الإجازات: 1 يوم
- الخصم المالي الأساسي: 6000 / 30 * 0.10 = 20 جنيه
- مضاعفة للغياب بدون عذر: 20 * 2.0 = 40 جنيه
- الرصيد المتبقي: 1 يوم

**اليوم الخامس (رصيد منتهي)**:
- خصم من الإجازات: 0 (الرصيد منتهي)
- خصم من الراتب: 6000 / 30 * 0.10 = 20 جنيه

---

## 4. نظام الطباعة متعدد الطابعات

### 🎯 الهدف
دعم 3 أنواع طابعات:
- **Zebra**: للباركود والليبلات
- **xprinter**: للإيصالات الحرارية
- **HP LaserJet**: للفواتير والتقارير

### 📂 الدوال الرئيسية

#### 1. `send_to_zebra_printer()`
```python
# إرسال أوامر ZPL عبر socket
connection_type: network | usb
network → socket.connect(ip, port)
usb → win32print.WritePrinter()
```

#### 2. `send_to_thermal_printer()`
```python
# استخدام python-escpos
from escpos.printer import Network
printer = Network(ip, port)
printer.text(content)
printer.cut()
```

#### 3. `send_to_laser_printer()`
```python
# Windows: win32api.ShellExecute("print", pdf_file)
# Linux: cups.Connection().printFile()
```

### ⚙️ إعداد الطابعات

**في Django Admin**:
```python
# طابعة 1: Zebra للباركود
name: "Zebra ZD420"
printer_type: zebra
document_type: barcode
connection_type: network
ip_address: 192.168.1.100
port: 9100
is_default: True

# طابعة 2: xprinter للإيصالات
name: "Xprinter XP-80"
printer_type: xprinter
document_type: receipt
connection_type: network
ip_address: 192.168.1.101
port: 9100
is_default: True

# طابعة 3: HP للفواتير
name: "HP LaserJet P1102"
printer_type: hp_laserjet
document_type: invoice
connection_type: shared
shared_printer_name: "HP_P1102"
is_default: True
```

### 🔄 التوجيه التلقائي

عند طباعة مستند:
```python
if document_type == 'barcode':
    printer = PrinterConfiguration.objects.get(
        document_type='barcode',
        is_default=True
    )
    send_to_zebra_printer(zpl_commands, printer)

elif document_type == 'receipt':
    printer = PrinterConfiguration.objects.get(
        document_type='receipt',
        is_default=True
    )
    send_to_thermal_printer(html_content, printer)

elif document_type == 'invoice':
    printer = PrinterConfiguration.objects.get(
        document_type='invoice',
        is_default=True
    )
    send_to_laser_printer(pdf_file, printer)
```

---

## 5. نظام بطاقات الهوية

### 🎯 الهدف
- إنشاء بطاقة هوية لكل موظف
- QR Code يحتوي على بيانات تسجيل الدخول المشفرة
- طباعة البطاقة
- مسح QR Code للدخول التلقائي

### 📂 الموديل الجديد

#### `EmployeeIDCard`
```python
employee: ForeignKey(Employee)
card_number: CharField (فريد) - "EMP-00001-ABC12345"
qr_code_data: TextField - JWT token مشفر
qr_code_image: ImageField - صورة QR Code
issue_date: DateField - تاريخ الإصدار
expiry_date: DateField - تاريخ الانتهاء (بعد 12 شهر)
status: active | expired | lost | replaced
print_count: عدد مرات الطباعة
scan_count: عدد مرات المسح
```

### 🔐 JWT Token في QR Code

```python
payload = {
    'user_id': employee.user.id,
    'employee_id': employee.id,
    'username': employee.user.username,
    'exp': datetime.utcnow() + timedelta(days=365),
    'type': 'employee_qr_login'
}
token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

### 📱 سير العمل

#### إنشاء البطاقة:
```python
# من صفحة تفاصيل الموظف
/hr/id-cards/generate/<employee_id>/

# خطوات:
1. إنهاء صلاحية البطاقات القديمة
2. توليد رقم بطاقة فريد
3. إنشاء QR Code مع JWT
4. حفظ صورة QR Code
5. إعادة التوجيه لصفحة الطباعة
```

#### طباعة البطاقة:
```python
/hr/id-cards/print/<card_id>/

# Template: hr/id_card_print.html
يحتوي على:
- صورة الموظف
- الاسم والوظيفة
- الرقم الوظيفي
- QR Code
- شعار الشركة
- تاريخ الإصدار والانتهاء
```

#### تسجيل الدخول بـ QR:
```python
/hr/qr-login/

# الواجهة:
1. كاميرا لمسح QR Code (html5-qrcode)
2. قراءة التوكن
3. verify_qr_login_token()
4. تسجيل دخول تلقائي
5. إعادة توجيه للبوابة
```

### 🎨 تصميم البطاقة

```html
<div class="id-card" style="width: 8.5cm; height: 5.5cm;">
  <div class="header">
    <img src="{{ company_logo }}" />
    <h3>{{ company_name }}</h3>
  </div>
  
  <div class="body">
    <img src="{{ employee.photo }}" class="photo" />
    <h2>{{ employee.arabic_name }}</h2>
    <p>{{ employee.position }}</p>
    <p>{{ employee.employee_id }}</p>
  </div>
  
  <div class="footer">
    <img src="{{ card.qr_code_image }}" class="qr-code" />
    <p>صالحة حتى: {{ card.expiry_date }}</p>
  </div>
</div>
```

---

## 6. إعداد النظام

### 📦 تثبيت المكتبات

```bash
# الانتقال لمجلد المشروع
cd h:\برمجة\الشامل\الشامل\الشامل\app

# تفعيل البيئة الافتراضية
.\.venv\Scripts\Activate.ps1

# تثبيت المكتبات الجديدة
pip install python-zpl==0.2.0
pip install python-escpos==3.0
pip install PyJWT==2.9.0

# Windows only - للطباعة المباشرة
pip install pywin32

# Linux only - إذا كنت على Linux
# sudo apt-get install libcups2-dev
# pip install pycups
```

### 🗄️ تطبيق Migrations

```bash
# إنشاء migrations للموديلات الجديدة
python manage.py makemigrations inventory
python manage.py makemigrations hr

# تطبيق Migrations
python manage.py migrate
```

### ⚙️ الإعدادات الأولية

#### 1. إنشاء سياسة غياب افتراضية
```python
# في Django Admin أو shell
from hr.models import AbsencePolicy

AbsencePolicy.objects.create(
    name="السياسة الافتراضية",
    deduct_from_leave_first=True,
    salary_deduction_percentage=10,  # 10% من الراتب اليومي
    unauthorized_absence_multiplier=2.0,
    is_default=True,
    is_active=True
)
```

#### 2. إعداد الطابعات
```python
# في Django Admin > Inventory > Printer Configurations
# أضف 3 طابعات حسب الأمثلة في القسم 4
```

#### 3. إعداد أيام العمل
```python
from hr.models import WeekendDay

# الجمعة والسبت عطلة
WeekendDay.objects.create(day_of_week=4, is_working_day=False)  # Friday
WeekendDay.objects.create(day_of_week=5, is_working_day=False)  # Saturday
```

### 🔄 المهام اليومية (Cron)

**إعداد Celery Task** (اختياري):
```python
# في hr/tasks.py
from celery import shared_task
from .hr_utils import check_and_process_daily_absences

@shared_task
def process_daily_absences():
    return check_and_process_daily_absences()

# في celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'process-daily-absences': {
        'task': 'hr.tasks.process_daily_absences',
        'schedule': crontab(hour=0, minute=1),  # كل يوم 12:01 صباحاً
    },
}
```

**أو Windows Task Scheduler**:
```bash
# إنشاء ملف process_absences.bat
cd h:\برمجة\الشامل\الشامل\الشامل\app
.\.venv\Scripts\python.exe manage.py shell -c "from hr.hr_utils import check_and_process_daily_absences; check_and_process_daily_absences()"

# جدولة في Task Scheduler:
# - Trigger: يومياً الساعة 12:01 صباحاً
# - Action: Start a program -> process_absences.bat
```

---

## 7. دليل الاستخدام

### 👤 للموظف

#### تقديم طلب إجازة:
1. الدخول للنظام: `http://localhost:8000/hr/employee-portal/`
2. اختر "طلب إجازة جديد"
3. املأ البيانات:
   - نوع الإجازة
   - تاريخ البداية والنهاية
   - السبب
4. اضغط "تقديم"
5. ستظهر رسالة تأكيد إذا كان الرصيد كافي

#### عرض الرصيد:
- في البوابة الرئيسية `/hr/employee-portal/`
- ستجد جدول بأنواع الإجازات والرصيد المتبقي

### 👨‍💼 للمسؤول

#### الموافقة على الإجازات:
1. الدخول: `http://localhost:8000/hr/leave-approval/`
2. ستجد قائمة بالطلبات المعلقة
3. لكل طلب:
   - اضغط "موافقة" للقبول
   - اضغط "رفض" واكتب السبب

#### إنشاء بطاقة هوية:
1. الذهاب لصفحة تفاصيل الموظف
2. اضغط "إنشاء بطاقة هوية جديدة"
3. ستفتح صفحة الطباعة تلقائياً
4. اطبع البطاقة

### 🏭 لمشرف الإنتاج

#### طباعة باركود:
1. إنشاء أمر إنتاج من `/production/orders/create/`
2. عند الانتهاء، غيّر الحالة إلى "مكتمل"
3. سيتم تلقائياً:
   - إنشاء وحدات المنتج التام
   - توليد باركود لكل وحدة
   - طباعة على طابعة Zebra

#### طباعة يدوية:
إذا فشلت الطباعة التلقائية:
```python
# في Django shell
from production.models import FinishedGoodUnit
from inventory.barcode_utils import print_finished_unit_label_auto

unit = FinishedGoodUnit.objects.get(id=123)
success, message = print_finished_unit_label_auto(unit)
print(message)
```

### 🖨️ اختبار الطابعات

```python
# في Django shell
from inventory.models import PrinterConfiguration
from inventory.barcode_utils import send_to_zebra_printer

# الحصول على طابعة Zebra
printer = PrinterConfiguration.objects.get(printer_type='zebra', is_default=True)

# أوامر ZPL تجريبية
zpl = """
^XA
^FO50,50^A0N,50,50^FDTest Print^FS
^FO50,120^BCN,100,Y,N,N^FD123456789012^FS
^XZ
"""

success, message = send_to_zebra_printer(zpl, printer)
print(f"Success: {success}, Message: {message}")
```

---

## 🐛 استكشاف الأخطاء

### مشكلة: الطباعة التلقائية لا تعمل

**الحل**:
1. فحص وجود طابعة Zebra افتراضية:
   ```python
   from inventory.models import PrinterConfiguration
   PrinterConfiguration.objects.filter(
       printer_type='zebra',
       document_type='barcode',
       is_default=True
   ).exists()
   ```
2. فحص الاتصال بالطابعة:
   ```bash
   # Windows
   Test-NetConnection -ComputerName 192.168.1.100 -Port 9100
   ```
3. فحص Logs:
   ```python
   # في production/signals.py
   # ستجد رسائل warning إذا فشلت الطباعة
   ```

### مشكلة: QR Code لا يعمل للدخول

**الحل**:
1. فحص صلاحية البطاقة:
   ```python
   from hr.models import EmployeeIDCard
   card = EmployeeIDCard.objects.get(card_number='...')
   print(card.is_valid())  # يجب أن يكون True
   ```
2. فحص التوكن:
   ```python
   from hr.hr_utils import verify_qr_login_token
   success, result = verify_qr_login_token(card.qr_code_data)
   print(f"Success: {success}, Result: {result}")
   ```

### مشكلة: الخصم التلقائي لا يعمل

**الحل**:
1. فحص وجود سياسة افتراضية:
   ```python
   from hr.models import AbsencePolicy
   AbsencePolicy.objects.filter(is_default=True, is_active=True).exists()
   ```
2. تشغيل المهمة يدوياً:
   ```python
   from hr.hr_utils import check_and_process_daily_absences
   result = check_and_process_daily_absences()
   print(result)
   ```

---

## 📞 الدعم الفني

- **مشاكل الطباعة**: تحقق من `/docs/PRINTER_TROUBLESHOOTING.md`
- **مشاكل الإجازات**: تحقق من `/docs/HR_TROUBLESHOOTING.md`
- **مشاكل الباركود**: تحقق من `/docs/BARCODE_TROUBLESHOOTING.md`

---

## 🔄 التحديثات المستقبلية

### مخطط:
- [ ] إشعارات SMS/Email عند الموافقة/الرفض
- [ ] تكامل مع أجهزة البصمة (ZKTeco SDK)
- [ ] تطبيق موبايل لطلب الإجازات
- [ ] تقارير تحليلية للغياب
- [ ] نظام حوافز للحضور المنتظم
- [ ] طباعة ليبلات بالجملة (Batch Printing)
- [ ] دعم طابعات إضافية (Brother, Canon)

---

**تم بحمد الله ✨**  
نظام شامل ومتكامل لإدارة الإنتاج والموارد البشرية 🎯
