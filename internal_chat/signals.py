"""
Signals للدردشة الداخلية
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import ChatSettings, OnlineStatus

User = get_user_model()


@receiver(post_save, sender=User)
def create_chat_profile(sender, instance, created, **kwargs):
    """إنشاء إعدادات الدردشة للمستخدم الجديد"""
    if created:
        ChatSettings.objects.get_or_create(user=instance)
        OnlineStatus.objects.get_or_create(user=instance)
