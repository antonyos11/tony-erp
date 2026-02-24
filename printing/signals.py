"""
Django signals to trigger automatic printing when documents are posted.
إشارات Django لتفعيل الطباعة التلقائية عند ترحيل المستندات.

Covers:
  - Sales invoices → A4 printer on posting
  - Production packaging → Zebra barcode labels on completion
  - POS orders → Thermal receipt on payment
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# A. Sales Invoice auto-print on posting
# ──────────────────────────────────────────

@receiver(post_save, sender='sales.Invoice')
def auto_print_invoice_on_post(sender, instance, **kwargs):
    """Auto-print sales invoice when it's marked as posted."""
    if not kwargs.get('created', False) and getattr(instance, 'is_posted', False):
        update_fields = kwargs.get('update_fields')
        if update_fields and 'is_posted' in update_fields:
            try:
                from printing.integrations.sales import auto_print_sales_invoice
                success, msg = auto_print_sales_invoice(instance)
                if success:
                    logger.info(f"Auto-printed invoice #{instance.number}")
                else:
                    logger.warning(f"Auto-print failed for invoice #{instance.number}: {msg}")
            except Exception as e:
                logger.error(f"Auto-print error for invoice #{instance.number}: {e}")


# ──────────────────────────────────────────
# B. Production – barcode on packaging complete
# ──────────────────────────────────────────

@receiver(post_save, sender='production.PipelineStageEntry')
def auto_print_on_packaging_complete(sender, instance, **kwargs):
    """Auto-print barcode when packaging stage completes."""
    update_fields = kwargs.get('update_fields')

    # Only trigger when status changes
    if update_fields and 'status' not in update_fields:
        return
    if getattr(instance, 'status', '') != 'completed':
        return

    # Check if this is the packaging stage
    stage_name = ''
    if hasattr(instance, 'work_center') and instance.work_center:
        stage_name = (instance.work_center.name or '').lower()
    elif hasattr(instance, 'stage') and instance.stage:
        stage_name = (getattr(instance.stage, 'name', '') or '').lower()

    packaging_keywords = ('packaging', 'تغليف', 'pack', 'packing')
    if not any(kw in stage_name for kw in packaging_keywords):
        return

    try:
        from printing.integrations.production import on_packaging_complete
        user = getattr(instance, 'completed_by', None)
        success, msg = on_packaging_complete(instance, user)
        if success:
            logger.info(f"Auto-printed barcode for stage entry #{instance.pk}")
        else:
            logger.warning(f"Barcode auto-print failed: {msg}")
    except Exception as e:
        logger.error(f"Barcode auto-print error: {e}")


# ──────────────────────────────────────────
# C. POS – auto-print receipt on payment
# ──────────────────────────────────────────

@receiver(post_save, sender='pos.POSOrder')
def auto_print_pos_receipt(sender, instance, **kwargs):
    """Auto-print POS receipt when order status becomes 'paid' or 'completed'."""
    update_fields = kwargs.get('update_fields')

    status = getattr(instance, 'status', '')
    if status not in ('paid', 'completed', 'مكتمل'):
        return

    # Only trigger on status change, not on every save
    if update_fields and 'status' not in update_fields:
        return

    # Avoid double-print: check if receipt was already printed
    from printing.models import UnifiedPrintJob
    already_printed = UnifiedPrintJob.objects.filter(
        source_app='pos',
        source_model='POSOrder',
        source_id=str(instance.pk),
        document_type='sales_receipt',
        status__in=['sent', 'printing', 'completed'],
    ).exists()

    if already_printed:
        return

    try:
        from pos.print_service import print_pos_receipt
        user = getattr(instance, 'cashier', None) or getattr(instance, 'created_by', None)
        success, msg, job = print_pos_receipt(instance, user=user)
        if success:
            logger.info(f"Auto-printed POS receipt for order #{instance.pk}")
        else:
            logger.warning(f"POS receipt auto-print failed: {msg}")
    except Exception as e:
        logger.error(f"POS receipt auto-print error: {e}")
