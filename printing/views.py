"""واجهات الطباعة الموحدة - Unified Printing Views & API"""
import json
import base64

from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required

from printing.services import build_warranty_label_payload
from printing.dispatch import PrintDispatcher
from printing.models import UnifiedPrintJob, PrinterConfiguration


@login_required
def printing_dashboard(request):
    """لوحة تحكم الطباعة"""
    printers = PrinterConfiguration.objects.filter(is_active=True)
    recent_jobs = UnifiedPrintJob.objects.select_related(
        'printer', 'requested_by'
    ).order_by('-created_at')[:50]
    agent_status = PrintDispatcher.get_agent_status()

    return render(request, 'printing/dashboard_new.html', {
        'printers': printers,
        'recent_jobs': recent_jobs,
        'agent_status': agent_status,
    })


def _get_unit_or_404(unit_model, unit_id):
    try:
        return unit_model.objects.select_related('product', 'warranty_policy').get(pk=unit_id)
    except unit_model.DoesNotExist:
        raise Http404("الوحدة غير موجودة")


@login_required
@require_GET
def warranty_label_json(request, unit_id):
    """إرجاع بيانات ملصق الضمان في JSON (للاستخدام مع الطابعات اللاسلكية/الموبايل)."""
    from production.models import FinishedGoodUnit
    unit = _get_unit_or_404(FinishedGoodUnit, unit_id)
    payload = build_warranty_label_payload(unit)
    return JsonResponse({
        'success': True,
        'label': payload.data,
        'zpl': payload.zpl,
        'escpos': payload.escpos,
    })


@login_required
@require_GET
def warranty_label_zpl(request, unit_id):
    """إرجاع ZPL نصي لطباعة الملصق مباشرة."""
    from production.models import FinishedGoodUnit
    unit = _get_unit_or_404(FinishedGoodUnit, unit_id)
    payload = build_warranty_label_payload(unit)
    return HttpResponse(payload.zpl, content_type='text/plain; charset=utf-8')


@login_required
@require_GET
def warranty_label_escpos(request, unit_id):
    """إرجاع ESC/POS نصي للطابعات الحرارية."""
    from production.models import FinishedGoodUnit
    unit = _get_unit_or_404(FinishedGoodUnit, unit_id)
    payload = build_warranty_label_payload(unit)
    return HttpResponse(payload.escpos, content_type='text/plain; charset=utf-8')


# ──────────────────────────────────────────
# Unified Print API - واجهة الطباعة الموحدة
# ──────────────────────────────────────────

@login_required
@require_POST
def api_print_document(request):
    """
    Universal print API. Accepts JSON:
    {
        "document_type": "sales_invoice",
        "source_app": "sales",
        "source_model": "Invoice",
        "source_id": "123",
        "action": "auto"  // auto | reprint
    }
    """
    data = json.loads(request.body)
    doc_type = data.get('document_type')
    action = data.get('action', 'auto')
    source_id = data.get('source_id', '')

    if action == 'reprint':
        # Find last job for this source and reprint
        last_job = UnifiedPrintJob.objects.filter(
            source_app=data.get('source_app', ''),
            source_model=data.get('source_model', ''),
            source_id=source_id,
        ).order_by('-created_at').first()

        if last_job:
            success, msg, job = PrintDispatcher.reprint(str(last_job.pk), user=request.user)
            return JsonResponse({
                'success': success,
                'message': msg,
                'job_id': str(job.pk) if job else None,
            })
        return JsonResponse({'success': False, 'message': 'لا توجد مهمة طباعة سابقة.'})

    # Auto-print based on document type
    handlers = {
        'sales_invoice': _handle_sales_invoice_print,
        'sales_receipt': _handle_sales_receipt_print,
        'purchase_order': _handle_purchase_order_print,
        'hr_id_card': _handle_hr_id_card_print,
        'journal_entry': _handle_journal_entry_print,
    }

    handler = handlers.get(doc_type)
    if not handler:
        return JsonResponse({'success': False, 'message': f'نوع مستند غير معروف: {doc_type}'})

    success, msg = handler(source_id, request.user)
    return JsonResponse({'success': success, 'message': msg})


