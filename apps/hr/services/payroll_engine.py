"""
محرك حساب الرواتب
يحسب الراتب تلقائياً بناء على الحضور والغياب والإضافي والجزاءات والسلف
وينشئ القيد المحاسبي
"""
import calendar
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.hr.models import (
    Employee, Attendance, Payroll, PayrollLine, Penalty,
    SalaryAdvance, ProductionPieceWork
)
from apps.accounts.services.journal_engine import JournalEngine


class PayrollEngine:
    """محرك الرواتب"""

    OVERTIME_RATE = Decimal('1.5')  # معامل الساعة الإضافية
    DAILY_HOURS = Decimal('8')      # ساعات العمل اليومية
    WORKING_DAYS = 26               # أيام العمل الشهرية

    @classmethod
    @transaction.atomic
    def calculate_payroll(cls, month, year, branch, user=None):
        """حساب مسيّر الرواتب لفرع معين"""
        existing = Payroll.objects.filter(month=month, year=year, branch=branch).first()
        if existing and existing.status in ('approved', 'paid'):
            raise ValueError(f"مسيّر الرواتب لشهر {month}/{year} معتمد بالفعل!")

        if existing and existing.status in ('draft', 'calculated'):
            existing.lines.all().delete()
            existing.delete()

        payroll = Payroll.objects.create(
            month=month,
            year=year,
            branch=branch,
            status='draft',
            created_by=user,
            updated_by=user,
        )

        employees = Employee.objects.filter(
            branch=branch, is_active=True
        ).select_related('department', 'job_title')

        total_gross = Decimal('0')
        total_deductions = Decimal('0')
        total_net = Decimal('0')
        total_bonuses = Decimal('0')
        total_overtime = Decimal('0')

        days_in_month = calendar.monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)

        for emp in employees:
            line = cls._calculate_employee_salary(payroll, emp, month_start, month_end, user)
            total_gross += line.gross_salary
            total_deductions += line.total_deductions
            total_net += line.net_salary
            total_bonuses += line.bonus + line.incentive
            total_overtime += line.overtime_amount

        payroll.total_gross = total_gross
        payroll.total_deductions = total_deductions
        payroll.total_net = total_net
        payroll.total_bonuses = total_bonuses
        payroll.total_overtime = total_overtime
        payroll.status = 'calculated'
        payroll.save()

        return payroll

    @classmethod
    def _calculate_employee_salary(cls, payroll, employee, month_start, month_end, user):
        """حساب راتب موظف واحد"""
        attendances = Attendance.objects.filter(
            employee=employee,
            date__range=[month_start, month_end],
        )

        present_days = attendances.filter(status='present').count()
        absent_days = attendances.filter(status='absent').count()
        late_count = attendances.filter(status='late').count()
        total_overtime = sum(
            a.overtime_hours for a in attendances.filter(overtime_hours__gt=0)
        )
        # ensure Decimal
        total_overtime = Decimal(str(total_overtime))

        # الراتب الأساسي والبدلات
        basic = employee.basic_salary
        housing = employee.housing_allowance
        transport = employee.transport_allowance
        food = employee.food_allowance
        other_allow = employee.other_allowances
        gross = basic + housing + transport + food + other_allow

        # خصم الغياب
        daily_rate = gross / cls.WORKING_DAYS
        absence_deduction = daily_rate * Decimal(str(absent_days))

        # خصم التأخير (كل 3 تأخيرات = يوم غياب)
        late_deduction = daily_rate * Decimal(str(late_count // 3))

        # الإضافي
        hourly_rate = daily_rate / cls.DAILY_HOURS
        overtime_amount = hourly_rate * cls.OVERTIME_RATE * total_overtime

        # المكافآت
        bonuses_qs = Penalty.objects.filter(
            employee=employee,
            date__range=[month_start, month_end],
            penalty_type__in=['bonus', 'incentive'],
        )
        total_bonus = sum(b.amount for b in bonuses_qs.filter(penalty_type='bonus'))
        total_incentive = sum(b.amount for b in bonuses_qs.filter(penalty_type='incentive'))
        total_bonus = Decimal(str(total_bonus))
        total_incentive = Decimal(str(total_incentive))

        # الجزاءات
        penalties_qs = Penalty.objects.filter(
            employee=employee,
            date__range=[month_start, month_end],
            penalty_type='deduction',
        )
        penalty_deduction = Decimal(str(sum(p.amount for p in penalties_qs)))

        # خصم السلف
        advance_deduction = Decimal('0')
        active_advances = SalaryAdvance.objects.filter(
            employee=employee, status='approved', remaining_amount__gt=0
        )
        for advance in active_advances:
            deduction = min(advance.monthly_deduction, advance.remaining_amount)
            advance_deduction += deduction
            advance.remaining_amount -= deduction
            if advance.remaining_amount <= 0:
                advance.remaining_amount = Decimal('0')
                advance.status = 'fully_paid'
            advance.save()

        commission = Decimal('0')

        # عمل بالقطعة
        if employee.employment_type == 'production':
            piece_works = ProductionPieceWork.objects.filter(
                employee=employee,
                date__range=[month_start, month_end],
                is_approved=True,
            )
            piece_total = Decimal(str(sum(pw.total for pw in piece_works)))
            gross = piece_total if piece_total > 0 else gross

        # يومية
        if employee.employment_type == 'daily':
            gross = employee.daily_rate * Decimal(str(present_days))

        social_insurance = employee.social_insurance_deduction
        tax = employee.tax_deduction

        total_additions = overtime_amount + total_bonus + total_incentive + commission
        total_deduct = (
            absence_deduction + late_deduction + penalty_deduction +
            advance_deduction + social_insurance + tax
        )
        net = gross + total_additions - total_deduct

        line = PayrollLine.objects.create(
            payroll=payroll,
            employee=employee,
            basic_salary=basic,
            housing_allowance=housing,
            transport_allowance=transport,
            food_allowance=food,
            other_allowances=other_allow,
            overtime_hours=total_overtime,
            overtime_amount=overtime_amount,
            bonus=total_bonus,
            incentive=total_incentive,
            commission=commission,
            absence_days=absent_days,
            absence_deduction=absence_deduction,
            late_deduction=late_deduction,
            penalty_deduction=penalty_deduction,
            advance_deduction=advance_deduction,
            social_insurance=social_insurance,
            tax=tax,
            gross_salary=gross,
            total_additions=total_additions,
            total_deductions=total_deduct,
            net_salary=net,
            working_days=cls.WORKING_DAYS,
            actual_days=present_days,
        )
        return line

    @classmethod
    @transaction.atomic
    def approve_payroll(cls, payroll, user=None):
        """اعتماد المسيّر"""
        if payroll.status != 'calculated':
            raise ValueError("المسيّر يجب أن يكون محسوباً أولاً")
        payroll.status = 'approved'
        payroll.updated_by = user
        payroll.save()
        return payroll

    @classmethod
    @transaction.atomic
    def pay_payroll(cls, payroll, user=None):
        """
        صرف الرواتب — إنشاء القيد المحاسبي
        من ح/ رواتب وأجور  611
        إلى ح/ الخزينة    1111
        """
        if payroll.status != 'approved':
            raise ValueError("المسيّر يجب أن يكون معتمداً أولاً")

        lines_data = [
            {
                'account_code': '611',
                'debit': payroll.total_net,
                'credit': 0,
                'description': f'رواتب شهر {payroll.month}/{payroll.year} - {payroll.branch.name}',
            },
            {
                'account_code': '1111',
                'debit': 0,
                'credit': payroll.total_net,
                'description': f'صرف رواتب شهر {payroll.month}/{payroll.year}',
            },
        ]

        entry = JournalEngine.create_entry(
            source='payroll',
            description=f'رواتب شهر {payroll.month}/{payroll.year} - فرع {payroll.branch.name}',
            branch=payroll.branch,
            lines_data=lines_data,
            user=user,
            auto_post=True,
        )

        payroll.journal_entry = entry
        payroll.status = 'paid'
        payroll.paid_date = timezone.now().date()
        payroll.updated_by = user
        payroll.save()
        return payroll
