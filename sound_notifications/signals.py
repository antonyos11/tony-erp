"""
إشارات نظام الأصوات
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def create_sound_preferences(sender, instance, created, **kwargs):
    """إنشاء تفضيلات صوت للمستخدم الجديد"""
    if created:
        from .models import UserSoundPreference, SoundTheme
        default_theme = SoundTheme.objects.filter(is_default=True).first()
        UserSoundPreference.objects.create(
            user=instance,
            theme=default_theme
        )
