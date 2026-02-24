"""
Purchases module integration:
  - Auto-print Purchase Order on posting/approval
تكامل المشتريات:
  - طباعة تلقائية لأمر الشراء عند التأكيد/الموافقة
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def auto_print_purchase_order(purchase_order, user=None) -> Tuple[bool, str]:
    """
    Called when a purchase order is approved/posted.
    Generates A4 PDF and sends to the configured printer.
    """
    from printing.dispatch import PrintDispatcher
    from django.template.loader import render_to_string

    try:
        from core.models import Company
        company = Company.objects.first()
    except Exception:
        company = None

    html = render_to_string('printing/po_print_a4.html', {
        'po': purchase_order,
        'items': purchase_order.items.select_related('product').all(),
        'company': company,
    })

    pdf_bytes = _try_pdf(html)
    if pdf_bytes:
        success, msg, job = PrintDispatcher.print_pdf(
            document_type='purchase_order',
            pdf_bytes=pdf_bytes,
            title=f"أمر شراء #{purchase_order.number}",
            user=user,
            source_app='purchases',
            source_model='PurchaseOrder',
            source_id=str(purchase_order.pk),
        )
    else:
        success, msg, job = PrintDispatcher.print_html(
            document_type='purchase_order',
            html=html,
            title=f"أمر شراء #{purchase_order.number}",
            user=user,
            source_app='purchases',
            source_model='PurchaseOrder',
            source_id=str(purchase_order.pk),
        )

    return success, msg


def _try_pdf(html: str):
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception:
        return None
