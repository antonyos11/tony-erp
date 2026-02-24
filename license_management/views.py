from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import License, LicenseRenewal, GovernmentPermit
from django.utils import timezone
from datetime import timedelta

@login_required
def dashboard(request):
    licenses = License.objects.order_by('-created_at')[:10]
    permits = []
    
    total_licenses = License.objects.count()
    active_licenses = License.objects.filter(status='active').count()
    expiring_soon = License.objects.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=30),
        status='active'
    ).count()
    total_permits = 0
    
    context = {
        'page_title': 'التراخيص والتصاريح',
        'licenses': licenses,
        'permits': permits,
        'total_licenses': total_licenses,
        'active_licenses': active_licenses,
        'expiring_soon': expiring_soon,
        'total_permits': total_permits,
    }
    return render(request, 'license_management/dashboard.html', context)

@login_required
def license_list(request):
    licenses = License.objects.all().order_by('-issue_date')
    paginator = Paginator(licenses, 20)
    page = request.GET.get('page')
    licenses = paginator.get_page(page)
    
    context = {
        'page_title': 'قائمة التراخيص',
        'licenses': licenses,
    }
    return render(request, 'license_management/license_list.html', context)

@login_required
def license_create(request):
    if request.method == 'POST':
        try:
            license_obj = License.objects.create(
                license_number=request.POST.get('license_number'),
                license_type=request.POST.get('license_type', 'business'),
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                issuing_authority=request.POST.get('issuing_authority', ''),
                issue_date=request.POST.get('issue_date'),
                expiry_date=request.POST.get('expiry_date'),
                status='active',
                notes=request.POST.get('notes', ''),
                responsible_person=request.user,
            )
            messages.success(request, f'تم إنشاء الترخيص بنجاح!')
            return redirect('license_management:license_detail', pk=license_obj.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'إضافة ترخيص جديد',
    }
    return render(request, 'license_management/license_form.html', context)

@login_required
def license_detail(request, pk):
    license_obj = get_object_or_404(License, pk=pk)
    renewals = LicenseRenewal.objects.filter(license=license_obj).order_by('-renewal_date')
    
    context = {
        'page_title': f'ترخيص: {license_obj.name}',
        'license': license_obj,
        'renewals': renewals,
    }
    return render(request, 'license_management/license_detail.html', context)

@login_required
def license_edit(request, pk):
    license_obj = get_object_or_404(License, pk=pk)
    
    if request.method == 'POST':
        license_obj.license_number = request.POST.get('license_number', license_obj.license_number)
        license_obj.license_type = request.POST.get('license_type', license_obj.license_type)
        license_obj.name = request.POST.get('name', license_obj.name)
        license_obj.status = request.POST.get('status', license_obj.status)
        license_obj.notes = request.POST.get('notes', license_obj.notes)
        license_obj.save()
        messages.success(request, 'تم تحديث الترخيص بنجاح!')
        return redirect('license_management:license_detail', pk=license_obj.id)
    
    context = {
        'page_title': f'تعديل: {license_obj.name}',
        'license': license_obj,
    }
    return render(request, 'license_management/license_form.html', context)

@login_required
def license_delete(request, pk):
    license_obj = get_object_or_404(License, pk=pk)
    if request.method == 'POST':
        license_obj.delete()
        messages.success(request, 'تم حذف الترخيص بنجاح!')
        return redirect('license_management:license_list')
    
    context = {
        'page_title': f'حذف: {license_obj.name}',
        'license': license_obj,
    }
    return render(request, 'license_management/license_confirm_delete.html', context)
