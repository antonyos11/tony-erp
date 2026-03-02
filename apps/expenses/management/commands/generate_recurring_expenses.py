from django.core.management.base import BaseCommand
from apps.expenses.services.expense_engine import ExpenseEngine


class Command(BaseCommand):
    help = 'توليد المصروفات الدورية المستحقة'

    def handle(self, *args, **options):
        generated = ExpenseEngine.generate_recurring_expenses()
        self.stdout.write(self.style.SUCCESS(f'تم توليد {len(generated)} مصروف دوري'))
