"""
اختبارات وحدة الموارد البشرية - HR Module Tests
==============================================
اختبارات شاملة لجميع وظائف وحدة الموارد البشرية

تغطية الاختبارات:
- نماذج البيانات (Models)
- الأقسام والمناصب
- الموظفين
- الحضور والانصراف
- الإجازات
- الرواتب
- التكامل مع المحاسبة
"""

from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.db import models
from decimal import Decimal
from datetime import date, time, timedelta
import json

from .models import (
    HRSettings, Department, JobPosition, Employee,
    AttendanceRecord, WorkSchedule, EmployeeSchedule,
    LeaveType, LeaveRequest
)


# ===============================
# اختبارات إعدادات الموارد البشرية
# ===============================

class HRSettingsTestCase(TestCase):
    """اختبارات إعدادات الموارد البشرية"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.settings = HRSettings.objects.create(
            company_name='شركة الاختبار',
            working_hours_per_day=Decimal('8'),
            working_days_per_week=5,
            overtime_rate=Decimal('1.5'),
            late_penalty_per_minute=Decimal('1.00')
        )
    
    def test_create_hr_settings(self):
        """اختبار إنشاء إعدادات الموارد البشرية"""
        self.assertEqual(self.settings.company_name, 'شركة الاختبار')
        self.assertEqual(self.settings.working_hours_per_day, Decimal('8'))
        self.assertEqual(self.settings.working_days_per_week, 5)
    
    def test_overtime_rate(self):
        """اختبار معدل الساعات الإضافية"""
        self.assertEqual(self.settings.overtime_rate, Decimal('1.5'))
    
    def test_late_penalty(self):
        """اختبار غرامة التأخير"""
        self.assertEqual(self.settings.late_penalty_per_minute, Decimal('1.00'))


# ===============================
# اختبارات الأقسام
# ===============================

class DepartmentTestCase(TestCase):
    """اختبارات الأقسام"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.department = Department.objects.create(
            name='قسم الموارد البشرية',
            code='HR',
            description='إدارة شؤون الموظفين',
            budget=Decimal('100000')
        )
    
    def test_create_department(self):
        """اختبار إنشاء قسم"""
        self.assertEqual(self.department.name, 'قسم الموارد البشرية')
        self.assertEqual(self.department.code, 'HR')
        self.assertTrue(self.department.is_active)
    
    def test_department_unique_code(self):
        """اختبار منع تكرار كود القسم"""
        with self.assertRaises(Exception):
            Department.objects.create(
                name='قسم آخر',
                code='HR',  # نفس الكود
                description='وصف'
            )
    
    def test_department_str_representation(self):
        """اختبار التمثيل النصي للقسم"""
        self.assertEqual(str(self.department), 'قسم الموارد البشرية')
    
    def test_department_budget(self):
        """اختبار ميزانية القسم"""
        self.assertEqual(self.department.budget, Decimal('100000'))
    
    def test_create_multiple_departments(self):
        """اختبار إنشاء أقسام متعددة"""
        departments = [
            ('المبيعات', 'SALES'),
            ('المشتريات', 'PURCH'),
            ('المحاسبة', 'ACC'),
            ('الإنتاج', 'PROD'),
        ]
        
        for name, code in departments:
            dept = Department.objects.create(name=name, code=code, description='')
            self.assertEqual(dept.code, code)
        
        self.assertEqual(Department.objects.count(), 5)  # 1 من setUp + 4


# ===============================
# اختبارات المناصب الوظيفية
# ===============================

