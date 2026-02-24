"""
عروض نظام إدارة الشحن - Tony ERP
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import (
    ShippingCompany, ShippingZone, ShippingRate, Shipment,
    ShipmentTracking, ShippingPickup, ShippingInvoice, ShippingInvoiceItem
)
from .forms import (
    ShippingCompanyForm, ShippingZoneForm, ShippingRateForm, ShipmentForm,
    ShipmentTrackingForm, ShippingPickupForm, ShippingInvoiceForm
)


@login_required
def dashboard(request):
    """لوحة تحكم الشحن"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # إحصائيات عامة
    total_shipments = Shipment.objects.count()
    pending_shipments = Shipment.objects.filter(status='pending').count()
    in_transit_shipments = Shipment.objects.filter(status='in_transit').count()
    delivered_today = Shipment.objects.filter(
        status='delivered',
        actual_delivery__date=today
    ).count()
    
    # إحصائيات مالية
    total_shipping_cost = Shipment.objects.aggregate(total=Sum('shipping_cost'))['total'] or 0
    pending_cod = Shipment.objects.filter(
        payment_type='cod',
        status__in=['pending', 'in_transit', 'out_for_delivery']
    ).aggregate(total=Sum('cod_amount'))['total'] or 0
    
    # شحنات حديثة
    recent_shipments = Shipment.objects.select_related('company', 'zone')[:10]
    
    # طلبات استلام معلقة
    pending_pickups = ShippingPickup.objects.filter(status='pending').count()
    
    # توزيع الشحنات حسب الحالة
    status_stats = Shipment.objects.values('status').annotate(count=Count('id'))
    
    # أفضل شركات الشحن
    top_companies = ShippingCompany.objects.annotate(
        shipment_count=Count('shipments')
    ).order_by('-shipment_count')[:5]
    
    context = {
        'total_shipments': total_shipments,
        'pending_shipments': pending_shipments,
        'in_transit_shipments': in_transit_shipments,
        'delivered_today': delivered_today,
        'total_shipping_cost': total_shipping_cost,
        'pending_cod': pending_cod,
        'recent_shipments': recent_shipments,
        'pending_pickups': pending_pickups,
        'status_stats': status_stats,
        'top_companies': top_companies,
    }
    return render(request, 'shipping/dashboard.html', context)


# ==================== شركات الشحن ====================

@login_required
def company_list(request):
    """قائمة شركات الشحن"""
    companies = ShippingCompany.objects.annotate(
        shipment_count=Count('shipments')
    ).order_by('-is_active', 'name')
    
    paginator = Paginator(companies, 20)
    page = request.GET.get('page')
    companies = paginator.get_page(page)
    
    return render(request, 'shipping/company_list.html', {'companies': companies})


@login_required
def company_create(request):
    """إضافة شركة شحن جديدة"""
    if request.method == 'POST':
        form = ShippingCompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة شركة الشحن بنجاح'))
            return redirect('shipping:company_list')
    else:
        form = ShippingCompanyForm()
    
    return render(request, 'shipping/company_form.html', {'form': form, 'title': _('إضافة شركة شحن')})


@login_required
def company_edit(request, pk):
    """تعديل شركة شحن"""
    company = get_object_or_404(ShippingCompany, pk=pk)
    if request.method == 'POST':
        form = ShippingCompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث بيانات الشركة بنجاح'))
            return redirect('shipping:company_list')
    else:
        form = ShippingCompanyForm(instance=company)
    
    return render(request, 'shipping/company_form.html', {
        'form': form, 
        'company': company,
        'title': _('تعديل شركة شحن')
    })


@login_required
def company_detail(request, pk):
    """تفاصيل شركة شحن"""
    company = get_object_or_404(ShippingCompany, pk=pk)
    shipments = company.shipments.order_by('-created_at')[:20]
    rates = company.rates.select_related('zone').order_by('zone__name')
    
    return render(request, 'shipping/company_detail.html', {
        'company': company,
        'shipments': shipments,
        'rates': rates,
    })


