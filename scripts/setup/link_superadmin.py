#!/usr/bin/env python
"""ربط المستخدم superadmin بملف موظف"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from hr.models import Employee, Department, JobPosition
from django.contrib.auth import get_user_model
from datetime import date

User = get_user_model()

def link_superadmin_to_employee():
    """ربط superadmin بملف موظف جديد"""
    
    # الحصول على المستخدم superadmin
    try:
        user = User.objects.get(username='superadmin')
        print(f"✅ تم العثور على المستخدم: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print("❌ لا يوجد مستخدم superadmin")
        return
    
    # التحقق من وجود ملف موظف
    try:
        emp = user.employee_profile
        print(f"✅ المستخدم لديه ملف موظف بالفعل: {emp.employee_id}")
        return
    except Employee.DoesNotExist:
        pass
    
    # إنشاء أو الحصول على القسم
    department, created = Department.objects.get_or_create(
        name='الإدارة',
        defaults={
            'description': 'الإدارة العليا',
            'is_active': True
        }
    )
    if created:
        print(f"✅ تم إنشاء قسم: {department.name}")
    else:
        print(f"✅ القسم موجود: {department.name}")
    
    # إنشاء أو الحصول على المنصب
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
    else:
        print(f"✅ المنصب موجود: {position.title}")
    
    # إنشاء موظف جديد برقم مختلف
    print("جاري إنشاء ملف الموظف...")
    
    # البحث عن رقم موظف غير مستخدم
    employee_id = 'EMP000'  # رقم خاص بالـ superadmin
    
    try:
        employee = Employee.objects.create(
            employee_id=employee_id,
            user=user,
            first_name=user.first_name or 'Super',
            last_name=user.last_name or 'Admin',
            arabic_name='المدير العام',
            national_id='1234567890',
            gender='M',
            birth_date=date(1990, 1, 1),
            marital_status='single',
            phone='0500000000',
            email=user.email or 'admin@tonyerp.com',
            address='العنوان الافتراضي',
            emergency_contact_name='جهة اتصال الطوارئ',
            emergency_contact_phone='0500000001',
            department=department,
            position=position,
            hire_date=date.today(),
            status='active',
            basic_salary=20000.00,
            housing_allowance=2000.00,
            transportation_allowance=1000.00
        )
        
        print("\n" + "="*60)
        print("✅ تم إنشاء ملف الموظف بنجاح!")
        print("="*60)
        print(f"رقم الموظف: {employee.employee_id}")
        print(f"الاسم: {employee.full_name}")
        print(f"القسم: {employee.department.name}")
        print(f"المنصب: {employee.position.title}")
        print(f"الراتب الأساسي: {employee.basic_salary}")
        print("\n🎉 يمكنك الآن الدخول إلى بوابة الموظف!")
        
    except Exception as e:
        print(f"❌ خطأ أثناء إنشاء الموظف: {e}")
        raise

if __name__ == '__main__':
    link_superadmin_to_employee()
