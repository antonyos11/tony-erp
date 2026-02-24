"""
printing/print_service.py — Global Intelligent Print Router
============================================================
خدمة الطباعة الذكية — نقطة الدخول الموحدة لجميع عمليات الطباعة

All modules should call PrintService instead of PrintManager directly.

Flow:
  1. Caller says: PrintService.print(document_type, payload, request_or_user)
  2. PrintService detects the user's station (from middleware / session / IP)
  3. Looks up the PrinterMapping for (station, document_type)
  4. Routes to the correct agent + printer via Channels WebSocket
  5. Falls back to PrintDispatcher legacy routing if no station mapping exists
"""

import base64
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class PrintService:
    """
    Unified entry point for ALL printing across Tony ERP.
    نقطة الدخول الموحدة لجميع عمليات الطباعة.
    """

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    @staticmethod
    def print_barcode(
        zpl_command: str,
        *,
        request=None,
        user=None,
        title: str = 'Barcode Label',
        copies: int = 1,
        source_model: str = '',
        source_id: str = '',
        document_type: str = 'production_barcode',
    ) -> Tuple[bool, str, Optional[Any]]:
        """Print a ZPL barcode label, auto-routed to the user's station."""
        station, mapping = PrintService._resolve_station_mapping(
            document_type=document_type,
            request=request,
            user=user,
        )

        if mapping:
            return PrintService._dispatch_to_station(
                station=station,
                mapping=mapping,
                payload={
                    'action': 'print_zebra_zpl',
                    'zpl': zpl_command,
                    'copies': copies or mapping.copies,
                    'title': title,
                },
                document_type=document_type,
                user=user or _extract_user(request),
                source_model=source_model,
                source_id=source_id,
            )

        # Fallback to legacy PrintDispatcher
        from printing.dispatch import PrintDispatcher
        return PrintDispatcher.print_zpl(
            document_type=document_type,
            zpl_command=zpl_command,
            title=title,
            copies=copies,
            user=user or _extract_user(request),
            source_model=source_model,
            source_id=str(source_id),
        )

    @staticmethod
    def print_receipt(
        escpos_data: bytes = b'',
        html: str = '',
        *,
        request=None,
        user=None,
        title: str = 'POS Receipt',
        copies: int = 1,
        source_id: str = '',
        document_type: str = 'sales_receipt',
    ) -> Tuple[bool, str, Optional[Any]]:
        """Print a thermal receipt (ESC/POS or HTML)."""
        station, mapping = PrintService._resolve_station_mapping(
            document_type=document_type,
            request=request,
            user=user,
        )

        if mapping:
            payload = {
                'action': 'print_thermal_receipt',
                'copies': copies or mapping.copies,
                'title': title,
            }
            if escpos_data:
                payload['raw_base64'] = base64.b64encode(escpos_data).decode('ascii')
            elif html:
                payload['html'] = html
            else:
                return False, 'لا توجد بيانات إيصال (ESC/POS أو HTML).', None

            return PrintService._dispatch_to_station(
                station=station,
                mapping=mapping,
                payload=payload,
                document_type=document_type,
                user=user or _extract_user(request),
                source_model='POSOrder',
                source_id=source_id,
            )

        # Fallback
        from printing.dispatch import PrintDispatcher
        if escpos_data:
            return PrintDispatcher.print_escpos(
                document_type=document_type,
                raw_data=escpos_data,
                title=title,
                copies=copies,
                user=user or _extract_user(request),
                source_id=str(source_id),
            )
        elif html:
            return PrintDispatcher.print_html(
                document_type=document_type,
                html=html,
                title=title,
                copies=copies,
                user=user or _extract_user(request),
                source_id=str(source_id),
            )
        return False, 'لا توجد بيانات.', None

    @staticmethod
    def print_document(
        pdf_bytes: bytes = b'',
        html: str = '',
        *,
        request=None,
        user=None,
        title: str = '',
        copies: int = 1,
        document_type: str = 'sales_invoice',
        source_app: str = '',
        source_model: str = '',
        source_id: str = '',
    ) -> Tuple[bool, str, Optional[Any]]:
        """Print an A4 document (PDF or HTML)."""
        station, mapping = PrintService._resolve_station_mapping(
            document_type=document_type,
            request=request,
            user=user,
        )

        if mapping:
            payload = {
                'action': 'print_a4',
                'copies': copies or mapping.copies,
                'title': title,
            }
            if pdf_bytes:
                payload['pdf_base64'] = base64.b64encode(pdf_bytes).decode('ascii')
            elif html:
                payload['html'] = html
            else:
                return False, 'لا توجد بيانات مستند.', None

            return PrintService._dispatch_to_station(
                station=station,
                mapping=mapping,
                payload=payload,
                document_type=document_type,
                user=user or _extract_user(request),
                source_app=source_app,
                source_model=source_model,
                source_id=source_id,
            )

        # Fallback
        from printing.dispatch import PrintDispatcher
        if pdf_bytes:
            return PrintDispatcher.print_pdf(
                document_type=document_type,
                pdf_bytes=pdf_bytes,
                title=title,
                copies=copies,
                user=user or _extract_user(request),
                source_app=source_app,
                source_model=source_model,
                source_id=str(source_id),
            )
        elif html:
            return PrintDispatcher.print_html(
                document_type=document_type,
                html=html,
                title=title,
                copies=copies,
                user=user or _extract_user(request),
                source_app=source_app,
                source_model=source_model,
                source_id=str(source_id),
            )
        return False, 'لا توجد بيانات.', None

    # ──────────────────────────────────────────
    # Station Test Printing
    # ──────────────────────────────────────────

    @staticmethod
    def test_station_printers(station, user=None) -> Dict[str, Tuple[bool, str]]:
        """
        Send a test print for every enabled mapping on a station.
        Returns {document_type: (success, message)}.
        """
        from .models import PrinterMapping
        results = {}

        mappings = PrinterMapping.objects.filter(
            station=station, is_enabled=True,
        ).select_related('printer_config')

        for mapping in mappings:
            doc_type = mapping.document_type

            if doc_type in ('barcode', 'production_barcode', 'warranty_label'):
                zpl = (
                    "^XA^PW400^LL200"
                    "^FO30,30^A0N,35,35^FDTest OK^FS"
                    f"^FO30,80^A0N,20,20^FD{station.display_name or station.machine_name}^FS"
                    "^FO30,110^BCN,50,Y,N,N^FD123456^FS"
                    "^XZ"
                )
                ok, msg, _ = PrintService._dispatch_to_station(
                    station=station, mapping=mapping,
                    payload={'action': 'print_zebra_zpl', 'zpl': zpl, 'copies': 1,
                             'title': f'Test - {doc_type}'},
                    document_type=doc_type, user=user,
                )
                results[doc_type] = (ok, msg)

            elif doc_type in ('sales_receipt', 'kitchen_receipt'):
                escpos = b'\x1b\x40\x1b\x61\x01Test Print OK\n\n\n\x1d\x56\x00'
                ok, msg, _ = PrintService._dispatch_to_station(
                    station=station, mapping=mapping,
                    payload={
                        'action': 'print_thermal_receipt',
                        'raw_base64': base64.b64encode(escpos).decode('ascii'),
                        'copies': 1, 'title': f'Test - {doc_type}',
                    },
                    document_type=doc_type, user=user,
                )
                results[doc_type] = (ok, msg)

            else:
                # A4 test — simple HTML
                html_content = (
                    '<html><body style="font-family:Arial;text-align:center;padding:40px">'
                    f'<h1>Tony ERP — طباعة تجريبية</h1>'
                    f'<p>المحطة: {station.display_name or station.machine_name}</p>'
                    f'<p>نوع المستند: {doc_type}</p>'
                    f'<p>{timezone.now():%Y-%m-%d %H:%M:%S}</p>'
                    '</body></html>'
                )
                ok, msg, _ = PrintService._dispatch_to_station(
                    station=station, mapping=mapping,
                    payload={'action': 'print_a4', 'html': html_content, 'copies': 1,
                             'title': f'Test - {doc_type}'},
                    document_type=doc_type, user=user,
                )
                results[doc_type] = (ok, msg)

        return results

    # ──────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────

    @staticmethod
    def _resolve_station_mapping(
        document_type: str,
        request=None,
        user=None,
    ):
        """
        Determine the user's station and find the matching printer mapping.
        Returns (station, mapping) or (None, None) if not found.
        """
        from .models import PrintStation, PrinterMapping, StationSession

        station = None

        # 1. From middleware (if request available)
        if request and hasattr(request, 'print_station') and request.print_station:
            station = request.print_station

        # 2. From StationSession (if only user given)
        if not station and user:
            try:
                session = StationSession.objects.select_related('station').get(user=user)
                if session.station.is_active:
                    station = session.station
            except StationSession.DoesNotExist:
                pass

        # 3. From user assignment
        if not station and user:
            station = PrintStation.objects.filter(
                assigned_users=user,
                is_active=True,
            ).first()

        if not station:
            return None, None

        # Find the mapping for this station + document_type
        mapping = PrinterMapping.objects.filter(
            station=station,
            document_type=document_type,
            is_enabled=True,
        ).select_related('printer_config').order_by('-priority').first()

        if not mapping:
            # Try 'general' fallback
            mapping = PrinterMapping.objects.filter(
                station=station,
                document_type='general',
                is_enabled=True,
            ).select_related('printer_config').order_by('-priority').first()

        # Auto-resolve from discovered printers when no mapping exists
        if not mapping and station.is_online and station.discovered_printers:
            mapping = PrintService._auto_resolve_from_discovered(
                station=station,
                document_type=document_type,
            )

        return station, mapping

    @staticmethod
    def _auto_resolve_from_discovered(station, document_type: str):
        """
        When no explicit PrinterMapping exists, infer the correct printer
        from the station's discovered_printers based on document_type rules.

        Rules:
          - sales_receipt, kitchen_receipt, generic_receipt → first 'thermal' printer
          - production_barcode, product_barcode, warranty_label → first 'zebra' printer
          - sales_invoice, purchase_invoice, report, hr_document → first 'a4' printer

        Creates a transient (unsaved) PrinterMapping for routing.
        """
        from .models import PrinterMapping

        # Document type → required printer type
        TYPE_RULES = {
            'sales_receipt': 'thermal',
            'kitchen_receipt': 'thermal',
            'generic_receipt': 'thermal',
            'production_barcode': 'zebra',
            'product_barcode': 'zebra',
            'warranty_label': 'zebra',
            'barcode': 'zebra',
            'sales_invoice': 'a4',
            'purchase_order': 'a4',
            'purchase_invoice': 'a4',
            'report': 'a4',
            'hr_document': 'a4',
            'journal_entry': 'a4',
            'trial_balance': 'a4',
            'generic_a4': 'a4',
        }

        target_type = TYPE_RULES.get(document_type)
        if not target_type:
            return None

        discovered = station.discovered_printers or []

        # Find first printer matching the required type
        candidate = None
        for p in discovered:
            if p.get('type') == target_type:
                # Prefer the one marked as default
                if p.get('is_default'):
                    candidate = p
                    break
                if candidate is None:
                    candidate = p

        if not candidate:
            return None

        # Build a transient mapping (not saved to DB — admin should confirm)
        mapping = PrinterMapping(
            station=station,
            document_type=document_type,
            local_printer_name=candidate['name'],
            copies=1,
            is_enabled=True,
            priority=0,
        )
        mapping._auto_resolved = True

        logger.info(
            f"Auto-resolved {document_type} → {candidate['name']} "
            f"(type={target_type}) on station {station.machine_name}"
        )

        return mapping

    @staticmethod
    def _dispatch_to_station(
        station,
        mapping,
        payload: dict,
        document_type: str,
        user=None,
        source_app: str = '',
        source_model: str = '',
        source_id: str = '',
    ) -> Tuple[bool, str, Optional[Any]]:
        """
        Send a print command to a specific station's agent via Channels.
        Creates a UnifiedPrintJob for tracking.
        """
        from .models import UnifiedPrintJob, PrinterConfiguration

        # Determine the target printer
        printer_config = mapping.printer_config if hasattr(mapping, 'printer_config') else None
        local_printer = mapping.local_printer_name

        # CRITICAL: Use the EXACT local_printer_name from the mapping first.
        # This is the name the agent discovered (e.g., 'XP-80C (copy 2)')
        # and must match exactly to avoid routing to the wrong USB device.
        if local_printer:
            payload['printer_name'] = local_printer
        elif printer_config:
            payload['printer_name'] = (
                printer_config.cups_printer_name
                or printer_config.shared_printer_name
                or printer_config.name
            )
        else:
            payload['printer_name'] = ''

        if printer_config and printer_config.ip_address:
            payload['ip'] = str(printer_config.ip_address)
            payload['port'] = printer_config.port

        # Add station identity so the correct agent picks it up
        payload['target_station'] = station.machine_name
        payload['copies'] = payload.get('copies', mapping.copies)

        # Create tracking job
        job = UnifiedPrintJob.objects.create(
            document_type=document_type,
            printer=printer_config,
            zpl_command=payload.get('zpl', ''),
            escpos_data=(
                base64.b64decode(payload['raw_base64'])
                if 'raw_base64' in payload else b''
            ),
            pdf_base64=payload.get('pdf_base64', ''),
            html_content=payload.get('html', ''),
            title=payload.get('title', ''),
            copies=payload.get('copies', 1),
            source_app=source_app,
            source_model=source_model,
            source_id=str(source_id),
            requested_by=user,
        )

        payload['job_id'] = str(job.id)

        # Dispatch via Channels — target station-specific group
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer is None:
                job.status = 'failed'
                job.error_message = 'لا يوجد channel layer مُعدّ'
                job.save(update_fields=['status', 'error_message'])
                return False, 'وكيل الطباعة غير متاح (لا يوجد channel layer).', job

            # Send to station-specific group
            group_name = f"print_station_{station.machine_name}"

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'print.command',
                    'data': payload,
                },
            )

            job.status = 'sent'
            job.sent_at = timezone.now()
            job.save(update_fields=['status', 'sent_at'])

            if printer_config:
                PrinterConfiguration.objects.filter(pk=printer_config.pk).update(
                    total_prints=models.F('total_prints') + 1,
                )

            printer_label = local_printer or (printer_config.name if printer_config else '?')
            logger.info(
                f"Print job {job.id} dispatched: "
                f"{document_type} → {station.display_name or station.machine_name} / {printer_label}"
            )
            return True, f"تم الإرسال إلى {station.display_name or station.machine_name} ({printer_label})", job

        except Exception as e:
            logger.error(f"Failed to dispatch to station {station.machine_name}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.save(update_fields=['status', 'error_message'])
            return False, f"فشل الإرسال: {e}", job

    # ──────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────

    @staticmethod
    def get_user_station(request=None, user=None):
        """Return the user's current station or None."""
        station, _ = PrintService._resolve_station_mapping(
            document_type='__probe__', request=request, user=user,
        )
        return station

    @staticmethod
    def list_station_printers(station) -> List[Dict[str, Any]]:
        """Return all enabled mappings for a station as dicts."""
        from .models import PrinterMapping
        mappings = PrinterMapping.objects.filter(
            station=station, is_enabled=True,
        ).select_related('printer_config').order_by('document_type')

        return [
            {
                'document_type': m.document_type,
                'document_type_display': m.get_document_type_display(),
                'printer_name': m.local_printer_name or (m.printer_config.name if m.printer_config else '—'),
                'copies': m.copies,
                'is_network': bool(m.printer_config and m.printer_config.ip_address),
            }
            for m in mappings
        ]


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

def _extract_user(request):
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None