@login_required
@require_POST
def api_print_trial_balance(request):
    """Print trial balance report."""
    data = json.loads(request.body)
    date_from = data.get('date_from')
    date_to = data.get('date_to')

    if not date_from or not date_to:
        return JsonResponse({'success': False, 'message': 'يجب تحديد تاريخ البداية والنهاية.'})

    from printing.integrations.accounting import print_trial_balance
    success, msg = print_trial_balance(date_from, date_to, user=request.user)
    return JsonResponse({'success': success, 'message': msg})


@login_required
@require_POST
def api_reprint_job(request, job_id):
    """Reprint a specific job."""
    success, msg, job = PrintDispatcher.reprint(str(job_id), user=request.user)
    return JsonResponse({
        'success': success,
        'message': msg,
        'job_id': str(job.pk) if job else None,
    })


@login_required
@require_GET
def api_agent_status(request):
    """Check if print agent is connected — station-aware."""
    from printing.manager import PrintManager
    from printing.models import PrintStation
    status = PrintManager.get_agent_status()

    # Add station details
    online_stations = PrintStation.objects.filter(is_active=True, is_online=True)
    status['stations'] = [
        {
            'name': s.display_name or s.machine_name,
            'machine_name': s.machine_name,
            'ip': str(s.machine_ip) if s.machine_ip else None,
            'printers': s.discovered_printers or [],
            'last_seen': s.last_seen.isoformat() if s.last_seen else None,
            'os': s.os_platform,
            'version': s.agent_version,
        }
        for s in online_stations
    ]
    status['online'] = status.get('online', False) or online_stations.exists()

    pending_count = UnifiedPrintJob.objects.filter(status__in=['queued', 'sent']).count()
    failed_count = UnifiedPrintJob.objects.filter(status='failed').count()

    return JsonResponse({
        **status,
        'pending_jobs': pending_count,
        'failed_jobs': failed_count,
    })


@login_required
@require_GET
def api_job_status(request, job_id):
    """Get status of a specific print job."""
    try:
        job = UnifiedPrintJob.objects.get(pk=job_id)
        return JsonResponse({
            'success': True,
            'job_id': str(job.pk),
            'status': job.status,
            'title': job.title,
            'error': job.error_message,
            'created_at': job.created_at.isoformat(),
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        })
    except UnifiedPrintJob.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'المهمة غير موجودة'}, status=404)


