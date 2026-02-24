from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from hr.models import (
    Department, JobPosition, LeaveType, WorkSchedule, HRSettings
)
from accounting.models import Account, AccountType, CostCenter
from decimal import Decimal


class Command(BaseCommand):
    help = 'إعداد البيانات الأساسية لنظام الموارد البشرية'

    def handle(self, *args, **options):
        self.stdout.write('بدء إعداد البيانات الأساسية للموارد البشرية...')
        
        # إنشاء الأقسام
        self.create_departments()
        
        # إنشاء أنواع الإجازات
        self.create_leave_types()
        
        # إنشاء جدولة العمل الافتراضية
        self.create_work_schedules()
        
        # إنشاء الحسابات المحاسبية للموارد البشرية
        self.create_hr_accounts()
        
        # إعداد إعدادات الموارد البشرية
        self.create_hr_settings()
        
        self.stdout.write(
            self.style.SUCCESS('تم إعداد البيانات الأساسية للموارد البشرية بنجاح!')
        )

    def create_departments(self):
        """إنشاء الأقسام الأساسية"""
        departments_data = [
            {'name': 'الموارد البشرية', 'code': 'HR'},
            {'name': 'المحاسبة والمالية', 'code': 'ACC'},
            {'name': 'المبيعات والتسويق', 'code': 'SALES'},
            {'name': 'تقنية المعلومات', 'code': 'IT'},
            {'name': 'العمليات', 'code': 'OPS'},
            {'name': 'الإدارة العامة', 'code': 'ADMIN'},
        ]
        
        for dept_data in departments_data:
            # إنشاء مركز التكلفة
            cost_center, created = CostCenter.objects.get_or_create(
                code=dept_data['code'],
                defaults={
                    'name': f"مركز تكلفة {dept_data['name']}",
                    'description': f"مركز التكلفة الخاص بقسم {dept_data['name']}"
                }
            )
            
            # إنشاء القسم
            department, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults={
                    'name': dept_data['name'],
                    'description': f"قسم {dept_data['name']}",
                    'budget': Decimal('100000.00'),
                    'cost_center': cost_center
                }
            )
            
            if created:
                self.stdout.write(f'تم إنشاء قسم: {department.name}')

    def create_leave_types(self):
        """إنشاء أنواع الإجازات"""
        leave_types_data = [
            {
                'name': 'إجازة سنوية',
                'days_per_year': 21,
                'is_paid': True,
                'carry_forward': True,
                'max_carry_forward_days': 7,
                'requires_approval': True
            },
            {
                'name': 'إجازة مرضية',
                'days_per_year': 30,
                'is_paid': True,
                'carry_forward': False,
                'max_carry_forward_days': 0,
                'requires_approval': True
            },
            {
                'name': 'إجازة طوارئ',
                'days_per_year': 5,
                'is_paid': True,
                'carry_forward': False,
                'max_carry_forward_days': 0,
                'requires_approval': True
            },
            {
                'name': 'إجازة أمومة',
                'days_per_year': 70,
                'is_paid': True,
                'carry_forward': False,
                'max_carry_forward_days': 0,
                'requires_approval': True
            },
            {
                'name': 'إجازة أبوة',
                'days_per_year': 3,
                'is_paid': True,
                'carry_forward': False,
                'max_carry_forward_days': 0,
                'requires_approval': True
            },
            {
                'name': 'إجازة بدون راتب',
                'days_per_year': 30,
                'is_paid': False,
                'carry_forward': False,
                'max_carry_forward_days': 0,
                'requires_approval': True
            },
        ]
        
        for leave_data in leave_types_data:
            leave_type, created = LeaveType.objects.get_or_create(
                name=leave_data['name'],
                defaults=leave_data
            )
            
            if created:
                self.stdout.write(f'تم إنشاء نوع إجازة: {leave_type.name}')

    def create_work_schedules(self):
        """إنشاء جدولة العمل"""
        from datetime import time
        
        # جدولة العمل الأساسية (الأحد إلى الخميس)
        schedule, created = WorkSchedule.objects.get_or_create(
            name='الدوام الرسمي',
            defaults={
                'is_default': True,
                'sunday_start': time(8, 0),
                'sunday_end': time(17, 0),
                'monday_start': time(8, 0),
                'monday_end': time(17, 0),
                'tuesday_start': time(8, 0),
                'tuesday_end': time(17, 0),
                'wednesday_start': time(8, 0),
                'wednesday_end': time(17, 0),
                'thursday_start': time(8, 0),
                'thursday_end': time(17, 0),
                'grace_period_minutes': 15,
                'break_duration_minutes': 60,
            }
        )
        
        if created:
            self.stdout.write(f'تم إنشاء جدولة العمل: {schedule.name}')

    def create_hr_accounts(self):
        """إنشاء الحسابات المحاسبية للموارد البشرية"""
        hr_accounts = [
            {
                'code': '5100',
                'name': 'مصاريف الرواتب والأجور',
                'account_type': AccountType.EXPENSE,
                'description': 'حساب مصاريف رواتب وأجور الموظفين'
            },
            {
                'code': '2100',
                'name': 'رواتب وأجور مستحقة الدفع',
                'account_type': AccountType.LIABILITY,
                'description': 'حساب الرواتب والأجور المستحقة للموظفين'
            },
            {
                'code': '5110',
                'name': 'مصاريف الساعات الإضافية',
                'account_type': AccountType.EXPENSE,
                'description': 'حساب مصاريف الساعات الإضافية'
            },
            {
                'code': '5120',
                'name': 'مصاريف المكافآت والحوافز',
                'account_type': AccountType.EXPENSE,
                'description': 'حساب مصاريف المكافآت والحوافز'
            },
            {
                'code': '5130',
                'name': 'مصاريف التأمين الطبي',
                'account_type': AccountType.EXPENSE,
                'description': 'حساب مصاريف التأمين الطبي للموظفين'
            },
            {
                'code': '5140',
                'name': 'مصاريف التدريب والتطوير',
                'account_type': AccountType.EXPENSE,
                'description': 'حساب مصاريف تدريب وتطوير الموظفين'
            },
        ]
        
        for account_data in hr_accounts:
            account, created = Account.objects.get_or_create(
                code=account_data['code'],
                defaults=account_data
            )
            
            if created:
                self.stdout.write(f'تم إنشاء حساب: {account.code} - {account.name}')

    def create_hr_settings(self):
        """إعداد إعدادات الموارد البشرية"""
        # الحصول على الحسابات
        try:
            salary_expense_account = Account.objects.get(code='5100')
            salary_payable_account = Account.objects.get(code='2100')
            overtime_expense_account = Account.objects.get(code='5110')
            bonus_expense_account = Account.objects.get(code='5120')
            
            hr_settings, created = HRSettings.objects.get_or_create(
                defaults={
                    'company_name': 'الشركة الشاملة للمحاسبة',
                    'working_hours_per_day': Decimal('8.00'),
                    'working_days_per_week': 5,
                    'overtime_rate': Decimal('1.50'),
                    'late_penalty_per_minute': Decimal('0.50'),
                    'salary_expense_account': salary_expense_account,
                    'salary_payable_account': salary_payable_account,
                    'overtime_expense_account': overtime_expense_account,
                    'bonus_expense_account': bonus_expense_account,
                }
            )
            
            if created:
                self.stdout.write('تم إنشاء إعدادات الموارد البشرية')
                
        except Account.DoesNotExist as e:
            self.stdout.write(
                self.style.WARNING(f'تعذر ربط بعض الحسابات المحاسبية: {e}')
            )

    def create_job_positions(self):
        """إنشاء المناصب الوظيفية الأساسية"""
        positions_data = [
            # قسم الموارد البشرية
            {
                'title': 'مدير الموارد البشرية',
                'code': 'HR-MGR',
                'department_code': 'HR',
                'min_salary': 15000,
                'max_salary': 25000,
                'description': 'إدارة جميع شؤون الموارد البشرية',
                'requirements': 'شهادة جامعية في الموارد البشرية أو إدارة الأعمال، خبرة 5 سنوات على الأقل'
            },
            {
                'title': 'أخصائي موارد بشرية',
                'code': 'HR-SPEC',
                'department_code': 'HR',
                'min_salary': 8000,
                'max_salary': 12000,
                'description': 'تنفيذ سياسات الموارد البشرية',
                'requirements': 'شهادة جامعية، خبرة سنتين على الأقل'
            },
            # قسم المحاسبة
            {
                'title': 'مدير المحاسبة',
                'code': 'ACC-MGR',
                'department_code': 'ACC',
                'min_salary': 12000,
                'max_salary': 20000,
                'description': 'إدارة العمليات المحاسبية والمالية',
                'requirements': 'شهادة محاسبة، زمالة مهنية مفضلة، خبرة 7 سنوات'
            },
            {
                'title': 'محاسب',
                'code': 'ACC-001',
                'department_code': 'ACC',
                'min_salary': 6000,
                'max_salary': 10000,
                'description': 'القيام بالأعمال المحاسبية اليومية',
                'requirements': 'شهادة محاسبة، خبرة 3 سنوات'
            },
            # المبيعات
            {
                'title': 'مدير المبيعات',
                'code': 'SALES-MGR',
                'department_code': 'SALES',
                'min_salary': 10000,
                'max_salary': 18000,
                'description': 'إدارة فريق المبيعات وتحقيق الأهداف',
                'requirements': 'شهادة جامعية، خبرة 5 سنوات في المبيعات'
            },
            {
                'title': 'مندوب مبيعات',
                'code': 'SALES-REP',
                'department_code': 'SALES',
                'min_salary': 4000,
                'max_salary': 8000,
                'description': 'البيع المباشر للعملاء',
                'requirements': 'شهادة ثانوية على الأقل، مهارات تواصل ممتازة'
            },
        ]
        
        for pos_data in positions_data:
            try:
                department = Department.objects.get(code=pos_data['department_code'])
                position, created = JobPosition.objects.get_or_create(
                    code=pos_data['code'],
                    defaults={
                        'title': pos_data['title'],
                        'department': department,
                        'description': pos_data['description'],
                        'requirements': pos_data['requirements'],
                        'min_salary': Decimal(str(pos_data['min_salary'])),
                        'max_salary': Decimal(str(pos_data['max_salary'])),
                        'is_active': True,
                    }
                )
                
                if created:
                    self.stdout.write(f'تم إنشاء منصب: {position.title}')
                    
            except Department.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'تعذر العثور على القسم: {pos_data["department_code"]}')
                )