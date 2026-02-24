from django.core.management.base import BaseCommand
from showrooms.accounting_helpers import check_and_mark_overdue_payments


class Command(BaseCommand):
    help = 'فحص دفعات الإيجار المتأخرة وتحديثها'
    
    def handle(self, *args, **options):
        self.stdout.write('جاري فحص دفعات الإيجار المتأخرة...')
        
        overdue_count = check_and_mark_overdue_payments()
        
        if overdue_count > 0:
            self.stdout.write(
                self.style.WARNING(f'تم تحديد {overdue_count} دفعة كمتأخرة')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('لا توجد دفعات متأخرة')
            )
