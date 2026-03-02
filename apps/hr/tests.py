"""
اختبارات الموارد البشرية — RITA ERP
تغطي: الموظفين، الحضور، الإجازات، حساب الرواتب، الجزاءات، السلف، عمل بالقطعة
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import User, Branch
from apps.hr.models import (
    Department, JobTitle, Employee, Attendance,
    LeaveRequest, LeaveBalance, Penalty, SalaryAdvance,
    Payroll, PayrollLine, ProductionPieceWork,
)
from apps.hr.services.payroll_engine import PayrollEngine


# ══════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════

def make_branch(name='فرع رئيسي'):
    return Branch.objects.create(name=name)


def make_user(username='testuser', password='testpass123'):
    return User.objects.create_user(username=username, password=password, first_name='اختبار')


def make_department(branch):
    return Department.objects.create(name='قسم الاختبار', branch=branch)


def make_job_title(department):
    return JobTitle.objects.create(
        name='مسمى اختباري',
        department=department,
        min_salary=Decimal('3000'),
        max_salary=Decimal('8000'),
    )


def make_employee(
    user, branch, department, job_title,
    basic_salary=Decimal('5000'),
    employment_type='full_time',
    employee_number='EMP001',
    national_id='12345678901234',
):
    return Employee.objects.create(
        user=user,
        employee_number=employee_number,
        full_name_ar='موظف اختباري',
        national_id=national_id,
        date_of_birth=date(1990, 1, 1),
        gender='male',
        phone='01000000000',
        address='عنوان اختباري',
        governorate='القاهرة',
        branch=branch,
        department=department,
        job_title=job_title,
        employment_type=employment_type,
        hire_date=date(2020, 1, 1),
        basic_salary=basic_salary,
        housing_allowance=Decimal('500'),
        transport_allowance=Decimal('300'),
        social_insurance_deduction=Decimal('400'),
        tax_deduction=Decimal('100'),
    )


# ══════════════════════════════════════════════════════
# Test: Models
# ══════════════════════════════════════════════════════

class EmployeeModelTest(TestCase):
    def setUp(self):
        self.branch = make_branch()
        self.user = make_user()
        self.dept = make_department(self.branch)
        self.jt = make_job_title(self.dept)
        self.emp = make_employee(self.user, self.branch, self.dept, self.jt)

    def test_employee_str(self):
        self.assertIn('EMP001', str(self.emp))
        self.assertIn('موظف اختباري', str(self.emp))

    def test_gross_salary_calculation(self):
        """إجمالي = أساسي + بدل سكن + نقل"""
        expected = Decimal('5000') + Decimal('500') + Decimal('300')
        self.assertEqual(self.emp.gross_salary, expected)

    def test_net_salary_calculation(self):
        """صافي = إجمالي - تأمين - ضريبة"""
        gross = self.emp.gross_salary
        expected = gross - Decimal('400') - Decimal('100')
        self.assertEqual(self.emp.net_salary, expected)

    def test_employee_is_active_default(self):
        self.assertTrue(self.emp.is_active)

    def test_department_str(self):
        self.assertEqual(str(self.dept), 'قسم الاختبار')

    def test_job_title_str(self):
        self.assertEqual(str(self.jt), 'مسمى اختباري')


# ══════════════════════════════════════════════════════
# Test: Attendance
# ══════════════════════════════════════════════════════

class AttendanceTest(TestCase):
    def setUp(self):
        self.branch = make_branch()
        self.user = make_user()
        self.dept = make_department(self.branch)
        self.jt = make_job_title(self.dept)
        self.emp = make_employee(self.user, self.branch, self.dept, self.jt)

    def test_create_attendance_present(self):
        att = Attendance.objects.create(
            employee=self.emp,
            date=date.today(),
            status='present',
            check_in=timezone.now().time(),
        )
        self.assertEqual(att.status, 'present')

    def test_attendance_unique_per_day(self):
        """لا يمكن تسجيل حضور مرتين لنفس اليوم"""
        Attendance.objects.create(employee=self.emp, date=date.today(), status='present')
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            Attendance.objects.create(employee=self.emp, date=date.today(), status='absent')

    def test_attendance_with_overtime(self):
        att = Attendance.objects.create(
            employee=self.emp,
            date=date.today(),
            status='present',
            overtime_hours=Decimal('2.5'),
        )
        self.assertEqual(att.overtime_hours, Decimal('2.5'))

    def test_late_attendance(self):
        att = Attendance.objects.create(
            employee=self.emp,
            date=date.today(),
            status='late',
            late_minutes=30,
        )
        self.assertEqual(att.late_minutes, 30)


# ══════════════════════════════════════════════════════
# Test: Leave Request
# ══════════════════════════════════════════════════════

class LeaveRequestTest(TestCase):
    def setUp(self):
        self.branch = make_branch()
        self.user = make_user()
        self.approver = make_user('approver')
        self.dept = make_department(self.branch)
        self.jt = make_job_title(self.dept)
        self.emp = make_employee(self.user, self.branch, self.dept, self.jt)

    def test_create_leave_request(self):
        start = date.today()
        end = start + timedelta(days=4)
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            leave_type='annual',
            start_date=start,
            end_date=end,
            days_count=5,
            reason='إجازة سنوية',
            status='pending',
        )
        self.assertEqual(leave.status, 'pending')
        self.assertEqual(leave.days_count, 5)

    def test_approve_leave(self):
        start = date.today()
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            leave_type='sick',
            start_date=start,
            end_date=start + timedelta(days=2),
            days_count=3,
            reason='مرض',
        )
        leave.status = 'approved'
        leave.approved_by = self.approver
        leave.approved_at = timezone.now()
        leave.save()

        leave.refresh_from_db()
        self.assertEqual(leave.status, 'approved')
        self.assertEqual(leave.approved_by, self.approver)

    def test_reject_leave(self):
        leave = LeaveRequest.objects.create(
            employee=self.emp,
            leave_type='annual',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            days_count=3,
            reason='سبب غير مقبول',
        )
        leave.status = 'rejected'
        leave.rejection_reason = 'ضغط عمل'
        leave.save()
        self.assertEqual(leave.status, 'rejected')

    def test_leave_balance(self):
        balance = LeaveBalance.objects.create(
            employee=self.emp,
            year=date.today().year,
            annual_balance=21,
            used_annual=5,
            sick_balance=7,
            used_sick=2,
        )
        self.assertEqual(balance.remaining_annual, 16)
        self.assertEqual(balance.remaining_sick, 5)

    def test_leave_balance_with_carried_over(self):
        balance = LeaveBalance.objects.create(
            employee=self.emp,
            year=date.today().year,
            annual_balance=21,
            used_annual=10,
            carried_over=3,
        )
        self.assertEqual(balance.remaining_annual, 14)


# ══════════════════════════════════════════════════════
# Test: Salary Calculation (PayrollEngine)
# ══════════════════════════════════════════════════════

class PayrollEngineTest(TestCase):
    def setUp(self):
        self.branch = make_branch()
        self.admin_user = make_user('admin', 'adminpass')
        self.admin_user.is_staff = True
        self.admin_user.save()
        self.dept = make_department(self.branch)
        self.jt = make_job_title(self.dept)

        # 5 موظفين
        users = [make_user(f'emp_user_{i}') for i in range(5)]
        self.employees = []
        for i, u in enumerate(users):
            emp = make_employee(
                u, self.branch, self.dept, self.jt,
                basic_salary=Decimal('4000'),
                employee_number=f'EMP{i+10:03d}',
                national_id=f'9900000000{i:04d}',
            )
            self.employees.append(emp)

        # الشهر والسنة
        self.month = 1
        self.year = 2026

        # تسجيل حضور: 20 يوم حاضر + يومين غياب
        from datetime import date as d
        for emp in self.employees:
            for day in range(1, 23):  # 22 يوم
                try:
                    dt = d(self.year, self.month, day)
                    status = 'present' if day <= 20 else 'absent'
                    Attendance.objects.create(
                        employee=emp,
                        date=dt,
                        status=status,
                        overtime_hours=Decimal('1') if day <= 5 else Decimal('0'),
                    )
                except ValueError:
                    pass

    def test_calculate_payroll_creates_lines(self):
        payroll = PayrollEngine.calculate_payroll(
            self.month, self.year, self.branch, user=self.admin_user
        )
        self.assertEqual(payroll.status, 'calculated')
        self.assertEqual(payroll.lines.count(), 5)

    def test_payroll_deducts_absence(self):
        payroll = PayrollEngine.calculate_payroll(
            self.month, self.year, self.branch, user=self.admin_user
        )
        for line in payroll.lines.all():
            self.assertGreater(line.absence_deduction, Decimal('0'))
            self.assertEqual(line.absence_days, 2)

    def test_payroll_adds_overtime(self):
        payroll = PayrollEngine.calculate_payroll(
            self.month, self.year, self.branch, user=self.admin_user
        )
        for line in payroll.lines.all():
            self.assertGreater(line.overtime_amount, Decimal('0'))

    def test_net_salary_equals_gross_minus_deductions_plus_additions(self):
        payroll = PayrollEngine.calculate_payroll(
            self.month, self.year, self.branch, user=self.admin_user
        )
        for line in payroll.lines.all():
            expected_net = line.gross_salary + line.total_additions - line.total_deductions
            self.assertAlmostEqual(float(line.net_salary), float(expected_net), places=2)

    def test_payroll_totals_match_lines(self):
        payroll = PayrollEngine.calculate_payroll(
            self.month, self.year, self.branch, user=self.admin_user
        )
        # نجمع net_salary من قاعدة البيانات (مقرّبة بالفعل إلى خانتين)
        calculated_net = sum(ln.net_salary for ln in payroll.lines.all())
        # نقبل فرقاً لا يتجاوز 0.10 بسبب تقريب الحساب اليومي per-employee
        self.assertAlmostEqual(float(payroll.total_net), float(calculated_net), delta=0.10)

    def test_cannot_recalculate_approved_payroll(self):
        payroll = PayrollEngine.calculate_payroll(
            self.month, self.year, self.branch, user=self.admin_user
        )
        PayrollEngine.approve_payroll(payroll, user=self.admin_user)
        with self.assertRaises(ValueError):
            PayrollEngine.calculate_payroll(
                self.month, self.year, self.branch, user=self.admin_user
            )

    def test_approve_payroll(self):
        payroll = PayrollEngine.calculate_payroll(
            self.month, self.year, self.branch, user=self.admin_user
        )
        approved = PayrollEngine.approve_payroll(payroll, user=self.admin_user)
        self.assertEqual(approved.status, 'approved')

    def test_approve_requires_calculated_status(self):
        payroll = Payroll.objects.create(
            month=3, year=2026, branch=self.branch, status='draft'
        )
        with self.assertRaises(ValueError):
            PayrollEngine.approve_payroll(payroll)


# ══════════════════════════════════════════════════════
# Test: Penalties & Bonuses
# ══════════════════════════════════════════════════════

class PenaltyTest(TestCase):
    def setUp(self):
        self.branch = make_branch()
        self.user = make_user()
        self.dept = make_department(self.branch)
        self.jt = make_job_title(self.dept)
        self.emp = make_employee(self.user, self.branch, self.dept, self.jt)

    def test_create_deduction_penalty(self):
        p = Penalty.objects.create(
            employee=self.emp,
            penalty_type='deduction',
            date=date.today(),
            amount=Decimal('200'),
            reason='تأخر متكرر',
        )
        self.assertEqual(p.penalty_type, 'deduction')
        self.assertEqual(p.amount, Decimal('200'))

    def test_create_bonus(self):
        p = Penalty.objects.create(
            employee=self.emp,
            penalty_type='bonus',
            date=date.today(),
            amount=Decimal('500'),
            reason='تميز في الأداء',
        )
        self.assertTrue(p.amount > 0)

    def test_penalty_reflected_in_payroll(self):
        """الجزاء يُخصم من الراتب"""
        admin = make_user('admin2')
        Penalty.objects.create(
            employee=self.emp,
            penalty_type='deduction',
            date=date(2026, 2, 15),
            amount=Decimal('300'),
            reason='مخالفة',
        )
        payroll = PayrollEngine.calculate_payroll(2, 2026, self.branch, user=admin)
        line = payroll.lines.get(employee=self.emp)
        self.assertEqual(line.penalty_deduction, Decimal('300'))


# ══════════════════════════════════════════════════════
# Test: Salary Advance
# ══════════════════════════════════════════════════════

class SalaryAdvanceTest(TestCase):
    def setUp(self):
        self.branch = make_branch()
        self.user = make_user()
        self.dept = make_department(self.branch)
        self.jt = make_job_title(self.dept)
        self.emp = make_employee(self.user, self.branch, self.dept, self.jt)

    def test_create_advance(self):
        adv = SalaryAdvance.objects.create(
            employee=self.emp,
            date=date.today(),
            amount=Decimal('1200'),
            reason='احتياج شخصي',
            deduction_months=3,
            monthly_deduction=Decimal('400'),
            remaining_amount=Decimal('1200'),
            status='approved',
        )
        self.assertEqual(adv.remaining_amount, Decimal('1200'))

    def test_advance_deducted_in_payroll(self):
        """السلفة تُخصم من الراتب الشهري"""
        admin = make_user('admin3')
        SalaryAdvance.objects.create(
            employee=self.emp,
            date=date(2026, 2, 1),
            amount=Decimal('900'),
            reason='سلفة',
            deduction_months=3,
            monthly_deduction=Decimal('300'),
            remaining_amount=Decimal('900'),
            status='approved',
        )
        payroll = PayrollEngine.calculate_payroll(2, 2026, self.branch, user=admin)
        line = payroll.lines.get(employee=self.emp)
        self.assertEqual(line.advance_deduction, Decimal('300'))

    def test_advance_fully_paid_after_deductions(self):
        """السلفة تصبح مسددة بالكامل بعد خصم كل الأقساط"""
        admin = make_user('admin4')
        adv = SalaryAdvance.objects.create(
            employee=self.emp,
            date=date(2026, 2, 1),
            amount=Decimal('400'),
            reason='سلفة صغيرة',
            deduction_months=1,
            monthly_deduction=Decimal('400'),
            remaining_amount=Decimal('400'),
            status='approved',
        )
        PayrollEngine.calculate_payroll(2, 2026, self.branch, user=admin)
        adv.refresh_from_db()
        self.assertEqual(adv.status, 'fully_paid')
        self.assertEqual(adv.remaining_amount, Decimal('0'))


# ══════════════════════════════════════════════════════
# Test: Piece Work
# ══════════════════════════════════════════════════════

class PieceWorkTest(TestCase):
    def setUp(self):
        from apps.inventory.models import Product, Category
        self.branch = make_branch()
        self.user = make_user()
        self.dept = make_department(self.branch)
        self.jt = make_job_title(self.dept)
        self.emp = make_employee(
            self.user, self.branch, self.dept, self.jt,
            employment_type='production', basic_salary=Decimal('3000'),
        )
        # إنشاء منتج للاختبار
        cat = Category.objects.create(name='تصنيف اختبار')
        from apps.inventory.models import UnitOfMeasure
        uom = UnitOfMeasure.objects.create(name='قطعة', symbol='قطعة')
        self.product = Product.objects.create(
            code='TST001', name='منتج اختباري',
            category=cat, unit=uom,
            cost_price=Decimal('10'), retail_price=Decimal('15'),
        )

    def test_create_piece_work(self):
        pw = ProductionPieceWork.objects.create(
            employee=self.emp,
            date=date.today(),
            product=self.product,
            quantity=Decimal('50'),
            rate=Decimal('3'),
            total=Decimal('150'),
            is_approved=True,
        )
        self.assertEqual(pw.total, Decimal('150'))
        self.assertTrue(pw.is_approved)

    def test_piece_work_salary_in_payroll(self):
        """عامل الإنتاج: راتبه = مجموع القطع"""
        admin = make_user('admin5')
        ProductionPieceWork.objects.create(
            employee=self.emp,
            date=date(2026, 3, 10),
            product=self.product,
            quantity=Decimal('100'),
            rate=Decimal('5'),
            total=Decimal('500'),
            is_approved=True,
        )
        ProductionPieceWork.objects.create(
            employee=self.emp,
            date=date(2026, 3, 20),
            product=self.product,
            quantity=Decimal('80'),
            rate=Decimal('5'),
            total=Decimal('400'),
            is_approved=True,
        )
        payroll = PayrollEngine.calculate_payroll(3, 2026, self.branch, user=admin)
        line = payroll.lines.get(employee=self.emp)
        self.assertEqual(line.gross_salary, Decimal('900'))


# ══════════════════════════════════════════════════════
# Test: Views (HTTP Responses)
# ══════════════════════════════════════════════════════

class HRViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user('viewuser', 'viewpass')
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='viewuser', password='viewpass')

        self.branch = make_branch()
        self.dept = make_department(self.branch)
        self.jt = make_job_title(self.dept)
        emp_user = make_user('empuser')
        self.emp = make_employee(
            emp_user, self.branch, self.dept, self.jt
        )

    def _check_url(self, url_name, kwargs=None, expected_status=200):
        url = reverse(url_name, kwargs=kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, expected_status,
                         f"URL {url_name} returned {response.status_code}")
        return response

    def test_employee_list_returns_200(self):
        self._check_url('hr:employee_list')

    def test_employee_create_returns_200(self):
        self._check_url('hr:employee_create')

    def test_employee_detail_returns_200(self):
        self._check_url('hr:employee_detail', {'pk': self.emp.pk})

    def test_employee_update_returns_200(self):
        self._check_url('hr:employee_update', {'pk': self.emp.pk})

    def test_attendance_list_returns_200(self):
        self._check_url('hr:attendance_list')

    def test_attendance_bulk_returns_200(self):
        self._check_url('hr:attendance_bulk')

    def test_leave_list_returns_200(self):
        self._check_url('hr:leave_list')

    def test_leave_create_returns_200(self):
        self._check_url('hr:leave_create')

    def test_penalty_list_returns_200(self):
        self._check_url('hr:penalty_list')

    def test_penalty_create_returns_200(self):
        self._check_url('hr:penalty_create')

    def test_advance_list_returns_200(self):
        self._check_url('hr:advance_list')

    def test_advance_create_returns_200(self):
        self._check_url('hr:advance_create')

    def test_payroll_list_returns_200(self):
        self._check_url('hr:payroll_list')

    def test_payroll_calculate_returns_200(self):
        self._check_url('hr:payroll_calculate')

    def test_department_list_returns_200(self):
        self._check_url('hr:department_list')

    def test_piece_work_list_returns_200(self):
        self._check_url('hr:piece_work_list')

    def test_piece_work_create_returns_200(self):
        self._check_url('hr:piece_work_create')

    def test_employee_list_requires_login(self):
        self.client.logout()
        url = reverse('hr:employee_list')
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)
        self.assertIn(response.status_code, [302, 403])

    def test_payroll_detail_returns_200(self):
        payroll = Payroll.objects.create(
            month=1, year=2026, branch=self.branch,
            status='calculated',
        )
        self._check_url('hr:payroll_detail', {'pk': payroll.pk})
