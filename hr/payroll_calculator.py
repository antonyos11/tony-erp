"""
Payroll Auto-Calculator
حاسبة الرواتب التلقائية
"""

from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import (
    Employee,
    Payroll,
    AttendanceRecord,
    LeaveRequest,
    HRSettings
)


class PayrollCalculator:
    """محرك حساب الرواتب التلقائي"""
    
    def __init__(self, employee, period_start, period_end):
        self.employee = employee
        self.period_start = period_start
        self.period_end = period_end
        self.settings = HRSettings.objects.first()
    
    def calculate(self):
        """حساب راتب الموظف للفترة المحددة"""
        
        # Basic salary components
        basic_salary = self.employee.basic_salary
        housing = self.employee.housing_allowance or Decimal('0')
        transportation = self.employee.transportation_allowance or Decimal('0')
        other_allowances = self.employee.other_allowances or Decimal('0')
        
        # Calculate attendance
        attendance_data = self.calculate_attendance()
        
        # Calculate overtime
        overtime_hours = attendance_data['overtime_hours']
        overtime_amount = self.calculate_overtime(overtime_hours)
        
        # Calculate bonuses (from production if available)
        bonus_amount = self.calculate_bonus()
        
        # Calculate deductions
        late_penalty = self.calculate_late_penalty(attendance_data['late_minutes'])
        absence_deduction = self.calculate_absence_deduction(attendance_data['absence_days'])
        
        # حساب خصم أقساط السلف
        loan_deduction, loan_installments = self.calculate_loan_deductions()
        
        # Calculate totals
        gross_salary = (
            basic_salary + housing + transportation + 
            other_allowances + overtime_amount + bonus_amount
        )
        
        total_deductions = late_penalty + absence_deduction + loan_deduction
        net_salary = gross_salary - total_deductions
        
        return {
            'basic_salary': basic_salary,
            'housing_allowance': housing,
            'transportation_allowance': transportation,
            'other_allowances': other_allowances,
            'overtime_hours': overtime_hours,
            'overtime_amount': overtime_amount,
            'bonus_amount': bonus_amount,
            'late_penalty': late_penalty,
            'absence_deduction': absence_deduction,
            'loan_deduction': loan_deduction,
            'loan_installments': loan_installments,
            'gross_salary': gross_salary,
            'total_deductions': total_deductions,
            'net_salary': net_salary,
            'attendance_data': attendance_data,
        }
    
    def calculate_attendance(self):
        """حساب بيانات الحضور"""
        records = AttendanceRecord.objects.filter(
            employee=self.employee,
            timestamp__date__range=(self.period_start, self.period_end),
            record_type='check_in'
        )
        
        total_days = 0
        worked_hours = Decimal('0')
        overtime_hours = Decimal('0')
        late_minutes = Decimal('0')
        early_departures = 0
        
        # Get employee schedule
        schedule = self.employee.work_schedules.first()
        expected_hours_per_day = Decimal('8')  # Default
        if schedule:
            # Calculate from schedule
            # This is simplified - in real system, calculate from actual schedule times
            expected_hours_per_day = Decimal('8')
        
        # Group by date
        dates = records.values_list('timestamp__date', flat=True).distinct()
        
        for day in dates:
            day_records = AttendanceRecord.objects.filter(
                employee=self.employee,
                timestamp__date=day
            ).order_by('timestamp')
            
            check_in = day_records.filter(record_type='check_in').first()
            check_out = day_records.filter(record_type='check_out').first()
            
            if check_in and check_out:
                total_days += 1
                
                # Calculate worked hours
                duration = check_out.timestamp - check_in.timestamp
                hours = Decimal(duration.total_seconds()) / Decimal('3600')
                worked_hours += hours
                
                # Calculate overtime (if worked more than expected)
                if hours > expected_hours_per_day:
                    overtime_hours += (hours - expected_hours_per_day)
                
                # Calculate late (simplified - compare to 9:00 AM)
                # In real system, get from schedule
                expected_start_time = timezone.datetime.combine(
                    day,
                    timezone.datetime.strptime('09:00', '%H:%M').time()
                )
                if check_in.timestamp > expected_start_time:
                    late_duration = check_in.timestamp - expected_start_time
                    late_minutes += Decimal(late_duration.total_seconds()) / Decimal('60')
        
        # Calculate absence days
        total_period_days = (self.period_end - self.period_start).days + 1
        working_days = self.get_working_days_count()
        absence_days = working_days - total_days
        
        # Subtract approved leaves
        approved_leaves = LeaveRequest.objects.filter(
            employee=self.employee,
            status='approved',
            start_date__lte=self.period_end,
            end_date__gte=self.period_start
        )
        
        for leave in approved_leaves:
            # Calculate overlap days
            overlap_start = max(leave.start_date, self.period_start)
            overlap_end = min(leave.end_date, self.period_end)
            leave_days = (overlap_end - overlap_start).days + 1
            absence_days = max(0, absence_days - leave_days)
        
        return {
            'total_days': total_days,
            'worked_hours': worked_hours,
            'overtime_hours': overtime_hours,
            'late_minutes': late_minutes,
            'absence_days': max(0, absence_days),
            'expected_days': working_days,
        }
    
    def get_working_days_count(self):
        """حساب أيام العمل في الفترة (excluding weekends)"""
        working_days = 0
        current_date = self.period_start
        
        while current_date <= self.period_end:
            # Skip Friday (4) and Saturday (5) for Egypt
            # Adjust based on your country
            if current_date.weekday() not in [4, 5]:  # Fri, Sat
                working_days += 1
            current_date += timedelta(days=1)
        
        return working_days
    
    def calculate_overtime(self, overtime_hours):
        """حساب مبلغ الساعات الإضافية"""
        if overtime_hours <= 0:
            return Decimal('0')
        
        # Calculate hourly rate
        monthly_salary = self.employee.basic_salary
        # Assuming 26 working days, 8 hours per day
        hourly_rate = monthly_salary / (Decimal('26') * Decimal('8'))
        
        # Apply overtime rate (usually 1.5x)
        overtime_rate = Decimal('1.5')
        if self.settings:
            overtime_rate = self.settings.overtime_rate
        
        return overtime_hours * hourly_rate * overtime_rate
    
    def calculate_bonus(self):
        """حساب المكافآت من الإنتاجية"""
        # Try to get production bonus
        try:
            from production.models import WorkerProduction
            
            production_records = WorkerProduction.objects.filter(
                worker=self.employee.user,
                date__range=(self.period_start, self.period_end),
                supervisor_approved=True
            )
            
            total_bonus = production_records.aggregate(
                total=Sum('labor_cost_amount')
            )['total'] or Decimal('0')
            
            return total_bonus
        
        except ImportError:
            # Production module not available
            return Decimal('0')
    
    def calculate_late_penalty(self, late_minutes):
        """حساب غرامة التأخير"""
        if late_minutes <= 0:
            return Decimal('0')
        
        penalty_per_minute = Decimal('0')
        if self.settings:
            penalty_per_minute = self.settings.late_penalty_per_minute
        
        return late_minutes * penalty_per_minute
    
    def calculate_absence_deduction(self, absence_days):
        """حساب خصم الغياب"""
        if absence_days <= 0:
            return Decimal('0')
        
        # Deduct daily salary for each absence day
        monthly_salary = self.employee.basic_salary
        daily_salary = monthly_salary / Decimal('26')  # Assuming 26 working days
        
        return absence_days * daily_salary
    
    def calculate_loan_deductions(self):
        """
        حساب خصم أقساط السلف المستحقة للفترة الحالية
        Returns: (total_amount, installments_list)
        """
        from .models import EmployeeLoan, LoanInstallment
        
        total_loan_deduction = Decimal('0')
        installments_to_deduct = []
        
        # البحث عن الأقساط المستحقة في هذا الشهر
        pending_installments = LoanInstallment.objects.filter(
            loan__employee=self.employee,
            loan__status__in=['approved', 'active'],
            status='pending',
            due_date__lte=self.period_end,
            due_date__gte=self.period_start
        ).select_related('loan')
        
        for installment in pending_installments:
            total_loan_deduction += installment.amount
            installments_to_deduct.append(installment)
        
        return total_loan_deduction, installments_to_deduct


