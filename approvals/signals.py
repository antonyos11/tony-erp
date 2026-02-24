from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ApprovalRequest
from notifications.services import send_notification_safe
from .services import get_approvers

@receiver(post_save, sender=ApprovalRequest)
def approval_created(sender, instance: ApprovalRequest, created, **kwargs):
    if created:
        amount = instance.amount or 0
        users = get_approvers(amount, instance.current_level)
        send_notification_safe(
            users=list(users),
            title=f"طلب موافقة جديد #{instance.id}",
            message=f"مطلوب موافقة على عنصر {instance.content_type}#{instance.object_id} بمبلغ {amount}",
            level='info'
        )