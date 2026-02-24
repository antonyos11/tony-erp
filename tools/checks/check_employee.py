#!/usr/bin/env python
"""فحص حالة الموظفين في قاعدة البيانات"""

from hr.models import Employee
from django.contrib.auth import get_user_model

User = get_user_model()

# فحص الموظفين الموجودين
employees = Employee.objects.all()
print(f"\n{'='*60}")
print(f"عدد الموظفين في قاعدة البيانات: {employees.count()}")
print(f"{'='*60}\n")

for emp in employees:
    print(f"رقم الموظف: {emp.employee_id}")
    print(f"  الاسم: {emp.full_name}")
    print(f"  User ID: {emp.user_id if emp.user else 'بدون user'}")
    print(f"  القسم: {emp.department}")
    print(f"  المنصب: {emp.position}")
    print("-" * 40)

# فحص المستخدم superadmin
print(f"\n{'='*60}")
print("فحص المستخدم superadmin:")
print(f"{'='*60}\n")

try:
    user = User.objects.get(username='superadmin')
    print(f"✅ المستخدم superadmin موجود (ID: {user.id})")
    print(f"   Email: {user.email}")
    print(f"   First name: {user.first_name}")
    print(f"   Last name: {user.last_name}")
    
    try:
        emp = user.employee_profile
        print(f"\n✅ لديه ملف موظف:")
        print(f"   رقم الموظف: {emp.employee_id}")
        print(f"   الاسم: {emp.full_name}")
    except Employee.DoesNotExist:
        print("\n❌ ليس لديه ملف موظف (employee_profile)")
        print("   يحتاج إلى ربط ملف موظف موجود أو إنشاء ملف جديد")
except User.DoesNotExist:
    print("❌ لا يوجد مستخدم superadmin")
