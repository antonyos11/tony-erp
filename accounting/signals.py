from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import JournalEntryItem
from .services import invalidate_account_balance

@receiver([post_save, post_delete], sender=JournalEntryItem)
def _invalidate_balance(sender, instance: JournalEntryItem, **kwargs):
    if instance.account.id:
        invalidate_account_balance(instance.account.id)