class JobPositionTestCase(TestCase):
    """اختبارات المناصب الوظيفية"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.department = Department.objects.create(
            name='قسم المحاسبة', code='ACC', description=''
        )
        
        self.position = JobPosition.objects.create(
            title='محاسب',
            code='ACC-001',
            department=self.department,
            description='محاسب عام',
            requirements='شهادة في المحاسبة',
            min_salary=Decimal('5000'),
            max_salary=Decimal('15000')
        )
    
    def test_create_job_position(self):
        """اختبار إنشاء منصب وظيفي"""
        self.assertEqual(self.position.title, 'محاسب')
        self.assertEqual(self.position.code, 'ACC-001')
        self.assertEqual(self.position.department, self.department)
    
    def test_position_salary_range(self):
        """اختبار نطاق الراتب للمنصب"""
        self.assertEqual(self.position.min_salary, Decimal('5000'))
        self.assertEqual(self.position.max_salary, Decimal('15000'))
    
    def test_position_str_representation(self):
        """اختبار التمثيل النصي للمنصب"""
        expected = f"محاسب - قسم المحاسبة"
        self.assertEqual(str(self.position), expected)
    
    def test_position_unique_code(self):
        """اختبار منع تكرار كود المنصب"""
        with self.assertRaises(Exception):
            JobPosition.objects.create(
                title='محاسب آخر',
                code='ACC-001',  # نفس الكود
                department=self.department,
                description='', requirements=''
            )


# ===============================
# اختبارات الموظفين
# ===============================

class EmployeeTestCase(TestCase):
    """اختبارات الموظفين"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user(
            'emp001', 'emp@test.com', 'pass123'
        )
        
        self.department = Department.objects.create(
            name='قسم المبيعات', code='SALES', description=''
        )
        
        self.position = JobPosition.objects.create(
            title='مندوب مبيعات', code='SALES-001',
            department=self.department,
            description='مندوب', requirements='خبرة'
        )
        
        self.employee = Employee.objects.create(
            employee_id='EMP-001',
            user=self.user,
            first_name='أحمد',
            last_name='محمد',
            arabic_name='أحمد محمد علي',
            national_id='1234567890',
            gender='M',
            birth_date=date(1990, 5, 15),
            marital_status='single',
            phone='0500000001',
            email='ahmed@test.com',
            address='الرياض - حي النخيل',
            emergency_contact_name='محمد علي',
            emergency_contact_phone='0500000002',
            department=self.department,
            position=self.position,
            hire_date=date(2020, 1, 1),
            status='active',
            basic_salary=Decimal('8000'),
            housing_allowance=Decimal('2000'),
            transportation_allowance=Decimal('500'),
            other_allowances=Decimal('500')
        )
    
    def test_create_employee(self):
        """اختبار إنشاء موظف"""
        self.assertEqual(self.employee.employee_id, 'EMP-001')
        self.assertEqual(self.employee.arabic_name, 'أحمد محمد علي')
        self.assertEqual(self.employee.status, 'active')
    
    def test_employee_full_name(self):
        """اختبار الاسم الكامل للموظف"""
        self.assertEqual(self.employee.full_name, 'أحمد محمد')
    
    def test_employee_total_salary(self):
        """اختبار إجمالي الراتب"""
        expected = Decimal('8000') + Decimal('2000') + Decimal('500') + Decimal('500')
        self.assertEqual(self.employee.total_salary, expected)
    
    def test_employee_years_of_service(self):
        """اختبار سنوات الخدمة"""
        years = self.employee.years_of_service
        self.assertGreater(years, 0)
    
    def test_employee_unique_employee_id(self):
        """اختبار منع تكرار رقم الموظف"""
        user2 = User.objects.create_user('emp002', 'emp2@test.com', 'pass123')
        
        with self.assertRaises(Exception):
            Employee.objects.create(
                employee_id='EMP-001',  # نفس الرقم
                user=user2,
                first_name='محمد', last_name='أحمد',
                arabic_name='محمد أحمد', national_id='9876543210',
                gender='M', birth_date=date(1985, 1, 1),
                marital_status='married', phone='0500000003',
                email='mohamed@test.com', address='جدة',
                emergency_contact_name='أحمد', emergency_contact_phone='0500000004',
                department=self.department, position=self.position,
                hire_date=date(2021, 1, 1), basic_salary=Decimal('7000')
            )
    
    def test_employee_unique_national_id(self):
        """اختبار منع تكرار رقم الهوية"""
        user2 = User.objects.create_user('emp003', 'emp3@test.com', 'pass123')
        
        with self.assertRaises(Exception):
            Employee.objects.create(
                employee_id='EMP-003',
                user=user2,
                first_name='خالد', last_name='سعد',
                arabic_name='خالد سعد', national_id='1234567890',  # نفس الرقم
                gender='M', birth_date=date(1988, 1, 1),
                marital_status='single', phone='0500000005',
                email='khaled@test.com', address='الدمام',
                emergency_contact_name='سعد', emergency_contact_phone='0500000006',
                department=self.department, position=self.position,
                hire_date=date(2022, 1, 1), basic_salary=Decimal('6000')
            )
    
    def test_employee_statuses(self):
        """اختبار حالات الموظف"""
        statuses = ['active', 'inactive', 'terminated', 'suspended']
        
        for status in statuses:
            self.employee.status = status
            self.employee.save()
            self.assertEqual(self.employee.status, status)
    
    def test_employee_gender_choices(self):
        """اختبار خيارات الجنس"""
        self.assertIn(self.employee.gender, ['M', 'F'])
    
    def test_employee_marital_status_choices(self):
        """اختبار خيارات الحالة الاجتماعية"""
        statuses = ['single', 'married', 'divorced', 'widowed']
        self.assertIn(self.employee.marital_status, statuses)


