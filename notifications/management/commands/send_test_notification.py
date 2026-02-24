from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.services import send_notification


class Command(BaseCommand):
    help = 'Send a test notification to the first superuser (or any active user).'

    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(self.style.ERROR('No active users found'))
            return
        send_notification(user, 'اختبار إشعار', 'هذا إشعار تجريبي للتأكد من عمل النظام', 'info')
        self.stdout.write(self.style.SUCCESS(f'Sent test notification to {user.username}'))