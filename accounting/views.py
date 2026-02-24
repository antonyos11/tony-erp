import openpyxl
from reportlab.pdfgen import canvas
import json
import hashlib
from decimal import Decimal, InvalidOperation
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q
from django.db.models import Sum
from django.db import models
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

# --- Excel Export Placeholders ---
def export_accounts_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws: ws.append(['ID', 'Name', 'Type'])
    for acc in Account.objects.all():
        if ws: ws.append([acc.id, acc.name, acc.account_type])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="accounts.xlsx"'
    wb.save(response)
    return response

def export_journal_entries_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws: ws.append(['ID', 'Date', 'Description'])
    for je in JournalEntry.objects.all():
        if ws: ws.append([je.id, je.date, je.description])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="journal_entries.xlsx"'
    wb.save(response)
    return response

def export_customers_excel(request):
    from partners.models import Customer
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws: ws.append(['ID', 'Name', 'Email', 'Phone'])
    for c in Customer.objects.all():
        if ws: ws.append([c.id, c.name, c.email, c.phone])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="customers.xlsx"'
    wb.save(response)
    return response

def export_suppliers_excel(request):
    from partners.models import Supplier
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws: ws.append(['ID', 'Name', 'Email', 'Phone'])
    for s in Supplier.objects.all():
        if ws: ws.append([s.id, s.name, s.email, s.phone])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="suppliers.xlsx"'
    wb.save(response)
    return response

def export_invoices_excel(request):
    from sales.models import Invoice
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws: ws.append(['ID', 'Number', 'Customer', 'Date', 'Total'])
    for inv in Invoice.objects.all():
        if ws: ws.append([inv.id, inv.number, inv.customer.name if inv.customer else '', inv.date, inv.total])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="invoices.xlsx"'
    wb.save(response)
    return response

def export_purchase_bills_excel(request):
    from purchases.models import PurchaseBill
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws: ws.append(['ID', 'Number', 'Supplier', 'Date', 'Total'])
    for pb in PurchaseBill.objects.all():
        if ws: ws.append([pb.id, pb.number, pb.supplier.name if pb.supplier else '', pb.date, pb.total])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="purchase_bills.xlsx"'
    wb.save(response)
    return response

# --- PDF Export Placeholders ---
def export_accounts_pdf(request):
    from io import BytesIO
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "دليل الحسابات (تصدير PDF تجريبي)")
    y = 780
    for acc in Account.objects.all():
        p.drawString(100, y, f"{acc.id} - {acc.name} - {acc.account_type}")
        y -= 20
        if y < 50:
            p.showPage(); y = 800
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="accounts.pdf"'
    return response

def export_journal_entries_pdf(request):
    from io import BytesIO
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "قيود اليومية (تصدير PDF تجريبي)")
    y = 780
    for je in JournalEntry.objects.all():
        p.drawString(100, y, f"{je.id} - {je.date} - {je.description}")
        y -= 20
        if y < 50:
            p.showPage(); y = 800
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="journal_entries.pdf"'
    return response

def export_customers_pdf(request):
    from partners.models import Customer
    from io import BytesIO
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "العملاء (تصدير PDF تجريبي)")
    y = 780
    for c in Customer.objects.all():
        p.drawString(100, y, f"{c.id} - {c.name} - {c.email} - {c.phone}")
        y -= 20
        if y < 50:
            p.showPage(); y = 800
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="customers.pdf"'
    return response

def export_suppliers_pdf(request):
    from partners.models import Supplier
    from io import BytesIO
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "الموردين (تصدير PDF تجريبي)")
    y = 780
    for s in Supplier.objects.all():
        p.drawString(100, y, f"{s.id} - {s.name} - {s.email} - {s.phone}")
        y -= 20
        if y < 50:
            p.showPage(); y = 800
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="suppliers.pdf"'
    return response

def export_invoices_pdf(request):
    from sales.models import Invoice
    from io import BytesIO
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "فواتير المبيعات (تصدير PDF تجريبي)")
    y = 780
    for inv in Invoice.objects.all():
        p.drawString(100, y, f"{inv.id} - {inv.number} - {inv.customer.name if inv.customer else ''} - {inv.date} - {inv.total}")
        y -= 20
        if y < 50:
            p.showPage(); y = 800
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoices.pdf"'
    return response

def export_purchase_bills_pdf(request):
    from purchases.models import PurchaseBill
    from io import BytesIO
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "فواتير المشتريات (تصدير PDF تجريبي)")
    y = 780
    for pb in PurchaseBill.objects.all():
        p.drawString(100, y, f"{pb.id} - {pb.number} - {pb.supplier.name if pb.supplier else ''} - {pb.date} - {pb.total}")
        y -= 20
        if y < 50:
            p.showPage(); y = 800
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="purchase_bills.pdf"'
    return response
import csv
from django.http import HttpResponse

def export_accounts(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="accounts.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Type'])
    for acc in Account.objects.all():
        writer.writerow([acc.id, acc.name, acc.account_type])
    return response

def export_journal_entries(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="journal_entries.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Date', 'Description'])
    for je in JournalEntry.objects.all():
        writer.writerow([je.id, je.date, je.description])
    return response

from partners.models import Customer, Supplier
def export_customers(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Email', 'Phone'])
    for c in Customer.objects.all():
        writer.writerow([c.id, c.name, c.email, c.phone])
    return response

def export_suppliers(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="suppliers.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Email', 'Phone'])
    for s in Supplier.objects.all():
        writer.writerow([s.id, s.name, s.email, s.phone])
    return response

from sales.models import Invoice
def export_invoices(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Number', 'Customer', 'Date', 'Total'])
    for inv in Invoice.objects.all():
        writer.writerow([inv.id, inv.number, inv.customer.name if inv.customer else '', inv.date, inv.total])
    return response

from purchases.models import PurchaseBill
def export_purchase_bills(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchase_bills.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Number', 'Supplier', 'Date', 'Total'])
    for pb in PurchaseBill.objects.all():
        writer.writerow([pb.id, pb.number, pb.supplier.name if pb.supplier else '', pb.date, pb.total])
    return response
def export_tools(request):
    """صفحة تصدير البيانات المحاسبية (Placeholder)."""
    return render(request, 'accounting/export_tools.html')
from django.shortcuts import render, redirect, get_object_or_404
import logging
from django.template import engines, TemplateDoesNotExist
from django.http import HttpResponse

logger = logging.getLogger(__name__)

# Unified safe render helper (was missing causing NameError).
## _safe_render helper removed after template stabilization.

# Early diagnostic: verify 'money' filter exists to avoid TemplateSyntaxError later.
try:  # pragma: no cover - defensive initialization
    _django_engine = engines['django']
    _filters = getattr(_django_engine.engine, 'filters', {})
    if 'money' not in _filters:
        logger.debug("Template filter 'money' not found at import time. Ensure settings.TEMPLATES.OPTIONS.builtins includes 'core.templatetags.money_tags'.")
except Exception as _e:  # silent fallback with debug
    logger.debug("Could not pre-check money filter: %s", _e)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .auth import require_perm
from django.contrib import messages
from .models import Account, JournalEntry, JournalEntryItem, CostCenter, FiscalYear
from django.db.models import Q
from decimal import Decimal
from django.http import JsonResponse
from django.utils.timezone import now as _now
from datetime import date, datetime, timedelta
from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:  # type hints only
    from django.db.models.query import QuerySet
    from .models import JournalEntryItem as JournalEntryItemType

@login_required
@require_perm('accounting.run_depreciation')
def asset_depreciation(request):
    """عرض مبسط لجمع بيانات إهلاك الأصول (Placeholder).

    يعتمد حالياً على نموذج Machine في تطبيق maintenance إن وجد لتقدير:
      - العمر المستخدم (سنوات)
      - الإهلاك السنوي
      - القيمة الدفترية الحالية
    مستقبلًا: سيتم استبداله بنموذج Asset وسجلات إهلاك فعلية مع إمكانية ترحيل قيود.
    """
    machines_all = []
    total_purchase = Decimal('0')
    total_book = Decimal('0')
    total_annual_dep = Decimal('0')
    per_method = {}
    maintenance_available = True
    try:
        from maintenance.models import Machine  # type: ignore
        today = _now().date()
        # Hard cap for performance (configurable later)
        qs = Machine.objects.filter(is_active=True).only('id','code','name','purchase_price','salvage_value','useful_life_years','purchase_date','depreciation_method')[:1000]
        for m in qs:
            try:
                years_used = Decimal(str((today - m.purchase_date).days / 365.25))
            except Exception:
                years_used = Decimal('0')
            if years_used < 0:
                years_used = Decimal('0')
            try:
                annual = (m.purchase_price - m.salvage_value) / m.useful_life_years if m.useful_life_years else Decimal('0')
            except Exception:
                annual = Decimal('0')
            try:
                book_val = getattr(m, 'current_book_value', m.purchase_price)
            except Exception:
                book_val = m.purchase_price
            total_purchase += m.purchase_price or 0
            total_book += Decimal(str(book_val))
            total_annual_dep += Decimal(str(annual))
            method = getattr(m, 'depreciation_method', 'unknown') or 'unknown'
            d = {
                'id': m.id,
                'code': m.code,
                'name': m.name,
                'purchase_price': m.purchase_price,
                'salvage_value': m.salvage_value,
                'useful_life_years': m.useful_life_years,
                'years_used': float(years_used),
                'annual_depreciation': annual,
                'current_book_value': book_val,
                'method': method,
            }
            per_method.setdefault(method, {'count':0,'annual':Decimal('0'),'book':Decimal('0'),'purchase':Decimal('0')})
            per_method[method]['count'] += 1
            per_method[method]['annual'] += Decimal(str(annual))
            per_method[method]['book'] += Decimal(str(book_val))
            per_method[method]['purchase'] += Decimal(str(m.purchase_price or 0))
            machines_all.append(d)
    except Exception as e:  # pragma: no cover - graceful degrade
        maintenance_available = False
        logger.warning("Asset depreciation view degraded: %s", e)

    # Pagination
    try:
        page = max(1, int(request.GET.get('page','1')))
    except ValueError:
        page = 1
    try:
        page_size = int(request.GET.get('page_size','100'))
    except ValueError:
        page_size = 100
    page_size = min(max(20, page_size), 500)
    offset = (page-1)*page_size
    machines = machines_all[offset: offset+page_size]
    total_pages = (len(machines_all)//page_size) + (1 if len(machines_all)%page_size else 0)

    context = {
        'machines': machines,
        'total_purchase': total_purchase,
        'total_book_value': total_book,
        'total_annual_depreciation': total_annual_dep,
        'count': len(machines_all),
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'offset': offset,
        'per_method': per_method,
        'maintenance_available': maintenance_available,
    }
    export = request.GET.get('export')
    if export == 'csv':
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="asset_depreciation.csv"'
        w = csv.writer(resp)
        w.writerow(['ID','Code','Name','Method','PurchasePrice','Salvage','LifeYears','YearsUsed','AnnualDep','BookValue'])
        for m in machines_all:
            w.writerow([m['id'], m['code'], m['name'], m['method'], m['purchase_price'], m['salvage_value'], m['useful_life_years'], m['years_used'], m['annual_depreciation'], m['current_book_value']])
        w.writerow([])
        w.writerow(['Totals','','','', str(total_purchase),'','', '', str(total_annual_dep), str(total_book)])
        return resp
    if export == 'xlsx':
        try:
            import openpyxl
            from io import BytesIO
            from django.http import HttpResponse
            wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Depreciation'
            if ws: ws.append(['ID','Code','Name','Method','PurchasePrice','Salvage','LifeYears','YearsUsed','AnnualDep','BookValue'])
            for m in machines_all:
                if ws: ws.append([m['id'], m['code'], m['name'], m['method'], float(m['purchase_price'] or 0), float(m['salvage_value'] or 0), m['useful_life_years'], m['years_used'], float(m['annual_depreciation']), float(m['current_book_value'])])
            
            if ws: 
                ws.append([])
            if ws: 
                ws.append(['Totals','','','', float(total_purchase), '', '', '', float(total_annual_dep), float(total_book)])
            if ws: 
                ws.append([])
            if ws: 
                ws.append(['Method','Count','TotalPurchase','TotalAnnual','TotalBook'])
            for method, d in per_method.items():
                if ws: ws.append([method, d['count'], float(d['purchase']), float(d['annual']), float(d['book'])])
            bio = BytesIO(); wb.save(bio); bio.seek(0)
            resp = HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = 'attachment; filename=asset_depreciation.xlsx'
            return resp
        except Exception:
            from django.http import HttpResponse
            return HttpResponse('openpyxl not installed', content_type='text/plain; charset=utf-8')
    if request.GET.get('format') == 'json':
        return JsonResponse({
            'count': len(machines_all),
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
            },
            'maintenance_available': maintenance_available,
            'totals': {
                'purchase': str(total_purchase),
                'book_value': str(total_book),
                'annual_depreciation': str(total_annual_dep),
            },
            'per_method': {k: {
                'count': v['count'],
                'purchase': str(v['purchase']),
                'annual': str(v['annual']),
                'book': str(v['book']),
            } for k, v in per_method.items()},
            'results': [
                {
                    'id': m['id'], 'code': m['code'], 'name': m['name'], 'method': m['method'],
                    'purchase_price': str(m['purchase_price']), 'salvage_value': str(m['salvage_value']),
                    'useful_life_years': m['useful_life_years'], 'years_used': m['years_used'],
                    'annual_depreciation': str(m['annual_depreciation']), 'current_book_value': str(m['current_book_value']),
                } for m in machines
            ]
        })
    return render(request, 'accounting/asset_depreciation.html', context)

@login_required
def assets_overview(request):
    # Permission check (redundant but explicit)
    if not (request.user.is_superuser or request.user.has_perm('accounting.view_account')):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('ليست لديك صلاحية عرض الأصول')

    # Parameters
    q = (request.GET.get('q') or '').strip()
    export = request.GET.get('export')  # csv / xlsx / None
    order = (request.GET.get('order') or 'code').strip()
    group = (request.GET.get('group') or '').strip()  # 'prefix' / ''
    try:
        prefix_len = int(request.GET.get('prefix_len') or 2)
    except ValueError:
        prefix_len = 2
    try:
        page = max(1, int(request.GET.get('page', '1')))
    except ValueError:
        page = 1
    try:
        page_size = int(request.GET.get('page_size', '50'))
    except ValueError:
        page_size = 50
    page_size = min(max(10, page_size), 500)

    # Base queryset
    qs = Account.objects.filter(is_active=True, account_type='asset')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))

    # Ordering
    valid_orders = {'code', '-code', 'balance', '-balance'}
    if order not in valid_orders:
        order = 'code'
    if order in {'balance', '-balance'}:
        # Evaluate queryset (balance likely a Python property)
        data_list = list(qs)
        reverse = order.startswith('-')
        data_list.sort(key=lambda a: getattr(a, 'balance', Decimal('0')), reverse=reverse)
        ordered = data_list
    else:
        ordered = list(qs.order_by(order))

    grouped = None
    if group == 'prefix':
        from collections import defaultdict
        from typing import TypedDict, Any, Dict, List
        class _GroupData(TypedDict):
            accounts: List[Any]
            balance: Decimal
        grouped_map: Dict[str, _GroupData] = defaultdict(lambda: {'accounts': [], 'balance': Decimal('0')})
        for acc in ordered:
            prefix = (acc.code or '')[:prefix_len]
            try:
                bal = acc.balance
            except Exception:
                bal = Decimal('0')
            grouped_map[prefix]['accounts'].append(acc)
            grouped_map[prefix]['balance'] += bal
        grouped = [
            {
                'prefix': k,
                'count': len(grouped_map[k]['accounts']),
                'balance': grouped_map[k]['balance'],
                'accounts': grouped_map[k]['accounts']
            }
            for k in grouped_map.keys()
        ]
        grouped.sort(key=lambda g: g['prefix'])

    # Pagination (only if not grouped)
    if not grouped:
        total_accounts = len(ordered)
        total_balance = Decimal('0')
        for acc in ordered[:2000]:  # cap for performance
            try:
                total_balance += acc.balance
            except Exception:
                pass
        offset = (page - 1) * page_size
        page_qs = ordered[offset: offset + page_size]
        rows = []
        for acc in page_qs:
            try:
                bal = acc.balance
            except Exception:
                bal = Decimal('0')
            rows.append({'id': acc.id, 'code': acc.code, 'name': acc.name, 'balance': bal})
        total_pages = (total_accounts // page_size) + (1 if total_accounts % page_size else 0)
    else:
        rows = []
        total_accounts = sum(g['count'] for g in grouped)
        total_balance = sum(g['balance'] for g in grouped)
        total_pages = 1
        offset = 0

    context = {
        'query': q,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'total_assets_accounts': total_accounts,
        'total_assets_balance': total_balance,
        'asset_accounts': rows,
        'offset': offset,
        'export': export,
        'order': order,
        'group': group,
        'prefix_len': prefix_len,
        'grouped': grouped,
    }

    # CSV export
    if export == 'csv':
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="assets_overview.csv"'
        w = csv.writer(resp)
        if grouped:
            w.writerow(['Prefix', 'Count', 'Balance'])
            for g in grouped:
                w.writerow([g['prefix'], g['count'], f"{g['balance']}"])
        else:
            w.writerow(['ID', 'Code', 'Name', 'Balance'])
            for r in rows:
                w.writerow([r['id'], r['code'], r['name'], f"{r['balance']}"])
        w.writerow([])
        w.writerow(['Total Accounts', total_accounts, 'Total Balance', f"{total_balance}"])
        return resp

    # XLSX export
    if export == 'xlsx':
        try:
            import openpyxl
            from io import BytesIO
            from django.http import HttpResponse
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Assets'
            if grouped:
                if ws: ws.append(['Prefix', 'Count', 'Balance'])
                for g in grouped:
                    if ws: ws.append([g['prefix'], g['count'], float(g['balance'])])
            else:
                if ws: ws.append(['ID', 'Code', 'Name', 'Balance'])
                for r in rows:
                    if ws: ws.append([r['id'], r['code'], r['name'], float(r['balance'])])
            if ws: ws.append([])
            if ws: ws.append(['Total Accounts', total_accounts, 'Total Balance', float(total_balance)])
            bio = BytesIO(); wb.save(bio); bio.seek(0)
            resp = HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = 'attachment; filename=assets_overview.xlsx'
            return resp
        except Exception:
            from django.http import HttpResponse
            return HttpResponse('XLSX export requires openpyxl', content_type='text/plain; charset=utf-8')

    # JSON API
    if request.GET.get('format') == 'json':
        return JsonResponse({
            'query': q,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_accounts': total_accounts
            },
            'total_assets_balance': str(total_balance),
            'order': order,
            'group': group,
            'prefix_len': prefix_len,
            'grouped': grouped,
            'results': [
                {'id': r['id'], 'code': r['code'], 'name': r['name'], 'balance': str(r['balance'])}
                for r in rows
            ]
        })

    return render(request, 'accounting/assets_overview.html', context)


@login_required
def accounting_dashboard(request):
    # Minimal placeholder dashboard to resolve missing view error.
    # Shows quick stats for asset accounts reused from assets_overview for now.
    qs = Account.objects.filter(is_active=True, account_type='asset')[:50]
    total_assets = Account.objects.filter(is_active=True, account_type='asset').count()
    try:
        total_balance = sum(getattr(a, 'balance', 0) for a in qs)
    except Exception:
        total_balance = 0
    context = {
        'total_assets_accounts': total_assets,
        'sample_asset_accounts': qs,
        'total_assets_balance': total_balance,
    }
    if request.GET.get('format') == 'json':
        return JsonResponse({
            'total_assets_accounts': total_assets,
            'total_assets_balance': str(total_balance),
            'sample': [
                {'id': a.id, 'code': a.code, 'name': a.name, 'balance': str(getattr(a, 'balance', 0))}
                for a in qs
            ]
        })
    return render(request, 'accounting/dashboard.html', context)


@login_required
@require_perm('accounting.close_year')
def period_close_year(request):
    """واجهة إقفال السنة المالية (Placeholder).

    الخطوات المستقبلية المتوقعة:
      1. التحقق من عدم وجود قيود غير مرحلة.
      2. إنشاء قيود الإقفال (إقفال الإيرادات والمصروفات إلى الأرباح المبقاة / حساب نتيجة).
      3. وسم السنة المالية الحالية بأنها مقفلة وتعطيل التعديل على قيودها.
      4. إنشاء سنة مالية جديدة (اختياري مع نموذج).
    حالياً: تعرض ملخصاً تمهيدياً فقط.
    """
    from .models import FiscalYear  # استيراد محلي لتقليل مشاكل circular
    fy = FiscalYear.objects.filter(is_active=True, is_closed=False).first()
    message_error = None
    closure_obj = None
    from .services.accounting import perform_year_close, YearCloseError  # type: ignore
    unposted_count = JournalEntry.objects.filter(is_posted=False, date__gte=fy.start_date if fy else None, date__lte=fy.end_date if fy else None).count() if fy else 0
    if request.method == 'POST' and fy:
        if unposted_count != 0:
            message_error = 'هناك قيود غير مرحلة داخل نطاق السنة.'
        else:
            try:
                closure_obj = perform_year_close(fy, request.user)
                from django.contrib import messages as _msg
                _msg.success(request, f'تم إقفال السنة {fy.name} وإنشاء القيد {closure_obj.journal_entry.number}')
                return redirect('accounting:period_close_year')
            except YearCloseError as e:
                message_error = str(e)
            except Exception as e:  # pragma: no cover
                message_error = f'خطأ غير متوقع: {e}'
    context = {
        'active_fiscal_year': fy,
        'unposted_entries': unposted_count,
        'can_close': fy is not None and unposted_count == 0,
        'error': message_error,
        'closure': closure_obj,
    }
    return render(request, 'accounting/period_close_year.html', context)


@login_required
@require_perm('accounting.close_month')
def period_close_month(request):
    """واجهة إقفال شهر (Placeholder مبسط).

    منطق مستقبلي: تجميع قيود التسويات (الإهلاك، المؤجلات، المخصصات) ثم ترحيلها.
    """
    today = date.today()
    current_month = today.replace(day=1)
    unposted_count = JournalEntry.objects.filter(is_posted=False, date__month=today.month, date__year=today.year).count()
    context = {
        'month': current_month,
        'unposted_entries': unposted_count,
        'can_close': unposted_count == 0,
    }
    return render(request, 'accounting/period_close_month.html', context)


@login_required
@require_perm('accounting.add_periodadjustment')
def period_adjustments(request):
    """قائمة تسويات نهاية الفترة (Placeholder).
    سيستبدل لاحقاً بواجهة إضافة/عرض قيود التسويات المتكررة أو الآلية.
    """
    adjustments = []  # لاحقاً: جلب من نموذج PeriodAdjustment إن وجد
    context = {'adjustments': adjustments}
    return render(request, 'accounting/period_adjustments.html', context)


@login_required
@require_perm('accounting.manage_recurring')
def recurring_journal_entries(request):
    """عرض القيود المتكررة (Placeholder) لحين تنفيذ نموذج فعلي.
    """
    try:
        from .models import JournalEntryTemplate
    except Exception:
        templates = []
    else:
        templates = JournalEntryTemplate.objects.all()[:200]
    context = {'templates': templates}
    return render(request, 'accounting/recurring_journal_entries.html', context)


@login_required
def badges_view(request):
    """إرجاع قيم الشارات (مع كاش قصير) بصيغة JSON.

    الشارات الحالية:
        - draft_journal_count: القيود غير المرحلة.
        - unposted_journal_entries_count: alias.
        - pending_purchase_orders_count: أوامر شراء لم تُستكمل.
        - aging_receivables_count: عدد عملاء لديهم ذمم متأخرة (تقديري سريع).
        - aging_payables_pending: عدد موردين لديهم التزامات متأخرة.
        - bank_reconcile_pending: حسابات بنكية بها حركات غير مسوّاة.
    يتم تخزين النتيجة 15 ثانية في ذاكرة العملية (in-process cache).
    """
    from django.core.cache import cache
    cache_key = 'acc_badges_v2'
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached, json_dumps_params={'ensure_ascii': False})

    # احصاء القيود غير المرحلة
    try:
        draft_journal_count = JournalEntry.objects.filter(is_posted=False).count()
    except Exception:
        draft_journal_count = 0

    # أوامر شراء قيد التنفيذ
    try:
        from purchases.models import PurchaseOrder
        pending_purchase_orders_count = PurchaseOrder.objects.filter(status__in=['draft','confirmed','partial']).count()
    except Exception:
        pending_purchase_orders_count = 0

    # Aging Receivables: تقدير بسيط (عملاء لديهم فواتير أقدم من 30 يوم غير مدفوعة بالكامل)
    try:
        from sales.models import Invoice
        from django.utils import timezone
        from django.db.models import F
        threshold = timezone.now().date() - timedelta(days=30)
        aging_receivables_count = Invoice.objects.filter(
            is_deleted=False, 
            due_date__lt=threshold, 
            paid__lt=F('cached_total') - F('discount')
        ).values('customer_id').distinct().count()
    except Exception:
        aging_receivables_count = 0

    # Aging Payables: فواتير شراء متأخرة (موردين)
    try:
        from purchases.models import PurchaseBill
        from django.utils import timezone
        from django.db.models import Sum as DSum
        threshold2 = timezone.now().date() - timedelta(days=30)
        # PurchaseBill لا يحتوي على due_date - نستخدم date بدلاً منها
        # ونحسب remaining من total - paid
        from purchases.models import PurchaseItem
        aging_bills = PurchaseBill.objects.filter(
            status='posted', 
            date__lt=threshold2,
            is_deleted=False
        ).annotate(
            item_total=DSum('items__total')
        ).exclude(paid__gte=models.F('item_total') - models.F('discount'))
        aging_payables_pending = aging_bills.values('supplier_id').distinct().count()
    except Exception:
        aging_payables_pending = 0

    # Bank Reconcile Pending: حسابات بنكية لديها معاملات غير مسوّاة
    try:
        from accounting.models import BankTransaction
        bank_reconcile_pending = BankTransaction.objects.filter(is_reconciled=False).values('account_id').distinct().count()
    except Exception:
        bank_reconcile_pending = 0

    data = {
        'draft_journal_count': draft_journal_count,
        'unposted_journal_entries_count': draft_journal_count,
        'pending_purchase_orders_count': pending_purchase_orders_count,
        'aging_receivables_count': aging_receivables_count,
        'aging_payables_pending': aging_payables_pending,
        'bank_reconcile_pending': bank_reconcile_pending,
        'draft_journal_url': reverse('accounting:journal_drafts_list'),
        'ts': datetime.utcnow().isoformat() + 'Z'
    }
    cache.set(cache_key, data, 15)
    return JsonResponse(data, json_dumps_params={'ensure_ascii': False})


@login_required
def fiscal_year_list(request):
    """قائمة السنوات المالية"""
    fiscal_years = FiscalYear.objects.all().order_by('-start_date')
    return render(request, 'accounting/fiscal_years/list.html', {'fiscal_years': fiscal_years})


@login_required
def fiscal_year_create(request):
    """إنشاء سنة مالية جديدة وتعيينها نشطة.

    الحقول: name, start_date, end_date, is_active (افتراضياً نعم). يمنع التداخل البسيط.
    """
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        make_active = True  # نعينها نشطة دائماً لإنهاء التنبيه في اللوحة
        try:
            sd = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            ed = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if ed < sd:
                raise ValueError('تاريخ النهاية يجب أن يكون بعد البداية')
        except Exception:
            messages.error(request, 'تواريخ غير صالحة، استخدم صيغة YYYY-MM-DD')
            return render(request, 'accounting/fiscal_year_form.html', {
                'name': name, 'start_date': start_date_str, 'end_date': end_date_str,
            })

        # منع تداخل التواريخ بشكل مبسط
        overlap = FiscalYear.objects.filter(
            models.Q(start_date__lte=ed) & models.Q(end_date__gte=sd)
        ).exists()
        if overlap:
            messages.error(request, 'هناك سنة مالية تتداخل مع هذه الفترة')
        elif not name:
            messages.error(request, 'الاسم مطلوب')
        else:
            fy = FiscalYear(name=name, start_date=sd, end_date=ed, is_active=make_active)
            fy.save()
            messages.success(request, 'تم إنشاء السنة المالية وتفعيلها')
            return redirect('accounting:dashboard')

    # افتراضات ملائمة: بداية ونهاية السنة الحالية
    today = date.today()
    default_start = today.replace(month=1, day=1)
    default_end = today.replace(month=12, day=31)
    return render(request, 'accounting/fiscal_year_form.html', {
        'default_name': f'FY {today.year}',
        'default_start': default_start.strftime('%Y-%m-%d'),
        'default_end': default_end.strftime('%Y-%m-%d'),
    })


@login_required
def pending_purchase_invoices(request):
    """عرض 'فواتير قيد التنفيذ' : أوامر شراء لم تُكتمل محاسبياً.

    التعريف: أمر شراء حالته draft/confirmed/partial ولم يتم ترحيل الفاتورة الناتجة (bill.status != posted)
    أو لا يوجد فاتورة بعد.
    يدعم ?supplier= للفلترة و ?status= لحالات الأمر (draft/confirmed/partial).
    """
    from purchases.models import PurchaseOrder
    supplier_query = (request.GET.get('supplier') or '').strip()
    status_filter = (request.GET.get('status') or '').strip()
    search_q = (request.GET.get('q') or '').strip()
    qs = PurchaseOrder.objects.select_related('supplier','bill').filter(status__in=['draft','confirmed','partial']).filter(
        models.Q(bill__isnull=True) | ~models.Q(bill__status='posted')
    )
    # فلترة المورد: اسم جزئي أو ID
    if supplier_query:
        if supplier_query.isdigit():
            qs = qs.filter(supplier_id=int(supplier_query))
        else:
            qs = qs.filter(supplier__name__icontains=supplier_query)
    if status_filter in ['draft','confirmed','partial']:
        qs = qs.filter(status=status_filter)
    # بحث عام: رقم الأمر / اسم المورد / رقم فاتورة الشراء (إن وجدت)
    if search_q:
        qs = qs.filter(
            Q(number__icontains=search_q) |
            Q(supplier__name__icontains=search_q) |
            Q(bill__number__icontains=search_q)
        )
    orders = qs.order_by('-date','-id')[:300]
    context = {
        'orders': orders,
        'supplier_id': supplier_query,
        'status_filter': status_filter,
        'search_q': search_q,
    }
    return render(request, 'accounting/pending_purchase_invoices.html', context)


@login_required
def supplier_statement(request, supplier_id):
    """عرض كشف حساب مورد مبسط (فواتير مشتريات + مدفوعات عامة)."""
    try:
        from partners.models import Supplier
    except Exception:
        messages.error(request, 'نموذج المورد غير متاح حالياً')
        return redirect('accounting:dashboard')
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    date_from = request.GET.get('date_from') or None
    date_to = request.GET.get('date_to') or None
    from datetime import datetime as _dt
    def _parse(d):
        if not d: return None
        try:
            return _dt.strptime(d, '%Y-%m-%d').date()
        except Exception:
            return None
    df = _parse(date_from)
    dt = _parse(date_to)
    # استيراد متأخر لتقليل أخطاء التحميل في حال تعطل services
    try:
        from .services import build_supplier_statement  # type: ignore
    except Exception:  # pragma: no cover
        def build_supplier_statement(*a, **kw):  # type: ignore
            return {'opening_balance': 0, 'invoices': [], 'payments': [], 'balance': 0, 'aging': {}}
    statement = build_supplier_statement(supplier, date_from=df, date_to=dt)
    ctx = { 'supplier': supplier, **statement }
    return render(request, 'accounting/supplier_statement.html', ctx)


@login_required
def chart_of_accounts(request):
    """عرض شجرة/دليل الحسابات مع دعم الفلترة بالنوع والبحث.

    يدعم المعاملات:
    - type: نوع الحساب (asset/liability/equity/revenue/expense)
    - search: جزء من الاسم أو الكود
    - status: active/inactive
    """
    qs = Account.objects.all()

    # فلترة حسب الحالة
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    selected_type = request.GET.get('type') or ''
    if selected_type:
        qs = qs.filter(account_type=selected_type)

    search_query = (request.GET.get('search') or '').strip()
    if search_query:
        qs = qs.filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query)
        )

    accounts = qs.select_related('parent').prefetch_related('children').order_by('code')
    account_types = Account._meta.get_field('account_type').choices
    
    # إحصائيات سريعة
    stats = {
        'assets': Account.objects.filter(account_type='asset').count(),
        'liabilities': Account.objects.filter(account_type='liability').count(),
        'revenues': Account.objects.filter(account_type='revenue').count(),
        'expenses': Account.objects.filter(account_type='expense').count(),
    }

    context = {
        'accounts': accounts,
        'account_types': account_types,
        'selected_type': selected_type,
        'search_query': search_query,
        'stats': stats,
    }
    return render(request, 'accounting/chart_of_accounts.html', context)


@login_required
def expense_accounts(request):
    """عرض سريع لحسابات المصروفات فقط (اختصار من دليل الحسابات)."""
    # إعادة توجيه مع معامل الفلترة type=expense لاستخدام نفس منطق دليل الحسابات
    from django.urls import reverse
    if request.GET.get('type') == 'expense':
        return chart_of_accounts(request)
    return redirect(f"{reverse('accounting:chart_of_accounts')}?type=expense")


@login_required
def account_details(request, pk):
    """تفاصيل حساب (JSON) للاستخدام في النافذة المنبثقة.

    يرجع:
      {
        id, code, name, type, balance, debits, credits, can_post,
        recent_entries: [ {date, number, description, debit, credit, amount, entry_id} ]
      }
    """
    account = get_object_or_404(Account, pk=pk, is_active=True)

    # تجميع الحركات (إرشاد للمحلل الساكن حول علاقة العكس)
    items_qs = cast('QuerySet[JournalEntryItemType]', account.journal_entries)
    items_qs = items_qs.select_related('journal_entry').order_by('-journal_entry__date', '-journal_entry__id')[:15]
    debits_total = cast('QuerySet[JournalEntryItemType]', account.journal_entries).filter(type='debit').aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
    credits_total = cast('QuerySet[JournalEntryItemType]', account.journal_entries).filter(type='credit').aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    # توازن حسب نوع الحساب (نفس منطق الخاصية balance لكن بدون تنفيذ استعلامين منفصلين إضافيين)
    if account.account_type in ['asset', 'expense']:
        balance = debits_total - credits_total
    else:
        balance = credits_total - debits_total

    recent_entries = []
    for it in items_qs:
        je = it.journal_entry
        recent_entries.append({
            'id': it.id,
            'entry_id': int(je.pk),
            'date': je.date.strftime('%Y-%m-%d'),
            'number': je.number,
            'description': it.description or je.description[:60],
            'type': it.type,
            'amount': float(it.amount),
            'debit': float(it.amount) if it.type == 'debit' else 0.0,
            'credit': float(it.amount) if it.type == 'credit' else 0.0,
        })

    data = {
        'id': int(account.pk),
        'code': account.code,
        'name': account.name,
        'type': account.account_type,
        'type_display': getattr(account, 'get_account_type_display', lambda: account.account_type)(),
        'can_post': account.can_post,
        'debits': float(debits_total),
        'credits': float(credits_total),
        'balance': float(balance),
        'recent_entries': recent_entries,
    }
    return JsonResponse({'success': True, 'account': data}, json_dumps_params={'ensure_ascii': False})


@login_required
def journal_drafts_list(request):
    """قائمة القيود غير المرحلة (مسودات) مع فلترة بسيطة وترقيم.

    المعاملات المدعومة:
      - q: نص بحث في رقم القيد / الوصف / المرجع
      - type: نوع القيد (manual, sales, purchase, payment, receipt, adjustment)
      - date_from / date_to: نطاق التاريخ
      - page / page_size: ترقيم
    """
    qs = JournalEntry.objects.filter(is_posted=False).order_by('-date', '-id')
    search_q = (request.GET.get('q') or '').strip()
    if search_q:
        qs = qs.filter(
            Q(number__icontains=search_q) | Q(description__icontains=search_q) | Q(reference__icontains=search_q)
        )
    entry_type = (request.GET.get('type') or '').strip()
    if entry_type in dict(JournalEntry.ENTRY_TYPE):
        qs = qs.filter(entry_type=entry_type)
    from django.utils.dateparse import parse_date
    df_raw = request.GET.get('date_from') or ''
    dt_raw = request.GET.get('date_to') or ''
    df = parse_date(df_raw) if df_raw else None
    dt = parse_date(dt_raw) if dt_raw else None
    if df:
        qs = qs.filter(date__gte=df)
    if dt:
        qs = qs.filter(date__lte=dt)
    try:
        page = max(1, int(request.GET.get('page', '1')))
    except ValueError:
        page = 1
    try:
        page_size = int(request.GET.get('page_size', '50'))
    except ValueError:
        page_size = 50
    page_size = min(max(10, page_size), 200)
    total = qs.count()
    offset = (page - 1) * page_size
    entries = qs.select_related('created_by')[offset: offset + page_size]
    total_pages = (total // page_size) + (1 if total % page_size else 0)
    # CSV Export
    if request.GET.get('export') == 'csv':
        import csv
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="journal_drafts.csv"'
        writer = csv.writer(resp)
        writer.writerow(['id','number','date','type','description','total_debit','total_credit','balanced'])
        for je in qs.select_related('created_by')[:5000]:
            writer.writerow([je.id, je.number, je.date, je.entry_type, je.description[:100], je.total_debit, je.total_credit, 'Y' if je.is_balanced else 'N'])
        return resp
    context = {
        'entries': entries,
        'search_q': search_q,
        'entry_type': entry_type,
        'date_from': df_raw,
        'date_to': dt_raw,
        'page': page,
        'page_size': page_size,
        'offset': offset,
        'total': total,
        'total_pages': total_pages,
        'entry_types': JournalEntry.ENTRY_TYPE,
        'print_mode': request.GET.get('print') == '1',
    }
    if request.GET.get('print') == '1':
        return render(request, 'accounting/journal_drafts_list_print.html', context)
    return render(request, 'accounting/journal_drafts_list.html', context)


@login_required
def journal_drafts_bulk_post(request):
    """ترحيل جماعي لمسودات قيود محددة.

    يقبل POST مع حقل entries[] = قائمة أرقام/معرّفات القيود.
    يتحقق من توازن كل قيد قبل الترحيل ويتجاوز غير المتوازن.
    يعيد JSON (للاستخدام AJAX) أو يعيد توجيه إذا طلب متصفح HTML.
    """
    if request.method != 'POST':
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])
    # نقبل كل من entries[], ids و ids[] للتوافق مع الواجهة الحالية
    ids = []
    if request.POST.getlist('ids'):
        ids = request.POST.getlist('ids')
    elif request.POST.getlist('ids[]'):
        ids = request.POST.getlist('ids[]')
    else:
        ids = request.POST.getlist('entries') or request.POST.getlist('entries[]')
    from django.http import JsonResponse
    success = []
    skipped = []
    from django.db import transaction
    for raw_id in ids:
        if not raw_id.isdigit():
            skipped.append({'id': raw_id, 'reason': 'معرّف غير صالح'})
            continue
        try:
            je = JournalEntry.objects.get(pk=int(raw_id), is_posted=False)
        except JournalEntry.DoesNotExist:
            skipped.append({'id': raw_id, 'reason': 'غير موجود أو مرحّل'})
            continue
        if not je.is_balanced:
            skipped.append({'id': je.id, 'reason': 'غير متوازن'})
            continue
        try:
            with transaction.atomic():
                je.is_posted = True
                je.save(update_fields=['is_posted'])
                # سجل تدقيق إذا توفر
                try:
                    from core.models import AuditLog
                    AuditLog.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        action=AuditLog.ACTION_UPDATE if hasattr(AuditLog, 'ACTION_UPDATE') else 'update',
                        model_name='JournalEntry',
                        app_label='accounting',
                        object_id=str(je.pk),
                        object_repr=str(je),
                        changes={'bulk_post': True},
                    )
                except Exception:
                    pass
                success.append(je.id)
        except Exception as e:  # pragma: no cover
            skipped.append({'id': je.id, 'reason': str(e)})
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        return JsonResponse({'success_ids': success, 'skipped': skipped}, json_dumps_params={'ensure_ascii': False})
    from django.contrib import messages
    if success:
        messages.success(request, f'تم ترحيل {len(success)} قيود.')
    if skipped:
        messages.warning(request, f'تم تجاهل {len(skipped)} قيود غير صالحة/غير متوازنة.')
    from django.shortcuts import redirect
    return redirect('accounting:journal_drafts_list')