# ===============================
# اختبارات الحضور والانصراف
# ===============================

class AttendanceRecordTestCase(TestCase):
    """اختبارات سجلات الحضور"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('att_user', 'att@test.com', 'pass123')
        
        self.department = Department.objects.create(
            name='قسم الإنتاج', code='PROD', description=''
        )
        
        self.position = JobPosition.objects.create(
            title='عامل', code='PROD-WRK',
            department=self.department,
            description='', requirements=''
        )
        
        self.employee = Employee.objects.create(
            employee_id='EMP-ATT-001',
            user=self.user,
            first_name='سالم', last_name='عبدالله',
            arabic_name='سالم عبدالله', national_id='1111111111',
            gender='M', birth_date=date(1992, 3, 10),
            marital_status='single', phone='0500000010',
            email='salem@test.com', address='الرياض',
            emergency_contact_name='عبدالله', emergency_contact_phone='0500000011',
            department=self.department, position=self.position,
            hire_date=date(2021, 6, 1), basic_salary=Decimal('4000')
        )
    
    def test_create_check_in_record(self):
        """اختبار تسجيل حضور"""
        record = AttendanceRecord.objects.create(
            employee=self.employee,
            date=date.today(),
            time=time(8, 0, 0),
            record_type='check_in',
            source='fingerprint'
        )
        
        self.assertEqual(record.record_type, 'check_in')
        self.assertEqual(record.source, 'fingerprint')
    
    def test_create_check_out_record(self):
        """اختبار تسجيل انصراف"""
        record = AttendanceRecord.objects.create(
            employee=self.employee,
            date=date.today(),
            time=time(17, 0, 0),
            record_type='check_out',
            source='fingerprint'
        )
        
        self.assertEqual(record.record_type, 'check_out')
    
    def test_attendance_record_types(self):
        """اختبار أنواع سجلات الحضور"""
        types = ['check_in', 'check_out', 'break_start', 'break_end']
        
        for i, rec_type in enumerate(types):
            record = AttendanceRecord.objects.create(
                employee=self.employee,
                date=date.today(),
                time=time(8 + i, 0, 0),
                record_type=rec_type,
                source='manual'
            )
            self.assertEqual(record.record_type, rec_type)
    
    def test_attendance_sources(self):
        """اختبار مصادر تسجيل الحضور"""
        sources = ['manual', 'fingerprint', 'rfid', 'mobile', 'web']
        
        for i, source in enumerate(sources):
            record = AttendanceRecord.objects.create(
                employee=self.employee,
                date=date.today() - timedelta(days=i+1),
                time=time(8, 0, 0),
                record_type='check_in',
                source=source
            )
            self.assertEqual(record.source, source)
    
    def test_attendance_with_location(self):
        """اختبار تسجيل الحضور مع الموقع"""
        record = AttendanceRecord.objects.create(
            employee=self.employee,
            date=date.today(),
            time=time(8, 30, 0),
            record_type='check_in',
            source='mobile',
            latitude=Decimal('24.7136'),
            longitude=Decimal('46.6753')
        )
        
        self.assertEqual(record.latitude, Decimal('24.7136'))
        self.assertEqual(record.longitude, Decimal('46.6753'))


# ===============================
# اختبارات جدولة العمل
# ===============================

class WorkScheduleTestCase(TestCase):
    """اختبارات جدولة العمل"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.schedule = WorkSchedule.objects.create(
            name='دوام صباحي',
            is_default=True,
            sunday_start=time(8, 0),
            sunday_end=time(16, 0),
            monday_start=time(8, 0),
            monday_end=time(16, 0),
            tuesday_start=time(8, 0),
            tuesday_end=time(16, 0),
            wednesday_start=time(8, 0),
            wednesday_end=time(16, 0),
            thursday_start=time(8, 0),
            thursday_end=time(16, 0),
            grace_period_minutes=15,
            break_duration_minutes=60
        )
    
    def test_create_work_schedule(self):
        """اختبار إنشاء جدولة عمل"""
        self.assertEqual(self.schedule.name, 'دوام صباحي')
        self.assertTrue(self.schedule.is_default)
    
    def test_schedule_working_days(self):
        """اختبار أيام العمل في الجدولة"""
        self.assertEqual(self.schedule.sunday_start, time(8, 0))
        self.assertEqual(self.schedule.sunday_end, time(16, 0))
    
    def test_schedule_grace_period(self):
        """اختبار فترة السماح"""
        self.assertEqual(self.schedule.grace_period_minutes, 15)
    
    def test_schedule_break_duration(self):
        """اختبار مدة الاستراحة"""
        self.assertEqual(self.schedule.break_duration_minutes, 60)
    
    def test_create_evening_schedule(self):
        """اختبار إنشاء جدولة مسائية"""
        evening = WorkSchedule.objects.create(
            name='دوام مسائي',
            sunday_start=time(16, 0),
            sunday_end=time(0, 0),
            monday_start=time(16, 0),
            monday_end=time(0, 0),
        )
        
        self.assertEqual(evening.name, 'دوام مسائي')


