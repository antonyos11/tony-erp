from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VehicleExpense, FleetAccountingSettings, Trip, DriverViolation

@receiver(post_save, sender=VehicleExpense)
def create_vehicle_expense_journal(sender, instance: VehicleExpense, created, **kwargs):
    """إنشاء قيد محاسبي تلقائي بعد حفظ مصروف مركبة جديد إذا تم تفعيل ذلك."""
    if created:
        settings = FleetAccountingSettings.get()
        if settings.auto_create_journals:
            instance.ensure_journal_entry(getattr(instance, 'created_by', None))


@receiver(post_save, sender=Trip)
def update_vehicle_odometer(sender, instance: Trip, created, **kwargs):
    """تحديث عداد المركبة تلقائياً عند إنشاء رحلة جديدة ذات مسافة."""
    if created and instance.distance_km:
        try:
            vehicle = instance.vehicle
            vehicle.current_odometer = (vehicle.current_odometer or 0) + int(instance.distance_km)
            vehicle.save(update_fields=["current_odometer"])
        except Exception:
            pass


@receiver(post_save, sender=DriverViolation)
def create_expense_from_violation(sender, instance: DriverViolation, created, **kwargs):
    """إنشاء مصروف مركبة عند تسجيل مخالفة مدفوعة (أو عند تعديلها إلى مدفوعة) لضمان ظهورها في تحليلات المصروفات.

    لا يتم التكرار إذا كان هناك مصروف سبق إنشاؤه (نبحث بوصف مرجعي). تصنيف المصروف: fine.
    """
    try:
        if instance.is_paid and instance.amount and instance.driver_id:
            ref_desc = f"مخالفة: {instance.violation_type} #{instance.id}"
            exists = VehicleExpense.objects.filter(description=ref_desc).exists()
            if not exists:
                VehicleExpense.objects.create(
                    vehicle=instance.vehicle if instance.vehicle_id else None,
                    driver=instance.driver,
                    category='fine',
                    description=ref_desc,
                    amount=instance.amount,
                    date=instance.date,
                )
    except Exception:
        pass
