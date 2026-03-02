from django.core.management.base import BaseCommand
from apps.notifications.services.notification_engine import NotificationEngine


class Command(BaseCommand):
    help = 'فحص وتوليد الإشعارات التلقائية'

    def handle(self, *args, **options):
        self.stdout.write('جاري فحص الإشعارات...')
        NotificationEngine.run_all_checks()
        self.stdout.write(self.style.SUCCESS('تم فحص الإشعارات بنجاح'))