@login_required
@require_perm('accounting.add_account')
def account_create(request):
    """إنشاء حساب جديد (نموذج مبسط جداً)."""
    if request.method == 'POST':
        code = request.POST.get('code','').strip()
        name = request.POST.get('name','').strip()
        account_type = request.POST.get('account_type') or 'asset'
        parent_id = request.POST.get('parent') or None
        if not code or not name:
            messages.error(request, 'الرجاء إدخال كود واسم.')
        elif Account.objects.filter(code=code).exists():
            messages.error(request, 'الكود مستخدم مسبقاً.')
        else:
            parent = Account.objects.filter(pk=parent_id).first() if parent_id else None
            acc = Account.objects.create(
                code=code,
                name=name,
                account_type=account_type,
                parent=parent,
                can_post=True
            )
            messages.success(request, f'تم إنشاء الحساب {acc.code}')
            return redirect('accounting:chart_of_accounts')
    context = {
        'account_types': Account._meta.get_field('account_type').choices,
        'parent_accounts': Account.objects.order_by('code')[:500],
    }
    return render(request, 'accounting/account_form.html', context)


@login_required
@require_perm('accounting.change_account')
def account_edit(request, pk):
    """تعديل حساب قائم (نموذج مبسط)."""
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        description = (request.POST.get('description') or '').strip()
        account_type = request.POST.get('account_type') or account.account_type
        parent_id = request.POST.get('parent') or None
        if not name:
            messages.error(request, 'الاسم مطلوب')
        else:
            # منع اختيار الحساب نفسه كأب أو جعله ابناً لأحد أبنائه (تحقق بسيط)
            if parent_id and int(parent_id) == int(account.pk):
                messages.error(request, 'لا يمكن أن يكون الحساب أباً لنفسه')
            else:
                if parent_id:
                    parent_obj = Account.objects.filter(pk=parent_id).exclude(pk=account.pk).first()
                else:
                    parent_obj = None
                account.name = name
                account.description = description
                account.account_type = account_type
                if parent_obj: account.parent = parent_obj
                account.save(update_fields=['name','description','account_type','parent','updated_at'])
                messages.success(request, 'تم تحديث الحساب')
                return redirect('accounting:chart_of_accounts')
    context = {
        'edit_mode': True,
        'account': account,
        'account_types': Account._meta.get_field('account_type').choices,
    'parent_accounts': Account.objects.exclude(pk=account.pk).order_by('code')[:500],
    }
    return render(request, 'accounting/account_form.html', context)


@login_required
def journal_entries_list(request):
    """قائمة القيود مع فلترة الحالة والبحث (أحدث 200)."""
    qs = JournalEntry.objects.all()
    status = (request.GET.get('status') or '').strip().lower()
    if status == 'unposted':
        qs = qs.filter(is_posted=False)
    elif status == 'posted':
        qs = qs.filter(is_posted=True)
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(description__icontains=q) | Q(number__icontains=q))
    entries = qs.order_by('-date','-id')[:200]
    return render(request, 'accounting/journal_entries_list.html', {
        'entries': entries,
        'status': status,
        'q': q,
    })


@login_required
def journal_entry_detail(request, pk):
    je = get_object_or_404(JournalEntry, pk=pk)
    # نمرر كلا الاسمين لضمان توافق القالب (يستخدم journal_entry) وأي كود قد يعتمد على entry
    return render(request, 'accounting/journal_entry_detail.html', {
        'entry': je,
        'journal_entry': je,
        'items': cast("QuerySet[JournalEntryItemType]", je.items).select_related('account')
    })


@login_required
@require_perm('accounting.create_journal_entry')
def journal_entry_create(request):
    """إنشاء قيد محاسبي محسّن مع دعم AJAX ومميزات متقدمة."""
    from django.http import JsonResponse
    from django.db import transaction
    from decimal import InvalidOperation
    from django.core.cache import cache
    
    # التحقق من صلاحيات إضافية
    can_auto_post = request.user.has_perm('accounting.post_journal_entry')
    
    # Handle AJAX requests for account search and validation
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        action = request.GET.get('action')
        
        if action == 'search_accounts':
            query = request.GET.get('q', '').strip()[:50]  # حد أمان
            cache_key = f'acc_search:{query}'
            accounts_data = cache.get(cache_key)
            
            if accounts_data is None:
                accounts_qs = Account.objects.filter(
                    can_post=True, is_active=True
                ).filter(
                    Q(name__icontains=query) | Q(code__icontains=query)
                ).select_related('parent').order_by('code')[:100]
                
                accounts_data = [
                    {
                        'id': acc.id,
                        'code': acc.code,
                        'name': acc.name,
                        'full_name': f"{acc.code} - {acc.name}",
                        'account_type': acc.account_type,
                        'requires_cost_center': acc.requires_cost_center,
                        'balance': float(acc.balance) if hasattr(acc, 'balance') else 0.0,
                        'parent_name': acc.parent.name if acc.parent else None
                    }
                    for acc in accounts_qs
                ]
                cache.set(cache_key, accounts_data, 300)  # 5 دقائق
                
            return JsonResponse({'accounts': accounts_data})
        
        elif action == 'validate_entry':
            # التحقق من صحة القيد قبل الإرسال
            try:
                items = request.GET.getlist('items[]')
                total_debit = Decimal('0')
                total_credit = Decimal('0')
                errors = []
                
                for item_data in items:
                    # parse item data (simplified)
                    parts = item_data.split('|')
                    if len(parts) >= 3:
                        account_id, amount_str, entry_type = parts[0], parts[1], parts[2]
                        try:
                            amount = Decimal(amount_str)
                            if entry_type == 'debit':
                                total_debit += amount
                            else:
                                total_credit += amount
                        except InvalidOperation:
                            errors.append(f'مبلغ غير صالح: {amount_str}')
                
                is_balanced = abs(total_debit - total_credit) < Decimal('0.01')
                
                return JsonResponse({
                    'is_valid': len(errors) == 0 and is_balanced,
                    'is_balanced': is_balanced,
                    'total_debit': float(total_debit),
                    'total_credit': float(total_credit),
                    'errors': errors
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
    
    # Get cached data for form
    cache_timeout = 600  # 10 دقائق
    
    accounts = cache.get('acc_form_accounts')
    if accounts is None:
        accounts = Account.objects.filter(
            can_post=True, is_active=True
        ).select_related('parent').order_by('code')[:1000]
        cache.set('acc_form_accounts', accounts, cache_timeout)
    
    cost_centers_qs = cache.get('acc_form_cost_centers')
    if cost_centers_qs is None:
        cost_centers_qs = CostCenter.objects.filter(is_active=True).order_by('code')[:500]
        cache.set('acc_form_cost_centers', cost_centers_qs, cache_timeout)
    
    # قيم مميزة للحقول النصية مع كاش
    distinct_limit = 200
    analytics_cache_key = 'acc_form_analytics'
    analytics_data = cache.get(analytics_cache_key)
    
    if analytics_data is None:
        known_master_accounts = list(
            JournalEntryItem.objects.exclude(master_account__isnull=True).exclude(master_account='')
            .values_list('master_account', flat=True).distinct()[:distinct_limit]
        )
        known_analytics = list(
            JournalEntryItem.objects.exclude(analytics__isnull=True).exclude(analytics='')
            .values_list('analytics', flat=True).distinct()[:distinct_limit]
        )
        known_analytics_2 = list(
            JournalEntryItem.objects.exclude(analytics_2__isnull=True).exclude(analytics_2='')
            .values_list('analytics_2', flat=True).distinct()[:distinct_limit]
        )
        known_analytics_3 = list(
            JournalEntryItem.objects.exclude(analytics_3__isnull=True).exclude(analytics_3='')
            .values_list('analytics_3', flat=True).distinct()[:distinct_limit]
        )
        
        analytics_data = {
            'master_accounts': known_master_accounts,
            'analytics': known_analytics,
            'analytics_2': known_analytics_2,
            'analytics_3': known_analytics_3,
        }
        cache.set(analytics_cache_key, analytics_data, cache_timeout)

    if request.method == 'POST':
        # Enhanced form processing with better error handling
        try:
            with transaction.atomic():
                # Basic validation
                desc = (request.POST.get('description') or '').strip()
                if not desc:
                    raise ValueError('وصف القيد مطلوب')
                
                reference = (request.POST.get('reference') or '').strip()
                entry_type = request.POST.get('entry_type') or 'manual'
                auto_post = request.POST.get('auto_post') == 'on' and can_auto_post
                
                # Parse date
                date_str = request.POST.get('date')
                try:
                    from datetime import datetime as _dt
                    je_date = _dt.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
                except Exception:
                    je_date = date.today()
                
                # Validate fiscal year if auto-posting
                if auto_post:
                    fy = FiscalYear.objects.filter(
                        start_date__lte=je_date, 
                        end_date__gte=je_date, 
                        is_closed=False
                    ).first()
                    if not fy:
                        raise ValueError('التاريخ خارج نطاق سنة مالية نشطة')
                
                # Parse items with enhanced validation
                account_ids = request.POST.getlist('account[]')
                types = request.POST.getlist('type[]')
                amounts_raw = request.POST.getlist('amount[]')
                item_descs = request.POST.getlist('item_description[]')
                cost_center_ids = request.POST.getlist('cost_center[]')
                master_accounts = request.POST.getlist('master_account[]')
                analytics_list = request.POST.getlist('analytics[]')
                analytics2_list = request.POST.getlist('analytics_2[]')
                analytics3_list = request.POST.getlist('analytics_3[]')
                
                if len(account_ids) < 2:
                    raise ValueError('يجب إدخال بندين على الأقل')
                
                # Validate and prepare items
                items_data = []
                total_debit = Decimal('0')
                total_credit = Decimal('0')
                
                for idx, (acc_id, t, amt_str) in enumerate(zip(account_ids, types, amounts_raw)):
                    if not acc_id or not t or not amt_str:
                        continue  # Skip empty rows
                    
                    try:
                        amt = Decimal(amt_str.replace(',', ''))
                        if amt <= 0:
                            raise ValueError(f'المبلغ يجب أن يكون أكبر من صفر (سطر {idx+1})')
                    except (InvalidOperation, ValueError) as e:
                        raise ValueError(f'مبلغ غير صالح في السطر {idx+1}: {amt_str}')
                    
                    # Validate account
                    try:
                        account = Account.objects.get(id=int(acc_id), can_post=True, is_active=True)
                    except Account.DoesNotExist:
                        raise ValueError(f'حساب غير صالح في السطر {idx+1}')
                    
                    # Handle cost center
                    cc_val = None
                    if idx < len(cost_center_ids) and cost_center_ids[idx]:
                        try:
                            cc_val = int(cost_center_ids[idx])
                            # Validate cost center exists
                            if not CostCenter.objects.filter(id=cc_val, is_active=True).exists():
                                cc_val = None
                        except (ValueError, TypeError):
                            cc_val = None
                    
                    # Check if account requires cost center
                    if account.requires_cost_center and not cc_val and not account.default_cost_center:
                        raise ValueError(f'الحساب {account.name} يتطلب تحديد مركز تكلفة')
                    
                    item_data = {
                        'account_id': int(acc_id),
                        'type': t,
                        'amount': amt,
                        'description': (item_descs[idx] if idx < len(item_descs) else '').strip()[:255],
                        'cost_center_id': cc_val,
                        'master_account': (master_accounts[idx] if idx < len(master_accounts) else '').strip()[:200],
                        'analytics': (analytics_list[idx] if idx < len(analytics_list) else '').strip()[:200],
                        'analytics_2': (analytics2_list[idx] if idx < len(analytics2_list) else '').strip()[:200],
                        'analytics_3': (analytics3_list[idx] if idx < len(analytics3_list) else '').strip()[:200],
                    }
                    items_data.append(item_data)
                    
                    if t == 'debit':
                        total_debit += amt
                    else:
                        total_credit += amt
                
                if not items_data:
                    raise ValueError('لا توجد بنود صالحة في القيد')
                
                # Check if balanced
                if abs(total_debit - total_credit) >= Decimal('0.01'):
                    if auto_post:
                        raise ValueError('لا يمكن ترحيل قيد غير متوازن')
                    else:
                        messages.warning(request, 'تحذير: القيد غير متوازن')
                
                # Create journal entry
                je = JournalEntry.objects.create(
                    date=je_date,
                    entry_type=entry_type if entry_type in dict(JournalEntry.ENTRY_TYPE) else 'manual',
                    description=desc,
                    reference=reference,
                    created_by=request.user,
                    is_posted=False,  # Will be posted later if needed
                )
                
                # Create items
                for item_data in items_data:
                    cost_center = None
                    if item_data['cost_center_id']:
                        cost_center = CostCenter.objects.filter(
                            id=item_data['cost_center_id'], is_active=True
                        ).first()
                    
                    JournalEntryItem.objects.create(
                        journal_entry=je,
                        account_id=item_data['account_id'],
                        type=item_data['type'],
                        amount=item_data['amount'],
                        description=item_data['description'] or desc,
                        cost_center=cost_center,
                        master_account=item_data['master_account'],
                        analytics=item_data['analytics'],
                        analytics_2=item_data['analytics_2'],
                        analytics_3=item_data['analytics_3'],
                    )
                
                # Auto-post if requested and balanced
                if auto_post and je.is_balanced:
                    je.is_posted = True
                    je.full_clean()
                    je.save(update_fields=['is_posted'])
                
                # Clear relevant caches
                cache.delete_pattern('acc_form_*')
                
                success_msg = f'تم إنشاء القيد {je.number}'
                if je.is_posted:
                    success_msg += ' وترحيله بنجاح'
                else:
                    success_msg += ' كمسودة'
                    
                messages.success(request, success_msg)
                
                # Handle AJAX response
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': success_msg,
                        'journal_entry_id': je.id,
                        'redirect_url': reverse('accounting:journal_entry_detail', args=[je.pk])
                    })
                
                return redirect('accounting:journal_entry_detail', pk=je.pk)
                
        except Exception as e:
            error_msg = f'فشل إنشاء القيد: {str(e)}'
            messages.error(request, error_msg)
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)

    # Enhanced context with additional data
    context = {
        'accounts': accounts,
        'today': date.today(),
        'entry_types': JournalEntry.ENTRY_TYPE,
        'cost_centers': cost_centers_qs,
        'can_auto_post': can_auto_post,
        'fiscal_years': FiscalYear.objects.filter(is_active=True)[:5],
        'recent_entries': JournalEntry.objects.filter(
            created_by=request.user
        ).order_by('-created_at')[:5],
        **analytics_data,
    }
    return render(request, 'accounting/journal_entry_form.html', context)


