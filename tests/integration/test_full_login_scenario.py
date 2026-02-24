"""
اختبار سيناريو الدخول الكامل ببطاقة الموظف
"""
import os
import sys
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from hr.models import Employee, EmployeeIDCard, AttendanceRecord
from hr.hr_utils import verify_qr_login_token
from datetime import date

print('=' * 70)
print('اختبار سيناريو الدخول الكامل ببطاقة الموظف')
print('=' * 70)

client = Client()

# 1. اختبار صفحة تسجيل الدخول
print('\n=== 1. اختبار صفحة تسجيل الدخول ===')
response = client.get('/accounts/login/')
print(f'  GET /accounts/login/: {response.status_code}')
if response.status_code == 200:
    content = response.content.decode('utf-8')
    has_qr_section = 'qr-login-section' in content or 'qrScannerModal' in content
    print(f'  ✓ قسم QR Login موجود: {has_qr_section}')
else:
    print(f'  ✗ خطأ في تحميل الصفحة')

# 2. اختبار QR Attendance Action API
print('\n=== 2. اختبار QR Attendance Action API ===')

# الحصول على بطاقة نشطة
active_card = EmployeeIDCard.objects.filter(status='active').first()
if active_card:
    print(f'  البطاقة المستخدمة: {active_card.card_number}')
    print(f'  الموظف: {active_card.employee.arabic_name}')
    
    # اختبار التحقق من QR Token
    print('\n  --- اختبار التحقق من QR Token ---')
    success, result = verify_qr_login_token(active_card.qr_code_data)
    if success:
        print(f'  ✓ التحقق من JWT Token ناجح')
        print(f'    المستخدم: {result.username}')
    else:
        print(f'  ✗ فشل التحقق: {result}')
    
    # اختبار API endpoint
    print('\n  --- اختبار qr_attendance_action API ---')
    
    # اختبار بـ token كامل (JWT)
    response = client.post(
        '/hr/qr-login/action/',
        data=json.dumps({'token': active_card.qr_code_data, 'action': 'status'}),
        content_type='application/json'
    )
    print(f'  POST with JWT token: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'    Success: {data.get("success")}')
        print(f'    Message: {data.get("message")}')
        if data.get('employee'):
            print(f'    Employee: {data["employee"].get("name")}')
    else:
        try:
            print(f'    Error: {response.json()}')
        except:
            print(f'    Error: {response.content[:200]}')
    
    # اختبار برقم البطاقة فقط
    print('\n  --- اختبار برقم البطاقة ---')
    response = client.post(
        '/hr/qr-login/action/',
        data=json.dumps({'token': active_card.card_number, 'action': 'status'}),
        content_type='application/json'
    )
    print(f'  POST with card number: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'    Success: {data.get("success")}')
        print(f'    Message: {data.get("message")}')
    else:
        try:
            print(f'    Error: {response.json()}')
        except:
            pass
    
    # اختبار تسجيل حضور تلقائي
    print('\n  --- اختبار تسجيل الحضور التلقائي ---')
    response = client.post(
        '/hr/qr-login/action/',
        data=json.dumps({'token': active_card.qr_code_data, 'action': 'auto'}),
        content_type='application/json'
    )
    print(f'  POST auto attendance: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'    Success: {data.get("success")}')
        print(f'    Message: {data.get("message")}')
        print(f'    Action: {data.get("action_performed")}')
        if data.get('redirect_url'):
            print(f'    Redirect: {data.get("redirect_url")}')

else:
    print('  ✗ لا توجد بطاقات نشطة للاختبار')

# 3. فحص سجلات الحضور
print('\n=== 3. فحص سجلات الحضور اليوم ===')
today_records = AttendanceRecord.objects.filter(date=date.today())
print(f'  عدد السجلات اليوم: {today_records.count()}')
for rec in today_records:
    print(f'    - {rec.employee.arabic_name}: {rec.record_type} @ {rec.time} (source: {rec.source})')

# 4. اختبار بوابة الموظف
print('\n=== 4. اختبار بوابة الموظف ===')

# تسجيل دخول المستخدم أولاً
user = User.objects.get(username='superadmin')
client.force_login(user)

response = client.get('/hr/employee-portal/')
print(f'  GET /hr/employee-portal/: {response.status_code}')
if response.status_code == 200:
    print(f'  ✓ بوابة الموظف تعمل')
elif response.status_code == 302:
    print(f'  ⚠ إعادة توجيه إلى: {response.url}')
else:
    print(f'  ✗ خطأ: {response.status_code}')

# 5. اختبار صفحة بطاقات الهوية
print('\n=== 5. اختبار صفحة إدارة البطاقات ===')
response = client.get('/hr/id-cards/')
print(f'  GET /hr/id-cards/: {response.status_code}')
if response.status_code == 200:
    print(f'  ✓ صفحة البطاقات تعمل')
else:
    print(f'  ✗ خطأ: {response.status_code}')

print('\n' + '=' * 70)
print('انتهى الاختبار')
print('=' * 70)