# ==================== مناطق الشحن ====================

@login_required
def zone_list(request):
    """قائمة مناطق الشحن"""
    zones = ShippingZone.objects.annotate(
        rate_count=Count('rates')
    ).order_by('country', 'name')
    
    return render(request, 'shipping/zone_list.html', {'zones': zones})


@login_required
def zone_create(request):
    """إضافة منطقة شحن"""
    if request.method == 'POST':
        form = ShippingZoneForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة منطقة الشحن بنجاح'))
            return redirect('shipping:zone_list')
    else:
        form = ShippingZoneForm()
    
    return render(request, 'shipping/zone_form.html', {'form': form, 'title': _('إضافة منطقة شحن')})


@login_required
def zone_edit(request, pk):
    """تعديل منطقة شحن"""
    zone = get_object_or_404(ShippingZone, pk=pk)
    if request.method == 'POST':
        form = ShippingZoneForm(request.POST, instance=zone)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث المنطقة بنجاح'))
            return redirect('shipping:zone_list')
    else:
        form = ShippingZoneForm(instance=zone)
    
    return render(request, 'shipping/zone_form.html', {'form': form, 'zone': zone, 'title': _('تعديل منطقة')})


# ==================== تعريفات الأسعار ====================

@login_required
def rate_list(request):
    """قائمة تعريفات الأسعار"""
    rates = ShippingRate.objects.select_related('company', 'zone').order_by('company', 'zone', 'weight_from')
    
    # فلترة
    company_id = request.GET.get('company')
    zone_id = request.GET.get('zone')
    
    if company_id:
        rates = rates.filter(company_id=company_id)
    if zone_id:
        rates = rates.filter(zone_id=zone_id)
    
    companies = ShippingCompany.objects.filter(is_active=True)
    zones = ShippingZone.objects.filter(is_active=True)
    
    return render(request, 'shipping/rate_list.html', {
        'rates': rates,
        'companies': companies,
        'zones': zones,
    })


@login_required
def rate_create(request):
    """إضافة تعريفة سعر"""
    if request.method == 'POST':
        form = ShippingRateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة التعريفة بنجاح'))
            return redirect('shipping:rate_list')
    else:
        form = ShippingRateForm()
    
    return render(request, 'shipping/rate_form.html', {'form': form, 'title': _('إضافة تعريفة سعر')})


@login_required
def rate_edit(request, pk):
    """تعديل تعريفة سعر"""
    rate = get_object_or_404(ShippingRate, pk=pk)
    if request.method == 'POST':
        form = ShippingRateForm(request.POST, instance=rate)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث التعريفة بنجاح'))
            return redirect('shipping:rate_list')
    else:
        form = ShippingRateForm(instance=rate)
    
    return render(request, 'shipping/rate_form.html', {'form': form, 'rate': rate, 'title': _('تعديل تعريفة')})


# ==================== الشحنات ====================

@login_required
def shipment_list(request):
    """قائمة الشحنات"""
    shipments = Shipment.objects.select_related('company', 'zone').order_by('-created_at')
    
    # فلترة
    status = request.GET.get('status')
    company_id = request.GET.get('company')
    search = request.GET.get('search')
    
    if status:
        shipments = shipments.filter(status=status)
    if company_id:
        shipments = shipments.filter(company_id=company_id)
    if search:
        shipments = shipments.filter(
            Q(tracking_number__icontains=search) |
            Q(receiver_name__icontains=search) |
            Q(receiver_phone__icontains=search)
        )
    
    paginator = Paginator(shipments, 25)
    page = request.GET.get('page')
    shipments = paginator.get_page(page)
    
    companies = ShippingCompany.objects.filter(is_active=True)
    
    return render(request, 'shipping/shipment_list.html', {
        'shipments': shipments,
        'companies': companies,
        'status_choices': Shipment.STATUS_CHOICES,
    })


