"""
Signals for Users app - Auto-create UserProfile on User creation
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    إنشاء UserProfile تلقائياً عند إنشاء مستخدم جديد
    Auto-create UserProfile when a new User is created
    """
    if created:
        try:
            from users.models import UserProfile, UserRole
            
            # Check if profile already exists (safety check)
            if hasattr(instance, 'profile'):
                return
            
            # Get or create a default role
            default_role, _ = UserRole.objects.get_or_create(
                name='viewer',
                defaults={
                    'display_name': 'مستخدم عرض فقط',
                    'description': 'دور افتراضي للمستخدمين الجدد',
                    'can_approve': False,
                    'max_approval_amount': 0,
                }
            )
            
            # Create UserProfile (use get_or_create to avoid duplicate)
            profile, prof_created = UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'arabic_name': instance.get_full_name() or instance.username,
                    'employee_id': f'EMP-{instance.id:06d}',
                    'role': default_role,
                    'is_approved': False,
                    'must_change_password': True,
                }
            )
            
            if prof_created:
                logger.info(f"UserProfile created for user: {instance.username}")
            else:
                logger.info(f"UserProfile already exists for user: {instance.username}")
            
        except Exception as e:
            logger.error(f"Error creating UserProfile for {instance.username}: {str(e)}")
