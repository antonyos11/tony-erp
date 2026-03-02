"""
management command: close_fiscal_year — Sprint 20
إقفال السنة المالية ونقل الأرصدة
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal


class Command(BaseCommand):
    help = 'إقفال السنة المالية الحالية وفتح سنة جديدة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='السنة المالية للإقفال (مثلاً 2025)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='معاينة فقط بدون تنفيذ',
        )

    def handle(self, *args, **options):
        from apps.accounts.models import Account, JournalEntry, JournalLine, FiscalYear
        from django.db.models import Sum

        year = options.get('year') or timezone.now().year
        dry_run = options.get('dry_run', False)

        self.stdout.write(f'[RITA ERP] إقفال السنة المالية: {year}')
        if dry_run:
            self.stdout.write(self.style.WARNING('--- معاينة فقط (dry-run) ---'))

        # 1. التحقق من وجود السنة المالية
        try:
            fiscal_year = FiscalYear.objects.get(
                start_date__year=year, is_active=True
            )
        except FiscalYear.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'لم يتم العثور على سنة مالية نشطة للعام {year}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ: {e}'))
            return

        # 2. حساب أرصدة الإيرادات والمصروفات
        revenue_accounts = Account.objects.filter(
            account_type='revenue', is_active=True, is_detail=True
        )
        expense_accounts = Account.objects.filter(
            account_type='expense', is_active=True, is_detail=True
        )

        total_revenue = Decimal('0')
        total_expenses = Decimal('0')

        for acc in revenue_accounts:
            lines = JournalLine.objects.filter(
                account=acc,
                entry__status='posted',
                entry__date__year=year,
            ).aggregate(d=Sum('debit'), c=Sum('credit'))
            balance = (lines['c'] or Decimal('0')) - (lines['d'] or Decimal('0'))
            total_revenue += balance
            self.stdout.write(f'  إيراد: {acc.name} — {balance:,.2f}')

        for acc in expense_accounts:
            lines = JournalLine.objects.filter(
                account=acc,
                entry__status='posted',
                entry__date__year=year,
            ).aggregate(d=Sum('debit'), c=Sum('credit'))
            balance = (lines['d'] or Decimal('0')) - (lines['c'] or Decimal('0'))
            total_expenses += balance
            self.stdout.write(f'  مصروف: {acc.name} — {balance:,.2f}')

        net_profit = total_revenue - total_expenses
        self.stdout.write(f'\nإجمالي الإيرادات: {total_revenue:,.2f}')
        self.stdout.write(f'إجمالي المصروفات: {total_expenses:,.2f}')
        self.stdout.write(self.style.SUCCESS(f'صافي الربح/الخسارة: {net_profit:,.2f}'))

        if dry_run:
            self.stdout.write(self.style.WARNING('لم يتم إجراء أي تعديلات (dry-run)'))
            return

        # 3. إنشاء قيد إقفال
        try:
            retained_earnings_acc = Account.objects.filter(
                code__startswith='3',
                name__icontains='أرباح محتجز',
            ).first() or Account.objects.filter(account_type='equity').first()

            if not retained_earnings_acc:
                self.stdout.write(self.style.WARNING('لم يتم العثور على حساب الأرباح المحتجزة'))
                return

            closing_entry = JournalEntry.objects.create(
                entry_number=f'CLO-{year}-001',
                date=timezone.now().date(),
                description=f'قيد إقفال السنة المالية {year}',
                status='posted',
                is_auto=True,
            )

            # تصفير الإيرادات
            for acc in revenue_accounts:
                lines = JournalLine.objects.filter(
                    account=acc, entry__status='posted', entry__date__year=year
                ).aggregate(d=Sum('debit'), c=Sum('credit'))
                balance = (lines['c'] or Decimal('0')) - (lines['d'] or Decimal('0'))
                if balance > 0:
                    JournalLine.objects.create(
                        entry=closing_entry,
                        account=acc,
                        debit=balance,
                        credit=Decimal('0'),
                        description=f'إقفال الإيراد {acc.name}',
                    )

            # تصفير المصروفات
            for acc in expense_accounts:
                lines = JournalLine.objects.filter(
                    account=acc, entry__status='posted', entry__date__year=year
                ).aggregate(d=Sum('debit'), c=Sum('credit'))
                balance = (lines['d'] or Decimal('0')) - (lines['c'] or Decimal('0'))
                if balance > 0:
                    JournalLine.objects.create(
                        entry=closing_entry,
                        account=acc,
                        debit=Decimal('0'),
                        credit=balance,
                        description=f'إقفال المصروف {acc.name}',
                    )

            # نقل صافي الربح للأرباح المحتجزة
            if net_profit > 0:
                JournalLine.objects.create(
                    entry=closing_entry,
                    account=retained_earnings_acc,
                    debit=Decimal('0'),
                    credit=net_profit,
                    description=f'صافي ربح السنة {year}',
                )
            elif net_profit < 0:
                JournalLine.objects.create(
                    entry=closing_entry,
                    account=retained_earnings_acc,
                    debit=abs(net_profit),
                    credit=Decimal('0'),
                    description=f'صافي خسارة السنة {year}',
                )

            # إغلاق السنة المالية الحالية
            fiscal_year.is_active = False
            fiscal_year.save()

            # فتح سنة مالية جديدة
            new_year = year + 1
            FiscalYear.objects.create(
                name=f'السنة المالية {new_year}',
                start_date=f'{new_year}-01-01',
                end_date=f'{new_year}-12-31',
                is_active=True,
            )

            self.stdout.write(self.style.SUCCESS(
                f'\n✅ تم إقفال السنة المالية {year} بنجاح'
                f'\n✅ تم فتح السنة المالية {new_year}'
                f'\n✅ قيد الإقفال: {closing_entry.entry_number}'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطأ في إنشاء قيد الإقفال: {e}'))
