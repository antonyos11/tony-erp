"""
خدمة طباعة الفواتير والإيصالات — RITA ERP
"""
from __future__ import annotations

from django.template.loader import render_to_string
from django.utils import timezone

from apps.printing.models import PrintTemplate


def _get_default_template(template_type: str) -> PrintTemplate | None:
    """جلب القالب الافتراضي لنوع معيَّن."""
    return PrintTemplate.objects.filter(
        template_type=template_type,
        is_default=True,
        is_deleted=False,
    ).first()


def render_invoice_html(invoice, paper_size: str = 'a4') -> str:
    """
    تصيير HTML لفاتورة بيع.
    invoice: مثيل SalesInvoice
    paper_size: 'a4' | 'a5' | 'thermal_80'
    """
    template = _get_default_template('invoice')

    context = {
        'invoice':    invoice,
        'lines':      invoice.lines.select_related('product').all(),
        'company':    _get_company_info(),
        'paper_size': paper_size,
        'printed_at': timezone.now(),
    }

    if template and template.html_content:
        from django.template import Context, Template
        t = Template(template.html_content)
        c = Context(context)
        return t.render(c)

    # قالب افتراضي مدمَج
    return render_to_string('printing/invoice_default.html', context)


def render_receipt_html(invoice, payment=None, paper_size: str = 'thermal_80') -> str:
    """
    تصيير HTML لإيصال قبض.
    invoice: مثيل SalesInvoice
    payment: مثيل Payment اختياري
    """
    template = _get_default_template('receipt')

    context = {
        'invoice':    invoice,
        'payment':    payment,
        'company':    _get_company_info(),
        'paper_size': paper_size,
        'printed_at': timezone.now(),
    }

    if template and template.html_content:
        from django.template import Context, Template
        t = Template(template.html_content)
        c = Context(context)
        return t.render(c)

    return render_to_string('printing/receipt_default.html', context)


def _get_company_info() -> dict:
    """جلب بيانات الشركة من الإعدادات."""
    try:
        from apps.core.models import Company
        company = Company.objects.first()
        if company:
            return {
                'name':    company.name,
                'address': getattr(company, 'address', ''),
                'phone':   getattr(company, 'phone', ''),
                'tax_number': getattr(company, 'tax_number', ''),
            }
    except Exception:
        pass
    return {'name': 'RITA ERP', 'address': '', 'phone': '', 'tax_number': ''}
