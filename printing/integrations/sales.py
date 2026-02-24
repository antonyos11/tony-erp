"""
Sales module integration:
  - Auto-print invoice on posting
  - Receipt printing for POS
تكامل المبيعات:
  - طباعة تلقائية للفاتورة عند الترحيل
  - طباعة إيصال نقطة البيع
"""
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def auto_print_sales_invoice(invoice, user=None) -> Tuple[bool, str]:
    """
    Called when a sales invoice is posted.
    Generates A4 PDF and sends to the configured printer.
    """
    from printing.dispatch import PrintDispatcher
    from django.template.loader import render_to_string

    try:
        from core.models import Company
        company = Company.objects.first()
    except Exception:
        company = None

    items = invoice.items.select_related('product').all()

    html = render_to_string('sales/invoice_print_a4_new.html', {
        'invoice': invoice,
        'items': items,
        'company': company,
    })

    pdf_bytes = _render_html_to_pdf(html)
    if pdf_bytes:
        success, msg, job = PrintDispatcher.print_pdf(
            document_type='sales_invoice',
            pdf_bytes=pdf_bytes,
            title=f"فاتورة #{invoice.number}",
            user=user,
            source_app='sales',
            source_model='Invoice',
            source_id=str(invoice.pk),
        )
    else:
        success, msg, job = PrintDispatcher.print_html(
            document_type='sales_invoice',
            html=html,
            title=f"فاتورة #{invoice.number}",
            user=user,
            source_app='sales',
            source_model='Invoice',
            source_id=str(invoice.pk),
        )

    return success, msg


def print_pos_receipt(order, user=None) -> Tuple[bool, str]:
    """Print a POS thermal receipt."""
    from printing.dispatch import PrintDispatcher
    from django.template.loader import render_to_string

    template_name = 'pos/receipt_thermal.html'
    try:
        from django.template.loader import get_template
        get_template(template_name)
    except Exception:
        template_name = 'sales/invoice_print_thermal.html'

    html = render_to_string(template_name, {
        'order': order,
    })

    success, msg, job = PrintDispatcher.print_html(
        document_type='sales_receipt',
        html=html,
        title=f"إيصال POS #{order.id}",
        user=user,
        source_app='pos',
        source_model='POSOrder',
        source_id=str(order.pk),
    )
    return success, msg


def _render_html_to_pdf(html: str) -> Optional[bytes]:
    """Convert HTML to PDF using WeasyPrint (if available)."""
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except ImportError:
        logger.warning("WeasyPrint not installed; falling back to HTML printing.")
        return None
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None
