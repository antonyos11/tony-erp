"""
إنشاء ملف موظف للمستخدم superadmin
"""
import os
import sys
import django

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth.models import User
from hr.models import Employee, Department, JobPosition
from datetime import date

def create_employee_for_admin():
    """إنشاء ملف موظف للمستخدم superadmin"""
    
    # الحصول على المستخدم
    try:
        user = User.objects.get(username='superadmin')
    except User.DoesNotExist:
        print("❌ المستخدم superadmin غير موجود!")
        return
    
    # التحقق من وجود موظف
    if hasattr(user, 'employee_profile'):
        print("✅ المستخدم لديه ملف موظف بالفعل!")
        print(f"   رقم الموظف: {user.employee_profile.employee_id}")
        print(f"   الاسم: {user.employee_profile.arabic_name}")
        return
    
    # الحصول على أو إنشاء قسم
    department, created = Department.objects.get_or_create(
        name='الإدارة',
        defaults={
            'description': 'القسم الإداري',
            'is_active': True
        }
    )
    if created:
        print(f"✅ تم إنشاء قسم: {department.name}")
    
    # الحصول على أو إنشاء منصب
    position, created = JobPosition.objects.get_or_create(
        title='مدير عام',
        defaults={
            'description': 'المدير العام للشركة',
            'department': department,
            'min_salary': 10000.00,
            'max_salary': 50000.00,
            'is_active': True
        }
    )
    if created:
        print(f"✅ تم إنشاء منصب: {position.title}")
    
    # إنشاء أو الحصول على موظف
    employee, emp_created = Employee.objects.get_or_create(
        user=user,
        defaults={
            'employee_id': 'EMP001',
            'first_name': 'Super',
            'last_name': 'Admin',
            'arabic_name': 'المدير العام',
            'national_id': '1234567890',
            'gender': 'M',
            'birth_date': date(1990, 1, 1),
            'marital_status': 'single',
            'phone': '0500000000',
            'email': user.email or 'admin@tonyerp.com',
            'address': 'العنوان الافتراضي',
            'emergency_contact_name': 'جهة اتصال الطوارئ',
            'emergency_contact_phone': '0500000001',
            'department': department,
            'position': position,
            'hire_date': date.today(),
            'status': 'active',
            'basic_salary': 10000.00,
            'housing_allowance': 2000.00,
            'transportation_allowance': 1000.00
        }
    )
    
    if emp_created:
        print("✅ تم إنشاء ملف موظف بنجاح!")
    else:
        print("✅ ملف الموظف موجود بالفعل!")
    print(f"   رقم الموظف: {employee.employee_id}")
    print(f"   الاسم: {employee.arabic_name}")
    print(f"   القسم: {employee.department.name}")
    print(f"   المنصب: {employee.position.title}")
    print("\n🎉 يمكنك الآن الوصول لبوابة الموظف!")

if __name__ == '__main__':
    create_employee_for_admin()