def generate_tracking_number():
    """توليد رقم تتبع فريد"""
    return f"SHP-{uuid.uuid4().hex[:10].upper()}"


@login_required
def shipment_create(request):
    """إنشاء شحنة جديدة"""
    if request.method == 'POST':
        form = ShipmentForm(request.POST)
        if form.is_valid():
            shipment = form.save(commit=False)
            shipment.tracking_number = generate_tracking_number()
            shipment.created_by = request.user
            shipment.save()
            
            # إضافة سجل تتبع أول
            ShipmentTracking.objects.create(
                shipment=shipment,
                status='pending',
                description=_('تم إنشاء الشحنة'),
                updated_by=request.user
            )
            
            messages.success(request, _('تم إنشاء الشحنة بنجاح. رقم التتبع: ') + shipment.tracking_number)
            return redirect('shipping:shipment_detail', pk=shipment.pk)
    else:
        form = ShipmentForm()
    
    return render(request, 'shipping/shipment_form.html', {'form': form, 'title': _('إنشاء شحنة جديدة')})


@login_required
def shipment_edit(request, pk):
    """تعديل شحنة"""
    shipment = get_object_or_404(Shipment, pk=pk)
    if request.method == 'POST':
        form = ShipmentForm(request.POST, instance=shipment)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الشحنة بنجاح'))
            return redirect('shipping:shipment_detail', pk=pk)
    else:
        form = ShipmentForm(instance=shipment)
    
    return render(request, 'shipping/shipment_form.html', {
        'form': form, 
        'shipment': shipment,
        'title': _('تعديل شحنة')
    })


@login_required
def shipment_detail(request, pk):
    """تفاصيل شحنة"""
    shipment = get_object_or_404(Shipment, pk=pk)
    tracking_history = shipment.tracking_history.order_by('-timestamp')
    
    return render(request, 'shipping/shipment_detail.html', {
        'shipment': shipment,
        'tracking_history': tracking_history,
    })


@login_required
def shipment_update_status(request, pk):
    """تحديث حالة الشحنة"""
    shipment = get_object_or_404(Shipment, pk=pk)
    
    if request.method == 'POST':
        form = ShipmentTrackingForm(request.POST)
        if form.is_valid():
            tracking = form.save(commit=False)
            tracking.shipment = shipment
            tracking.updated_by = request.user
            tracking.save()
            
            # تحديث حالة الشحنة
            shipment.status = tracking.status
            if tracking.status == 'delivered':
                shipment.actual_delivery = timezone.now()
            elif tracking.status == 'picked_up':
                shipment.pickup_date = timezone.now()
            shipment.save()
            
            messages.success(request, _('تم تحديث حالة الشحنة بنجاح'))
            return redirect('shipping:shipment_detail', pk=pk)
    else:
        form = ShipmentTrackingForm()
    
    return render(request, 'shipping/update_status.html', {
        'form': form,
        'shipment': shipment,
    })


# ==================== طلبات الاستلام ====================

@login_required
def pickup_list(request):
    """قائمة طلبات الاستلام"""
    pickups = ShippingPickup.objects.select_related('company').order_by('-scheduled_date')
    
    status = request.GET.get('status')
    if status:
        pickups = pickups.filter(status=status)
    
    paginator = Paginator(pickups, 20)
    page = request.GET.get('page')
    pickups = paginator.get_page(page)
    
    return render(request, 'shipping/pickup_list.html', {
        'pickups': pickups,
        'status_choices': ShippingPickup.STATUS_CHOICES,
    })


def generate_pickup_number():
    """توليد رقم استلام فريد"""
    return f"PKP-{uuid.uuid4().hex[:8].upper()}"


