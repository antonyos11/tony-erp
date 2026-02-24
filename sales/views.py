from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import connection
from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper, Value
from django.db.models.functions import Coalesce
from django.db import models
from datetime import date, timedelta
from django.utils import timezone
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext as _t  # i18n
import csv
from .models import Invoice, InvoiceItem, FieldVisit, CollectionTask, SalesReturn, SalesReturnItem, InvoicePayment
from core.models import AuditLog
from .services.payments import cancel_payment
from .utils import build_customer_statement
from .forms import FieldVisitForm
from partners.models import Customer
from inventory.models import Product, Location, Stock, PrinterConfiguration
from inventory.barcode_utils import send_to_thermal_printer
from payments.models import PaymentMethod
from decimal import Decimal, InvalidOperation
import math
import json
from django.views.decorators.http import require_POST
from .models import InvoicePaymentAllocation  # new allocation model


@login_required
def customer_list(request):
    """قائمة العملاء - redirect to partners"""
    return redirect('partners:customers_list')


@login_required
def product_lookup_barcode(request):
    """بحث منتج بالباركود أو SKU (GET ?code=). يرجع JSON للاستخدام في نموذج الفاتورة.
    يدعم أيضاً البحث الجزئي عند توفر multiple (يرجع أول مطابق)."""
    code = request.GET.get('code','').strip()
    from inventory.models import Product
    if not code:
        return JsonResponse({'success': False, 'message': _t('لا يوجد باركود')}, status=400)
    try:
        product = Product.objects.filter(Q(barcode=code) | Q(sku=code)).first()
        if not product:
            product = Product.objects.filter(Q(barcode__icontains=code) | Q(sku__icontains=code)).first()
        if not product:
            return JsonResponse({'success': False, 'message': _t('لم يتم العثور على منتج')}, status=404)
        return JsonResponse({'success': True, 'id': product.id, 'name': product.name, 'sku': product.sku, 'price': float(product.price)})
    except Exception as e:
        return JsonResponse({'success': False, 'message': _t('خطأ: %(error)s') % {'error': e}}, status=500)


@login_required
@require_POST
def invoice_item_delete(request, item_id):
    """حذف بند فاتورة عبر AJAX وإرجاع المخزون."""
    try:
        item = get_object_or_404(InvoiceItem.objects.select_related('invoice','product','location'), pk=item_id)
        invoice = item.invoice
        # استرجاع المخزون (عكس عملية التخفيض في signal)
        try:
            stock = Stock.objects.get(product=item.product, location=item.location)
            stock.quantity += item.quantity
            stock.save(update_fields=['quantity'])
        except Stock.DoesNotExist:
            pass
        item.delete()
        return JsonResponse({'success': True, 'message': _t('تم الحذف'), 'invoice_totals': {'total': float(invoice.total), 'remaining': float(invoice.remaining)}})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def sales_dashboard(request):
    """لوحة المبيعات: روابط سريعة للأقسام الجديدة وإحصائيات بسيطة."""
    from showrooms.mixins import get_active_showroom_id, is_all_showrooms_mode
    
    active_showroom_id = get_active_showroom_id(request)
    show_all = is_all_showrooms_mode(request)
    
    # فلترة حسب الفرع - ملاحظة: Invoice لا يحتوي على حقل showroom حالياً
    invoices_qs = Invoice.objects.all()
    # تم تعطيل فلترة الفرع لأن Invoice model لا يدعم ذلك
    
    invoice_items_qs = InvoiceItem.objects.filter(invoice__date=date.today())
    # تم تعطيل فلترة الفرع لأن Invoice model لا يدعم ذلك
    
    customers_qs = Customer.objects.all()
    
    stats = {
        'invoices': invoices_qs.count(),
        'customers': customers_qs.count(),
        'today_sales': invoice_items_qs.aggregate(total=Sum('price'))['total'] or 0,
    }
    return render(request, 'sales/dashboard.html', {'stats': stats, 'title': _t('لوحة المبيعات')})


@login_required
def field_sales(request):
    """المبيعات الخارجية: سجل الزيارات/العقود (هيكل مبدئي)."""
    qs = FieldVisit.objects.select_related('employee', 'customer').all()
    # فلاتر بسيطة
    customer = request.GET.get('customer')
    if customer:
        qs = qs.filter(customer__name__icontains=customer)
    outcome = request.GET.get('outcome')
    if outcome:
        qs = qs.filter(outcome=outcome)
    # CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="field_visits.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Date', 'Employee', 'Customer', 'Subject', 'Outcome', 'Next Action'])
        for v in qs:
            writer.writerow([
                v.visit_date,
                getattr(v.employee, 'arabic_name', '') if v.employee else '',
                v.customer.name if v.customer else '',
                v.subject,
                v.get_outcome_display(),
                v.next_action_date or '',
            ])
        return response
    return render(request, 'sales/field_sales.html', {
        'title': _t('المبيعات الخارجية'),
        'visits': qs,
    })


@login_required
def field_visit_create(request):
    """إضافة زيارة ميدانية جديدة"""
    if request.method == 'POST':
        form = FieldVisitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _t('تم حفظ الزيارة بنجاح'))
            return redirect('sales:field_sales')
        else:
            messages.error(request, _t('الرجاء تصحيح الأخطاء أدناه'))
    else:
        form = FieldVisitForm()
    return render(request, 'sales/field_visit_form.html', {'form': form, 'title': _t('إضافة زيارة ميدانية')})


@login_required
def field_visit_edit(request, pk):
    visit = get_object_or_404(FieldVisit, pk=pk)
    if request.method == 'POST':
        form = FieldVisitForm(request.POST, instance=visit)
        if form.is_valid():
            form.save()
            messages.success(request, _t('تم تحديث الزيارة'))
            return redirect('sales:field_sales')
        else:
            messages.error(request, _t('الرجاء تصحيح الأخطاء أدناه'))
    else:
        form = FieldVisitForm(instance=visit)
    return render(request, 'sales/field_visit_form.html', {'form': form, 'title': _t('تعديل زيارة')})


@login_required
def location_tracking(request):
    """صفحة تتبع المندوبين والمواقع المباشرة"""
    return render(request, 'sales/location_tracking_new.html', {
        'title': _t('تتبع المواقع المباشر'),
    })


@login_required
def rep_mobile_tracker(request):
    """صفحة المندوب لإرسال موقعه تلقائياً - مصممة للموبايل"""
    return render(request, 'sales/rep_mobile_tracker.html', {
        'title': _t('تتبع موقعي'),
    })


@login_required
def tracking_api(request):
    """API لجلب بيانات تتبع المندوبين"""
    from hr.models import Employee
    from datetime import timedelta
    
    # جلب الزيارات الأخيرة مع مواقعها
    today = date.today()
    recent_cutoff = timezone.now() - timedelta(hours=24)
    
    # جلب الموظفين النشطين مع آخر مواقعهم
    employees = Employee.objects.filter(status='active').select_related('user')
    
    users_data = []
    active_count = 0
    total_locations = 0
    
    for emp in employees:
        # جلب آخر زيارة لهذا الموظف مع موقع
        last_visit = FieldVisit.objects.filter(
            employee=emp,
            latitude__isnull=False,
            longitude__isnull=False
        ).order_by('-created_at').first()
        
        if last_visit:
            # التحقق إذا كان نشط (زيارة في آخر ساعة)
            is_online = last_visit.created_at >= (timezone.now() - timedelta(hours=1)) if last_visit.created_at else False
            
            users_data.append({
                'id': emp.id,
                'name': emp.arabic_name or f"{emp.first_name} {emp.last_name}" or f"موظف {emp.id}",
                'latitude': float(last_visit.latitude) if last_visit.latitude else None,
                'longitude': float(last_visit.longitude) if last_visit.longitude else None,
                'is_online': is_online,
                'customer': last_visit.customer.name if last_visit.customer else None,
                'last_seen': last_visit.created_at.strftime('%H:%M') if last_visit.created_at else None,
                'visit_id': last_visit.id,
            })
            
            if is_online:
                active_count += 1
            total_locations += 1
    
    return JsonResponse({
        'success': True,
        'users': users_data,
        'active_users': active_count,
        'total_locations': total_locations,
        'updated_at': timezone.now().isoformat(),
    })


