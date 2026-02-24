"""
Central Print Manager - Smart routing for all document types.
مدير الطباعة المركزي - توجيه ذكي لجميع أنواع المستندات.

Routes documents to the correct physical printer based on type,
availability, and user configuration. Wraps PrintDispatcher with
health checks and automatic fallback logic.
"""
import logging
import socket
from typing import Optional, Tuple, Dict, Any, List

from django.utils import timezone

from .models import PrinterConfiguration, UnifiedPrintJob
from .dispatch import PrintDispatcher

logger = logging.getLogger(__name__)

# Map high-level printer categories to model printer_type values
PRINTER_TYPE_MAP = {
    'zebra': ['zebra'],
    'xprinter': ['thermal'],
    'thermal': ['thermal'],
    'a4': ['a4'],
}

# Map high-level document categories to model document_type values
DOCUMENT_CATEGORY_MAP = {
    'barcode': ['production_barcode', 'product_barcode', 'warranty_label'],
    'receipt': ['sales_receipt', 'generic_receipt'],
    'invoice': ['sales_invoice'],
    'document': ['purchase_order', 'journal_entry', 'trial_balance', 'generic_a4'],
    'id_card': ['hr_id_card'],
}


class PrintManager:
    """
    High-level print orchestration layer.
    All modules should call PrintManager instead of PrintDispatcher directly.
    Provides: health checks, automatic fallback, printer discovery.
    """

    # ──────────────────────────────────────────
    # Printer Health / Discovery
    # ──────────────────────────────────────────

    @staticmethod
    def get_available_printers(printer_type: str = None) -> List[Dict[str, Any]]:
        """Return active printers, optionally filtered by type."""
        qs = PrinterConfiguration.objects.filter(is_active=True)
        if printer_type:
            # Support both 'xprinter' alias and raw model values
            type_values = PRINTER_TYPE_MAP.get(printer_type, [printer_type])
            qs = qs.filter(printer_type__in=type_values)
        qs = qs.order_by('-is_default', 'name')

        results = []
        for p in qs:
            info = {
                'id': str(p.id),
                'name': p.name,
                'printer_type': p.printer_type,
                'document_type': p.document_type,
                'connection_type': p.connection_type,
                'ip_address': str(p.ip_address) if p.ip_address else '',
                'port': p.port,
                'is_default': p.is_default,
                'is_online': PrintManager._check_printer_online(p),
            }
            results.append(info)
        return results

    @staticmethod
    def _check_printer_online(printer: 'PrinterConfiguration', timeout: float = 1.5) -> bool:
        """Quick TCP check for network printers; USB/local assumed online."""
        if printer.connection_type not in ('network',) or not printer.ip_address:
            # USB / CUPS / shared / agent – assume online (agent handles errors)
            return True
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((str(printer.ip_address), printer.port or 9100))
            sock.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    @staticmethod
    def _find_fallback_printer(
        printer_type: str, document_type: str = None, exclude_id=None
    ) -> Optional['PrinterConfiguration']:
        """Find an alternative printer when the default is offline."""
        type_values = PRINTER_TYPE_MAP.get(printer_type, [printer_type])
        qs = PrinterConfiguration.objects.filter(
            printer_type__in=type_values,
            is_active=True,
        )
        if document_type:
            # Try same document type first
            qs_doc = qs.filter(document_type=document_type)
            if exclude_id:
                qs_doc = qs_doc.exclude(pk=exclude_id)
            for p in qs_doc.order_by('-is_default'):
                if PrintManager._check_printer_online(p):
                    return p
            # If none found with same doc type, try any printer of same type
            if exclude_id:
                qs = qs.exclude(pk=exclude_id)
        else:
            if exclude_id:
                qs = qs.exclude(pk=exclude_id)

        for p in qs.order_by('-is_default'):
            if PrintManager._check_printer_online(p):
                return p
        return None

    # ──────────────────────────────────────────
    # A. Barcode / Warranty Labels (ZPL → Zebra)
    # ──────────────────────────────────────────

    @staticmethod
    def print_barcode_label(
        zpl_command: str,
        *,
        title: str = 'Barcode Label',
        copies: int = 1,
        user=None,
        source_model: str = '',
        source_id: str = '',
        document_type: str = 'production_barcode',
        printer_id=None,
    ) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
        """
        Send a ZPL label to the Zebra printer.
        Falls back to another Zebra if the default is offline.
        """
        printer = PrintManager._resolve_with_fallback(
            document_type=document_type,
            printer_type='zebra',
            printer_id=printer_id,
        )
        if not printer:
            return False, 'لا توجد طابعة Zebra متاحة. تحقق من الاتصال أو أضف طابعة في الإعدادات.', None

        return PrintDispatcher.print_zpl(
            document_type=document_type,
            zpl_command=zpl_command,
            title=title,
            copies=copies,
            user=user,
            source_app='production',
            source_model=source_model,
            source_id=source_id,
            printer_id=str(printer.pk),
        )

    # ──────────────────────────────────────────
    # B. POS Receipts (ESC/POS → XPrinter)
    # ──────────────────────────────────────────

    @staticmethod
    def print_receipt(
        escpos_data: bytes,
        *,
        title: str = 'POS Receipt',
        copies: int = 1,
        user=None,
        source_id: str = '',
        document_type: str = 'sales_receipt',
        printer_id=None,
    ) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
        """
        Send ESC/POS receipt to the first available XPrinter.
        """
        printer = PrintManager._resolve_with_fallback(
            document_type=document_type,
            printer_type='thermal',
            printer_id=printer_id,
        )
        if not printer:
            return False, 'لا توجد طابعة حرارية متاحة للإيصالات.', None

        return PrintDispatcher.print_escpos(
            document_type=document_type,
            raw_data=escpos_data,
            title=title,
            copies=copies,
            user=user,
            source_app='pos',
            source_model='POSOrder',
            source_id=source_id,
            printer_id=str(printer.pk),
        )

    @staticmethod
    def print_receipt_html(
        html: str,
        *,
        title: str = 'POS Receipt',
        copies: int = 1,
        user=None,
        source_id: str = '',
        document_type: str = 'sales_receipt',
        printer_id=None,
    ) -> Tuple[bool, str, Optional[UnifiedPrintJob]]:
        """Send HTML receipt to thermal printer (agent renders it)."""
        printer = PrintManager._resolve_with_fallback(
            document_type=document_type,
            printer_type='thermal',
            printer_id=printer_id,
        )
        if not printer:
            return False, 'لا توجد طابعة حرارية متاحة للإيصالات.', None

        return PrintDispatcher.print_html(
            document_type=document_type,
            html=html,
            title=title,
            copies=copies,
            user=user,
            source_app='pos',
            source_model='POSOrder',
            source_id=source_id,
            printer_id=str(printer.pk),
        )

    # ──────────────────────────────────────────
    # C. Standard A4 Documents (PDF → RICOH / Laser)
    # ──────────────────────────────────────────

    @staticmethod
    def print_document(
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
        """
        Send a PDF to an A4 printer (invoices, trial balance, HR docs).
        """
        printer = PrintManager._resolve_with_fallback(
            document_type=document_type,
            printer_type='a4',
            printer_id=printer_id,
        )
        if not printer:
            return False, f'لا توجد طابعة A4 متاحة لنوع المستند "{document_type}".', None

        return PrintDispatcher.print_pdf(
            document_type=document_type,
            pdf_bytes=pdf_bytes,
            title=title,
            copies=copies,
            user=user,
            source_app=source_app,
            source_model=source_model,
            source_id=source_id,
            printer_id=str(printer.pk),
        )

    @staticmethod
    def print_document_html(
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
        """Send HTML document to an A4 printer."""
        printer = PrintManager._resolve_with_fallback(
            document_type=document_type,
            printer_type='a4',
            printer_id=printer_id,
        )
        if not printer:
            return False, f'لا توجد طابعة A4 متاحة لنوع المستند "{document_type}".', None

        return PrintDispatcher.print_html(
            document_type=document_type,
            html=html,
            title=title,
            copies=copies,
            user=user,
            source_app=source_app,
            source_model=source_model,
            source_id=source_id,
            printer_id=str(printer.pk),
        )

    # ──────────────────────────────────────────
    # Routing internals
    # ──────────────────────────────────────────

    @staticmethod
    def _resolve_with_fallback(
        document_type: str,
        printer_type: str,
        printer_id=None,
    ) -> Optional['PrinterConfiguration']:
        """
        Resolve printer with automatic fallback:
        1. Use explicit printer_id if given
        2. Use default printer for that document_type
        3. Fall back to any online printer of the same type
        """
        # Explicit printer
        if printer_id:
            try:
                p = PrinterConfiguration.objects.get(pk=printer_id, is_active=True)
                if PrintManager._check_printer_online(p):
                    return p
                logger.warning(
                    f"Requested printer {p.name} is offline, searching fallback..."
                )
            except PrinterConfiguration.DoesNotExist:
                pass

        # Default printer for this document type
        default = PrinterConfiguration.objects.filter(
            document_type=document_type,
            is_default=True,
            is_active=True,
        ).first()

        if default and PrintManager._check_printer_online(default):
            return default

        # Fallback: any online printer matching the type
        fallback = PrintManager._find_fallback_printer(
            printer_type,
            document_type,
            exclude_id=default.pk if default else None,
        )
        if fallback:
            logger.info(
                f"Using fallback printer '{fallback.name}' for {document_type}"
            )
        return fallback

    # ──────────────────────────────────────────
    # Agent status (delegates to dispatcher)
    # ──────────────────────────────────────────

    @staticmethod
    def get_agent_status() -> Dict[str, Any]:
        """Check agent connectivity — enhanced with PrintStation awareness."""
        status = PrintDispatcher.get_agent_status()

        # ── Check PrintStation online status ──
        try:
            from printing.models import PrintStation
            online_stations = PrintStation.objects.filter(
                is_active=True, is_online=True
            )
            station_count = online_stations.count()

            if station_count > 0:
                # Station is online = agent IS connected
                status['online'] = True
                status['station_connected'] = True
                status['online_stations'] = station_count

                # Collect all discovered printers from online stations
                all_discovered = []
                for st in online_stations:
                    for p in (st.discovered_printers or []):
                        all_discovered.append({
                            'name': p.get('name', ''),
                            'type': p.get('type', 'unknown'),
                            'station': st.display_name or st.machine_name,
                            'station_ip': str(st.machine_ip) if st.machine_ip else '',
                        })
                status['discovered_printers'] = all_discovered
            else:
                status['online_stations'] = 0
                status['discovered_printers'] = []
        except Exception:
            status['online_stations'] = 0

        status['printers'] = PrintManager.get_available_printers()
        return status

    # ──────────────────────────────────────────
    # Test prints
    # ──────────────────────────────────────────

    @staticmethod
    def send_test_print(printer_id, printer_type: str = '', user=None) -> Tuple[bool, str]:
        """Send a test print to the specified printer."""
        if printer_type in ('zebra',):
            zpl = "^XA^PW400^LL200^FO30,30^A0N,40,40^FDTest OK^FS^FO30,80^BCN,60,Y,N,N^FD123456^FS^XZ"
            success, msg, _ = PrintManager.print_barcode_label(
                zpl_command=zpl,
                title='Test Print - Zebra',
                printer_id=printer_id,
                user=user,
            )
            return success, msg
        elif printer_type in ('thermal', 'xprinter'):
            data = b'\x1b\x40\x1b\x61\x01Test Print OK\n\n\n\x1d\x56\x00'
            success, msg, _ = PrintManager.print_receipt(
                escpos_data=data,
                title='Test Print - Thermal',
                printer_id=printer_id,
                user=user,
            )
            return success, msg
        else:
            html = '<h1 style="text-align:center;margin-top:200px;">Test Print OK</h1><p style="text-align:center;">Tony ERP Printing System</p>'
            success, msg, _ = PrintManager.print_document_html(
                document_type='generic_a4',
                html=html,
                title='Test Print - A4',
                printer_id=printer_id,
                user=user,
            )
            return success, msg
