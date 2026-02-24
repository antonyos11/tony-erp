"""
Management command to create missing UserProfiles for existing users
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserProfile, UserRole
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إنشاء ملفات تعريف (UserProfile) للمستخدمين الموجودين الذين لا يملكون ملف تعريف'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض المستخدمين الذين سيتم إنشاء ملفات تعريف لهم دون تنفيذ فعلي',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get users without profiles
        users_without_profile = User.objects.filter(profile__isnull=True)
        count = users_without_profile.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ جميع المستخدمين لديهم ملفات تعريف'))
            return
        
        self.stdout.write(f'📊 عدد المستخدمين بدون ملفات تعريف: {count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 وضع المعاينة - لن يتم إجراء أي تغييرات\n'))
            for user in users_without_profile:
                self.stdout.write(f'  - {user.username} (ID: {user.id})')
            return
        
        # Get or create default role
        default_role, created = UserRole.objects.get_or_create(
            name='viewer',
            defaults={
                'display_name': 'مستخدم عرض فقط',
                'description': 'دور افتراضي للمستخدمين الجدد',
                'can_approve': False,
                'max_approval_amount': 0,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ تم إنشاء الدور الافتراضي: {default_role.name}'))
        
        # Create profiles
        created_count = 0
        failed_count = 0
        
        for user in users_without_profile:
            try:
                with transaction.atomic():
                    profile = UserProfile.objects.create(
                        user=user,
                        arabic_name=user.get_full_name() or user.username,
                        employee_id=f'EMP-{user.id:06d}',
                        role=default_role,
                        is_approved=user.is_superuser,  # Auto-approve superusers
                        must_change_password=not user.is_superuser,
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✅ تم إنشاء ملف تعريف للمستخدم: {user.username}'))
                    
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f'❌ فشل إنشاء ملف تعريف للمستخدم {user.username}: {str(e)}'))
                logger.error(f'Failed to create profile for {user.username}: {str(e)}')
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✅ تم إنشاء: {created_count}'))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ فشل: {failed_count}'))
        self.stdout.write('='*60)