@login_required
@require_GET
def api_download_fallback(request, job_id):
    """Download PDF fallback when agent is offline."""
    try:
        job = UnifiedPrintJob.objects.get(pk=job_id)
    except UnifiedPrintJob.DoesNotExist:
        raise Http404

    if job.pdf_base64:
        pdf_data = base64.b64decode(job.pdf_base64)
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{job.title or "document"}.pdf"'
        return response
    elif job.html_content:
        response = HttpResponse(job.html_content, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="{job.title or "document"}.html"'
        return response
    else:
        return JsonResponse({'success': False, 'message': 'لا يوجد محتوى قابل للتنزيل لهذه المهمة.'})


@login_required
@require_GET
def api_recent_jobs(request):
    """Get recent print jobs as JSON."""
    jobs = UnifiedPrintJob.objects.select_related('printer').order_by('-created_at')[:30]
    data = []
    for j in jobs:
        data.append({
            'id': str(j.pk),
            'title': j.title,
            'document_type': j.document_type,
            'status': j.status,
            'printer': j.printer.name if j.printer else '',
            'created_at': j.created_at.isoformat(),
            'has_pdf': bool(j.pdf_base64),
            'has_html': bool(j.html_content),
        })
    return JsonResponse({'jobs': data})


# ──────────────────────────────────────────
# Internal handlers
# ──────────────────────────────────────────

def _handle_sales_invoice_print(source_id, user):
    from sales.models import Invoice
    invoice = get_object_or_404(Invoice, pk=source_id)
    from printing.integrations.sales import auto_print_sales_invoice
    return auto_print_sales_invoice(invoice, user)


def _handle_sales_receipt_print(source_id, user):
    try:
        from pos.models import POSOrder
        order = get_object_or_404(POSOrder, pk=source_id)
        from printing.integrations.sales import print_pos_receipt
        return print_pos_receipt(order, user)
    except Exception as e:
        return False, str(e)


def _handle_purchase_order_print(source_id, user):
    from purchases.models import PurchaseOrder
    po = get_object_or_404(PurchaseOrder, pk=source_id)
    from printing.integrations.purchases import auto_print_purchase_order
    return auto_print_purchase_order(po, user)


def _handle_hr_id_card_print(source_id, user):
    from hr.models import Employee
    employee = get_object_or_404(Employee, pk=source_id)
    from printing.integrations.hr import print_employee_id_card
    return print_employee_id_card(employee, user)


def _handle_journal_entry_print(source_id, user):
    from accounting.models import JournalEntry
    entry = get_object_or_404(JournalEntry, pk=source_id)
    from printing.integrations.accounting import print_journal_entry
    return print_journal_entry(entry, user)


# ──────────────────────────────────────────
# Printer Settings UI
# ──────────────────────────────────────────

@login_required
@require_GET
def printer_settings(request):
    """Printer settings page - view and manage printer assignments."""
    from printing.manager import PrintManager
    from printing.models import PrintStation, PrinterMapping

    printers = PrintManager.get_available_printers()
    document_types = PrinterConfiguration.DOCUMENT_TYPE_CHOICES

    # Group printers by type
    grouped = {
        'zebra': [p for p in printers if p['printer_type'] == 'zebra'],
        'thermal': [p for p in printers if p['printer_type'] == 'thermal'],
        'a4': [p for p in printers if p['printer_type'] == 'a4'],
        'card': [p for p in printers if p['printer_type'] == 'card'],
    }

    # ── Station-aware status ──
    stations = PrintStation.objects.filter(is_active=True).order_by('-is_online', 'display_name')
    any_agent_online = stations.filter(is_online=True).exists()

    # Build set of discovered printer names from online stations
    online_printer_names = set()
    for station in stations.filter(is_online=True):
        for dp in (station.discovered_printers or []):
            name = dp.get('name', '')
            if name:
                online_printer_names.add(name.lower().strip())

    # Enrich each printer with real online status from stations
    for printer_list in grouped.values():
        for p in printer_list:
            p_name = (p.get('name') or '').lower().strip()
            # Check if any station discovered this printer
            p['agent_online'] = (
                any_agent_online and (
                    p_name in online_printer_names
                    or any(p_name in dp_name for dp_name in online_printer_names)
                    or any(dp_name in p_name for dp_name in online_printer_names)
                    or bool(p.get('ip_address'))  # Network printers reachable if agent up
                )
            )
            # If agent is online but connection_type is agent, mark as online too
            if not p['agent_online'] and any_agent_online and p.get('connection_type') == 'agent':
                p['agent_online'] = True

    # User's current station
    user_station = getattr(request, 'print_station', None)

    return render(request, 'printing/printer_settings.html', {
        'printers': printers,
        'grouped_printers': grouped,
        'document_types': document_types,
        'stations': stations,
        'any_agent_online': any_agent_online,
        'user_station': user_station,
    })


@login_required
@require_POST
def printer_set_default(request):
    """API: Set a printer as default for its document type."""
    data = json.loads(request.body)
    printer_id = data.get('printer_id')
    document_type = data.get('document_type')

    if not printer_id:
        return JsonResponse({'success': False, 'error': 'printer_id required'})

    try:
        printer = PrinterConfiguration.objects.get(pk=printer_id, is_active=True)

        # Unset other defaults for this document type
        target_doc = document_type or printer.document_type
        PrinterConfiguration.objects.filter(
            document_type=target_doc,
            is_default=True,
        ).exclude(pk=printer.pk).update(is_default=False)

        # Set this one as default
        printer.is_default = True
        update_fields = ['is_default']
        if document_type and document_type != printer.document_type:
            printer.document_type = document_type
            update_fields.append('document_type')
        printer.save(update_fields=update_fields)

        return JsonResponse({
            'success': True,
            'message': f'{printer.name} is now the default for {printer.get_document_type_display()}'
        })
    except PrinterConfiguration.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Printer not found'})


@login_required
@require_POST
def api_test_print(request):
    """API: Send a test print to a specific printer."""
    from printing.manager import PrintManager

    data = json.loads(request.body)
    printer_id = data.get('printer_id')
    printer_type = data.get('printer_type', 'a4')

    if not printer_id:
        return JsonResponse({'success': False, 'error': 'printer_id required'})

    success, msg = PrintManager.send_test_print(
        printer_id=printer_id,
        printer_type=printer_type,
        user=request.user,
    )
    return JsonResponse({'success': success, 'message': msg})


# ──────────────────────────────────────────
# Station Printer Mapping — Dynamic UI + API
# ──────────────────────────────────────────

@login_required
@require_GET
def api_station_live_printers(request, station_id):
    """
    Return the live discovered printers for a specific station.
    Used by the admin UI dropdown instead of manual text input.
    """
    from printing.models import PrintStation
    try:
        station = PrintStation.objects.get(pk=station_id, is_active=True)
    except PrintStation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Station not found'}, status=404)

    printers = station.discovered_printers or []

    # Group by type for the UI
    grouped = {'zebra': [], 'thermal': [], 'a4': []}
    for p in printers:
        ptype = p.get('type', 'a4')
        grouped.setdefault(ptype, []).append({
            'name': p.get('name', ''),
            'type': ptype,
            'is_default': p.get('is_default', False),
            'description': p.get('description', ''),
        })

    return JsonResponse({
        'success': True,
        'station': station.display_name or station.machine_name,
        'machine_name': station.machine_name,
        'is_online': station.is_online,
        'printers': printers,
        'grouped': grouped,
    })


@login_required
@require_POST
def api_test_station_printer(request, station_id):
    """
    Send a test print to a SPECIFIC printer on a SPECIFIC station.
    Admin clicks Test on each copy, sees which physical device responds,
    then saves it as the default — solving the 'copy 2 vs copy 3' problem.
    """
    from printing.models import PrintStation
    import uuid

    try:
        station = PrintStation.objects.get(pk=station_id, is_active=True)
    except PrintStation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Station not found'}, status=404)

    if not station.is_online:
        return JsonResponse({'success': False, 'error': 'Station is offline'}, status=400)

    body = json.loads(request.body)
    printer_name = body.get('printer_name', '')
    printer_type = body.get('printer_type', 'thermal')

    if not printer_name:
        return JsonResponse({'success': False, 'error': 'printer_name is required'}, status=400)

    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from django.utils import timezone as tz

    channel_layer = get_channel_layer()
    if not channel_layer:
        return JsonResponse({'success': False, 'error': 'No channel layer'}, status=500)

    now = tz.now().strftime('%Y-%m-%d %H:%M:%S')
    test_id = str(uuid.uuid4())[:8].upper()

    if printer_type == 'zebra':
        payload = {
            'action': 'print_zebra_zpl',
            'printer_name': printer_name,
            'request_id': test_id,
            'zpl': (
                f"^XA^PW400^LL300"
                f"^FO30,30^A0N,40,40^FDTony ERP Test^FS"
                f"^FO30,80^A0N,25,25^FD{printer_name}^FS"
                f"^FO30,120^A0N,20,20^FD{now}^FS"
                f"^FO30,160^A0N,20,20^FDID: {test_id}^FS"
                f"^FO30,200^BCN,60,Y,N,N^FD{test_id}^FS"
                f"^XZ"
            ),
        }
    elif printer_type in ('thermal', 'xprinter'):
        # ESC/POS: init + center + bold + name + cut
        escpos = bytearray()
        escpos += b'\x1b\x40'              # Initialize
        escpos += b'\x1b\x61\x01'          # Center align
        escpos += b'\x1b\x45\x01'          # Bold ON
        escpos += b'=== TEST PRINT ===\n'
        escpos += b'\x1b\x45\x00'          # Bold OFF
        escpos += f'\nPrinter: {printer_name}\n'.encode('utf-8', errors='replace')
        escpos += f'Station: {station.machine_name}\n'.encode('utf-8', errors='replace')
        escpos += f'Time: {now}\n'.encode('utf-8', errors='replace')
        escpos += f'ID: {test_id}\n'.encode('utf-8', errors='replace')
        escpos += b'\n'
        escpos += b'\x1b\x61\x01'          # Center
        escpos += b'If you see this, THIS is\n'
        escpos += b'the correct printer!\n'
        escpos += b'\n\n\n'
        escpos += b'\x1d\x56\x00'          # Full cut

        payload = {
            'action': 'print_thermal_receipt',
            'printer_name': printer_name,
            'request_id': test_id,
            'raw_base64': base64.b64encode(bytes(escpos)).decode('ascii'),
            'cut_paper': True,
        }
    else:
        # A4 test
        payload = {
            'action': 'print_a4',
            'printer_name': printer_name,
            'request_id': test_id,
            'html': (
                f'<html><body style="font-family:Arial;text-align:center;padding:80px">'
                f'<h1>Tony ERP - Test Print</h1>'
                f'<h2>Printer: {printer_name}</h2>'
                f'<p>Station: {station.machine_name}</p>'
                f'<p>Time: {now}</p>'
                f'<p>ID: {test_id}</p>'
                f'<hr><p>If you see this page, this printer is working correctly.</p>'
                f'</body></html>'
            ),
        }

    group_name = f"print_station_{station.machine_name}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {'type': 'print.command', 'data': payload},
    )

    return JsonResponse({
        'success': True,
        'test_id': test_id,
        'printer_name': printer_name,
        'station': station.machine_name,
        'message': f'Test sent to {printer_name} on {station.display_name or station.machine_name}',
    })


