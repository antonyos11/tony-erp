"""
Views وحدة الفروع الموحدة - محدث
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal

from .models import (
    Branch, BranchStaff, BranchTransfer, BranchTransferItem,
    POSDevice, BranchAttendance, BranchExpense, BranchPurchase,
    BranchPayroll, BranchShift, BranchStockMovement
)
from .forms import (
    BranchForm, BranchStaffForm, BranchTransferForm, BranchTransferItemFormSet,
    POSDeviceForm, BranchExpenseForm, BranchPayrollForm, BranchShiftForm
)


def generate_transfer_number():
    today = timezone.now()
    prefix = f"TR{today.strftime('%Y%m%d')}"
    last = BranchTransfer.objects.filter(transfer_number__startswith=prefix).order_by('-transfer_number').first()
    new_num = int(last.transfer_number[-4:]) + 1 if last else 1
    return f"{prefix}{new_num:04d}"


# ==================== Dashboard ====================

@login_required
def branches_dashboard(request):
    """لوحة تحكم الفروع المتقدمة"""
    # إحصائيات الفروع
    total_branches = Branch.objects.count()
    active_branches_qs = Branch.objects.filter(is_active=True).annotate(
        staff_count=Count('staff', distinct=True),
        pos_devices_count=Count('pos_devices', distinct=True)
    )
    
    # إحصائيات التحويلات
    transfers_stats = {
        'pending': BranchTransfer.objects.filter(status='pending').count(),
        'in_transit': BranchTransfer.objects.filter(status='in_transit').count(),
        'received': BranchTransfer.objects.filter(status='received').count(),
        'total_value': BranchTransfer.objects.filter(
            status__in=['approved', 'in_transit', 'received']
        ).aggregate(total=Sum('total_value'))['total'] or 0
    }
    
    stats = {
        'total_branches': total_branches,
        'active_branches': active_branches_qs.count(),
        'inactive_branches': total_branches - active_branches_qs.count(),
        'total_staff': BranchStaff.objects.count(),
        'total_pos_devices': POSDevice.objects.count(),
        'active_pos_devices': POSDevice.objects.filter(is_active=True).count(),
        'active_transfers': BranchTransfer.objects.filter(
            status__in=['pending', 'approved', 'in_transit']
        ).count(),
    }
    
    # آخر العمليات
    recent_transfers = BranchTransfer.objects.select_related(
        'from_branch', 'to_branch'
    ).prefetch_related('items').order_by('-created_at')[:5]
    
    recent_expenses = BranchExpense.objects.select_related(
        'branch'
    ).order_by('-created_at')[:5]
    
    context = {
        'stats': stats,
        'recent_transfers': recent_transfers,
        'recent_expenses': recent_expenses,
        'active_branches': active_branches_qs[:10],
    }
    
    return render(request, 'branches/branches_dashboard.html', context)


# ==================== الفروع ====================

@login_required
def branch_list(request):
    """قائمة الفروع المحدثة"""
    branches = Branch.objects.annotate(
        staff_count=Count('staff', distinct=True),
        pos_devices_count=Count('pos_devices', distinct=True),
        transfers_out_count=Count('transfers_out', distinct=True),
        transfers_in_count=Count('transfers_in', distinct=True)
    ).select_related('manager', 'parent_branch')
    
    # Filters
    branch_type = request.GET.get('branch_type')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if branch_type:
        branches = branches.filter(branch_type=branch_type)
    if status:
        branches = branches.filter(status=status)
    if search:
        branches = branches.filter(
            Q(name__icontains=search) | Q(code__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(branches, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'branches/branch_list.html', {
        'branches': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1
    })


@login_required
def branch_detail(request, pk):
    """تفاصيل الفرع المحدثة"""
    branch = get_object_or_404(Branch, pk=pk)
    
    # إحصائيات الفرع
    staff = BranchStaff.objects.filter(branch=branch).select_related('employee')
    pos_devices = POSDevice.objects.filter(branch=branch)
    
    # التحويلات
    transfers_out = BranchTransfer.objects.filter(from_branch=branch).select_related(
        'to_branch'
    ).prefetch_related('items')[:10]
    
    transfers_in = BranchTransfer.objects.filter(to_branch=branch).select_related(
        'from_branch'
    ).prefetch_related('items')[:10]
    
    # المصروفات الأخيرة
    recent_expenses = BranchExpense.objects.filter(branch=branch).order_by('-date')[:10]
    
    # الإحصائيات
    stats = {
        'staff_count': staff.count(),
        'pos_devices_count': pos_devices.count(),
        'transfers_out_count': transfers_out.count(),
        'transfers_in_count': transfers_in.count(),
        'total_expenses': recent_expenses.aggregate(total=Sum('amount'))['total'] or 0,
    }
    
    context = {
        'branch': branch,
        'stats': stats,
        'staff': staff,
        'pos_devices': pos_devices,
        'transfers_out': transfers_out,
        'transfers_in': transfers_in,
        'recent_expenses': recent_expenses,
    }
    
    return render(request, 'branches/branch_detail.html', context)


@login_required
def branch_create(request):
    """إنشاء فرع جديد"""
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.created_by = request.user
            branch.save()
            messages.success(request, 'تم إنشاء الفرع بنجاح')
            return redirect('branches:branch_detail', pk=branch.pk)
    else:
        form = BranchForm()
    
    return render(request, 'branches/branch_form.html', {
        'form': form,
        'branch': None
    })


@login_required
def branch_edit(request, pk):
    """تعديل فرع"""
    branch = get_object_or_404(Branch, pk=pk)
    
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث بيانات الفرع بنجاح')
            return redirect('branches:branch_detail', pk=branch.pk)
    else:
        form = BranchForm(instance=branch)
    
    return render(request, 'branches/branch_form.html', {
        'form': form,
        'branch': branch
    })


@login_required
def branch_delete(request, pk):
    """حذف فرع"""
    branch = get_object_or_404(Branch, pk=pk)
    
    if request.method == 'POST':
        branch.delete()
        messages.success(request, 'تم حذف الفرع بنجاح')
        return redirect('branches:branch_list')
    
    return render(request, 'branches/branch_confirm_delete.html', {
        'branch': branch
    })


# ==================== التحويلات ====================

@login_required
def transfer_list(request):
    """قائمة التحويلات المحدثة"""
    transfers = BranchTransfer.objects.select_related(
        'from_branch', 'to_branch', 'created_by'
    ).prefetch_related('items')
    
    # Filters
    from_branch = request.GET.get('from_branch')
    to_branch = request.GET.get('to_branch')
    status = request.GET.get('status')
    
    if from_branch:
        transfers = transfers.filter(from_branch_id=from_branch)
    if to_branch:
        transfers = transfers.filter(to_branch_id=to_branch)
    if status:
        transfers = transfers.filter(status=status)
    
    # إحصائيات
    stats = {
        'pending': transfers.filter(status='pending').count(),
        'in_transit': transfers.filter(status='in_transit').count(),
        'received': transfers.filter(status='received').count(),
        'total_value': transfers.filter(
            status__in=['approved', 'in_transit', 'received']
        ).aggregate(total=Sum('total_value'))['total'] or 0
    }
    
    # Pagination
    paginator = Paginator(transfers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    branches = Branch.objects.filter(is_active=True)
    
    return render(request, 'branches/transfer_list.html', {
        'transfers': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'stats': stats,
        'branches': branches,
    })


@login_required
def transfer_detail(request, pk):
    """تفاصيل التحويل"""
    transfer = get_object_or_404(
        BranchTransfer.objects.select_related(
            'from_branch', 'to_branch', 'created_by'
        ).prefetch_related('items__product'),
        pk=pk
    )
    
    context = {
        'transfer': transfer,
    }
    
    return render(request, 'branches/transfer_detail.html', context)


@login_required
def transfer_create(request):
    """إنشاء تحويل جديد"""
    if request.method == 'POST':
        form = BranchTransferForm(request.POST)
        formset = BranchTransferItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                transfer = form.save(commit=False)
                transfer.created_by = request.user
                transfer.transfer_number = generate_transfer_number()
                transfer.save()
                
                items = formset.save(commit=False)
                total = Decimal('0')
                for item in items:
                    item.transfer = transfer
                    item.save()
                    total += item.total_price
                
                transfer.total_value = total
                transfer.save()
                
                messages.success(request, 'تم إنشاء التحويل بنجاح')
                return redirect('branches:transfer_detail', pk=transfer.pk)
    else:
        form = BranchTransferForm()
        formset = BranchTransferItemFormSet()
    
    return render(request, 'branches/transfer_form.html', {
        'form': form,
        'formset': formset,
        'transfer': None
    })


# ==================== API Actions ====================

@login_required
def transfer_approve(request, pk):
    """اعتماد التحويل"""
    if request.method == 'POST':
        transfer = get_object_or_404(BranchTransfer, pk=pk)
        if transfer.status == 'pending':
            transfer.status = 'approved'
            transfer.approved_by = request.user
            transfer.approved_at = timezone.now()
            transfer.save()
            return JsonResponse({'status': 'success'}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'status': 'error', 'message': 'الحالة غير صحيحة'}, json_dumps_params={'ensure_ascii': False})
    return JsonResponse({'status': 'error'}, json_dumps_params={'ensure_ascii': False})


@login_required
def transfer_ship(request, pk):
    """شحن التحويل"""
    if request.method == 'POST':
        transfer = get_object_or_404(BranchTransfer, pk=pk)
        if transfer.status == 'approved':
            transfer.status = 'in_transit'
            transfer.shipped_at = timezone.now()
            transfer.save()
            return JsonResponse({'status': 'success'}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'status': 'error', 'message': 'الحالة غير صحيحة'}, json_dumps_params={'ensure_ascii': False})
    return JsonResponse({'status': 'error'}, json_dumps_params={'ensure_ascii': False})


@login_required
def transfer_receive(request, pk):
    """استلام التحويل"""
    if request.method == 'POST':
        transfer = get_object_or_404(BranchTransfer, pk=pk)
        if transfer.status == 'in_transit':
            transfer.status = 'received'
            transfer.received_by = request.user
            transfer.received_at = timezone.now()
            transfer.save()
            return JsonResponse({'status': 'success'}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'status': 'error', 'message': 'الحالة غير صحيحة'}, json_dumps_params={'ensure_ascii': False})
    return JsonResponse({'status': 'error'}, json_dumps_params={'ensure_ascii': False})


@login_required
def transfer_cancel(request, pk):
    """إلغاء التحويل"""
    if request.method == 'POST':
        transfer = get_object_or_404(BranchTransfer, pk=pk)
        if transfer.status == 'pending':
            transfer.status = 'cancelled'
            transfer.save()
            return JsonResponse({'status': 'success'}, json_dumps_params={'ensure_ascii': False})
        return JsonResponse({'status': 'error', 'message': 'لا يمكن إلغاء التحويل بعد الاعتماد'}, json_dumps_params={'ensure_ascii': False})
    return JsonResponse({'status': 'error'}, json_dumps_params={'ensure_ascii': False})


# ==================== الموظفين ====================

@login_required
def staff_list(request):
    """قائمة الموظفين"""
    staff = BranchStaff.objects.select_related('branch', 'employee')
    
    # Filters
    branch = request.GET.get('branch')
    if branch:
        staff = staff.filter(branch_id=branch)
    
    branches = Branch.objects.filter(is_active=True)
    
    return render(request, 'branches/staff_list.html', {
        'staff': staff,
        'branches': branches,
    })


@login_required
def expense_list(request):
    """قائمة المصروفات"""
    expenses = BranchExpense.objects.select_related('branch', 'created_by')
    
    # Filters
    branch = request.GET.get('branch')
    if branch:
        expenses = expenses.filter(branch_id=branch)
    
    branches = Branch.objects.filter(is_active=True)
    
    return render(request, 'branches/expense_list.html', {
        'expenses': expenses,
        'branches': branches,
    })
