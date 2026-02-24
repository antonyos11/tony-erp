"""
واجهات عرض المخزون المتقدمة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from inventory.models_advanced import StockAlert, LotTracking, CycleCount, CycleCountItem
from inventory.forms_advanced import StockAlertForm, LotTrackingForm, CycleCountForm


# ──────────────────────────────────────
#  تنبيهات المخزون
# ──────────────────────────────────────
@login_required
def stock_alert_list(request):
    alerts = StockAlert.objects.select_related('product', 'warehouse').all()
    severity = request.GET.get('severity')
    active = request.GET.get('active')
    if severity:
        alerts = alerts.filter(severity=severity)
    if active == '1':
        alerts = alerts.filter(is_active=True)
    elif active == '0':
        alerts = alerts.filter(is_active=False)
    paginator = Paginator(alerts.order_by('-created_at'), 20)
    alerts = paginator.get_page(request.GET.get('page'))
    return render(request, 'inventory/stock_alert_list.html', {
        'alerts': alerts,
        'page_title': 'تنبيهات المخزون',
    })


@login_required
def stock_alert_create(request):
    if request.method == 'POST':
        form = StockAlertForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء التنبيه بنجاح')
            return redirect('inventory:stock_alert_list')
    else:
        form = StockAlertForm()
    return render(request, 'inventory/stock_alert_form.html', {
        'form': form,
        'page_title': 'إضافة تنبيه مخزون',
    })


@login_required
def stock_alert_edit(request, pk):
    alert = get_object_or_404(StockAlert, pk=pk)
    if request.method == 'POST':
        form = StockAlertForm(request.POST, instance=alert)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث التنبيه بنجاح')
            return redirect('inventory:stock_alert_list')
    else:
        form = StockAlertForm(instance=alert)
    return render(request, 'inventory/stock_alert_form.html', {
        'form': form,
        'alert': alert,
        'page_title': 'تعديل التنبيه',
    })


@login_required
def stock_alert_delete(request, pk):
    alert = get_object_or_404(StockAlert, pk=pk)
    if request.method == 'POST':
        alert.delete()
        messages.success(request, 'تم حذف التنبيه بنجاح')
        return redirect('inventory:stock_alert_list')
    return render(request, 'inventory/confirm_delete.html', {
        'object': alert,
        'object_name': f'تنبيه: {alert.product}',
        'cancel_url': 'inventory:stock_alert_list',
        'page_title': 'حذف تنبيه',
    })


# ──────────────────────────────────────
#  تتبع اللوتات والدفعات
# ──────────────────────────────────────
@login_required
def lot_list(request):
    lots = LotTracking.objects.select_related('product', 'supplier').all()
    q = request.GET.get('q')
    if q:
        lots = lots.filter(
            Q(lot_number__icontains=q) |
            Q(batch_number__icontains=q) |
            Q(product__name__icontains=q)
        )
    expired = request.GET.get('expired')
    if expired == '1':
        lots = lots.filter(expiry_date__lt=timezone.now().date())
    paginator = Paginator(lots.order_by('-received_date'), 20)
    lots = paginator.get_page(request.GET.get('page'))
    return render(request, 'inventory/lot_list.html', {
        'lots': lots,
        'page_title': 'تتبع اللوتات والدفعات',
    })


@login_required
def lot_create(request):
    if request.method == 'POST':
        form = LotTrackingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة اللوت بنجاح')
            return redirect('inventory:lot_list')
    else:
        form = LotTrackingForm()
    return render(request, 'inventory/lot_form.html', {
        'form': form,
        'page_title': 'إضافة لوت / دفعة',
    })


@login_required
def lot_detail(request, pk):
    lot = get_object_or_404(LotTracking.objects.select_related('product', 'supplier'), pk=pk)
    return render(request, 'inventory/lot_detail.html', {
        'lot': lot,
        'page_title': f'لوت: {lot.lot_number}',
    })


@login_required
def lot_edit(request, pk):
    lot = get_object_or_404(LotTracking, pk=pk)
    if request.method == 'POST':
        form = LotTrackingForm(request.POST, instance=lot)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث اللوت بنجاح')
            return redirect('inventory:lot_detail', pk=lot.pk)
    else:
        form = LotTrackingForm(instance=lot)
    return render(request, 'inventory/lot_form.html', {
        'form': form,
        'lot': lot,
        'page_title': f'تعديل لوت: {lot.lot_number}',
    })


# ──────────────────────────────────────
#  الجرد الدوري
# ──────────────────────────────────────
@login_required
def cycle_count_list(request):
    counts = CycleCount.objects.select_related('warehouse', 'created_by').all()
    status = request.GET.get('status')
    if status:
        counts = counts.filter(status=status)
    paginator = Paginator(counts.order_by('-scheduled_date'), 20)
    counts = paginator.get_page(request.GET.get('page'))
    return render(request, 'inventory/cycle_count_list.html', {
        'counts': counts,
        'page_title': 'الجرد الدوري',
    })


@login_required
def cycle_count_create(request):
    if request.method == 'POST':
        form = CycleCountForm(request.POST)
        if form.is_valid():
            count = form.save(commit=False)
            count.created_by = request.user
            count.save()
            messages.success(request, f'تم إنشاء الجرد "{count.name}" بنجاح')
            return redirect('inventory:cycle_count_detail', pk=count.pk)
    else:
        form = CycleCountForm()
    return render(request, 'inventory/cycle_count_form.html', {
        'form': form,
        'page_title': 'إنشاء جرد دوري',
    })


@login_required
def cycle_count_detail(request, pk):
    count = get_object_or_404(CycleCount.objects.select_related('warehouse', 'created_by'), pk=pk)
    items = count.items.select_related('product').all()
    return render(request, 'inventory/cycle_count_detail.html', {
        'count': count,
        'items': items,
        'page_title': f'الجرد: {count.name}',
    })


@login_required
def cycle_count_complete(request, pk):
    """إتمام الجرد الدوري"""
    count = get_object_or_404(CycleCount, pk=pk)
    if request.method == 'POST':
        try:
            count.complete_count()
            messages.success(request, f'تم إتمام الجرد "{count.name}" بنجاح')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    return redirect('inventory:cycle_count_detail', pk=count.pk)
