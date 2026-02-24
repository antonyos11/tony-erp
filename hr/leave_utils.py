"""
دوال حساب الإجازات وأيام العمل
"""

from datetime import timedelta
from .models import WeekendDay, PublicHoliday


def calculate_working_days(start_date, end_date):
    """
    حساب عدد أيام العمل بين تاريخين (باستثناء عطل نهاية الأسبوع والعطل الرسمية)
    
    Args:
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
    
    Returns:
        int: عدد أيام العمل
    """
    if start_date > end_date:
        return 0
    
    # الحصول على أيام عطلة نهاية الأسبوع (is_active=True يعني عطلة)
    weekend_days = set(
        WeekendDay.objects.filter(is_active=True).values_list('day_of_week', flat=True)
    )
    
    # الحصول على العطل الرسمية
    holidays = set(
        PublicHoliday.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values_list('date', flat=True)
    )
    
    # حساب الأيام
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # فحص إذا كان يوم عطلة نهاية أسبوع
        weekday = current_date.weekday()  # 0=Monday, 6=Sunday
        
        if weekday not in weekend_days and current_date not in holidays:
            working_days += 1
        
        current_date += timedelta(days=1)
    
    return working_days


def calculate_leave_balance(employee, leave_type):
    """
    حساب رصيد إجازات الموظف (wrapper لـ hr_utils)
    
    Args:
        employee: كائن Employee
        leave_type: نوع الإجازة
    
    Returns:
        float: الرصيد المتبقي
    """
    from .hr_utils import calculate_employee_leave_balance
    
    balance_info = calculate_employee_leave_balance(employee, leave_type)
    return balance_info['remaining_days']


def is_working_day(check_date):
    """
    فحص إذا كان تاريخ معين يوم عمل
    
    Args:
        check_date: التاريخ للفحص
    
    Returns:
        bool: True إذا كان يوم عمل
    """
    # فحص عطلة نهاية الأسبوع (is_active=True يعني عطلة)
    weekday = check_date.weekday()
    weekend = WeekendDay.objects.filter(
        day_of_week=weekday,
        is_active=True
    ).exists()
    
    if weekend:
        return False
    
    # فحص العطل الرسمية
    holiday = PublicHoliday.objects.filter(date=check_date).exists()
    
    return not holiday


def get_next_working_day(start_date, skip_days=1):
    """
    الحصول على يوم العمل التالي
    
    Args:
        start_date: تاريخ البداية
        skip_days: عدد أيام العمل للتخطي
    
    Returns:
        date: يوم العمل التالي
    """
    current_date = start_date
    working_days_found = 0
    
    while working_days_found < skip_days:
        current_date += timedelta(days=1)
        
        if is_working_day(current_date):
            working_days_found += 1
    
    return current_date
