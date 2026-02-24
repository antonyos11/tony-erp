from django.core.management.base import BaseCommand
from accounting.services import AccountService
from decimal import Decimal

class Command(BaseCommand):
    help = 'عرض ميزان المراجعة (مبسط) مع إمكانية إخفاء الحسابات التجميعية.'

    def add_arguments(self, parser):
        parser.add_argument('--no-groups', action='store_true', help='إخفاء الحسابات التجميعية وإظهار الحسابات القابلة للقيد فقط')

    def handle(self, *args, **options):
        include_groups = not options['no_groups']
        rows = AccountService.get_trial_balance(include_groups=include_groups)
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        self.stdout.write('ميزان المراجعة' + (' (بدون مجموعات)' if not include_groups else ' (مع المجموعات)'))
        self.stdout.write('-' * 70)
        for r in rows:
            total_debit += r.debit
            total_credit += r.credit
            indent = '  ' * r.level
            self.stdout.write(f"{indent}{r.code:<8} {r.name:<30} D:{r.debit:>10} C:{r.credit:>10} B:{r.balance:>10}")
        self.stdout.write('-' * 70)
        self.stdout.write(f"الإجمالي: D:{total_debit} C:{total_credit}")
        if total_debit == total_credit:
            self.stdout.write(self.style.SUCCESS('✅ الميزان متوازن'))
        else:
            self.stdout.write(self.style.WARNING('⚠ الميزان غير متوازن'))
