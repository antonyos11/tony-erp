from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest
from datetime import date, datetime, timedelta
from django.db.models import Sum, F, Q, Count, DecimalField, ExpressionWrapper, IntegerField, Case, When, Value
from django.db.models.functions import Coalesce
from inventory.models import Product, Category
from sales.models import Invoice
from purchases.models import PurchaseBill
from accounting.models import Revenue, Expense
from users.models import UserSession
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from urllib.parse import urlencode
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _t
from django.utils import timezone
from django.db import transaction
import csv, json
from core.models import AuditLog, Currency, Company
from .forms import CurrencyForm, CompanySettingsForm, CurrencyExchangeRateForm
import socket
import base64
from io import BytesIO
from typing import Any
import os
import zipfile
import time

try:
    import qrcode
except ImportError:
    qrcode = None


def home(request: HttpRequest):
    """صفحة ترحيب للمستخدمين غير المسجلين، وتوجيه للوحة التحكم للمسجلين."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'home.html')


def offline_page(request: HttpRequest):
    """صفحة PWA للعمل بدون اتصال بالإنترنت."""
    return render(request, 'offline.html')


@login_required
def debug_sidebar_links(request):
    """صفحة debug لفحص روابط القائمة الجانبية"""
    return render(request, 'debug_sidebar_links.html')


@login_required
def coming_soon(request: HttpRequest, feature: str = None):
    """صفحة 'قريباً' للميزات التي لم تُبنى بعد."""
    import random
    
    # قاموس الميزات مع معلومات تفصيلية
    feature_data = {
        'late-tasks': {
            'name': _('المهام المتأخرة'),
            'icon': 'bi-clock-history',
            'color': '#ef4444',
            'progress': 45,
            'description': _('تتبع المهام المتأخرة وإدارة الأولويات بشكل فعال'),
            'eta': _('يناير 2026'),
        },
        'payroll-items': {
            'name': _('مفردات المرتب'),
            'icon': 'bi-cash-stack',
            'color': '#10b981',
            'progress': 100,
            'description': _('إدارة شاملة لمفردات الرواتب والبدلات والخصومات'),
            'eta': _('متاح الآن'),
            'url': 'hr:payroll_dashboard',
        },
        'cash-forecast': {
            'name': _('التحقق النقدي المتوقع'),
            'icon': 'bi-graph-up-arrow',
            'color': '#3b82f6',
            'progress': 60,
            'description': _('توقعات التدفق النقدي وتحليل السيولة'),
            'eta': _('فبراير 2026'),
        },
        'models': {
            'name': _('الموديلات'),
            'icon': 'bi-box-seam',
            'color': '#8b5cf6',
            'progress': 35,
            'description': _('إدارة موديلات المنتجات والتصنيفات'),
            'eta': _('مارس 2026'),
        },
        'account-statement': {
            'name': _('كشف حساب عملاء/موردين'),
            'icon': 'bi-file-earmark-text',
            'color': '#06b6d4',
            'progress': 90,
            'description': _('كشوف حسابات تفصيلية للعملاء والموردين'),
            'eta': _('خلال أيام'),
        },
        'customer-debts': {
            'name': _('مديونيات العملاء'),
            'icon': 'bi-person-lines-fill',
            'color': '#f59e0b',
            'progress': 70,
            'description': _('تقارير شاملة عن مديونيات العملاء وأعمارها'),
            'eta': _('يناير 2026'),
        },
        'supplier-debts': {
            'name': _('مديونيات الموردين'),
            'icon': 'bi-truck',
            'color': '#ec4899',
            'progress': 70,
            'description': _('تقارير تفصيلية عن مستحقات الموردين'),
            'eta': _('يناير 2026'),
        },
        'sales-representatives': {
            'name': _('مبيعات المناديب والعملاء'),
            'icon': 'bi-people-fill',
            'color': '#14b8a6',
            'progress': 55,
            'description': _('تحليل أداء المناديب ومبيعات العملاء'),
            'eta': _('فبراير 2026'),
        },
        'top-selling': {
            'name': _('الأصناف الأكثر مبيعاً'),
            'icon': 'bi-trophy-fill',
            'color': '#eab308',
            'progress': 85,
            'description': _('تقارير الأصناف الأكثر مبيعاً مع تحليلات'),
            'eta': _('قريباً جداً'),
        },
        'least-selling': {
            'name': _('الأصناف الأقل مبيعاً'),
            'icon': 'bi-graph-down-arrow',
            'color': '#64748b',
            'progress': 85,
            'description': _('تحليل الأصناف الراكدة وقليلة الحركة'),
            'eta': _('قريباً جداً'),
        },
        'daily-expenses': {
            'name': _('تقرير المصاريف اليومية'),
            'icon': 'bi-calendar-day',
            'color': '#f97316',
            'progress': 75,
            'description': _('متابعة المصاريف اليومية بالتفصيل'),
            'eta': _('يناير 2026'),
        },
        'comprehensive': {
            'name': _('تقرير شامل'),
            'icon': 'bi-file-earmark-bar-graph',
            'color': '#6366f1',
            'progress': 40,
            'description': _('تقرير شامل يجمع كل البيانات المهمة'),
            'eta': _('مارس 2026'),
        },
        'price-comparison': {
            'name': _('مقارنة الأسعار'),
            'icon': 'bi-currency-exchange',
            'color': '#22c55e',
            'progress': 50,
            'description': _('مقارنة أسعار المنتجات عبر الفترات'),
            'eta': _('فبراير 2026'),
        },
        'monthly-comparison': {
            'name': _('مقارنة الشهور'),
            'icon': 'bi-calendar3',
            'color': '#a855f7',
            'progress': 65,
            'description': _('مقارنة الأداء بين الشهور المختلفة'),
            'eta': _('يناير 2026'),
        },
        'equipment-usage': {
            'name': _('استخدام المعدات'),
            'icon': 'bi-tools',
            'color': '#0891b2',
            'progress': 30,
            'description': _('تتبع استخدام المعدات والأدوات'),
            'eta': _('أبريل 2026'),
        },
        'equipment-maintenance': {
            'name': _('صيانة المعدات'),
            'icon': 'bi-wrench-adjustable',
            'color': '#dc2626',
            'progress': 25,
            'description': _('جدولة ومتابعة صيانة المعدات'),
            'eta': _('أبريل 2026'),
        },
        'material-consumption': {
            'name': _('استهلاك المواد'),
            'icon': 'bi-box2-fill',
            'color': '#84cc16',
            'progress': 55,
            'description': _('تحليل استهلاك المواد الخام'),
            'eta': _('فبراير 2026'),
        },
    }
    
    # البيانات الافتراضية
    default_data = {
        'name': _('هذه الميزة'),
        'icon': 'bi-stars',
        'color': '#f59e0b',
        'progress': random.randint(40, 85),
        'description': _('ميزة جديدة قيد التطوير لتحسين تجربتك'),
        'eta': _('قريباً'),
    }
    
    # الحصول على بيانات الميزة
    feature_info = feature_data.get(feature, default_data) if feature else default_data
    
    # إذا كانت الميزة مكتملة 100% وبها رابط، توجيه المستخدم مباشرة
    if feature_info.get('progress', 0) >= 100 and feature_info.get('url'):
        from django.urls import reverse
        try:
            return redirect(reverse(feature_info['url']))
        except Exception:
            pass
    
    # حساب مرحلة التطوير
    progress = feature_info['progress']
    if progress >= 90:
        stage = 'testing'
        stage_name = _('الاختبار النهائي')
    elif progress >= 70:
        stage = 'development'
        stage_name = _('التطوير المتقدم')
    elif progress >= 50:
        stage = 'development'
        stage_name = _('التطوير')
    elif progress >= 30:
        stage = 'design'
        stage_name = _('التصميم')
    else:
        stage = 'planning'
        stage_name = _('التخطيط')
    
    # الميزات المشابهة (قريبة من الاكتمال)
    similar_features = [
        {'name': v['name'], 'progress': v['progress'], 'icon': v['icon'], 'color': v['color']}
        for k, v in feature_data.items()
        if v['progress'] >= 70 and k != feature
    ][:3]
    
    context = {
        'feature': feature,
        'feature_title': feature_info['name'],
        'feature_icon': feature_info['icon'],
        'feature_color': feature_info['color'],
        'feature_progress': feature_info['progress'],
        'feature_description': feature_info['description'],
        'feature_eta': feature_info['eta'],
        'stage': stage,
        'stage_name': stage_name,
        'similar_features': similar_features,
    }
    return render(request, 'core/coming_soon.html', context)


def _detect_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for ai in socket.getaddrinfo(hostname, None):
            addr = str(ai[4][0])
            if ':' in addr:
                continue
            if addr.startswith('127.'):
                continue
            if addr not in ips:
                ips.append(addr)
    except Exception:
        pass
    # طريقة بديلة
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return ips or ['127.0.0.1']

@login_required
def server_qr(request: HttpRequest):
    """صفحة مشاركة الرابط عبر الشبكة + QR.
    - تعرض HTML جاهز مع صورة QR إن توفرت مكتبة qrcode.
    - تُرجع JSON عند طلب format=json أو Accept: application/json.
    """
    port_str = request.GET.get('port') or '8000'
    try:
        port = int(port_str)
    except Exception:
        port = 8000

    ips = _detect_ips()
    preferred_ip = ips[0] if ips else '127.0.0.1'
    selected_ip = request.GET.get('ip') or preferred_ip
    if selected_ip not in ips:
        selected_ip = preferred_ip
    server_url = f"http://{selected_ip}:{port}/"
    current_url = f"http://{request.get_host().split(':')[0]}:{port}/"

    qr_data_url = None
    qr_b64_only = None
    qrcode_available = qrcode is not None
    if qrcode_available:
        try:
            # Re-import inside guarded block to satisfy type checkers
            import qrcode as _qrcode  # type: ignore
            img = _qrcode.make(server_url)
            buf = BytesIO()
            img.save(buf, 'PNG')
            qr_b64_only = base64.b64encode(buf.getvalue()).decode('ascii')
            qr_data_url = f"data:image/png;base64,{qr_b64_only}"
        except Exception:
            qr_data_url = None

    # JSON mode
    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        payload = {'url': server_url, 'current': current_url, 'ips': ips, 'selected_ip': selected_ip, 'port': port}
        if qr_b64_only:
            payload['qr_b64'] = qr_b64_only
            payload['qr_base64'] = qr_data_url
        if not qrcode_available:
            payload['message'] = 'qrcode lib not installed'
        return JsonResponse(payload)

    context = {
        'url': server_url,
        'current_url': current_url,
        'ips': ips,
        'qr_b64': qr_b64_only,
        'qr_base64': qr_data_url,
        'qrcode_available': qrcode_available,
        'port': port,
        'selected_ip': selected_ip,
    }
    return render(request, 'core/server_qr.html', context)


@login_required
def network_diagnose(request: HttpRequest):
    """اختبار الشبكة على المنافذ والعناوين المحلية"""
    port_str = request.GET.get('port') or '8000'
    try:
        port = int(port_str)
    except Exception:
        port = 8000

    ips = _detect_ips()
    tests: list[dict[str, Any]] = []

    # اختبر كل IP محلي
    for ip in ips:
        result: dict[str, Any] = {'ip': ip, 'port': port, 'ok': False, 'connect_ms': None, 'error': None}
        start = None
        s = None
        try:
            start = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.7)
            s.connect((ip, port))
            result['ok'] = True
        except Exception as e:
            result['error'] = str(e)[:120]
        finally:
            if start is not None:
                result['connect_ms'] = int((time.time() - start) * 1000)
            try:
                if s:
                    s.close()
            except Exception:
                pass
        tests.append(result)

    # جرّب 127.0.0.1 أيضاً
    loopback_result: dict[str, Any] = {'ip': '127.0.0.1', 'port': port, 'ok': False, 'connect_ms': None, 'error': None}
    start = None
    s = None
    try:
        start = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(('127.0.0.1', port))
        loopback_result['ok'] = True
    except Exception as e:
        loopback_result['error'] = str(e)[:120]
    finally:
        if start is not None:
            loopback_result['connect_ms'] = int((time.time() - start) * 1000)
        try:
            if s:
                s.close()
        except Exception:
            pass
    tests.append(loopback_result)

    hints = []
    if not any(t.get('ok') for t in tests):
        hints.append('الخادم لا يستمع على هذا المنفذ أو الجدار الناري يمنع الاتصال.')
    elif not any(t.get('ok') and not str(t.get('ip')).startswith('127.') for t in tests):
        hints.append('الاتصال يعمل محلياً فقط. تأكد من وضع الشبكة (Private) وقاعدة الجدار الناري.')
    hints.append(f'شغّل الخادم على كل الواجهات: python manage.py runserver 0.0.0.0:{port}')
    hints.append(f'قاعدة جدار ناري (Windows): netsh advfirewall firewall add rule name="DjangoDev{port}" dir=in action=allow protocol=TCP localport={port}')

    context = {'tests': tests, 'port': port, 'hints': hints, 'ips': ips}
    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse(context)
    return render(request, 'core/network_diagnose.html', context)


@login_required
def dashboard(request: HttpRequest):
    """لوحة التحكم المخصصة للمستخدمين المصرح لهم"""
    try:
        from hr.models import AttendanceRecord
        employee = getattr(request.user, 'employee_profile', None)
        if employee and not getattr(employee, 'attendance_exempt', False):
            today = date.today()
            checked_in = AttendanceRecord.objects.filter(
                employee=employee, date=today, record_type='check_in'
            ).exists()
            checked_out = AttendanceRecord.objects.filter(
                employee=employee, date=today, record_type='check_out'
            ).exists()

            if not checked_in:
                messages.warning(request, 'يجب تسجيل الحضور أولاً للدخول إلى النظام')
                return redirect('hr:employee_welcome')

            if checked_out:
                messages.warning(request, 'تم تسجيل انصرافك اليوم. لا يمكنك الدخول للنظام.')
                return redirect('hr:employee_welcome')
    except Exception:
        pass

    # التحقق من طلبات AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_dashboard_data(request)
    
    # محاولة الحصول على البيانات من Cache
    from django.core.cache import cache
    from showrooms.mixins import get_active_showroom_id, is_all_showrooms_mode, scope_queryset_to_active_showroom
    
    active_showroom_id = get_active_showroom_id(request)
    show_all = is_all_showrooms_mode(request)
    range_param = (request.GET.get('range') or '30').strip()
    
    # بناء مفتاح cache فريد للمستخدم والفرع والفترة
    cache_key = f"dashboard:v2:{request.user.id}:{active_showroom_id or 'all'}:{range_param}"
    
    # محاولة الحصول من cache (300 ثانية = 5 دقائق)
    cached_context = cache.get(cache_key)
    if cached_context and not request.GET.get('refresh'):
        return render(request, 'core/dashboard_biznify.html', cached_context)
    
    # تحديد الفرع الحالي أو وضع "جميع الفروع"
    active_showroom_id = get_active_showroom_id(request)
    show_all = is_all_showrooms_mode(request)
    
    # Date range handling (7/30/90/custom)
    today = date.today()
    range_param = (request.GET.get('range') or '30').strip()
    try:
        period_end = today
        if range_param.lower() == '7':
            days = 7
        elif range_param.lower() == '90':
            days = 90
        elif range_param.lower() == 'custom':
            df = request.GET.get('from') or request.GET.get('date_from')
            dt = request.GET.get('to') or request.GET.get('date_to')
            d_from = date.fromisoformat(df) if df else (today - timedelta(days=29))
            d_to = date.fromisoformat(dt) if dt else today
            if d_from > d_to:
                d_from, d_to = d_to, d_from
            days = max(1, (d_to - d_from).days + 1)
            period_end = d_to
        else:
            days = 30
        # allow explicit 'to' even for non-custom (optional)
        to_override = request.GET.get('to') or request.GET.get('date_to')
        if to_override:
            try:
                period_end = date.fromisoformat(to_override)
            except Exception:
                pass
    except Exception:
        days = 30
        period_end = today

    # Current period start (inclusive)
    period_start = period_end - timedelta(days=days - 1)
    last_30_days = period_start  # legacy name used below
    
    # Real KPIs
    # Use item-level aggregations to avoid fragile reverse relation annotation patterns
    from sales.models import InvoiceItem
    from purchases.models import PurchaseItem
    sales_expr = ExpressionWrapper(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2))
    purchase_expr = ExpressionWrapper(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    
    # فلترة المبيعات حسب الفرع
    invoice_items_qs = InvoiceItem.objects.filter(invoice__date__gte=last_30_days, invoice__date__lte=period_end)
    if active_showroom_id and not show_all:
        invoice_items_qs = invoice_items_qs.filter(invoice__showroom_id=active_showroom_id)
    total_sales = invoice_items_qs.aggregate(total=Sum(sales_expr))['total'] or 0
    
    # فلترة المشتريات حسب الفرع
    purchase_items_qs = PurchaseItem.objects.filter(bill__date__gte=last_30_days, bill__date__lte=period_end)
    if active_showroom_id and not show_all:
        purchase_items_qs = purchase_items_qs.filter(bill__showroom_id=active_showroom_id)
    total_purchases = purchase_items_qs.aggregate(total=Sum(purchase_expr))['total'] or 0
    
    # Estimated profit (sales - purchase costs)
    estimated_profit = total_sales - total_purchases
    
    # Low stock alerts - فلترة حسب الفرع
    stock_qs = Product.objects.annotate(total_qty=Coalesce(Sum('stocks__quantity'), 0))
    if active_showroom_id and not show_all:
        # showroom_link هو reverse OneToOne من Showroom إلى Location
        # نستخدم showroom_link__id للوصول إلى معرف المعرض
        stock_qs = Product.objects.annotate(
            total_qty=Coalesce(Sum('stocks__quantity', filter=Q(stocks__location__showroom_link__id=active_showroom_id)), 0)
        )
    low_stock_count = stock_qs.filter(total_qty__lt=F('min_stock')).count()
    
    # Chart data for last N days (up to 30 for readability)
    chart_labels = []
    sales_data = []
    purchases_data = []
    chart_window = min(days, 30)
    
    # تحسين الأداء: جلب بيانات الرسم البياني في query واحد بدلاً من query لكل يوم
    chart_start = period_end - timedelta(days=chart_window - 1)
    
    # جلب مجموع المبيعات حسب اليوم دفعة واحدة
    from django.db.models.functions import TruncDate
    
    daily_sales_qs = InvoiceItem.objects.filter(
        invoice__date__gte=chart_start,
        invoice__date__lte=period_end
    )
    if active_showroom_id and not show_all:
        daily_sales_qs = daily_sales_qs.filter(invoice__showroom_id=active_showroom_id)
    daily_sales_map = {
        str(item['day']): float(item['total'] or 0)
        for item in daily_sales_qs.annotate(day=TruncDate('invoice__date'))
        .values('day')
        .annotate(total=Sum(sales_expr))
    }
    
    # جلب مجموع المشتريات حسب اليوم دفعة واحدة
    daily_purchases_qs = PurchaseItem.objects.filter(
        bill__date__gte=chart_start,
        bill__date__lte=period_end
    )
    if active_showroom_id and not show_all:
        daily_purchases_qs = daily_purchases_qs.filter(bill__showroom_id=active_showroom_id)
    daily_purchases_map = {
        str(item['day']): float(item['total'] or 0)
        for item in daily_purchases_qs.annotate(day=TruncDate('bill__date'))
        .values('day')
        .annotate(total=Sum(purchase_expr))
    }
    
    # بناء بيانات الرسم البياني من الخرائط
    for i in range(chart_window - 1, -1, -1):
        day = period_end - timedelta(days=i)
        day_str = str(day)
        chart_labels.append(day.strftime('%m-%d'))
        sales_data.append(daily_sales_map.get(day_str, 0.0))
        purchases_data.append(daily_purchases_map.get(day_str, 0.0))
    
    # إحصائيات النظام
    system_stats = {
        'total_users': User.objects.filter(is_active=True).count(),
        'active_sessions': UserSession.objects.filter(is_active=True).count(),
        'modules_count': 8,
    }

    # لوحات مختصرة: آخر الفواتير وتنبيهات المخزون - مع فلترة الفرع
    try:
        recent_invoices_qs = Invoice.objects.select_related('customer', 'showroom').order_by('-date', '-id')
        if active_showroom_id and not show_all:
            recent_invoices_qs = recent_invoices_qs.filter(showroom_id=active_showroom_id)
        recent_invoices = recent_invoices_qs[:5]
    except Exception:
        recent_invoices = []
    try:
        if active_showroom_id and not show_all:
            low_stock_items = (
                Product.objects
                .annotate(total_qty=Coalesce(Sum('stocks__quantity', filter=Q(stocks__location__showroom_link_id=active_showroom_id)), 0))
                .filter(total_qty__lt=F('min_stock'))
                .order_by('total_qty')[:8]
            )
        else:
            low_stock_items = (
                Product.objects
                .annotate(total_qty=Coalesce(Sum('stocks__quantity'), 0))
                .filter(total_qty__lt=F('min_stock'))
                .order_by('total_qty')[:8]
            )
    except Exception:
        low_stock_items = []
    
    # مقارنة مع فترة سابقة بنفس الطول - مع فلترة الفرع
    prev_start = period_start - timedelta(days=days)
    prev_end = period_start - timedelta(days=1)
    def _sum_sales(d_from, d_to):
        qs = InvoiceItem.objects.filter(invoice__date__gte=d_from, invoice__date__lte=d_to)
        if active_showroom_id and not show_all:
            qs = qs.filter(invoice__showroom_id=active_showroom_id)
        return qs.aggregate(total=Sum(sales_expr))['total'] or 0
    def _sum_purchases(d_from, d_to):
        qs = PurchaseItem.objects.filter(bill__date__gte=d_from, bill__date__lte=d_to)
        if active_showroom_id and not show_all:
            qs = qs.filter(bill__showroom_id=active_showroom_id)
        return qs.aggregate(total=Sum(purchase_expr))['total'] or 0
    prev_sales = _sum_sales(prev_start, prev_end)
    prev_purchases = _sum_purchases(prev_start, prev_end)
    prev_profit = (prev_sales - prev_purchases)

    def _pct_change(current, prev):
        try:
            c = float(current or 0)
            p = float(prev or 0)
            if p == 0:
                return 100.0 if c > 0 else 0.0
            return ((c - p) / abs(p)) * 100.0
        except Exception:
            return 0.0

    kpi_trends = {
        'sales': _pct_change(total_sales, prev_sales),
        'purchases': _pct_change(total_purchases, prev_purchases),
        'profit': _pct_change((total_sales - total_purchases), prev_profit),
        # low_stock trend not meaningful; set 0
        'low_stock': 0.0,
    }

    # تكوين البطاقات بناءً على الإعداد
    kpi_map = {
        'sales': {"key":"sales", "title": "المبيعات", "value": f"{total_sales:,.2f}", "variant": "primary", "icon": "bi-cart-check", "trend": kpi_trends['sales']},
        'purchases': {"key":"purchases", "title": "المشتريات", "value": f"{total_purchases:,.2f}", "variant": "success", "icon": "bi-bag-plus", "trend": kpi_trends['purchases']},
        'profit': {"key":"profit", "title": "الأرباح التقديرية", "value": f"{estimated_profit:,.2f}", "variant": "warning", "icon": "bi-graph-up-arrow", "trend": kpi_trends['profit']},
        'low_stock': {"key":"low_stock", "title": "تنبيهات المخزون", "value": low_stock_count, "variant": "danger", "icon": "bi-exclamation-triangle", "trend": 0.0},
    }
    try:
        from core.models import AppSettings
        app_settings = AppSettings.get()
        visible_keys = [k.strip() for k in (app_settings.kpi_visible_keys or '').split(',') if k.strip()]
        if not visible_keys:
            visible_keys = getattr(settings, 'KPI_VISIBLE_KEYS', ['sales','purchases','profit','low_stock'])
    except Exception:
        visible_keys = getattr(settings, 'KPI_VISIBLE_KEYS', ['sales','purchases','profit','low_stock'])
    cards = [kpi_map[k] for k in visible_keys if k in kpi_map]

    # حالة الفواتير (مدفوعة/جزئية/غير مدفوعة/ملغاة) - مع فلترة الفرع
    invoice_qs = Invoice.objects.filter(date__gte=period_start, date__lte=period_end)
    if active_showroom_id and not show_all:
        invoice_qs = invoice_qs.filter(showroom_id=active_showroom_id)
    total_invoices = invoice_qs.count() or 0
    paid_count = invoice_qs.aggregate(
        c=Sum(Case(When(paid__gte=F('cached_total') - F('discount'), then=Value(1)), default=Value(0), output_field=IntegerField()))
    )['c'] or 0
    partial_count = invoice_qs.aggregate(
        c=Sum(Case(
            When(paid__gt=0, paid__lt=F('cached_total') - F('discount'), then=Value(1)),
            default=Value(0), output_field=IntegerField()))
    )['c'] or 0
    canceled_qs = Invoice.objects.filter(is_deleted=True, date__gte=period_start, date__lte=period_end)
    if active_showroom_id and not show_all:
        canceled_qs = canceled_qs.filter(showroom_id=active_showroom_id)
    canceled_count = canceled_qs.count()
    unpaid_count = max(total_invoices - paid_count - partial_count, 0)
    invoice_breakdown = {
        'labels': ['مدفوعة', 'جزئية', 'غير مدفوعة', 'ملغاة'],
        'values': [int(paid_count), int(partial_count), int(unpaid_count), int(canceled_count)],
        'colors': ['#6f63ff', '#4ac0c6', '#f5a623', '#ff6b81'],
    }

    # بيانات شهرية (آخر 12 شهراً): مبيعات/مشتريات وصافي التدفق - مع فلترة الفرع
    def month_anchor(d: date, months_back: int) -> date:
        base_month = d.month - 1 - months_back
        year = d.year + base_month // 12
        month = (base_month % 12) + 1
        return date(year, month, 1)

    monthly_labels: list[str] = []
    monthly_sales: list[float] = []
    monthly_purchases: list[float] = []
    monthly_net: list[float] = []
    for i in range(11, -1, -1):
        start_m = month_anchor(period_end, i)
        # next month
        end_m = month_anchor(period_end, i - 1) if i > 0 else date(period_end.year, period_end.month, 1) + timedelta(days=32)
        end_m = end_m.replace(day=1) - timedelta(days=1)
        monthly_labels.append(start_m.strftime('%b'))
        m_sales_qs = InvoiceItem.objects.filter(invoice__date__gte=start_m, invoice__date__lte=end_m)
        if active_showroom_id and not show_all:
            m_sales_qs = m_sales_qs.filter(invoice__showroom_id=active_showroom_id)
        m_sales = m_sales_qs.aggregate(total=Sum(sales_expr))['total'] or 0
        m_pur_qs = PurchaseItem.objects.filter(bill__date__gte=start_m, bill__date__lte=end_m)
        if active_showroom_id and not show_all:
            m_pur_qs = m_pur_qs.filter(bill__showroom_id=active_showroom_id)
        m_pur = m_pur_qs.aggregate(total=Sum(purchase_expr))['total'] or 0
        monthly_sales.append(float(m_sales))
        monthly_purchases.append(float(m_pur))
        monthly_net.append(float(m_sales) - float(m_pur))

    # ===== البطاقات الجديدة =====
    # إجمالي المصروفات الشهرية
    current_month_start = date(period_end.year, period_end.month, 1)
    try:
        expenses_qs = Expense.objects.filter(
            date__gte=current_month_start,
            date__lte=period_end
        )
        # ملاحظة: Expense model لا يحتوي على حقل showroom
        monthly_expenses_total = expenses_qs.aggregate(total=Sum('amount'))['total'] or 0
    except Exception:
        monthly_expenses_total = 0
    
    # صافي التحصيلات الشهرية
    try:
        revenues_qs = Revenue.objects.filter(
            date__gte=current_month_start,
            date__lte=period_end
        )
        # ملاحظة: Revenue model لا يحتوي على حقل showroom
        monthly_collections = revenues_qs.aggregate(total=Sum('amount'))['total'] or 0
    except Exception:
        monthly_collections = 0
    
    # المركز المالي الحالي (الأصول - الخصوم)
    try:
        from accounting.models import Account
        # حساب إجمالي الأصول (نوع asset)
        total_assets = Account.objects.filter(
            account_type='asset'
        ).aggregate(total=Sum('balance'))['total'] or 0
        # حساب إجمالي الخصوم (نوع liability)
        total_liabilities = Account.objects.filter(
            account_type='liability'
        ).aggregate(total=Sum('balance'))['total'] or 0
        financial_position = float(total_assets) - float(total_liabilities)
    except Exception:
        financial_position = 0
    
    # أفضل المنتجات مبيعاً
    try:
        top_products_qs = (
            InvoiceItem.objects
            .filter(invoice__date__gte=period_start, invoice__date__lte=period_end)
            .select_related('product')
            .values('product__id', 'product__name')
            .annotate(
                total_qty=Sum('quantity'),
                total_sales=Sum(sales_expr)
            )
            .order_by('-total_sales')[:5]
        )
        top_products = [
            {'name': p['product__name'], 'total_qty': p['total_qty'], 'total_sales': p['total_sales']}
            for p in top_products_qs
        ]
    except Exception:
        top_products = []
    
    # عدد العملاء النشطين
    try:
        from partners.models import Customer
        customer_count = Customer.objects.count()
    except Exception:
        customer_count = 0
    
    # عدد المنتجات
    try:
        product_count = Product.objects.count()
    except Exception:
        product_count = 0
    
    # البطاقات الإضافية
    extra_cards = {
        'monthly_expenses': {
            "key": "monthly_expenses",
            "title": "إجمالي المصروفات الشهرية",
            "value": f"{monthly_expenses_total:,.2f}",
            "variant": "danger",
            "icon": "bi-cash-stack",
        },
        'monthly_collections': {
            "key": "monthly_collections",
            "title": "صافي التحصيلات الشهرية",
            "value": f"{monthly_collections:,.2f}",
            "variant": "success",
            "icon": "bi-wallet2",
        },
        'financial_position': {
            "key": "financial_position",
            "title": "المركز المالي الحالي",
            "value": f"{financial_position:,.2f}",
            "variant": "info",
            "icon": "bi-bank",
        },
        # ========== الأنظمة الجديدة (10 أنظمة) ==========
        'sales_forecasting': {
            "key": "sales_forecasting",
            "title": "التنبؤ بالمبيعات AI",
            "value": "نشط",
            "variant": "primary",
            "icon": "bi-graph-up-arrow",
        },
        'marketing_campaigns': {
            "key": "marketing_campaigns",
            "title": "الحملات التسويقية",
            "value": "جاهز",
            "variant": "success",
            "icon": "bi-megaphone",
        },
        'tender_bidding': {
            "key": "tender_bidding",
            "title": "المناقصات والعطاءات",
            "value": "متاح",
            "variant": "info",
            "icon": "bi-file-earmark-text",
        },
        'warranty_management': {
            "key": "warranty_management",
            "title": "إدارة الضمانات",
            "value": "نشط",
            "variant": "warning",
            "icon": "bi-shield-check",
        },
        'customer_profitability': {
            "key": "customer_profitability",
            "title": "ربحية العملاء",
            "value": "متاح",
            "variant": "success",
            "icon": "bi-wallet2",
        },
        'energy_management': {
            "key": "energy_management",
            "title": "إدارة الطاقة",
            "value": "جاهز",
            "variant": "danger",
            "icon": "bi-lightning-charge",
        },
        'complaint_management': {
            "key": "complaint_management",
            "title": "إدارة الشكاوى",
            "value": "نشط",
            "variant": "warning",
            "icon": "bi-headset",
        },
        'license_management': {
            "key": "license_management",
            "title": "التراخيص والتصاريح",
            "value": "متاح",
            "variant": "info",
            "icon": "bi-file-earmark-medical",
        },
        'competitive_intelligence': {
            "key": "competitive_intelligence",
            "title": "الذكاء التنافسي",
            "value": "جاهز",
            "variant": "primary",
            "icon": "bi-binoculars",
        },
        'compliance_management': {
            "key": "compliance_management",
            "title": "الامتثال والمراجعة",
            "value": "نشط",
            "variant": "success",
            "icon": "bi-check-circle",
        },
    }

    # ===== فلترة البطاقات حسب صلاحيات المستخدم =====
    if not request.user.is_superuser:
        # البطاقات الأساسية: فلترة حسب نوع KPI
        _perm_map_cards = {
            'sales': lambda u: u.has_perm('sales.view_invoice') or u.has_perm('accounting.view_journalentry'),
            'purchases': lambda u: u.has_perm('purchases.view_purchasebill') or u.has_perm('accounting.view_journalentry'),
            'profit': lambda u: u.has_perm('accounting.view_journalentry'),
            'low_stock': lambda u: u.has_perm('inventory.view_product'),
        }
        cards = [c for c in cards if _perm_map_cards.get(c.get('key', ''), lambda u: False)(request.user)]

        # البطاقات الإضافية: فلترة حسب الصلاحية
        _perm_map_extra = {
            'monthly_expenses': lambda u: u.has_perm('accounting.view_journalentry'),
            'monthly_collections': lambda u: u.has_perm('accounting.view_journalentry'),
            'financial_position': lambda u: u.has_perm('accounting.view_journalentry'),
            'sales_forecasting': lambda u: u.has_perm('sales.view_invoice'),
            'marketing_campaigns': lambda u: u.has_perm('sales.view_invoice'),
            'customer_profitability': lambda u: u.has_perm('sales.view_invoice') or u.has_perm('partners.view_customer'),
        }
        extra_cards = {k: v for k, v in extra_cards.items()
                       if _perm_map_extra.get(k, lambda u: u.is_superuser)(request.user)}

    context = {
        'cards': cards,
        'extra_cards': extra_cards,
        'chart_labels': chart_labels,
        'sales_data': sales_data,
        'purchases_data': purchases_data,
        'kpi_trends': kpi_trends,
        'range_days': days,
        'period_from': period_start,
        'period_to': period_end,
        'range_param': range_param,
        'recent_audit': AuditLog.objects.select_related('user').order_by('-created_at')[:8],
    'recent_invoices': recent_invoices,
    'low_stock_items': low_stock_items,
        'invoice_breakdown': invoice_breakdown,
        'flow_labels': monthly_labels,
        'flow_net': monthly_net,
        'monthly_sales': monthly_sales,
        'monthly_purchases': monthly_purchases,
        'flow_json': {'labels': monthly_labels, 'net': monthly_net},
        'bars_json': {'labels': monthly_labels, 'sales': monthly_sales, 'purchases': monthly_purchases},
        'daily_json': {'labels': chart_labels, 'sales': sales_data, 'purchases': purchases_data},
        'top_products_json': {'labels': [p['name'] for p in top_products], 'data': [float(p['total_sales']) for p in top_products]},
        **system_stats,
        # بيانات إضافية للتصميم الجديد
        'total_sales': total_sales,
        'total_purchases': total_purchases,
        'total_profit': estimated_profit,
        'invoice_count': total_invoices,
        'low_stock_count': low_stock_count,
        'daily_profit': float(sales_data[-1] if sales_data else 0) - float(purchases_data[-1] if purchases_data else 0),
        'monthly_profit': sum(monthly_net) if monthly_net else 0,
        'yearly_profit': sum(monthly_net) if monthly_net else 0,
        'recent_activities': AuditLog.objects.select_related('user').order_by('-created_at')[:10],
        'top_products': top_products,
        'customer_count': customer_count,
        'product_count': product_count,
        # بيانات إضافية لتصميم Biznify
        'prev_sales': prev_sales,
        'prev_purchases': prev_purchases,
        'active_products_count': product_count - low_stock_count if product_count else 0,
        'categories_count': Category.objects.count(),
        # اعتماد القالب الحديث دائماً
        'base_template': 'base_v2.html',
    }
    
    # ==================== تقرير اليوم المختصر ====================
    try:
        from sales.models import Invoice as SalesInvoice
        from purchases.models import PurchaseBill
        
        today = date.today()
        
        # مبيعات اليوم
        today_sales_qs = InvoiceItem.objects.filter(invoice__date=today)
        if active_showroom_id and not show_all:
            today_sales_qs = today_sales_qs.filter(invoice__showroom_id=active_showroom_id)
        today_sales_total = today_sales_qs.aggregate(total=Sum(sales_expr))['total'] or 0
        
        # مشتريات اليوم
        today_purchases_qs = PurchaseItem.objects.filter(bill__date=today)
        if active_showroom_id and not show_all:
            today_purchases_qs = today_purchases_qs.filter(bill__showroom_id=active_showroom_id)
        today_purchases_total = today_purchases_qs.aggregate(total=Sum(purchase_expr))['total'] or 0
        
        # عدد فواتير اليوم
        today_invoices_qs = SalesInvoice.objects.filter(date=today)
        if active_showroom_id and not show_all:
            today_invoices_qs = today_invoices_qs.filter(showroom_id=active_showroom_id)
        today_invoices_count = today_invoices_qs.count()
        
        # عدد فواتير المشتريات اليوم
        today_purchases_bills_qs = PurchaseBill.objects.filter(date=today)
        if active_showroom_id and not show_all:
            today_purchases_bills_qs = today_purchases_bills_qs.filter(showroom_id=active_showroom_id)
        today_purchases_count = today_purchases_bills_qs.count()
        
        # التحصيلات اليوم
        try:
            from payments.models import PaymentTransaction
            today_collections_qs = PaymentTransaction.objects.filter(date=today, transaction_type='receipt')
            today_collections = today_collections_qs.aggregate(total=Sum('amount'))['total'] or 0
        except Exception:
            today_collections = 0
        
        # المصروفات اليوم
        try:
            today_expenses_qs = Expense.objects.filter(date=today)
            today_expenses = today_expenses_qs.aggregate(total=Sum('amount'))['total'] or 0
        except Exception:
            today_expenses = 0
        
        # صافي اليوم
        today_net_profit = float(today_sales_total) - float(today_purchases_total)
        today_net_cash = float(today_collections) - float(today_expenses)
        
        # عدد العملاء الجدد اليوم
        try:
            from partners.models import Customer
            today_new_customers = Customer.objects.filter(
                id__in=SalesInvoice.objects.filter(date=today).values('customer_id')
            ).count()
        except Exception:
            today_new_customers = 0
        
        context['daily_report'] = {
            'date': today,
            'sales_total': today_sales_total,
            'sales_count': today_invoices_count,
            'purchases_total': today_purchases_total,
            'purchases_count': today_purchases_count,
            'collections': today_collections,
            'expenses': today_expenses,
            'net_profit': today_net_profit,
            'net_cash': today_net_cash,
            'new_customers': today_new_customers,
        }
    except Exception as e:
        context['daily_report'] = None
    
    # إضافة عدد التصنيفات
    try:
        context['categories_count'] = Category.objects.count()
    except Exception:
        context['categories_count'] = 0
    
    # إضافة بيانات الحضور للموارد البشرية
    try:
        from hr.models import (
            AttendanceRecord,
            Employee,
            EmployeeSchedule,
            WorkSchedule,
            LeaveRequest,
            PublicHoliday,
            WeekendDay,
        )
        import json
        today = date.today()

        # الموظفون النشطون الخاضعون للحضور
        active_employees_qs = Employee.objects.filter(status='active', attendance_exempt=False)
        total_employees = active_employees_qs.count()

        # سجلات الحضور اليوم
        today_checkins = AttendanceRecord.objects.filter(
            date=today,
            record_type='check_in',
            employee__status='active',
            employee__attendance_exempt=False,
        )
        today_checkouts = AttendanceRecord.objects.filter(
            date=today,
            record_type='check_out',
            employee__status='active',
            employee__attendance_exempt=False,
        )
        present_ids = set(today_checkins.values_list('employee_id', flat=True).distinct())
        present_today = len(present_ids)

        # الإجازات المعتمدة لليوم
        leave_ids = set(
            LeaveRequest.objects.filter(
                status='approved',
                start_date__lte=today,
                end_date__gte=today,
            ).values_list('employee_id', flat=True)
        )
        leave_count = len(leave_ids)

        # العطلات الرسمية/الأسبوعية
        is_weekend = WeekendDay.objects.filter(day_of_week=today.weekday(), is_active=True).exists()
        is_public_holiday = PublicHoliday.objects.filter(
            Q(is_recurring=False, date=today) |
            Q(is_recurring=True, date__month=today.month, date__day=today.day)
        ).exists()
        if is_weekend or is_public_holiday:
            holiday_count = max(total_employees - present_today - leave_count, 0)
        else:
            holiday_count = 0

        # الغياب = موظفون نشطون - حاضر - إجازة - عطلة
        absent_count = max(total_employees - present_today - leave_count - holiday_count, 0)

        # حساب التأخير والانصراف المبكر بناءً على جدول العمل
        default_schedule = WorkSchedule.objects.filter(is_default=True).first()
        weekday_map = {
            0: ('monday_start', 'monday_end'),
            1: ('tuesday_start', 'tuesday_end'),
            2: ('wednesday_start', 'wednesday_end'),
            3: ('thursday_start', 'thursday_end'),
            4: ('friday_start', 'friday_end'),
            5: ('saturday_start', 'saturday_end'),
            6: ('sunday_start', 'sunday_end'),
        }

        schedule_cache = {}
        def _schedule_for_employee(emp_id):
            if emp_id in schedule_cache:
                return schedule_cache[emp_id]
            sched = (
                EmployeeSchedule.objects.filter(
                    employee_id=emp_id,
                    is_active=True,
                    start_date__lte=today,
                )
                .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
                .select_related('schedule')
                .order_by('-start_date')
                .first()
            )
            schedule_cache[emp_id] = sched.schedule if sched else default_schedule
            return schedule_cache[emp_id]

        late_count = 0
        early_out_count = 0
        late_employee_ids = set()
        early_out_employee_ids = set()
        start_field, end_field = weekday_map.get(today.weekday(), (None, None))

        if start_field and end_field:
            # حساب التأخير - نأخذ أول تسجيل حضور لكل موظف فقط
            seen_checkin_employees = set()
            for rec in today_checkins.select_related('employee').order_by('employee_id', 'time'):
                if rec.employee_id in seen_checkin_employees:
                    continue
                seen_checkin_employees.add(rec.employee_id)
                schedule = _schedule_for_employee(rec.employee_id)
                if not schedule:
                    continue
                start_time = getattr(schedule, start_field, None)
                if not start_time:
                    continue
                grace_minutes = getattr(schedule, 'grace_period_minutes', 0) or 0
                threshold = (datetime.combine(today, start_time) + timedelta(minutes=grace_minutes)).time()
                if rec.time > threshold:
                    late_employee_ids.add(rec.employee_id)

            # حساب الانصراف المبكر - نأخذ آخر تسجيل انصراف لكل موظف فقط
            last_checkout = {}
            for rec in today_checkouts.select_related('employee').order_by('employee_id', 'time'):
                last_checkout[rec.employee_id] = rec
            for emp_id, rec in last_checkout.items():
                schedule = _schedule_for_employee(emp_id)
                if not schedule:
                    continue
                end_time = getattr(schedule, end_field, None)
                if not end_time:
                    continue
                if rec.time < end_time:
                    early_out_employee_ids.add(emp_id)

            late_count = len(late_employee_ids)
            early_out_count = len(early_out_employee_ids)

        context['attendance_present'] = present_today
        context['attendance_absent'] = absent_count
        context['attendance_late'] = late_count
        context['attendance_early_out'] = early_out_count
        context['attendance_holiday'] = holiday_count
        context['attendance_leave'] = leave_count

        # الحضور حسب القسم (أسماء + أعداد)
        dept_rows = list(
            today_checkins.values('employee__department__name')
            .annotate(count=Count('employee', distinct=True))
            .order_by('-count')
        )
        dept_labels = [row['employee__department__name'] or 'غير محدد' for row in dept_rows]
        dept_values = [row['count'] for row in dept_rows]
        if not dept_labels:
            dept_labels = ['لا توجد بيانات']
            dept_values = [0]
        context['dept_attendance_labels_json'] = json.dumps(dept_labels)
        context['dept_attendance_values_json'] = json.dumps(dept_values)
    except Exception:
        # قيم افتراضية في حالة عدم توفر بيانات الموارد البشرية
        context['attendance_present'] = 0
        context['attendance_absent'] = 0
        context['attendance_late'] = 0
        context['attendance_early_out'] = 0
        context['attendance_holiday'] = 0
        context['attendance_leave'] = 0
        context['dept_attendance_labels_json'] = '[]'
        context['dept_attendance_values_json'] = '[]'
    
    # حفظ البيانات في Cache لمدة 5 دقائق (300 ثانية)
    cache.set(cache_key, context, 300)
    
    # استخدام تصميم Biznify الجديد
    template = 'core/dashboard_biznify.html'
    return render(request, template, context)


@permission_required('core.view_company', raise_exception=True)
def company_settings(request: HttpRequest):
    from core.models import Company, AppSettings, CompanyPhone
    from core.forms import CompanyPhoneFormSet
    import os
    # جلب بيانات الشركة الحالية
    company = Company.objects.first()
    brand_labels = {
        'primary': 'رئيسي',
        'primary_dark': 'رئيسي داكن',
        'primary_light': 'رئيسي فاتح',
        'info': 'معلومات',
        'success': 'نجاح',
        'warning': 'تحذير',
        'danger': 'خطر',
    }
    kpi_choices = {
        'sales': 'المبيعات (30 يوم)',
        'purchases': 'المشتريات (30 يوم)',
        'profit': 'الأرباح التقديرية',
        'low_stock': 'تنبيهات المخزون',
    }
    # القيم الحالية
    app_settings = AppSettings.get()
    brand_colors = dict(app_settings.brand_colors or {})
    if not brand_colors:
        brand_colors = {k: os.getenv(f'BRAND_{k.upper()}', '') for k in brand_labels.keys()}
    kpi_visible = [k.strip() for k in (app_settings.kpi_visible_keys or '').split(',') if k.strip()] or getattr(settings, 'KPI_VISIBLE_KEYS', ['sales','purchases','profit','low_stock'])
    
    # Phone formset
    phone_formset = CompanyPhoneFormSet(instance=company, prefix='phones') if company else None
    
    # معالجة الحفظ
    if request.method == 'POST':
        from django.contrib import messages
        import logging
        logger = logging.getLogger(__name__)
        
        form_type = request.POST.get('form_type', '')
        logger.warning(f"[LOGO DEBUG] form_type: {form_type}")
        logger.warning(f"[LOGO DEBUG] POST keys: {list(request.POST.keys())}")
        logger.warning(f"[LOGO DEBUG] FILES keys: {list(request.FILES.keys())}")
        
        # نموذج بيانات الشركة (شعار + اسم + ألوان + KPI)
        if form_type == 'company_settings':
            # شعار واسم الشركة
            name = request.POST.get('name')
            logo = request.FILES.get('logo')
            
            logger.warning(f"[LOGO DEBUG] name={name}, logo={logo}")
            
            # إنشاء Company إذا لم تكن موجودة
            if not company:
                company = Company.objects.create(name=name or 'Tony ERP')
            
            if name:
                company.name = name
            
            # حفظ بيانات الشركة الأساسية
            company.address = request.POST.get('address', '') or company.address
            company.phone = request.POST.get('phone', '') or company.phone
            company.mobile = request.POST.get('mobile', '') or ''
            company.email = request.POST.get('email', '') or ''
            company.tax_id = request.POST.get('tax_id', '') or company.tax_id
            company.commercial_register = request.POST.get('commercial_register', '') or ''
            company.slogan = request.POST.get('slogan', '') or ''
            company.footer_text = request.POST.get('footer_text', '') or ''
            
            # نسبة ضريبة القيمة المضافة
            vat_rate = request.POST.get('default_vat_rate', '')
            logger.warning(f"[VAT SAVE] raw value from POST: '{vat_rate}'")
            if vat_rate:
                try:
                    from decimal import Decimal
                    company.default_vat_rate = Decimal(str(vat_rate).strip())
                    logger.warning(f"[VAT SAVE] assigned to company: {company.default_vat_rate}")
                except Exception as e:
                    logger.warning(f"[VAT SAVE] Decimal conversion error: {e}")
            else:
                logger.warning("[VAT SAVE] vat_rate was EMPTY in POST")
            
            # مواقع التواصل الاجتماعي
            company.website = request.POST.get('website', '') or ''
            company.whatsapp = request.POST.get('whatsapp', '') or ''
            company.facebook = request.POST.get('facebook', '') or ''
            company.instagram = request.POST.get('instagram', '') or ''
            company.twitter = request.POST.get('twitter', '') or ''
            company.tiktok = request.POST.get('tiktok', '') or ''
            company.youtube = request.POST.get('youtube', '') or ''
            company.linkedin = request.POST.get('linkedin', '') or ''
            
            if logo:
                # حفظ اللوجو بشكل صريح
                logger.warning(f"[LOGO DEBUG] Saving logo: {logo.name}, size: {logo.size}")
                company.logo.save(logo.name, logo, save=True)
                logger.warning(f"[LOGO DEBUG] After save, company.logo = {company.logo}")
                messages.success(request, f'تم رفع الشعار: {logo.name}')
            else:
                logger.warning(f"[VAT SAVE] About to save company. default_vat_rate = {company.default_vat_rate}")
                company.save()
                company.refresh_from_db()
                logger.warning(f"[VAT SAVE] After save + refresh. default_vat_rate = {company.default_vat_rate}")
            
            # حفظ أرقام الهواتف المتعددة
            phone_formset = CompanyPhoneFormSet(request.POST, instance=company, prefix='phones')
            if phone_formset.is_valid():
                phone_formset.save()
            else:
                logger.warning(f"Phone formset errors: {phone_formset.errors}")
            
            # ألوان الهوية + KPI في AppSettings
            colors = {}
            for k in brand_labels.keys():
                color = request.POST.get(f'brand_{k}')
                if color:
                    colors[k] = color
            if colors:
                app_settings.brand_colors = colors
            kpi_keys = request.POST.getlist('kpi_keys')
            if kpi_keys:
                app_settings.kpi_visible_keys = ','.join(kpi_keys)
            app_settings.save()
            messages.success(request, 'تم حفظ إعدادات الشركة بنجاح')
            return redirect('core:company_settings')
        
        # نموذج إعدادات التدقيق
        elif form_type == 'audit_settings':
            # إعدادات التدقيق
            try:
                audit_retention_days = int(request.POST.get('audit_retention_days') or app_settings.audit_retention_days or 90)
            except Exception:
                audit_retention_days = app_settings.audit_retention_days or 90
            app_settings.audit_retention_days = audit_retention_days
            # حد الحوادث الشهري لتنبيه السلامة
            try:
                safety_threshold = int(request.POST.get('safety_incident_alert_threshold') or app_settings.safety_incident_alert_threshold or 3)
                if safety_threshold < 1:
                    safety_threshold = 1
            except Exception:
                safety_threshold = app_settings.safety_incident_alert_threshold or 3
            app_settings.safety_incident_alert_threshold = safety_threshold
            # قوائم JSON بسيطة مفصولة بفواصل
            def _split_list(val):
                return [x.strip() for x in (val or '').split(',') if x.strip()]
            app_settings.audit_sensitive_fields = _split_list(request.POST.get('audit_sensitive_fields'))
            app_settings.audit_ignore_apps = _split_list(request.POST.get('audit_ignore_apps'))
            app_settings.audit_ignore_models = _split_list(request.POST.get('audit_ignore_models'))
            # قواعد تنبيه: JSON نصي
            import json as _json
            try:
                rules_text = request.POST.get('audit_alert_rules') or '[]'
                app_settings.audit_alert_rules = _json.loads(rules_text)
            except Exception:
                pass
            # بريد تنبيهات السلامة: قائمة مفصولة بفواصل
            safety_emails_raw = request.POST.get('safety_alert_emails', '')
            safety_emails = [e.strip() for e in safety_emails_raw.split(',') if e.strip()]
            app_settings.safety_alert_emails = safety_emails
            app_settings.save()
            messages.success(request, 'تم حفظ إعدادات التدقيق بنجاح')
            # إعادة تحميل الصفحة بعد الحفظ
            return redirect('core:company_settings')
    # Refresh phone formset after POST
    if company:
        phone_formset = CompanyPhoneFormSet(instance=company, prefix='phones')
    
    context = {
        'company': company,
        'phone_formset': phone_formset,
        'brand_labels': brand_labels,
        'brand_colors': brand_colors,
        'kpi_choices': kpi_choices,
        'kpi_visible': kpi_visible,
    # Audit settings context
    'audit_retention_days': app_settings.audit_retention_days,
    'audit_sensitive_fields': ','.join(app_settings.audit_sensitive_fields or []),
    'audit_ignore_apps': ','.join(app_settings.audit_ignore_apps or []),
    'audit_ignore_models': ','.join(app_settings.audit_ignore_models or []),
    'audit_alert_rules': (app_settings.audit_alert_rules or []),
    'safety_incident_alert_threshold': app_settings.safety_incident_alert_threshold or 3,
    'safety_alert_emails': ','.join(app_settings.safety_alert_emails or []),
    }
    return render(request, 'core/company_settings.html', context)


@login_required
def factory_reset(request: HttpRequest):
    """إعادة ضبط المصنع للنظام مع حواجز أمان قوية.

    - يسمح فقط للمشرفين الفائقين أو من لديهم صلاحية change_company.
    - يتطلب تأكيداً كتابياً: "I UNDERSTAND, RESET ALL DATA".
    - خيار إنشاء نسخة احتياطية Zip سريعة من قاعدة البيانات والوسائط قبل التفريغ.
    - يحتفظ بمستخدمي النظام والأذونات (auth) ولا يمس جداول الهجرة.
    """
    from django.contrib.auth.decorators import user_passes_test
    from django.db import connection
    from django.apps import apps
    from django.contrib.auth import get_user_model

    if not request.user.is_superuser and not request.user.has_perm('core.change_company'):
        messages.error(request, _t('غير مصرح لك بتنفيذ هذه العملية.'))
        return redirect('core:company_settings')

    if request.method == 'POST':
        raw_confirm = (request.POST.get('confirm_text') or '').strip()
        make_backup = bool(request.POST.get('make_backup'))

        # النص المطلوب للتأكيد بالعربي
        required_phrase = 'أوافق على الحذف'
        if raw_confirm != required_phrase:
            messages.error(request, _t('يجب كتابة عبارة التأكيد تماماً: %(p)s') % {'p': required_phrase})
            return redirect('core:company_settings')

        backup_path = None
        try:
            with transaction.atomic():
                # 1) نسخة احتياطية اختيارية
                if make_backup:
                    backups_dir = os.path.join(os.getcwd(), 'backups')
                    os.makedirs(backups_dir, exist_ok=True)
                    backup_name = f"backup_before_reset_{date.today().isoformat()}.zip"
                    backup_path = os.path.join(backups_dir, backup_name)
                    with zipfile.ZipFile(backup_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        # قاعدة البيانات (SQLite فقط)
                        db_path = os.path.join(os.getcwd(), 'db.sqlite3')
                        if os.path.exists(db_path):
                            zf.write(db_path, arcname='db.sqlite3')
                        # مجلد الوسائط
                        media_root = getattr(settings, 'MEDIA_ROOT', None) or os.path.join(os.getcwd(), 'media')
                        if os.path.isdir(media_root):
                            for root, dirs, files in os.walk(media_root):
                                for fname in files:
                                    fpath = os.path.join(root, fname)
                                    arc = os.path.relpath(fpath, media_root)
                                    zf.write(fpath, arcname=f"media/{arc}")

                # 2) تفريغ البيانات من معظم التطبيقات باستثناء auth و contenttypes و sessions الأساسية للمستخدمين
                preserve_apps = {'auth', 'admin', 'contenttypes', 'sessions'}
                # جداول نستثنيها صراحةً
                preserve_models = {
                    ('auth', 'User'), ('auth', 'Group'), ('auth', 'Permission'),
                }

                # امسح سجلات سجلات التدقيق قبل كل شيء لتقليل الحجم
                try:
                    AuditLog.objects.all().delete()
                except Exception:
                    pass

                # مر على جميع النماذج وقم بحذف البيانات بأمان
                for model in apps.get_models():
                    app_label = model._meta.app_label
                    model_name = model.__name__
                    # تخطِّ المحفوظات والمستخدمين وما إلى ذلك
                    if app_label in preserve_apps or (app_label, model_name) in preserve_models:
                        continue
                    # لا تلمس نماذج الهجرة
                    if app_label == 'migrations' or model_name.lower() == 'migration':
                        continue
                    # الأفضل استخدام .objects.all().delete() لتفادي TRUNCATE على SQLite
                    try:
                        model.objects.all().delete()
                    except Exception:
                        # fallback: تجاهل النماذج التي لا يمكن حذفها (علاقات محمية)
                        pass

                # إعادة تهيئة الحد الأدنى: شركة واحدة وإعدادات التطبيق
                try:
                    from core.models import AppSettings, Company, Currency
                    # لا نحذف العملات كلياً، لكن نعيد الإعدادات الافتراضية إذا فرغت
                    if not Currency.objects.exists():
                        Currency.get_default()  # سينشئ EGP إذا لزم
                    AppSettings.get()  # يضمن وجود سجل واحد
                    if not Company.objects.exists():
                        Company.objects.create(name='المحاسب الشامل')
                except Exception:
                    pass

            if backup_path:
                messages.success(request, _t('تمت إعادة الضبط بنجاح. تم إنشاء نسخة احتياطية: %(p)s') % {'p': backup_path})
            else:
                messages.success(request, _t('تمت إعادة الضبط بنجاح.'))
        except Exception as e:
            messages.error(request, _t('فشل إعادة الضبط: %(err)s') % {'err': str(e)[:200]})
        else:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ACTION_DELETE,
                    model_name='System',
                    app_label='core',
                    object_id='factory_reset',
                    object_repr='Factory reset executed',
                    changes={'backup': bool(backup_path)}
                )
            except Exception:
                pass
        return redirect('core:company_settings')

    # GET: أظهر صفحة الإعدادات مع منطقة الخطر
    return redirect('core:company_settings')

@login_required
def get_hr_attendance_data(request):
    """API endpoint لجلب بيانات حضور الموارد البشرية مع دعم فلترة التاريخ"""
    try:
        from hr.models import (
            AttendanceRecord, Employee, EmployeeSchedule, WorkSchedule,
            LeaveRequest, PublicHoliday, WeekendDay,
        )
        import json

        # التاريخ المطلوب (يأتي من فلتر التاريخ في الداشبورد)
        date_str = request.GET.get('date')
        if date_str:
            try:
                target_date = date.fromisoformat(date_str)
            except (ValueError, TypeError):
                target_date = date.today()
        else:
            target_date = date.today()

        # الموظفون النشطون الخاضعون للحضور
        active_employees_qs = Employee.objects.filter(status='active', attendance_exempt=False)
        total_employees = active_employees_qs.count()

        # سجلات الحضور لليوم المحدد
        today_checkins = AttendanceRecord.objects.filter(
            date=target_date,
            record_type='check_in',
            employee__status='active',
            employee__attendance_exempt=False,
        )
        today_checkouts = AttendanceRecord.objects.filter(
            date=target_date,
            record_type='check_out',
            employee__status='active',
            employee__attendance_exempt=False,
        )
        present_ids = set(today_checkins.values_list('employee_id', flat=True).distinct())
        present_today = len(present_ids)

        # الإجازات المعتمدة
        leave_ids = set(
            LeaveRequest.objects.filter(
                status='approved',
                start_date__lte=target_date,
                end_date__gte=target_date,
            ).values_list('employee_id', flat=True)
        )
        leave_count = len(leave_ids)

        # العطلات
        is_weekend = WeekendDay.objects.filter(day_of_week=target_date.weekday(), is_active=True).exists()
        is_public_holiday = PublicHoliday.objects.filter(
            Q(is_recurring=False, date=target_date) |
            Q(is_recurring=True, date__month=target_date.month, date__day=target_date.day)
        ).exists()
        if is_weekend or is_public_holiday:
            holiday_count = max(total_employees - present_today - leave_count, 0)
        else:
            holiday_count = 0

        absent_count = max(total_employees - present_today - leave_count - holiday_count, 0)

        # حساب التأخير والانصراف المبكر
        default_schedule = WorkSchedule.objects.filter(is_default=True).first()
        weekday_map = {
            0: ('monday_start', 'monday_end'), 1: ('tuesday_start', 'tuesday_end'),
            2: ('wednesday_start', 'wednesday_end'), 3: ('thursday_start', 'thursday_end'),
            4: ('friday_start', 'friday_end'), 5: ('saturday_start', 'saturday_end'),
            6: ('sunday_start', 'sunday_end'),
        }
        schedule_cache = {}

        def _schedule_for_emp(emp_id):
            if emp_id in schedule_cache:
                return schedule_cache[emp_id]
            sched = (
                EmployeeSchedule.objects.filter(
                    employee_id=emp_id, is_active=True, start_date__lte=target_date,
                ).filter(Q(end_date__isnull=True) | Q(end_date__gte=target_date))
                .select_related('schedule').order_by('-start_date').first()
            )
            schedule_cache[emp_id] = sched.schedule if sched else default_schedule
            return schedule_cache[emp_id]

        late_employee_ids = set()
        early_out_employee_ids = set()
        start_field, end_field = weekday_map.get(target_date.weekday(), (None, None))

        if start_field and end_field:
            seen = set()
            for rec in today_checkins.select_related('employee').order_by('employee_id', 'time'):
                if rec.employee_id in seen:
                    continue
                seen.add(rec.employee_id)
                schedule = _schedule_for_emp(rec.employee_id)
                if not schedule:
                    continue
                st = getattr(schedule, start_field, None)
                if not st:
                    continue
                grace = getattr(schedule, 'grace_period_minutes', 0) or 0
                threshold = (datetime.combine(target_date, st) + timedelta(minutes=grace)).time()
                if rec.time > threshold:
                    late_employee_ids.add(rec.employee_id)

            last_checkout = {}
            for rec in today_checkouts.select_related('employee').order_by('employee_id', 'time'):
                last_checkout[rec.employee_id] = rec
            for emp_id, rec in last_checkout.items():
                schedule = _schedule_for_emp(emp_id)
                if not schedule:
                    continue
                et = getattr(schedule, end_field, None)
                if not et:
                    continue
                if rec.time < et:
                    early_out_employee_ids.add(emp_id)

        # الحضور حسب القسم
        dept_rows = list(
            today_checkins.values('employee__department__name')
            .annotate(count=Count('employee', distinct=True))
            .order_by('-count')
        )
        dept_labels = [row['employee__department__name'] or 'غير محدد' for row in dept_rows]
        dept_values = [row['count'] for row in dept_rows]
        if not dept_labels:
            dept_labels = ['لا توجد بيانات']
            dept_values = [0]

        return JsonResponse({
            'status': 'success',
            'attendance_present': present_today,
            'attendance_absent': absent_count,
            'attendance_late': len(late_employee_ids),
            'attendance_early_out': len(early_out_employee_ids),
            'attendance_holiday': holiday_count,
            'attendance_leave': leave_count,
            'dept_labels': dept_labels,
            'dept_values': dept_values,
            'total_employees': total_employees,
            'target_date': target_date.isoformat(),
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'attendance_present': 0, 'attendance_absent': 0,
            'attendance_late': 0, 'attendance_early_out': 0,
            'attendance_holiday': 0, 'attendance_leave': 0,
            'dept_labels': [], 'dept_values': [],
        }, status=500)


@login_required
def get_dashboard_data(request):
    """API endpoint لجلب بيانات لوحة التحكم عبر AJAX"""
    try:
        from django.apps import apps
        today = date.today()
        # Parse range similar to dashboard view
        range_param = (request.GET.get('range') or '30').strip()
        try:
            period_end = today
            if range_param.lower() == '7':
                days = 7
            elif range_param.lower() == '90':
                days = 90
            elif range_param.lower() == 'custom':
                df = request.GET.get('from') or request.GET.get('date_from')
                dt = request.GET.get('to') or request.GET.get('date_to')
                d_from = date.fromisoformat(df) if df else (today - timedelta(days=29))
                d_to = date.fromisoformat(dt) if dt else today
                if d_from > d_to:
                    d_from, d_to = d_to, d_from
                days = max(1, (d_to - d_from).days + 1)
                period_end = d_to
            else:
                days = 30
            to_override = request.GET.get('to') or request.GET.get('date_to')
            if to_override:
                try:
                    period_end = date.fromisoformat(to_override)
                except Exception:
                    pass
        except Exception:
            days = 30
            period_end = today

        period_start = period_end - timedelta(days=days - 1)
        last_30_days = period_start

        # البيانات الأساسية
        data: dict[str, object] = {
            'last_updated': today.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'success',
        }

        # إحصائيات المبيعات
        try:
            from sales.models import InvoiceItem as _InvoiceItem
            total_sales = _InvoiceItem.objects.filter(
                invoice__date__gte=last_30_days, invoice__date__lte=period_end
            ).aggregate(total=Sum(ExpressionWrapper(
                F('quantity') * F('price'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )))['total'] or 0
            data['total_sales'] = float(total_sales)
        except Exception:
            data['total_sales'] = 0

        # إحصائيات المشتريات
        try:
            from purchases.models import PurchaseItem as _PurchaseItem
            total_purchases = _PurchaseItem.objects.filter(
                bill__date__gte=last_30_days, bill__date__lte=period_end
            ).aggregate(total=Sum(ExpressionWrapper(
                F('quantity') * F('cost'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )))['total'] or 0
            data['total_purchases'] = float(total_purchases)
        except Exception:
            data['total_purchases'] = 0

        # إحصائيات المخزون
        try:
            Product = apps.get_model('inventory', 'Product')
            data['total_products'] = Product.objects.count()
            data['low_stock_products'] = Product.objects.annotate(
                total_qty=Coalesce(Sum('stocks__quantity'), 0)
            ).filter(total_qty__lt=F('min_stock')).count()
        except Exception:
            data['total_products'] = 0
            data['low_stock_products'] = 0

        # إحصائيات الموارد البشرية
        try:
            Employee = apps.get_model('hr', 'Employee')
            data['total_employees'] = Employee.objects.filter(status='active').count()
        except Exception:
            data['total_employees'] = 0

        # إحصائيات CRM
        try:
            Customer = apps.get_model('crm', 'Customer')
            Opportunity = apps.get_model('crm', 'Opportunity')
            data['total_customers'] = Customer.objects.count()
            data['open_opportunities'] = Opportunity.objects.filter(
                stage__is_won=False, stage__is_lost=False
            ).count()
        except Exception:
            data['total_customers'] = 0
            data['open_opportunities'] = 0

        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def logout_view(request):
    """تسجيل خروج مخصص"""
    from django.contrib.auth import logout
    try:
        from hr.models import AttendanceRecord
        employee = getattr(request.user, 'employee_profile', None)
        if employee and not getattr(employee, 'attendance_exempt', False):
            today = date.today()
            checked_in = AttendanceRecord.objects.filter(
                employee=employee, date=today, record_type='check_in'
            ).exists()
            checked_out = AttendanceRecord.objects.filter(
                employee=employee, date=today, record_type='check_out'
            ).exists()

            if checked_in and not checked_out:
                messages.warning(request, 'لا يمكن تسجيل الخروج قبل تسجيل الانصراف')
                return redirect('hr:employee_welcome')
    except Exception:
        pass
    
    if request.method == 'POST':
        logout(request)
        return redirect('/')
    else:
        # إذا كان GET request، وجه لصفحة تأكيد أو اخرج مباشرة
        logout(request)
        return redirect('/')


@login_required
def switch_account(request):
    """تبديل الحساب - تسجيل دخول بحساب آخر بدون تسجيل خروج/انصراف"""
    from django.contrib.auth import authenticate, login as auth_login
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'يرجى إدخال اسم المستخدم وكلمة المرور')
            return render(request, 'core/switch_account.html')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                # تسجيل دخول مباشر بدون تسجيل خروج (لا يؤثر على الحضور)
                auth_login(request, user)
                messages.success(request, f'تم تبديل الحساب إلى {username} بنجاح')
                return redirect('/')
            else:
                messages.error(request, 'هذا الحساب غير مفعل')
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')
    
    return render(request, 'core/switch_account.html')


def login_view(request):
    """صفحة تسجيل الدخول"""
    from django.contrib.auth import authenticate, login
    from django.contrib import messages
    
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/dashboard/')
            return redirect(next_url)
        else:
            messages.error(request, _t('اسم المستخدم أو كلمة المرور غير صحيحة'))
    
    return render(request, 'registration/login.html')


@login_required


@permission_required('core.view_auditlog', raise_exception=True)
def audit_logs(request: HttpRequest):
    """قائمة بسيطة لسجلات التدقيق مع بحث سريع"""
    q = request.GET.get('q', '').strip()
    action = request.GET.get('action', '').strip()
    user_id = request.GET.get('user', '').strip()
    app_label = request.GET.get('app_label', '').strip()
    model_name = request.GET.get('model_name', '').strip()
    object_id = request.GET.get('object_id', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    sort = request.GET.get('sort', 'created_at').strip() or 'created_at'
    ip_address = request.GET.get('ip_address', '').strip()
    user_agent = request.GET.get('user_agent', '').strip()
    order = request.GET.get('order', 'desc').strip().lower()

    qs = AuditLog.objects.all().select_related('user')
    if q:
        qs = qs.filter(
            Q(app_label__icontains=q) | Q(model_name__icontains=q) | Q(object_id__icontains=q) |
            Q(object_repr__icontains=q) | Q(user__username__icontains=q) | Q(ip_address__icontains=q)
        )
    if action:
        qs = qs.filter(action=action)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if app_label:
        qs = qs.filter(app_label__iexact=app_label)
    if model_name:
        qs = qs.filter(model_name__iexact=model_name)
    if object_id:
        qs = qs.filter(object_id=str(object_id))
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if ip_address:
        qs = qs.filter(ip_address__icontains=ip_address)
    if user_agent:
        qs = qs.filter(user_agent__icontains=user_agent)

    # Sorting
    allowed_sort = {'created_at','action','user','app_label','model_name','object_id','ip_address'}
    sort_field = 'created_at' if sort not in allowed_sort else sort
    if sort_field == 'user':
        order_by = ('-user__username' if order == 'desc' else 'user__username')
    else:
        order_by = (f"-{sort_field}" if order == 'desc' else sort_field)
    qs = qs.order_by(order_by)

    # Pagination
    page = request.GET.get('page', '1')
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(page)

    # CSV export (exports up to 5000 of the filtered records)
    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        # Add BOM for Excel UTF-8 support
        response.write('\ufeff')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'created_at','action','user','app_label','model_name','object_id','object_repr','ip_address','user_agent','changes'
        ])
        for r in qs[:5000]:
            writer.writerow([
                r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                r.action,
                (r.user.username if r.user else ''),
                r.app_label,
                r.model_name,
                r.object_id,
                r.object_repr,
                r.ip_address or '',
                r.user_agent or '',
                json.dumps(r.changes or {}, ensure_ascii=False),
            ])
        return response

    # XLSX export (best-effort, falls back to CSV if openpyxl not available)
    if request.GET.get('format') == 'xlsx':
        try:
            from openpyxl import Workbook
            wb: Any = Workbook()
            ws: Any = wb.active
            ws.title = 'Audit Logs'
            if ws: ws.append(['created_at','action','user','app_label','model_name','object_id','object_repr','ip_address','user_agent','changes'])
            for r in qs[:5000]:
                if ws: ws.append([
                    r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    r.action,
                    (r.user.username if r.user else ''),
                    r.app_label,
                    r.model_name,
                    r.object_id,
                    r.object_repr,
                    r.ip_address or '',
                    r.user_agent or '',
                    json.dumps(r.changes or {}, ensure_ascii=False),
                ])
            from io import BytesIO
            buf = BytesIO()
            wb.save(buf)
            buf.seek(0)
            resp = HttpResponse(buf.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = 'attachment; filename="audit_logs.xlsx"'
            return resp
        except Exception:
            # Fallback to CSV
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response.write('\ufeff')
            response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'created_at','action','user','app_label','model_name','object_id','object_repr','ip_address','user_agent','changes'
            ])
            for r in qs[:5000]:
                writer.writerow([
                    r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    r.action,
                    (r.user.username if r.user else ''),
                    r.app_label,
                    r.model_name,
                    r.object_id,
                    r.object_repr,
                    r.ip_address or '',
                    r.user_agent or '',
                    json.dumps(r.changes or {}, ensure_ascii=False),
                ])
            return response

    # Print-friendly page
    if request.GET.get('format') == 'print':
        context = {'logs': qs[:500], 'q': q, 'action': action, 'user_id': user_id, 'app_label': app_label, 'model_name': model_name, 'object_id': object_id}
        return render(request, 'core/audit_logs_print.html', context)
    # بيانات مساعدة للواجهة
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Build base query string for pagination links
    base_qs = urlencode({
        k: v for k, v in {
            'q': q,
            'action': action,
            'user': user_id,
            'app_label': app_label,
            'model_name': model_name,
            'object_id': object_id,
            'date_from': date_from,
            'date_to': date_to,
            'sort': sort,
            'order': order,
            'ip_address': ip_address,
            'user_agent': user_agent,
        }.items() if v
    })

    context = {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'base_qs': base_qs,
        'q': q,
        'action': action,
        'user_id': user_id,
        'app_label': app_label,
        'model_name': model_name,
        'object_id': object_id,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort,
        'order': order,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'users': User.objects.filter(is_active=True).order_by('username')[:200],
        'action_choices': AuditLog.ACTION_CHOICES,
        'sort_choices': [
            ('created_at','التاريخ'),
            ('action','الإجراء'),
            ('user','المستخدم'),
            ('app_label','التطبيق'),
            ('model_name','النموذج'),
            ('object_id','المعرف'),
            ('ip_address','IP'),
        ],
    }
    return render(request, 'core/audit_logs.html', context)


# ============== إدارة العملات ==============

@permission_required('core.view_currency', raise_exception=True)
def currency_settings(request):
    """صفحة إعدادات العملات"""
    currencies = Currency.objects.all().order_by('code')
    default_currency = Currency.get_default()
    
    context = {
        'currencies': currencies,
        'default_currency': default_currency,
        'page_title': _('إعدادات العملات'),
        'breadcrumb': [
            {'name': _('الرئيسية'), 'url': '/'},
            {'name': _('إعدادات النظام'), 'url': '#'},
            {'name': _('العملات'), 'url': '#', 'active': True}
        ]
    }
    return render(request, 'core/currency_settings.html', context)


@permission_required('core.add_currency', raise_exception=True)
def currency_add(request):
    """إضافة عملة جديدة"""
    if request.method == 'POST':
        form = CurrencyForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    currency = form.save()
                    messages.success(request, _t('تم إنشاء العملة %(name)s بنجاح') % {'name': currency.name})
                    return redirect('core:currency_settings')
            except Exception as e:
                messages.error(request, _t('حدث خطأ في إنشاء العملة: %(err)s') % {'err': str(e)})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, _t('%(field)s: %(error)s') % {'field': field, 'error': error})
    else:
        form = CurrencyForm()
    
    context = {
        'form': form,
        'page_title': _('إضافة عملة جديدة'),
        'form_action': _('إضافة'),
        'breadcrumb': [
            {'name': _('الرئيسية'), 'url': '/'},
            {'name': _('إعدادات العملات'), 'url': 'core:currency_settings'},
            {'name': _('إضافة عملة'), 'url': '#', 'active': True}
        ]
    }
    return render(request, 'core/currency_form.html', context)


@permission_required('core.change_currency', raise_exception=True)
def currency_edit(request, currency_id):
    """تعديل عملة موجودة"""
    currency = get_object_or_404(Currency, id=currency_id)
    
    if request.method == 'POST':
        form = CurrencyForm(request.POST, instance=currency)
        if form.is_valid():
            try:
                with transaction.atomic():
                    currency = form.save()
                    messages.success(request, _t('تم تحديث العملة %(name)s بنجاح') % {'name': currency.name})
                    return redirect('core:currency_settings')
            except Exception as e:
                messages.error(request, _t('حدث خطأ في تحديث العملة: %(err)s') % {'err': str(e)})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, _t('%(field)s: %(error)s') % {'field': field, 'error': error})
    else:
        form = CurrencyForm(instance=currency)
    
    context = {
        'form': form,
        'currency': currency,
        'page_title': _t('تعديل العملة %(name)s') % {'name': currency.name},
        'form_action': _('تحديث'),
        'breadcrumb': [
            {'name': _('الرئيسية'), 'url': '/'},
            {'name': _('إعدادات العملات'), 'url': 'core:currency_settings'},
            {'name': _t('تعديل %(name)s') % {'name': currency.name}, 'url': '#', 'active': True}
        ]
    }
    return render(request, 'core/currency_form.html', context)


@permission_required('core.delete_currency', raise_exception=True)
def currency_delete(request, currency_id):
    """حذف عملة"""
    currency = get_object_or_404(Currency, id=currency_id)
    
    # لا يمكن حذف العملة الافتراضية
    if currency.is_default:
        messages.error(request, _t('لا يمكن حذف العملة الافتراضية'))
        return redirect('core:currency_settings')
    
    if request.method == 'POST':
        currency_name = currency.name
        try:
            currency.delete()
            messages.success(request, _t('تم حذف العملة %(name)s بنجاح') % {'name': currency_name})
        except Exception as e:
            messages.error(request, _t('حدث خطأ في حذف العملة: %(err)s') % {'err': str(e)})
        return redirect('core:currency_settings')
    
    context = {
        'currency': currency,
        'page_title': _t('حذف العملة %(name)s') % {'name': currency.name},
        'breadcrumb': [
            {'name': _('الرئيسية'), 'url': '/'},
            {'name': _('إعدادات العملات'), 'url': 'core:currency_settings'},
            {'name': _('حذف عملة'), 'url': '#', 'active': True}
        ]
    }
    return render(request, 'core/currency_confirm_delete.html', context)


@permission_required('core.change_currency', raise_exception=True)
def currency_set_default(request, currency_id):
    """تعيين عملة كافتراضية"""
    if request.method == 'POST':
        currency = get_object_or_404(Currency, id=currency_id)
        
        if not currency.is_active:
            messages.error(request, _t('لا يمكن تعيين عملة غير نشطة كافتراضية'))
        else:
            try:
                with transaction.atomic():
                    # إلغاء الافتراضية من باقي العملات
                    Currency.objects.filter(is_default=True).update(is_default=False)
                    # تعيين العملة الجديدة كافتراضية
                    currency.is_default = True
                    currency.save()
                    messages.success(request, _t('تم تعيين %(name)s كعملة افتراضية') % {'name': currency.name})
            except Exception as e:
                messages.error(request, _t('حدث خطأ: %(err)s') % {'err': str(e)})
    
    return redirect('core:currency_settings')


@permission_required('core.change_currency', raise_exception=True)
def currency_exchange_rates(request):
    """تحديث أسعار الصرف"""
    if request.method == 'POST':
        form = CurrencyExchangeRateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    messages.success(request, _t('تم تحديث أسعار الصرف بنجاح'))
                    return redirect('core:currency_settings')
            except Exception as e:
                messages.error(request, _t('حدث خطأ في تحديث أسعار الصرف: %(err)s') % {'err': str(e)})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, _t('%(field)s: %(error)s') % {'field': field, 'error': error})
    else:
        form = CurrencyExchangeRateForm()
    
    context = {
        'form': form,
        'page_title': _('تحديث أسعار الصرف'),
        'breadcrumb': [
            {'name': _('الرئيسية'), 'url': '/'},
            {'name': _('إعدادات العملات'), 'url': 'core:currency_settings'},
            {'name': _('أسعار الصرف'), 'url': '#', 'active': True}
        ]
    }
    return render(request, 'core/currency_exchange_rates.html', context)


# ============== إعدادات الشركة ==============


# ============== Health Check Endpoints ==============

from django.http import JsonResponse
from django.db import connection


# ======================================================================
# DEPRECATED: استخدم core.health_views بدلاً من هذه الدوال
# تم الإبقاء عليها للتوافق الخلفي فقط
# ======================================================================
def health_live(request):
    """Deprecated: use core.health_views.health_live instead"""
    from core.health_views import health_live as _health_live
    return _health_live(request)


def health_ready(request):
    """Deprecated: use core.health_views.health_ready instead"""
    from core.health_views import health_ready as _health_ready
    return _health_ready(request)


# ===== إدارة الفروع =====
@login_required
def branch_list(request):
    """قائمة الفروع - توجيه إلى نظام الفروع الرئيسي"""
    # توجيه إلى صفحة الفروع في branches app
    return redirect('branches:branch_list')


@login_required
@permission_required('core.add_branch', raise_exception=True)
def branch_create(request):
    """إنشاء فرع جديد"""
    from .forms import BranchForm
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء الفرع بنجاح')
            return redirect('core:branch_list')
    else:
        form = BranchForm()
    return render(request, 'core/branches/form.html', {'form': form, 'title': 'إنشاء فرع جديد'})


@login_required
@permission_required('core.change_branch', raise_exception=True)
def branch_edit(request, pk):
    """تعديل فرع"""
    from .models import Branch
    from .forms import BranchForm
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الفرع بنجاح')
            return redirect('core:branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'core/branches/form.html', {'form': form, 'title': 'تعديل الفرع', 'branch': branch})


@login_required
@permission_required('core.delete_branch', raise_exception=True)
def branch_delete(request, pk):
    """حذف فرع"""
    from .models import Branch
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        branch.delete()
        messages.success(request, 'تم حذف الفرع بنجاح')
        return redirect('core:branch_list')
    return render(request, 'core/branches/delete.html', {'branch': branch})


# ===== إدارة الدول =====
@login_required
def country_list(request):
    """قائمة الدول"""
    from .models import Country
    countries = Country.objects.all().order_by('name')
    return render(request, 'core/countries/list.html', {'countries': countries})


@login_required
def country_create(request):
    """إنشاء دولة جديدة"""
    from .forms import CountryForm
    if request.method == 'POST':
        form = CountryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء الدولة بنجاح')
            return redirect('core:country_list')
    else:
        form = CountryForm()
    return render(request, 'core/countries/form.html', {'form': form, 'title': 'إنشاء دولة جديدة'})


@login_required
def country_edit(request, pk):
    """تعديل دولة"""
    from .models import Country
    from .forms import CountryForm
    country = get_object_or_404(Country, pk=pk)
    if request.method == 'POST':
        form = CountryForm(request.POST, instance=country)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الدولة بنجاح')
            return redirect('core:country_list')
    else:
        form = CountryForm(instance=country)
    return render(request, 'core/countries/form.html', {'form': form, 'title': 'تعديل الدولة', 'country': country})


@login_required
def country_delete(request, pk):
    """حذف دولة"""
    from .models import Country
    country = get_object_or_404(Country, pk=pk)
    if request.method == 'POST':
        country.delete()
        messages.success(request, 'تم حذف الدولة بنجاح')
        return redirect('core:country_list')
    return render(request, 'core/countries/delete.html', {'country': country})


# ===== إدارة المحافظات =====
@login_required
def state_list(request):
    """قائمة المحافظات"""
    from .models import State
    states = State.objects.select_related('country').all().order_by('country__name', 'name')
    return render(request, 'core/states/list.html', {'states': states})


@login_required
def states_by_country(request, country_id):
    """إرجاع المحافظات الخاصة بدولة معينة (للاستخدام في القوائم المنسدلة)"""
    from .models import State
    states = State.objects.filter(country_id=country_id, is_active=True).order_by('name')
    payload = [{'id': state.id, 'name': state.name, 'code': state.code} for state in states]
    return JsonResponse({'states': payload})


@login_required
def state_create(request):
    """إنشاء محافظة جديدة"""
    from .forms import StateForm
    if request.method == 'POST':
        form = StateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء المحافظة بنجاح')
            return redirect('core:state_list')
    else:
        form = StateForm()
    return render(request, 'core/states/form.html', {'form': form, 'title': 'إنشاء محافظة جديدة'})


@login_required
def state_edit(request, pk):
    """تعديل محافظة"""
    from .models import State
    from .forms import StateForm
    state = get_object_or_404(State, pk=pk)
    if request.method == 'POST':
        form = StateForm(request.POST, instance=state)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث المحافظة بنجاح')
            return redirect('core:state_list')
    else:
        form = StateForm(instance=state)
    return render(request, 'core/states/form.html', {'form': form, 'title': 'تعديل المحافظة', 'state': state})


@login_required
def state_delete(request, pk):
    """حذف محافظة"""
    from .models import State
    state = get_object_or_404(State, pk=pk)
    if request.method == 'POST':
        state.delete()
        messages.success(request, 'تم حذف المحافظة بنجاح')
        return redirect('core:state_list')
    return render(request, 'core/states/delete.html', {'state': state})


# ===== إدارة الصفحات =====
@login_required
def page_list(request):
    """قائمة الصفحات"""
    from .models import Page
    pages = Page.objects.select_related('parent').all().order_by('order', 'name')
    
    # إحصائيات
    active_count = pages.filter(is_active=True).count()
    menu_count = pages.filter(is_menu_item=True).count()
    parent_count = pages.filter(parent__isnull=True).count()
    
    return render(request, 'core/pages/list.html', {
        'pages': pages,
        'active_count': active_count,
        'menu_count': menu_count,
        'parent_count': parent_count,
    })


@login_required
def page_create(request):
    """إنشاء صفحة جديدة"""
    from .forms import PageForm
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء الصفحة بنجاح')
            return redirect('core:page_list')
    else:
        form = PageForm()
    return render(request, 'core/pages/form.html', {'form': form, 'title': 'إنشاء صفحة جديدة'})


@login_required
def page_edit(request, pk):
    """تعديل صفحة"""
    from .models import Page
    from .forms import PageForm
    page = get_object_or_404(Page, pk=pk)
    if request.method == 'POST':
        form = PageForm(request.POST, instance=page)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الصفحة بنجاح')
            return redirect('core:page_list')
    else:
        form = PageForm(instance=page)
    return render(request, 'core/pages/form.html', {'form': form, 'title': 'تعديل الصفحة', 'page': page})


@login_required
def page_delete(request, pk):
    """حذف صفحة"""
    from .models import Page
    page = get_object_or_404(Page, pk=pk)
    if request.method == 'POST':
        page.delete()
        messages.success(request, 'تم حذف الصفحة بنجاح')
        return redirect('core:page_list')
    return render(request, 'core/pages/delete.html', {'page': page})


# ==================== لوحة التحكم الموحدة ====================

@login_required
def unified_dashboard(request):
    """
    لوحة التحكم الموحدة للشركة + المصنع + المعارض
    تعرض نظرة شاملة على جميع العمليات
    """
    return render(request, 'core/unified_dashboard.html')


@login_required
def mrp_dashboard(request):
    """
    لوحة تحكم تخطيط موارد الإنتاج (MRP)
    """
    from core.dashboard_contexts import get_mrp_context
    context = get_mrp_context()
    return render(request, 'production/mrp_dashboard.html', context)


@login_required
def costing_dashboard(request):
    """
    لوحة تحكم التكلفة الصناعية
    """
    from core.dashboard_contexts import get_costing_context
    context = get_costing_context()
    return render(request, 'production/costing_dashboard.html', context)


@login_required
def distribution_dashboard(request):
    """
    لوحة تحكم توزيع المعارض
    """
    from core.dashboard_contexts import get_distribution_context
    context = get_distribution_context()
    return render(request, 'branches/distribution_dashboard.html', context)


@login_required
def integration_dashboard(request):
    """
    لوحة تحكم تكامل المصنع-المعارض
    """
    return render(request, 'production/integration_dashboard.html')


# ================================
# Custom Error Handlers
# ================================
def custom_404(request, exception=None):
    """Custom 404 error handler that returns JSON for API requests"""
    # Check if this is an API request
    is_api = (
        request.path.startswith('/api/') or
        'application/json' in request.headers.get('Accept', '')
    )
    
    if is_api:
        return JsonResponse({
            'success': False,
            'error': 'الصفحة المطلوبة غير موجودة',
            'status_code': 404
        }, status=404)
    
    return render(request, '404.html', {'path': request.path}, status=404)


def custom_403(request, exception=None):
    """Custom 403 error handler that returns JSON for API requests"""
    # Check if this is an API request
    is_api = (
        request.path.startswith('/api/') or
        'application/json' in request.headers.get('Accept', '')
    )
    
    if is_api:
        return JsonResponse({
            'success': False,
            'error': 'غير مصرح لك بالوصول إلى هذه الصفحة',
            'status_code': 403
        }, status=403)
    
    return render(request, '403.html', status=403)


def custom_500(request):
    """Custom 500 error handler that returns JSON for API requests"""
    # Check if this is an API request
    is_api = (
        request.path.startswith('/api/') or
        'application/json' in request.headers.get('Accept', '')
    )
    
    if is_api:
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في الخادم',
            'status_code': 500
        }, status=500)
    
    return render(request, 'errors/500.html', status=500)


# ============================================================
# صفحات التحسينات الجديدة
# ============================================================

@login_required
def enhanced_dashboard(request: HttpRequest):
    """لوحة المعلومات المحسنة مع KPIs"""
    context = {
        'page_title': 'لوحة المعلومات المحسنة',
        'page_icon': 'chart-line',
    }
    return render(request, 'dashboard/enhanced_dashboard.html', context)


@login_required
def keyboard_shortcuts(request: HttpRequest):
    """صفحة اختصارات لوحة المفاتيح"""
    context = {
        'page_title': 'اختصارات لوحة المفاتيح',
        'page_icon': 'keyboard',
    }
    return render(request, 'dashboard/keyboard_shortcuts.html', context)


@login_required
def help_page(request: HttpRequest):
    """صفحة المساعدة والدعم"""
    context = {
        'page_title': 'المساعدة والدعم',
        'page_icon': 'question-circle',
    }
    return render(request, 'dashboard/help.html', context)

@login_required
def improvements_settings(request: HttpRequest):
    """صفحة إعدادات التحسينات"""
    context = {
        'page_title': 'إعدادات التحسينات',
        'page_icon': 'sliders-h',
    }
    return render(request, 'dashboard/settings.html', context)
