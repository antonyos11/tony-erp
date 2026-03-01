"""
محرك ضريبة القيمة المضافة
يحسب الضريبة ويسجلها تلقائياً
"""
from decimal import Decimal, ROUND_HALF_UP
from apps.accounts.models import TaxTransaction


class VATEngine:
    """محرك ضريبة القيمة المضافة 14%"""

    DEFAULT_RATE = Decimal('14.00')

    @classmethod
    def calculate_tax(cls, amount, rate=None, price_includes_tax=False):
        """
        حساب الضريبة

        amount: المبلغ
        rate: نسبة الضريبة (افتراضي 14%)
        price_includes_tax: هل السعر شامل الضريبة؟

        Returns: dict {amount_before_tax, tax_amount, total}
        """
        rate = rate or cls.DEFAULT_RATE
        amount = Decimal(str(amount))

        if price_includes_tax:
            # السعر شامل الضريبة — نستخرج الضريبة منه
            amount_before_tax = (amount / (1 + rate / 100)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            tax_amount = amount - amount_before_tax
        else:
            # السعر قبل الضريبة — نضيف الضريبة عليه
            amount_before_tax = amount
            tax_amount = (amount * rate / 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        return {
            'amount_before_tax': amount_before_tax,
            'tax_amount': tax_amount,
            'total': amount_before_tax + tax_amount,
            'rate': rate,
        }

    @classmethod
    def record_tax_transaction(cls, tax_type, amount_before_tax, tax_amount,
                               journal_entry, is_taxable_purchase=True,
                               is_taxable_sale=True, rate=None):
        """
        تسجيل حركة ضريبية
        """
        rate = rate or cls.DEFAULT_RATE

        return TaxTransaction.objects.create(
            tax_type=tax_type,
            date=journal_entry.date,
            amount_before_tax=amount_before_tax,
            tax_rate=rate,
            tax_amount=tax_amount,
            journal_entry=journal_entry,
            is_taxable_purchase=is_taxable_purchase,
            is_taxable_sale=is_taxable_sale,
        )

    @classmethod
    def get_vat_summary(cls, start_date, end_date):
        """
        ملخص الضريبة لفترة معينة (للإقرار الضريبي)
        """
        from django.db.models import Sum

        input_tax = TaxTransaction.objects.filter(
            tax_type='input',
            date__range=[start_date, end_date],
        ).aggregate(
            total=Sum('tax_amount'),
            base=Sum('amount_before_tax'),
        )

        output_tax = TaxTransaction.objects.filter(
            tax_type='output',
            date__range=[start_date, end_date],
        ).aggregate(
            total=Sum('tax_amount'),
            base=Sum('amount_before_tax'),
        )

        input_total  = input_tax['total']  or Decimal('0')
        output_total = output_tax['total'] or Decimal('0')

        return {
            'period': f'{start_date} - {end_date}',
            'input_tax': {
                'base_amount': input_tax['base'] or Decimal('0'),
                'tax_amount':  input_total,
            },
            'output_tax': {
                'base_amount': output_tax['base'] or Decimal('0'),
                'tax_amount':  output_total,
            },
            'net_payable': output_total - input_total,   # موجب = مستحق، سالب = مسترد
            'status': 'مستحق الدفع' if output_total > input_total else 'مستحق الاسترداد',
        }
