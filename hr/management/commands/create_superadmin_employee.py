"""
Django management command to create employee profile for superadmin user
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from hr.models import Employee, Department, JobPosition
from datetime import date

User = get_user_model()


class Command(BaseCommand):
    help = 'Create employee profile for superadmin user'

    def handle(self, *args, **options):
        # Get superadmin user
        try:
            user = User.objects.get(username='superadmin')
            self.stdout.write(f'Found user: {user.username} (ID: {user.id})')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Superadmin user not found'))
            return

        # Check if employee profile already exists
        try:
            emp = user.employee_profile
            self.stdout.write(self.style.SUCCESS(f'Employee profile already exists: {emp.employee_id}'))
            return
        except Employee.DoesNotExist:
            pass

        # Create or get department
        department, created = Department.objects.get_or_create(
            name='الإدارة',
            defaults={
                'description': 'الإدارة العليا',
                'is_active': True
            }
        )
        self.stdout.write(f'Department: {department.name}')

        # Create or get job position
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
        self.stdout.write(f'Position: {position.title}')

        # Create employee
        try:
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

            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(self.style.SUCCESS('Employee profile created successfully!'))
            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(f'Employee ID: {employee.employee_id}')
            self.stdout.write(f'Name: {employee.full_name}')
            self.stdout.write(f'Department: {employee.department.name}')
            self.stdout.write(f'Position: {employee.position.title}')
            self.stdout.write(f'Basic Salary: {employee.basic_salary}')
            self.stdout.write(self.style.SUCCESS('\nYou can now access the employee portal!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating employee: {e}'))
            raise
