from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta

from .models import (
    AssetCategory,
    Asset,
    DepreciationSchedule,
    AssetMaintenance,
    AssetTransfer
)


@login_required
def asset_list(request):
    """قائمة الأصول الثابتة"""
    assets = Asset.objects.select_related('category', 'assigned_to').all()
    
    # Filters
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        assets = assets.filter(status=status_filter)
    if category_filter:
        assets = assets.filter(category_id=category_filter)
    if search:
        assets = assets.filter(
            Q(number__icontains=search) |
            Q(name__icontains=search) |
            Q(serial_number__icontains=search)
        )
    
    # Stats
    stats = {
        'total_assets': Asset.objects.count(),
        'total_cost': Asset.objects.aggregate(total=Sum('acquisition_cost'))['total'] or Decimal('0'),
        'active_assets': Asset.objects.filter(status='active').count(),
        'total_depreciation': DepreciationSchedule.objects.filter(status='posted').aggregate(
            total=Sum('depreciation_amount')
        )['total'] or Decimal('0'),
    }
    
    categories = AssetCategory.objects.filter(is_active=True)
    
    context = {
        'assets': assets,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search': search,
        'status_choices': Asset.STATUS_CHOICES,
        'categories': categories,
        'stats': stats,
    }
    return render(request, 'fixed_assets/asset_list.html', context)


@login_required
def asset_create(request):
    """إنشاء أصل جديد"""
    if request.method == 'POST':
        try:
            asset = Asset.objects.create(
                name=request.POST['name'],
                category_id=request.POST['category'],
                description=request.POST.get('description', ''),
                serial_number=request.POST.get('serial_number', ''),
                manufacturer=request.POST.get('manufacturer', ''),
                model=request.POST.get('model', ''),
                location=request.POST.get('location', ''),
                department=request.POST.get('department', ''),
                acquisition_date=request.POST['acquisition_date'],
                acquisition_cost=Decimal(request.POST['acquisition_cost']),
                depreciation_method=request.POST.get('depreciation_method', 'straight_line'),
                useful_life_years=int(request.POST.get('useful_life_years', 5)),
                salvage_value=Decimal(request.POST.get('salvage_value', '0')),
                status=request.POST.get('status', 'active'),
                created_by=request.user
            )
            
            messages.success(request, f'تم إنشاء الأصل {asset.number} بنجاح')
            return redirect('fixed_assets:asset_detail', pk=asset.pk)
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    categories = AssetCategory.objects.filter(is_active=True)
    context = {
        'categories': categories,
        'method_choices': Asset.DEPRECIATION_METHOD_CHOICES,
        'status_choices': Asset.STATUS_CHOICES,
    }
    return render(request, 'fixed_assets/asset_form.html', context)


@login_required
def asset_detail(request, pk):
    """تفاصيل أصل"""
    asset = get_object_or_404(
        Asset.objects.select_related('category', 'assigned_to', 'created_by'),
        pk=pk
    )
    
    depreciation_entries = asset.depreciation_entries.all()[:12]
    maintenance_records = asset.maintenance_records.all()[:10]
    transfers = asset.transfers.all()[:10]
    
    context = {
        'asset': asset,
        'depreciation_entries': depreciation_entries,
        'maintenance_records': maintenance_records,
        'transfers': transfers,
    }
    return render(request, 'fixed_assets/asset_detail.html', context)


@login_required
def asset_edit(request, pk):
    """تعديل أصل"""
    asset = get_object_or_404(Asset, pk=pk)
    
    if request.method == 'POST':
        try:
            asset.name = request.POST['name']
            asset.category_id = request.POST['category']
            asset.description = request.POST.get('description', '')
            asset.location = request.POST.get('location', '')
            asset.department = request.POST.get('department', '')
            asset.status = request.POST.get('status', 'active')
            asset.save()
            
            messages.success(request, 'تم تحديث الأصل بنجاح')
            return redirect('fixed_assets:asset_detail', pk=pk)
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    categories = AssetCategory.objects.filter(is_active=True)
    context = {
        'asset': asset,
        'categories': categories,
        'status_choices': Asset.STATUS_CHOICES,
    }
    return render(request, 'fixed_assets/asset_form.html', context)


@login_required
@permission_required('fixed_assets.add_depreciationschedule', raise_exception=True)
def asset_depreciate(request, pk):
    """حساب استهلاك الأصل"""
    asset = get_object_or_404(Asset, pk=pk)
    
    if request.method == 'POST':
        try:
            # Generate depreciation schedule for next period
            today = date.today()
            period_start = today.replace(day=1)
            period_end = period_start + relativedelta(months=1, days=-1)
            
            # Check if already exists
            if DepreciationSchedule.objects.filter(
                asset=asset,
                period_start=period_start
            ).exists():
                messages.warning(request, 'جدول الاستهلاك لهذه الفترة موجود بالفعل')
                return redirect('fixed_assets:asset_detail', pk=pk)
            
            # Calculate depreciation
            monthly_depreciation = asset.calculate_monthly_depreciation()
            accumulated = asset.accumulated_depreciation + monthly_depreciation
            book_value = asset.acquisition_cost - accumulated
            
            # Create entry
            schedule = DepreciationSchedule.objects.create(
                asset=asset,
                period_start=period_start,
                period_end=period_end,
                depreciation_amount=monthly_depreciation,
                accumulated_depreciation=accumulated,
                book_value=book_value
            )
            
            messages.success(request, f'تم إنشاء قسط استهلاك بقيمة {monthly_depreciation}')
            return redirect('fixed_assets:asset_detail', pk=pk)
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    return render(request, 'fixed_assets/asset_depreciate.html', {'asset': asset})


