from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import UtilityMeter, UtilityReading, EnergyConsumptionAnalysis
from django.db.models import Sum, Avg

@login_required
def dashboard(request):
    meters = UtilityMeter.objects.filter(is_active=True)
    recent_readings = UtilityReading.objects.select_related('meter').order_by('-reading_date')[:10]
    analyses = EnergyConsumptionAnalysis.objects.order_by('-period_end')[:5]
    
    total_meters = meters.count()
    total_readings = UtilityReading.objects.count()
    avg_consumption = UtilityReading.objects.aggregate(avg=Avg('consumption'))['avg'] or 0
    
    context = {
        'page_title': 'إدارة الطاقة',
        'meters': meters,
        'recent_readings': recent_readings,
        'analyses': analyses,
        'total_meters': total_meters,
        'total_readings': total_readings,
        'avg_consumption': avg_consumption,
    }
    return render(request, 'energy_management/dashboard.html', context)

@login_required
def meter_list(request):
    meters = UtilityMeter.objects.all().order_by('meter_number')
    paginator = Paginator(meters, 20)
    page = request.GET.get('page')
    meters = paginator.get_page(page)
    
    context = {
        'page_title': 'قائمة العدادات',
        'meters': meters,
    }
    return render(request, 'energy_management/meter_list.html', context)

@login_required
def meter_create(request):
    if request.method == 'POST':
        try:
            from django.utils import timezone
            meter = UtilityMeter.objects.create(
                meter_number=request.POST.get('meter_number'),
                utility_type=request.POST.get('utility_type', 'electricity'),
                location=request.POST.get('location', ''),
                installation_date=request.POST.get('installation_date', timezone.now().date()),
                is_active=True,
            )
            messages.success(request, f'تم إضافة العداد بنجاح!')
            return redirect('energy_management:meter_detail', pk=meter.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'إضافة عداد جديد',
    }
    return render(request, 'energy_management/meter_form.html', context)

@login_required
def meter_detail(request, pk):
    meter = get_object_or_404(UtilityMeter, pk=pk)
    readings = UtilityReading.objects.filter(meter=meter).order_by('-reading_date')[:20]
    
    context = {
        'page_title': f'عداد: {meter.meter_number}',
        'meter': meter,
        'readings': readings,
    }
    return render(request, 'energy_management/meter_detail.html', context)

@login_required
def meter_edit(request, pk):
    meter = get_object_or_404(UtilityMeter, pk=pk)
    
    if request.method == 'POST':
        meter.meter_number = request.POST.get('meter_number', meter.meter_number)
        meter.utility_type = request.POST.get('utility_type', meter.utility_type)
        meter.location = request.POST.get('location', meter.location)
        meter.is_active = request.POST.get('is_active') == 'on'
        meter.save()
        messages.success(request, 'تم تحديث العداد بنجاح!')
        return redirect('energy_management:meter_detail', pk=meter.id)
    
    context = {
        'page_title': f'تعديل: {meter.meter_number}',
        'meter': meter,
    }
    return render(request, 'energy_management/meter_form.html', context)

@login_required
def meter_delete(request, pk):
    meter = get_object_or_404(UtilityMeter, pk=pk)
    if request.method == 'POST':
        meter.delete()
        messages.success(request, 'تم حذف العداد بنجاح!')
        return redirect('energy_management:meter_list')
    
    context = {
        'page_title': f'حذف: {meter.name}',
        'meter': meter,
    }
    return render(request, 'energy_management/meter_confirm_delete.html', context)

@login_required
def reading_list(request):
    readings = UtilityReading.objects.select_related('meter').order_by('-reading_date')
    paginator = Paginator(readings, 20)
    page = request.GET.get('page')
    readings = paginator.get_page(page)
    
    context = {
        'page_title': 'قراءات العدادات',
        'readings': readings,
    }
    return render(request, 'energy_management/reading_list.html', context)

@login_required
def reading_create(request):
    meters = UtilityMeter.objects.filter(is_active=True)
    
    if request.method == 'POST':
        meter = get_object_or_404(UtilityMeter, pk=request.POST.get('meter'))
        reading = UtilityReading.objects.create(
            meter=meter,
            reading_date=request.POST.get('reading_date'),
            reading_value=request.POST.get('reading_value', 0),
            consumption=request.POST.get('consumption', 0),
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, f'تم تسجيل القراءة بنجاح!')
        return redirect('energy_management:meter_detail', pk=meter.id)
    
    context = {
        'page_title': 'تسجيل قراءة جديدة',
        'meters': meters,
    }
    return render(request, 'energy_management/reading_form.html', context)