@login_required
@require_POST
def api_save_printer_mapping(request, station_id):
    """
    Save a printer mapping from the dynamic dropdown UI.
    Replaces manual text entry with agent-discovered printer names.
    """
    from printing.models import PrintStation, PrinterMapping

    try:
        station = PrintStation.objects.get(pk=station_id, is_active=True)
    except PrintStation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Station not found'}, status=404)

    body = json.loads(request.body)
    document_type = body.get('document_type', '')
    printer_name = body.get('printer_name', '')
    copies = int(body.get('copies', 1))
    priority = int(body.get('priority', 0))

    if not document_type or not printer_name:
        return JsonResponse({
            'success': False,
            'error': 'document_type and printer_name are required',
        }, status=400)

    # Try to find a matching PrinterConfiguration
    printer_config = None
    config_candidates = PrinterConfiguration.objects.filter(is_active=True)
    for cfg in config_candidates:
        names_to_check = [
            cfg.name.lower(),
            (cfg.cups_printer_name or '').lower(),
            (cfg.shared_printer_name or '').lower(),
        ]
        if printer_name.lower() in names_to_check:
            printer_config = cfg
            break

    mapping, created = PrinterMapping.objects.update_or_create(
        station=station,
        document_type=document_type,
        defaults={
            'local_printer_name': printer_name,
            'printer_config': printer_config,
            'copies': copies,
            'priority': priority,
            'is_enabled': True,
        },
    )

    return JsonResponse({
        'success': True,
        'created': created,
        'mapping_id': str(mapping.pk),
        'message': f'{printer_name} → {document_type} on {station.display_name or station.machine_name}',
    })


@login_required
@require_GET
def station_mapping_view(request):
    """
    Station-to-printer mapping page — replaces manual text input
    with live dropdowns populated from agent-discovered printers.
    """
    from printing.models import PrintStation, PrinterMapping

    stations = PrintStation.objects.filter(
        is_active=True,
    ).prefetch_related('printer_mappings').order_by('-is_online', 'display_name')

    # Use PrinterMapping.DOCUMENT_TYPE_CHOICES which includes all mapping-relevant types
    from printing.models import PrinterMapping as PM
    document_types = PM.DOCUMENT_TYPE_CHOICES

    return render(request, 'printing/station_printer_mapping.html', {
        'stations': stations,
        'document_types': document_types,
    })
