"""
اختبار شامل لنظام الدخول ببطاقة الموظف
يفحص جميع السيناريوهات والتكامل مع الصلاحيات والموديولات
"""
import os
import sys
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType
from hr.models import Employee, EmployeeIDCard, AttendanceRecord, Department, JobPosition, LeaveRequest, LeaveType
from hr.hr_utils import verify_qr_login_token, create_employee_id_card
from users.models import UserRole
from datetime import date, timedelta

def print_header(title):
    print('\n' + '=' * 70)
    print(f' {title}')
    print('=' * 70)

def print_section(title):
    print(f'\n--- {title} ---')

def test_result(success, message):
    symbol = '✓' if success else '✗'
    print(f'  {symbol} {message}')
    return success

print_header('اختبار شامل لنظام الدخول ببطاقة الموظف')

client = Client(enforce_csrf_checks=False)
all_tests_passed = True

# ====== 1. فحص البنية التحتية ======
print_section('1. فحص البنية التحتية')

# فحص الموظفين
emp_count = Employee.objects.count()
all_tests_passed &= test_result(emp_count > 0, f'عدد الموظفين: {emp_count}')

# فحص بطاقات الهوية
card_count = EmployeeIDCard.objects.count()
all_tests_passed &= test_result(card_count > 0, f'عدد بطاقات الهوية: {card_count}')

# فحص البطاقات النشطة
active_cards = EmployeeIDCard.objects.filter(status='active').count()
all_tests_passed &= test_result(active_cards > 0, f'بطاقات نشطة: {active_cards}')

# فحص الموظفين المرتبطين بمستخدمين
emp_with_users = Employee.objects.filter(user__isnull=False).count()
all_tests_passed &= test_result(emp_with_users > 0, f'موظفين مع حسابات: {emp_with_users}')

# ====== 2. فحص صفحة تسجيل الدخول ======
print_section('2. فحص صفحة تسجيل الدخول')

response = client.get('/accounts/login/')
all_tests_passed &= test_result(response.status_code == 200, f'صفحة تسجيل الدخول: {response.status_code}')

content = response.content.decode('utf-8')
has_qr = 'qr-login-section' in content or 'qrScannerModal' in content
all_tests_passed &= test_result(has_qr, 'قسم الدخول بـ QR موجود')

has_barcode = 'qrTokenInput' in content
all_tests_passed &= test_result(has_barcode, 'حقل إدخال الباركود موجود')

has_camera = 'toggleCameraBtn' in content or 'cameraScanner' in content
all_tests_passed &= test_result(has_camera, 'دعم الكاميرا موجود')

# ====== 3. اختبار الدخول بالطرق المختلفة ======
print_section('3. اختبار الدخول بالطرق المختلفة')

active_card = EmployeeIDCard.objects.filter(status='active').first()
if active_card:
    # تنظيف سجلات اليوم
    AttendanceRecord.objects.filter(employee=active_card.employee, date=date.today()).delete()
    
    # أ. الدخول برقم البطاقة
    resp = client.post('/hr/qr-login/action/', 
        data=json.dumps({'token': active_card.card_number, 'action': 'status'}),
        content_type='application/json')
    all_tests_passed &= test_result(resp.status_code == 200, f'الدخول برقم البطاقة: {resp.status_code}')
    
    # ب. الدخول برقم الموظف
    resp = client.post('/hr/qr-login/action/',
        data=json.dumps({'token': active_card.employee.employee_id, 'action': 'status'}),
        content_type='application/json')
    all_tests_passed &= test_result(resp.status_code == 200, f'الدخول برقم الموظف: {resp.status_code}')
    
    # ج. الدخول بـ QR Token
    resp = client.post('/hr/qr-login/action/',
        data=json.dumps({'token': active_card.qr_code_data, 'action': 'status'}),
        content_type='application/json')
    all_tests_passed &= test_result(resp.status_code == 200, f'الدخول بـ QR Token: {resp.status_code}')
    
    # د. تسجيل الحضور
    resp = client.post('/hr/qr-login/action/',
        data=json.dumps({'token': active_card.card_number, 'action': 'check_in'}),
        content_type='application/json')
    data = resp.json()
    all_tests_passed &= test_result(data.get('success'), f'تسجيل الحضور: {data.get("message")}')
    
    # هـ. تسجيل الانصراف
    resp = client.post('/hr/qr-login/action/',
        data=json.dumps({'token': active_card.card_number, 'action': 'check_out'}),
        content_type='application/json')
    data = resp.json()
    all_tests_passed &= test_result(data.get('success'), f'تسجيل الانصراف: {data.get("message")}')
    
    # و. التسجيل التلقائي (يجب أن يقول "تم التسجيل مسبقاً")
    resp = client.post('/hr/qr-login/action/',
        data=json.dumps({'token': active_card.card_number, 'action': 'auto'}),
        content_type='application/json')
    data = resp.json()
    all_tests_passed &= test_result(data.get('success'), f'التسجيل التلقائي: {data.get("message")}')