@login_required
def pickup_create(request):
    """إنشاء طلب استلام"""
    if request.method == 'POST':
        form = ShippingPickupForm(request.POST)
        if form.is_valid():
            pickup = form.save(commit=False)
            pickup.pickup_number = generate_pickup_number()
            pickup.created_by = request.user
            pickup.save()
            messages.success(request, _('تم إنشاء طلب الاستلام بنجاح'))
            return redirect('shipping:pickup_list')
    else:
        form = ShippingPickupForm()
    
    return render(request, 'shipping/pickup_form.html', {'form': form, 'title': _('طلب استلام جديد')})


# ==================== الفواتير ====================

@login_required
def invoice_list(request):
    """قائمة فواتير الشحن"""
    invoices = ShippingInvoice.objects.select_related('company').order_by('-invoice_date')
    
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    paginator = Paginator(invoices, 20)
    page = request.GET.get('page')
    invoices = paginator.get_page(page)
    
    return render(request, 'shipping/invoice_list.html', {
        'invoices': invoices,
        'status_choices': ShippingInvoice.STATUS_CHOICES,
    })


@login_required
def invoice_detail(request, pk):
    """تفاصيل فاتورة"""
    invoice = get_object_or_404(ShippingInvoice, pk=pk)
    items = invoice.items.select_related('shipment')
    
    return render(request, 'shipping/invoice_detail.html', {
        'invoice': invoice,
        'items': items,
    })


# ==================== التتبع العام ====================

def track_shipment(request):
    """صفحة تتبع الشحنات (عامة)"""
    shipment = None
    tracking_history = None
    error = None
    
    tracking_number = request.GET.get('tracking')
    if tracking_number:
        try:
            shipment = Shipment.objects.select_related('company', 'zone').get(
                tracking_number=tracking_number
            )
            tracking_history = shipment.tracking_history.order_by('-timestamp')
        except Shipment.DoesNotExist:
            error = _('لم يتم العثور على شحنة بهذا الرقم')
    
    return render(request, 'shipping/track_shipment.html', {
        'shipment': shipment,
        'tracking_history': tracking_history,
        'error': error,
        'tracking_no': tracking_number,
    })



# ==================== التقارير ====================

@login_required
def reports_dashboard(request):
    """لوحة تقارير الشحن"""
    return render(request, 'shipping/reports_dashboard.html')


@login_required
def shipments_report(request):
    """تقرير الشحنات"""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    company_id = request.GET.get('company')
    
    shipments = Shipment.objects.select_related('company', 'zone')
    
    if from_date:
        shipments = shipments.filter(created_at__date__gte=from_date)
    if to_date:
        shipments = shipments.filter(created_at__date__lte=to_date)
    if company_id:
        shipments = shipments.filter(company_id=company_id)
    
    # إحصائيات
    stats = shipments.aggregate(
        total_count=Count('id'),
        total_cost=Sum('shipping_cost'),
        total_cod=Sum('cod_amount'),
    )
    
    status_breakdown = shipments.values('status').annotate(count=Count('id'))
    
    companies = ShippingCompany.objects.filter(is_active=True)
    
    return render(request, 'shipping/shipments_report.html', {
        'shipments': shipments[:100],
        'stats': stats,
        'status_breakdown': status_breakdown,
        'companies': companies,
    })


@login_required
def cod_report(request):
    """تقرير الدفع عند الاستلام"""
    shipments = Shipment.objects.filter(
        payment_type='cod'
    ).select_related('company').order_by('-created_at')
    
    status = request.GET.get('status')
    if status:
        shipments = shipments.filter(status=status)
    
    stats = {
        'pending': shipments.filter(status__in=['pending', 'in_transit', 'out_for_delivery']).aggregate(
            count=Count('id'), total=Sum('cod_amount')
        ),
        'delivered': shipments.filter(status='delivered').aggregate(
            count=Count('id'), total=Sum('cod_amount')
        ),
        'returned': shipments.filter(status='returned').aggregate(
            count=Count('id'), total=Sum('cod_amount')
        ),
    }
    
    return render(request, 'shipping/cod_report.html', {
        'shipments': shipments[:100],
        'stats': stats,
    })
