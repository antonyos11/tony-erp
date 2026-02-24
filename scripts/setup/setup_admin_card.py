"""
سكريبت إنشاء بطاقة هوية لمدير النظام وإكمال الإعداد
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from hr.models import Employee, EmployeeIDCard
from hr.hr_utils import create_employee_id_card
from datetime import date, timedelta

print('=' * 60)
print('إنشاء بطاقة هوية لمدير النظام')
print('=' * 60)

# البحث عن موظف مدير النظام
admin_employee = Employee.objects.filter(employee_id='EMP-ADMIN-001').first()

if admin_employee:
    print(f'تم العثور على الموظف: {admin_employee.arabic_name}')
    print(f'المستخدم المرتبط: {admin_employee.user.username}')
    
    # فحص إذا كان لديه بطاقة
    existing_card = admin_employee.id_cards.filter(status='active').first()
    
    if existing_card:
        print(f'✓ لديه بطاقة نشطة بالفعل: {existing_card.card_number}')
    else:
        print('⚠ لا توجد بطاقة نشطة، جاري الإنشاء...')
        
        try:
            card = create_employee_id_card(admin_employee, expiry_months=12)
            print(f'✓ تم إنشاء البطاقة بنجاح!')
            print(f'  - رقم البطاقة: {card.card_number}')
            print(f'  - تاريخ الانتهاء: {card.expiry_date}')
            print(f'  - QR Code: {"موجود" if card.qr_code_data else "غير موجود"}')
        except Exception as e:
            print(f'✗ خطأ في إنشاء البطاقة: {e}')
else:
    print('✗ لم يتم العثور على موظف مدير النظام')

# فحص الصلاحيات
print('\n' + '=' * 60)
print('فحص نظام الصلاحيات')
print('=' * 60)

# عرض الصلاحيات الموجودة لموديول HR
hr_content_types = ContentType.objects.filter(app_label='hr')
print(f'\nعدد نماذج HR: {hr_content_types.count()}')

hr_permissions = Permission.objects.filter(content_type__app_label='hr')
print(f'عدد صلاحيات HR: {hr_permissions.count()}')

# عرض بعض الصلاحيات
print('\nبعض صلاحيات HR:')
for perm in hr_permissions[:10]:
    print(f'  - {perm.codename}: {perm.name}')

# فحص صلاحيات superadmin
superadmin = User.objects.get(username='superadmin')
print(f'\nالمستخدم: {superadmin.username}')
print(f'  - is_superuser: {superadmin.is_superuser}')
print(f'  - is_staff: {superadmin.is_staff}')
print(f'  - عدد الصلاحيات المباشرة: {superadmin.user_permissions.count()}')
print(f'  - عدد المجموعات: {superadmin.groups.count()}')

# عرض المجموعات
if superadmin.groups.exists():
    print('\n  المجموعات:')
    for group in superadmin.groups.all():
        print(f'    - {group.name} ({group.permissions.count()} صلاحيات)')

print('\n' + '=' * 60)
print('انتهى')
print('=' * 60)
