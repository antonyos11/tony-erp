from django.core.management.base import BaseCommand
from apps.crm.services.crm_engine import CRMEngine


class Command(BaseCommand):
    help = 'تحديث تقييمات كل العملاء'

    def handle(self, *args, **options):
        CRMEngine.update_all_ratings()
        self.stdout.write(self.style.SUCCESS('تم تحديث تقييمات العملاء'))
