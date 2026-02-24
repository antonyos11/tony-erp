from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Warranty, WarrantyClaim, WarrantyPolicy
from django.db.models import Count

@login_required
def dashboard(request):
    warranties = Warranty.objects.select_related('product', 'customer').order_by('-start_date')[:10]
    claims = WarrantyClaim.objects.select_related('warranty').order_by('-claim_date')[:10]
    
    total_warranties = Warranty.objects.count()
    active_warranties = Warranty.objects.filter(status='active').count()
    total_claims = WarrantyClaim.objects.count()
    pending_claims = WarrantyClaim.objects.filter(status='pending').count()
    
    context = {
        'page_title': 'إدارة الضمانات',
        'warranties': warranties,
        'claims': claims,
        'total_warranties': total_warranties,
        'active_warranties': active_warranties,
        'total_claims': total_claims,
        'pending_claims': pending_claims,
    }
    return render(request, 'warranty_management/dashboard.html', context)

@login_required
def warranty_list(request):
    warranties = Warranty.objects.all().order_by('-start_date')
    paginator = Paginator(warranties, 20)
    page = request.GET.get('page')
    warranties = paginator.get_page(page)
    
    context = {
        'page_title': 'قائمة الضمانات',
        'warranties': warranties,
    }
    return render(request, 'warranty_management/warranty_list.html', context)

@login_required
def warranty_create(request):
    if request.method == 'POST':
        try:
            warranty = Warranty.objects.create(
                warranty_number=request.POST.get('warranty_number'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                warranty_type=request.POST.get('warranty_type', 'standard'),
                status='active',
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, f'تم إنشاء الضمان بنجاح!')
            return redirect('warranty_management:warranty_detail', pk=warranty.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'إضافة ضمان جديد',
    }
    return render(request, 'warranty_management/warranty_form.html', context)

@login_required
def warranty_detail(request, pk):
    warranty = get_object_or_404(Warranty, pk=pk)
    claims = WarrantyClaim.objects.filter(warranty=warranty).order_by('-claim_date')
    
    context = {
        'page_title': f'ضمان: {warranty.warranty_number}',
        'warranty': warranty,
        'claims': claims,
    }
    return render(request, 'warranty_management/warranty_detail.html', context)

@login_required
def warranty_edit(request, pk):
    warranty = get_object_or_404(Warranty, pk=pk)
    
    if request.method == 'POST':
        warranty.warranty_number = request.POST.get('warranty_number', warranty.warranty_number)
        warranty.warranty_type = request.POST.get('warranty_type', warranty.warranty_type)
        warranty.status = request.POST.get('status', warranty.status)
        warranty.notes = request.POST.get('notes', warranty.notes)
        warranty.save()
        messages.success(request, 'تم تحديث الضمان بنجاح!')
        return redirect('warranty_management:warranty_detail', pk=warranty.id)
    
    context = {
        'page_title': f'تعديل: {warranty.warranty_number}',
        'warranty': warranty,
    }
    return render(request, 'warranty_management/warranty_form.html', context)

@login_required
def warranty_delete(request, pk):
    warranty = get_object_or_404(Warranty, pk=pk)
    if request.method == 'POST':
        warranty.delete()
        messages.success(request, 'تم حذف الضمان بنجاح!')
        return redirect('warranty_management:warranty_list')
    
    context = {
        'page_title': f'حذف: {warranty.warranty_number}',
        'warranty': warranty,
    }
    return render(request, 'warranty_management/warranty_confirm_delete.html', context)

@login_required
def claim_list(request):
    claims = WarrantyClaim.objects.select_related('warranty').order_by('-claim_date')
    paginator = Paginator(claims, 20)
    page = request.GET.get('page')
    claims = paginator.get_page(page)
    
    context = {
        'page_title': 'مطالبات الضمان',
        'claims': claims,
    }
    return render(request, 'warranty_management/claim_list.html', context)

@login_required
def claim_create(request):
    warranties = Warranty.objects.filter(status='active')
    
    if request.method == 'POST':
        warranty = get_object_or_404(Warranty, pk=request.POST.get('warranty'))
        claim = WarrantyClaim.objects.create(
            warranty=warranty,
            claim_number=request.POST.get('claim_number'),
            description=request.POST.get('description', ''),
            status='pending',
        )
        messages.success(request, f'تم تقديم المطالبة بنجاح!')
        return redirect('warranty_management:claim_detail', pk=claim.id)
    
    context = {
        'page_title': 'تقديم مطالبة جديدة',
        'warranties': warranties,
    }
    return render(request, 'warranty_management/claim_form.html', context)

@login_required
def claim_detail(request, pk):
    claim = get_object_or_404(WarrantyClaim, pk=pk)
    
    context = {
        'page_title': f'مطالبة: {claim.claim_number}',
        'claim': claim,
    }
    return render(request, 'warranty_management/claim_detail.html', context)
