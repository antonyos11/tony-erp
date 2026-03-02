"""
محرك المصروفات وسندات الصرف والقبض
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.expenses.models import (
    Expense, RecurringExpense, PaymentVoucher, ReceiptVoucher,
    PettyCash, PettyCashTransaction
)
from apps.accounts.services.journal_engine import JournalEngine
from apps.accounts.services.vat_engine import VATEngine


class ExpenseEngine:
    """محرك المصروفات"""

    @staticmethod
    def _generate_expense_number():
        today = timezone.now()
        count = Expense.objects.filter(date__year=today.year, date__month=today.month).count() + 1
        return f"EXP-{today.strftime('%Y%m')}-{count:04d}"

    @classmethod
    @transaction.atomic
    def create_expense(cls, category, branch, description, amount,
                       is_taxable=False, payment_method='cash',
                       supplier=None, department=None, receipt_image=None, user=None):
        """إنشاء مصروف"""
        tax_amount = Decimal('0')
        if is_taxable:
            vat = VATEngine.calculate_tax(amount)
            tax_amount = vat['tax_amount']

        expense = Expense.objects.create(
            expense_number=cls._generate_expense_number(),
            date=timezone.now().date(),
            category=category,
            branch=branch,
            department=department,
            description=description,
            amount=amount,
            tax_amount=tax_amount,
            total=amount + tax_amount,
            is_taxable=is_taxable,
            payment_method=payment_method,
            supplier=supplier,
            receipt_image=receipt_image,
            status='draft',
            created_by=user,
            updated_by=user,
        )
        return expense

    @classmethod
    @transaction.atomic
    def approve_and_pay_expense(cls, expense, user=None):
        """اعتماد وصرف مصروف — ينشئ القيد"""
        if expense.status not in ('draft', 'pending'):
            raise ValueError("المصروف ليس في حالة تسمح بالاعتماد")

        account_code = expense.category.account.code

        lines_data = [
            {
                'account_code': account_code,
                'debit': expense.amount,
                'credit': 0,
                'description': expense.description,
            },
        ]

        if expense.is_taxable and expense.tax_amount > 0:
            lines_data.append({
                'account_code': '115',
                'debit': expense.tax_amount,
                'credit': 0,
                'description': f'ضريبة مشتريات - {expense.description}',
            })

        lines_data.append({
            'account_code': '1111',
            'debit': 0,
            'credit': expense.total,
            'description': f'صرف - {expense.description}',
        })

        entry = JournalEngine.create_entry(
            source='expense',
            description=f'مصروف: {expense.description}',
            branch=expense.branch,
            lines_data=lines_data,
            source_document=expense.expense_number,
            user=user,
            auto_post=True,
        )

        expense.journal_entry = entry
        expense.status = 'paid'
        expense.approved_by = user
        expense.approved_at = timezone.now()
        expense.updated_by = user
        expense.save()
        return expense

    @classmethod
    def generate_recurring_expenses(cls, user=None):
        """
        توليد مصروفات دورية مستحقة
        يُشغل يومياً (cron job أو management command)
        """
        today = timezone.now().date()
        recurring = RecurringExpense.objects.filter(
            is_active=True,
            next_due_date__lte=today,
        )

        generated = []
        for rec in recurring:
            if rec.end_date and rec.end_date < today:
                rec.is_active = False
                rec.save()
                continue

            expense = cls.create_expense(
                category=rec.category,
                branch=rec.branch,
                description=f'{rec.name} - {today.strftime("%Y/%m")}',
                amount=rec.amount,
                supplier=rec.supplier,
                user=user,
            )

            if rec.auto_approve:
                cls.approve_and_pay_expense(expense, user=user)

            # تحديث تاريخ الاستحقاق القادم
            from dateutil.relativedelta import relativedelta
            freq_map = {
                'weekly': relativedelta(weeks=1),
                'monthly': relativedelta(months=1),
                'quarterly': relativedelta(months=3),
                'semi_annual': relativedelta(months=6),
                'annual': relativedelta(years=1),
            }
            rec.next_due_date = rec.next_due_date + freq_map.get(rec.frequency, relativedelta(months=1))
            rec.save()
            generated.append(expense)

        return generated


class VoucherEngine:
    """محرك سندات الصرف والقبض"""

    @staticmethod
    def _generate_payment_number():
        today = timezone.now()
        count = PaymentVoucher.objects.filter(date__year=today.year, date__month=today.month).count() + 1
        return f"PV-{today.strftime('%Y%m')}-{count:04d}"

    @staticmethod
    def _generate_receipt_number():
        today = timezone.now()
        count = ReceiptVoucher.objects.filter(date__year=today.year, date__month=today.month).count() + 1
        return f"RV-{today.strftime('%Y%m')}-{count:04d}"

    @classmethod
    @transaction.atomic
    def create_payment_voucher(cls, branch, beneficiary_type, amount, description,
                               debit_account, credit_account, payment_method='cash',
                               supplier=None, employee=None, customer=None,
                               beneficiary_name='', user=None):
        """إنشاء سند صرف"""
        voucher = PaymentVoucher.objects.create(
            voucher_number=cls._generate_payment_number(),
            date=timezone.now().date(),
            branch=branch,
            beneficiary_type=beneficiary_type,
            supplier=supplier,
            employee=employee,
            customer=customer,
            beneficiary_name=beneficiary_name,
            amount=amount,
            description=description,
            payment_method=payment_method,
            debit_account=debit_account,
            credit_account=credit_account,
            status='draft',
            created_by=user,
            updated_by=user,
        )
        return voucher

    @classmethod
    @transaction.atomic
    def approve_payment_voucher(cls, voucher, user=None):
        """اعتماد وتنفيذ سند صرف"""
        if voucher.status != 'draft':
            raise ValueError("السند ليس في حالة مسودة")

        lines_data = [
            {
                'account_code': voucher.debit_account.code,
                'debit': voucher.amount,
                'credit': 0,
                'description': voucher.description,
            },
            {
                'account_code': voucher.credit_account.code,
                'debit': 0,
                'credit': voucher.amount,
                'description': voucher.description,
            },
        ]

        entry = JournalEngine.create_entry(
            source='expense',
            description=f'سند صرف: {voucher.description}',
            branch=voucher.branch,
            lines_data=lines_data,
            source_document=voucher.voucher_number,
            user=user,
            auto_post=True,
        )

        voucher.journal_entry = entry
        voucher.status = 'paid'
        voucher.approved_by = user
        voucher.updated_by = user
        voucher.save()
        return voucher

    @classmethod
    @transaction.atomic
    def create_receipt_voucher(cls, branch, payer_type, amount, description,
                               debit_account, credit_account, payment_method='cash',
                               customer=None, payer_name='', invoice=None, user=None):
        """إنشاء سند قبض"""
        voucher = ReceiptVoucher.objects.create(
            voucher_number=cls._generate_receipt_number(),
            date=timezone.now().date(),
            branch=branch,
            payer_type=payer_type,
            customer=customer,
            payer_name=payer_name,
            amount=amount,
            description=description,
            payment_method=payment_method,
            debit_account=debit_account,
            credit_account=credit_account,
            invoice=invoice,
            status='draft',
            created_by=user,
            updated_by=user,
        )
        return voucher

    @classmethod
    @transaction.atomic
    def approve_receipt_voucher(cls, voucher, user=None):
        """اعتماد وتنفيذ سند قبض"""
        if voucher.status != 'draft':
            raise ValueError("السند ليس في حالة مسودة")

        lines_data = [
            {
                'account_code': voucher.debit_account.code,
                'debit': voucher.amount,
                'credit': 0,
                'description': voucher.description,
            },
            {
                'account_code': voucher.credit_account.code,
                'debit': 0,
                'credit': voucher.amount,
                'description': voucher.description,
            },
        ]

        entry = JournalEngine.create_entry(
            source='manual',
            description=f'سند قبض: {voucher.description}',
            branch=voucher.branch,
            lines_data=lines_data,
            source_document=voucher.voucher_number,
            user=user,
            auto_post=True,
        )

        voucher.journal_entry = entry
        voucher.status = 'received'
        voucher.approved_by = user
        voucher.updated_by = user
        voucher.save()

        # تحديث رصيد الفاتورة لو مرتبطة
        if voucher.invoice:
            from apps.sales.services.sales_engine import SalesEngine
            SalesEngine.record_payment(voucher.invoice, voucher.amount, user=user)

        return voucher


class PettyCashEngine:
    """محرك العهدة النثرية"""

    @classmethod
    @transaction.atomic
    def replenish(cls, petty_cash, amount, user=None):
        """تعبئة العهدة"""
        PettyCashTransaction.objects.create(
            petty_cash=petty_cash,
            date=timezone.now().date(),
            transaction_type='in',
            amount=amount,
            description=f'تعبئة عهدة {petty_cash.name}',
            created_by=user,
            updated_by=user,
        )
        petty_cash.current_balance += amount
        petty_cash.save()

        # قيد: من العهدة إلى الخزينة
        lines_data = [
            {'account_code': petty_cash.account.code, 'debit': amount, 'credit': 0,
             'description': f'تعبئة عهدة {petty_cash.name}'},
            {'account_code': '1111', 'debit': 0, 'credit': amount,
             'description': f'تعبئة عهدة {petty_cash.name}'},
        ]
        JournalEngine.create_entry(
            source='expense', description=f'تعبئة عهدة {petty_cash.name}',
            branch=petty_cash.branch, lines_data=lines_data, user=user, auto_post=True,
        )
        return petty_cash

    @classmethod
    @transaction.atomic
    def spend(cls, petty_cash, amount, description, category=None, receipt_image=None, user=None):
        """صرف من العهدة"""
        if amount > petty_cash.current_balance:
            raise ValueError(f"رصيد العهدة غير كافي! المتاح: {petty_cash.current_balance}")

        PettyCashTransaction.objects.create(
            petty_cash=petty_cash,
            date=timezone.now().date(),
            transaction_type='out',
            amount=amount,
            description=description,
            category=category,
            receipt_image=receipt_image,
            created_by=user,
            updated_by=user,
        )
        petty_cash.current_balance -= amount
        petty_cash.save()

        # قيد: من المصروف إلى العهدة
        expense_account = category.account.code if category else '619'
        lines_data = [
            {'account_code': expense_account, 'debit': amount, 'credit': 0, 'description': description},
            {'account_code': petty_cash.account.code, 'debit': 0, 'credit': amount, 'description': description},
        ]
        JournalEngine.create_entry(
            source='expense', description=f'صرف من عهدة {petty_cash.name}: {description}',
            branch=petty_cash.branch, lines_data=lines_data, user=user, auto_post=True,
        )
        return petty_cash
