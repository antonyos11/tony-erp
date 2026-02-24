"""
ZATCA E-Invoice Auto-generation Signal
عند حفظ فاتورة مبيعات، يتم إنشاء فاتورة إلكترونية تلقائياً وتوليد QR Code و Hash
"""
import uuid
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='sales.Invoice')
def auto_create_einvoice(sender, instance, created, **kwargs):
    """إنشاء فاتورة إلكترونية تلقائياً عند إنشاء فاتورة مبيعات"""
    if not created:
        return

    try:
        from zatca_integration.models import EInvoice, ZATCAConfiguration

        # تحقق من وجود إعدادات ZATCA نشطة
        try:
            config = ZATCAConfiguration.objects.filter(is_active=True).first()
            if not config:
                logger.debug('ZATCA: No active configuration found, skipping e-invoice generation')
                return
        except Exception:
            return

        # تأكد من عدم وجود فاتورة إلكترونية مسبقة
        if EInvoice.objects.filter(invoice=instance).exists():
            return

        # تحديد العداد التالي
        last_counter = EInvoice.objects.order_by('-invoice_counter').values_list('invoice_counter', flat=True).first()
        next_counter = (last_counter or 0) + 1

        # تحديد نوع الفاتورة
        invoice_type = 'B2C'  # افتراضي: فاتورة ضريبية مبسطة
        total_val = getattr(instance, 'total', 0) or 0
        if hasattr(total_val, '__call__'):
            try:
                total_val = total_val()
            except Exception:
                total_val = 0
        if float(total_val) > 1000:
            invoice_type = 'B2B'  # فاتورة ضريبية كاملة للمبالغ الكبيرة

        # الحصول على hash الفاتورة السابقة
        previous_hash = ''
        last_einvoice = EInvoice.objects.order_by('-created_at').first()
        if last_einvoice:
            previous_hash = last_einvoice.invoice_hash or ''

        # إنشاء الفاتورة الإلكترونية
        einvoice = EInvoice.objects.create(
            invoice=instance,
            uuid=uuid.uuid4(),
            invoice_counter=next_counter,
            invoice_type=invoice_type,
            previous_invoice_hash=previous_hash,
            status='draft',
        )

        # توليد Hash
        try:
            einvoice.generate_hash()
        except Exception as e:
            logger.warning(f'ZATCA: Failed to generate hash for invoice {instance.pk}: {e}')

        # توليد QR Code
        try:
            einvoice.generate_qr_code()
        except Exception as e:
            logger.warning(f'ZATCA: Failed to generate QR code for invoice {instance.pk}: {e}')

        # توليد XML
        try:
            einvoice.generate_xml_invoice()
        except Exception as e:
            logger.warning(f'ZATCA: Failed to generate XML for invoice {instance.pk}: {e}')

        logger.info(f'ZATCA: E-invoice created for invoice {instance.pk} (counter={next_counter})')

    except Exception as e:
        # لا نعرقل حفظ الفاتورة الأصلية بسبب خطأ في ZATCA
        logger.error(f'ZATCA: Error auto-creating e-invoice for invoice {instance.pk}: {e}')
