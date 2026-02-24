from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Employee, Payroll, AttendanceRecord
from datetime import date, datetime

@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    """إنشاء ملف موظف تلقائياً عند إنشاء مستخدم جديد"""
    if created and not hasattr(instance, 'employee_profile'):
        # يمكن إنشاء ملف موظف أساسي هنا إذا لزم الأمر
        pass

@receiver(post_save, sender=AttendanceRecord)
def update_payroll_attendance(sender, instance, created, **kwargs):
    """تحديث بيانات الحضور في الراتب عند تسجيل حضور/انصراف"""
    if created:
        # يمكن إضافة منطق لحساب الساعات الإضافية أو التأخير
        pass

@receiver(post_save, sender=Payroll)
def create_accounting_entry(sender, instance, created, **kwargs):
    """إنشاء القيد المحاسبي عند اعتماد الراتب"""
    if instance.status == 'approved' and not instance.journal_entry:
        # يتم إنشاء القيد المحاسبي في المنظر
        pass