# ====== 4. اختبار بوابة الموظف ======
print_section('4. اختبار بوابة الموظف')

# تسجيل الدخول
superadmin = User.objects.get(username='superadmin')
client.force_login(superadmin)

resp = client.get('/hr/employee-portal/')
all_tests_passed &= test_result(resp.status_code == 200, f'بوابة الموظف: {resp.status_code}')

# ====== 5. اختبار صفحات إدارة البطاقات ======
print_section('5. اختبار صفحات إدارة البطاقات')

resp = client.get('/hr/id-cards/')
all_tests_passed &= test_result(resp.status_code == 200, f'قائمة البطاقات: {resp.status_code}')

if active_card:
    resp = client.get(f'/hr/id-cards/preview/{active_card.id}/')
    all_tests_passed &= test_result(resp.status_code == 200, f'معاينة البطاقة: {resp.status_code}')

# ====== 6. اختبار التكامل مع HR ======
print_section('6. اختبار التكامل مع HR')

resp = client.get('/hr/')
all_tests_passed &= test_result(resp.status_code == 200, f'لوحة HR: {resp.status_code}')

resp = client.get('/hr/employees/')
all_tests_passed &= test_result(resp.status_code == 200, f'قائمة الموظفين: {resp.status_code}')

resp = client.get('/hr/attendance/')
all_tests_passed &= test_result(resp.status_code == 200, f'سجل الحضور: {resp.status_code}')

# ====== 7. فحص سجلات الحضور ======
print_section('7. فحص سجلات الحضور')

today_records = AttendanceRecord.objects.filter(date=date.today())
all_tests_passed &= test_result(today_records.count() > 0, f'سجلات اليوم: {today_records.count()}')

qr_records = today_records.filter(source='qr')
all_tests_passed &= test_result(qr_records.count() > 0, f'سجلات QR: {qr_records.count()}')

# ====== 8. فحص الصلاحيات ======
print_section('8. فحص الصلاحيات')

hr_perms = Permission.objects.filter(content_type__app_label='hr').count()
all_tests_passed &= test_result(hr_perms > 0, f'صلاحيات HR: {hr_perms}')

# فحص صلاحيات superadmin
all_tests_passed &= test_result(superadmin.is_superuser, f'superadmin is_superuser: {superadmin.is_superuser}')

# ====== 9. اختبار رفض البطاقة غير الصالحة ======
print_section('9. اختبار رفض البطاقة غير الصالحة')

resp = client.post('/hr/qr-login/action/',
    data=json.dumps({'token': 'INVALID-TOKEN-12345', 'action': 'status'}),
    content_type='application/json')
data = resp.json()
all_tests_passed &= test_result(not data.get('success'), f'رفض بطاقة غير صالحة: {data.get("message")}')

resp = client.post('/hr/qr-login/action/',
    data=json.dumps({'token': '', 'action': 'status'}),
    content_type='application/json')
all_tests_passed &= test_result(resp.status_code in [400, 403], f'رفض بطاقة فارغة: {resp.status_code}')

# ====== 10. ملخص النتائج ======
print_header('ملخص النتائج')

if all_tests_passed:
    print('\n  ✓✓✓ جميع الاختبارات نجحت! ✓✓✓')
    print('\n  نظام الدخول ببطاقة الموظف يعمل بشكل صحيح.')
else:
    print('\n  ✗ بعض الاختبارات فشلت!')
    print('  راجع الأخطاء أعلاه.')

print('\n' + '=' * 70)
print(' الميزات المتاحة:')
print('=' * 70)
print('''
  1. تسجيل الدخول عبر:
     - رقم بطاقة الموظف
     - رقم الموظف (Employee ID)
     - QR Code / Barcode

  2. تسجيل الحضور والانصراف التلقائي

  3. بوابة الموظف للخدمة الذاتية

  4. إدارة بطاقات الهوية:
     - إنشاء بطاقات جديدة
     - معاينة وطباعة
     - إبطال واستبدال

  5. التكامل مع:
     - نظام الموارد البشرية (HR)
     - نظام الصلاحيات والمستخدمين
     - سجلات الحضور
''')
