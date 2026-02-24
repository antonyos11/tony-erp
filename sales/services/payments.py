from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass
from django.utils import timezone
from django.db import transaction
from typing import Optional

from sales.models import InvoicePayment, Invoice
from accounting.models import AccountingSettings, JournalEntry, JournalEntryItem, Account
from django.contrib.auth import get_user_model

User = get_user_model()

@dataclass
class PaymentCreateResult:
    payment: InvoicePayment
    posted: bool


def _resolve_cash_account(settings_obj: AccountingSettings, payment_method) -> Account:
    # TODO: لاحقاً دعم حسابات متعددة حسب نوع الطريقة (بنك/صندوق/شيك)
    if settings_obj.cash_account is None:
        raise ValueError('لم يتم ضبط حساب النقدية/البنك في إعدادات المحاسبة')
    return settings_obj.cash_account


def create_payment(*, invoice: Optional[Invoice], customer, amount: Decimal, payment_method, reference: str, description: str, user, auto_post: bool = True) -> PaymentCreateResult:
    if amount <= 0:
        raise ValueError('المبلغ يجب أن يكون أكبر من صفر')
    pay = InvoicePayment.objects.create(
        invoice=invoice,
        customer=customer,
        amount=amount,
        payment_method=payment_method,
        reference=reference,
        description=description,
        created_by=user,
        status='draft',
    )
    posted = False
    if auto_post:
        post_payment(pay, user)
        posted = True
    return PaymentCreateResult(payment=pay, posted=posted)


def post_payment(payment: InvoicePayment, user) -> InvoicePayment:
    if payment.status != 'draft':
        return payment
    settings_obj = AccountingSettings.get()
    cash_acc = _resolve_cash_account(settings_obj, payment.payment_method)
    if payment.invoice_id:
        credit_acc = settings_obj.ar_account
        if credit_acc is None:
            raise ValueError('لم يتم ضبط حساب العملاء في إعدادات المحاسبة')
        payment.is_advance = False
    else:
        credit_acc = settings_obj.customer_advances_account
        if credit_acc is None:
            raise ValueError('لم يتم ضبط حساب سلف العملاء في إعدادات المحاسبة')
        payment.is_advance = True

    with transaction.atomic():
        je = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=f'Receipt {payment.receipt_number or ''}',
            entry_type='payment',
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
        )
        JournalEntryItem.objects.bulk_create([
            JournalEntryItem(journal_entry=je, account=cash_acc, type='debit', amount=payment.amount),
            JournalEntryItem(journal_entry=je, account=credit_acc, type='credit', amount=payment.amount),
        ])
        payment.journal_entry = je
        payment.status = 'posted'
        payment.posted_at = timezone.now()
        payment.posted_by = user
        payment.save(update_fields=['journal_entry','status','posted_at','posted_by','is_advance'])
    return payment


def cancel_payment(payment: InvoicePayment, user, reason: str = '') -> InvoicePayment:
    if payment.status != 'posted':
        raise ValueError('لا يمكن إلغاء دفعة غير مرحلة')
    if not payment.journal_entry_id:
        raise ValueError('لا يوجد قيد مرتبط بهذه الدفعة لإلغائه')
    if payment.reverse_journal_entry_id:
        return payment  # already cancelled

    settings_obj = AccountingSettings.get()
    with transaction.atomic():
        orig_je = payment.journal_entry
        # إنشاء قيد عكسي (دائن يصبح مدين والعكس) بنفس التاريخ الحالي
        reverse_desc = f"عكس دفعة {payment.receipt_number or payment.id} {reason}".strip()
        rev_je = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=reverse_desc,
            entry_type='payment',
            created_by=user,
            is_posted=True,
        )
        # عكس البنود
        orig_items = list(orig_je.items.all())  # type: ignore[attr-defined]
        rev_items = []
        for it in orig_items:
            rev_items.append(JournalEntryItem(
                journal_entry=rev_je,
                account=it.account,
                type='debit' if it.type == 'credit' else 'credit',
                amount=it.amount,
                description=f"عكس {it.id}"
            ))
        JournalEntryItem.objects.bulk_create(rev_items)
        # تحديث حالة الدفعة
        payment.status = 'cancelled'
        payment.reverse_journal_entry = rev_je
        payment.save(update_fields=['status','reverse_journal_entry'])
    return payment
