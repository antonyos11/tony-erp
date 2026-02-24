from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from accounting.models import (
    CostPool, CostPoolConsumption, CostAllocationRun, CostAllocationResult,
    JournalEntry, JournalEntryItem, Account, CostPoolSourceAccount
)

class Command(BaseCommand):
    help = 'تشغيل توزيع التكاليف (مبدئي: يجمع ويحسب ويخلق قيوداً)'

    def add_arguments(self, parser):
        parser.add_argument('--period', required=True, help='صيغة مثل 2025-09 أو 2025Q3')
        parser.add_argument('--dry-run', action='store_true', help='عدم إنشاء قيود فعلية')
        parser.add_argument('--note', default='', help='ملاحظات للتشغيل')
        parser.add_argument('--force', action='store_true', help='السماح بإعادة تشغيل فترة سبق اكتمالها')

    def handle(self, *args, **options):
        period = options['period']
        dry_run = options['dry_run']
        note = options['note']
        force = options['force']

        if not force and CostAllocationRun.objects.filter(period=period, status='completed').exists():
            raise CommandError(f'تم بالفعل تنفيذ توزيع مكتمل لهذه الفترة {period}. استخدم --force لإعادة التنفيذ.')

        with transaction.atomic():
            run = CostAllocationRun.objects.create(period=period, executed_by=None, notes=note, status='running')
            pools = CostPool.objects.filter(is_active=True).select_related('driver','debit_account','credit_account')
            if not pools.exists():
                self.stdout.write(self.style.WARNING('لا توجد مجمعات نشطة'))
                run.status = 'empty'
                run.save(update_fields=['status'])
                return

            total_indirect = Decimal('0')
            total_allocated = Decimal('0')
            for pool in pools:
                consumptions = list(CostPoolConsumption.objects.filter(pool=pool, period=period).select_related('cost_center'))
                if not consumptions:
                    continue
                total_qty = sum(c.driver_quantity for c in consumptions)
                if total_qty <= 0:
                    continue
                # حساب مبلغ المجمع من الحسابات المصدر
                pool_amount = Decimal('0')
                sources = CostPoolSourceAccount.objects.filter(pool=pool, is_active=True).select_related('account')
                if sources:
                    for s in sources:
                        acc = s.account
                        # رصيد الحساب (استخدام خاصية balance الحالية) - يمكن تحسينه باستعلام مجمع حسب فترة لاحقاً
                        acc_balance = acc.balance
                        portion = acc_balance * (s.percentage/Decimal('100')) if s.percentage and s.percentage > 0 else acc_balance
                        pool_amount += portion
                if pool_amount <= 0:
                    # لا يوجد تكلفة ليتم توزيعها
                    continue
                rate = (pool_amount / total_qty) if pool_amount else Decimal('0')
                # إنشاء قيد توزيع لكل مجمع (يمكن دمجه لاحقاً في قيد واحد شامل)
                je = None
                if not dry_run:
                    je = JournalEntry.objects.create(
                        description=f'توزيع تكاليف مجمع {pool.code} للفترة {period}',
                        entry_type='adjustment',
                        reference=f'ALLOC-{period}-{pool.code}',
                        date=timezone.now().date(),
                        created_by=None,  # يمكن تزويد مستخدم لاحقاً
                        is_posted=True
                    )
                alloc_items = []
                for c in consumptions:
                    allocated = (rate * c.driver_quantity).quantize(Decimal('0.01'))
                    total_allocated += allocated
                    # بند مدين (تحميل المصروف على مركز المستفيد) - إن وجد debit_account للمجمع
                    if not dry_run and pool.debit_account:
                        alloc_items.append(JournalEntryItem(
                            journal_entry=je,
                            account=pool.debit_account,
                            type='debit',
                            amount=allocated,
                            description=f'تحميل {pool.code} {period}',
                            cost_center=c.cost_center
                        ))
                    # تسجيل النتيجة
                    CostAllocationResult.objects.create(
                        run=run,
                        pool=pool,
                        cost_center=c.cost_center,
                        driver_quantity=c.driver_quantity,
                        driver_rate=rate,
                        allocated_amount=allocated,
                        journal_entry=je
                    )
                # بند مقابل دائن (تفريغ المجمع) بمبلغ إجمالي
                if not dry_run and pool.credit_account and alloc_items:
                    alloc_items.append(JournalEntryItem(
                        journal_entry=je,
                        account=pool.credit_account,
                        type='credit',
                        amount=sum(i.amount for i in alloc_items if i.type=='debit'),
                        description=f'تفريغ مجمع {pool.code} {period}'
                    ))
                if not dry_run and alloc_items:
                    JournalEntryItem.objects.bulk_create(alloc_items)
                total_indirect += pool_amount

            run.total_indirect_cost = total_indirect
            run.total_allocated = total_allocated
            run.status = 'completed'
            run.finished_at = timezone.now()
            run.save(update_fields=['total_indirect_cost','total_allocated','status','finished_at'])

        if dry_run:
            self.stdout.write(self.style.WARNING('تم التشغيل بوضع Dry-Run (لم تُنشأ قيود).'))
        self.stdout.write(self.style.SUCCESS(f'اكتمل تشغيل التوزيع للفترة {period}. إجمالي موزع: {total_allocated}'))
