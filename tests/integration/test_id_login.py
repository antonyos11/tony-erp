"""
سكريبت اختبار نظام الدخول ببطاقة الموظف
"""
import os
import sys
import django

# تهيئة Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from hr.models import Employee, EmployeeIDCard, Department, JobPosition
from hr.hr_utils import generate_employee_qr_login, verify_qr_login_token

print('=' * 60)
print('فحص نظام الدخول ببطاقة الموظف (ID Login System)')
print('=' * 60)

# 1. فحص المستخدمين
print('\n=== 1. فحص المستخدمين ===')
users = User.objects.all()[:10]
print(f'إجمالي المستخدمين: {User.objects.count()}')
for u in users:
    has_emp = hasattr(u, 'employee_profile')
    emp = getattr(u, 'employee_profile', None) if has_emp else None
    print(f'  - {u.username} (ID: {u.id}, Active: {u.is_active}, Has Employee: {has_emp})')
    if emp:
        print(f'      -> Employee: {emp.arabic_name}, EmpID: {emp.employee_id}')

# 2. فحص الموظفين
print('\n=== 2. فحص الموظفين ===')
employees = Employee.objects.all()[:10]
print(f'إجمالي الموظفين: {Employee.objects.count()}')
for emp in employees:
    user = emp.user
    print(f'  - {emp.arabic_name} (ID: {emp.employee_id}, User: {user.username if user else "لا يوجد"})')

# 3. فحص بطاقات الهوية
print('\n=== 3. فحص بطاقات الهوية ===')
cards = EmployeeIDCard.objects.all()[:10]
print(f'إجمالي البطاقات: {EmployeeIDCard.objects.count()}')
print(f'بطاقات نشطة: {EmployeeIDCard.objects.filter(status="active").count()}')
for card in cards:
    print(f'  - رقم البطاقة: {card.card_number}')
    print(f'      الموظف: {card.employee.arabic_name}')
    print(f'      الحالة: {card.status}')
    print(f'      QR Data موجود: {"✓" if card.qr_code_data else "✗"}')
    print(f'      صلاحية: {card.expiry_date}')

# 4. اختبار نظام التحقق من QR
print('\n=== 4. اختبار نظام التحقق من QR ===')
active_card = EmployeeIDCard.objects.filter(status='active', qr_code_data__isnull=False).exclude(qr_code_data='').first()
if active_card:
    print(f'اختبار بطاقة: {active_card.card_number}')
    print(f'الموظف: {active_card.employee.arabic_name}')
    
    # اختبار التحقق من QR Token
    success, result = verify_qr_login_token(active_card.qr_code_data)
    if success:
        print(f'✓ التحقق ناجح! المستخدم: {result.username}')
    else:
        print(f'✗ فشل التحقق: {result}')
else:
    print('لا توجد بطاقات نشطة مع QR Code')

# 5. فحص الموظفين بدون بطاقات
print('\n=== 5. الموظفين بدون بطاقات هوية ===')
employees_without_cards = Employee.objects.filter(id_cards__isnull=True)
print(f'عدد الموظفين بدون بطاقات: {employees_without_cards.count()}')
for emp in employees_without_cards[:5]:
    print(f'  - {emp.arabic_name} (ID: {emp.employee_id})')

# 6. فحص الموظفين بدون حساب مستخدم
print('\n=== 6. الموظفين بدون حساب مستخدم ===')
employees_without_user = Employee.objects.filter(user__isnull=True)
print(f'عدد الموظفين بدون حساب: {employees_without_user.count()}')
for emp in employees_without_user[:5]:
    print(f'  - {emp.arabic_name} (ID: {emp.employee_id})')

print('\n' + '=' * 60)
print('انتهى الفحص')
print('=' * 60)