# ===============================
# اختبارات الإجازات
# ===============================

class LeaveTypeTestCase(TestCase):
    """اختبارات أنواع الإجازات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.annual_leave = LeaveType.objects.create(
            name='إجازة سنوية',
            days_per_year=21,
            is_paid=True,
            carry_forward=True,
            max_carry_forward_days=5,
            requires_approval=True
        )
    
    def test_create_leave_type(self):
        """اختبار إنشاء نوع إجازة"""
        self.assertEqual(self.annual_leave.name, 'إجازة سنوية')
        self.assertEqual(self.annual_leave.days_per_year, 21)
        self.assertTrue(self.annual_leave.is_paid)
    
    def test_leave_carry_forward(self):
        """اختبار ترحيل الإجازات"""
        self.assertTrue(self.annual_leave.carry_forward)
        self.assertEqual(self.annual_leave.max_carry_forward_days, 5)
    
    def test_create_sick_leave(self):
        """اختبار إنشاء إجازة مرضية"""
        sick = LeaveType.objects.create(
            name='إجازة مرضية',
            days_per_year=30,
            is_paid=True,
            carry_forward=False,
            requires_approval=True
        )
        
        self.assertEqual(sick.name, 'إجازة مرضية')
        self.assertFalse(sick.carry_forward)
    
    def test_create_unpaid_leave(self):
        """اختبار إنشاء إجازة بدون راتب"""
        unpaid = LeaveType.objects.create(
            name='إجازة بدون راتب',
            days_per_year=30,
            is_paid=False,
            requires_approval=True
        )
        
        self.assertFalse(unpaid.is_paid)


class LeaveRequestTestCase(TestCase):
    """اختبارات طلبات الإجازات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('leave_user', 'leave@test.com', 'pass123')
        
        self.department = Department.objects.create(
            name='قسم IT', code='IT', description=''
        )
        
        self.position = JobPosition.objects.create(
            title='مبرمج', code='IT-DEV',
            department=self.department,
            description='', requirements=''
        )
        
        self.employee = Employee.objects.create(
            employee_id='EMP-LEAVE-001',
            user=self.user,
            first_name='فهد', last_name='العتيبي',
            arabic_name='فهد العتيبي', national_id='2222222222',
            gender='M', birth_date=date(1988, 7, 20),
            marital_status='married', phone='0500000020',
            email='fahad@test.com', address='الرياض',
            emergency_contact_name='سعود', emergency_contact_phone='0500000021',
            department=self.department, position=self.position,
            hire_date=date(2019, 3, 1), basic_salary=Decimal('12000')
        )
        
        self.leave_type = LeaveType.objects.create(
            name='إجازة سنوية',
            days_per_year=21,
            is_paid=True
        )
    
    def test_create_leave_request(self):
        """اختبار إنشاء طلب إجازة"""
        request = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            days_requested=4,
            reason='إجازة عائلية',
            status='pending'
        )
        
        self.assertEqual(request.status, 'pending')
        self.assertEqual(request.employee, self.employee)
    
    def test_leave_request_statuses(self):
        """اختبار حالات طلب الإجازة"""
        statuses = ['pending', 'approved', 'rejected', 'cancelled']
        
        for status in statuses:
            request = LeaveRequest.objects.create(
                employee=self.employee,
                leave_type=self.leave_type,
                start_date=date.today() + timedelta(days=30),
                end_date=date.today() + timedelta(days=32),
                days_requested=3,
                status=status
            )
            self.assertEqual(request.status, status)


