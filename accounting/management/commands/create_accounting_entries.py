from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from accounting.models import Account, JournalEntry, JournalEntryItem
from sales.models import Invoice
from purchases.models import PurchaseBill


class Command(BaseCommand):
    help = 'إنشاء قيود محاسبية من فواتير المبيعات والمشتريات الموجودة'

    def handle(self, *args, **options):
        """تنفيذ الأمر"""
        self.stdout.write(self.style.SUCCESS('بدء إنشاء القيود المحاسبية'))

        # إنشاء قيود من فواتير المبيعات
        sales_count = self.create_sales_entries()

        # إنشاء قيود من فواتير المشتريات
        purchases_count = self.create_purchase_entries()

        self.stdout.write(
            self.style.SUCCESS(
                f'تم إنشاء {sales_count} قيد من المبيعات و {purchases_count} قيد من المشتريات'
            )
        )

    def create_sales_entries(self):
        """إنشاء قيود محاسبية من فواتير المبيعات"""
        self.stdout.write('معالجة فواتير المبيعات...')

        # الحصول على الحسابات المطلوبة
        try:
            customers_account = Account.objects.get(code='1100')  # العملاء
            sales_account = Account.objects.get(code='4001')     # مبيعات البضائع
            cash_account = Account.objects.get(code='1001')      # النقدية
            cost_account = Account.objects.get(code='5001')      # تكلفة البضاعة المباعة
            inventory_account = Account.objects.get(code='1200') # المخزون
        except Account.DoesNotExist as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ: حساب مطلوب غير موجود: {e}')
            )
            return 0

        invoices = Invoice.objects.all()
        created_count = 0

        for invoice in invoices:
            # تحقق إذا كان هناك قيد محاسبي للفاتورة
            if JournalEntry.objects.filter(invoice=invoice).exists():
                continue

            try:
                with transaction.atomic():
                    # إنشاء قيد المبيعات
                    journal_entry = JournalEntry.objects.create(
                        date=invoice.date,
                        entry_type='sales',
                        description=f'مبيعات للعميل {invoice.customer.name} - فاتورة {invoice.number}',
                        reference=invoice.number,
                        invoice=invoice,
                        is_posted=True
                    )

                    # حساب إجمالي الفاتورة
                    total_amount = invoice.total

                    # قيد المدين - العملاء أو النقدية
                    debit_account = cash_account if invoice.paid == total_amount else customers_account
                    JournalEntryItem.objects.create(
                        journal_entry=journal_entry,
                        account=debit_account,
                        type='debit',
                        amount=total_amount,
                        description=f'مبيعات {invoice.customer.name}'
                    )

                    # قيد الدائن - المبيعات
                    JournalEntryItem.objects.create(
                        journal_entry=journal_entry,
                        account=sales_account,
                        type='credit',
                        amount=total_amount,
                        description=f'إيرادات مبيعات {invoice.customer.name}'
                    )

                    # قيد تكلفة البضاعة المباعة
                    total_cost = Decimal('0')
                    for item in invoice.items.all():
                        item_cost = item.quantity * item.product.cost
                        total_cost += item_cost

                    if total_cost > 0:
                        # مدين: تكلفة البضاعة المباعة
                        JournalEntryItem.objects.create(
                            journal_entry=journal_entry,
                            account=cost_account,
                            type='debit',
                            amount=total_cost,
                            description=f'تكلفة البضاعة المباعة - {invoice.number}'
                        )

                        # دائن: المخزون
                        JournalEntryItem.objects.create(
                            journal_entry=journal_entry,
                            account=inventory_account,
                            type='credit',
                            amount=total_cost,
                            description=f'تكلفة البضاعة المباعة - {invoice.number}'
                        )

                    # إذا كان هناك دفع جزئي
                    if 0 < invoice.paid < total_amount:
                        # قيد إضافي لتسجيل الدفع
                        paid_entry = JournalEntry.objects.create(
                            date=invoice.date,
                            entry_type='receipt',
                            description=f'دفع جزئي من العميل {invoice.customer.name} - فاتورة {invoice.number}',
                            reference=f'{invoice.number}-PAYMENT',
                            invoice=invoice,
                            is_posted=True
                        )

                        # مدين: النقدية
                        JournalEntryItem.objects.create(
                            journal_entry=paid_entry,
                            account=cash_account,
                            type='debit',
                            amount=invoice.paid,
                            description=f'تحصيل من {invoice.customer.name}'
                        )

                        # دائن: العملاء
                        JournalEntryItem.objects.create(
                            journal_entry=paid_entry,
                            account=customers_account,
                            type='credit',
                            amount=invoice.paid,
                            description=f'تحصيل من {invoice.customer.name}'
                        )

                    created_count += 1
                    self.stdout.write(f'  تمت معالجة فاتورة {invoice.number}')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  خطأ في فاتورة {invoice.number}: {e}')
                )

        return created_count

    def create_purchase_entries(self):
        """إنشاء قيود محاسبية من فواتير المشتريات"""
        self.stdout.write('معالجة فواتير المشتريات...')

        # الحصول على الحسابات المطلوبة
        try:
            suppliers_account = Account.objects.get(code='2001')  # الموردين
            inventory_account = Account.objects.get(code='1200')  # المخزون
            cash_account = Account.objects.get(code='1001')       # النقدية
        except Account.DoesNotExist as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ: حساب مطلوب غير موجود: {e}')
            )
            return 0

        purchase_bills = PurchaseBill.objects.all()
        created_count = 0

        for bill in purchase_bills:
            # تحقق إذا كان هناك قيد محاسبي للفاتورة
            if JournalEntry.objects.filter(purchase_bill=bill).exists():
                continue

            try:
                with transaction.atomic():
                    # إنشاء قيد المشتريات
                    journal_entry = JournalEntry.objects.create(
                        date=bill.date,
                        entry_type='purchase',
                        description=f'مشتريات من المورد {bill.supplier.name} - فاتورة {bill.number}',
                        reference=bill.number,
                        purchase_bill=bill,
                        is_posted=True
                    )

                    # حساب إجمالي فاتورة المشتريات
                    total_amount = bill.total

                    # قيد المدين - المخزون
                    JournalEntryItem.objects.create(
                        journal_entry=journal_entry,
                        account=inventory_account,
                        type='debit',
                        amount=total_amount,
                        description=f'مشتريات من {bill.supplier.name}'
                    )

                    # قيد الدائن - الموردين أو النقدية
                    credit_account = cash_account if bill.paid == total_amount else suppliers_account
                    JournalEntryItem.objects.create(
                        journal_entry=journal_entry,
                        account=credit_account,
                        type='credit',
                        amount=total_amount,
                        description=f'مشتريات من {bill.supplier.name}'
                    )

                    # إذا كان هناك دفع جزئي
                    if 0 < bill.paid < total_amount:
                        # قيد إضافي لتسجيل الدفع
                        paid_entry = JournalEntry.objects.create(
                            date=bill.date,
                            entry_type='payment',
                            description=f'دفع جزئي للمورد {bill.supplier.name} - فاتورة {bill.number}',
                            reference=f'{bill.number}-PAYMENT',
                            purchase_bill=bill,
                            is_posted=True
                        )

                        # مدين: الموردين
                        JournalEntryItem.objects.create(
                            journal_entry=paid_entry,
                            account=suppliers_account,
                            type='debit',
                            amount=bill.paid,
                            description=f'دفع لـ {bill.supplier.name}'
                        )

                        # دائن: النقدية
                        JournalEntryItem.objects.create(
                            journal_entry=paid_entry,
                            account=cash_account,
                            type='credit',
                            amount=bill.paid,
                            description=f'دفع لـ {bill.supplier.name}'
                        )

                    created_count += 1
                    self.stdout.write(f'  تمت معالجة فاتورة {bill.number}')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  خطأ في فاتورة {bill.number}: {e}')
                )

        return created_count