def auto_calculate_payroll(employee, period_start, period_end):
    """حساب تلقائي للراتب وإنشاء سجل Payroll"""
    calculator = PayrollCalculator(employee, period_start, period_end)
    data = calculator.calculate()
    
    # حساب other_deductions بإضافة خصم السلف
    other_deductions = data.get('loan_deduction', Decimal('0'))
    
    # Create or update payroll
    payroll, created = Payroll.objects.update_or_create(
        employee=employee,
        period_start=period_start,
        period_end=period_end,
        defaults={
            'basic_salary': data['basic_salary'],
            'housing_allowance': data['housing_allowance'],
            'transportation_allowance': data['transportation_allowance'],
            'other_allowances': data['other_allowances'],
            'overtime_hours': data['overtime_hours'],
            'overtime_amount': data['overtime_amount'],
            'bonus_amount': data['bonus_amount'],
            'late_penalty': data['late_penalty'],
            'absence_deduction': data['absence_deduction'],
            'other_deductions': other_deductions,
            'status': 'calculated',
            'calculated_at': timezone.now(),
        }
    )
    
    # ربط وتسجيل أقساط السلف المخصومة
    loan_installments = data.get('loan_installments', [])
    for installment in loan_installments:
        installment.mark_as_deducted(payroll)
    
    # Totals are calculated automatically in Payroll.save()
    
    return payroll, created


def bulk_calculate_payroll(period_start, period_end, employees=None):
    """حساب تلقائي جماعي للرواتب"""
    if employees is None:
        employees = Employee.objects.filter(status='active')
    
    results = {
        'created': 0,
        'updated': 0,
        'failed': 0,
        'errors': []
    }
    
    for employee in employees:
        try:
            payroll, created = auto_calculate_payroll(employee, period_start, period_end)
            if created:
                results['created'] += 1
            else:
                results['updated'] += 1
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"{employee.arabic_name}: {str(e)}")
    
    return results