@login_required
@require_perm('accounting.post_journal_entry')
def post_journal_entry(request, pk):
    je = get_object_or_404(JournalEntry, pk=pk)
    if request.method == 'POST':
        if je.is_posted:
            messages.info(request, 'القيد مرحل مسبقاً.')
            return redirect('accounting:journal_entry_detail', pk=pk)
        try:
            from .services import post_journal_entry as svc_post  # type: ignore
            svc_post(je, force=False)
            messages.success(request, 'تم ترحيل القيد بنجاح.')
        except ValidationError as ve:  # type: ignore
            messages.error(request, f'فشل الترحيل: {ve}')
        except Exception as e:  # pragma: no cover
            messages.error(request, f'خطأ غير متوقع أثناء الترحيل: {e}')
        return redirect('accounting:journal_entry_detail', pk=pk)
    return render(request, 'accounting/journal_entry_post_confirm.html', {'entry': je})


@login_required
@require_perm('accounting.post_journal_entry')
def reverse_journal_entry(request, pk):
    """إنشاء قيد عكسي لقيد مرحل (بدون حذف الأصلي)."""
    je = get_object_or_404(JournalEntry, pk=pk)
    if request.method == 'POST':
        try:
            from .journal_service import JournalService  # type: ignore
            rev = JournalService.reverse(je, user=request.user)
            messages.success(request, f'تم إنشاء القيد العكسي {rev.number} بنجاح.')
            return redirect('accounting:journal_entry_detail', pk=rev.pk)
        except Exception as e:  # pragma: no cover
            messages.error(request, f'فشل إنشاء القيد العكسي: {e}')
            return redirect('accounting:journal_entry_detail', pk=je.pk)
    return render(request, 'accounting/journal_entry_reverse_confirm.html', {'entry': je})


