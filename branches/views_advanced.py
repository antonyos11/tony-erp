"""
واجهات عرض الفروع المتقدمة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from branches.models_advanced import (
    BranchTarget, InterBranchTransfer, InterBranchTransferItem, BranchProfitability
)
from branches.forms_advanced import BranchTargetForm, InterBranchTransferForm


# ──────────────────────────────────────
#  أهداف الفروع
# ──────────────────────────────────────
@login_required
def target_list(request):
    targets = BranchTarget.objects.select_related('branch').all()
    branch = request.GET.get('branch')
    if branch:
        targets = targets.filter(branch_id=branch)
    paginator = Paginator(targets.order_by('-period'), 20)
    targets = paginator.get_page(request.GET.get('page'))
    return render(request, 'branches/target_list.html', {
        'targets': targets,
        'page_title': 'أهداف الفروع',
    })


@login_required
def target_create(request):
    if request.method == 'POST':
        form = BranchTargetForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الهدف بنجاح')
            return redirect('branches:target_list')
    else:
        form = BranchTargetForm()
    return render(request, 'branches/target_form.html', {
        'form': form,
        'page_title': 'إضافة هدف',
    })


@login_required
def target_edit(request, pk):
    target = get_object_or_404(BranchTarget, pk=pk)
    if request.method == 'POST':
        form = BranchTargetForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الهدف بنجاح')
            return redirect('branches:target_list')
    else:
        form = BranchTargetForm(instance=target)
    return render(request, 'branches/target_form.html', {
        'form': form,
        'target': target,
        'page_title': f'تعديل هدف: {target.branch}',
    })


@login_required
def target_detail(request, pk):
    target = get_object_or_404(BranchTarget.objects.select_related('branch'), pk=pk)
    return render(request, 'branches/target_detail.html', {
        'target': target,
        'page_title': f'هدف: {target.branch}',
    })


# ──────────────────────────────────────
#  التحويلات بين الفروع
# ──────────────────────────────────────
@login_required
def inter_transfer_list(request):
    transfers = InterBranchTransfer.objects.select_related(
        'from_branch', 'to_branch', 'requested_by'
    ).all()
    status = request.GET.get('status')
    if status:
        transfers = transfers.filter(status=status)
    paginator = Paginator(transfers.order_by('-request_date'), 20)
    transfers = paginator.get_page(request.GET.get('page'))
    return render(request, 'branches/inter_transfer_list.html', {
        'transfers': transfers,
        'page_title': 'التحويلات بين الفروع',
    })


@login_required
def inter_transfer_create(request):
    if request.method == 'POST':
        form = InterBranchTransferForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.requested_by = request.user
            transfer.save()
            messages.success(request, f'تم إنشاء طلب التحويل رقم {transfer.transfer_number}')
            return redirect('branches:inter_transfer_detail', pk=transfer.pk)
    else:
        form = InterBranchTransferForm()
    return render(request, 'branches/inter_transfer_form.html', {
        'form': form,
        'page_title': 'إنشاء تحويل بين الفروع',
    })


@login_required
def inter_transfer_detail(request, pk):
    transfer = get_object_or_404(
        InterBranchTransfer.objects.select_related(
            'from_branch', 'to_branch', 'requested_by', 'approved_by', 'received_by'
        ), pk=pk
    )
    items = transfer.items.select_related('product').all()
    return render(request, 'branches/inter_transfer_detail.html', {
        'transfer': transfer,
        'items': items,
        'page_title': f'تحويل: {transfer.transfer_number}',
    })


@login_required
def inter_transfer_approve(request, pk):
    """اعتماد تحويل بين الفروع"""
    transfer = get_object_or_404(InterBranchTransfer, pk=pk)
    if request.method == 'POST':
        try:
            transfer.status = 'approved'
            transfer.approved_by = request.user
            transfer.save(update_fields=['status', 'approved_by'])
            messages.success(request, f'تم اعتماد التحويل {transfer.transfer_number}')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    return redirect('branches:inter_transfer_detail', pk=pk)


@login_required
def inter_transfer_receive(request, pk):
    """استلام تحويل بين الفروع"""
    transfer = get_object_or_404(InterBranchTransfer, pk=pk)
    if request.method == 'POST':
        try:
            transfer.status = 'received'
            transfer.received_by = request.user
            transfer.receive_date = timezone.now()
            transfer.save(update_fields=['status', 'received_by', 'receive_date'])
            messages.success(request, f'تم تأكيد استلام التحويل {transfer.transfer_number}')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    return redirect('branches:inter_transfer_detail', pk=pk)


# ──────────────────────────────────────
#  ربحية الفروع
# ──────────────────────────────────────
@login_required
def profitability_list(request):
    records = BranchProfitability.objects.select_related('branch').all()
    branch = request.GET.get('branch')
    if branch:
        records = records.filter(branch_id=branch)
    paginator = Paginator(records.order_by('-period'), 20)
    records = paginator.get_page(request.GET.get('page'))
    return render(request, 'branches/profitability_list.html', {
        'records': records,
        'page_title': 'ربحية الفروع',
    })


@login_required
def profitability_detail(request, pk):
    record = get_object_or_404(BranchProfitability.objects.select_related('branch'), pk=pk)
    return render(request, 'branches/profitability_detail.html', {
        'record': record,
        'page_title': f'ربحية {record.branch} - {record.period}',
    })
