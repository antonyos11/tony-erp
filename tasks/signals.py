"""
إشارات نظام المهام
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def create_default_task_list(sender, instance, created, **kwargs):
    """إنشاء قائمة مهام افتراضية للمستخدم الجديد"""
    if created:
        from .models import TaskList
        TaskList.objects.create(
            name='مهامي',
            owner=instance,
            is_default=True
        )
