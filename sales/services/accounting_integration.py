"""
Sales Accounting Integration Service
Handles journal entry creation from invoices and sales transactions
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from typing import Optional

from sales.models import Invoice
from accounting.models import AccountingSettings, JournalEntry, JournalEntryItem, Account


def post_invoice_to_accounting(invoice: Invoice, user, description: str = '') -> Optional[JournalEntry]:
    """
    Create journal entry from invoice
    Debit: Accounts Receivable (AR)
    Credit: Sales Revenue (or Inventory Account as fallback)
    Credit: Tax Payable (if applicable)
    """
    if not invoice or invoice.total <= 0:
        return None
    
    settings = AccountingSettings.get()
    
    # Validate required accounts
    if not settings.ar_account:
        raise ValueError('لم يتم ضبط حساب العملاء (AR) في إعدادات المحاسبة')
    
    # Find sales revenue account (code 4xxx or type 'revenue')
    sales_revenue_account = Account.objects.filter(
        account_type='revenue'
    ).filter(
        code__startswith='4'
    ).first()
    
    if not sales_revenue_account:
        # Fallback: try to find any revenue account
        sales_revenue_account = Account.objects.filter(account_type='revenue').first()
    
    if not sales_revenue_account:
        # Last fallback: use inventory account if available
        if settings.inventory_account:
            sales_revenue_account = settings.inventory_account
        else:
            raise ValueError('لم يتم العثور على حساب إيرادات المبيعات. يرجى إنشاء حساب من نوع "revenue" برقم 4xxx')
    
    total_amount = invoice.total
    discount_amount = invoice.discount or Decimal('0')
    
    # Calculate subtotal before tax  
    items_subtotal = sum(item.quantity * item.price for item in invoice.items.all())  # type: ignore[attr-defined]
    
    # Calculate tax amount
    tax_amount = Decimal('0')
    if invoice.is_tax_inclusive:
        # If tax is inclusive, extract tax from total
        # Assuming 14% VAT (Egypt standard)
        tax_rate = Decimal('0.14')
        # Total = Subtotal + (Subtotal * tax_rate)
        # Total = Subtotal * (1 + tax_rate)
        # Subtotal = Total / (1 + tax_rate)
        subtotal_before_tax = total_amount / (Decimal('1') + tax_rate)
        tax_amount = total_amount - subtotal_before_tax
    else:
        # Tax is not included or zero
        tax_amount = Decimal('0')
    
    with transaction.atomic():
        # Create journal entry
        je_description = description or f'فاتورة بيع رقم {invoice.number} - {invoice.customer.name}'
        
        je = JournalEntry.objects.create(
            date=invoice.date or timezone.now().date(),
            description=je_description,
            entry_type='invoice',
            created_by=user,
            is_posted=True,
            posted_at=timezone.now(),
        )
        
        # Debit AR for full invoice total
        JournalEntryItem.objects.create(
            journal_entry=je,
            account=settings.ar_account,
            type='debit',
            amount=total_amount,
            description=f'العميل: {invoice.customer.name}'
        )
        
        # Credit Sales Revenue (subtotal minus discount)
        sales_amount = items_subtotal - discount_amount
        if sales_amount > 0:
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=sales_revenue_account,
                type='credit',
                amount=sales_amount,
                description='إيرادات مبيعات'
            )
        
        # Credit Tax Payable if applicable (use vat_output_account)
        if tax_amount > 0 and settings.vat_output_account:
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=settings.vat_output_account,
                type='credit',
                amount=tax_amount,
                description='ضريبة القيمة المضافة'
            )
        
        return je


def reverse_invoice_accounting(invoice: Invoice, user, reason: str = '') -> Optional[JournalEntry]:
    """
    Create reversing journal entry for invoice (when invoice is deleted/cancelled)
    """
    # This would find the original JE and reverse it
    # For now, return None as we need to link JE to Invoice first
    return None