@login_required
def general_ledger(request):
    """دفتر الأستاذ العام.

    يدعم عرض صفحة اختيار الحساب (قائمة منسدلة) مع فلترة بالمدى التاريحي.
    - عند وجود ?account=ID يعرض حركات ذلك الحساب (entries) ويمرر متغيرات القالب
      المستخدمة في `templates/accounting/general_ledger.html` مثل:
        accounts, selected_account, entries, balance, date_from, date_to
    - عند غياب معامل account يعيد سلوك بسيط سابق (قائمة حسابات مع آخر حركات)
    """
    from django.utils.dateparse import parse_date

    # قائمة الحسابات للقائمة المنسدلة
    accounts = Account.objects.filter(is_active=True).only('id','code','name','account_type').order_by('code')[:500]

    account_id = request.GET.get('account') or ''
    date_from = request.GET.get('date_from') or None
    date_to = request.GET.get('date_to') or None

    # إذا طُلب عرض حساب معين
    if account_id and account_id.isdigit():
        selected_account = Account.objects.filter(pk=int(account_id), is_active=True).first()
        if not selected_account:
            # لا نرمي 404 هنا لأن القالب يعرض رسالة ودليل الحسابات
            return render(request, 'accounting/general_ledger.html', {
                'accounts': accounts,
                'selected_account': None,
            })

        # بناء الاستعلام على بنود دفتر اليومية المرتبطة بالحساب
        items_qs = cast("QuerySet[JournalEntryItemType]", selected_account.journal_entries)
        items_qs = items_qs.select_related('journal_entry', 'account').defer('journal_entry__description')
        # فلترة بالتاريخ إذا وُجد
        if date_from:
            df = parse_date(date_from)
            if df:
                items_qs = items_qs.filter(journal_entry__date__gte=df)
        if date_to:
            dt = parse_date(date_to)
            if dt:
                items_qs = items_qs.filter(journal_entry__date__lte=dt)

        # تقسيم (pagination) بسيط بالمعامل page و page_size (حد أقصى 500)
        try:
            page = max(1, int(request.GET.get('page', '1')))
        except ValueError:
            page = 1
        try:
            page_size = int(request.GET.get('page_size', '100'))
        except ValueError:
            page_size = 100
        page_size = min(max(10, page_size), 500)
        offset = (page - 1) * page_size
        entries_qs = items_qs.order_by('-journal_entry__date', '-journal_entry__id')
        total_count = entries_qs.count()
        entries = entries_qs[offset: offset + page_size]

        context = {
            'accounts': accounts,
            'selected_account': selected_account,
            'entries': entries,
            'page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': (total_count // page_size) + (1 if total_count % page_size else 0),
            'balance': selected_account.balance,
            'date_from': date_from,
            'date_to': date_to,
        }
        return render(request, 'accounting/general_ledger.html', context)

    # الوضع الافتراضي: إظهار ملخص لعدة حسابات (سلوك سابق)
    data = []
    qs = Account.objects.filter(is_active=True).order_by('code')[:50]
    for acc in qs:
        je_items_qs = cast("QuerySet[JournalEntryItemType]", acc.journal_entries)
        items = je_items_qs.select_related('journal_entry').order_by('-journal_entry__date')[:20]
        data.append({'account': acc, 'balance': acc.balance, 'items': items})
    return render(request, 'accounting/general_ledger.html', {'accounts_data': data, 'accounts': accounts})


@login_required
def trial_balance(request):
    """ميزان المراجعة (مبسط)."""
    rows = []
    total_debit = Decimal('0'); total_credit = Decimal('0')
    try:
        page = max(1, int(request.GET.get('page', '1')))
    except ValueError:
        page = 1
    try:
        page_size = int(request.GET.get('page_size', '200'))
    except ValueError:
        page_size = 200
    page_size = min(max(50, page_size), 1000)
    qs_all = Account.objects.filter(is_active=True).order_by('code')
    total_accounts = qs_all.count()
    offset = (page - 1) * page_size
    qs = qs_all[offset: offset + page_size]
    for acc in qs:
        bal = acc.balance
        debit = credit = Decimal('0')
        if acc.account_type in ['asset','expense']:
            if bal >= 0:
                debit = bal
            else:
                credit = -bal
        else:
            if bal >= 0:
                credit = bal
            else:
                debit = -bal
        total_debit += debit; total_credit += credit
        rows.append({'account': acc, 'debit': debit, 'credit': credit})
    
    # Support JSON format
    if request.GET.get('format') == 'json':
        return JsonResponse({
            'rows': [{'account_id': r['account'].id, 'account_code': r['account'].code, 
                      'account_name': r['account'].name, 'debit': str(r['debit']), 
                      'credit': str(r['credit'])} for r in rows],
            'total_debit': str(total_debit),
            'total_credit': str(total_credit),
            'page': page,
            'page_size': page_size,
            'total_accounts': total_accounts,
            'total_pages': (total_accounts // page_size) + (1 if total_accounts % page_size else 0),
        })
    
    context = {
        'rows': rows,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'page': page,
        'page_size': page_size,
        'total_accounts': total_accounts,
        'total_pages': (total_accounts // page_size) + (1 if total_accounts % page_size else 0),
    }
    return render(request, 'accounting/trial_balance.html', context)


@login_required
def balance_sheet(request):
    """الميزانية العمومية (مبسطة جداً)."""
    assets = []; liabilities = []; equity = []
    for acc in Account.objects.filter(is_active=True):
        bal = acc.balance
        if acc.account_type == 'asset':
            assets.append((acc, bal))
        elif acc.account_type == 'liability':
            liabilities.append((acc, bal))
        elif acc.account_type == 'equity':
            equity.append((acc, bal))
    context = {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': sum(b for _, b in assets),
        'total_liabilities_equity': sum(b for _, b in liabilities) + sum(b for _, b in equity),
    }
    return render(request, 'accounting/balance_sheet.html', context)


# ==============================================
# تكامل موديول المبيعات داخل واجهة الحسابات
# ==============================================
from django.contrib.auth.decorators import permission_required


@login_required
def sales_payments_overview(request):
    """عرض مبسط لآخر (50) دفعة فواتير مبيعات لسهولة الوصول من قسم الحسابات."""
    try:
        from sales.models import InvoicePayment
    except Exception:
        rows = []
    else:
        qs = (InvoicePayment.objects
              .select_related('invoice__customer', 'invoice')
              .order_by('-id')[:50])
        rows = [
            {
                'id': p.id,
                'invoice_id': getattr(p.invoice, 'id', ''),
                'invoice_number': getattr(p.invoice, 'number', ''),
                'customer': getattr(getattr(p.invoice, 'customer', None), 'name', ''),
                'amount': p.amount,
                'date': p.date,
                'sequence': p.monthly_sequence,
                'printed_count': p.printed_count,
            } for p in qs
        ]
    return render(request, 'accounting/sales_payments_overview.html', {'payments': rows})


@login_required
def sales_customer_statement(request, customer_id):
    """عرض كشف حساب عميل من داخل قسم الحسابات (يُعيد استخدام نفس المنطق)."""
    if Customer is None:
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound('النظام غير جاهز بعد')
    customer = get_object_or_404(Customer, pk=customer_id)
    from django.utils.dateparse import parse_date
    date_from = parse_date(request.GET.get('date_from')) if request.GET.get('date_from') else None
    date_to = parse_date(request.GET.get('date_to')) if request.GET.get('date_to') else None
    if date_from and not date_to:
        from datetime import date as _d
        date_to = _d.today()
    try:
        from sales.utils import build_customer_statement  # type: ignore
    except Exception:
        def build_customer_statement(*a, **kw):  # type: ignore
            return {'opening_balance': 0, 'invoices': [], 'payments': [], 'balance': 0, 'aging': {}}
    statement = build_customer_statement(customer, date_from=date_from, date_to=date_to)
    ctx = {'customer': customer, **statement}
    # السماح بالطباعة بنفس صلاحية المبيعات
    if request.GET.get('print') == '1':
        if not request.user.has_perm('sales.print_customerstatement'):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('ليست لديك صلاحية طباعة كشف الحساب')
        ctx['printed_by'] = request.user
        # تسجل عملية الطباعة في سجل التدقيق إن وُجد
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ACTION_UPDATE,
                model_name='CustomerStatement',
                app_label='sales',
                object_id=str(customer.pk),
                object_repr=str(customer),
                changes={'print': 'customer_statement_accounting'},
            )
        except Exception:
            pass
        # إعادة استخدام قالب الطباعة الخاص بالمبيعات لتوحيد الشكل
        return render(request, 'sales/customer_statement_print.html', ctx)
    # يمكن إنشاء قالب خاص بالحسابات، حالياً نعيد استخدام قالب المبيعات العادي
    return render(request, 'sales/customer_statement.html', ctx)


@login_required
def sales_customer_statement_sample(request):
    """صفحة مساعدة تعرض نموذج إدخال رقم عميل للوصول السريع لكشف الحساب من الحسابات."""
    if request.method == 'POST':
        cid = request.POST.get('customer_id')
        if cid and cid.isdigit():
            return redirect('accounting:sales_customer_statement', customer_id=int(cid))
    
    # جلب قائمة العملاء لتسهيل الاختيار
    customers = []
    try:
        from partners.models import Partner
        customers = Partner.objects.filter(
            partner_type__in=['customer', 'both']
        ).order_by('name')[:50]  # أول 50 عميل
    except (ImportError, Exception):
        pass
    
    return render(request, 'accounting/sales_customer_statement_sample.html', {
        'customers': customers,
    })

@login_required
def cash_receipt_create(request):
    """نقطة دخول بديلة داخل قسم المحاسبة لإنشاء إيصال قبض نقدي.

    تقوم بالتحقق من صلاحية إضافة دفعة مبيعات ثم تعيد التوجيه الدائم
    إلى نموذج إنشاء الإيصال في تطبيق المبيعات للحفاظ على منطق موحد.
    يُستخدم هذا لتلبية الروابط أو الاختصارات القديمة مثل /accounting/cash/receipt/.
    """
    # فحص الصلاحية (نفس الصلاحية المستخدمة في sales.receipt_create)
    if not request.user.has_perm('sales.add_invoicepayment'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('ليست لديك صلاحية إضافة إيصال قبض')
    # دعم استلام ?next أو تمرير invoice_number مباشرة
    from django.urls import reverse
    target = reverse('sales:receipt_create')
    invoice_number = request.GET.get('invoice_number')
    if invoice_number:
        # نضيفه كـ query param حتى لا نفقد سلاسة الاستخدام
        import urllib.parse
        target = f"{target}?invoice_number={urllib.parse.quote(invoice_number)}"
    # سجل تدقيق اختياري
    try:
        from core.models import AuditLog  # type: ignore
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ACTION_ACCESS if hasattr(AuditLog, 'ACTION_ACCESS') else getattr(AuditLog, 'ACTION_VIEW', AuditLog.ACTION_UPDATE),
            model_name='InvoicePayment',
            app_label='accounting',
            object_id='-',
            object_repr='CashReceiptRedirect',
            changes={'redirect_to': target}
        )
    except Exception:
        pass
    from django.http import HttpResponsePermanentRedirect
    return HttpResponsePermanentRedirect(target)

@login_required
def cash_transfer_create(request):
    from .forms import CashTransferForm
    if not request.user.has_perm('accounting.add_journalentry'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('ليست لديك صلاحية إنشاء قيد')
    if request.method == 'POST':
        form = CashTransferForm(request.POST)
        if form.is_valid():
            from_account = form.cleaned_data['from_account']
            to_account = form.cleaned_data['to_account']
            amount = form.cleaned_data['amount']
            date_val = form.cleaned_data['date']
            desc = form.cleaned_data.get('description') or f"تحويل نقدي من {from_account.code} إلى {to_account.code}"
            post_now = form.cleaned_data.get('post_now')
            from django.db import transaction
            from .models import JournalEntry, JournalEntryItem
            with transaction.atomic():
                je = JournalEntry.objects.create(
                    date=date_val,
                    entry_type='manual',
                    description=desc,
                    created_by=request.user,
                    is_posted=bool(post_now),
                )
                JournalEntryItem.objects.create(journal_entry=je, account=from_account, type='credit', amount=amount, description=desc)
                JournalEntryItem.objects.create(journal_entry=je, account=to_account, type='debit', amount=amount, description=desc)
            from django.contrib import messages
            messages.success(request, f'تم إنشاء تحويل نقدي بقيد رقم {je.number}')
            from django.urls import reverse
            return redirect(reverse('accounting:journal_entry_detail', args=[je.id]))
    else:
        initial = {}
        if request.GET.get('from_account') and request.GET.get('from_account').isdigit():
            initial['from_account'] = int(request.GET['from_account'])
        if request.GET.get('to_account') and request.GET.get('to_account').isdigit():
            initial['to_account'] = int(request.GET['to_account'])
        from datetime import date as _date
        initial.setdefault('date', _date.today())
        form = CashTransferForm(initial=initial)
    return render(request, 'accounting/cash_transfer_form.html', {'form': form})


@login_required
def cash_positions_view(request):
    if not (request.user.has_perm('accounting.view_cashposition') or request.user.is_staff):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('ليست لديك صلاحية عرض الأرصدة النقدية')
    from django.core.cache import cache
    from django.db.models import Sum, Q, F, Value, DecimalField, Max
    
    prefix = (request.GET.get('prefix') or '').strip()
    q = (request.GET.get('q') or '').strip()
    cache_key = f"cashpos:v2:{prefix}:{q}"
    result = cache.get(cache_key)
    
    if result is None or request.GET.get('refresh') == '1':
        # Filter for Asset and Liability accounts
        base = Account.objects.filter(is_active=True, can_post=True, account_type__in=['asset','liability'])
        if prefix:
            base = base.filter(code__startswith=prefix)
        if q:
            base = base.filter(Q(name__icontains=q) | Q(code__icontains=q))
            
        # Annotate sums and last transaction date
        items = base.annotate(
            debits=Sum('journal_entries__amount', filter=Q(journal_entries__type='debit')),
            credits=Sum('journal_entries__amount', filter=Q(journal_entries__type='credit')),
            last_tx_date=Max('journal_entries__journal_entry__date')
        ).order_by('code')[:500]
        
        accounts_data = []
        total_balance = Decimal('0')
        total_assets = Decimal('0')
        total_liabilities = Decimal('0')
        
        for acc in items:
            deb = acc.debits or Decimal('0')
            cre = acc.credits or Decimal('0')
            # Calculate balance based on account type
            bal = deb - cre if acc.account_type in ['asset','expense'] else cre - deb
            total_balance += bal
            
            if acc.account_type == 'asset':
                total_assets += bal
            elif acc.account_type == 'liability':
                total_liabilities += bal
                
            accounts_data.append({
                'id': acc.id, 
                'code': acc.code, 
                'name': acc.name, 
                'balance': float(bal),
                'last_tx_date': acc.last_tx_date
            })
            
        result = {
            'accounts': accounts_data, 
            'count': len(accounts_data), 
            'total_balance': float(total_balance),
            'total_assets': float(total_assets),
            'total_liabilities': float(total_liabilities),
            'net_position': float(total_balance),
            'error': None, 
            'prefix': prefix, 
            'q': q
        }
        cache.set(cache_key, result, 30)
        
    if request.GET.get('format') == 'json':
        from django.http import JsonResponse
        return JsonResponse(result, json_dumps_params={'ensure_ascii': False})
    return render(request, 'accounting/cash_positions.html', result)

def cash_flow_statement(request):
    """قائمة التدفقات النقدية المبسطة (HTML افتراضي، JSON عند ?format=json).

    تعتمد على `compute_cash_flow` لتجميع الأرقام (تشغيلي/استثماري/تمويلي)
    وتدعم: المقارنة (?compare=1) / التفصيل (?breakdown=1) / الفلاتر / التصدير / الكاش.
    """
    from .reporting import CashFlowParams, compute_cash_flow
    date_from_str = request.GET.get('date_from', date.today().replace(month=1, day=1).strftime('%Y-%m-%d'))
    date_to_str = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    cost_center_id = request.GET.get('cost_center')
    account_prefix = request.GET.get('account_prefix', '').strip()
    compare_flag = request.GET.get('compare') == '1'
    breakdown_flag = request.GET.get('breakdown') == '1'

    from django.core.cache import cache
    cache_key = None; context = None
    if not breakdown_flag and request.GET.get('no_cache','0')!='1':
        cache_key = f"acct:cashflow:{date_from_str}:{date_to_str}:{cost_center_id or 'all'}:{account_prefix}:{'cmp' if compare_flag else 'nocmp'}"
        context = cache.get(cache_key)
    if context is None:
        try:
            params = CashFlowParams(
                date_from=datetime.strptime(date_from_str,'%Y-%m-%d').date(),
                date_to=datetime.strptime(date_to_str,'%Y-%m-%d').date(),
                cost_center_id=int(cost_center_id) if cost_center_id else None,
                account_prefix=account_prefix,
                include_breakdown=breakdown_flag,
                compare_previous=compare_flag,
            )
        except ValueError:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest('Invalid date format')
        context = compute_cash_flow(params)
        if cache_key:
            cache.set(cache_key, context, 120)

    # JSON
    if request.GET.get('format') == 'json':
        from django.http import JsonResponse
        return JsonResponse(context, json_dumps_params={'ensure_ascii': False})

    # Export
    export_fmt = request.GET.get('export')
    if export_fmt in ('csv','xlsx'):
        operating=context['operating']; investing=context['investing']; financing=context['financing']; net_change=context['net_change']; prev_period=context.get('prev_period')
        if export_fmt=='csv':
            import csv
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition']=f"attachment; filename=cash_flow_{date_from_str}_{date_to_str}.csv"
            w=csv.writer(response)
            w.writerow(['القسم','التدفقات الداخلة','التدفقات الخارجة','الصافي'])
            w.writerow(['تشغيلي', f"{operating['inflows']:.2f}", f"{operating['outflows']:.2f}", f"{operating['net']:.2f}"])
            w.writerow(['استثماري', f"{investing['inflows']:.2f}", f"{investing['outflows']:.2f}", f"{investing['net']:.2f}"])
            w.writerow(['تمويلي', f"{financing['inflows']:.2f}", f"{financing['outflows']:.2f}", f"{financing['net']:.2f}"])
            w.writerow([]); w.writerow(['إجمالي التغير','','', f"{net_change:.2f}"])
            if prev_period:
                w.writerow([]); w.writerow(['-- مقارنة الفترة السابقة --']); w.writerow(['صافي سابق (تشغيلي)', f"{prev_period['operating']['net']:.2f}"])
            return response
        else:
            try:
                import openpyxl
                from openpyxl.worksheet.worksheet import Worksheet
                from io import BytesIO
                wb = openpyxl.Workbook()
                ws = cast("Worksheet", wb.active)
                ws.title = 'Cash Flow'
                if ws: ws.append(['القسم','التدفقات الداخلة','التدفقات الخارجة','الصافي'])
                if ws: ws.append(['تشغيلي', float(operating['inflows']), float(operating['outflows']), float(operating['net'])])
                if ws: ws.append(['استثماري', float(investing['inflows']), float(investing['outflows']), float(investing['net'])])
                if ws: ws.append(['تمويلي', float(financing['inflows']), float(financing['outflows']), float(financing['net'])])
                if ws: 
                    ws.append([])
                if ws: 
                    ws.append(['إجمالي التغير','','', float(net_change)])
                if prev_period:
                    if ws: 
                        ws.append([])
                    if ws: 
                        ws.append(['مقارنة الفترة السابقة'])
                    if ws: 
                        ws.append(['تشغيلي (سابق)', float(prev_period['operating']['net'])])
                bio = BytesIO(); wb.save(bio); bio.seek(0)
                resp = HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                resp['Content-Disposition'] = f"attachment; filename=cash_flow_{date_from_str}_{date_to_str}.xlsx"
                return resp
            except Exception:
                pass
    return render(request, 'accounting/cash_flow_statement.html', context)


@login_required
def accounting_settings_menu(request):
    """إعدادات المحاسبة العامة: VAT والحسابات الافتراضية + تعيينات التدفق النقدي.

    يتطلب صلاحية تغيير على وحدة المحاسبة أو superuser.
    - GET: يعرض الإعدادات الحالية والحسابات والتعيينات.
    - POST form=basic: يحدث حقول VAT والحسابات الافتراضية.
    - POST form=cashflow: ينشئ/يحدث تعيين فئة التدفق النقدي لحساب.
    """
    # فحص صلاحية مدير مالي (تغيير) أو سوبر يوزر
    has_change = False
    try:
        has_change = request.user.has_module_permission('accounting', 'change')
    except Exception:
        has_change = False
    if not (request.user.is_superuser or has_change):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('ليست لديك صلاحية للوصول إلى إعدادات المحاسبة')

    try:
        from .models import AccountingSettings, CashFlowAccountMapping
    except Exception as _imp_err:  # pragma: no cover
        messages.error(request, f'الموديلات غير متاحة حالياً: {str(_imp_err)}')
        return render(request, 'accounting/settings.html', {'settings': None, 'accounts': [], 'mappings': []})

    settings_obj = AccountingSettings.get()
    accounts = Account.objects.filter(is_active=True).order_by('code')[:2000]

    if request.method == 'POST':
        form_kind = request.POST.get('form') or 'basic'
        try:
            if form_kind == 'basic':
                settings_obj.enable_vat = (request.POST.get('enable_vat') == 'on')
                try:
                    settings_obj.default_vat_rate = Decimal((request.POST.get('default_vat_rate') or '0').replace(',', ''))
                except Exception:
                    settings_obj.default_vat_rate = Decimal('0')
                # ربط الحسابات الافتراضية (كلها اختيارية)
                def _to_int(v):
                    try:
                        return int(v) if v else None
                    except Exception:
                        return None
                settings_obj.inventory_account_id = _to_int(request.POST.get('inventory_account'))
                settings_obj.ap_account_id = _to_int(request.POST.get('ap_account'))
                settings_obj.ar_account_id = _to_int(request.POST.get('ar_account'))
                settings_obj.cash_account_id = _to_int(request.POST.get('cash_account'))
                settings_obj.vat_input_account_id = _to_int(request.POST.get('vat_input_account'))
                settings_obj.vat_output_account_id = _to_int(request.POST.get('vat_output_account'))
                settings_obj.save()
                messages.success(request, 'تم تحديث الإعدادات الأساسية')
                return redirect('accounting:settings')
            elif form_kind == 'cashflow':
                acc_id = request.POST.get('account')
                category = request.POST.get('category')
                note = (request.POST.get('note') or '').strip()
                if acc_id and category in dict(CashFlowAccountMapping.CATEGORY_CHOICES):
                    mapping, _ = CashFlowAccountMapping.objects.update_or_create(
                        account_id=int(acc_id),
                        defaults={'category': category, 'note': note}
                    )
                    messages.success(request, f'تم تحديث تعيين التدفق النقدي للحساب #{mapping.account.id}')
                    return redirect('accounting:settings')
                else:
                    messages.error(request, 'بيانات التعيين غير صالحة')
            elif form_kind == 'cashflow_delete':
                mapping_id = request.POST.get('mapping_id')
                try:
                    m = CashFlowAccountMapping.objects.get(pk=int(mapping_id))
                    m.delete()
                    messages.success(request, 'تم حذف التعيين')
                except Exception:
                    messages.error(request, 'فشل حذف التعيين')
                return redirect('accounting:settings')
        except Exception as e:
            messages.error(request, f'فشل حفظ الإعدادات: {e}')

    mappings = CashFlowAccountMapping.objects.select_related('account').order_by('account__code')
    ctx = {
        'settings': settings_obj,
        'accounts': accounts,
        'mappings': mappings,
    }
    return render(request, 'accounting/settings.html', ctx)

@login_required
def accounting_settings(request):
    """Backwards-compatible alias for settings view.

    URL patterns and reverse('accounting:settings') expect `accounting_settings`.
    Delegates to `accounting_settings_menu` to avoid breaking existing links.
    """
    return accounting_settings_menu(request)

@login_required
def income_statement(request):
    """قائمة الدخل"""
    date_from = request.GET.get('date_from', date.today().replace(month=1, day=1).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    # الإيرادات
    revenue_accounts = Account.objects.filter(account_type='revenue', is_active=True)
    revenue_data = []
    total_revenue = Decimal('0')
    
    for account in revenue_accounts:
        # حساب الرصيد في الفترة المحددة
        items = JournalEntryItem.objects.filter(
            account=account,
            journal_entry__is_posted=True,
            journal_entry__date__range=[date_from, date_to]
        )
        
        credits = items.filter(type='credit').aggregate(
            total=Sum('amount'))['total'] or Decimal('0')
        debits = items.filter(type='debit').aggregate(
            total=Sum('amount'))['total'] or Decimal('0')
        
        balance = credits - debits
        if balance > 0:
            revenue_data.append({'account': account, 'balance': balance})
            total_revenue += balance
    
    # المصروفات
    expense_accounts = Account.objects.filter(account_type='expense', is_active=True)
    expense_data = []
    total_expenses = Decimal('0')
    
    for account in expense_accounts:
        items = JournalEntryItem.objects.filter(
            account=account,
            journal_entry__is_posted=True,
            journal_entry__date__range=[date_from, date_to]
        )
        
        debits = items.filter(type='debit').aggregate(
            total=Sum('amount'))['total'] or Decimal('0')
        credits = items.filter(type='credit').aggregate(
            total=Sum('amount'))['total'] or Decimal('0')
        
        balance = debits - credits
        if balance > 0:
            expense_data.append({'account': account, 'balance': balance})
            total_expenses += balance
    
    net_income = total_revenue - total_expenses
    
    context = {
        'revenue_data': revenue_data,
        'expense_data': expense_data,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_income': net_income,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'accounting/income_statement.html', context)


@login_required
def aging_receivables_report(request):
    """تقرير أعمار الذمم (عملاء).

    المعاملات:
      - as_of: تاريخ الأساس (YYYY-MM-DD) افتراض: اليوم.
      - q: بحث جزئي في اسم العميل أو رقم الفاتورة.
      - overdue_only=1: إظهار المتأخرة فقط (>30 أو أي bucket >0).
      - export=csv: تنزيل CSV.
    """
    from django.utils import timezone
    from sales.models import Invoice
    from partners.models import Customer
    import csv, io
    from django.core.cache import cache
    as_of_str = request.GET.get('as_of') or ''
    try:
        as_of_date = datetime.strptime(as_of_str, '%Y-%m-%d').date() if as_of_str else timezone.now().date()
    except Exception:
        as_of_date = timezone.now().date()
    q = (request.GET.get('q') or '').strip()
    overdue_only = request.GET.get('overdue_only') == '1'

    invoices = Invoice.objects.filter(is_deleted=False)
    # لا يوجد حقل فعلي باسم remaining (هو property) لذا نستخدم Annotation للحساب (cached_total - discount - paid)
    from django.db.models import DecimalField, ExpressionWrapper, F
    invoices = invoices.annotate(
        remaining_amount=ExpressionWrapper(
            (F('cached_total') - F('discount') - F('paid')),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    ).filter(remaining_amount__gt=0)
    # تاريخ الاستحقاق: استخدم due_date إن وجد وإلا date
    # سنحسب الفرق بالأيام: days_overdue = (as_of_date - due_date)
    if q:
        from django.db.models import Q
        invoices = invoices.filter(
            Q(number__icontains=q) | Q(customer__name__icontains=q)
        )

    # جلب الحقول اللازمة
    invoices = invoices.select_related('customer')

    cache_allowed = request.GET.get('no_cache') != '1'
    cache_key = f"aging:recv:{as_of_date}:{q or '-'}:{'1' if overdue_only else '0'}"
    cached = cache.get(cache_key) if cache_allowed else None
    if cached:
        rows = cached['rows']
        buckets = cached['buckets']
        grand_total = cached['grand_total']
        gen_ts = cached.get('generated_ts')
        ttl = 60
        from time import time as _now
        now_ts = int(_now())
        age_seconds = max(0, now_ts - (gen_ts or now_ts))
        remaining_seconds = max(0, ttl - age_seconds)
        cache_meta = {
            'generated_ts': gen_ts,
            'age_seconds': age_seconds,
            'remaining_seconds': remaining_seconds,
            'ttl': ttl,
        }
        cache_hit = True
    else:
        # محاولة استخدام تجميع SQL شرطي (PostgreSQL فقط + وجود حقل فعلي remaining)
        aggregated_success = False
        buckets = {'c0_30': Decimal('0'), 'c31_60': Decimal('0'), 'c61_90': Decimal('0'), 'c90p': Decimal('0')}
        rows = []
        try:
            from django.db import connection
            from django.db.models import Sum, Case, When, DecimalField
            from django.db.models.functions import Coalesce
            if connection.vendor == 'postgresql':
                remaining_field_names = [f.name for f in Invoice._meta.get_fields() if hasattr(f, 'attname')]
                if 'remaining' in remaining_field_names:  # حقل فعلي
                    # حدود البوكِت
                    b30 = as_of_date - timedelta(days=30)
                    b60 = as_of_date - timedelta(days=60)
                    b90 = as_of_date - timedelta(days=90)
                    due_expr = Coalesce('due_date', 'date')
                    base = invoices.annotate(due_eff=due_expr)
                    agg_qs = base.values('customer_id', 'customer__name').annotate(
                        c0_30=Coalesce(Sum(Case(When(due_eff__gte=b60, then='remaining'), default=0, output_field=DecimalField(max_digits=18, decimal_places=2))), 0),
                        c31_60=Coalesce(Sum(Case(When(due_eff__lt=b60, due_eff__gte=b90, then='remaining'), default=0, output_field=DecimalField(max_digits=18, decimal_places=2))), 0),
                        c61_90=Coalesce(Sum(Case(When(due_eff__lt=b90, due_eff__gte=b90 - timedelta(days=30), then=0), default=0, output_field=DecimalField(max_digits=18, decimal_places=2))), 0),  # placeholder to keep structure
                    )
                    # لأن التقسيم السابق معقد، نعيد تعريف التجميع بشروط دقيقة لكل طبقة
                    agg_qs = base.values('customer_id', 'customer__name').annotate(
                        c0_30=Coalesce(Sum(Case(When(due_eff__gte=b30, then='remaining'), When(due_eff__gt=as_of_date, then='remaining'), default=0, output_field=DecimalField())), 0),
                        c31_60=Coalesce(Sum(Case(When(due_eff__lt=b30, due_eff__gte=b60, then='remaining'), default=0, output_field=DecimalField())), 0),
                        c61_90=Coalesce(Sum(Case(When(due_eff__lt=b60, due_eff__gte=b90, then='remaining'), default=0, output_field=DecimalField())), 0),
                        c90p=Coalesce(Sum(Case(When(due_eff__lt=b90, then='remaining'), default=0, output_field=DecimalField())), 0),
                        total=Coalesce(Sum('remaining'), 0),
                    )
                    tmp_rows = []
                    for r in agg_qs:
                        c0 = r['c0_30'] or Decimal('0')
                        c31 = r['c31_60'] or Decimal('0')
                        c61 = r['c61_90'] or Decimal('0')
                        c90p = r['c90p'] or Decimal('0')
                        total = r['total'] or (c0 + c31 + c61 + c90p)
                        tmp_rows.append({
                            'customer': type('CObj', (), {'id': r['customer_id'], 'name': r['customer__name']})(),
                            'c0_30': c0,
                            'c31_60': c31,
                            'c61_90': c61,
                            'c90p': c90p,
                            'total': total,
                        })
                        buckets['c0_30'] += c0
                        buckets['c31_60'] += c31
                        buckets['c61_90'] += c61
                        buckets['c90p'] += c90p
                    rows = tmp_rows
                    aggregated_success = True
        except Exception:
            aggregated_success = False
        if not aggregated_success:
            # fallback Python loop
            per_customer = {}
            for inv in invoices:
                due = inv.due_date or inv.date
                days = (as_of_date - due).days
                # استخدم annotation إن وُجد لتفادي استدعاء property لكل عنصر
                amt = getattr(inv, 'remaining_amount', None)
                if amt is None:
                    amt = inv.remaining or Decimal('0')
                if days < 0:
                    bucket_key = 'c0_30'
                elif days <= 30:
                    bucket_key = 'c0_30'
                elif days <= 60:
                    bucket_key = 'c31_60'
                elif days <= 90:
                    bucket_key = 'c61_90'
                else:
                    bucket_key = 'c90p'
                buckets[bucket_key] += amt
                cust = inv.customer
                entry = per_customer.get(cust.id)
                if not entry:
                    entry = per_customer[cust.id] = {
                        'customer': cust,
                        'c0_30': Decimal('0'),
                        'c31_60': Decimal('0'),
                        'c61_90': Decimal('0'),
                        'c90p': Decimal('0'),
                        'total': Decimal('0'),
                    }
                entry[bucket_key] += amt
                entry['total'] += amt
            rows = list(per_customer.values())
        if overdue_only:
            rows = [r for r in rows if (r['c31_60'] or r['c61_90'] or r['c90p'])]
        rows.sort(key=lambda r: (r['c90p'], r['total']), reverse=True)
        grand_total = sum(r['total'] for r in rows) if rows else Decimal('0')
        cache_hit = False
        if cache_allowed:
            from time import time as _now
            cache.set(cache_key, {
                'rows': rows,
                'buckets': buckets,
                'grand_total': grand_total,
                'generated_ts': int(_now()),
            }, 60)
        cache_meta = None

    total_before_overdue = len(rows)
    if overdue_only:
        # بعد التطبيق يكون total_after_overdue = len(rows) (تم بالفعل فوق)
        total_after_overdue = len(rows)
        # إظهار ملخص فوق الجدول
        buckets_summary = {
            'c0_30': sum(r['c0_30'] for r in rows),
            'c31_60': sum(r['c31_60'] for r in rows),
            'c61_90': sum(r['c61_90'] for r in rows),
            'c90p': sum(r['c90p'] for r in rows),
            'total': grand_total,
        }
        # إضافة حقل days_overdue للتصنيف
        for r in rows:
            due = r['customer'].invoices.first().due_date or r['customer'].invoices.first().date
            r['days_overdue'] = (as_of_date - due).days
        # فرز متقدم: أولاً حسب days_overdue ثم حسب total
        rows.sort(key=lambda r: (r['days_overdue'], r['total']), reverse=True)
    context = {
        'as_of_date': as_of_date,
        'buckets': buckets,
        'rows': rows,
        'total_before_overdue': total_before_overdue,
        'total_after_overdue': total_after_overdue if overdue_only else None,
        'cache_hit': cache_hit,
        'cache_meta': cache_meta,
        'query': request.GET.dict(),
    }
    return render(request, 'accounting/aging_receivables_report.html', context)


@login_required
def aging_payables_report(request):
    """تقرير أعمار الذمم الدائنة (موردون).

    مشابه لتقرير الذمم المدينة لكن يستند إلى فواتير الشراء (PurchaseBill).
    المعاملات:
      - as_of: تاريخ الأساس (YYYY-MM-DD) افتراض: اليوم
      - q: بحث جزئي في اسم المورد أو رقم الفاتورة
      - overdue_only=1: إظهار المتأخرة (>30 يوم)
      - export=csv: تنزيل CSV مبسط
    """
    from django.utils import timezone
    from datetime import datetime as _dt
    from decimal import Decimal
    from django.core.cache import cache
    try:
        from purchases.models import PurchaseBill  # type: ignore
    except Exception:
        # فشل استيراد نموذج فواتير الشراء => عرض رسالة بسيطة
        return render(request, 'accounting/aging_payables.html', {
            'rows': [], 'buckets': {}, 'as_of_date': timezone.now().date(),
            'error': 'نموذج فواتير الشراء غير متاح حالياً'
        })

    as_of_str = request.GET.get('as_of') or ''
    try:
        as_of_date = _dt.strptime(as_of_str, '%Y-%m-%d').date() if as_of_str else timezone.now().date()
    except Exception:
        as_of_date = timezone.now().date()
    q = (request.GET.get('q') or '').strip()
    overdue_only = request.GET.get('overdue_only') == '1'

    bills = PurchaseBill.objects.filter(status='posted')
    # يفترض وجود حقل remaining_amount (مستخدم سابقاً في badges_view)
    try:
        bills = bills.filter(remaining_amount__gt=0)
    except Exception:
        # fallback: لو لم يوجد الحقل نحاول استخدام paid/total إن توفرت
        from django.db.models import F, DecimalField, ExpressionWrapper
        try:
            bills = bills.annotate(_remaining=ExpressionWrapper(
                (F('cached_total') - F('discount') - F('paid')),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )).filter(_remaining__gt=0)
        except Exception:
            pass  # سنستمر حتى لو لم نتمكن

    if q:
        from django.db.models import Q
        bills = bills.filter(Q(number__icontains=q) | Q(supplier__name__icontains=q))

    bills = bills.select_related('supplier')

    cache_allowed = request.GET.get('no_cache') != '1'
    cache_key = f"aging:pay:{as_of_date}:{q or '-'}:{'1' if overdue_only else '0'}"
    cached = cache.get(cache_key) if cache_allowed else None
    if cached:
        rows = cached['rows']; buckets = cached['buckets']; grand_total = cached['grand_total']
        cache_hit = True; cache_meta = cached.get('meta')
    else:
        buckets = { 'c0_30': Decimal('0'), 'c31_60': Decimal('0'), 'c61_90': Decimal('0'), 'c90p': Decimal('0') }
        per_supplier: dict[int, dict] = {}
        for b in bills:
            due = getattr(b, 'due_date', None) or getattr(b, 'date', as_of_date)
            days = (as_of_date - due).days
            amt = getattr(b, 'remaining_amount', None)
            if amt is None:
                # محاولة ثانية: حقل _remaining (من annotation) أو 0
                amt = getattr(b, '_remaining', Decimal('0'))
            if days < 0:
                bucket_key = 'c0_30'
            elif days <= 30:
                bucket_key = 'c0_30'
            elif days <= 60:
                bucket_key = 'c31_60'
            elif days <= 90:
                bucket_key = 'c61_90'
            else:
                bucket_key = 'c90p'
            buckets[bucket_key] += amt
            supp = b.supplier
            entry = per_supplier.get(supp.id)
            if not entry:
                entry = per_supplier[supp.id] = {
                    'supplier': supp,
                    'c0_30': Decimal('0'), 'c31_60': Decimal('0'), 'c61_90': Decimal('0'), 'c90p': Decimal('0'), 'total': Decimal('0'),
                }
            entry[bucket_key] += amt
            entry['total'] += amt
        rows = list(per_supplier.values())
        if overdue_only:
            rows = [r for r in rows if (r['c31_60'] or r['c61_90'] or r['c90p'])]
        rows.sort(key=lambda r: (r['c90p'], r['total']), reverse=True)
        grand_total = sum(r['total'] for r in rows) if rows else Decimal('0')
        cache_hit = False
        cache_meta = None
        if cache_allowed:
            from time import time as _now
            cache.set(cache_key, {
                'rows': rows,
                'buckets': buckets,
                'grand_total': grand_total,
                'meta': {'generated_ts': int(_now())},
            }, 60)

    # تصدير CSV
    if request.GET.get('export') == 'csv':
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="aging_payables_{as_of_date}.csv"'
        w = csv.writer(resp)
        w.writerow(['Supplier','0-30','31-60','61-90','90+','Total'])
        for r in rows[:5000]:
            w.writerow([
                getattr(r['supplier'], 'name', ''),
                f"{r['c0_30']:.2f}", f"{r['c31_60']:.2f}", f"{r['c61_90']:.2f}", f"{r['c90p']:.2f}", f"{r['total']:.2f}"
            ])
        w.writerow([]); w.writerow(['Grand Total','','','', '', f"{grand_total:.2f}"])
        return resp

    context = {
        'as_of_date': as_of_date,
        'buckets': buckets,
        'rows': rows,
        'cache_hit': cache_hit,
        'cache_meta': cache_meta,
        'query': request.GET.dict(),
        'overdue_only': overdue_only,
        'grand_total': grand_total,
    }
    return render(request, 'accounting/aging_payables.html', context)


@login_required
def tax_report_view(request):
    """تقرير ضريبي مبسط (VAT) يجمع ضريبة المخرجات وضريبة المدخلات.

    الهدف: إزالة خطأ AttributeError عند تحميل URLConf وإتاحة نظرة سريعة.

    المعاملات المدعومة:
      - period=month|quarter|ytd (افتراضياً month)
      - as_of=YYYY-MM-DD (تاريخ الأساس، افتراض: اليوم)
      - export=csv لتنزيل ملف CSV مختصر

    يعتمد على وجود موديلات فواتير المبيعات والشراء. يحاول التعرف على حقول الضريبة
    بعدة أسماء محتملة لتجنب التعطل (tax_amount / total_tax / vat_amount / tax / total_vat).
    في حال عدم توفر النماذج أو الحقول يُرجع أصفاراً.
    """
    from datetime import datetime as _dt
    from decimal import Decimal
    from django.utils import timezone
    from django.core.cache import cache
    from django.db.models import Q

    as_of_str = request.GET.get('as_of') or ''
    try:
        as_of_date = _dt.strptime(as_of_str, '%Y-%m-%d').date() if as_of_str else timezone.now().date()
    except Exception:
        as_of_date = timezone.now().date()
    period = request.GET.get('period') or 'month'
    if period not in ['month','quarter','ytd']:
        period = 'month'

    # حساب بداية الفترة وفق الاختيار
    if period == 'month':
        period_start = as_of_date.replace(day=1)
    elif period == 'quarter':
        q = ((as_of_date.month - 1) // 3) + 1
        first_month = 3 * (q - 1) + 1
        period_start = as_of_date.replace(month=first_month, day=1)
    else:  # ytd
        period_start = as_of_date.replace(month=1, day=1)

    cache_key = f"tax_report:{period}:{as_of_date.isoformat()}"
    cached = None if request.GET.get('no_cache') == '1' else cache.get(cache_key)
    if cached:
        context = cached
    else:
        sales_vat = Decimal('0')
        purchase_vat = Decimal('0')
        sales_rows = []
        purchase_rows = []
        model_errors = []

        # أسماء الحقول المحتملة لضريبة الفاتورة
        tax_field_candidates = ['tax_amount','total_tax','vat_amount','tax','total_vat']

        def extract_tax(obj):
            for fn in tax_field_candidates:
                val = getattr(obj, fn, None)
                if val not in (None, ''):
                    try:
                        return Decimal(str(val))
                    except Exception:
                        continue
            return Decimal('0')

        # فواتير المبيعات
        try:
            from sales.models import Invoice
            qs = Invoice.objects.filter(is_deleted=False, date__gte=period_start, date__lte=as_of_date)
            for inv in qs.order_by('-date','-id')[:500]:  # حد أمان
                tax_val = extract_tax(inv)
                if tax_val:
                    sales_vat += tax_val
                sales_rows.append({'number': getattr(inv,'number', inv.id), 'date': getattr(inv,'date', None), 'tax': tax_val})
        except Exception as e:  # pragma: no cover
            model_errors.append(f"Invoice: {e}")

        # فواتير الشراء
        try:
            from purchases.models import PurchaseBill  # type: ignore
            pb_qs = PurchaseBill.objects.filter(status='posted', date__gte=period_start, date__lte=as_of_date)
            for bill in pb_qs.order_by('-date','-id')[:500]:
                tax_val = extract_tax(bill)
                if tax_val:
                    purchase_vat += tax_val
                purchase_rows.append({'number': getattr(bill,'number', bill.id), 'date': getattr(bill,'date', None), 'tax': tax_val})
        except Exception as e:  # pragma: no cover
            model_errors.append(f"PurchaseBill: {e}")

        net_vat = sales_vat - purchase_vat

        context = {
            'period': period,
            'as_of_date': as_of_date,
            'period_start': period_start,
            'sales_vat': sales_vat,
            'purchase_vat': purchase_vat,
            'net_vat': net_vat,
            'sales_rows': sales_rows,
            'purchase_rows': purchase_rows,
            'model_errors': model_errors,
            'cache_hit': False,
        }
        # خزن نتيجة مبسطة 60 ثانية
        if not model_errors:
            cache.set(cache_key, context, 60)

    # تصدير CSV
    if request.GET.get('export') == 'csv':
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="tax_report_{period}_{as_of_date}.csv"'
        w = csv.writer(resp)
        w.writerow(['Period', context['period'], 'As Of', context['as_of_date'], 'Start', context['period_start']])
        w.writerow([])
        w.writerow(['Sales VAT', f"{context['sales_vat']:.2f}", 'Purchase VAT', f"{context['purchase_vat']:.2f}", 'Net VAT', f"{context['net_vat']:.2f}"])
        w.writerow([])
        w.writerow(['Sales Invoices'])
        w.writerow(['Number','Date','Tax'])
        for r in context['sales_rows'][:5000]:
            w.writerow([r['number'], getattr(r['date'],'isoformat', lambda: '')(), f"{r['tax']:.2f}"])
        w.writerow([])
        w.writerow(['Purchase Bills'])
        w.writerow(['Number','Date','Tax'])
        for r in context['purchase_rows'][:5000]:
            w.writerow([r['number'], getattr(r['date'],'isoformat', lambda: '')(), f"{r['tax']:.2f}"])
        return resp

    return render(request, 'accounting/tax_report.html', context)

@login_required
def bank_reconcile_view(request):
    if not (request.user.has_perm('accounting.reconcile_bank') or request.user.is_staff):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('ليست لديك صلاحية تسوية البنك')
    account_id = request.GET.get('account')
    unreconciled = []
    error = None
    reconciled_count = 0
    bank_account = None
    recent_bank_transactions = []
    bank_balance = None
    unreconciled_count = 0
    try:
        from .models import BankTransaction, Account  # type: ignore
        if account_id and account_id.isdigit():
            bank_account = Account.objects.filter(pk=int(account_id)).first()
        if request.method == 'POST' and request.POST.get('action') == 'reconcile':
            ids = request.POST.getlist('tx_ids')
            from django.db import transaction
            with transaction.atomic():
                qs_upd = BankTransaction.objects.filter(is_reconciled=False, id__in=ids)
                reconciled_count = qs_upd.update(is_reconciled=True)
            from django.contrib import messages
            messages.success(request, f'تمت تسوية {reconciled_count} حركة')
            from django.urls import reverse
            import urllib.parse
            params = {}
            if account_id: params['account'] = account_id
            url = reverse('accounting:bank_reconcile')
            if params:
                url += '?' + urllib.parse.urlencode(params)
            return redirect(url)
        qs = BankTransaction.objects.filter(is_reconciled=False)
        if bank_account:
            qs = qs.filter(account=bank_account)
        unreconciled = list(qs.select_related('account').order_by('-date','-id')[:500])
        unreconciled_count = qs.count()
        # رصيد حساب البنك (تجميعي) إن وجد
        if bank_account:
            try:
                bank_balance = bank_account.aggregate_balance()
            except Exception:
                bank_balance = None
            recent_bank_transactions = list(
                BankTransaction.objects.filter(account=bank_account).order_by('-date','-id')[:20]
            )
    except Exception as e:  # pragma: no cover
        error = str(e)
    context = {
        'unreconciled_transactions': unreconciled,
        'selected_account_id': account_id,
        'error': error,
        'reconciled_count': reconciled_count,
        'bank_account': bank_account,
        'recent_bank_transactions': recent_bank_transactions,
        'bank_balance': bank_balance,
        'unreconciled_count': unreconciled_count,
    }
    return render(request, 'accounting/bank_reconcile.html', context)

@login_required
def bank_transaction_toggle_reconciled(request, pk):
    """تبديل حالة التسوية لحركة بنك واحدة والعودة للصفحة السابقة."""
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    from .models import BankTransaction  # type: ignore
    tx = get_object_or_404(BankTransaction, pk=pk)
    tx.is_reconciled = not tx.is_reconciled
    tx.save(update_fields=['is_reconciled'])
    messages.success(request, 'تم تحديث حالة الحركة')
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    from django.urls import reverse
    return redirect(reverse('accounting:bank_reconcile'))


# ========================= ستبات مراكز التكلفة =========================
@login_required
def cost_centers_list(request):
    from .models import CostCenter
    centers = CostCenter.objects.filter(is_active=True).order_by('code')[:500]
    total = centers.count()
    return render(request, 'accounting/cost_centers_list.html', {
        'cost_centers': centers,
        'total_centers': total,
    })

@login_required
def cost_center_create(request):
    from .models import CostCenter
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip()
        name = (request.POST.get('name') or '').strip()
        parent_id = request.POST.get('parent') or None
        manager_id = request.POST.get('manager') or None
        description = (request.POST.get('description') or '').strip()
        
        if not code or not name:
            messages.error(request, 'الكود والاسم مطلوبان')
        elif CostCenter.objects.filter(code=code).exists():
            messages.error(request, 'الكود مستخدم من قبل')
        else:
            parent = None
            if parent_id and parent_id.isdigit():
                parent = CostCenter.objects.filter(pk=int(parent_id), is_active=True).first()
            
            manager = None
            if manager_id and manager_id.isdigit():
                manager = User.objects.filter(pk=int(manager_id), is_active=True).first()
            
            CostCenter.objects.create(
                code=code,
                name=name,
                parent=parent,
                manager=manager,
                description=description,
                is_active=True
            )
            messages.success(request, 'تم إنشاء مركز التكلفة بنجاح')
            return redirect('accounting:cost_centers_list')
    
    # استرجاع المراكز الرئيسية للقائمة المنسدلة
    parent_centers = CostCenter.objects.filter(is_active=True).order_by('code')[:100]
    
    return render(request, 'accounting/cost_center_form.html', {
        'managers': User.objects.filter(is_active=True).order_by('username')[:200],
        'parent_centers': parent_centers,
    })

@login_required
def cost_center_detail(request, pk):
    from .models import CostCenter, CostCenterBudget, FiscalYear, JournalEntryItem
    center = get_object_or_404(CostCenter, pk=pk)
    fiscal_year = FiscalYear.objects.filter(is_active=True).first()
    budget = None
    if fiscal_year:
        budget = CostCenterBudget.objects.filter(cost_center=center, fiscal_year=fiscal_year).first()
    entries = JournalEntryItem.objects.filter(cost_center=center).order_by('-journal_entry__date')[:25]
    return render(request, 'accounting/cost_center_detail.html', {
        'cost_center': center,
        'entries': entries,
        'budget': budget,
        'fiscal_year': fiscal_year,
    })

@login_required
def cost_allocations_list(request):
    """عرض مبدئي (Placeholder) لواجهة توزيع التكاليف.

    الهدف الحالي: إزالة خطأ 404 عند زيارة /accounting/cost/allocations
    لاحقاً يمكن توسيعها لعرض:
      - أساليب توزيع التكاليف العامة (مصاريف عمومية -> مراكز تكلفة)
      - ملخص استهلاك مراكز التكلفة / نسب التوزيع
      - أزرار حساب/تطبيق دفعة توزيع جديدة
    حالياً تعرض قائمة مراكز التكلفة النشطة وأي ميزانيات مرتبطة بالسنة الحالية.
    """
    from .models import CostCenter, CostCenterBudget, FiscalYear
    fiscal_year = FiscalYear.objects.filter(is_active=True).first()
    centers = list(CostCenter.objects.filter(is_active=True).order_by('code')[:200])
    budgets = {}
    if fiscal_year:
        for b in CostCenterBudget.objects.filter(fiscal_year=fiscal_year, cost_center__in=centers):
            # استخدام pk بدلاً من cost_center_id لتجنب تحذير محلل الأنواع
            budgets[b.cost_center.pk] = b
    context = {
        'fiscal_year': fiscal_year,
        'cost_centers': centers,
        'budgets': budgets,
        'center_rows': [(c, budgets.get(c.pk)) for c in centers],
        'planned_feature': True,
    }
    return render(request, 'accounting/cost_allocations_list.html', context)

# ========================= ستبات قوالب القيود =========================
@login_required
def journal_templates_list(request):
    from .models import JournalEntryTemplate
    templates = JournalEntryTemplate.objects.filter(is_active=True).order_by('name')[:500]
    return render(request, 'accounting/journal_templates_list.html', {'templates': templates})

@login_required
def journal_template_create(request):
    from .models import JournalEntryTemplate
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if not name:
            messages.error(request, 'الاسم مطلوب')
        else:
            tpl = JournalEntryTemplate.objects.create(name=name, template_type='manual', is_active=True, created_by=request.user)
            messages.success(request, 'تم إنشاء القالب')
            return redirect('accounting:journal_template_detail', pk=tpl.pk)
    return render(request, 'accounting/journal_template_form.html', {})

@login_required
def journal_template_detail(request, pk):
    from .models import JournalEntryTemplate, JournalEntryTemplateItem, Account, CostCenter
    from django.contrib import messages
    from decimal import Decimal
    
    tpl = get_object_or_404(JournalEntryTemplate, pk=pk)
    
    # معالجة إضافة بند جديد
    if request.method == 'POST':
        try:
            account_id = request.POST.get('account')
            item_type = request.POST.get('type')
            amount_raw = request.POST.get('amount', '').strip()
            description = request.POST.get('description', '').strip()
            cost_center_id = request.POST.get('cost_center')
            sequence_raw = request.POST.get('sequence', '').strip()
            
            # التحقق من الحساب
            if not account_id:
                messages.error(request, 'الرجاء اختيار الحساب')
            elif item_type not in ['debit', 'credit']:
                messages.error(request, 'نوع الحركة غير صحيح')
            else:
                account = get_object_or_404(Account, id=account_id)
                
                # تحويل المبلغ
                amount = None
                if amount_raw:
                    try:
                        amount = Decimal(amount_raw.replace(',', ''))
                        if amount < 0:
                            messages.error(request, 'المبلغ يجب أن يكون موجب')
                            amount = None
                    except:
                        messages.error(request, 'المبلغ غير صحيح')
                
                # تحديد الترتيب
                sequence = None
                if sequence_raw:
                    try:
                        sequence = int(sequence_raw)
                    except:
                        pass
                
                if sequence is None:
                    max_seq = tpl.items.aggregate(models.Max('sequence'))['sequence__max']
                    sequence = (max_seq or 0) + 1
                
                # مركز التكلفة
                cost_center = None
                if cost_center_id:
                    try:
                        cost_center = CostCenter.objects.get(id=cost_center_id)
                    except CostCenter.DoesNotExist:
                        pass
                
                # إنشاء البند
                if 'error' not in [msg.level_tag for msg in messages.get_messages(request)]:
                    JournalEntryTemplateItem.objects.create(
                        template=tpl,
                        account=account,
                        type=item_type,
                        amount=amount,
                        description=description,
                        cost_center=cost_center,
                        sequence=sequence
                    )
                    messages.success(request, f'تم إضافة البند بنجاح: {account.name}')
                    return redirect('accounting:journal_template_detail', pk=pk)
        
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    # جلب البنود
    items_attr = getattr(tpl, 'items', None)
    if items_attr is not None and hasattr(items_attr, 'all'):
        try:
            qs = items_attr.all()
            template_items = qs.order_by('sequence') if hasattr(qs, 'order_by') else qs
        except Exception:
            template_items = []
    elif isinstance(items_attr, (list, tuple)):
        template_items = list(items_attr)
    else:
        template_items = []
    
    # حساب الترتيب التالي
    next_sequence = 1
    if template_items:
        try:
            max_seq = max([item.sequence for item in template_items if hasattr(item, 'sequence')])
            next_sequence = max_seq + 1
        except:
            next_sequence = len(template_items) + 1
    
    # جلب الحسابات ومراكز التكلفة للنموذج
    accounts = Account.objects.filter(is_active=True, can_post=True).order_by('code')[:500]
    cost_centers = CostCenter.objects.filter(is_active=True).order_by('code')[:200]
    
    return render(request, 'accounting/journal_template_detail.html', {
        'template': tpl,
        'template_items': template_items,
        'accounts': accounts,
        'cost_centers': cost_centers,
        'next_sequence': next_sequence,
    })

@login_required
def smart_journal_entry_create(request):
    from .models import JournalEntryTemplate, JournalEntry, JournalEntryItem, Account
    templates = JournalEntryTemplate.objects.filter(is_active=True)[:200]
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        total_amount_raw = request.POST.get('total_amount') or '0'
        try:
            from decimal import Decimal
            total_amount = Decimal(total_amount_raw.replace(',', ''))
        except Exception:
            total_amount = None
        if not template_id or not template_id.isdigit():
            messages.error(request, 'قالب غير صالح')
        elif total_amount is None or total_amount <= 0:
            messages.error(request, 'مبلغ غير صالح')
        else:
            tpl = get_object_or_404(JournalEntryTemplate, pk=int(template_id))
            from datetime import date as _d
            desc = (request.POST.get('description') or tpl.name or 'قيد ذكي').strip()
            from django.db import transaction as _tx
            with _tx.atomic():
                je = JournalEntry.objects.create(
                    date=_d.today(),
                    entry_type='manual',
                    description=desc,
                    created_by=request.user
                )
                # توزيع مبسط: أول بند مدين، ثاني بند دائن بنفس القيمة (إن وُجد)
                items = list(getattr(tpl, 'items').all()[:2]) if hasattr(tpl,'items') else []
                if len(items) < 2:
                    # fallback: اختيار حسابين قابلين للترحيل
                    accs = list(Account.objects.filter(can_post=True, is_active=True).order_by('code')[:2])
                    if len(accs) == 2:
                        JournalEntryItem.objects.bulk_create([
                            JournalEntryItem(journal_entry=je, account=accs[0], type='debit', amount=total_amount, description=desc),
                            JournalEntryItem(journal_entry=je, account=accs[1], type='credit', amount=total_amount, description=desc),
                        ])
                else:
                    # استخدم نوع كل بند كما هو إن وجد حقل type
                    for i, it in enumerate(items[:2]):
                        it_type = getattr(it, 'type', 'debit' if i == 0 else 'credit')
                        JournalEntryItem.objects.create(
                            journal_entry=je,
                            account=getattr(it, 'account'),
                            type=it_type,
                            amount=total_amount,
                            description=desc,
                        )
                messages.success(request, f'تم إنشاء القيد {je.number}')
                return redirect('accounting:journal_entry_detail', pk=je.pk)
    return render(request, 'accounting/smart_journal_entry_form.html', {'templates': templates})

# ========================= ستبات نظام القروض =========================
@login_required
def loans_dashboard(request):
    try:
        from .models import Loan, LoanPayment
        total_loans = Loan.objects.count()
        active_loans = Loan.objects.filter(status='active').count()
        recent_loans = Loan.objects.order_by('-created_at')[:5]
        recent_payments = LoanPayment.objects.order_by('-payment_date')[:5]
    except Exception:
        total_loans = active_loans = 0
        recent_loans = []; recent_payments = []
    return render(request, 'accounting/loans_dashboard.html', {
        'total_loans': total_loans,
        'active_loans': active_loans,
        'recent_loans': recent_loans,
        'recent_payments': recent_payments,
    })

@login_required
def loan_list(request):
    from .models import Loan, Bank
    from decimal import InvalidOperation
    
    loans = []
    try:
        # محاولة جلب القروض مع معالجة الأخطاء
        all_loans = Loan.objects.select_related('bank').order_by('-created_at')[:500]
        
        # فحص كل قرض على حدة لتجنب الأخطاء
        for loan in all_loans:
            try:
                # محاولة الوصول للحقول للتأكد من صحة البيانات
                _ = loan.principal_amount
                _ = loan.interest_rate
                _ = loan.outstanding_balance
                loans.append(loan)
            except (InvalidOperation, ValueError, TypeError):
                # تجاهل القروض التي بها بيانات غير صحيحة
                continue
    except Exception as e:
        from django.contrib import messages
        messages.warning(request, f'تحذير: بعض القروض قد تحتوي على بيانات غير صحيحة')
    
    # جلب قائمة البنوك بشكل منفصل
    try:
        banks = Bank.objects.filter(is_active=True).order_by('name')
    except Exception:
        banks = []
    
    return render(request, 'accounting/loan_list.html', {
        'loans': loans,
        'banks': banks
    })

@login_required
def loan_create(request):
    try:
        from .models import Loan, Bank
    except Exception:
        messages.error(request, 'نموذج القروض غير متاح')
        return redirect('accounting:dashboard')
    if request.method == 'POST':
        try:
            from django.utils import timezone
            principal = request.POST.get('principal_amount') or '0'
            from decimal import Decimal
            principal_val = Decimal(principal.replace(',', ''))
            loan = Loan.objects.create(
                loan_number=f"LOAN-{timezone.now().strftime('%Y%m%d')}-{Loan.objects.count()+1:03d}",
                bank_id=request.POST.get('bank') or None,
                principal_amount=principal_val,
                interest_rate=request.POST.get('interest_rate') or 0,
                duration_months=request.POST.get('duration_months') or 0,
                disbursement_date=request.POST.get('disbursement_date') or timezone.now().date(),
                loan_account_id=request.POST.get('loan_account') or None,
                outstanding_balance=principal_val,
                status='active',
                created_by=request.user,
            )
            messages.success(request, 'تم إنشاء القرض')
            return redirect('accounting:loan_list')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    try:
        from .models import Account as _Acc
        loan_accounts = _Acc.objects.filter(account_type='liability')[:300]
    except Exception:
        loan_accounts = []
    
    try:
        banks = Bank.objects.filter(is_active=True).order_by('name')
    except Exception:
        banks = []
    
    return render(request, 'accounting/loan_form.html', {
        'banks': banks,
        'loan_accounts': loan_accounts,
    })

@login_required
def loan_detail(request, pk):
    try:
        from .models import Loan
        loan = get_object_or_404(Loan, pk=pk)
        payments = getattr(loan, 'payments', None)
        if payments is not None and hasattr(payments, 'all'):
            payments = payments.all().order_by('-payment_date')[:200]
    except Exception:
        loan = None; payments = []
    return render(request, 'accounting/loan_detail.html', {'loan': loan, 'payments': payments})

@login_required
def loan_payment_create(request, loan_id):
    try:
        from .models import Loan, LoanPayment
        loan = get_object_or_404(Loan, pk=loan_id)
    except Exception:
        messages.error(request, 'القرض غير متاح')
        return redirect('accounting:loan_list')
    if request.method == 'POST':
        from decimal import Decimal
        from django.utils import timezone
        try:
            amount = Decimal((request.POST.get('amount') or '0').replace(',', ''))
            interest_portion = Decimal((request.POST.get('interest_portion') or '0').replace(',', ''))
            principal_portion = amount - interest_portion
            LoanPayment.objects.create(
                loan=loan,
                payment_date=request.POST.get('payment_date') or timezone.now().date(),
                amount=amount,
                principal_portion=principal_portion,
                interest_portion=interest_portion,
                created_by=request.user,
            )
            messages.success(request, 'تم تسجيل الدفعة')
            return redirect('accounting:loan_detail', pk=loan_id)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    return render(request, 'accounting/loan_payment_form.html', {'loan': loan})

# ========================= ستبات الشيكات =========================
@login_required
def cheque_list(request):
    try:
        from .models import Cheque
        from django.db.models import Q
        status = request.GET.get('status') or ''
        ctype = request.GET.get('type') or ''
        search = (request.GET.get('search') or '').strip()
        qs = Cheque.objects.all().order_by('-due_date','-created_at')[:2000]
        if status:
            qs = qs.filter(status=status)
        if ctype:
            qs = qs.filter(cheque_type=ctype)
        if search:
            qs = qs.filter(Q(number__icontains=search) | Q(bank_name__icontains=search) | Q(partner__name__icontains=search))
        cheques = list(qs[:500])
    except Exception:
        cheques = []
        status = ctype = search = ''
    return render(request, 'accounting/cheque_list.html', {
        'cheques': cheques,
        'status': status,
        'cheque_type': ctype,
        'search': search,
    })

@login_required
def cheque_create(request):
    try:
        from .models import Cheque
    except Exception:
        messages.error(request, 'نموذج الشيك غير متاح')
        return redirect('accounting:cheque_list')
    if request.method == 'POST':
        try:
            from django.utils import timezone
            ch = Cheque(
                number=request.POST.get('number') or '',
                bank_name=request.POST.get('bank_name') or '',
                cheque_type=request.POST.get('cheque_type') or 'incoming',
                status=request.POST.get('status') or 'received',
                partner_id=request.POST.get('partner') or None,
                amount=request.POST.get('amount') or 0,
                issue_date=request.POST.get('issue_date') or timezone.now().date(),
                due_date=request.POST.get('due_date') or None,
                notes=request.POST.get('notes') or '',
                created_by=request.user,
            )
            if 'image' in request.FILES:
                ch.image = request.FILES['image']
            ch.save()
            messages.success(request, 'تم حفظ الشيك')
            return redirect('accounting:cheque_list')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    return render(request, 'accounting/cheque_form.html', {})

@login_required
def cheque_detail(request, pk):
    try:
        from .models import Cheque
        ch = get_object_or_404(Cheque, pk=pk)
    except Exception:
        ch = None
    return render(request, 'accounting/cheque_detail.html', {'cheque': ch})

@login_required
def cheque_delete(request, pk):
    try:
        from .models import Cheque
        ch = get_object_or_404(Cheque, pk=pk)
    except Exception:
        messages.error(request, 'الشيك غير متاح')
        return redirect('accounting:cheque_list')
    if request.method == 'POST':
        try:
            ch.delete()
            messages.success(request, 'تم حذف الشيك')
            return redirect('accounting:cheque_list')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    return render(request, 'accounting/cheque_confirm_delete.html', {'cheque': ch})

# ========================= أداة التشخيص =========================
@login_required
def diagnostics_view(request):
    from django.conf import settings
    from django.db import connection
    from django.utils import timezone
    info = {
        'debug': getattr(settings, 'DEBUG', False),
        'database_engine': connection.settings_dict.get('ENGINE',''),
        'now': timezone.now(),
        'user': request.user,
        'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
    }
    # فحص سريع لبعض الموديلات
    model_counts = {}
    try:
        model_counts['accounts'] = __import__('accounting.models', fromlist=['Account']).Account.objects.count()
    except Exception:
        pass
    info['model_counts'] = model_counts
    return render(request, 'accounting/diagnostics.html', info)

@login_required
def bank_statement_import(request):
    """استيراد كشف بنكي CSV مع خيار مطابقة تلقائية."""
    from decimal import Decimal, InvalidOperation
    import csv, io
    from django.utils.dateparse import parse_date
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.urls import reverse
    from .models import BankTransaction, Account, JournalEntryItem

    account_id = request.GET.get('account') or request.POST.get('account')
    target_account = None
    if account_id and account_id.isdigit():
        target_account = Account.objects.filter(pk=int(account_id)).first()
    
    if request.method == 'POST' and 'file' in request.FILES:
        if not target_account:
            messages.error(request, 'يجب اختيار حساب البنك أولاً')
            return redirect(request.path + (f'?account={account_id}' if account_id else ''))
        f = request.FILES['file']
        try:
            content = f.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                content = f.read().decode('windows-1256')
            except Exception:
                messages.error(request, 'ترميز الملف غير مدعوم (UTF-8).')
                return redirect(request.path + f'?account={account_id}')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if rows and rows[0] and 'date' in rows[0][0].lower():
            rows = rows[1:]
        created = 0; matched = 0; errors = []
        auto_match = request.POST.get('auto_match') == '1'
        window_days = 7
        from datetime import timedelta
        for idx, r in enumerate(rows, start=1):
            if not r or len(r) < 3:
                errors.append(f'سطر {idx}: أعمدة غير كافية')
                continue
            date_str = r[0].strip(); desc = (r[1] if len(r) > 1 else '').strip(); amount_str = r[2].strip(); ref = (r[3] if len(r) > 3 else '')[:100]
            dt = parse_date(date_str)
            if not dt:
                errors.append(f'سطر {idx}: تاريخ غير صالح {date_str}')
                continue
            try:
                amount_val = Decimal(amount_str.replace(',', ''))
            except (InvalidOperation, ValueError):
                errors.append(f'سطر {idx}: مبلغ غير صالح {amount_str}')
                continue
            tx = BankTransaction.objects.create(
                account=target_account,
                date=dt,
                description=desc[:255],
                amount=amount_val,
                reference=ref,
            )
            created += 1
            if auto_match:
                from django.db.models import Q
                low = amount_val - Decimal('0.01'); high = amount_val + Decimal('0.01')
                dt_from = dt - timedelta(days=window_days); dt_to = dt + timedelta(days=window_days)
                jqs = JournalEntryItem.objects.filter(
                    journal_entry__date__gte=dt_from,
                    journal_entry__date__lte=dt_to,
                    account=target_account,
                    amount__gte=low,
                    amount__lte=high,
                ).order_by('-journal_entry__date')[:5]
                for jitem in jqs:
                    tx.is_reconciled = True
                    tx.description = (tx.description + ' | match:' + str(jitem.journal_entry_id))[:255]
                    tx.save(update_fields=['is_reconciled','description'])
                    matched += 1
                    break
        return render(request, 'accounting/bank_statement_import_result.html', {
            'account': target_account,
            'created': created,
            'matched': matched,
            'errors': errors,
            'auto_match': auto_match,
        })
    
    return render(request, 'accounting/bank_statement_import.html', {
        'account': target_account,
        'selected_account_id': account_id,
    })



@login_required
@require_perm('accounting.create_journal_entry')
def import_journal_view(request):
    """استيراد قيود يومية من ملف CSV بسيط.

    صيغة الأعمدة المطلوبة:
    date, description, reference, entry_type, account_code, type, amount, [cost_center_code]

    حيث:
    - date: تاريخ القيد بصيغة YYYY-MM-DD
    - description: وصف القيد
    - reference: المرجع (اختياري)
    - entry_type: نوع القيد (manual, sales, purchase, payment, receipt, adjustment)
    - account_code: كود الحساب (يجب أن يكون موجوداً في النظام)
    - type: نوع البند (debit أو credit)
    - amount: المبلغ (رقم موجب)
    - cost_center_code: كود مركز التكلفة (اختياري)

    - يجمع البنود حسب (date, description, reference, entry_type) لإنشاء قيد واحد.
    - يدعم ?post=1 للترحيل التلقائي إذا كان القيد متوازنًا وكان تاريخ القيد ضمن سنة مالية نشطة.
    - يتجاهل الأسطر التي لا تحتوي على account_code/type/amount صالح.
    """
    from decimal import Decimal, InvalidOperation
    import csv, io
    from django.utils.dateparse import parse_date
    from django.db import transaction
    from django.urls import reverse
    from django.contrib import messages
    from .models import Account, CostCenter, JournalEntry, JournalEntryItem, FiscalYear

    if request.method == 'POST' and 'file' in request.FILES:
        f = request.FILES['file']
        try:
            content = f.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                content = f.read().decode('windows-1256')
            except Exception:
                messages.error(request, 'ترميز الملف غير مدعوم. استخدم UTF-8.')
                return redirect(request.path)
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        # تخطّي رأس الجدول إذا وُجد
        if rows and rows[0] and 'date' in rows[0][0].lower():
            rows = rows[1:]
        created_entries = 0
        created_items = 0
        errors = []
        post_flag = request.POST.get('post') == '1' or request.GET.get('post') == '1'
        # تجميع حسب تعريف القيد
        from collections import defaultdict
        grouped: dict[tuple, list] = defaultdict(list)
        for idx, r in enumerate(rows, start=1):
            if not r:
                continue
            # حد أدنى من الأعمدة
            date_str = (r[0] if len(r) > 0 else '').strip()
            desc = (r[1] if len(r) > 1 else '').strip() or 'Imported Journal'
            ref = (r[2] if len(r) > 2 else '').strip()
            entry_type = (r[3] if len(r) > 3 else 'manual').strip() or 'manual'
            account_code = (r[4] if len(r) > 4 else '').strip()
            line_type = (r[5] if len(r) > 5 else '').strip().lower()  # debit/credit
            amount_str = (r[6] if len(r) > 6 else '').strip()
            cc_code = (r[7] if len(r) > 7 else '').strip()
            dt = parse_date(date_str)
            if not dt:
                errors.append(f'سطر {idx}: تاريخ غير صالح: {date_str}')
                continue
            if not account_code:
                errors.append(f'سطر {idx}: كود الحساب (account_code) مفقود')
                continue
            if line_type not in ('debit','credit'):
                errors.append(f'سطر {idx}: نوع البند (type) يجب أن يكون debit أو credit، وُجد: {line_type}')
                continue
            try:
                amount = Decimal(amount_str.replace(',', ''))
            except (InvalidOperation, ValueError):
                errors.append(f'سطر {idx}: مبلغ غير صالح: {amount_str}')
                continue
            grouped[(dt, desc, ref, entry_type)].append({
                'account_code': account_code,
                'type': line_type,
                'amount': amount,
                'cc_code': cc_code,
            })
        # إنشاء القيود
        for (dt, desc, ref, entry_type), items in grouped.items():
            # تحقق سريع من السنة المالية عند طلب الترحيل
            if post_flag:
                fy = FiscalYear.objects.filter(start_date__lte=dt, end_date__gte=dt, is_closed=False).first()
                if not fy:
                    errors.append(f'{dt} خارج نطاق سنة مالية نشطة: لن يتم ترحيل القيد.')
            try:
                with transaction.atomic():
                    je = JournalEntry.objects.create(
                        date=dt,
                        entry_type=entry_type if entry_type in dict(JournalEntry.ENTRY_TYPE) else 'manual',
                        description=desc,
                        reference=ref,
                        created_by=request.user,
                        is_posted=False,
                    )
                    debit_total = Decimal('0'); credit_total = Decimal('0')
                    for it in items:
                        acc = Account.objects.filter(code=it['account_code']).first()
                        if not acc:
                            raise ValueError(f"حساب غير موجود: {it['account_code']}")
                        cc = None
                        if it['cc_code']:
                            cc = CostCenter.objects.filter(code=it['cc_code']).first()
                        JournalEntryItem.objects.create(
                            journal_entry=je,
                            account=acc,
                            type=it['type'],
                            amount=it['amount'],
                            description=desc[:255],
                            cost_center=cc,
                        )
                        if it['type'] == 'debit':
                            debit_total += it['amount']
                        else:
                            credit_total += it['amount']
                    created_items += len(items)
                    # ترحيل إذا متوازن ومطلوب
                    if post_flag and debit_total == credit_total:
                        je.is_posted = True
                        je.full_clean(validate_unique=False)
                        je.save(update_fields=['is_posted'])
                    created_entries += 1
            except Exception as e:
                errors.append(f"فشل إنشاء قيد بتاريخ {dt}: {e}")
                continue
        return render(request, 'accounting/import_journal_result.html', {
            'created_entries': created_entries,
            'created_items': created_items,
            'errors': errors,
            'post_flag': post_flag,
        })

    return render(request, 'accounting/import_journal.html', {})


# ========================= أدوات النظام =========================

@login_required
def tools_fixes(request):
    """صفحة الإصلاحات السريعة للنظام المحاسبي.
    
    تتيح تشغيل مجموعة من الإصلاحات والتحققات التلقائية:
    - إصلاح القيود غير المتوازنة
    - إعادة حساب أرصدة الحسابات
    - تنظيف البيانات المكررة
    - التحقق من تكامل البيانات
    """
    from .models import JournalEntry, Account, JournalEntryItem
    from django.db.models import Sum, Q
    from decimal import Decimal
    
    context = {
        'fixes_run': False,
        'results': []
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        results = []
        
        if action == 'check_unbalanced':
            # التحقق من القيود غير المتوازنة
            unbalanced_count = 0
            for entry in JournalEntry.objects.all():
                if not entry.is_balanced:
                    unbalanced_count += 1
            
            results.append({
                'title': 'فحص القيود غير المتوازنة',
                'status': 'warning' if unbalanced_count > 0 else 'success',
                'message': f'تم العثور على {unbalanced_count} قيد غير متوازن' if unbalanced_count > 0 else 'جميع القيود متوازنة'
            })
        
        elif action == 'fix_unbalanced':
            # محاولة إصلاح القيود غير المتوازنة
            fixed_count = 0
            for entry in JournalEntry.objects.filter(is_posted=False):
                if not entry.is_balanced:
                    # إلغاء الترحيل للقيود غير المتوازنة
                    entry.is_posted = False
                    entry.save()
                    fixed_count += 1
            
            results.append({
                'title': 'إصلاح القيود غير المتوازنة',
                'status': 'success',
                'message': f'تم إلغاء ترحيل {fixed_count} قيد غير متوازن'
            })
        
        elif action == 'check_accounts':
            # التحقق من الحسابات
            accounts_without_code = Account.objects.filter(Q(code__isnull=True) | Q(code='')).count()
            from django.db.models import Count
            duplicate_codes = Account.objects.values('code').annotate(count=Count('code')).filter(count__gt=1).count()
            
            results.append({
                'title': 'فحص الحسابات',
                'status': 'warning' if (accounts_without_code + duplicate_codes) > 0 else 'success',
                'message': f'حسابات بدون كود: {accounts_without_code}, أكواد مكررة: {duplicate_codes}'
            })
        
        elif action == 'cleanup_data':
            # تنظيف البيانات
            deleted_count = JournalEntryItem.objects.filter(journal_entry__isnull=True).delete()[0]
            
            results.append({
                'title': 'تنظيف البيانات',
                'status': 'success',
                'message': f'تم حذف {deleted_count} عنصر قيد يتيم'
            })
        
        context['fixes_run'] = True
        context['results'] = results
    
    # إحصائيات عامة
    context.update({
        'total_entries': JournalEntry.objects.count(),
        'posted_entries': JournalEntry.objects.filter(is_posted=True).count(),
        'draft_entries': JournalEntry.objects.filter(is_posted=False).count(),
        'total_accounts': Account.objects.count(),
    })
    
    return render(request, 'accounting/tools_fixes.html', context)


@login_required
def accounting_help(request):
    """
    مركز المساعدة للنظام المحاسبي
    عرض معلومات مفيدة وروابط سريعة للمساعدة
    """
    from django.urls import reverse
    
    context = {
        'page_title': 'مركز المساعدة - النظام المحاسبي',
        'help_sections': [
            {
                'title': 'البدء السريع',
                'icon': 'bi-play-circle',
                'items': [
                    {'title': 'دليل الحسابات', 'description': 'إعداد وإدارة دليل الحسابات', 'url': reverse('accounting:chart_of_accounts')},
                    {'title': 'إنشاء قيد جديد', 'description': 'إضافة قيد محاسبي جديد', 'url': reverse('accounting:journal_entry_create')},
                    {'title': 'لوحة التحكم المحاسبية', 'description': 'نظرة عامة على النظام المحاسبي', 'url': reverse('accounting:dashboard')},
                ]
            },
            {
                'title': 'التقارير المحاسبية',
                'icon': 'bi-graph-up',
                'items': [
                    {'title': 'دفتر الأستاذ العام', 'description': 'عرض جميع حركات الحسابات', 'url': reverse('accounting:general_ledger')},
                    {'title': 'ميزان المراجعة', 'description': 'ميزان المراجعة لفترة محددة', 'url': reverse('accounting:trial_balance')},
                    {'title': 'الميزانية العمومية', 'description': 'قائمة المركز المالي', 'url': reverse('accounting:balance_sheet')},
                    {'title': 'قائمة الدخل', 'description': 'قائمة الأرباح والخسائر', 'url': reverse('accounting:income_statement')},
                ]
            },
            {
                'title': 'الأدوات والإعدادات',
                'icon': 'bi-tools',
                'items': [
                    {'title': 'إعدادات المحاسبة', 'description': 'إعدادات النظام المحاسبي', 'url': reverse('accounting:settings')},
                    {'title': 'استيراد قيود', 'description': 'استيراد قيود من ملف CSV', 'url': reverse('accounting:import_journal')},
                    {'title': 'تصدير البيانات', 'description': 'تصدير البيانات المحاسبية', 'url': reverse('accounting:export_tools')},
                    {'title': 'تشخيص النظام', 'description': 'فحص وتشخيص مشاكل النظام', 'url': reverse('accounting:diagnostics')},
                ]
            },
        ]
    }
    
    return render(request, 'accounting/help.html', context)


@login_required
def accounting_settings_overview(request):
    """
    صفحة الإعدادات العامة للنظام المحاسبي
    """
    context = {
        'page_title': 'إعدادات النظام المحاسبي',
        'settings_sections': [
            {
                'title': 'الحسابات الافتراضية',
                'description': 'تكوين الحسابات الافتراضية للعمليات التلقائية',
                'url': 'accounting:settings_defaults',
                'icon': 'bi-link-45deg'
            },
            {
                'title': 'السنة المالية',
                'description': 'إعداد وإدارة السنوات المالية',
                'url': 'accounting:fiscal_year_create',
                'icon': 'bi-calendar-range'
            },
            {
                'title': 'إعدادات الضرائب',
                'description': 'تكوين أنواع الضرائب والمعدلات',
                'url': 'accounting:tax_settings',
                'icon': 'bi-percent'
            }
        ]
    }
    
    return render(request, 'accounting/settings.html', context)


@login_required  
def accounting_settings_defaults(request):
    """
    صفحة تكوين الحسابات الافتراضية
    """
    from .models import Account
    
    context = {
        'page_title': 'الحسابات الافتراضية',
        'accounts': Account.objects.all(),
        'default_accounts': {
            'cash_account': 'الخزينة الرئيسية',
            'sales_account': 'المبيعات',
            'purchases_account': 'المشتريات', 
            'accounts_receivable': 'العملاء',
            'accounts_payable': 'الموردين',
            'cost_of_goods_sold': 'تكلفة البضاعة المباعة',
            'inventory_account': 'المخزون',
            'retained_earnings': 'الأرباح المحتجزة'
        }
    }
    
    return render(request, 'accounting/settings_defaults.html', context)


@login_required
def tax_settings(request):
    """
    صفحة إعدادات الضرائب والقيمة المضافة
    """
    from .forms import TaxSettingsForm
    from .models import AccountingSettings
    
    # الحصول على سجل الإعدادات أو إنشاؤه
    try:
        settings_instance = AccountingSettings.objects.first()
        if not settings_instance:
            settings_instance = AccountingSettings.get()  # ينشئ السجل مع القيم الافتراضية
    except Exception as e:
        logger.error(f"خطأ في جلب إعدادات المحاسبة: {e}")
        settings_instance = None
    
    if request.method == 'POST':
        form = TaxSettingsForm(request.POST, instance=settings_instance)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'تم حفظ إعدادات الضرائب بنجاح!')
                return redirect('accounting:tax_settings')
            except Exception as e:
                logger.error(f"خطأ في حفظ إعدادات الضرائب: {e}")
                messages.error(request, f'حدث خطأ أثناء الحفظ: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = TaxSettingsForm(instance=settings_instance)
    
    context = {
        'page_title': 'إعدادات الضرائب',
        'form': form,
        'settings': settings_instance,
        'breadcrumb': [
            {'title': 'المحاسبة', 'url': 'accounting:dashboard'},
            {'title': 'الإعدادات', 'url': 'accounting:settings'},
            {'title': 'إعدادات الضرائب', 'url': None}
        ]
    }
    
    return render(request, 'accounting/tax_settings.html', context)


# API Endpoints for Enhanced Functionality

@require_http_methods(["GET"])
def account_search_api(request):
    """AJAX search for accounts - used in the enhanced journal entry form"""
    try:
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 2:
            return JsonResponse({'results': []}, json_dumps_params={'ensure_ascii': False})
        
        # Cache key for the search
        cache_key = f'account_search_{hashlib.md5(query.encode()).hexdigest()[:10]}'
        cached_results = cache.get(cache_key)
        
        if cached_results is not None:
            return JsonResponse({'results': cached_results}, json_dumps_params={'ensure_ascii': False})
        
        # Search in account code and name
        accounts = Account.objects.filter(
            Q(code__icontains=query) | Q(name__icontains=query)
        ).values('id', 'code', 'name', 'type')[:20]
        
        results = []
        for account in accounts:
            results.append({
                'id': account['id'],
                'text': f"{account['code']} - {account['name']}",
                'code': account['code'],
                'name': account['name'],
                'type': account['type']
            })
        
        # Cache for 10 minutes
        cache.set(cache_key, results, 600)
        
        return JsonResponse({'results': results}, json_dumps_params={'ensure_ascii': False})
    
    except Exception as e:
        logger.error(f"Error in account search API: {str(e)}")
        return JsonResponse({'error': 'حدث خطأ في البحث'}, json_dumps_params={'ensure_ascii': False}, status=500)

@require_http_methods(["POST"])
@csrf_exempt
def journal_entry_validate_api(request):
    """Real-time validation for journal entry"""
    try:
        data = json.loads(request.body)
        
        # Validate basic structure
        items = data.get('items', [])
        if len(items) < 2:
            return JsonResponse({
                'valid': False,
                'errors': ['يجب أن تحتوي القيود على عنصرين على الأقل']
            })
        
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        errors = []
        account_ids = []
        
        for i, item in enumerate(items):
            try:
                account_id = item.get('account_id')
                debit = Decimal(str(item.get('debit', '0'))) if item.get('debit') else Decimal('0')
                credit = Decimal(str(item.get('credit', '0'))) if item.get('credit') else Decimal('0')
                
                if not account_id:
                    errors.append(f'الصف {i+1}: يجب اختيار حساب')
                    continue
                
                if debit == 0 and credit == 0:
                    errors.append(f'الصف {i+1}: يجب إدخال مبلغ في المدين أو الدائن')
                    continue
                
                if debit > 0 and credit > 0:
                    errors.append(f'الصف {i+1}: لا يمكن إدخال مبلغ في المدين والدائن معاً')
                    continue
                
                account_ids.append(account_id)
                total_debit += debit
                total_credit += credit
                
            except (ValueError, TypeError, InvalidOperation) as e:
                errors.append(f'الصف {i+1}: قيمة غير صحيحة')
        
        # Check balance
        if abs(total_debit - total_credit) > Decimal('0.01'):
            errors.append(f'القيد غير متوازن: المدين {total_debit:.2f} - الدائن {total_credit:.2f}')
        
        # Check for duplicate accounts
        if len(account_ids) != len(set(account_ids)):
            errors.append('لا يمكن استخدام نفس الحساب أكثر من مرة')
        
        # Validate accounts exist
        valid_accounts = Account.objects.filter(id__in=account_ids).count()
        if valid_accounts != len([aid for aid in account_ids if aid]):
            errors.append('بعض الحسابات المحددة غير صحيحة')
        
        return JsonResponse({
            'valid': len(errors) == 0,
            'errors': errors,
            'totals': {
                'debit': float(total_debit),
                'credit': float(total_credit),
                'balanced': abs(total_debit - total_credit) <= Decimal('0.01')
            }
        })
    
    except Exception as e:
        logger.error(f"Error in journal entry validation API: {str(e)}")
        return JsonResponse({'error': 'حدث خطأ في التحقق من القيد'}, json_dumps_params={'ensure_ascii': False}, status=500)

@require_http_methods(["POST"])
@csrf_exempt
def journal_entry_draft_save_api(request):
    """Auto-save draft journal entry"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'غير مخول'}, json_dumps_params={'ensure_ascii': False}, status=401)
        
        data = json.loads(request.body)
        
        # Create a simple cache key for the user's draft
        cache_key = f'journal_draft_{request.user.id}'
        
        # Save to cache with expiry of 1 hour
        cache.set(cache_key, {
            'data': data,
            'timestamp': timezone.now().isoformat(),
            'user_id': request.user.id
        }, 3600)
        
        return JsonResponse({
            'saved': True,
            'timestamp': timezone.now().isoformat()
        }, json_dumps_params={'ensure_ascii': False})
    
    except Exception as e:
        logger.error(f"Error saving journal entry draft: {str(e)}")
        return JsonResponse({'error': 'حدث خطأ في حفظ المسودة'}, json_dumps_params={'ensure_ascii': False}, status=500)

@require_http_methods(["GET"])
def journal_templates_api(request):
    """Get journal entry templates for quick creation"""
    try:
        # Simple predefined templates - in a real system these might come from a database
        templates = [
            {
                'id': 'cash_sale',
                'name': 'مبيعات نقدية',
                'description': 'قالب للمبيعات النقدية',
                'items': [
                    {'account_type': 'cash', 'side': 'debit', 'description': 'الصندوق'},
                    {'account_type': 'revenue', 'side': 'credit', 'description': 'المبيعات'}
                ]
            },
            {
                'id': 'cash_purchase',
                'name': 'مشتريات نقدية',
                'description': 'قالب للمشتريات النقدية',
                'items': [
                    {'account_type': 'expense', 'side': 'debit', 'description': 'المشتريات'},
                    {'account_type': 'cash', 'side': 'credit', 'description': 'الصندوق'}
                ]
            },
            {
                'id': 'salary_payment',
                'name': 'دفع رواتب',
                'description': 'قالب لدفع الرواتب',
                'items': [
                    {'account_type': 'expense', 'side': 'debit', 'description': 'مصروف الرواتب'},
                    {'account_type': 'cash', 'side': 'credit', 'description': 'الصندوق'}
                ]
            },
            {
                'id': 'rent_payment',
                'name': 'دفع إيجار',
                'description': 'قالب لدفع الإيجار',
                'items': [
                    {'account_type': 'expense', 'side': 'debit', 'description': 'مصروف الإيجار'},
                    {'account_type': 'cash', 'side': 'credit', 'description': 'الصندوق'}
                ]
            }
        ]
        
        return JsonResponse({'templates': templates}, json_dumps_params={'ensure_ascii': False})
    
    except Exception as e:
        logger.error(f"Error getting journal templates: {str(e)}")
        return JsonResponse({'error': 'حدث خطأ في تحميل القوالب'}, json_dumps_params={'ensure_ascii': False}, status=500)


@login_required
def accounting_dashboard_new(request):
    """
    لوحة التحكم الجديدة للمحاسبة - البنية المحسّنة
    مع 4 تبويبات أفقية وتصفية حسب دور المستخدم
    """
    from .accounting_structure import (
        ACCOUNTING_TABS,
        ACCOUNTING_STRUCTURE,
        ACCOUNTING_ADVANCED_SETTINGS,
        get_user_accounting_tabs,
        filter_items_by_user
    )
    from .permissions import get_user_accounting_role, AccountingRoles
    
    # الحصول على دور المستخدم
    user_role = get_user_accounting_role(request.user)
    
    # الحصول على التبويبات المتاحة للمستخدم
    available_tab_ids = get_user_accounting_tabs(request.user)
    
    # تصفية التبويبات
    tabs = {
        tab_id: tab_data 
        for tab_id, tab_data in ACCOUNTING_TABS.items() 
        if tab_id in available_tab_ids
    }
    
    # تصفية العناصر داخل كل تبويب
    filtered_structure = {}
    for tab_id in available_tab_ids:
        if tab_id not in ACCOUNTING_STRUCTURE:
            continue
            
        filtered_structure[tab_id] = {
            'groups': []
        }
        
        for group in ACCOUNTING_STRUCTURE[tab_id].get('groups', []):
            # تصفية العناصر داخل المجموعة
            filtered_items = filter_items_by_user(group.get('items', []), request.user)
            
            # إضافة المجموعة فقط إذا كانت تحتوي على عناصر
            if filtered_items:
                filtered_structure[tab_id]['groups'].append({
                    'id': group.get('id'),
                    'label': group.get('label'),
                    'icon': group.get('icon'),
                    'items': filtered_items
                })
    
    # إضافة الإعدادات المتقدمة للمدير المالي فقط
    advanced_settings = None
    if user_role == AccountingRoles.CFO:
        advanced_items = filter_items_by_user(
            ACCOUNTING_ADVANCED_SETTINGS.get('items', []), 
            request.user
        )
        if advanced_items:
            advanced_settings = {
                'id': ACCOUNTING_ADVANCED_SETTINGS.get('id'),
                'label': ACCOUNTING_ADVANCED_SETTINGS.get('label'),
                'icon': ACCOUNTING_ADVANCED_SETTINGS.get('icon'),
                'items': advanced_items
            }
    
    # حساب الشارات (Badges)
    badges = calculate_dashboard_badges(request.user)
    
    context = {
        'tabs': tabs,
        'structure': filtered_structure,
        'advanced_settings': advanced_settings,
        'user_role': user_role,
        'user_role_label': AccountingRoles.ROLE_LABELS.get(user_role, '') if user_role else '',
        'badges': badges,
    }
    
    return render(request, 'accounting/accounting_dashboard_new.html', context)


def calculate_dashboard_badges(user):
    """حساب قيم الشارات (Badges) للوحة التحكم"""
    badges = {}
    
    try:
        # قيود المسودة
        badges['draft_journal_count'] = JournalEntry.objects.filter(
            is_posted=False
        ).count()
        
        # الفواتير المعلقة
        from sales.models import Invoice
        badges['pending_invoices_count'] = Invoice.objects.filter(
            status='pending'
        ).count()
        
        # فواتير الشراء المعلقة
        from purchases.models import PurchaseBill
        badges['pending_purchase_count'] = PurchaseBill.objects.filter(
            status='pending'
        ).count()
        
        # الذمم المدينة المتأخرة
        from sales.models import Invoice
        from datetime import date
        badges['overdue_receivables_count'] = Invoice.objects.filter(
            status='posted',
            due_date__lt=date.today()
        ).exclude(amount_paid__gte=F('total')).count() if hasattr(Invoice, 'due_date') else 0
        
        # الذمم الدائنة القادمة
        badges['upcoming_payables_count'] = PurchaseBill.objects.filter(
            status='posted',
            due_date__gte=date.today(),
            due_date__lte=date.today() + timedelta(days=7)
        ).count() if hasattr(PurchaseBill, 'due_date') else 0
        
        # البنوك التي تحتاج تسوية
        badges['bank_reconcile_pending'] = BankAccount.objects.filter(
            is_active=True,
            last_reconciled_date__lt=date.today() - timedelta(days=30)
        ).count() if BankAccount.objects.exists() else 0
        
    except Exception as e:
        logger.error(f"Error calculating dashboard badges: {str(e)}")
    
    return badges

# =============================
# تسجيل الحسابات - إيراد ومنصرف
# =============================

@login_required
@permission_required('accounting.add_accountentry', raise_exception=True)
def revenue_create(request):
    """إنشاء قيد إيراد جديد"""
    from .models import AccountEntry, FinancialAnalysis1, FinancialAnalysis2, Account, Treasury, Bank, ElectronicAccount, FawryMachine, VisaMachine
    from partners.models import Supplier
    from django.http import JsonResponse
    from django.contrib.contenttypes.models import ContentType
    
    if request.method == 'POST':
        try:
            # التحقق من التكرار إذا كان مطلوباً
            check_duplicate = request.POST.get('check_duplicate') == 'true'
            if check_duplicate:
                amount = Decimal(request.POST.get('amount', '0'))
                date = request.POST.get('date')
                ledger_account_id = request.POST.get('ledger_account')
                
                duplicates = AccountEntry.objects.filter(
                    entry_type='revenue',
                    date=date,
                    amount=amount,
                    ledger_account_id=ledger_account_id
                ).count()
                
                if duplicates > 0:
                    return JsonResponse({
                        'duplicate_found': True,
                        'message': f'تحذير: يوجد {duplicates} قيد مشابه بنفس التاريخ والمبلغ والحساب'
                    })
            
            # معالجة صاحب العملية (owner)
            owner_type = request.POST.get('owner_type')
            owner_id = request.POST.get('owner_id')
            owner_content_type = None
            owner_object_id = None
            
            if owner_type and owner_id:
                # تحديد نوع النموذج بناءً على النوع المحدد
                model_map = {
                    'supplier': ('partners', 'Supplier'),
                    'customer': ('crm', 'Customer'),
                    'driver': ('fleet', 'Driver'),
                    'employee': ('hr', 'Employee'),
                }
                
                if owner_type in model_map:
                    app_label, model_name = model_map[owner_type]
                    try:
                        owner_content_type = ContentType.objects.get(
                            app_label=app_label, 
                            model=model_name.lower()
                        )
                        owner_object_id = int(owner_id)
                    except (ContentType.DoesNotExist, ValueError):
                        pass
            
            entry = AccountEntry.objects.create(
                entry_type='revenue',
                date=request.POST.get('date'),
                amount=Decimal(request.POST.get('amount', '0')),
                description=request.POST.get('description', ''),
                ledger_account_id=request.POST.get('ledger_account'),
                financial_analysis_1_id=request.POST.get('financial_analysis_1') or None,
                financial_analysis_2_id=request.POST.get('financial_analysis_2') or None,
                cost_center_id=request.POST.get('cost_center') or None,
                owner_content_type=owner_content_type,
                owner_object_id=owner_object_id,
                supplier_id=request.POST.get('supplier') or None,  # للتوافق مع النظام القديم
                # حقول وجهة الدخول
                destination_type=request.POST.get('destination_type') or None,
                treasury_id=request.POST.get('treasury') or None,
                bank_id=request.POST.get('bank') or None,
                electronic_account_id=request.POST.get('electronic_account') or None,
                fawry_machine_id=request.POST.get('fawry_machine') or None,
                visa_machine_id=request.POST.get('visa_machine') or None,
                created_by=request.user
            )
            
            # إنشاء القيد المحاسبي التلقائي
            from core.integration_services import AccountingIntegrationService
            try:
                journal_entry = AccountingIntegrationService.create_revenue_expense_journal_entry(
                    entry, 
                    request.user
                )
                if journal_entry:
                    messages.success(
                        request, 
                        f'تم تسجيل الإيراد بنجاح - رقم {entry.id} | قيد محاسبي: {journal_entry.number}'
                    )
                else:
                    messages.success(request, f'تم تسجيل الإيراد بنجاح - رقم {entry.id}')
            except Exception as je_error:
                logger.error(f"خطأ في إنشاء القيد التلقائي: {str(je_error)}")
                messages.success(request, f'تم تسجيل الإيراد بنجاح - رقم {entry.id}')
                messages.warning(
                    request,
                    f'لم يتم إنشاء القيد المحاسبي التلقائي: {str(je_error)}'
                )
            
            # حفظ + جديد
            if request.POST.get('continue_new') == 'true':
                return redirect('accounting:revenue_create')
            return redirect('accounting:account_entries_list')
        except Exception as e:
            messages.error(request, f'خطأ في تسجيل الإيراد: {str(e)}')
    
    # جلب بيانات أصحاب العمليات
    from crm.models import Customer
    from fleet.models import Driver
    from hr.models import Employee
    
    # تحضير قائمة العملاء مع اسم العرض
    customers_list = []
    for c in Customer.objects.all()[:500]:
        display_name = c.company_name or f"{c.first_name or ''} {c.last_name or ''}".strip() or f"عميل #{c.id}"
        customers_list.append({'id': c.id, 'display_name': display_name})
    
    # تحضير قائمة الموظفين مع اسم العرض
    employees_list = []
    for e in Employee.objects.filter(status='active')[:500]:
        full_name = f"{e.first_name or ''} {e.last_name or ''}".strip() or f"موظف #{e.id}"
        employees_list.append({'id': e.id, 'full_name': full_name})
    
    context = {
        'title': 'تسجيل إيراد جديد',
        'entry_type': 'revenue',
        'entry_type_label': 'إيراد',
        'accounts': Account.objects.filter(is_active=True, can_post=True).order_by('code'),
        'analysis_1_list': FinancialAnalysis1.objects.filter(is_active=True),
        'analysis_2_list': FinancialAnalysis2.objects.filter(is_active=True),
        'cost_centers': CostCenter.objects.filter(is_active=True),
        'suppliers': Supplier.objects.all().order_by('name'),
        'customers': customers_list,
        'drivers': Driver.objects.filter(active=True).order_by('name')[:500],
        'employees': employees_list,
        # إضافة حقول وجهة الدخول
        'treasuries': Treasury.objects.filter(is_active=True).order_by('name'),
        'banks': Bank.objects.filter(is_active=True).order_by('name'),
        'electronic_accounts': ElectronicAccount.objects.filter(is_active=True).order_by('name'),
        'fawry_machines': FawryMachine.objects.filter(is_active=True).order_by('name'),
        'visa_machines': VisaMachine.objects.select_related('bank').filter(is_active=True).order_by('name'),
    }
    return render(request, 'accounting/account_entry_form.html', context)


@login_required
@permission_required('accounting.add_accountentry', raise_exception=True)
def expense_create(request):
    """إنشاء قيد منصرف جديد"""
    from .models import AccountEntry, FinancialAnalysis1, FinancialAnalysis2, Account, Treasury, Bank, ElectronicAccount, FawryMachine, VisaMachine
    from django.http import JsonResponse
    from django.contrib.contenttypes.models import ContentType
    
    if request.method == 'POST':
        try:
            # التحقق من التكرار إذا كان مطلوباً
            check_duplicate = request.POST.get('check_duplicate') == 'true'
            if check_duplicate:
                amount = Decimal(request.POST.get('amount', '0'))
                date = request.POST.get('date')
                ledger_account_id = request.POST.get('ledger_account')
                
                duplicates = AccountEntry.objects.filter(
                    entry_type='expense',
                    date=date,
                    amount=amount,
                    ledger_account_id=ledger_account_id
                ).count()
                
                if duplicates > 0:
                    return JsonResponse({
                        'duplicate_found': True,
                        'message': f'تحذير: يوجد {duplicates} قيد مشابه بنفس التاريخ والمبلغ والحساب'
                    })
            
            # معالجة صاحب العملية (owner)
            owner_type = request.POST.get('owner_type')
            owner_id = request.POST.get('owner_id')
            owner_content_type = None
            owner_object_id = None
            
            if owner_type and owner_id:
                # تحديد نوع النموذج بناءً على النوع المحدد
                model_map = {
                    'supplier': ('partners', 'Supplier'),
                    'customer': ('crm', 'Customer'),
                    'driver': ('fleet', 'Driver'),
                    'employee': ('hr', 'Employee'),
                }
                
                if owner_type in model_map:
                    app_label, model_name = model_map[owner_type]
                    try:
                        owner_content_type = ContentType.objects.get(
                            app_label=app_label, 
                            model=model_name.lower()
                        )
                        owner_object_id = int(owner_id)
                    except (ContentType.DoesNotExist, ValueError):
                        pass
            
            entry = AccountEntry.objects.create(
                entry_type='expense',
                date=request.POST.get('date'),
                amount=Decimal(request.POST.get('amount', '0')),
                description=request.POST.get('description', ''),
                ledger_account_id=request.POST.get('ledger_account'),
                financial_analysis_1_id=request.POST.get('financial_analysis_1') or None,
                financial_analysis_2_id=request.POST.get('financial_analysis_2') or None,
                cost_center_id=request.POST.get('cost_center') or None,
                owner_content_type=owner_content_type,
                owner_object_id=owner_object_id,
                # حقول وجهة الخروج
                destination_type=request.POST.get('destination_type') or None,
                treasury_id=request.POST.get('treasury') or None,
                bank_id=request.POST.get('bank') or None,
                electronic_account_id=request.POST.get('electronic_account') or None,
                fawry_machine_id=request.POST.get('fawry_machine') or None,
                visa_machine_id=request.POST.get('visa_machine') or None,
                created_by=request.user
            )
            
            # إنشاء القيد المحاسبي التلقائي
            from core.integration_services import AccountingIntegrationService
            try:
                journal_entry = AccountingIntegrationService.create_revenue_expense_journal_entry(
                    entry, 
                    request.user
                )
                if journal_entry:
                    messages.success(
                        request, 
                        f'تم تسجيل المنصرف بنجاح - رقم {entry.id} | قيد محاسبي: {journal_entry.number}'
                    )
                else:
                    messages.success(request, f'تم تسجيل المنصرف بنجاح - رقم {entry.id}')
            except Exception as je_error:
                logger.error(f"خطأ في إنشاء القيد التلقائي: {str(je_error)}")
                messages.success(request, f'تم تسجيل المنصرف بنجاح - رقم {entry.id}')
                messages.warning(
                    request,
                    f'لم يتم إنشاء القيد المحاسبي التلقائي: {str(je_error)}'
                )
            
            # حفظ + جديد
            if request.POST.get('continue_new') == 'true':
                return redirect('accounting:expense_create')
            return redirect('accounting:account_entries_list')
        except Exception as e:
            messages.error(request, f'خطأ في تسجيل المنصرف: {str(e)}')
    
    # جلب بيانات أصحاب العمليات
    from partners.models import Supplier
    from crm.models import Customer
    from fleet.models import Driver
    from hr.models import Employee
    
    # تحضير قائمة العملاء مع اسم العرض
    customers_list = []
    for c in Customer.objects.all()[:500]:
        display_name = c.company_name or f"{c.first_name or ''} {c.last_name or ''}".strip() or f"عميل #{c.id}"
        customers_list.append({'id': c.id, 'display_name': display_name})
    
    # تحضير قائمة الموظفين مع اسم العرض
    employees_list = []
    for e in Employee.objects.filter(status='active')[:500]:
        full_name = f"{e.first_name or ''} {e.last_name or ''}".strip() or f"موظف #{e.id}"
        employees_list.append({'id': e.id, 'full_name': full_name})
    
    context = {
        'title': 'تسجيل منصرف جديد',
        'entry_type': 'expense',
        'entry_type_label': 'منصرف',
        'accounts': Account.objects.filter(is_active=True, can_post=True).order_by('code'),
        'analysis_1_list': FinancialAnalysis1.objects.filter(is_active=True),
        'analysis_2_list': FinancialAnalysis2.objects.filter(is_active=True),
        'cost_centers': CostCenter.objects.filter(is_active=True),
        'suppliers': Supplier.objects.all().order_by('name'),
        'customers': customers_list,
        'drivers': Driver.objects.filter(active=True).order_by('name')[:500],
        'employees': employees_list,
        # إضافة حقول وجهة الخروج
        'treasuries': Treasury.objects.filter(is_active=True).order_by('name'),
        'banks': Bank.objects.filter(is_active=True).order_by('name'),
        'electronic_accounts': ElectronicAccount.objects.filter(is_active=True).order_by('name'),
        'fawry_machines': FawryMachine.objects.filter(is_active=True).order_by('name'),
        'visa_machines': VisaMachine.objects.select_related('bank').filter(is_active=True).order_by('name'),
    }
    return render(request, 'accounting/account_entry_form.html', context)


@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def get_recent_entries(request):
    """جلب آخر القيود للنسخ السريع"""
    from .models import AccountEntry
    from django.http import JsonResponse
    
    entry_type = request.GET.get('type', 'revenue')
    limit = int(request.GET.get('limit', 5))
    
    entries = AccountEntry.objects.filter(
        entry_type=entry_type,
        created_by=request.user
    ).select_related(
        'ledger_account', 'financial_analysis_1', 'financial_analysis_2', 
        'cost_center', 'supplier'
    ).order_by('-created_at')[:limit]
    
    data = [{
        'id': e.id,
        'date': str(e.date),
        'amount': str(e.amount),
        'description': e.description,
        'ledger_account': e.ledger_account_id,
        'ledger_account_name': f"{e.ledger_account.code} - {e.ledger_account.name}" if e.ledger_account else '',
        'financial_analysis_1': e.financial_analysis_1_id,
        'financial_analysis_2': e.financial_analysis_2_id,
        'cost_center': e.cost_center_id,
        'supplier': e.supplier_id,
    } for e in entries]
    
    return JsonResponse({'entries': data})


@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def account_entries_list(request):
    """قائمة قيود الحسابات"""
    from .models import AccountEntry
    
    entries = AccountEntry.objects.select_related(
        'ledger_account', 'financial_analysis_1', 'financial_analysis_2', 
        'cost_center', 'created_by', 'supplier'
    ).order_by('-date', '-created_at')
    
    # فلترة حسب النوع
    entry_type = request.GET.get('type')
    if entry_type in ['revenue', 'expense']:
        entries = entries.filter(entry_type=entry_type)
    
    # فلترة حسب التاريخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        entries = entries.filter(date__gte=date_from)
    if date_to:
        entries = entries.filter(date__lte=date_to)
    
    # حساب المجاميع
    totals = entries.aggregate(
        total_revenue=Sum('amount', filter=Q(entry_type='revenue')),
        total_expense=Sum('amount', filter=Q(entry_type='expense')),
    )
    
    context = {
        'title': 'قيود الحسابات',
        'entries': entries[:100],  # الحد الأقصى 100 قيد
        'totals': totals,
        'current_type': entry_type,
    }
    return render(request, 'accounting/account_entries_list.html', context)


@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def supplier_revenue_report(request):
    """تقرير ملخص الإيرادات حسب أصحاب العمليات (موردين، عملاء، سائقين، إلخ)"""
    from .models import AccountEntry
    from partners.models import Supplier
    from datetime import date
    from django.contrib.contenttypes.models import ContentType
    
    # فلترة حسب التاريخ
    date_from = request.GET.get('date_from', date.today().replace(month=1, day=1).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    # جلب القيود التي لها صاحب عملية
    entries_with_owner = AccountEntry.objects.filter(
        entry_type='revenue',
        date__range=[date_from, date_to],
        owner_content_type__isnull=False,
        owner_object_id__isnull=False
    ).select_related('owner_content_type')
    
    # تجميع البيانات حسب نوع وصاحب العملية
    owners_data = {}
    
    for entry in entries_with_owner:
        if entry.owner:
            owner_key = f"{entry.owner_content_type.model}_{entry.owner_object_id}"
            
            if owner_key not in owners_data:
                owners_data[owner_key] = {
                    'owner': entry.owner,
                    'owner_name': entry.owner_name,
                    'owner_type': entry.owner_content_type.model,
                    'owner_type_display': entry.owner_content_type.name,
                    'total_revenue': Decimal('0'),
                    'entries_count': 0,
                }
            
            owners_data[owner_key]['total_revenue'] += entry.amount
            owners_data[owner_key]['entries_count'] += 1
    
    # جلب الموردين من الحقل القديم للتوافق
    old_suppliers = Supplier.objects.filter(
        revenue_entries__entry_type='revenue',
        revenue_entries__date__range=[date_from, date_to],
        revenue_entries__owner_content_type__isnull=True  # فقط القيود التي لا تستخدم النظام الجديد
    ).distinct()
    
    for supplier in old_suppliers:
        entries = AccountEntry.objects.filter(
            supplier=supplier,
            entry_type='revenue',
            date__range=[date_from, date_to],
            owner_content_type__isnull=True
        )
        
        total_revenue = entries.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        count = entries.count()
        
        if total_revenue > 0:
            owner_key = f"supplier_old_{supplier.id}"
            owners_data[owner_key] = {
                'owner': supplier,
                'owner_name': supplier.name,
                'owner_type': 'supplier',
                'owner_type_display': 'مورد',
                'total_revenue': total_revenue,
                'entries_count': count,
            }
    
    # تحويل إلى قائمة وترتيب حسب الإيراد
    owners_list = list(owners_data.values())
    owners_list.sort(key=lambda x: x['total_revenue'], reverse=True)
    
    # إجمالي عام
    total_all = sum(o['total_revenue'] for o in owners_list)
    
    context = {
        'title': 'تقرير الإيرادات حسب أصحاب العمليات',
        'suppliers_data': owners_list,  # للتوافق مع القالب الحالي
        'total_all': total_all,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'accounting/supplier_revenue_report.html', context)


@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def supplier_revenue_detail(request, supplier_id):
    """تقرير تفصيلي لإيرادات مورد محدد"""
    from .models import AccountEntry
    from partners.models import Supplier
    from datetime import date
    
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    # فلترة حسب التاريخ
    date_from = request.GET.get('date_from', date.today().replace(month=1, day=1).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    entries = AccountEntry.objects.filter(
        supplier=supplier,
        entry_type='revenue',
        date__range=[date_from, date_to]
    ).select_related(
        'ledger_account', 'financial_analysis_1', 'financial_analysis_2', 
        'cost_center', 'created_by'
    ).order_by('-date', '-created_at')
    
    total_revenue = entries.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    context = {
        'title': f'إيرادات المورد: {supplier.name}',
        'supplier': supplier,
        'entries': entries,
        'total_revenue': total_revenue,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'accounting/supplier_revenue_detail.html', context)


@login_required
def get_owner_options(request):
    """AJAX endpoint لجلب خيارات صاحب العملية بناءً على النوع المحدد"""
    from django.http import JsonResponse
    from partners.models import Supplier
    from fleet.models import Driver
    
    owner_type = request.GET.get('type', '')
    
    try:
        options = []
        
        if owner_type == 'supplier':
            # جلب الموردين
            suppliers = Supplier.objects.all().order_by('name')[:500]
            options = [{'id': s.id, 'name': s.name} for s in suppliers]
            
        elif owner_type == 'customer':
            # جلب العملاء من CRM
            try:
                from crm.models import Customer as CRMCustomer
                customers = CRMCustomer.objects.all()[:500]
                options = []
                for c in customers:
                    # محاولة الحصول على اسم العميل من الحقول المختلفة
                    name = c.company_name or f"{c.first_name or ''} {c.last_name or ''}".strip() or f"عميل #{c.id}"
                    options.append({'id': c.id, 'name': name})
            except Exception as e:
                print(f"Error loading customers: {e}")
                options = []
                
        elif owner_type == 'driver':
            # جلب السائقين
            try:
                drivers = Driver.objects.filter(active=True).order_by('name')[:500]
                options = [{'id': d.id, 'name': d.name} for d in drivers]
            except Exception as e:
                print(f"Error loading drivers: {e}")
                options = []
            
        elif owner_type == 'employee':
            # جلب الموظفين
            try:
                from hr.models import Employee
                employees = Employee.objects.filter(status='active')[:500]
                options = []
                for e in employees:
                    name = f"{e.first_name or ''} {e.last_name or ''}".strip() or f"موظف #{e.id}"
                    options.append({'id': e.id, 'name': name})
            except Exception as e:
                print(f"Error loading employees: {e}")
                options = []
        
        return JsonResponse({
            'success': True,
            'options': options,
            'count': len(options)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@permission_required('accounting.view_financialanalysis1', raise_exception=True)
def financial_analysis_1_list(request):
    """قائمة التحليل المالي 1"""
    from .models import FinancialAnalysis1
    
    items = FinancialAnalysis1.objects.all().order_by('code')
    
    if request.method == 'POST' and request.user.has_perm('accounting.add_financialanalysis1'):
        code = request.POST.get('code')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if code and name:
            FinancialAnalysis1.objects.create(
                code=code, name=name, description=description
            )
            messages.success(request, 'تم إضافة التحليل المالي بنجاح')
            return redirect('accounting:financial_analysis_1_list')
    
    context = {
        'title': 'التحليلات المالية 1',
        'items': items,
        'can_add': request.user.has_perm('accounting.add_financialanalysis1'),
    }
    return render(request, 'accounting/financial_analysis_list.html', context)


@login_required
@permission_required('accounting.view_financialanalysis2', raise_exception=True)
def financial_analysis_2_list(request):
    """قائمة التحليل المالي 2"""
    from .models import FinancialAnalysis2
    
    items = FinancialAnalysis2.objects.all().order_by('code')
    
    if request.method == 'POST' and request.user.has_perm('accounting.add_financialanalysis2'):
        code = request.POST.get('code')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if code and name:
            FinancialAnalysis2.objects.create(
                code=code, name=name, description=description
            )
            messages.success(request, 'تم إضافة التحليل المالي بنجاح')
            return redirect('accounting:financial_analysis_2_list')
    
    context = {
        'title': 'التحليلات المالية 2',
        'items': items,
        'can_add': request.user.has_perm('accounting.add_financialanalysis2'),
    }
    return render(request, 'accounting/financial_analysis_list.html', context)


@login_required
def ledger_accounts_list(request):
    """دفتر الأستاذ - قائمة الحسابات"""
    accounts = Account.objects.filter(can_post=True, is_active=True).order_by('code')
    
    context = {
        'title': 'دفتر الأستاذ',
        'accounts': accounts,
    }
    return render(request, 'accounting/ledger_accounts_list.html', context)


# ============================================
# إدارة الحسابات الإلكترونية
# ============================================

@login_required
def electronic_accounts_list(request):
    """قائمة الحسابات الإلكترونية"""
    from .models import ElectronicAccount
    
    accounts = ElectronicAccount.objects.all().order_by('-is_active', 'name')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        accounts = accounts.filter(
            models.Q(name__icontains=search_query) |
            models.Q(code__icontains=search_query) |
            models.Q(phone_number__icontains=search_query)
        )
    
    # الفلترة حسب النوع
    account_type = request.GET.get('account_type', '')
    if account_type:
        accounts = accounts.filter(account_type=account_type)
    
    context = {
        'title': 'الحسابات الإلكترونية',
        'accounts': accounts,
        'search_query': search_query,
        'account_type': account_type,
    }
    return render(request, 'accounting/electronic_accounts_list.html', context)


@login_required
def electronic_account_create(request):
    """إضافة حساب إلكتروني جديد"""
    from .models import ElectronicAccount, Account
    
    if request.method == 'POST':
        try:
            account = ElectronicAccount.objects.create(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                account_type=request.POST.get('account_type'),
                phone_number=request.POST.get('phone_number', ''),
                email=request.POST.get('email', ''),
                account_id=request.POST.get('account_id', ''),
                current_balance=Decimal(request.POST.get('current_balance', '0')),
                linked_account_id=request.POST.get('linked_account') or None,
                is_active=request.POST.get('is_active') == 'on',
                notes=request.POST.get('notes', '')
            )
            messages.success(request, f'تم إضافة الحساب الإلكتروني "{account.name}" بنجاح')
            return redirect('accounting:electronic_accounts_list')
        except Exception as e:
            messages.error(request, f'خطأ في إضافة الحساب: {str(e)}')
    
    context = {
        'title': 'إضافة حساب إلكتروني جديد',
        'ledger_accounts': Account.objects.filter(is_active=True).order_by('code'),
    }
    return render(request, 'accounting/electronic_account_form.html', context)


@login_required
def electronic_account_edit(request, pk):
    """تعديل حساب إلكتروني"""
    from .models import ElectronicAccount, Account
    
    account = get_object_or_404(ElectronicAccount, pk=pk)
    
    if request.method == 'POST':
        try:
            account.name = request.POST.get('name')
            account.code = request.POST.get('code')
            account.account_type = request.POST.get('account_type')
            account.phone_number = request.POST.get('phone_number', '')
            account.email = request.POST.get('email', '')
            account.account_id = request.POST.get('account_id', '')
            account.current_balance = Decimal(request.POST.get('current_balance', '0'))
            account.linked_account_id = request.POST.get('linked_account') or None
            account.is_active = request.POST.get('is_active') == 'on'
            account.notes = request.POST.get('notes', '')
            account.save()
            
            messages.success(request, f'تم تحديث الحساب "{account.name}" بنجاح')
            return redirect('accounting:electronic_accounts_list')
        except Exception as e:
            messages.error(request, f'خطأ في تحديث الحساب: {str(e)}')
    
    context = {
        'title': 'تعديل حساب إلكتروني',
        'account': account,
        'ledger_accounts': Account.objects.filter(is_active=True).order_by('code'),
    }
    return render(request, 'accounting/electronic_account_form.html', context)


@login_required
def electronic_account_delete(request, pk):
    """حذف حساب إلكتروني"""
    from .models import ElectronicAccount
    
    account = get_object_or_404(ElectronicAccount, pk=pk)
    
    if request.method == 'POST':
        account_name = account.name
        account.delete()
        messages.success(request, f'تم حذف الحساب "{account_name}" بنجاح')
        return redirect('accounting:electronic_accounts_list')
    
    context = {
        'title': 'حذف حساب إلكتروني',
        'account': account,
    }
    return render(request, 'accounting/electronic_account_confirm_delete.html', context)


# ============================================
# إدارة الخزائن
# ============================================

@login_required
def treasuries_list(request):
    """قائمة الخزائن"""
    from .models import Treasury
    
    treasuries = Treasury.objects.select_related('responsible_person', 'showroom').all().order_by('-is_active', 'name')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        treasuries = treasuries.filter(
            models.Q(name__icontains=search_query) |
            models.Q(code__icontains=search_query) |
            models.Q(location__icontains=search_query)
        )
    
    context = {
        'title': 'الخزائن',
        'treasuries': treasuries,
        'search_query': search_query,
    }
    return render(request, 'accounting/treasuries_list.html', context)


@login_required
def treasury_create(request):
    """إضافة خزينة جديدة"""
    from .models import Treasury, Account
    
    if request.method == 'POST':
        try:
            treasury = Treasury.objects.create(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                location=request.POST.get('location', ''),
                responsible_person_id=request.POST.get('responsible_person') or None,
                current_balance=Decimal(request.POST.get('current_balance', '0')),
                linked_account_id=request.POST.get('linked_account') or None,
                showroom_id=request.POST.get('showroom') or None,
                is_active=request.POST.get('is_active') == 'on',
                notes=request.POST.get('notes', '')
            )
            messages.success(request, f'تم إضافة الخزينة "{treasury.name}" بنجاح')
            return redirect('accounting:treasuries_list')
        except Exception as e:
            messages.error(request, f'خطأ في إضافة الخزينة: {str(e)}')
    
    # جلب المعارض
    try:
        from showrooms.models import Showroom
        showrooms = Showroom.objects.filter(is_active=True).order_by('name')
    except:
        showrooms = []
    
    context = {
        'title': 'إضافة خزينة جديدة',
        'ledger_accounts': Account.objects.filter(is_active=True).order_by('code'),
        'users': User.objects.filter(is_active=True).order_by('username'),
        'showrooms': showrooms,
    }
    return render(request, 'accounting/treasury_form.html', context)


@login_required
def treasury_edit(request, pk):
    """تعديل خزينة"""
    from .models import Treasury, Account
    
    treasury = get_object_or_404(Treasury, pk=pk)
    
    if request.method == 'POST':
        try:
            treasury.name = request.POST.get('name')
            treasury.code = request.POST.get('code')
            treasury.location = request.POST.get('location', '')
            treasury.responsible_person_id = request.POST.get('responsible_person') or None
            treasury.current_balance = Decimal(request.POST.get('current_balance', '0'))
            treasury.linked_account_id = request.POST.get('linked_account') or None
            treasury.showroom_id = request.POST.get('showroom') or None
            treasury.is_active = request.POST.get('is_active') == 'on'
            treasury.notes = request.POST.get('notes', '')
            treasury.save()
            
            messages.success(request, f'تم تحديث الخزينة "{treasury.name}" بنجاح')
            return redirect('accounting:treasuries_list')
        except Exception as e:
            messages.error(request, f'خطأ في تحديث الخزينة: {str(e)}')
    
    # جلب المعارض
    try:
        from showrooms.models import Showroom
        showrooms = Showroom.objects.filter(is_active=True).order_by('name')
    except:
        showrooms = []
    
    context = {
        'title': 'تعديل خزينة',
        'treasury': treasury,
        'ledger_accounts': Account.objects.filter(is_active=True).order_by('code'),
        'users': User.objects.filter(is_active=True).order_by('username'),
        'showrooms': showrooms,
    }
    return render(request, 'accounting/treasury_form.html', context)


@login_required
def treasury_delete(request, pk):
    """حذف خزينة"""
    from .models import Treasury
    
    treasury = get_object_or_404(Treasury, pk=pk)
    
    if request.method == 'POST':
        treasury_name = treasury.name
        treasury.delete()
        messages.success(request, f'تم حذف الخزينة "{treasury_name}" بنجاح')
        return redirect('accounting:treasuries_list')
    
    context = {
        'title': 'حذف خزينة',
        'treasury': treasury,
    }
    return render(request, 'accounting/treasury_confirm_delete.html', context)


# ============================================
# إدارة البنوك
# ============================================

@login_required
def banks_list(request):
    """قائمة البنوك"""
    from .models import Bank
    
    banks = Bank.objects.all().order_by('-is_active', 'name')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        banks = banks.filter(
            models.Q(name__icontains=search_query) |
            models.Q(code__icontains=search_query) |
            models.Q(account_number__icontains=search_query)
        )
    
    context = {
        'title': 'البنوك',
        'banks': banks,
        'search_query': search_query,
    }
    return render(request, 'accounting/banks_list.html', context)


@login_required
def bank_create(request):
    """إضافة بنك جديد"""
    from .models import Bank
    
    if request.method == 'POST':
        try:
            bank = Bank.objects.create(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                account_number=request.POST.get('account_number', ''),
                address=request.POST.get('address', ''),
                phone=request.POST.get('phone', ''),
                email=request.POST.get('email', ''),
                contact_person=request.POST.get('contact_person', ''),
                swift_code=request.POST.get('swift_code', ''),
                current_balance=Decimal(request.POST.get('current_balance', '0')),
                is_active=request.POST.get('is_active') == 'on'
            )
            messages.success(request, f'تم إضافة البنك "{bank.name}" بنجاح')
            return redirect('accounting:banks_list')
        except Exception as e:
            messages.error(request, f'خطأ في إضافة البنك: {str(e)}')
    
    context = {
        'title': 'إضافة بنك جديد',
    }
    return render(request, 'accounting/bank_form.html', context)


@login_required
def bank_edit(request, pk):
    """تعديل بنك"""
    from .models import Bank
    
    bank = get_object_or_404(Bank, pk=pk)
    
    if request.method == 'POST':
        try:
            bank.name = request.POST.get('name')
            bank.code = request.POST.get('code')
            bank.account_number = request.POST.get('account_number', '')
            bank.address = request.POST.get('address', '')
            bank.phone = request.POST.get('phone', '')
            bank.email = request.POST.get('email', '')
            bank.contact_person = request.POST.get('contact_person', '')
            bank.swift_code = request.POST.get('swift_code', '')
            bank.current_balance = Decimal(request.POST.get('current_balance', '0'))
            bank.is_active = request.POST.get('is_active') == 'on'
            bank.save()
            
            messages.success(request, f'تم تحديث البنك "{bank.name}" بنجاح')
            return redirect('accounting:banks_list')
        except Exception as e:
            messages.error(request, f'خطأ في تحديث البنك: {str(e)}')
    
    context = {
        'title': 'تعديل بنك',
        'bank': bank,
    }
    return render(request, 'accounting/bank_form.html', context)


@login_required
def bank_delete(request, pk):
    """حذف بنك"""
    from .models import Bank
    
    bank = get_object_or_404(Bank, pk=pk)
    
    if request.method == 'POST':
        bank_name = bank.name
        bank.delete()
        messages.success(request, f'تم حذف البنك "{bank_name}" بنجاح')
        return redirect('accounting:banks_list')
    
    context = {
        'title': 'حذف بنك',
        'bank': bank,
    }
    return render(request, 'accounting/bank_confirm_delete.html', context)


# ============================================
# إدارة ماكينات الفوري
# ============================================

@login_required
def fawry_machines_list(request):
    """قائمة ماكينات الفوري"""
    from .models import FawryMachine
    
    machines = FawryMachine.objects.all().order_by('-is_active', 'name')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        machines = machines.filter(
            models.Q(name__icontains=search_query) |
            models.Q(code__icontains=search_query) |
            models.Q(machine_id__icontains=search_query) |
            models.Q(phone_number__icontains=search_query)
        )
    
    context = {
        'title': 'ماكينات الفوري',
        'machines': machines,
        'search_query': search_query,
    }
    return render(request, 'accounting/fawry_machines_list.html', context)


@login_required
def fawry_machine_create(request):
    """إنشاء ماكينة فوري جديدة"""
    from .models import FawryMachine, Account
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # محاولة استيراد الـ Showrooms
    try:
        from showrooms.models import Showroom
        showrooms = Showroom.objects.filter(is_active=True)
    except ImportError:
        showrooms = []
    
    if request.method == 'POST':
        try:
            machine = FawryMachine(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                machine_id=request.POST.get('machine_id'),
                phone_number=request.POST.get('phone_number', ''),
                location=request.POST.get('location', ''),
                current_balance=request.POST.get('current_balance') or 0,
                commission_rate=request.POST.get('commission_rate') or 0,
                is_active=request.POST.get('is_active') == 'on',
                notes=request.POST.get('notes', ''),
            )
            
            # الحقول الاختيارية
            if request.POST.get('responsible_person'):
                machine.responsible_person_id = request.POST.get('responsible_person')
            if request.POST.get('linked_account'):
                machine.linked_account_id = request.POST.get('linked_account')
            if request.POST.get('showroom'):
                machine.showroom_id = request.POST.get('showroom')
            
            machine.save()
            messages.success(request, 'تم إنشاء ماكينة الفوري بنجاح')
            return redirect('accounting:fawry_machines_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'title': 'إضافة ماكينة فوري',
        'ledger_accounts': Account.objects.filter(is_active=True).order_by('code'),
        'users': User.objects.filter(is_active=True).order_by('username'),
        'showrooms': showrooms,
    }
    return render(request, 'accounting/fawry_machine_form.html', context)


@login_required
def fawry_machine_edit(request, pk):
    """تعديل ماكينة فوري"""
    from .models import FawryMachine, Account
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    machine = get_object_or_404(FawryMachine, pk=pk)
    
    # محاولة استيراد الـ Showrooms
    try:
        from showrooms.models import Showroom
        showrooms = Showroom.objects.filter(is_active=True)
    except ImportError:
        showrooms = []
    
    if request.method == 'POST':
        try:
            machine.name = request.POST.get('name')
            machine.code = request.POST.get('code')
            machine.machine_id = request.POST.get('machine_id')
            machine.phone_number = request.POST.get('phone_number', '')
            machine.location = request.POST.get('location', '')
            machine.current_balance = request.POST.get('current_balance') or 0
            machine.commission_rate = request.POST.get('commission_rate') or 0
            machine.is_active = request.POST.get('is_active') == 'on'
            machine.notes = request.POST.get('notes', '')
            
            # الحقول الاختيارية
            machine.responsible_person_id = request.POST.get('responsible_person') or None
            machine.linked_account_id = request.POST.get('linked_account') or None
            machine.showroom_id = request.POST.get('showroom') or None
            
            machine.save()
            messages.success(request, 'تم تحديث ماكينة الفوري بنجاح')
            return redirect('accounting:fawry_machines_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'title': 'تعديل ماكينة فوري',
        'machine': machine,
        'ledger_accounts': Account.objects.filter(is_active=True).order_by('code'),
        'users': User.objects.filter(is_active=True).order_by('username'),
        'showrooms': showrooms,
    }
    return render(request, 'accounting/fawry_machine_form.html', context)


@login_required
def fawry_machine_delete(request, pk):
    """حذف ماكينة فوري"""
    from .models import FawryMachine
    
    machine = get_object_or_404(FawryMachine, pk=pk)
    
    if request.method == 'POST':
        machine_name = machine.name
        machine.delete()
        messages.success(request, f'تم حذف ماكينة الفوري "{machine_name}" بنجاح')
        return redirect('accounting:fawry_machines_list')
    
    context = {
        'title': 'حذف ماكينة فوري',
        'machine': machine,
    }
    return render(request, 'accounting/fawry_machine_confirm_delete.html', context)


# ============================================
# إدارة ماكينات الفيزا
# ============================================

@login_required
def visa_machines_list(request):
    """قائمة ماكينات الفيزا"""
    from .models import VisaMachine
    
    machines = VisaMachine.objects.select_related('bank').all().order_by('-is_active', 'name')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        machines = machines.filter(
            models.Q(name__icontains=search_query) |
            models.Q(code__icontains=search_query) |
            models.Q(terminal_id__icontains=search_query) |
            models.Q(merchant_id__icontains=search_query)
        )
    
    context = {
        'title': 'ماكينات الفيزا',
        'machines': machines,
        'search_query': search_query,
    }
    return render(request, 'accounting/visa_machines_list.html', context)


@login_required
def visa_machine_create(request):
    """إنشاء ماكينة فيزا جديدة"""
    from .models import VisaMachine, Account, Bank
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # محاولة استيراد الـ Showrooms
    try:
        from showrooms.models import Showroom
        showrooms = Showroom.objects.filter(is_active=True)
    except ImportError:
        showrooms = []
    
    if request.method == 'POST':
        try:
            machine = VisaMachine(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                terminal_id=request.POST.get('terminal_id'),
                merchant_id=request.POST.get('merchant_id', ''),
                machine_type=request.POST.get('machine_type', 'multi'),
                location=request.POST.get('location', ''),
                current_balance=request.POST.get('current_balance') or 0,
                commission_rate=request.POST.get('commission_rate') or 0,
                is_active=request.POST.get('is_active') == 'on',
                notes=request.POST.get('notes', ''),
            )
            
            # الحقول الاختيارية
            if request.POST.get('bank'):
                machine.bank_id = request.POST.get('bank')
            if request.POST.get('responsible_person'):
                machine.responsible_person_id = request.POST.get('responsible_person')
            if request.POST.get('linked_account'):
                machine.linked_account_id = request.POST.get('linked_account')
            if request.POST.get('showroom'):
                machine.showroom_id = request.POST.get('showroom')
            
            machine.save()
            messages.success(request, 'تم إنشاء ماكينة الفيزا بنجاح')
            return redirect('accounting:visa_machines_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'title': 'إضافة ماكينة فيزا',
        'ledger_accounts': Account.objects.filter(is_active=True).order_by('code'),
        'users': User.objects.filter(is_active=True).order_by('username'),
        'showrooms': showrooms,
        'banks': Bank.objects.filter(is_active=True).order_by('name'),
        'machine_types': VisaMachine.MACHINE_TYPES,
    }
    return render(request, 'accounting/visa_machine_form.html', context)


@login_required
def visa_machine_edit(request, pk):
    """تعديل ماكينة فيزا"""
    from .models import VisaMachine, Account, Bank
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    machine = get_object_or_404(VisaMachine, pk=pk)
    
    # محاولة استيراد الـ Showrooms
    try:
        from showrooms.models import Showroom
        showrooms = Showroom.objects.filter(is_active=True)
    except ImportError:
        showrooms = []
    
    if request.method == 'POST':
        try:
            machine.name = request.POST.get('name')
            machine.code = request.POST.get('code')
            machine.terminal_id = request.POST.get('terminal_id')
            machine.merchant_id = request.POST.get('merchant_id', '')
            machine.machine_type = request.POST.get('machine_type', 'multi')
            machine.location = request.POST.get('location', '')
            machine.current_balance = request.POST.get('current_balance') or 0
            machine.commission_rate = request.POST.get('commission_rate') or 0
            machine.is_active = request.POST.get('is_active') == 'on'
            machine.notes = request.POST.get('notes', '')
            
            # الحقول الاختيارية
            machine.bank_id = request.POST.get('bank') or None
            machine.responsible_person_id = request.POST.get('responsible_person') or None
            machine.linked_account_id = request.POST.get('linked_account') or None
            machine.showroom_id = request.POST.get('showroom') or None
            
            machine.save()
            messages.success(request, 'تم تحديث ماكينة الفيزا بنجاح')
            return redirect('accounting:visa_machines_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'title': 'تعديل ماكينة فيزا',
        'machine': machine,
        'ledger_accounts': Account.objects.filter(is_active=True).order_by('code'),
        'users': User.objects.filter(is_active=True).order_by('username'),
        'showrooms': showrooms,
        'banks': Bank.objects.filter(is_active=True).order_by('name'),
        'machine_types': VisaMachine.MACHINE_TYPES,
    }
    return render(request, 'accounting/visa_machine_form.html', context)


@login_required
def visa_machine_delete(request, pk):
    """حذف ماكينة فيزا"""
    from .models import VisaMachine
    
    machine = get_object_or_404(VisaMachine, pk=pk)
    
    if request.method == 'POST':
        machine_name = machine.name
        machine.delete()
        messages.success(request, f'تم حذف ماكينة الفيزا "{machine_name}" بنجاح')
        return redirect('accounting:visa_machines_list')
    
    context = {
        'title': 'حذف ماكينة فيزا',
        'machine': machine,
    }
    return render(request, 'accounting/visa_machine_confirm_delete.html', context)


# ============================================
# التقارير الجديدة - حسب حساب الأستاذ والتحليلات
# ============================================

@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def ledger_account_report(request):
    """تقرير حسب حساب الأستاذ"""
    from .models import AccountEntry, Account
    from django.db.models import Sum, Q
    from datetime import datetime
    
    # الحصول على المعاملات
    ledger_account_id = request.GET.get('ledger_account')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    entry_type = request.GET.get('entry_type', '')
    
    # بناء الاستعلام
    queryset = AccountEntry.objects.select_related(
        'ledger_account', 'financial_analysis_1', 'financial_analysis_2',
        'cost_center', 'created_by', 'treasury', 'bank', 'electronic_account',
        'fawry_machine', 'visa_machine'
    ).order_by('-date', '-created_at')
    
    if ledger_account_id:
        queryset = queryset.filter(ledger_account_id=ledger_account_id)
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    if entry_type:
        queryset = queryset.filter(entry_type=entry_type)
    
    # حساب الإحصائيات
    stats = queryset.aggregate(
        total_revenue=Sum('amount', filter=Q(entry_type='revenue')),
        total_expense=Sum('amount', filter=Q(entry_type='expense')),
        count_revenue=models.Count('id', filter=Q(entry_type='revenue')),
        count_expense=models.Count('id', filter=Q(entry_type='expense'))
    )
    
    context = {
        'title': 'تقرير حسب حساب الأستاذ',
        'entries': queryset[:500],
        'accounts': Account.objects.filter(is_active=True, can_post=True).order_by('code'),
        'stats': stats,
        'filters': {
            'ledger_account_id': ledger_account_id,
            'date_from': date_from,
            'date_to': date_to,
            'entry_type': entry_type,
        }
    }
    return render(request, 'accounting/reports/ledger_account_report.html', context)


@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def financial_analysis_1_report(request):
    """تقرير حسب التحليل المالي 1"""
    from .models import AccountEntry, FinancialAnalysis1
    from django.db.models import Sum, Q
    
    # الحصول على المعاملات
    analysis_1_id = request.GET.get('analysis_1')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    entry_type = request.GET.get('entry_type', '')
    
    # بناء الاستعلام
    queryset = AccountEntry.objects.select_related(
        'ledger_account', 'financial_analysis_1', 'financial_analysis_2',
        'cost_center', 'created_by', 'treasury', 'bank', 'electronic_account',
        'fawry_machine', 'visa_machine'
    ).order_by('-date', '-created_at')
    
    if analysis_1_id:
        queryset = queryset.filter(financial_analysis_1_id=analysis_1_id)
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    if entry_type:
        queryset = queryset.filter(entry_type=entry_type)
    
    # حساب الإحصائيات
    stats = queryset.aggregate(
        total_revenue=Sum('amount', filter=Q(entry_type='revenue')),
        total_expense=Sum('amount', filter=Q(entry_type='expense')),
        count_revenue=models.Count('id', filter=Q(entry_type='revenue')),
        count_expense=models.Count('id', filter=Q(entry_type='expense'))
    )
    
    context = {
        'title': 'تقرير التحليل المالي 1',
        'entries': queryset[:500],
        'analysis_list': FinancialAnalysis1.objects.filter(is_active=True).order_by('code'),
        'stats': stats,
        'filters': {
            'analysis_1_id': analysis_1_id,
            'date_from': date_from,
            'date_to': date_to,
            'entry_type': entry_type,
        }
    }
    return render(request, 'accounting/reports/financial_analysis_1_report.html', context)


@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def financial_analysis_2_report(request):
    """تقرير حسب التحليل المالي 2"""
    from .models import AccountEntry, FinancialAnalysis2
    from django.db.models import Sum, Q
    
    # الحصول على المعاملات
    analysis_2_id = request.GET.get('analysis_2')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    entry_type = request.GET.get('entry_type', '')
    
    # بناء الاستعلام
    queryset = AccountEntry.objects.select_related(
        'ledger_account', 'financial_analysis_1', 'financial_analysis_2',
        'cost_center', 'created_by', 'treasury', 'bank', 'electronic_account',
        'fawry_machine', 'visa_machine'
    ).order_by('-date', '-created_at')
    
    if analysis_2_id:
        queryset = queryset.filter(financial_analysis_2_id=analysis_2_id)
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    if entry_type:
        queryset = queryset.filter(entry_type=entry_type)
    
    # حساب الإحصائيات
    stats = queryset.aggregate(
        total_revenue=Sum('amount', filter=Q(entry_type='revenue')),
        total_expense=Sum('amount', filter=Q(entry_type='expense')),
        count_revenue=models.Count('id', filter=Q(entry_type='revenue')),
        count_expense=models.Count('id', filter=Q(entry_type='expense'))
    )
    
    context = {
        'title': 'تقرير التحليل المالي 2',
        'entries': queryset[:500],
        'analysis_list': FinancialAnalysis2.objects.filter(is_active=True).order_by('code'),
        'stats': stats,
        'filters': {
            'analysis_2_id': analysis_2_id,
            'date_from': date_from,
            'date_to': date_to,
            'entry_type': entry_type,
        }
    }
    return render(request, 'accounting/reports/financial_analysis_2_report.html', context)


@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def cost_center_report(request):
    """تقرير حسب مركز التكلفة"""
    from .models import AccountEntry, CostCenter
    from django.db.models import Sum, Q
    
    # الحصول على المعاملات
    cost_center_id = request.GET.get('cost_center')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    entry_type = request.GET.get('entry_type', '')
    
    # بناء الاستعلام
    queryset = AccountEntry.objects.select_related(
        'ledger_account', 'financial_analysis_1', 'financial_analysis_2',
        'cost_center', 'created_by', 'treasury', 'bank', 'electronic_account',
        'fawry_machine', 'visa_machine'
    ).order_by('-date', '-created_at')
    
    if cost_center_id:
        queryset = queryset.filter(cost_center_id=cost_center_id)
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    if entry_type:
        queryset = queryset.filter(entry_type=entry_type)
    
    # حساب الإحصائيات
    stats = queryset.aggregate(
        total_revenue=Sum('amount', filter=Q(entry_type='revenue')),
        total_expense=Sum('amount', filter=Q(entry_type='expense')),
        count_revenue=models.Count('id', filter=Q(entry_type='revenue')),
        count_expense=models.Count('id', filter=Q(entry_type='expense'))
    )
    
    context = {
        'title': 'تقرير مركز التكلفة',
        'entries': queryset[:500],
        'cost_centers': CostCenter.objects.filter(is_active=True).order_by('code'),
        'stats': stats,
        'filters': {
            'cost_center_id': cost_center_id,
            'date_from': date_from,
            'date_to': date_to,
            'entry_type': entry_type,
        }
    }
    return render(request, 'accounting/reports/cost_center_report.html', context)


@login_required
@permission_required('accounting.view_accountentry', raise_exception=True)
def owner_report(request):
    """تقرير حسب صاحب العملية"""
    from .models import AccountEntry
    from django.db.models import Sum, Q
    from django.contrib.contenttypes.models import ContentType
    
    # الحصول على المعاملات
    owner_type = request.GET.get('owner_type')
    owner_id = request.GET.get('owner_id')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    entry_type = request.GET.get('entry_type', '')
    
    # بناء الاستعلام
    queryset = AccountEntry.objects.select_related(
        'ledger_account', 'financial_analysis_1', 'financial_analysis_2',
        'cost_center', 'created_by', 'treasury', 'bank', 'electronic_account',
        'fawry_machine', 'visa_machine', 'owner_content_type'
    ).order_by('-date', '-created_at')
    
    if owner_type and owner_id:
        model_map = {
            'supplier': ('partners', 'Supplier'),
            'customer': ('crm', 'Customer'),
            'driver': ('fleet', 'Driver'),
            'employee': ('hr', 'Employee'),
        }
        
        if owner_type in model_map:
            app_label, model_name = model_map[owner_type]
            try:
                content_type = ContentType.objects.get(
                    app_label=app_label,
                    model=model_name.lower()
                )
                queryset = queryset.filter(
                    owner_content_type=content_type,
                    owner_object_id=owner_id
                )
            except ContentType.DoesNotExist:
                pass
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    if entry_type:
        queryset = queryset.filter(entry_type=entry_type)
    
    # حساب الإحصائيات
    stats = queryset.aggregate(
        total_revenue=Sum('amount', filter=Q(entry_type='revenue')),
        total_expense=Sum('amount', filter=Q(entry_type='expense')),
        count_revenue=models.Count('id', filter=Q(entry_type='revenue')),
        count_expense=models.Count('id', filter=Q(entry_type='expense'))
    )
    
    # جلب بيانات أصحاب العمليات
    from partners.models import Supplier
    from crm.models import Customer
    from fleet.models import Driver
    from hr.models import Employee
    
    context = {
        'title': 'تقرير صاحب العملية',
        'entries': queryset[:500],
        'suppliers': Supplier.objects.all().order_by('name')[:100],
        'customers': Customer.objects.all().order_by('company_name')[:100],
        'drivers': Driver.objects.filter(active=True).order_by('name')[:100],
        'employees': Employee.objects.filter(status='active').order_by('first_name')[:100],
        'stats': stats,
        'filters': {
            'owner_type': owner_type,
            'owner_id': owner_id,
            'date_from': date_from,
            'date_to': date_to,
            'entry_type': entry_type,
        }
    }
    return render(request, 'accounting/reports/owner_report.html', context)


# ============================================
# التحويلات بين الحسابات
# ============================================

@login_required
def transfers_list(request):
    """قائمة التحويلات"""
    from .models import AccountTransfer
    
    transfers = AccountTransfer.objects.select_related(
        'from_treasury', 'from_bank', 'from_electronic', 'from_fawry', 'from_visa',
        'to_treasury', 'to_bank', 'to_electronic', 'to_fawry', 'to_visa',
        'created_by'
    ).order_by('-date', '-created_at')
    
    # الفلترة
    search = request.GET.get('search', '')
    if search:
        transfers = transfers.filter(
            models.Q(transfer_number__icontains=search) |
            models.Q(reference_number__icontains=search) |
            models.Q(description__icontains=search)
        )
    
    date_from = request.GET.get('date_from')
    if date_from:
        transfers = transfers.filter(date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        transfers = transfers.filter(date__lte=date_to)
    
    from_type = request.GET.get('from_type', '')
    if from_type:
        transfers = transfers.filter(from_type=from_type)
    
    to_type = request.GET.get('to_type', '')
    if to_type:
        transfers = transfers.filter(to_type=to_type)
    
    status = request.GET.get('status', '')
    if status:
        transfers = transfers.filter(status=status)
    
    context = {
        'title': 'التحويلات بين الحسابات',
        'transfers': transfers[:200],
        'search': search,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'from_type': from_type,
            'to_type': to_type,
            'status': status,
        },
        'account_types': AccountTransfer.ACCOUNT_TYPES,
        'status_choices': AccountTransfer.STATUS_CHOICES,
    }
    return render(request, 'accounting/transfers_list.html', context)


@login_required
def transfer_create(request):
    """إنشاء تحويل جديد"""
    from .models import AccountTransfer, Treasury, Bank, ElectronicAccount, FawryMachine, VisaMachine
    from decimal import Decimal
    
    if request.method == 'POST':
        try:
            transfer = AccountTransfer(
                date=request.POST.get('date'),
                amount=Decimal(request.POST.get('amount', '0')),
                fees=Decimal(request.POST.get('fees', '0') or '0'),
                from_type=request.POST.get('from_type'),
                to_type=request.POST.get('to_type'),
                description=request.POST.get('description', ''),
                reference_number=request.POST.get('reference_number', ''),
                status=request.POST.get('status', 'completed'),
                created_by=request.user,
            )
            
            # تحديد حساب المصدر
            from_type = request.POST.get('from_type')
            if from_type == 'treasury':
                transfer.from_treasury_id = request.POST.get('from_treasury')
            elif from_type == 'bank':
                transfer.from_bank_id = request.POST.get('from_bank')
            elif from_type == 'electronic':
                transfer.from_electronic_id = request.POST.get('from_electronic')
            elif from_type == 'fawry':
                transfer.from_fawry_id = request.POST.get('from_fawry')
            elif from_type == 'visa':
                transfer.from_visa_id = request.POST.get('from_visa')
            
            # تحديد حساب الوجهة
            to_type = request.POST.get('to_type')
            if to_type == 'treasury':
                transfer.to_treasury_id = request.POST.get('to_treasury')
            elif to_type == 'bank':
                transfer.to_bank_id = request.POST.get('to_bank')
            elif to_type == 'electronic':
                transfer.to_electronic_id = request.POST.get('to_electronic')
            elif to_type == 'fawry':
                transfer.to_fawry_id = request.POST.get('to_fawry')
            elif to_type == 'visa':
                transfer.to_visa_id = request.POST.get('to_visa')
            
            transfer.full_clean()
            transfer.save()
            
            # تحديث الأرصدة (اختياري - يمكن تفعيله لاحقاً)
            # update_balances_on_transfer(transfer)
            
            messages.success(request, f'تم إنشاء التحويل رقم {transfer.transfer_number} بنجاح')
            return redirect('accounting:transfers_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'title': 'تحويل جديد',
        'treasuries': Treasury.objects.filter(is_active=True).order_by('name'),
        'banks': Bank.objects.filter(is_active=True).order_by('name'),
        'electronic_accounts': ElectronicAccount.objects.filter(is_active=True).order_by('name'),
        'fawry_machines': FawryMachine.objects.filter(is_active=True).order_by('name'),
        'visa_machines': VisaMachine.objects.select_related('bank').filter(is_active=True).order_by('name'),
        'account_types': AccountTransfer.ACCOUNT_TYPES,
        'status_choices': AccountTransfer.STATUS_CHOICES,
    }
    return render(request, 'accounting/transfer_form.html', context)


@login_required
def transfer_detail(request, pk):
    """عرض تفاصيل التحويل"""
    from .models import AccountTransfer
    
    transfer = get_object_or_404(AccountTransfer.objects.select_related(
        'from_treasury', 'from_bank', 'from_electronic', 'from_fawry', 'from_visa',
        'to_treasury', 'to_bank', 'to_electronic', 'to_fawry', 'to_visa',
        'created_by'
    ), pk=pk)
    
    context = {
        'title': f'تحويل {transfer.transfer_number}',
        'transfer': transfer,
    }
    return render(request, 'accounting/transfer_detail.html', context)


@login_required
def transfer_cancel(request, pk):
    """إلغاء التحويل"""
    from .models import AccountTransfer
    
    transfer = get_object_or_404(AccountTransfer, pk=pk)
    
    if request.method == 'POST':
        if transfer.status == 'completed':
            transfer.status = 'cancelled'
            transfer.save()
            messages.success(request, f'تم إلغاء التحويل رقم {transfer.transfer_number}')
        else:
            messages.error(request, 'لا يمكن إلغاء هذا التحويل')
        return redirect('accounting:transfers_list')
    
    context = {
        'title': 'إلغاء تحويل',
        'transfer': transfer,
    }
    return render(request, 'accounting/transfer_cancel.html', context)


# ==================== إعدادات القيود التلقائية ====================

@login_required
@permission_required('accounting.change_accountingsettings', raise_exception=True)
def settings_auto_journal(request):
    """إعدادات القيود المحاسبية التلقائية"""
    from .models import AccountingSettings, Account
    from django.contrib import messages
    
    settings = AccountingSettings.get()
    
    if request.method == 'POST':
        try:
            # تحديث الإعدادات
            settings.auto_create_journal_entries = request.POST.get('auto_create_journal_entries') == 'on'
            
            # تحديث الحسابات الافتراضية
            misc_revenue_id = request.POST.get('misc_revenue_account')
            if misc_revenue_id:
                settings.misc_revenue_account_id = int(misc_revenue_id)
            else:
                settings.misc_revenue_account = None
            
            misc_expense_id = request.POST.get('misc_expense_account')
            if misc_expense_id:
                settings.misc_expense_account_id = int(misc_expense_id)
            else:
                settings.misc_expense_account = None
            
            treasury_id = request.POST.get('default_treasury_account')
            if treasury_id:
                settings.default_treasury_account_id = int(treasury_id)
            else:
                settings.default_treasury_account = None
            
            bank_id = request.POST.get('default_bank_account')
            if bank_id:
                settings.default_bank_account_id = int(bank_id)
            else:
                settings.default_bank_account = None
            
            electronic_id = request.POST.get('default_electronic_account')
            if electronic_id:
                settings.default_electronic_account_id = int(electronic_id)
            else:
                settings.default_electronic_account = None
            
            settings.save()
            messages.success(request, 'تم حفظ إعدادات القيود التلقائية بنجاح')
            return redirect('accounting:settings')
        except Exception as e:
            messages.error(request, f'حدث خطأ في حفظ الإعدادات: {str(e)}')
    
    # جلب الحسابات للقوائم المنسدلة
    revenue_accounts = Account.objects.filter(account_type='revenue', is_active=True).order_by('code')
    expense_accounts = Account.objects.filter(account_type='expense', is_active=True).order_by('code')
    asset_accounts = Account.objects.filter(account_type='asset', is_active=True).order_by('code')
    
    context = {
        'title': 'إعدادات القيود التلقائية',
        'settings': settings,
        'revenue_accounts': revenue_accounts,
        'expense_accounts': expense_accounts,
        'asset_accounts': asset_accounts,
    }
    return render(request, 'accounting/settings_auto_journal.html', context)


@login_required
@permission_required('accounting.add_journalentry', raise_exception=True)
def create_entry_journal(request, pk):
    """إنشاء قيد محاسبي يدوي لسجل إيراد/مصروف موجود"""
    from .models import AccountEntry
    from core.integration_services import AccountingIntegrationService
    from django.contrib import messages
    
    entry = get_object_or_404(AccountEntry, pk=pk)
    
    # التحقق من عدم وجود قيد مسبقاً
    if entry.journal_entry:
        messages.warning(request, f'يوجد قيد محاسبي مرتبط بالفعل: {entry.journal_entry.number}')
        return redirect('accounting:journal_entry_detail', pk=entry.journal_entry.pk)
    
    if request.method == 'POST':
        try:
            journal_entry = AccountingIntegrationService.create_revenue_expense_journal_entry(
                entry, 
                request.user
            )
            if journal_entry:
                messages.success(
                    request,
                    f'تم إنشاء القيد المحاسبي {journal_entry.number} بنجاح'
                )
                return redirect('accounting:journal_entry_detail', pk=journal_entry.pk)
            else:
                messages.error(request, 'لم يتم إنشاء القيد المحاسبي. تأكد من إعدادات الحسابات الافتراضية.')
                return redirect('accounting:account_entries_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ في إنشاء القيد: {str(e)}')
            return redirect('accounting:account_entries_list')
    
    context = {
        'title': 'إنشاء قيد محاسبي يدوي',
        'entry': entry,
    }
    return render(request, 'accounting/create_entry_journal.html', context)
@login_required
def daily_expenses_report(request):
    """تقرير المصاريف اليومية."""
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    today = timezone.now().date()
    date_str = request.GET.get('date')
    
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else today
    except ValueError:
        report_date = today
        
    # Get expense accounts (typically type 'expense')
    expense_accounts = Account.objects.filter(account_type='expense')
    
    # Get journal entry items for these accounts on the specific date
    # Debits increase expenses
    expenses = JournalEntryItem.objects.filter(
        account__in=expense_accounts,
        journal_entry__date=report_date,
        journal_entry__is_posted=True
    ).select_related('account', 'journal_entry', 'cost_center')
    
    total_amount = expenses.aggregate(sum=Sum('amount'))['sum'] or 0
    
    # Group by account
    by_account = expenses.values('account__name', 'account__code').annotate(total=Sum('amount')).order_by('-total')
    
    # Group by cost center
    by_cost_center = expenses.values('cost_center__name').annotate(total=Sum('amount')).order_by('-total')
    
    context = {
        'title': f'تقرير المصاريف اليومية - {report_date}',
        'report_date': report_date,
        'expenses': expenses,
        'total_amount': total_amount,
        'by_account': by_account,
        'by_cost_center': by_cost_center,
    }
    return render(request, 'accounting/daily_expenses_report.html', context)
