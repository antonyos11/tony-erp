"""
اختبار API الدخول ببطاقة الموظف مع تصحيح الـ CSRF
"""
import os
import sys
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from hr.models import Employee, EmployeeIDCard, AttendanceRecord
from datetime import date

print('=' * 70)
print('اختبار API الدخول ببطاقة الموظف')
print('=' * 70)

client = Client(enforce_csrf_checks=False)  # تعطيل فحص CSRF للاختبار

# الحصول على بطاقة نشطة
active_card = EmployeeIDCard.objects.filter(status='active').first()
print(f'\nالبطاقة: {active_card.card_number}')
print(f'الموظف: {active_card.employee.arabic_name}')

# حذف سجلات الحضور السابقة لليوم (للاختبار النظيف)
print('\n--- تنظيف سجلات الحضور اليوم للاختبار ---')
deleted = AttendanceRecord.objects.filter(
    employee=active_card.employee,
    date=date.today()
).delete()
print(f'تم حذف {deleted[0]} سجلات')

# اختبار 1: الدخول برقم البطاقة
print('\n=== اختبار 1: الدخول برقم البطاقة ===')
response = client.post(
    '/hr/qr-login/action/',
    data=json.dumps({'token': active_card.card_number, 'action': 'auto'}),
    content_type='application/json'
)
print(f'Status: {response.status_code}')
try:
    data = response.json()
    print(f'Response: {json.dumps(data, ensure_ascii=False, indent=2)}')
except:
    print(f'Raw Response: {response.content.decode()[:500]}')

# اختبار 2: الدخول برقم الموظف
print('\n=== اختبار 2: الدخول برقم الموظف ===')
emp_id = active_card.employee.employee_id
print(f'رقم الموظف: {emp_id}')
response = client.post(
    '/hr/qr-login/action/',
    data=json.dumps({'token': emp_id, 'action': 'auto'}),
    content_type='application/json'
)
print(f'Status: {response.status_code}')
try:
    data = response.json()
    print(f'Response: {json.dumps(data, ensure_ascii=False, indent=2)}')
except:
    print(f'Raw Response: {response.content.decode()[:500]}')

# اختبار 3: الدخول بـ QR Token الكامل
print('\n=== اختبار 3: الدخول بـ QR Token ===')
response = client.post(
    '/hr/qr-login/action/',
    data=json.dumps({'token': active_card.qr_code_data, 'action': 'auto'}),
    content_type='application/json'
)
print(f'Status: {response.status_code}')
try:
    data = response.json()
    print(f'Response: {json.dumps(data, ensure_ascii=False, indent=2)}')
except:
    print(f'Raw Response: {response.content.decode()[:500]}')

# فحص سجلات الحضور
print('\n=== سجلات الحضور بعد الاختبار ===')
records = AttendanceRecord.objects.filter(
    employee=active_card.employee,
    date=date.today()
).order_by('time')
for rec in records:
    print(f'  {rec.record_type}: {rec.time} (source: {rec.source})')

print('\n' + '=' * 70)
print('انتهى')
print('=' * 70)
