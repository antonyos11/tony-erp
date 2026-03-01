"""
تنسيق الطابعة الحرارية 80mm — RITA ERP
"""
from __future__ import annotations

from django.utils import timezone


THERMAL_WIDTH = 42          # عدد الأحرف في السطر الواحد (80mm ~ 42 char)
SEPARATOR     = '-' * THERMAL_WIDTH
DOUBLE_SEP    = '=' * THERMAL_WIDTH


def _center(text: str, width: int = THERMAL_WIDTH) -> str:
    return text.center(width)


def _left_right(left: str, right: str, width: int = THERMAL_WIDTH) -> str:
    gap = width - len(left) - len(right)
    return f'{left}{" " * max(gap, 1)}{right}'


def format_receipt_text(invoice, payment=None, company: dict | None = None) -> str:
    """
    تنسيق إيصال قبض نصي للطابعة الحرارية 80mm.
    إرجاع: نص عادي يُرسَل مباشرةً للطابعة.
    """
    company = company or {}
    lines = []

    lines.append(DOUBLE_SEP)
    lines.append(_center(company.get('name', 'RITA ERP')))
    if company.get('address'):
        lines.append(_center(company['address']))
    if company.get('phone'):
        lines.append(_center(f"هاتف: {company['phone']}"))
    lines.append(SEPARATOR)

    lines.append(_center('إيصال قبض'))
    lines.append(SEPARATOR)

    lines.append(_left_right('الفاتورة:', str(invoice.invoice_number)))
    lines.append(_left_right('العميل:', str(getattr(invoice, 'customer', '') or '')))
    lines.append(_left_right('التاريخ:', str(invoice.invoice_date)))
    lines.append(SEPARATOR)

    # بنود الفاتورة
    for line in invoice.lines.select_related('product').all():
        product_name = str(line.product)[:20]
        qty_price    = f'{line.quantity} × {line.unit_price:.2f}'
        total        = f'{line.total_price:.2f}'
        lines.append(_left_right(product_name, qty_price))
        lines.append(_left_right('', total))

    lines.append(SEPARATOR)

    if hasattr(invoice, 'subtotal'):
        lines.append(_left_right('المجموع:', f'{invoice.subtotal:.2f}'))
    if hasattr(invoice, 'discount_amount') and invoice.discount_amount:
        lines.append(_left_right('الخصم:', f'-{invoice.discount_amount:.2f}'))
    if hasattr(invoice, 'tax_amount') and invoice.tax_amount:
        lines.append(_left_right('الضريبة:', f'{invoice.tax_amount:.2f}'))

    lines.append(DOUBLE_SEP)
    lines.append(_left_right('الإجمالي:', f'{invoice.total_amount:.2f}'))
    lines.append(DOUBLE_SEP)

    if payment:
        lines.append(_left_right('المدفوع:', f'{payment.amount:.2f}'))
        change = float(payment.amount) - float(invoice.total_amount)
        if change >= 0:
            lines.append(_left_right('الباقي:', f'{change:.2f}'))

    lines.append(SEPARATOR)
    lines.append(_center('شكراً لتعاملكم معنا'))
    lines.append(_center(timezone.now().strftime('%Y-%m-%d %H:%M')))
    lines.append(DOUBLE_SEP)

    return '\n'.join(lines)


def format_invoice_thermal(invoice, company: dict | None = None) -> str:
    """
    تنسيق فاتورة بيع للطابعة الحرارية 80mm.
    """
    company = company or {}
    lines   = []

    lines.append(DOUBLE_SEP)
    lines.append(_center(company.get('name', 'RITA ERP')))
    if company.get('tax_number'):
        lines.append(_center(f"الرقم الضريبي: {company['tax_number']}"))
    lines.append(SEPARATOR)

    lines.append(_center('فاتورة بيع'))
    lines.append(SEPARATOR)
    lines.append(_left_right('رقم الفاتورة:', str(invoice.invoice_number)))
    lines.append(_left_right('التاريخ:', str(invoice.invoice_date)))
    lines.append(_left_right('العميل:', str(getattr(invoice, 'customer', '') or '')))
    lines.append(SEPARATOR)

    header = _left_right('الصنف', 'الكمية × السعر')
    lines.append(header)
    lines.append(SEPARATOR)

    for item in invoice.lines.select_related('product').all():
        name     = str(item.product)[:22]
        detail   = f'{item.quantity}×{item.unit_price:.2f}={item.total_price:.2f}'
        lines.append(_left_right(name, detail))

    lines.append(DOUBLE_SEP)
    lines.append(_left_right('الإجمالي:', f'{invoice.total_amount:.2f}'))
    lines.append(DOUBLE_SEP)

    return '\n'.join(lines)