@login_required
@require_POST
def update_location(request):
    """API لتحديث موقع المندوب"""
    import json
    
    try:
        data = json.loads(request.body) if request.body else {}
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        
        if not latitude or not longitude:
            return JsonResponse({
                'success': False,
                'message': _t('الموقع غير صالح')
            }, status=400)
        
        # البحث عن الموظف المرتبط بالمستخدم
        from hr.models import Employee
        employee = Employee.objects.filter(user=request.user).first()
        
        if not employee:
            return JsonResponse({
                'success': False,
                'message': _t('لا يوجد ملف موظف مرتبط')
            }, status=400)
        
        # إنشاء أو تحديث زيارة بالموقع
        visit = FieldVisit.objects.create(
            employee=employee,
            visit_date=date.today(),
            latitude=latitude,
            longitude=longitude,
            location_accuracy=accuracy,
            check_in_time=timezone.now(),
            subject=_t('تحديث موقع تلقائي'),
            outcome='follow_up',
        )
        
        return JsonResponse({
            'success': True,
            'message': _t('تم تحديث الموقع'),
            'visit_id': visit.id,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def indoor_sales(request):
    """المبيعات الداخلية: نقطة بيع/مكالمات هاتفية (إظهار فواتير اليوم كتجربة)."""
    qs = (Invoice.objects.select_related('customer')
           .only('id', 'number', 'customer__name', 'date', 'discount', 'paid')
           .filter(date=date.today()).order_by('-id'))
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="indoor_sales_today.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Number', 'Customer', 'Date', 'Total', 'Paid'])
        for inv in qs:
            writer.writerow([inv.number, getattr(inv.customer, 'name', ''), inv.date, inv.total, inv.paid])
        return response
    return render(request, 'sales/indoor_sales.html', {'title': _t('المبيعات الداخلية'), 'invoices': qs})


@login_required
def key_accounts(request):
    """إدارة حسابات العملاء الرئيسية: قائمة ورعاية كبار العملاء."""
    key_customers = Customer.objects.filter(is_key_account=True)
    return render(request, 'sales/key_accounts.html', {'title': _t('إدارة حسابات العملاء'), 'key_customers': key_customers})


@login_required
def ecommerce_sales(request):
    """مبيعات أونلاين: عينة من المبيعات الأخيرة كتمثيل."""
    recent = (Invoice.objects.select_related('customer')
               .only('id', 'number', 'customer__name', 'date', 'discount')
               .order_by('-id')[:20])
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="ecommerce_sales_sample.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Number', 'Customer', 'Date', 'Total'])
        for inv in recent:
            writer.writerow([inv.number, getattr(inv.customer, 'name', ''), inv.date, inv.total])
        return response
    return render(request, 'sales/ecommerce_sales.html', {'title': _t('مبيعات أونلاين'), 'recent': recent})


@login_required
def pricing_offers(request):
    """التسعير والعروض: عرض قائمة منتجات مع الأسعار الحالية (تمثيلي) + CSV."""
    from inventory.models import Product
    qs = Product.objects.all()
    promo_flag = request.GET.get('promo') == '1'
    if promo_flag:
        # تصفية المنتجات التي لها عرض فعّال فعلاً (سعر فعلي مختلف)
        # لا يمكن الفلترة مباشرة على effective_price لأنه property، فنطبق شروط الحقول
        from django.utils import timezone
        today = timezone.now().date()
        qs = qs.filter(is_promo_active=True).filter(
            (
                (models.Q(promo_price__isnull=False) & models.Q(promo_price__gt=0)) |
                models.Q(promo_percent__gt=0)
            ) & (
                (models.Q(promo_start__isnull=True) | models.Q(promo_start__lte=today)) &
                (models.Q(promo_end__isnull=True) | models.Q(promo_end__gte=today))
            )
        )
    products = qs.order_by('name')[:200]
    if request.method == 'POST' and request.POST.get('update_promo'):
        try:
            pid = int(request.POST.get('product_id'))
            p = Product.objects.get(pk=pid)
            p.is_promo_active = bool(request.POST.get('is_promo_active'))
            from decimal import Decimal, InvalidOperation
            raw_pct = (request.POST.get('promo_percent') or '0').strip()
            raw_price = (request.POST.get('promo_price') or '').strip()
            try:
                p.promo_percent = Decimal(raw_pct or '0')
            except (InvalidOperation, TypeError):
                pass
            try:
                p.promo_price = Decimal(raw_price) if raw_price else None
            except (InvalidOperation, TypeError):
                p.promo_price = None
            p.promo_start = request.POST.get('promo_start') or None
            p.promo_end = request.POST.get('promo_end') or None
            p.save()
            from django.contrib import messages
            messages.success(request, _t('تم تحديث العرض للمنتج %(name)s') % {'name': p.name})
            return redirect('sales:pricing_offers')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, _t('فشل التحديث: %(error)s') % {'error': e})
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="price_list.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['SKU', 'Name', 'Price', 'Cost'])
        for p in products:
            writer.writerow([p.sku, p.name, p.effective_price, p.cost])
        return response
    return render(request, 'sales/pricing_offers.html', {
        'title': _t('التسعير والعروض'),
        'products': products,
        'promo_flag': promo_flag,
    })


@login_required
def followup_collection(request):
    """المتابعة والتحصيل: متابعة رضا العملاء والتحصيل (مبدئي)."""
    qs = CollectionTask.objects.select_related('customer', 'invoice', 'assigned_to').all()
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    # CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="collection_tasks.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Customer', 'Invoice', 'Due Date', 'Amount Due', 'Status', 'Assigned To'])
        for t in qs:
            writer.writerow([
                t.customer.name,
                t.invoice.number if t.invoice else '',
                t.due_date,
                t.amount_due,
                t.get_status_display(),
                getattr(t.assigned_to, 'arabic_name', '') if t.assigned_to else '',
            ])
        return response
    return render(request, 'sales/followup_collection.html', {'title': _t('المتابعة والتحصيل'), 'tasks': qs})


@login_required
@login_required
def sales_reporting_analytics(request):
    """تقارير المبيعات والتحليلات."""
    from django.db.models import Sum, Count, F
    from django.utils import timezone
    import json
    
    # Period handling
    period = request.GET.get('period', 'month')
    today = timezone.now().date()
    
    if period == 'today':
        start_date = today
        prev_start = today - timedelta(days=1)
        prev_end = prev_start
    elif period == 'week':
        start_date = today - timedelta(days=7)
        prev_start = start_date - timedelta(days=7)
        prev_end = start_date - timedelta(days=1)
    elif period == 'year':
        start_date = today - timedelta(days=365)
        prev_start = start_date - timedelta(days=365)
        prev_end = start_date - timedelta(days=1)
    else: # month default
        start_date = today - timedelta(days=30)
        prev_start = start_date - timedelta(days=30)
        prev_end = start_date - timedelta(days=1)
    
    # 1. KPIs
    current_invoices = Invoice.objects.filter(date__gte=start_date, is_deleted=False)
    prev_invoices = Invoice.objects.filter(date__gte=prev_start, date__lte=prev_end, is_deleted=False)
    
    # Revenue
    current_revenue = current_invoices.aggregate(total=Sum('cached_total'))['total'] or 0
    prev_revenue = prev_invoices.aggregate(total=Sum('cached_total'))['total'] or 0
    revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 100
    
    # Orders
    current_orders = current_invoices.count()
    prev_orders = prev_invoices.count()
    orders_change = ((current_orders - prev_orders) / prev_orders * 100) if prev_orders else 100
    
    # Customers
    active_customers = Customer.objects.filter(invoices__date__gte=start_date).distinct().count()
    prev_active = Customer.objects.filter(invoices__date__gte=prev_start, invoices__date__lte=prev_end).distinct().count()
    customers_change = ((active_customers - prev_active) / prev_active * 100) if prev_active else 100
    
    # Returns (Assuming SalesReturn model exists and linked)
    # Placeholder for returns if model not imported
    total_returns = 0
    returns_change = 0
    try:
        from .models import SalesReturn
        current_returns = SalesReturn.objects.filter(date__gte=start_date).aggregate(t=Sum('total'))['t'] or 0
        prev_returns_val = SalesReturn.objects.filter(date__gte=prev_start, date__lte=prev_end).aggregate(t=Sum('total'))['t'] or 0
        total_returns = current_returns
        returns_change = ((current_returns - prev_returns_val) / prev_returns_val * 100) if prev_returns_val else 0
    except Exception:
        pass

    kpis = {
        'total_revenue': current_revenue,
        'revenue_change': round(revenue_change, 1),
        'total_orders': current_orders,
        'orders_change': round(orders_change, 1),
        'active_customers': active_customers,
        'customers_change': round(customers_change, 1),
        'total_returns': total_returns,
        'returns_change': round(returns_change, 1),
    }

    # 2. Charts Data (Last 30 days)
    chart_labels = []
    chart_data = []
    
    # Prepare date range for chart
    chart_start = today - timedelta(days=29) if period == 'month' else start_date
    
    # Aggregate daily sales
    daily_sales = Invoice.objects.filter(date__gte=chart_start, is_deleted=False)\
        .values('date')\
        .annotate(total=Sum('cached_total'))\
        .order_by('date')
    
    sales_dict = {str(d['date']): d['total'] for d in daily_sales}
    
    current_d = chart_start
    while current_d <= today:
        d_str = str(current_d)
        chart_labels.append(current_d.strftime('%m-%d'))
        chart_data.append(float(sales_dict.get(d_str, 0)))
        current_d += timedelta(days=1)
        
    # Payment Methods
    # Assuming invoices have a payment method or paid amount distribution
    # Simplified: Paid vs Unpaid
    paid_amount = current_invoices.aggregate(sum=Sum('paid'))['sum'] or 0
    unpaid_amount = (current_revenue - paid_amount) if current_revenue else 0
    payment_data = [float(paid_amount), float(unpaid_amount), 0, 0] # Cash, Credit, Card, Transfer placeholder

    # 3. Top Lists
    # Top Products
    top_products = InvoiceItem.objects.filter(invoice__in=current_invoices)\
        .values('product__name')\
        .annotate(
            qty_sold=Sum('quantity'),
            revenue=Sum('price')
        )\
        .order_by('-revenue')[:5]
    
    top_products_list = [{'name': p['product__name'], 'qty_sold': p['qty_sold'], 'revenue': p['revenue']} for p in top_products]

    # Top Customers
    top_customers = current_invoices.values('customer__name')\
        .annotate(
            orders_count=Count('id'),
            total_spent=Sum('cached_total')
        )\
        .order_by('-total_spent')[:5]
        
    top_customers_list = []
    for c in top_customers:
        name = c['customer__name'] or 'عميل'
        top_customers_list.append({
            'name': name,
            'orders_count': c['orders_count'],
            'total_spent': c['total_spent']
        })

    # Top Reps - Invoice model does not have created_by; provide empty placeholder
    top_reps_list = []

    context = {
        'title': _t('التقارير والتحليل'),
        'kpis': kpis,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'payment_data': payment_data,
        'top_products': top_products_list,
        'top_customers': top_customers_list,
        'top_reps': top_reps_list,
    }
    return render(request, 'sales/reporting_analytics.html', context)


@login_required
def sales_coordination(request):
    """التنسيق مع الأقسام: روابط وإجراءات مع التسويق/المخازن/خدمة العملاء."""
    return render(request, 'sales/coordination.html', {'title': _t('التنسيق مع باقي الأقسام')})

@login_required
def invoice_list(request, template=None):
    """قائمة الفواتير مع فلاتر متقدمة محسّنة بالأٌنوتيشن (بدون تحويل queryset إلى قائمة)."""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    invoices = (Invoice.objects.select_related('customer', 'payment_method')
                .filter(is_deleted=False))
    # مجموع البنود = Sum(quantity * price) مع تحديد نوع الحقل لتفادي خطأ دمج الأنواع (Integer + Decimal)
    invoices = invoices.annotate(
        subtotal=Coalesce(
            Sum(
                F('items__quantity') * F('items__price'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        )
    )
    invoices = invoices.annotate(
        total_amount=ExpressionWrapper(F('subtotal') - F('discount'), output_field=DecimalField(max_digits=12, decimal_places=2))
    )
    search = request.GET.get('search','').strip()
    if search:
        invoices = invoices.filter(Q(number__icontains=search) | Q(customer__name__icontains=search))
    date_from = request.GET.get('date_from'); date_to = request.GET.get('date_to')
    if date_from: invoices = invoices.filter(date__gte=date_from)
    if date_to: invoices = invoices.filter(date__lte=date_to)
    pm = request.GET.get('payment_method')
    if pm: invoices = invoices.filter(payment_method_id=pm)
    status = request.GET.get('status')
    if status == 'paid':
        invoices = invoices.filter(total_amount__lte=F('paid'))
    elif status == 'partial':
        invoices = invoices.filter(paid__gt=0, paid__lt=F('total_amount'))
    elif status == 'unpaid':
        invoices = invoices.filter(paid=0)
    tax_flag = request.GET.get('taxed')  # '1' أو '0'
    if tax_flag == '1':
        invoices = invoices.filter(is_tax_inclusive=True)
    elif tax_flag == '0':
        invoices = invoices.filter(is_tax_inclusive=False)
    total_min = request.GET.get('total_min'); total_max = request.GET.get('total_max')
    if total_min:
        try: invoices = invoices.filter(total_amount__gte=Decimal(total_min))
        except Exception: pass
    if total_max:
        try: invoices = invoices.filter(total_amount__lte=Decimal(total_max))
        except Exception: pass
    
    # ترتيب الفواتير
    invoices = invoices.order_by('-date', '-id')
    
    # Pagination
    page_size = request.GET.get('page_size', '50')
    try:
        page_size = int(page_size)
        if page_size not in [25, 50, 100, 200]:
            page_size = 50
    except:
        page_size = 50
    
    paginator = Paginator(invoices, page_size)
    page = request.GET.get('page', '1')
    
    try:
        invoices_page = paginator.page(page)
    except PageNotAnInteger:
        invoices_page = paginator.page(1)
    except EmptyPage:
        invoices_page = paginator.page(paginator.num_pages)
    
    if request.GET.get('debug') == '1':
        from django.db import reset_queries
        reset_queries(); list(invoices_page); query_count=len(connection.queries)
    else:
        query_count=None
    from payments.models import PaymentMethod
    from django.db.models import Count
    
    # حساب الإحصائيات
    all_invoices = Invoice.objects.filter(is_deleted=False)
    stats = {
        'total_count': all_invoices.count(),
        'paid_count': all_invoices.filter(paid__gte=F('cached_total') - F('discount')).count(),
        'pending_count': all_invoices.filter(paid__lt=F('cached_total') - F('discount')).count(),
        'total_amount': all_invoices.aggregate(total=Sum('cached_total'))['total'] or 0,
    }
    
    context = {
        'invoices': invoices_page,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'query_count': query_count,
        'payment_methods': PaymentMethod.objects.filter(is_active=True).order_by('display_order','name')[:200],
        'selected_payment_method': pm,
        'status': status,
        'tax_flag': tax_flag,
        'total_min': total_min,
        'total_max': total_max,
        'stats': stats,
        'page_size': page_size,
    }
    
    # استخدام التصميم الجديد كافتراضي
    template_name = 'sales/invoice_list_new.html' if template == 'old' else 'sales/invoice_list_beautiful.html'
    return render(request, template_name, context)


@login_required
def invoice_create(request, template=None):
    """Create new invoice with enhanced features"""
    # Get company info for tax invoice
    try:
        from core.models import Company
        company = Company.objects.first()
        company_vat_rate = float(company.default_vat_rate) if company and company.default_vat_rate else 14.0
        company_tax_id = company.tax_id if company else ''
    except Exception:
        company_vat_rate = 14.0
        company_tax_id = ''

    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        due_date = request.POST.get('due_date') or None
        action = request.POST.get('action', 'save')  # 'save' or 'save_and_continue'
        
        from decimal import Decimal, InvalidOperation
        raw_discount = request.POST.get('discount', '0').strip() or '0'
        try:
            discount = Decimal(raw_discount)
        except (InvalidOperation, TypeError):
            discount = Decimal('0')
            
        payment_method_id = request.POST.get('payment_method') or None
        payment_reference = request.POST.get('payment_reference', '').strip()
        is_tax_inclusive = bool(request.POST.get('is_tax_inclusive'))
        is_withholding_applied = bool(request.POST.get('is_withholding_applied'))

        # --- New optional checkbox fields ---
        is_tax_invoice = bool(request.POST.get('is_tax_invoice'))
        enable_shipping = bool(request.POST.get('enable_shipping'))
        enable_extra_discount = bool(request.POST.get('enable_extra_discount'))
        enable_previous_balance = bool(request.POST.get('enable_previous_balance'))

        def _dec(field, default='0'):
            raw = request.POST.get(field, default).strip() or default
            try:
                return Decimal(raw)
            except (InvalidOperation, TypeError):
                return Decimal(default)

        tax_rate = _dec('tax_rate')
        tax_amount = _dec('tax_amount')
        shipping_cost = _dec('shipping_cost') if enable_shipping else Decimal('0')
        extra_discount_val = _dec('extra_discount') if enable_extra_discount else Decimal('0')
        previous_balance = _dec('previous_balance') if enable_previous_balance else Decimal('0')

        # التحقق من وجود العميل قبل المتابعة
        if not customer_id or not str(customer_id).strip():
            messages.error(request, _t('الرجاء تحديد العميل أولاً'))
            customers = Customer.objects.all().order_by('name')
            payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('display_order', 'name')
            products = Product.objects.all()
            locations = Location.objects.all()
            products_json = json.dumps([
                {'id': p.id, 'name': p.name, 'price': float(p.price) if p.price else 0, 'sku': p.sku or ''}
                for p in products
            ], ensure_ascii=False)
            context = {
                'customers': customers,
                'payment_methods': payment_methods,
                'products': products,
                'products_json': products_json,
                'locations': locations,
            }
            return render(request, 'sales/invoice_form_enhanced.html', context)

        try:
            customer = Customer.objects.filter(pk=customer_id).first()
            if not customer:
                messages.error(request, _t('العميل المحدد غير موجود. الرجاء اختيار عميل صحيح.'))
                customers = Customer.objects.all().order_by('name')
                payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('display_order', 'name')
                products = Product.objects.all()
                locations = Location.objects.all()
                products_json = json.dumps([
                    {'id': p.id, 'name': p.name, 'price': float(p.price) if p.price else 0, 'sku': p.sku or ''}
                    for p in products
                ], ensure_ascii=False)
                context = {
                    'customers': customers,
                    'payment_methods': payment_methods,
                    'products': products,
                    'products_json': products_json,
                    'locations': locations,
                }
                return render(request, 'sales/invoice_form_enhanced.html', context)

            # Generate new unique invoice number
            import random
            max_attempts = 10
            for attempt in range(max_attempts):
                last_invoice = Invoice.objects.order_by('-id').first()
                if last_invoice:
                    try:
                        last_number = int(last_invoice.number.split('-')[-1])
                        new_number = f"INV-{str(last_number + 1).zfill(6)}"
                    except (ValueError, IndexError):
                        # If last number is not parseable, use random
                        new_number = f"INV-{str(random.randint(100000, 999999))}"
                else:
                    new_number = "INV-000001"
                
                # Check if number exists
                if not Invoice.objects.filter(number=new_number).exists():
                    break
                else:
                    # If exists, add timestamp suffix on last attempt
                    if attempt == max_attempts - 1:
                        from django.utils import timezone
                        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                        new_number = f"INV-{timestamp}"
            
            # Create invoice
            invoice = Invoice.objects.create(
                number=new_number,
                customer=customer,
                due_date=due_date,
                discount=discount,
                is_tax_inclusive=is_tax_inclusive,
                is_withholding_applied=is_withholding_applied,
                payment_method=PaymentMethod.objects.filter(pk=payment_method_id).first() if payment_method_id else None,
                payment_reference=payment_reference,
                # Optional checkbox fields
                is_tax_invoice=is_tax_invoice,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                enable_shipping=enable_shipping,
                shipping_cost=shipping_cost,
                enable_extra_discount=enable_extra_discount,
                extra_discount=extra_discount_val,
                enable_previous_balance=enable_previous_balance,
                previous_balance=previous_balance,
            )
            
            # Process invoice items from JSON
            items_json_str = request.POST.get('items_json', '[]')
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'Invoice {new_number}: items_json = {items_json_str[:500]}')
            try:
                items_data = json.loads(items_json_str)
                logger.info(f'Invoice {new_number}: parsed {len(items_data)} items')
                items_created = 0
                for item_data in items_data:
                    product_id = item_data.get('product_id')
                    location_id = item_data.get('location_id')
                    
                    if product_id:
                        product = Product.objects.get(pk=product_id)
                        
                        # Get location - use provided or get first available
                        if location_id:
                            location = Location.objects.filter(pk=location_id).first()
                        if not location_id or not location:
                            location = Location.objects.first()
                        
                        # Skip if no location available
                        if not location:
                            messages.warning(request, _t('تحذير: لم يتم العثور على موقع للمنتج %(product)s') % {'product': product.name})
                            continue
                        
                        qty = item_data.get('quantity', 1)
                        # Convert to int for PositiveIntegerField (round up fractional)
                        qty_int = max(1, int(round(float(qty))))
                        
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            product=product,
                            location=location,
                            quantity=qty_int,
                            price=Decimal(str(item_data.get('price', 0))),
                        )
                        items_created += 1
                logger.info(f'Invoice {new_number}: created {items_created} items successfully')
                if items_created == 0 and len(items_data) > 0:
                    messages.warning(request, _t('تحذير: لم يتم إضافة أي أصناف للفاتورة'))
            except (json.JSONDecodeError, Product.DoesNotExist, KeyError, ValueError) as e:
                logger.error(f'Invoice {new_number}: error processing items: {e}')
                messages.warning(request, _t('تحذير: بعض العناصر لم يتم إضافتها: %(error)s') % {'error': str(e)})
            
            # Recalculate invoice totals - refresh from DB first because
            # post_save signals on InvoiceItem already updated cached_total atomically
            invoice.refresh_from_db()
            
            success_message = _t('تم إنشاء الفاتورة رقم %(num)s بنجاح') % {'num': new_number}
            messages.success(request, success_message)
            
            # Handle different actions
            if action == 'save_and_print':
                return redirect('sales:invoice_direct_print_a4', pk=invoice.pk)
            elif action == 'save_and_continue':
                return redirect('sales:invoice_detail', pk=invoice.pk)
            else:
                return redirect('sales:invoice_detail', pk=invoice.pk)
                
        except Exception as e:
            messages.error(request, _t('خطأ في إنشاء الفاتورة: %(error)s') % {'error': e})
    
    # Prepare context for GET request
    customers = Customer.objects.all().order_by('name')
    payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('display_order', 'name')
    products = Product.objects.all()
    locations = Location.objects.all()
    
    # Prepare products as JSON for JavaScript
    products_json = json.dumps([
        {'id': p.id, 'name': p.name, 'price': float(p.price) if p.price else 0, 'sku': p.sku or ''}
        for p in products
    ], ensure_ascii=False)
    
    context = {
        'customers': customers,
        'payment_methods': payment_methods,
        'products': products,
        'products_json': products_json,
        'locations': locations,
        'today': date.today().strftime('%Y-%m-%d'),
        'company_vat_rate': str(company_vat_rate).replace(',', '.'),
        'company_tax_id': company_tax_id,
    }
    
    # استخدام التصميم المحسّن إذا تم طلبه
    if template == 'enhanced':
        return render(request, 'sales/invoice_form_enhanced.html', context)
    
    # استخدام التصميم المحسّن كافتراضي
    return render(request, 'sales/invoice_form_enhanced.html', context)


@login_required
def invoice_detail(request, pk, template=None):
    """Invoice detail view with ability to add items"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        product_id = request.POST.get('product')
        location_id = request.POST.get('location')
        from decimal import Decimal, InvalidOperation
        try:
            quantity = int(request.POST.get('quantity', 0))
        except (TypeError, ValueError):
            quantity = 0
        raw_price = request.POST.get('price', '0').strip() or '0'
        try:
            price = Decimal(raw_price)
        except (InvalidOperation, TypeError):
            price = Decimal('0')
        if quantity <= 0:
            messages.error(request, _t('كمية غير صالحة'))
            if template == 'beautiful':
                return redirect('sales:invoice_detail_beautiful', pk=pk)
            return redirect('sales:invoice_detail', pk=pk)
        try:
            product = get_object_or_404(Product, pk=product_id)
            location = get_object_or_404(Location, pk=location_id)
            stock = Stock.objects.filter(product=product, location=location).first()
            
            # التحقق من المخزون مع السماح بالإضافة حتى لو كان صفر
            available_qty = stock.quantity if stock else 0
            
            if available_qty < quantity:
                messages.warning(request, _t('تحذير: المخزون المتاح %(available)s فقط من %(product)s. تم الإضافة بكمية %(qty)s (سيظهر مخزون سالب)') % {
                    'available': available_qty,
                    'product': product.name,
                    'qty': quantity
                })
            
            # إضافة المنتج للفاتورة حتى لو كان المخزون غير كافي
            InvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                location=location,
                quantity=quantity,
                price=price
            )
            
            if available_qty >= quantity:
                messages.success(request, _t('تم إضافة %(product)s للفاتورة') % {'product': product.name})
            else:
                messages.info(request, _t('تم إضافة %(product)s للفاتورة (يرجى تحديث المخزون لاحقاً)') % {'product': product.name})
        except Exception as e:
            messages.error(request, _t('خطأ في إضافة المنتج: %(error)s') % {'error': e})
        
        if template == 'beautiful':
            return redirect('sales:invoice_detail_beautiful', pk=pk)
        return redirect('sales:invoice_detail', pk=pk)
    products = Product.objects.all()
    locations = Location.objects.all()
    # Returns related data
    if hasattr(invoice, 'salesreturn_set'):
        sales_returns = list(invoice.salesreturn_set.all().order_by('-id'))
    else:
        sales_returns = []
    returned_qty_map = {}
    has_returnable_items = True
    try:
        from django.db.models import Sum
        rows = (SalesReturnItem.objects
                .filter(invoice_item__invoice=invoice)
                .values('invoice_item_id')
                .annotate(qty=Sum('quantity')))
        returned_qty_map = {r['invoice_item_id']: r['qty'] or 0 for r in rows}
        # Determine if there is at least one item still returnable
        inv_items = list(getattr(invoice, 'items', []).all())  # type: ignore[attr-defined]
        if inv_items:
            has_returnable_items = any((getattr(it, 'quantity', 0) - returned_qty_map.get(getattr(it, 'id', None), 0)) > 0 for it in inv_items)
            # Add return info to each item for template
            for it in inv_items:
                it.returned_qty = returned_qty_map.get(it.id, 0)
                it.remaining_qty = it.quantity - it.returned_qty
    except Exception:
        pass
    # جلب بيانات الشركة
    from core.models import Company
    company = Company.objects.first()
    
    context = {
        'invoice': invoice,
        'products': products,
        'locations': locations,
        'sales_returns': sales_returns,
        'returned_qty_map': returned_qty_map,
        'has_returnable_items': has_returnable_items,
        'company': company,
    }
    
    # استخدام التصميم الجديد كافتراضي
    template_name = 'sales/invoice_detail_new.html' if template == 'old' else 'sales/invoice_detail_beautiful.html'
    return render(request, template_name, context)


from django.db import transaction

@login_required
@require_POST
def invoice_post_accounting(request, pk):
    """ترحيل الفاتورة محاسبياً - إنشاء قيد محاسبي"""
    from sales.services.accounting_integration import post_invoice_to_accounting
    
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if invoice.is_posted and invoice.journal_entry:
        messages.warning(request, 'تم ترحيل هذه الفاتورة محاسبياً مسبقاً')
        return redirect('sales:invoice_detail', pk=pk)
    
    if invoice.is_deleted:
        messages.error(request, 'لا يمكن ترحيل فاتورة محذوفة')
        return redirect('sales:invoice_detail', pk=pk)
    
    try:
        with transaction.atomic():
            je = post_invoice_to_accounting(invoice, request.user)
            if je:
                invoice.journal_entry = je
                invoice.is_posted = True
                invoice.save(update_fields=['journal_entry', 'is_posted'])
                messages.success(request, f'تم ترحيل الفاتورة محاسبياً - قيد رقم {je.id}')
            else:
                messages.warning(request, 'لم يتم إنشاء قيد محاسبي (الفاتورة قد تكون بقيمة صفر)')
    except ValueError as e:
        messages.error(request, f'خطأ في الإعدادات المحاسبية: {str(e)}')
    except Exception as e:
        messages.error(request, f'خطأ في ترحيل الفاتورة: {str(e)}')
    
    return redirect('sales:invoice_detail', pk=pk)

@login_required
def sales_return_create(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                last = SalesReturn.objects.order_by('-id').first()
                seq = (last.id + 1) if last else 1
                sret = SalesReturn.objects.create(number=f"SR-{seq:06d}", invoice=invoice)
                for it in invoice.items.all():
                    qty = int(request.POST.get(f'item_{it.id}', 0))
                    if qty > 0:
                        if qty > it.quantity:
                            raise ValueError(_t('كمية المرتجع أكبر من المباعة'))
                        sritem = SalesReturnItem.objects.create(sales_return=sret, invoice_item=it, quantity=qty)
                        sritem.apply_stock()
                messages.success(request, _t('تم إنشاء مرتجع البيع %(num)s') % {'num': sret.number})
                return redirect('sales:sales_return_detail', pk=sret.pk)
        except Exception as e:
            messages.error(request, _t('خطأ في إنشاء مرتجع البيع: %(error)s') % {'error': e})
    return render(request, 'sales/sales_return_form.html', {'invoice': invoice})


@login_required
def sales_return_detail(request, pk):
    sret = get_object_or_404(SalesReturn, pk=pk)
    return render(request, 'sales/sales_return_detail.html', {'sret': sret})

@login_required
def sales_return_start(request):
    """اختيار فاتورة لإنشاء مرتجع بيع.

    يسمح بالبحث برقم الفاتورة أو اسم العميل، ثم إعادة التوجيه لنموذج المرتجع.
    """
    q = request.GET.get('q','').strip()
    date_from = request.GET.get('date_from') or ''
    date_to = request.GET.get('date_to') or ''
    invoices = Invoice.objects.select_related('customer').filter(is_deleted=False)
    if q:
        invoices = invoices.filter(Q(number__icontains=q) | Q(customer__name__icontains=q))
    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)
    invoices = invoices.order_by('-id')[:100]
    if request.method == 'POST':
        inv_id = request.POST.get('invoice_id')
        if inv_id and inv_id.isdigit():
            return redirect('sales:sales_return_create', invoice_id=int(inv_id))
        messages.error(request, _('يرجى اختيار فاتورة صالحة'))
    return render(request, 'sales/sales_return_start.html', {'invoices': invoices, 'q': q, 'date_from': date_from, 'date_to': date_to})


@login_required
def invoice_edit(request, pk):
    """Edit invoice – full-featured form matching the create page"""
    invoice = get_object_or_404(Invoice, pk=pk)

    # Company info for tax
    try:
        from core.models import Company
        company = Company.objects.first()
        company_vat_rate = float(company.default_vat_rate) if company and company.default_vat_rate else 14.0
        company_tax_id = company.tax_id if company else ''
    except Exception:
        company_vat_rate = 14.0
        company_tax_id = ''

    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        due_date = request.POST.get('due_date') or None
        from decimal import Decimal, InvalidOperation
        raw_discount = request.POST.get('discount', '0').strip() or '0'
        raw_paid = request.POST.get('paid', '0').strip() or '0'
        try:
            discount = Decimal(raw_discount)
        except (InvalidOperation, TypeError):
            discount = Decimal('0')
        try:
            paid = Decimal(raw_paid)
        except (InvalidOperation, TypeError):
            paid = Decimal('0')
        payment_method_id = request.POST.get('payment_method') or None
        payment_reference = request.POST.get('payment_reference', '').strip()
        bank_name = (request.POST.get('bank_name') or '').strip()
        bank_account = (request.POST.get('bank_account') or '').strip()

        # New optional checkbox fields
        is_tax_invoice = bool(request.POST.get('is_tax_invoice'))
        enable_shipping = bool(request.POST.get('enable_shipping'))
        enable_extra_discount = bool(request.POST.get('enable_extra_discount'))
        enable_previous_balance = bool(request.POST.get('enable_previous_balance'))

        def _dec(field, default='0'):
            raw = request.POST.get(field, default).strip() or default
            try:
                return Decimal(raw)
            except (InvalidOperation, TypeError):
                return Decimal(default)

        tax_rate = _dec('tax_rate')
        tax_amount = _dec('tax_amount')
        shipping_cost = _dec('shipping_cost') if enable_shipping else Decimal('0')
        extra_discount_val = _dec('extra_discount') if enable_extra_discount else Decimal('0')
        previous_balance = _dec('previous_balance') if enable_previous_balance else Decimal('0')

        # التحقق من وجود العميل قبل المتابعة
        if not customer_id or not str(customer_id).strip():
            messages.error(request, _t('الرجاء تحديد العميل أولاً'))
            return redirect('sales:invoice_edit', pk=invoice.pk)

        try:
            customer = Customer.objects.filter(pk=customer_id).first()
            if not customer:
                messages.error(request, _t('العميل المحدد غير موجود. الرجاء اختيار عميل صحيح.'))
                return redirect('sales:invoice_edit', pk=invoice.pk)
            invoice.customer = customer
            invoice.due_date = due_date
            invoice.discount = discount
            invoice.paid = paid
            invoice.payment_method = PaymentMethod.objects.filter(pk=payment_method_id).first() if payment_method_id else None
            invoice.payment_reference = payment_reference
            # Bank transfer details
            if invoice.payment_method and getattr(invoice.payment_method, 'type', '') == 'bank_transfer':
                invoice.bank_name = bank_name or getattr(invoice.payment_method, 'bank_name', '') or ''
                invoice.bank_account = bank_account or getattr(invoice.payment_method, 'account_number', '') or ''
            else:
                invoice.bank_name = ''
                invoice.bank_account = ''
            # Optional fields
            invoice.is_tax_invoice = is_tax_invoice
            invoice.tax_rate = tax_rate
            invoice.tax_amount = tax_amount
            invoice.enable_shipping = enable_shipping
            invoice.shipping_cost = shipping_cost
            invoice.enable_extra_discount = enable_extra_discount
            invoice.extra_discount = extra_discount_val
            invoice.enable_previous_balance = enable_previous_balance
            invoice.previous_balance = previous_balance
            invoice.save()
            messages.success(request, _t('تم تحديث الفاتورة بنجاح'))
            return redirect('sales:invoice_detail', pk=pk)
        except Exception as e:
            messages.error(request, _t('خطأ في تحديث الفاتورة: %(error)s') % {'error': e})

    customers = Customer.objects.all().order_by('name')
    payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('display_order', 'name')

    # Existing items as JSON for JS
    items_json = json.dumps([
        {
            'id': idx,
            'product_id': item.product_id,
            'product_name': item.product.name if item.product else '',
            'location_id': item.location_id or '',
            'location_name': item.location.name if item.location else '',
            'quantity': float(item.quantity),
            'price': float(item.price),
            'discount': 0,
            'tax': 0,
            'total': float(item.total),
            'available_stock': 999,
        }
        for idx, item in enumerate(invoice.items.select_related('product', 'location').all(), 1)
    ], ensure_ascii=False)

    products = Product.objects.all()
    locations = Location.objects.all()
    products_json = json.dumps([
        {'id': p.id, 'name': p.name, 'price': float(p.price) if p.price else 0, 'sku': p.sku or ''}
        for p in products
    ], ensure_ascii=False)

    context = {
        'invoice': invoice,
        'customers': customers,
        'payment_methods': payment_methods,
        'products': products,
        'products_json': products_json,
        'locations': locations,
        'today': date.today().isoformat(),
        'company_vat_rate': company_vat_rate,
        'company_tax_id': company_tax_id,
        'existing_items_json': items_json,
        'is_edit': True,
    }
    return render(request, 'sales/invoice_edit_enhanced.html', context)


@login_required
def invoice_print(request, pk):
    """Print-friendly invoice view"""
    invoice = get_object_or_404(Invoice, pk=pk)
    size = (request.GET.get('size') or 'a4').lower()
    if size not in ('a4', 'a5', 'pos'):
        size = 'a4'
    from core.models import Company
    from django.db.models import Sum
    from datetime import datetime
    
    # حساب الإجماليات
    subtotal = invoice.items.aggregate(total=Sum('price'))['total'] or 0
    # استخدام نسبة الضريبة من إعدادات الشركة
    company = Company.objects.first()
    vat_rate = Decimal('14')
    if company and company.default_vat_rate:
        vat_rate = company.default_vat_rate
    tax_amount = getattr(invoice, 'tax', None) or Decimal('0')
    
    # حساب رصيد العميل
    customer_balance_before = 0
    customer_balance_after = 0
    try:
        # رصيد العميل قبل هذه الفاتورة
        from accounting.models import JournalEntry
        # يمكن حسابه من الفواتير السابقة
        previous_invoices = Invoice.objects.filter(
            customer=invoice.customer,
            date__lt=invoice.date,
            is_deleted=False
        )
        total_previous = previous_invoices.aggregate(t=Sum('cached_total'))['t'] or 0
        paid_previous = previous_invoices.aggregate(p=Sum('paid'))['p'] or 0
        customer_balance_before = total_previous - paid_previous
        customer_balance_after = customer_balance_before + invoice.total - invoice.paid
    except Exception:
        pass
    
    # جلب بيانات الفرع
    branch_name = ''
    branch_phone = ''
    branch_address = ''
    
    if hasattr(invoice, 'location') and invoice.location:
        try:
            from showrooms.models import Showroom
            showroom = Showroom.objects.filter(location=invoice.location).first()
            if showroom:
                branch_name = showroom.name_ar or showroom.name or invoice.location.name
                branch_phone = showroom.contact_phone or ''
                branch_address = showroom.address or ''
            else:
                branch_name = invoice.location.name
        except:
            branch_name = invoice.location.name if invoice.location else ''
    
    # جلب جميع الفروع
    all_branches = []
    try:
        from showrooms.models import Showroom
        for branch in Showroom.objects.filter(is_active=True).order_by('id'):
            all_branches.append({
                'name': branch.name_ar or branch.name,
                'country': branch.country or '',
                'governorate': branch.governorate or '',
                'city': branch.city or '',
                'address': branch.address or '',
                'phone': branch.contact_phone or '',
            })
    except:
        pass
    
    context = {
        'invoice': invoice,
        'printed_by': request.user if request.user.is_authenticated else None,
        'company': company,
        'print_size': size,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'vat_rate': vat_rate,
        'customer_balance_before': customer_balance_before,
        'customer_balance_after': customer_balance_after,
        'branch_name': branch_name,
        'branch_phone': branch_phone,
        'branch_address': branch_address,
        'all_branches': all_branches,
        'now': datetime.now(),
    }
    if request.user.is_authenticated:
        try:
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ACTION_UPDATE,
                model_name='Invoice',
                app_label='sales',
                object_id=str(invoice.pk),
                object_repr=str(invoice),
                changes={'print': 'invoice_print_view'}
            )
        except Exception:
            pass
    
    # استخدام قالب مختلف حسب الحجم
    if size == 'pos':
        return render(request, 'sales/invoice_print_thermal.html', context)
    elif size == 'a4':
        return render(request, 'sales/invoice_print_a4_new.html', context)
    return render(request, 'sales/invoice_print_a4_new.html', context)


@login_required
def invoice_direct_print_a4(request, pk):
    """طباعة فاتورة A4 مباشرة على الطابعة المتصلة - مع بيانات الشركة والضريبة من الإعدادات"""
    invoice = get_object_or_404(Invoice, pk=pk)
    from core.models import Company
    from core.company_service import get_company_data
    from django.db.models import Sum
    from django.urls import reverse
    from datetime import datetime
    
    company = Company.objects.first()
    company_data = get_company_data()
    
    # نسبة الضريبة من إعدادات الشركة
    vat_rate = Decimal('14')
    if company and company.default_vat_rate:
        vat_rate = company.default_vat_rate
    
    # الإجماليات
    items = invoice.items.select_related('product', 'location').all()
    subtotal = sum(item.total for item in items)
    tax_amount = invoice.tax
    discount = invoice.discount or Decimal('0')
    total = invoice.total
    paid = invoice.paid or Decimal('0')
    remaining = invoice.remaining
    
    # رصيد العميل
    customer_balance_before = Decimal('0')
    customer_balance_after = Decimal('0')
    try:
        previous_invoices = Invoice.objects.filter(
            customer=invoice.customer, date__lt=invoice.date, is_deleted=False
        )
        total_previous = previous_invoices.aggregate(t=Sum('cached_total'))['t'] or Decimal('0')
        paid_previous = previous_invoices.aggregate(p=Sum('paid'))['p'] or Decimal('0')
        customer_balance_before = total_previous - paid_previous
        customer_balance_after = customer_balance_before + total - paid
    except Exception:
        pass
    
    # الفروع
    all_branches = []
    try:
        from showrooms.models import Showroom
        for branch in Showroom.objects.filter(is_active=True).order_by('id'):
            all_branches.append({
                'name': branch.name_ar or branch.name,
                'address': branch.address or '',
                'phone': branch.contact_phone or '',
                'governorate': branch.governorate or '',
                'city': branch.city or '',
            })
    except Exception:
        pass
    
    # طريقة الدفع
    payment_method_name = ''
    payment_method_icon = '💰'
    if invoice.payment_method:
        payment_method_name = invoice.payment_method.name
        ptype = getattr(invoice.payment_method, 'type', '')
        icons = {
            'cash': '💵', 'credit_card': '💳', 'bank_transfer': '🏦',
            'vodafone_cash': '📱', 'instapay': '📲', 'check': '📝',
            'orange_cash': '📱', 'etisalat_cash': '📱', 'wallet': '👛',
            'apple_pay': '🍎', 'installment': '📅',
        }
        payment_method_icon = icons.get(ptype, '💰')
    else:
        payment_method_name = 'نقدي'
        payment_method_icon = '💵'
    
    # بناء صفوف الأصناف
    items_rows = ''
    for idx, item in enumerate(items, 1):
        item_discount = getattr(item, 'discount_percent', 0) or 0
        items_rows += f'''<tr>
            <td style="text-align:center;padding:8px 5px;border-bottom:1px solid #e9ecef;font-size:11px;">{idx}</td>
            <td style="text-align:right;padding:8px 5px;border-bottom:1px solid #e9ecef;font-size:11px;">{item.product.name}</td>
            <td style="text-align:center;padding:8px 5px;border-bottom:1px solid #e9ecef;font-size:11px;">{item.quantity}</td>
            <td style="text-align:center;padding:8px 5px;border-bottom:1px solid #e9ecef;font-size:11px;direction:ltr;">{item.price:,.2f}</td>
            <td style="text-align:center;padding:8px 5px;border-bottom:1px solid #e9ecef;font-size:11px;">{item_discount}%</td>
            <td style="text-align:center;padding:8px 5px;border-bottom:1px solid #e9ecef;font-size:11px;direction:ltr;font-weight:bold;">{item.total:,.2f}</td>
        </tr>'''
    
    # فروع الشركة
    branches_html = ''
    if all_branches:
        branches_items = ''
        for b in all_branches:
            branches_items += f'''<div style="background:white;border-radius:5px;border-right:3px solid #667eea;font-size:10px;padding:8px;min-width:180px;flex:1;max-width:250px;">
                <strong>{b['name']}</strong><br>
                {b.get('governorate', '')} {(' - ' + b['city']) if b.get('city') else ''}<br>
                {('<small>' + b['address'] + '</small><br>') if b.get('address') else ''}
                {('📞 ' + b['phone']) if b.get('phone') else ''}
            </div>'''
        branches_html = f'''<div style="background:#f8f9fa;border-radius:10px;padding:15px;margin-bottom:15px;">
            <h6 style="color:#2c3e50;text-align:center;margin-bottom:10px;"><strong>🏪 فروعنا</strong></h6>
            <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;">{branches_items}</div>
        </div>'''
    
    # Logo
    logo_html = '<i style="font-size:32px;color:#667eea;">🏢</i>'
    if company_data.get('logo_url'):
        logo_html = f'<img src="{company_data["logo_url"]}" style="max-width:60px;max-height:60px;" alt="Logo">'
    
    # Watermark
    watermark_html = ''
    if company_data.get('logo_url'):
        watermark_html = f'''<div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);opacity:0.08;z-index:1;pointer-events:none;">
            <img src="{company_data['logo_url']}" style="width:400px;height:400px;object-fit:contain;">
        </div>'''
    
    # URLs
    print_url = reverse('sales:invoice_print', args=[invoice.pk])
    detail_url = reverse('sales:invoice_detail', args=[invoice.pk])
    
    # بناء HTML الفاتورة
    currency = company_data.get('currency_symbol', 'ج.م')
    now = datetime.now()
    
    html = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>فاتورة مبيعات #{invoice.number}</title>
    <style>
        @page {{ size: A4 portrait; margin: 8mm; }}
        * {{ margin:0;padding:0;box-sizing:border-box; }}
        body {{ font-family:'Segoe UI',Tahoma,Arial,sans-serif;font-size:12px;line-height:1.4;background:#fff;color:#333;direction:rtl; }}
        .container {{ max-width:210mm;margin:0 auto;background:#fff; }}
        @media print {{
            body {{ margin:0;padding:0; }}
            .no-print {{ display:none !important; }}
            .container {{ box-shadow:none; }}
            * {{ -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }}
        }}
        @media screen {{
            body {{ background:#f0f0f0;padding:20px; }}
            .container {{ box-shadow:0 0 20px rgba(0,0,0,0.1); }}
        }}
    </style>
</head>
<body>
{watermark_html}
<div class="container">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px 25px;display:flex;justify-content:space-between;align-items:center;">
        <div style="flex:1;">
            <h1 style="font-size:22px;font-weight:bold;margin-bottom:8px;">{company_data.get('name', 'الشركة')}</h1>
            {f'<p style="font-size:11px;opacity:0.95;margin:3px 0;font-style:italic;">{company_data["slogan"]}</p>' if company_data.get('slogan') else ''}
            {f'<p style="font-size:11px;opacity:0.95;margin:3px 0;">📍 {company_data["address"]}</p>' if company_data.get('address') else ''}
            {f'<p style="font-size:11px;opacity:0.95;margin:3px 0;">📞 {company_data["phone"]}</p>' if company_data.get('phone') else ''}
            {f'<p style="font-size:11px;opacity:0.95;margin:3px 0;">📱 {company_data["mobile"]}</p>' if company_data.get('mobile') else ''}
            {f'<p style="font-size:11px;opacity:0.95;margin:3px 0;">✉️ {company_data["email"]}</p>' if company_data.get('email') else ''}
            {f'<p style="font-size:11px;opacity:0.95;margin:3px 0;">🔢 الرقم الضريبي: {company_data["tax_id"]}</p>' if company_data.get('tax_id') else ''}
            {f'<p style="font-size:11px;opacity:0.95;margin:3px 0;">📋 س.ت: {company_data["commercial_register"]}</p>' if company_data.get('commercial_register') else ''}
            {f'<p style="font-size:11px;opacity:0.95;margin:3px 0;">🌐 {company_data["website"]}</p>' if company_data.get('website') else ''}
        </div>
        <div style="width:70px;height:70px;background:rgba(255,255,255,0.2);border-radius:10px;display:flex;align-items:center;justify-content:center;">
            {logo_html}
        </div>
    </div>
    
    <!-- Invoice Badge -->
    <div style="display:flex;justify-content:center;margin-top:-18px;position:relative;z-index:10;">
        <div style="background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);color:white;padding:10px 35px;border-radius:25px;font-size:16px;font-weight:bold;box-shadow:0 4px 15px rgba(79,172,254,0.4);">
            📄 فاتورة مبيعات #{invoice.number}
        </div>
    </div>
    
    <!-- Body -->
    <div style="padding:25px;">
        <!-- Info Cards -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:25px;">
            <!-- Invoice Details -->
            <div style="background:#f8f9fa;border-radius:10px;overflow:hidden;border:1px solid #e9ecef;">
                <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:10px 15px;font-weight:bold;font-size:13px;">
                    📄 تفاصيل الفاتورة
                </div>
                <div style="padding:15px;">
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;">
                        <span style="color:#6c757d;">رقم الفاتورة:</span>
                        <span style="font-weight:600;">#{invoice.number}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;">
                        <span style="color:#6c757d;">التاريخ:</span>
                        <span style="font-weight:600;">{invoice.date.strftime('%Y-%m-%d') if invoice.date else now.strftime('%Y-%m-%d')}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;">
                        <span style="color:#6c757d;">طريقة الدفع:</span>
                        <span style="font-weight:600;background:{'#28a745' if remaining <= 0 else '#ffc107'};color:{'white' if remaining <= 0 else '#212529'};padding:2px 10px;border-radius:10px;font-size:10px;">
                            {payment_method_icon} {payment_method_name}
                        </span>
                    </div>
                    {f'<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:11px;"><span style="color:#6c757d;">تاريخ الاستحقاق:</span><span style="font-weight:600;">{invoice.due_date.strftime("%Y-%m-%d")}</span></div>' if invoice.due_date else ''}
                </div>
            </div>
            
            <!-- Customer Details -->
            <div style="background:#f8f9fa;border-radius:10px;overflow:hidden;border:1px solid #e9ecef;">
                <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:10px 15px;font-weight:bold;font-size:13px;">
                    👤 بيانات العميل
                </div>
                <div style="padding:15px;">
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;">
                        <span style="color:#6c757d;">اسم العميل:</span>
                        <span style="font-weight:600;">{invoice.customer.name}</span>
                    </div>
                    {f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;"><span style="color:#6c757d;">الهاتف:</span><span style="font-weight:600;">{invoice.customer.phone}</span></div>' if hasattr(invoice.customer, 'phone') and invoice.customer.phone else ''}
                    {f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;"><span style="color:#6c757d;">العنوان:</span><span style="font-weight:600;">{invoice.customer.address}</span></div>' if hasattr(invoice.customer, 'address') and invoice.customer.address else ''}
                    {f'<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:11px;"><span style="color:#6c757d;">البريد:</span><span style="font-weight:600;">{invoice.customer.email}</span></div>' if hasattr(invoice.customer, 'email') and invoice.customer.email else ''}
                </div>
            </div>
        </div>
        
        <!-- Items Table -->
        <table style="width:100%;border-collapse:collapse;margin-bottom:25px;">
            <thead>
                <tr style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;">
                    <th style="padding:12px 10px;text-align:center;font-size:11px;width:5%;">#</th>
                    <th style="padding:12px 10px;text-align:right;font-size:11px;width:35%;">الصنف</th>
                    <th style="padding:12px 10px;text-align:center;font-size:11px;width:12%;">الكمية</th>
                    <th style="padding:12px 10px;text-align:center;font-size:11px;width:15%;">السعر</th>
                    <th style="padding:12px 10px;text-align:center;font-size:11px;width:13%;">الخصم %</th>
                    <th style="padding:12px 10px;text-align:center;font-size:11px;width:20%;">الإجمالي</th>
                </tr>
            </thead>
            <tbody>{items_rows}</tbody>
        </table>
        
        <!-- Summary -->
        <div style="display:flex;justify-content:flex-end;margin-bottom:20px;">
            <div style="width:380px;background:#f8f9fa;border-radius:10px;overflow:hidden;border:1px solid #e9ecef;">
                <div style="background:linear-gradient(135deg,#ffecd2 0%,#fcb69f 100%);padding:10px 15px;font-weight:bold;font-size:13px;color:#c44d34;">
                    🔥 ملخص المبالغ
                </div>
                <div style="padding:10px 15px;">
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;">
                        <span>الإجمالي قبل الخصم:</span>
                        <span style="font-weight:600;direction:ltr;">{currency} {subtotal:,.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;">
                        <span>الخصم:</span>
                        <span style="font-weight:600;direction:ltr;">{currency} {discount:,.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;">
                        <span>ضريبة القيمة المضافة ({vat_rate}%):</span>
                        <span style="font-weight:600;direction:ltr;">{currency} {tax_amount:,.2f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #dee2e6;font-size:11px;">
                        <span>المدفوع:</span>
                        <span style="font-weight:600;direction:ltr;color:#28a745;">{currency} {paid:,.2f}</span>
                    </div>
                    
                    <!-- Balance rows -->
                    <div style="margin-top:10px;border-top:2px solid #dee2e6;padding-top:10px;">
                        <div style="display:flex;justify-content:space-between;padding:8px 12px;border-radius:8px;margin-bottom:6px;background:#fff3cd;border:1px solid #ffc107;font-size:11px;">
                            <span>رصيد العميل قبل الفاتورة:</span>
                            <span style="color:#dc3545;font-weight:bold;direction:ltr;">{currency} {customer_balance_before:,.2f}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;padding:8px 12px;border-radius:8px;margin-bottom:6px;background:#d4edda;border:1px solid #28a745;font-size:11px;">
                            <span>المدفوع:</span>
                            <span style="color:#28a745;font-weight:bold;direction:ltr;">{currency} {paid:,.2f}</span>
                        </div>
                        {f'<div style="display:flex;justify-content:space-between;padding:8px 12px;border-radius:8px;margin-bottom:6px;background:#f8d7da;border:1px solid #dc3545;font-size:11px;"><span>المتبقي:</span><span style="color:#dc3545;font-weight:bold;direction:ltr;">{currency} {remaining:,.2f}</span></div>' if remaining > 0 else ''}
                        <div style="display:flex;justify-content:space-between;padding:8px 12px;border-radius:8px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;font-weight:bold;font-size:13px;">
                            <span>💰 الإجمالي النهائي:</span>
                            <span style="direction:ltr;">{currency} {total:,.2f}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Footer -->
    <div style="background:#f8f9fa;padding:15px 25px;text-align:center;border-top:1px solid #e9ecef;">
        {branches_html}
        <div style="font-size:11px;color:#6c757d;margin-bottom:5px;">
            {company_data.get('footer_text', '') or f'هذا المستند تم إنشاؤه بواسطة نظام {company_data.get("name", "Tony ERP")}'}
        </div>
        <div style="font-size:10px;color:#adb5bd;">
            تمت الطباعة: {now.strftime('%Y/%m/%d %H:%M')}
            {f' | بواسطة: {request.user.get_full_name() or request.user.username}' if request.user.is_authenticated else ''}
        </div>
    </div>
</div>

<!-- Print buttons -->
<div class="no-print" style="display:flex;justify-content:center;gap:15px;padding:20px;background:#e9ecef;">
    <button onclick="window.print()" style="padding:12px 25px;border:none;border-radius:25px;cursor:pointer;font-size:13px;font-weight:600;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;">
        🖨️ طباعة A4
    </button>
    <a href="{print_url}" style="padding:12px 25px;border:none;border-radius:25px;cursor:pointer;font-size:13px;font-weight:600;background:#28a745;color:white;text-decoration:none;">
        📄 عرض الطباعة العادية
    </a>
    <a href="{detail_url}" style="padding:12px 25px;border:none;border-radius:25px;cursor:pointer;font-size:13px;font-weight:600;background:#6c757d;color:white;text-decoration:none;">
        ← رجوع للفاتورة
    </a>
</div>

<script>
    // طباعة تلقائية عند فتح الصفحة
    window.onload = function() {{
        setTimeout(function() {{ window.print(); }}, 500);
    }};
    document.addEventListener('keydown', function(e) {{
        if ((e.ctrlKey && e.key === 'p') || e.key === 'Enter') {{
            e.preventDefault();
            window.print();
        }}
        if (e.key === 'Escape') {{ window.history.back(); }}
    }});
</script>
</body>
</html>'''
    
    return HttpResponse(html, content_type='text/html; charset=utf-8')


@login_required
def invoice_delete(request, pk):
    """حذف (منطقي) الفاتورة مع نفس ضوابط الحذف الحساسة (موافقة المدير المالي/المدير العام + كلمة مرور + سبب)."""
    invoice = get_object_or_404(Invoice, pk=pk, is_deleted=False)
    if request.method == 'POST':
        # تحقق الصلاحيات: المدير العام أو المدير المالي (صلاحية المحاسبة)
        approver = request.user
        has_finance_manager_perm = hasattr(approver, 'has_module_permission') and approver.has_module_permission('accounting', 'change')
        if not (approver.is_superuser or has_finance_manager_perm):
            messages.error(request, _t('يتطلب الحذف موافقة المدير المالي أو المدير العام.'))
            return redirect('sales:invoice_delete', pk=pk)

        # كلمة المرور للتحقق من هوية الموافق
        from django.contrib.auth.hashers import check_password
        pwd = (request.POST.get('confirm_password') or '').strip()
        if not pwd or not check_password(pwd, approver.password):
            messages.error(request, _t('فشل التحقق من كلمة مرور الموافقة.'))
            return redirect('sales:invoice_delete', pk=pk)

        # سبب الحذف (مطلوب)
        reason = (request.POST.get('reason') or '').strip()
        if not reason or len(reason) < 3:
            messages.error(request, _t('يجب إدخال سبب الحذف (3 أحرف على الأقل).'))
            return redirect('sales:invoice_delete', pk=pk)
        invoice.is_deleted = True
        invoice.deleted_at = timezone.now()
        invoice.deleted_by = request.user
        invoice.delete_reason = reason
        invoice.save(update_fields=['is_deleted','deleted_at','deleted_by','delete_reason'])
        try:
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ACTION_DELETE,
                model_name='Invoice',
                app_label='sales',
                object_id=str(invoice.pk),
                object_repr=str(invoice),
                changes={'reason': reason, 'delete_reason': reason}
            )
        except Exception:
            pass
        messages.success(request,_t('تم حذف الفاتورة (حذف منطقي)'))
        return redirect('sales:invoice_list')
    return render(request,'sales/invoice_delete_confirm.html',{'invoice':invoice})


@login_required
@require_POST
def invoice_item_add_ajax(request, invoice_id):
    """إضافة بند بالـ AJAX (مثال للتوسعة مع الباركود)."""
    invoice = get_object_or_404(Invoice, pk=invoice_id, is_deleted=False)
    product_id = request.POST.get('product'); location_id=request.POST.get('location')
    qty_raw = request.POST.get('quantity','1'); price_raw=request.POST.get('price','0')
    try:
        quantity = int(qty_raw); assert quantity>0
        price = Decimal(price_raw)
    except Exception:
        return JsonResponse({'success':False,'message':_t('بيانات غير صالحة')}, status=400)
    product = get_object_or_404(Product, pk=product_id)
    location = get_object_or_404(Location, pk=location_id)
    stock = Stock.objects.filter(product=product, location=location).first()
    
    # التحقق من المخزون مع السماح بالإضافة حتى لو كان صفر
    available_qty = stock.quantity if stock else 0
    warning_msg = None
    
    if available_qty < quantity:
        warning_msg = _t('تحذير: المخزون المتاح %(available)s فقط. تمت الإضافة (مخزون سالب)') % {'available': available_qty}
    
    # إضافة البند حتى لو كان المخزون غير كافي
    item = InvoiceItem.objects.create(invoice=invoice, product=product, location=location, quantity=quantity, price=price)
    try:
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.ACTION_CREATE,
            model_name='InvoiceItem',
            app_label='sales',
            object_id=str(item.pk),
            object_repr=f'{item.product} x {item.quantity}',
            changes={'invoice': invoice.number}
        )
    except Exception:
        pass
    
    response_data = {
        'success': True,
        'item': {
            'id': item.id,
            'product': item.product.name,
            'sku': item.product.sku,
            'location': item.location.name,
            'quantity': item.quantity,
            'returned_qty': 0,
            'remaining_qty': item.quantity,
            'price': float(item.price),
            'total': float(item.total),
        },
        'invoice_totals': {
            'total': float(invoice.total),
            'remaining': float(invoice.remaining)
        }
    }
    
    if warning_msg:
        response_data['warning'] = warning_msg
    
    return JsonResponse(response_data)


@login_required
def sales_daily_report(request):
    """تقرير يومي موسع: إجمالي حسب طريقة الدفع + تصدير CSV."""
    from django.utils.dateparse import parse_date
    day = request.GET.get('date')
    if day:
        try: day_parsed = parse_date(day)
        except Exception: day_parsed = date.today()
    else:
        day_parsed = date.today()
    items = (InvoiceItem.objects
             .filter(invoice__date=day_parsed, invoice__is_deleted=False)
             .select_related('invoice__payment_method','invoice__customer','product'))
    total_sales = items.aggregate(total=Sum('price'))['total'] or 0
    by_method = {}
    for it in items:
        key = it.invoice.payment_method.name if it.invoice.payment_method else _t('أخرى')
        by_method.setdefault(key, Decimal('0'))
        by_method[key] += it.price
    rows_method = [{'method':k,'total':v} for k,v in by_method.items()]
    export = request.GET.get('export')
    if export == 'csv':
        import csv
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition']=f'attachment; filename=daily_sales_{day_parsed}.csv'
        resp.write('\ufeff')
        w=csv.writer(resp); w.writerow(['Method','Total'])
        for r in rows_method: w.writerow([r['method'], r['total']])
        w.writerow(['ALL', total_sales])
        try:
            AuditLog.objects.create(user=request.user, action=AuditLog.ACTION_EXPORT, model_name='Invoice', app_label='sales', object_id='-', object_repr='daily_report', changes={'date': str(day_parsed), 'format': 'csv'})
        except Exception: pass
        return resp
    elif export == 'xlsx':
        from openpyxl import Workbook  # type: ignore
        from openpyxl.utils import get_column_letter  # type: ignore
        wb = Workbook()
        ws = wb.active
        ws.title = 'Daily Sales'
        if ws:
            ws.append(['Method','Total'])
            for r in rows_method:
                ws.append([r['method'], float(r['total'])])
            ws.append(['ALL', float(total_sales)])
        for col in range(1,3):
            ws.column_dimensions[get_column_letter(col)].width = 18
        from io import BytesIO
        bio = BytesIO(); wb.save(bio); bio.seek(0)
        resp = HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition']=f'attachment; filename=daily_sales_{day_parsed}.xlsx'
        try:
            AuditLog.objects.create(user=request.user, action=AuditLog.ACTION_EXPORT, model_name='Invoice', app_label='sales', object_id='-', object_repr='daily_report', changes={'date': str(day_parsed), 'format': 'xlsx'})
        except Exception: pass
        return resp
    return render(request,'sales/daily_report.html',{'date':day_parsed,'total_sales':total_sales,'by_method':rows_method})


@login_required
def invoice_add_payment(request, pk):
    """إضافة دفعة جزئية مع توليد إيصال وقيد محاسبي اختياري."""
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        from django.utils import timezone

        raw_amount = (request.POST.get('amount') or '0').strip() or '0'
        try:
            amount = Decimal(raw_amount)
        except (InvalidOperation, TypeError):
            amount = Decimal('0')

        payment_method_id = request.POST.get('payment_method') or None
        reference = (request.POST.get('reference') or '').strip()
        bank_name = (request.POST.get('bank_name') or '').strip()
        bank_account = (request.POST.get('bank_account') or '').strip()
        description = (request.POST.get('description') or '').strip()

        # التحقق الأساسي
        if amount <= 0:
            messages.error(request, _t('مبلغ غير صالح'))
            return redirect('sales:invoice_add_payment', pk=pk)
        if amount > invoice.remaining:
            messages.error(request, _t('المبلغ أكبر من المتبقي على الفاتورة'))
            return redirect('sales:invoice_add_payment', pk=pk)

        pm_obj = (PaymentMethod.objects.filter(pk=payment_method_id)
                  .select_related('account').first() if payment_method_id else None)

        # استكمال بيانات التحويل البنكي إن لزم
        if pm_obj and pm_obj.type == 'bank_transfer':
            bank_name = bank_name or getattr(pm_obj, 'bank_name', '') or ''
            bank_account = bank_account or getattr(pm_obj, 'account_number', '') or ''
        else:
            bank_name = ''
            bank_account = ''

        pay = InvoicePayment.objects.create(
            invoice=invoice,
            customer=invoice.customer,
            amount=amount,
            payment_method=pm_obj,
            reference=reference,
            bank_name=bank_name,
            bank_account=bank_account,
            description=description,
            created_by=request.user,
        )

        # إنشاء قيد تلقائي (اختياري)
        try:
            if pm_obj and getattr(pm_obj, 'account_id', None):
                from accounting.models import JournalEntry, JournalEntryItem, AccountingSettings, Account
                acct_settings = AccountingSettings.get()
                ar_acc = (getattr(acct_settings, 'ar_account', None)
                          or Account.objects.filter(name__icontains='عملاء').first())
                if ar_acc:
                    je = JournalEntry.objects.create(
                        description=_t('استلام دفعة فاتورة %(num)s') % {'num': invoice.number},
                        entry_type='payment',
                        reference=pay.receipt_number or reference,
                        date=timezone.now().date(),
                        created_by=request.user
                    )
                    JournalEntryItem.objects.bulk_create([
                        JournalEntryItem(
                            journal_entry=je,
                            account_id=pm_obj.account.id,
                            type='debit',
                            amount=pay.amount,
                            description=description or _t('دفعة عميل')
                        ),
                        JournalEntryItem(
                            journal_entry=je,
                            account_id=ar_acc.id,
                            type='credit',
                            amount=pay.amount,
                            description=description or _t('دفعة عميل')
                        )
                    ])
                    je.is_posted = True
                    je.save(update_fields=['is_posted'])
                    pay.journal_entry = je
                    pay.save(update_fields=['journal_entry'])
        except Exception as e:  # لا نمنع الدفعة عند فشل القيد
            import logging
            logging.getLogger(__name__).warning('فشل إنشاء القيد التلقائي للدفعة %s: %s', pay.id, e)

        messages.success(request, _t('تم تسجيل الدفعة رقم %(num)s') % {'num': pay.receipt_number})
        return redirect('sales:payment_receipt_print', payment_id=pay.id)

    context = {
        'invoice': invoice,
    'PAYMENT_METHODS': PaymentMethod.objects.filter(is_active=True).order_by('display_order','name'),
    }
    return render(request, 'sales/invoice_add_payment.html', context)


@login_required
def sales_quick_report(request):
    """تقرير سريع: مبيعات اليوم وإجمالي حسب العميل وأعلى المنتجات."""
    today = date.today()
    from django.db.models import Sum as DJSum
    items_qs = InvoiceItem.objects.filter(invoice__date=today).select_related('invoice__customer','product')
    total_sales = items_qs.aggregate(total=DJSum('price'))['total'] or 0
    by_customer = (items_qs
        .values('invoice__customer__name')
        .annotate(total=DJSum('price'))
        .order_by('-total')[:20])
    top_products = (items_qs
        .values('product__name','product__sku')
        .annotate(total_qty=DJSum('quantity'), total_amount=DJSum('price'))
        .order_by('-total_amount')[:20])
    return render(request,'sales/quick_report.html',{
        'title':_t('تقرير سريع - مبيعات اليوم'),
        'date': today,
        'total_sales': total_sales,
        'by_customer': by_customer,
        'top_products': top_products,
    })


@login_required
def payment_receipt_print(request, payment_id):
    pay = get_object_or_404(InvoicePayment.objects.select_related('invoice', 'customer'), pk=payment_id)
    size = (request.GET.get('size') or 'a5').lower()
    if size not in ('a4', 'a5', 'pos'):
        size = 'a5'
    # تحقق الصلاحية للطباعة
    if not request.user.has_perm('sales.print_invoicepayment'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(_t('ليست لديك صلاحية طباعة الإيصال'))
    # تحديث عداد الطباعة
    changed = False
    if not pay.first_printed_at:
        pay.first_printed_at = timezone.now()
        changed = True
    pay.printed_count += 1
    # قفل تلقائي بعد أول طباعة (يمكن لاحقاً جعلها إعداد)
    if not pay.locked:
        pay.locked = True
        changed = True
    if changed:
        InvoicePayment.objects.filter(pk=pay.pk).update(first_printed_at=pay.first_printed_at, printed_count=pay.printed_count, locked=pay.locked)
    # سجل التدقيق
    if request.user.is_authenticated:
        try:
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ACTION_UPDATE,
                model_name='InvoicePayment',
                app_label='sales',
                object_id=str(pay.pk),
                object_repr=str(pay),
                changes={'print': f'receipt_print_{pay.printed_count}'}
            )
        except Exception:
            pass
    return render(request, 'sales/payment_receipt_print.html', {
        'payment': pay,
        'invoice': pay.invoice,
        'printed_by': request.user if request.user.is_authenticated else None,
        'print_size': size,
    })


@login_required
def payment_allocate(request, payment_id):
    """تخصيص دفعة (مقدمة) إلى فاتورة مفتوحة واحدة أو أكثر (مبدئياً واحدة)."""
    payment = get_object_or_404(InvoicePayment.objects.select_related('customer'), pk=payment_id)
    if payment.invoice_id:
        messages.info(request, _t('هذه الدفعة مرتبطة مباشرة بفاتورة ولا تحتوي رصيداً للتخصيص'))
        return redirect('sales:payment_receipt_print', payment_id=payment.id)
    if not request.user.has_perm('sales.add_invoicepayment'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(_t('ليست لديك صلاحية'))
    unapplied = payment.unapplied_amount
    allocations = payment.allocations.select_related('invoice').all()
    if request.method == 'POST':
        # حذف تخصيص موجود
        if request.POST.get('delete_allocation'):
            alloc_id = request.POST.get('delete_allocation')
            alloc = payment.allocations.filter(pk=alloc_id).first()
            if not alloc:
                messages.error(request, _t('التخصيص غير موجود'))
            else:
                try:
                    alloc.delete()
                    messages.success(request, _t('تم حذف التخصيص'))
                except Exception as e:
                    messages.error(request, str(e))
            return redirect('sales:payment_allocate', payment_id=payment.id)
        # تخصيص تلقائي
        if request.POST.get('auto_allocate'):
            if unapplied <= 0:
                messages.info(request, _t('لا يوجد رصيد للتخصيص'))
                return redirect('sales:payment_allocate', payment_id=payment.id)
            from django.db import transaction
            try:
                with transaction.atomic():
                    remaining_unapplied = payment.unapplied_amount  # إعادة حساب داخل القفل
                    # فواتير مفتوحة مرتبة بالأقدمية
                    open_qs = (Invoice.objects.filter(customer=payment.customer)
                               .order_by('date', 'id'))
                    allocated_any = False
                    for inv in open_qs:
                        if remaining_unapplied <= 0:
                            break
                        inv_rem = inv.remaining
                        if inv_rem <= 0:
                            continue
                        alloc_amt = inv_rem if inv_rem <= remaining_unapplied else remaining_unapplied
                        if alloc_amt <= 0:
                            continue
                        InvoicePaymentAllocation.objects.create(payment=payment, invoice=inv, amount=alloc_amt, created_by=request.user)
                        remaining_unapplied -= alloc_amt
                        allocated_any = True
                    if allocated_any:
                        messages.success(request, _t('تم التخصيص التلقائي بنجاح'))
                    else:
                        messages.info(request, _t('لا توجد فواتير مفتوحة للتخصيص'))
            except Exception as e:
                messages.error(request, _t('فشل التخصيص التلقائي: %(err)s') % {'err': e})
            return redirect('sales:payment_allocate', payment_id=payment.id)
        # تخصيص يدوي
        invoice_number = (request.POST.get('invoice_number') or '').strip()
        amount_raw = (request.POST.get('amount') or '0').replace(',', '').strip()
        try:
            alloc_amount = Decimal(amount_raw)
        except (InvalidOperation, TypeError):
            alloc_amount = Decimal('0')
        errors = []
        invoice_obj = None
        if alloc_amount <= 0:
            errors.append(_t('مبلغ غير صالح'))
        invoice_obj = Invoice.objects.filter(number=invoice_number, customer=payment.customer).first()
        if not invoice_obj:
            errors.append(_t('لم يتم العثور على الفاتورة للعميل'))
        elif invoice_obj.remaining <= 0:
            errors.append(_t('الفاتورة مسددة أو ليس لديها متبقي'))
        if alloc_amount > unapplied:
            errors.append(_t('المبلغ يتجاوز الرصيد المتبقي في الدفعة'))
        if invoice_obj and alloc_amount > (invoice_obj.remaining + Decimal('0.0001')):
            errors.append(_t('المبلغ يتجاوز المتبقي على الفاتورة'))
        if not errors and invoice_obj:
            try:
                InvoicePaymentAllocation.objects.create(payment=payment, invoice=invoice_obj, amount=alloc_amount, created_by=request.user)
                messages.success(request, _t('تم تخصيص %(amt).2f للفاتورة %(inv)s') % {'amt': alloc_amount, 'inv': invoice_obj.number})
                return redirect('sales:payment_allocate', payment_id=payment.id)
            except Exception as e:
                messages.error(request, str(e))
        else:
            for err in errors:
                messages.error(request, err)
        # تحديث القيم بعد محاولة التخصيص
        unapplied = payment.unapplied_amount
        allocations = payment.allocations.select_related('invoice').all()
    # فواتير مفتوحة مختصرة لنفس العميل (أقدم أولاً)
    open_invoices = [inv for inv in payment.customer.invoices.order_by('date', 'id') if inv.remaining > 0][:50]
    return render(request, 'sales/payment_allocate.html', {
        'payment': payment,
        'unapplied': unapplied,
        'allocations': allocations,
        'open_invoices': open_invoices,
    })


@login_required
def receipt_create(request):
    """إنشاء دفعة / إيصال جديد مباشرة برقم الفاتورة أو اختيار عميل.

    المرحلة الأولى (سريعة): السماح بإدخال رقم فاتورة (number) أو اختيار عميل فقط.
    - لو تم توفير رقم فاتورة صالح يتم ربط الدفعة بالفاتورة والتحقق من المتبقي.
    - لو لم يتم توفير رقم فاتورة: (مرفوض حالياً لأن حقل invoice إجباري في الموديل)
      يمكن لاحقاً دعم دفعات عامة بعد تعديل الموديل للسماح invoice=null.
    """
    if not request.user.has_perm('sales.add_invoicepayment'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(_t('ليست لديك صلاحية إضافة دفعة'))

    from decimal import Decimal, InvalidOperation
    invoice_obj = None
    customer = None
    if request.method == 'POST':
        invoice_number = (request.POST.get('invoice_number') or '').strip()
        customer_id = (request.POST.get('customer') or '').strip()
        amount_raw = (request.POST.get('amount') or '0').replace(',', '').strip()
        method_id = request.POST.get('payment_method') or None
        reference = (request.POST.get('reference') or '').strip()
        description = (request.POST.get('description') or '').strip()
        bank_name = (request.POST.get('bank_name') or '').strip()
        bank_account = (request.POST.get('bank_account') or '').strip()
        errors = []
        # Parse amount
        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, TypeError):
            amount = Decimal('0')
        if amount <= 0:
            errors.append(_t('مبلغ غير صالح'))
        # Resolve invoice (optional now) & customer logic
        if invoice_number:
            invoice_obj = Invoice.objects.filter(number=invoice_number).first()
            if not invoice_obj:
                errors.append(_t('لم يتم العثور على الفاتورة'))
            else:
                if amount > invoice_obj.remaining:
                    errors.append(_t('المبلغ يتجاوز المتبقي على الفاتورة'))
                customer = invoice_obj.customer
        # If no invoice, require customer selection
        if not invoice_obj:
            if not customer_id:
                errors.append(_t('اختر العميل عند عدم إدخال رقم الفاتورة'))
            else:
                customer = Customer.objects.filter(pk=customer_id).first()
                if not customer:
                    errors.append(_t('العميل غير موجود'))
        # Payment method
        pm_obj = PaymentMethod.objects.filter(pk=method_id).first() if method_id else None
        # Normalize bank info for transfer only
        if pm_obj and getattr(pm_obj, 'type', '') == 'bank_transfer':
            bank_name = bank_name or getattr(pm_obj, 'bank_name', '') or ''
            bank_account = bank_account or getattr(pm_obj, 'account_number', '') or ''
        else:
            bank_name = ''
            bank_account = ''
        if not errors and customer:
            try:
                from .services.payments import create_payment
                result = create_payment(
                    invoice=invoice_obj,
                    customer=customer,
                    amount=amount,
                    payment_method=pm_obj,
                    reference=reference,
                    description=description,
                    user=request.user,
                    auto_post=True,
                )
                pay = result.payment
                try:
                    AuditLog.objects.create(
                        user=request.user,
                        action=AuditLog.ACTION_CREATE,
                        model_name='InvoicePayment',
                        app_label='sales',
                        object_id=str(pay.pk),
                        object_repr=str(pay),
                        changes={'advance': bool(pay.is_advance)} if pay.is_advance else {'invoice': invoice_obj.number if invoice_obj else None}
                    )
                except Exception:
                    pass
                if pay.is_advance:
                    messages.success(request, _t('تم تسجيل دفعة مقدمة رقم %(num)s') % {'num': pay.receipt_number})
                else:
                    messages.success(request, _t('تم تسجيل الدفعة رقم %(num)s') % {'num': pay.receipt_number})
                return redirect('sales:payment_receipt_print', payment_id=pay.id)
            except Exception as e:
                errors.append(str(e))
        for err in errors:
            messages.error(request, err)

    ctx = {
        'title': _t('استلام دفعة (إيصال) جديدة'),
    'PAYMENT_METHODS': PaymentMethod.objects.filter(is_active=True).order_by('display_order','name')[:200],
        'invoice_obj': invoice_obj,
        'customer': customer,
        'customers': Customer.objects.all().order_by('name')[:300],
    }
    return render(request, 'sales/receipt_create.html', ctx)


@login_required
def customer_statement(request, customer_id):
    """كشف حساب عميل (مبالغ فواتير - مدفوعات) مع إمكانية الطباعة"""
    customer = get_object_or_404(Customer, pk=customer_id)
    from django.utils.dateparse import parse_date
    date_from = parse_date(request.GET.get('date_from')) if request.GET.get('date_from') else None
    date_to = parse_date(request.GET.get('date_to')) if request.GET.get('date_to') else None
    if date_from and not date_to:
        from datetime import date as _date
        date_to = _date.today()
    # إنشاء دفعة جديدة (POST) من نفس صفحة كشف الحساب
    if request.method == 'POST' and request.POST.get('create_payment'):
        if not request.user.has_perm('sales.add_invoicepayment'):
            messages.error(request, _t('ليست لديك صلاحية إضافة دفعة'))
        else:
            try:
                invoice_id = int(request.POST.get('invoice_id'))
                amount_raw = (request.POST.get('amount') or '0').replace(',', '').strip()
                method_id = request.POST.get('payment_method') or None
                reference = (request.POST.get('reference') or '').strip()
                description = (request.POST.get('description') or '').strip()
                try:
                    amount = Decimal(amount_raw)
                except (InvalidOperation, TypeError):
                    raise ValueError(_t('مبلغ غير صالح'))
                inv = get_object_or_404(Invoice, pk=invoice_id, customer=customer)
                if amount <= 0:
                    raise ValueError(_t('المبلغ يجب أن يكون أكبر من صفر'))
                InvoicePayment.objects.create(
                    invoice=inv,
                    customer=customer,
                    amount=amount,
                    payment_method=PaymentMethod.objects.filter(pk=method_id).first() if method_id else None,
                    reference=reference,
                    description=description,
                    created_by=request.user,
                )
                messages.success(request, _t('تم تسجيل الدفعة بنجاح'))
                return redirect(request.path + '?' + request.META.get('QUERY_STRING', ''))
            except Exception as e:
                messages.error(request, _t('فشل إنشاء الدفعة: %(error)s') % {'error': e})
    # Force cache refresh
    force_refresh = request.GET.get('refresh') == '1'
    if force_refresh:
        try:
            from django.core.cache import cache
            from .utils import _statement_version_key
            cache.delete(_statement_version_key(customer.id))
        except Exception:
            pass
    statement = build_customer_statement(customer, date_from=date_from, date_to=date_to)
    timeline = statement['timeline']
    invoices_count = sum(1 for r in timeline if r['type'] == 'invoice')
    payments_count = sum(1 for r in timeline if r['type'] == 'payment')
    total_debit = sum(r['debit'] or 0 for r in timeline)
    total_credit = sum(r['credit'] or 0 for r in timeline)
    net_movement = total_debit - total_credit
    # بحث / تصفية عرض فقط (لا يؤثر على الرصيد المحسوب)
    q = request.GET.get('q', '').strip()
    if q:
        q_lower = q.lower()
        filtered_timeline = [r for r in timeline if q_lower in (str(r['number']).lower() + ' ' + str(r['description']).lower())]
    else:
        filtered_timeline = timeline
    # ترقيم صفحات (Pagination)
    try:
        page = int(request.GET.get('page', '1'))
        if page < 1: page = 1
    except ValueError:
        page = 1
    try:
        page_size = int(request.GET.get('page_size', '50'))
        if page_size <= 0: page_size = 50
        if page_size > 500: page_size = 500  # سقف وقائي
    except ValueError:
        page_size = 50
    total_rows = len(filtered_timeline)
    total_pages = math.ceil(total_rows / page_size) if total_rows else 1
    if page > total_pages:
        page = total_pages
    start = (page - 1) * page_size
    end = start + page_size
    display_timeline = filtered_timeline[start:end]
    pagination = {
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'total_rows': total_rows,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1,
        'next_page': page + 1,
        'start_index': start + 1 if total_rows else 0,
        'end_index': min(end, total_rows),
    }
    # بيانات رسم بياني بسيط (Sparkline)
    chart_points = [{'d': str(r['date']), 'b': r['balance']} for r in timeline]
    # فواتير مفتوحة (متبقي>0) لتمريرها في نموذج الدفعة
    open_invoices = []
    for inv in Invoice.objects.filter(customer=customer).order_by('-date')[:100]:
        rem = inv.remaining
        if rem > 0:
            open_invoices.append({'id': inv.id, 'number': inv.number, 'remaining': rem})
    # سلف / دفعات غير مخصصة (رصيد غير مخصص)
    advance_list = []
    try:
        advances_qs = InvoicePayment.objects.filter(customer=customer, invoice__isnull=True)
        total_unapplied_advances = Decimal('0')
        for p in advances_qs:
            ua = p.unapplied_amount
            if ua > 0:
                total_unapplied_advances += ua
                advance_list.append({'id': p.id, 'receipt': p.receipt_number, 'amount': p.amount, 'unapplied': ua, 'date': p.date})
    except Exception:
        total_unapplied_advances = Decimal('0')
    common_ctx = {
        'customer': customer,
        'invoices_count': invoices_count,
        'payments_count': payments_count,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'net_movement': net_movement,
        'q': q,
        'display_timeline': display_timeline,
        'chart_points': chart_points,
        'open_invoices': open_invoices,
    'payment_methods': PaymentMethod.objects.filter(is_active=True).order_by('display_order','name')[:100],
        'can_add_payment': request.user.has_perm('sales.add_invoicepayment'),
        'pagination': pagination,
        'unapplied_advances_total': total_unapplied_advances,
        'unapplied_advances': advance_list,
        **statement
    }
    # Export
    export_fmt = request.GET.get('export')
    if export_fmt in ('csv', 'xlsx'):
        rows = timeline
        if export_fmt == 'csv':
            import csv
            from django.http import HttpResponse
            resp = HttpResponse(content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename=statement_{customer.id}.csv'
            w = csv.writer(resp)
            w.writerow(['Date','Type','Number','Description','Debit','Credit','Balance'])
            w.writerow(['OPENING','--','--','Opening Balance', f"{statement['opening_balance']:.2f}", '', f"{statement['opening_balance']:.2f}"])
            for r in rows:
                w.writerow([r['date'], r['type'], r['number'], r['description'], r['debit'] or '', r['credit'] or '', f"{r['balance']:.2f}"])
            return resp
        else:
            try:
                import openpyxl  # type: ignore
                from openpyxl.utils import get_column_letter  # type: ignore
                from io import BytesIO
                wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Statement'
                if ws: ws.append(['Date','Type','Number','Description','Debit','Credit','Balance'])
                if ws: ws.append(['OPENING','--','--','Opening Balance', float(statement['opening_balance']), '', float(statement['opening_balance'])])
                for r in rows:
                    if ws: ws.append([str(r['date']), r['type'], r['number'], r['description'], r['debit'] or '', r['credit'] or '', float(r['balance'])])
                for i, col in enumerate(ws.columns, start=1):
                    max_len = 0
                    for cell in col:
                        if cell.value:
                            max_len = max(max_len, len(str(cell.value)))
                    ws.column_dimensions[get_column_letter(i)].width = min(max_len + 2, 40)
                buf = BytesIO(); wb.save(buf); buf.seek(0)
                from django.http import HttpResponse
                resp = HttpResponse(buf.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                resp['Content-Disposition'] = f'attachment; filename=statement_{customer.id}.xlsx'
                return resp
            except Exception:
                pass
    if request.GET.get('print') == '1':
        if not request.user.has_perm('sales.print_customerstatement'):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden(_t('ليست لديك صلاحية طباعة كشف الحساب'))

        # Normalize context for the print template.
        # templates/sales/customer_statement_print.html expects:
        # - transactions (with a no-arg .count())
        # - tx.reference / tx.running_balance
        # - closing_balance
        class _TxList(list):
            def count(self):  # type: ignore[override]
                return len(self)

        try:
            common_ctx['closing_balance'] = statement.get('balance')
            if common_ctx.get('date_to') is None:
                common_ctx['date_to'] = date.today()
            if common_ctx.get('date_from') is None:
                common_ctx['date_from'] = statement.get('date_from') or common_ctx.get('date_to')
            common_ctx['today'] = timezone.now()
            common_ctx['transactions'] = _TxList([
                {
                    'date': r.get('date'),
                    'reference': r.get('number'),
                    'description': r.get('description'),
                    'debit': r.get('debit'),
                    'credit': r.get('credit'),
                    'running_balance': r.get('balance'),
                }
                for r in statement.get('timeline', [])
            ])
        except Exception:
            # If any of the normalizations fail, keep rendering with whatever is available.
            pass

        common_ctx['printed_by'] = request.user if request.user.is_authenticated else None
        if request.user.is_authenticated:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ACTION_UPDATE,
                    model_name='CustomerStatement',
                    app_label='sales',
                    object_id=str(customer.pk),
                    object_repr=str(customer),
                    changes={'print': 'customer_statement'}
                )
            except Exception:
                pass
        return render(request, 'sales/customer_statement_print.html', common_ctx)
    return render(request, 'sales/customer_statement.html', common_ctx)


@login_required
def customer_statement_print(request, customer_id):
    """Named print endpoint used by templates.

    We keep the main rendering logic inside `customer_statement` and just
    forward to it by ensuring `print=1` is present.
    """
    from django.urls import reverse

    base = reverse('sales:customer_statement', args=[customer_id])
    q = request.GET.copy()
    q['print'] = '1'
    qs = q.urlencode()
    return redirect(f'{base}?{qs}' if qs else base)


@login_required
def customer_statement_pdf(request, customer_id):
    """Export customer statement as PDF.

    If PDF libraries aren't available, fall back to the print-friendly HTML.
    """
    customer = get_object_or_404(Customer, pk=customer_id)
    if not request.user.has_perm('sales.print_customerstatement'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(_t('ليست لديك صلاحية طباعة كشف الحساب'))

    # Reuse the same data builder used by the statement page.
    from django.utils.dateparse import parse_date
    date_from = parse_date(request.GET.get('date_from')) if request.GET.get('date_from') else None
    date_to = parse_date(request.GET.get('date_to')) if request.GET.get('date_to') else None
    if date_from and not date_to:
        date_to = date.today()
    statement = build_customer_statement(customer, date_from=date_from, date_to=date_to)
    timeline = statement.get('timeline', [])
    total_debit = sum(r.get('debit') or 0 for r in timeline)
    total_credit = sum(r.get('credit') or 0 for r in timeline)

    class _TxList(list):
        def count(self):  # type: ignore[override]
            return len(self)

    ctx = {
        'customer': customer,
        'date_from': statement.get('date_from') or date_from,
        'date_to': statement.get('date_to') or date_to or date.today(),
        'today': timezone.now(),
        'opening_balance': statement.get('opening_balance'),
        'closing_balance': statement.get('balance'),
        'total_debit': total_debit,
        'total_credit': total_credit,
        'transactions': _TxList([
            {
                'date': r.get('date'),
                'reference': r.get('number'),
                'description': r.get('description'),
                'debit': r.get('debit'),
                'credit': r.get('credit'),
                'running_balance': r.get('balance'),
            }
            for r in timeline
        ]),
    }

    from django.template.loader import render_to_string
    html = render_to_string('sales/customer_statement_print.html', ctx, request=request)

    # Try WeasyPrint, then xhtml2pdf, else fall back to HTML.
    filename = f'statement_{customer.id}.pdf'
    try:
        from weasyprint import HTML  # type: ignore
        pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp
    except Exception:
        pass
    try:
        from xhtml2pdf import pisa  # type: ignore
        from io import BytesIO
        buf = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buf, encoding='utf-8')
        if not getattr(pisa_status, 'err', 1):
            resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
            resp['Content-Disposition'] = f'attachment; filename="{filename}"'
            return resp
    except Exception:
        pass

    # Fallback: render the print page so the user can "Print to PDF".
    messages.info(request, _t('يمكنك استخدام Ctrl+P ثم اختيار حفظ كـ PDF'))
    return render(request, 'sales/customer_statement_print.html', ctx)


@login_required
def payment_cancel(request, payment_id):
    pay = get_object_or_404(InvoicePayment.objects.select_related('journal_entry'), pk=payment_id)
    if not request.user.has_perm('sales.cancel_invoicepayment'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(_t('ليست لديك صلاحية إلغاء الدفعة'))
    if request.method == 'POST':
        reason = (request.POST.get('reason') or '').strip()
        try:
            cancel_payment(pay, request.user, reason=reason)
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ACTION_UPDATE,
                    model_name='InvoicePayment',
                    app_label='sales',
                    object_id=str(pay.pk),
                    object_repr=str(pay),
                    changes={'cancel': reason or 'no-reason'}
                )
            except Exception:
                pass
            messages.success(request, _t('تم إلغاء الدفعة وإنشاء قيد عكسي'))
            return redirect('sales:payment_receipt_print', payment_id=pay.id)
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'sales/payment_cancel_confirm.html', {'payment': pay})


def _format_receipt_line(label: str, value: str, width: int = 42) -> str:
    label = str(label).strip()
    value = str(value).strip()
    padding = max(1, width - len(label) - len(value))
    return f"{label}{' ' * padding}{value}"


def _build_invoice_receipt_text(invoice, *, subtotal, tax_amount, total, balance, width: int = 42) -> str:
    """تجهيز نص إيصال مبسط للطابعات الحرارية."""

    def center(text: str) -> str:
        text = str(text)
        pad = max(0, (width - len(text)) // 2)
        return f"{' ' * pad}{text}"

    def fmt_amount(amount) -> str:
        return f"{Decimal(amount):,.2f}"

    lines = [
        center("فاتورة بيع"),
        center(f"رقم: {invoice.number}"),
        center(invoice.date.strftime('%Y-%m-%d %H:%M')),
        "-" * width,
        f"عميل: {invoice.customer.name if invoice.customer else 'عميل نقدي'}",
        "-" * width,
    ]

    for item in invoice.items.all():
        lines.append(str(item.product.name)[:width])
        lines.append(_format_receipt_line(f"{item.quantity} x {fmt_amount(item.price)}", fmt_amount(item.subtotal), width))

    lines.extend([
        "-" * width,
        _format_receipt_line("الإجمالي", fmt_amount(subtotal), width),
        _format_receipt_line("الضريبة", fmt_amount(tax_amount), width),
        _format_receipt_line("الخصم", fmt_amount(invoice.discount or 0), width),
        _format_receipt_line("الإجمالي النهائي", fmt_amount(total), width),
        _format_receipt_line("المدفوع", fmt_amount(invoice.paid or 0), width),
        _format_receipt_line("المتبقي", fmt_amount(balance), width),
        "-" * width,
        center("شكراً لزيارتكم"),
    ])

    return "\n".join(lines) + "\n"


@login_required
def invoice_thermal_print(request, pk):
    """طباعة الفاتورة بتنسيق حراري 80mm"""
    invoice = get_object_or_404(Invoice.objects.prefetch_related('items__product'), pk=pk)
    
    # حساب الإجماليات
    subtotal = sum(item.subtotal for item in invoice.items.all())
    tax_rate = Decimal('0.14')  # 14% VAT
    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount - invoice.discount
    balance = total - invoice.paid
    
    # جلب بيانات الشركة من قاعدة البيانات
    company_name = 'Tony ERP'
    company_address = ''
    company_phone = ''
    tax_number = ''
    company_logo = None
    try:
        from core.models import Company
        company = Company.objects.first()
        if company:
            company_name = company.name or 'Tony ERP'
            company_address = company.address or ''
            company_phone = company.phone or ''
            tax_number = company.tax_id or ''
            if company.logo:
                company_logo = company.logo.url
    except:
        pass
    
    context = {
        'invoice': invoice,
        'now': timezone.now(),
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'total': total,
        'balance': balance,
        # معلومات الشركة من قاعدة البيانات
        'company_name': company_name,
        'company_address': company_address,
        'company_phone': company_phone,
        'tax_number': tax_number,
        'company_logo': company_logo,
    }

    # طباعة مباشرة للطابعة الحرارية عند تمرير direct=1
    if request.GET.get('direct') == '1':
        printer = (
            PrinterConfiguration.objects.filter(document_type='receipt', is_active=True)
            .order_by('-is_default')
            .first()
        )

        if not printer:
            return JsonResponse({'success': False, 'message': _t('لا توجد طابعة إيصالات افتراضية مفعّلة')}, status=404)

        receipt_text = _build_invoice_receipt_text(
            invoice,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            balance=balance,
        )

        success, message = send_to_thermal_printer(
            receipt_text,
            printer,
            raw_text=True,
            title=_t('فاتورة مبيعات')
        )

        status_code = 200 if success else 500
        return JsonResponse(
            {
                'success': success,
                'message': message,
                'printer': printer.name,
                'printer_type': printer.printer_type,
                'connection_type': printer.connection_type,
            },
            status=status_code,
        )
    
    return render(request, 'sales/invoice_thermal_print.html', context)


# ==================== Customer Quick APIs ====================

from core.auth_helpers import login_or_jwt_required

@login_or_jwt_required
def customer_search_api(request):
    """البحث عن عميل برقم الموبايل أو الاسم أو الكود
    GET ?q=<search_term>&type=phone|name|all
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all').lower()
    
    if not query or len(query) < 2:
        return JsonResponse({'success': False, 'message': _t('أدخل كلمة بحث (حرفين على الأقل)'), 'customers': []})
    
    customers = Customer.objects.all()
    
    if search_type == 'phone':
        # البحث برقم الهاتف فقط
        customers = customers.filter(phone__icontains=query)
    elif search_type == 'name':
        # البحث بالاسم فقط
        customers = customers.filter(name__icontains=query)
    else:
        # البحث في جميع الحقول
        customers = customers.filter(
            Q(phone__icontains=query) |
            Q(name__icontains=query) |
            Q(email__icontains=query)
        )
    
    customers = customers[:20]  # حد أقصى 20 نتيجة
    
    results = []
    for c in customers:
        results.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone or '',
            'email': c.email or '',
            'address': c.address or '',
            'is_key_account': c.is_key_account,
        })
    
    return JsonResponse({
        'success': True,
        'count': len(results),
        'customers': results
    })


