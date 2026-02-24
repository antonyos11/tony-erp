"""
Central Print Dispatch Service
خدمة إرسال الطباعة المركزية

كل الأنظمة تستدعي هذه الخدمة للطباعة. تقوم بـ:
  1. توجيه الطابعة حسب نوع المستند (document_type → printer config)
  2. إنشاء مهمة طباعة وإدراجها في الطابور
  3. إرسال عبر WebSocket إلى وكيل الطباعة
  4. توفير بديل (PDF تنزيل) عند عدم اتصال الوكيل
"""
import logging
import base64
from typing import Optional, Tuple, Dict, Any

from django.utils import timezone

from .models import PrinterConfiguration, UnifiedPrintJob

logger = logging.getLogger(__name__)


class PrintDispatcher:
    """Unified print dispatcher for all Tony ERP modules."""

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    @staticmethod
    def print_zpl(
        document_type: str,
        zpl_command: str,
        *,
        title: str = '',
        copies: int = 1,
        user=None,
        source_app: str = '',
        source_model: str = '',
        source_id: str = '',
        printer_id=None,
    ) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
        """Send ZPL to a Zebra printer."""
        printer = PrintDispatcher._resolve_printer(document_type, printer_id)
        if not printer:
            return False, f"لا توجد طابعة مُعدّة لنوع المستند '{document_type}'. اذهب إلى الإدارة ← إعداد الطابعات.", None

        job = UnifiedPrintJob.objects.create(
            document_type=document_type,
            printer=printer,
            zpl_command=zpl_command,
            title=title,
            copies=copies,
            source_app=source_app,
            source_model=source_model,
            source_id=str(source_id),
            requested_by=user,
        )

        success, msg = PrintDispatcher._dispatch(job)
        return success, msg, job

    @staticmethod
    def print_pdf(
        document_type: str,
        pdf_bytes: bytes,
        *,
        title: str = '',
        copies: int = 1,
        user=None,
        source_app: str = '',
        source_model: str = '',
        source_id: str = '',
        printer_id=None,
    ) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
        """Send a PDF to an A4 printer."""
        printer = PrintDispatcher._resolve_printer(document_type, printer_id)
        if not printer:
            return False, f"لا توجد طابعة مُعدّة لنوع المستند '{document_type}'.", None

        job = UnifiedPrintJob.objects.create(
            document_type=document_type,
            printer=printer,
            pdf_base64=base64.b64encode(pdf_bytes).decode('ascii'),
            title=title,
            copies=copies,
            source_app=source_app,
            source_model=source_model,
            source_id=str(source_id),
            requested_by=user,
        )

        success, msg = PrintDispatcher._dispatch(job)
        return success, msg, job

    @staticmethod
    def print_html(
        document_type: str,
        html: str,
        *,
        title: str = '',
        copies: int = 1,
        user=None,
        source_app: str = '',
        source_model: str = '',
        source_id: str = '',
        printer_id=None,
    ) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
        """Send HTML content to a printer (rendered by the agent)."""
        printer = PrintDispatcher._resolve_printer(document_type, printer_id)
        if not printer:
            return False, f"لا توجد طابعة مُعدّة لنوع المستند '{document_type}'.", None

        job = UnifiedPrintJob.objects.create(
            document_type=document_type,
            printer=printer,
            html_content=html,
            title=title,
            copies=copies,
            source_app=source_app,
            source_model=source_model,
            source_id=str(source_id),
            requested_by=user,
        )

        success, msg = PrintDispatcher._dispatch(job)
        return success, msg, job

    @staticmethod
    def print_escpos(
        document_type: str,
        raw_data: bytes,
        *,
        title: str = '',
        copies: int = 1,
        user=None,
        source_app: str = '',
        source_model: str = '',
        source_id: str = '',
        printer_id=None,
    ) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
        """Send raw ESC/POS data to a thermal printer."""
        printer = PrintDispatcher._resolve_printer(document_type, printer_id)
        if not printer:
            return False, f"لا توجد طابعة مُعدّة لنوع المستند '{document_type}'.", None

        job = UnifiedPrintJob.objects.create(
            document_type=document_type,
            printer=printer,
            escpos_data=raw_data,
            title=title,
            copies=copies,
            source_app=source_app,
            source_model=source_model,
            source_id=str(source_id),
            requested_by=user,
        )

        success, msg = PrintDispatcher._dispatch(job)
        return success, msg, job

    @staticmethod
    def reprint(job_id: str, user=None) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
        """Reprint an existing job (creates a new job with same payload)."""
        try:
            original = UnifiedPrintJob.objects.get(pk=job_id)
        except UnifiedPrintJob.DoesNotExist:
            return False, "مهمة الطباعة غير موجودة.", None

        new_job = UnifiedPrintJob.objects.create(
            document_type=original.document_type,
            printer=original.printer,
            zpl_command=original.zpl_command,
            escpos_data=original.escpos_data,
            pdf_base64=original.pdf_base64,
            html_content=original.html_content,
            title=f"[إعادة طباعة] {original.title}",
            copies=original.copies,
            source_app=original.source_app,
            source_model=original.source_model,
            source_id=original.source_id,
            requested_by=user,
        )

        success, msg = PrintDispatcher._dispatch(new_job)
        return success, msg, new_job

    @staticmethod
    def get_agent_status() -> Dict[str, Any]:
        """Check if the print agent is connected."""
        try:
            from printing.models import PrintStation
            online_stations = PrintStation.objects.filter(
                is_active=True, is_online=True
            ).count()
            if online_stations > 0:
                return {
                    'online': True,
                    'online_stations': online_stations,
                    'channel_layer': 'active',
                }
            return {
                'online': False,
                'reason': 'لا يوجد وكيل طباعة متصل بالخادم',
                'online_stations': 0,
            }
        except Exception as e:
            return {'online': False, 'reason': str(e)}

    # ──────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────

    # Document type aliases — maps similar/related types to each other
    _DOC_TYPE_ALIASES = {
        'sales_receipt': ['generic_receipt', 'sales_receipt'],
        'generic_receipt': ['sales_receipt', 'generic_receipt'],
        'production_barcode': ['product_barcode', 'barcode', 'production_barcode'],
        'product_barcode': ['production_barcode', 'barcode', 'product_barcode'],
        'barcode': ['product_barcode', 'production_barcode', 'barcode'],
        'warranty_label': ['production_barcode', 'product_barcode', 'barcode', 'warranty_label'],
        'sales_invoice': ['generic_a4', 'sales_invoice'],
        'purchase_order': ['generic_a4', 'purchase_order'],
        'journal_entry': ['generic_a4', 'trial_balance', 'journal_entry'],
        'trial_balance': ['generic_a4', 'journal_entry', 'trial_balance'],
    }

    @staticmethod
    def _resolve_printer(document_type: str, printer_id=None) -> Optional[PrinterConfiguration]:
        """Find the right printer for a document type, with alias fallback."""
        if printer_id:
            try:
                return PrinterConfiguration.objects.get(pk=printer_id, is_active=True)
            except PrinterConfiguration.DoesNotExist:
                pass

        # Find default printer for this document type
        printer = PrinterConfiguration.objects.filter(
            document_type=document_type,
            is_active=True,
            is_default=True,
        ).first()

        if not printer:
            # Fallback: any active printer for this document type
            printer = PrinterConfiguration.objects.filter(
                document_type=document_type,
                is_active=True,
            ).first()

        # Alias fallback — try related document types
        if not printer:
            aliases = PrintDispatcher._DOC_TYPE_ALIASES.get(document_type, [])
            for alias in aliases:
                printer = PrinterConfiguration.objects.filter(
                    document_type=alias,
                    is_active=True,
                ).first()
                if printer:
                    logger.info(
                        f"Printer resolved via alias: {document_type} → {alias} → {printer.name}"
                    )
                    break

        return printer

    @staticmethod
    def _dispatch(job: UnifiedPrintJob) -> Tuple[bool, str]:
        """Send the job to the print agent via Channels WebSocket.
        
        Tries station-specific groups first (agents connected to Daphne),
        then falls back to the global broadcast group.
        If no agent is online, queues the job for later delivery.
        """
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer is None:
                job.status = 'failed'
                job.error_message = 'لا يوجد channel layer مُعدّ'
                job.save(update_fields=['status', 'error_message'])
                return False, 'وكيل الطباعة غير متاح (لا يوجد channel layer). قم بتنزيل الملف بدلاً من ذلك.'

            # Build the message payload for the agent
            payload = {
                'job_id': str(job.id),
                'document_type': job.document_type,
                'copies': job.copies,
                'title': job.title,
            }

            # Determine the action based on what's in the job
            if job.zpl_command:
                payload['action'] = 'print_zebra_zpl'
                payload['zpl'] = job.zpl_command
            elif job.pdf_base64:
                payload['action'] = 'print_a4'
                payload['pdf_base64'] = job.pdf_base64
            elif job.html_content:
                payload['action'] = 'print_a4'
                payload['html'] = job.html_content
            elif job.escpos_data:
                payload['action'] = 'print_thermal_receipt'
                payload['raw_base64'] = base64.b64encode(bytes(job.escpos_data)).decode('ascii')
            else:
                job.status = 'failed'
                job.error_message = 'لا يوجد محتوى قابل للطباعة في المهمة'
                job.save(update_fields=['status', 'error_message'])
                return False, 'لا يوجد محتوى قابل للطباعة'

            # Add printer connection info (generic fallback — overridden per-station below)
            generic_printer_name = ''
            if job.printer:
                generic_printer_name = job.printer.cups_printer_name or job.printer.shared_printer_name or job.printer.name
                payload['printer_name'] = generic_printer_name
                if job.printer.ip_address:
                    payload['ip'] = str(job.printer.ip_address)
                    payload['port'] = job.printer.port

            # --- Check if any agent is actually online ---
            from printing.models import PrintStation, PrinterMapping
            online_stations = list(
                PrintStation.objects.filter(
                    is_active=True, is_online=True
                )
            )

            if online_stations:
                # Resolve the list of document_type aliases to try
                doc_types_to_try = [job.document_type]
                aliases = PrintDispatcher._DOC_TYPE_ALIASES.get(job.document_type, [])
                for alias in aliases:
                    if alias not in doc_types_to_try:
                        doc_types_to_try.append(alias)

                sent_to = []
                for station in online_stations:
                    # Look up PrinterMapping to get the LOCAL printer name on this station
                    mapping = None
                    for dt in doc_types_to_try:
                        mapping = PrinterMapping.objects.filter(
                            station=station,
                            document_type=dt,
                            is_enabled=True,
                        ).exclude(local_printer_name='').order_by('-priority').first()
                        if mapping:
                            break

                    # Build station-specific payload
                    station_payload = dict(payload)  # shallow copy
                    if mapping:
                        station_payload['printer_name'] = mapping.local_printer_name
                        station_payload['copies'] = mapping.copies or job.copies
                        logger.info(
                            f"Station {station.machine_name}: "
                            f"mapped '{job.document_type}' → '{mapping.local_printer_name}'"
                        )
                    else:
                        logger.warning(
                            f"Station {station.machine_name}: "
                            f"no mapping for '{job.document_type}', "
                            f"using generic '{generic_printer_name}'"
                        )

                    async_to_sync(channel_layer.group_send)(
                        f"print_station_{station.machine_name}",
                        {'type': 'print.command', 'data': station_payload},
                    )
                    sent_to.append(station.machine_name)

                job.status = 'sent'
                job.sent_at = timezone.now()
                job.save(update_fields=['status', 'sent_at'])

                if job.printer:
                    job.printer.increment_print_count()

                logger.info(f"Print job dispatched: {job.id} → {sent_to}")
                return True, f"تم إرسال مهمة الطباعة إلى {job.printer.name if job.printer else 'الوكيل'}"
            else:
                # No station online — queue for later
                job.status = 'queued'
                job.error_message = 'لا يوجد وكيل طباعة متصل حالياً — المهمة في الانتظار'
                job.save(update_fields=['status', 'error_message'])
                logger.warning(f"Print job queued (no agent online): {job.id}")
                return False, 'الوكيل غير متصل — المهمة محفوظة وسيتم طباعتها عند اتصال الوكيل.'

        except Exception as e:
            logger.error(f"Failed to dispatch print job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.save(update_fields=['status', 'error_message'])
            return False, f"فشل إرسال مهمة الطباعة: {e}"

    @staticmethod
    def confirm_completed(job_id: str) -> bool:
        """Called by the print agent consumer when printing succeeds."""
        try:
            job = UnifiedPrintJob.objects.get(pk=job_id)
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'completed_at'])
            return True
        except UnifiedPrintJob.DoesNotExist:
            return False

    @staticmethod
    def mark_failed(job_id: str, error: str) -> bool:
        """Called by the print agent consumer when printing fails."""
        try:
            job = UnifiedPrintJob.objects.get(pk=job_id)
            job.status = 'failed'
            job.error_message = error
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'error_message', 'completed_at'])

            if job.printer:
                PrinterConfiguration.objects.filter(pk=job.printer_id).update(
                    last_error=error
                )
            return True
        except UnifiedPrintJob.DoesNotExist:
            return False
