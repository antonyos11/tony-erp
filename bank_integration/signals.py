"""
Signal handlers for bank integration
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='bank_integration.BankTransaction')
def on_bank_transaction_created(sender, instance, created, **kwargs):
    """معالج عند إنشاء عملية بنكية جديدة"""
    if created:
        # محاولة المطابقة التلقائية إذا كانت مفعلة
        if instance.account.auto_reconcile:
            from bank_integration.services import reconciliation_service
            reconciliation_service.auto_reconcile(instance.account)


@receiver(post_save, sender='risk_management.InsurancePolicy')
def on_policy_approaching_expiry(sender, instance, created, **kwargs):
    """معالج عند اقتراب انتهاء البوليصة"""
    if instance.is_expiring_soon(days=30):
        # إرسال تنبيه
        from notifications.models import Notification
        Notification.objects.create(
            title='تنبيه: انتهاء البوليصة قريباً',
            message=f'البوليصة {instance.policy_number} ستنتهي في {instance.end_date}',
            notification_type='warning'
        )


@receiver(post_save, sender='contract_management.Contract')
def on_contract_approaching_expiry(sender, instance, created, **kwargs):
    """معالج عند اقتراب انتهاء العقد"""
    if instance.is_expiring_soon(days=30):
        # إرسال تنبيه
        from notifications.models import Notification
        Notification.objects.create(
            title='تنبيه: انتهاء العقد قريباً',
            message=f'العقد {instance.contract_number} سينتهي في {instance.end_date}',
            notification_type='warning'
        )


@receiver(post_save, sender='intellectual_property.Patent')
def on_patent_approaching_expiry(sender, instance, created, **kwargs):
    """معالج عند اقتراب انتهاء براءة الاختراع"""
    if instance.is_expiring_soon(days=90):
        # تحديث التذكير
        instance.status = 'expired'
        instance.save(update_fields=['status'])