@login_required
def category_list(request):
    """قائمة تصنيفات الأصول"""
    categories = AssetCategory.objects.annotate(
        asset_count=Count('assets')
    ).all()
    
    context = {'categories': categories}
    return render(request, 'fixed_assets/category_list.html', context)


@login_required
def category_create(request):
    """إنشاء تصنيف جديد"""
    if request.method == 'POST':
        try:
            category = AssetCategory.objects.create(
                name=request.POST['name'],
                code=request.POST['code'],
                description=request.POST.get('description', ''),
                default_useful_life_years=int(request.POST.get('default_useful_life_years', 5)),
                default_salvage_value_percent=Decimal(request.POST.get('default_salvage_value_percent', '10'))
            )
            
            messages.success(request, 'تم إنشاء التصنيف بنجاح')
            return redirect('fixed_assets:category_list')
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    return render(request, 'fixed_assets/category_form.html')


@login_required
def depreciation_schedule(request):
    """جدول الاستهلاك"""
    schedules = DepreciationSchedule.objects.select_related('asset').all()
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        schedules = schedules.filter(status=status_filter)
    
    context = {
        'schedules': schedules,
        'status_filter': status_filter,
    }
    return render(request, 'fixed_assets/depreciation_schedule.html', context)


@login_required
@permission_required('fixed_assets.change_depreciationschedule', raise_exception=True)
def post_monthly_depreciation(request):
    """ترحيل الاستهلاك الشهري"""
    if request.method == 'POST':
        try:
            # Get all scheduled depreciation for posting
            schedules = DepreciationSchedule.objects.filter(status='scheduled')
            
            posted_count = 0
            for schedule in schedules:
                schedule.post_depreciation(user=request.user)
                posted_count += 1
            
            messages.success(request, f'تم ترحيل {posted_count} قسط استهلاك')
            return redirect('fixed_assets:depreciation_schedule')
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    return render(request, 'fixed_assets/post_depreciation.html')


@login_required
def maintenance_create(request, asset_id):
    """إضافة سجل صيانة"""
    asset = get_object_or_404(Asset, pk=asset_id)
    
    if request.method == 'POST':
        try:
            maintenance = AssetMaintenance.objects.create(
                asset=asset,
                maintenance_type=request.POST['maintenance_type'],
                date=request.POST.get('date', date.today()),
                description=request.POST['description'],
                cost=Decimal(request.POST.get('cost', '0')),
                performed_by=request.POST.get('performed_by', ''),
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            
            # Update asset
            asset.last_maintenance_date = maintenance.date
            asset.save(update_fields=['last_maintenance_date'])
            
            messages.success(request, 'تم إضافة سجل الصيانة')
            return redirect('fixed_assets:asset_detail', pk=asset_id)
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'asset': asset,
        'maintenance_types': AssetMaintenance.MAINTENANCE_TYPE_CHOICES,
    }
    return render(request, 'fixed_assets/maintenance_form.html', context)


@login_required
def maintenance_list(request):
    """قائمة الصيانة"""
    maintenance = AssetMaintenance.objects.select_related('asset').all()
    
    context = {'maintenance': maintenance}
    return render(request, 'fixed_assets/maintenance_list.html', context)


@login_required
def asset_transfer(request, asset_id):
    """نقل أصل"""
    asset = get_object_or_404(Asset, pk=asset_id)
    
    if request.method == 'POST':
        try:
            transfer = AssetTransfer.objects.create(
                asset=asset,
                transfer_date=request.POST.get('transfer_date', date.today()),
                from_location=asset.location,
                to_location=request.POST['to_location'],
                from_department=asset.department,
                to_department=request.POST.get('to_department', ''),
                reason=request.POST['reason'],
                notes=request.POST.get('notes', ''),
                transferred_by=request.user
            )
            
            # Update asset
            asset.location = transfer.to_location
            asset.department = transfer.to_department
            asset.save(update_fields=['location', 'department'])
            
            messages.success(request, 'تم نقل الأصل بنجاح')
            return redirect('fixed_assets:asset_detail', pk=asset_id)
        
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {'asset': asset}
    return render(request, 'fixed_assets/transfer_form.html', context)


@login_required
def asset_register(request):
    """سجل الأصول"""
    assets = Asset.objects.select_related('category').all()
    
    context = {'assets': assets}
    return render(request, 'fixed_assets/asset_register.html', context)


@login_required
def depreciation_report(request):
    """تقرير الاستهلاك"""
    from django.db.models import Sum
    
    # Summary by category
    categories = AssetCategory.objects.annotate(
        total_assets=Count('assets'),
        total_cost=Sum('assets__acquisition_cost'),
        total_depreciation=Sum('assets__depreciation_entries__depreciation_amount')
    )
    
    context = {'categories': categories}
    return render(request, 'fixed_assets/depreciation_report.html', context)
