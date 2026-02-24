from hr.models import Employee, Department, JobPosition
from django.contrib.auth import get_user_model
from datetime import date

User = get_user_model()

# الحصول على المستخدم superadmin
user = User.objects.get(username='superadmin')
print(f"✅ المستخدم: {user.username} (ID: {user.id})")

# التحقق من وجود ملف موظف
try:
    emp = user.employee_profile
    print(f"✅ لديه ملف موظف: {emp.employee_id}")
except:
    # إنشاء القسم والمنصب
    department, _ = Department.objects.get_or_create(
        name='الإدارة',
        defaults={'description': 'الإدارة العليا', 'is_active': True}
    )
    
    position, _ = JobPosition.objects.get_or_create(
        title='مدير عام',
        defaults={
            'description': 'المدير العام للشركة',
            'department': department,
            'min_salary': 10000.00,
            'max_salary': 50000.00,
            'is_active': True
        }
    )
    
    # إنشاء الموظف
    employee = Employee.objects.create(
        employee_id='EMP000',
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
    
    print(f"\n{'='*60}")
    print("✅ تم إنشاء ملف الموظف بنجاح!")
    print(f"{'='*60}")
    print(f"رقم الموظف: {employee.employee_id}")
    print(f"الاسم: {employee.full_name}")
    print(f"القسم: {employee.department.name}")
    print(f"المنصب: {employee.position.title}")
    print(f"الراتب الأساسي: {employee.basic_salary}")
    print("\n🎉 يمكنك الآن الدخول إلى بوابة الموظف!")