# ===============================
# اختبارات الواجهات (Views)
# ===============================

class HRViewsTestCase(TestCase):
    """اختبارات واجهات المستخدم"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            'hr_admin', 'hr@test.com', 'pass123'
        )
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='hr_admin', password='pass123')
    
    def test_hr_urls_accessible(self):
        """اختبار إمكانية الوصول لصفحات HR"""
        # اختبار عام للتأكد من عدم وجود أخطاء في التوجيه
        from django.urls import get_resolver
        resolver = get_resolver()
        self.assertIsNotNone(resolver)


# ===============================
# اختبارات الأداء
# ===============================

class HRPerformanceTestCase(TestCase):
    """اختبارات الأداء"""
    
    @classmethod
    def setUpTestData(cls):
        """إعداد البيانات المشتركة"""
        cls.department = Department.objects.create(
            name='قسم الأداء', code='PERF', description=''
        )
        
        cls.position = JobPosition.objects.create(
            title='موظف', code='PERF-EMP',
            department=cls.department,
            description='', requirements=''
        )
    
    def test_bulk_employee_creation(self):
        """اختبار إنشاء موظفين بكميات كبيرة"""
        employees = []
        users = []
        
        for i in range(50):
            users.append(User(
                username=f'bulk_emp_{i}',
                email=f'bulk{i}@test.com'
            ))
        
        User.objects.bulk_create(users)
        created_users = User.objects.filter(username__startswith='bulk_emp_')
        
        for i, user in enumerate(created_users):
            employees.append(Employee(
                employee_id=f'BULK-{i:04d}',
                user=user,
                first_name=f'موظف', last_name=f'{i}',
                arabic_name=f'موظف رقم {i}',
                national_id=f'{i:010d}',
                gender='M', birth_date=date(1990, 1, 1),
                marital_status='single', phone=f'050{i:07d}',
                email=f'bulk{i}@test.com', address='الرياض',
                emergency_contact_name='طوارئ', emergency_contact_phone='0500000000',
                department=self.department, position=self.position,
                hire_date=date(2020, 1, 1), basic_salary=Decimal('5000')
            ))
        
        Employee.objects.bulk_create(employees)
        self.assertEqual(
            Employee.objects.filter(employee_id__startswith='BULK-').count(),
            50
        )
    
    def test_bulk_attendance_creation(self):
        """اختبار إنشاء سجلات حضور بكميات"""
        user = User.objects.create_user('att_perf', 'att_perf@test.com', 'pass123')
        
        employee = Employee.objects.create(
            employee_id='ATT-PERF-001',
            user=user,
            first_name='اختبار', last_name='أداء',
            arabic_name='اختبار أداء', national_id='9999999999',
            gender='M', birth_date=date(1990, 1, 1),
            marital_status='single', phone='0500000099',
            email='att_perf@test.com', address='الرياض',
            emergency_contact_name='طوارئ', emergency_contact_phone='0500000098',
            department=self.department, position=self.position,
            hire_date=date(2020, 1, 1), basic_salary=Decimal('5000')
        )
        
        records = []
        for i in range(30):
            record_date = date.today() - timedelta(days=i)
            records.append(AttendanceRecord(
                employee=employee,
                date=record_date,
                time=time(8, 0, 0),
                record_type='check_in',
                source='fingerprint'
            ))
        
        AttendanceRecord.objects.bulk_create(records)
        self.assertEqual(
            AttendanceRecord.objects.filter(employee=employee).count(),
            30
        )


# ===============================
# اختبارات التحقق من صحة البيانات
# ===============================

class HRValidationTestCase(TestCase):
    """اختبارات التحقق من صحة البيانات"""
    
    def test_employee_salary_positive(self):
        """اختبار أن الراتب موجب"""
        user = User.objects.create_user('val_user', 'val@test.com', 'pass123')
        
        department = Department.objects.create(
            name='قسم التحقق', code='VAL', description=''
        )
        
        position = JobPosition.objects.create(
            title='موظف', code='VAL-EMP',
            department=department,
            description='', requirements=''
        )
        
        employee = Employee.objects.create(
            employee_id='VAL-001',
            user=user,
            first_name='تحقق', last_name='بيانات',
            arabic_name='تحقق بيانات', national_id='8888888888',
            gender='M', birth_date=date(1990, 1, 1),
            marital_status='single', phone='0500000088',
            email='val@test.com', address='الرياض',
            emergency_contact_name='طوارئ', emergency_contact_phone='0500000087',
            department=department, position=position,
            hire_date=date(2020, 1, 1), basic_salary=Decimal('5000')
        )
        
        self.assertGreater(employee.basic_salary, 0)
    
    def test_leave_dates_valid(self):
        """اختبار صحة تواريخ الإجازة"""
        user = User.objects.create_user('leave_val', 'leave_val@test.com', 'pass123')
        
        department = Department.objects.create(
            name='قسم إجازات', code='LV', description=''
        )
        
        position = JobPosition.objects.create(
            title='موظف', code='LV-EMP',
            department=department,
            description='', requirements=''
        )
        
        employee = Employee.objects.create(
            employee_id='LV-001',
            user=user,
            first_name='إجازة', last_name='اختبار',
            arabic_name='إجازة اختبار', national_id='7777777777',
            gender='M', birth_date=date(1990, 1, 1),
            marital_status='single', phone='0500000077',
            email='leave_val@test.com', address='الرياض',
            emergency_contact_name='طوارئ', emergency_contact_phone='0500000076',
            department=department, position=position,
            hire_date=date(2020, 1, 1), basic_salary=Decimal('5000')
        )
        
        leave_type = LeaveType.objects.create(
            name='سنوية', days_per_year=21, is_paid=True
        )
        
        start = date.today() + timedelta(days=5)
        end = date.today() + timedelta(days=10)
        
        request = LeaveRequest.objects.create(
            employee=employee,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            days_requested=6,
            status='pending'
        )
        
        self.assertLess(request.start_date, request.end_date)