@login_required
@require_POST
def customer_quick_create_api(request):
    """إنشاء عميل جديد بسرعة
    POST: name, phone, email, address
    """
    import json
    
    # محاولة قراءة البيانات من JSON أو form-data
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}
    else:
        data = request.POST
    
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    address = data.get('address', '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': _t('اسم العميل مطلوب')}, status=400)
    
    # التحقق من عدم وجود عميل بنفس رقم الهاتف
    if phone:
        existing = Customer.objects.filter(phone=phone).first()
        if existing:
            return JsonResponse({
                'success': False, 
                'message': _t('يوجد عميل مسجل بهذا الرقم: %(name)s') % {'name': existing.name},
                'existing_customer': {
                    'id': existing.id,
                    'name': existing.name,
                    'phone': existing.phone,
                }
            }, status=409)  # Conflict
    
    try:
        customer = Customer.objects.create(
            name=name,
            phone=phone,
            email=email,
            address=address,
        )
        
        # إنشاء سجل في AuditLog
        try:
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ACTION_CREATE,
                model_name='Customer',
                app_label='partners',
                object_id=str(customer.pk),
                object_repr=str(customer),
                changes={'quick_create': True, 'from': 'invoice_form'}
            )
        except Exception:
            pass
        
        return JsonResponse({
            'success': True,
            'message': _t('تم إنشاء العميل بنجاح'),
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone or '',
                'email': customer.email or '',
                'address': customer.address or '',
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': _t('خطأ في إنشاء العميل: %(error)s') % {'error': str(e)}}, status=500)


@login_required
def customer_details_api(request, customer_id):
    """جلب تفاصيل عميل محدد
    GET /sales/api/customers/<customer_id>/
    """
    try:
        customer = get_object_or_404(Customer, pk=customer_id)
        
        # حساب إجمالي المبيعات والمستحق
        from django.db.models import Sum
        invoices = Invoice.objects.filter(customer=customer, is_deleted=False)
        total_sales = invoices.aggregate(total=Sum('total'))['total'] or 0
        total_paid = invoices.aggregate(paid=Sum('paid'))['paid'] or 0
        balance = float(total_sales) - float(total_paid)
        
        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone or '',
                'email': customer.email or '',
                'address': customer.address or '',
                'is_key_account': customer.is_key_account,
                'total_sales': float(total_sales),
                'total_paid': float(total_paid),
                'balance': balance,
                'invoices_count': invoices.count(),
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def next_invoice_numbers_view(request):
    """
    عرض أرقام الفواتير التالية التي سيتم توليدها
    مفيد للتخطيط المسبق للمعاملات المحاسبية
    """
    from .next_invoice_number import preview_invoice_numbers
    
    next_numbers = preview_invoice_numbers()
    
    return render(request, 'sales/next_invoice_numbers.html', {
        'next_numbers': next_numbers,
    })


@login_required
def next_invoice_numbers_api(request):
    """
    API للحصول على أرقام الفواتير التالية بصيغة JSON
    """
    from .next_invoice_number import preview_invoice_numbers
    
    next_numbers = preview_invoice_numbers()
    
    return JsonResponse({
        'success': True,
        'next_numbers': next_numbers,
    })
