# -*- coding: utf-8 -*-
"""
Views موصول التحضير والاستماد
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
import json
import csv
from decimal import Decimal

from .models import (
    PreparationRequest, PreparationItem, PreparationApproval,
    ApprovalDocument, ApprovalDocumentItem, DocumentApproval
)
from .forms import (
    PreparationRequestForm, PreparationItemFormSet,
    ApprovalDocumentForm, ApprovalDocumentItemFormSet,
    ApprovalActionForm, PreparationFilterForm, ApprovalFilterForm
)
from .services import PreparationService, ApprovalDocumentService, DashboardService


# ==================== لوحات التحكم ====================

@login_required
def preparation_dashboard(request):
    """لوحة تحكم موصول التحضير"""
    context = {
        'title': _('موصول التحضير'),
        'summary': DashboardService.get_preparation_summary(request.user),
        'stats': PreparationService.get_statistics(),
    }
    
    # طلبات التحضير الأخيرة
    recent_preparations = PreparationRequest.objects.order_by('-created_at')[:10]
    context['recent_preparations'] = recent_preparations
    
    # الطلبات العاجلة
    urgent = PreparationRequest.objects.filter(
        priority='urgent',
        status__in=['pending', 'in_progress']
    ).order_by('-created_at')[:5]
    context['urgent_preparations'] = urgent
    
    # المتأخرة
    overdue = PreparationRequest.objects.filter(
        required_date__lt=timezone.now().date(),
        status__in=['pending', 'in_progress']
    ).order_by('required_date')[:5]
    context['overdue_preparations'] = overdue
    
    return render(request, 'mosool/preparation_dashboard.html', context)


@login_required
def approval_dashboard(request):
    """لوحة تحكم موصول الاستماد"""
    context = {
        'title': _('موصول الاستماد'),
        'summary': DashboardService.get_approval_summary(request.user),
        'stats': ApprovalDocumentService.get_statistics(),
    }
    
    # مستندات في انتظار اعتمادي
    pending_for_me = ApprovalDocumentService.get_pending_for_user(request.user)
    context['pending_for_me'] = pending_for_me[:10]
    context['pending_count'] = len(pending_for_me)
    
    # المستندات الأخيرة
    recent_docs = ApprovalDocument.objects.order_by('-created_at')[:10]
    context['recent_documents'] = recent_docs
    
    # المستندات المعتمدة اليوم
    today = timezone.now().date()
    approved_today = ApprovalDocument.objects.filter(
        status='approved',
        approved_at__date=today
    ).order_by('-approved_at')[:5]
    context['approved_today'] = approved_today
    
    return render(request, 'mosool/approval_dashboard.html', context)


# ==================== طلبات التحضير ====================

@login_required
def preparation_list(request):
    """قائمة طلبات التحضير"""
    form = PreparationFilterForm(request.GET)
    queryset = PreparationRequest.objects.select_related(
        'requested_by', 'department', 'assigned_to'
    ).prefetch_related('items')
    
    # تطبيق الفلاتر
    if form.is_valid():
        if form.cleaned_data.get('search'):
            search = form.cleaned_data['search']
            queryset = queryset.filter(
                Q(number__icontains=search) |
                Q(title__icontains=search)
            )
        if form.cleaned_data.get('status'):
            queryset = queryset.filter(status=form.cleaned_data['status'])
        if form.cleaned_data.get('request_type'):
            queryset = queryset.filter(request_type=form.cleaned_data['request_type'])
        if form.cleaned_data.get('priority'):
            queryset = queryset.filter(priority=form.cleaned_data['priority'])
        if form.cleaned_data.get('date_from'):
            queryset = queryset.filter(request_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            queryset = queryset.filter(request_date__lte=form.cleaned_data['date_to'])
    
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(queryset, 20)
    page = request.GET.get('page', 1)
    preparations = paginator.get_page(page)
    
    context = {
        'title': _('طلبات التحضير'),
        'preparations': preparations,
        'filter_form': form,
    }
    return render(request, 'mosool/preparation_list.html', context)


@login_required
def preparation_create(request):
    """إنشاء طلب تحضير جديد"""
    if request.method == 'POST':
        form = PreparationRequestForm(request.POST, request.FILES)
        formset = PreparationItemFormSet(request.POST, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                preparation = form.save(commit=False)
                preparation.requested_by = request.user
                preparation.save()
                
                formset.instance = preparation
                formset.save()
                
                # تحديث المجموع
                preparation.estimated_total = sum(
                    item.estimated_amount for item in preparation.items.all()
                )
                preparation.save(update_fields=['estimated_total'])
                
                messages.success(request, _('تم إنشاء طلب التحضير بنجاح'))
                return redirect('core:preparation_detail', pk=preparation.pk)
    else:
        form = PreparationRequestForm()
        formset = PreparationItemFormSet(prefix='items')
    
    context = {
        'title': _('طلب تحضير جديد'),
        'form': form,
        'formset': formset,
    }
    return render(request, 'mosool/preparation_form.html', context)


@login_required
def preparation_detail(request, pk):
    """تفاصيل طلب التحضير"""
    preparation = get_object_or_404(
        PreparationRequest.objects.select_related(
            'requested_by', 'department', 'cost_center', 'project', 'assigned_to'
        ).prefetch_related('items', 'approvals'),
        pk=pk
    )
    
    context = {
        'title': f'طلب التحضير {preparation.number}',
        'preparation': preparation,
        'items': preparation.items.all(),
        'approvals': preparation.approvals.select_related('approved_by').order_by('-created_at'),
        'can_edit': preparation.status == 'draft' and preparation.requested_by == request.user,
        'can_submit': preparation.status == 'draft',
        'can_approve': request.user.has_perm('core.can_approve_preparation'),
        'can_process': request.user.has_perm('core.can_process_preparation'),
    }
    return render(request, 'mosool/preparation_detail.html', context)


@login_required
def preparation_edit(request, pk):
    """تعديل طلب التحضير"""
    preparation = get_object_or_404(PreparationRequest, pk=pk)
    
    # التحقق من الصلاحيات
    if preparation.status != 'draft' or preparation.requested_by != request.user:
        messages.error(request, _('لا يمكن تعديل هذا الطلب'))
        return redirect('core:preparation_detail', pk=pk)
    
    if request.method == 'POST':
        form = PreparationRequestForm(request.POST, request.FILES, instance=preparation)
        formset = PreparationItemFormSet(request.POST, instance=preparation, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                preparation = form.save()
                formset.save()
                
                preparation.estimated_total = sum(
                    item.estimated_amount for item in preparation.items.all()
                )
                preparation.save(update_fields=['estimated_total'])
                
                messages.success(request, _('تم تحديث طلب التحضير'))
                return redirect('core:preparation_detail', pk=pk)
    else:
        form = PreparationRequestForm(instance=preparation)
        formset = PreparationItemFormSet(instance=preparation, prefix='items')
    
    context = {
        'title': f'تعديل طلب التحضير {preparation.number}',
        'form': form,
        'formset': formset,
        'preparation': preparation,
    }
    return render(request, 'mosool/preparation_form.html', context)


@login_required
@require_POST
def preparation_submit(request, pk):
    """تقديم طلب التحضير للمراجعة"""
    preparation = get_object_or_404(PreparationRequest, pk=pk)
    
    if preparation.submit():
        messages.success(request, _('تم تقديم الطلب للمراجعة'))
    else:
        messages.error(request, _('لا يمكن تقديم هذا الطلب'))
    
    return redirect('core:preparation_detail', pk=pk)


@login_required
@require_POST
@permission_required('core.can_process_preparation', raise_exception=True)
def preparation_start(request, pk):
    """بدء معالجة طلب التحضير"""
    preparation = get_object_or_404(PreparationRequest, pk=pk)
    
    if preparation.start_processing(request.user):
        messages.success(request, _('تم بدء معالجة الطلب'))
    else:
        messages.error(request, _('لا يمكن بدء معالجة هذا الطلب'))
    
    return redirect('core:preparation_detail', pk=pk)


@login_required
@require_POST
def preparation_complete(request, pk):
    """إكمال طلب التحضير"""
    preparation = get_object_or_404(PreparationRequest, pk=pk)
    
    if preparation.complete():
        messages.success(request, _('تم إكمال الطلب'))
    else:
        messages.error(request, _('لا يمكن إكمال هذا الطلب'))
    
    return redirect('core:preparation_detail', pk=pk)


@login_required
@require_POST
def preparation_cancel(request, pk):
    """إلغاء طلب التحضير"""
    preparation = get_object_or_404(PreparationRequest, pk=pk)
    reason = request.POST.get('reason', '')
    
    if preparation.cancel(reason):
        messages.success(request, _('تم إلغاء الطلب'))
    else:
        messages.error(request, _('لا يمكن إلغاء هذا الطلب'))
    
    return redirect('core:preparation_detail', pk=pk)


# ==================== مستندات الاستماد ====================

@login_required
def approval_list(request):
    """قائمة مستندات الاستماد"""
    form = ApprovalFilterForm(request.GET)
    queryset = ApprovalDocument.objects.select_related(
        'created_by', 'department', 'supplier', 'employee'
    ).prefetch_related('items')
    
    # تطبيق الفلاتر
    if form.is_valid():
        if form.cleaned_data.get('search'):
            search = form.cleaned_data['search']
            queryset = queryset.filter(
                Q(number__icontains=search) |
                Q(title__icontains=search)
            )
        if form.cleaned_data.get('status'):
            queryset = queryset.filter(status=form.cleaned_data['status'])
        if form.cleaned_data.get('document_type'):
            queryset = queryset.filter(document_type=form.cleaned_data['document_type'])
        if form.cleaned_data.get('date_from'):
            queryset = queryset.filter(document_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            queryset = queryset.filter(document_date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('min_amount'):
            queryset = queryset.filter(total_amount__gte=form.cleaned_data['min_amount'])
        if form.cleaned_data.get('max_amount'):
            queryset = queryset.filter(total_amount__lte=form.cleaned_data['max_amount'])
    
    queryset = queryset.order_by('-created_at')
    
    paginator = Paginator(queryset, 20)
    page = request.GET.get('page', 1)
    documents = paginator.get_page(page)
    
    context = {
        'title': _('مستندات الاستماد'),
        'documents': documents,
        'filter_form': form,
    }
    return render(request, 'mosool/approval_list.html', context)


@login_required
def approval_pending(request):
    """مستندات في انتظار اعتمادي"""
    documents = ApprovalDocumentService.get_pending_for_user(request.user)
    
    paginator = Paginator(documents, 20)
    page = request.GET.get('page', 1)
    documents_page = paginator.get_page(page)
    
    context = {
        'title': _('مستندات في انتظار الاعتماد'),
        'documents': documents_page,
        'is_pending_view': True,
    }
    return render(request, 'mosool/approval_list.html', context)


@login_required
def approval_create(request):
    """إنشاء مستند استماد جديد"""
    if request.method == 'POST':
        form = ApprovalDocumentForm(request.POST, request.FILES)
        formset = ApprovalDocumentItemFormSet(request.POST, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                document = form.save(commit=False)
                document.created_by = request.user
                document.save()
                
                formset.instance = document
                formset.save()
                
                document.total_amount = sum(
                    item.total_amount for item in document.items.all()
                )
                document.save(update_fields=['total_amount'])
                
                messages.success(request, _('تم إنشاء مستند الاستماد بنجاح'))
                return redirect('core:approval_detail', pk=document.pk)
    else:
        form = ApprovalDocumentForm()
        formset = ApprovalDocumentItemFormSet(prefix='items')
    
    context = {
        'title': _('مستند استماد جديد'),
        'form': form,
        'formset': formset,
    }
    return render(request, 'mosool/approval_form.html', context)


@login_required
def approval_detail(request, pk):
    """تفاصيل مستند الاستماد"""
    document = get_object_or_404(
        ApprovalDocument.objects.select_related(
            'created_by', 'department', 'cost_center', 'supplier', 'employee', 'preparation_request'
        ).prefetch_related('items', 'approvals'),
        pk=pk
    )
    
    # التحقق من إمكانية الاعتماد
    can_approve = False
    profile = getattr(request.user, 'profile', None)
    if profile and profile.role:
        user_level = getattr(profile.role, 'approval_level', 0)
        if document.status in ['pending', 'partial'] and user_level >= document.current_approval_level:
            can_approve = True
    
    context = {
        'title': f'مستند الاستماد {document.number}',
        'document': document,
        'items': document.items.all(),
        'approvals': document.approvals.select_related('approved_by').order_by('-created_at'),
        'can_edit': document.status == 'draft' and document.created_by == request.user,
        'can_submit': document.status == 'draft',
        'can_approve': can_approve,
        'approval_form': ApprovalActionForm() if can_approve else None,
    }
    return render(request, 'mosool/approval_detail.html', context)


@login_required
def approval_edit(request, pk):
    """تعديل مستند الاستماد"""
    document = get_object_or_404(ApprovalDocument, pk=pk)
    
    if document.status != 'draft' or document.created_by != request.user:
        messages.error(request, _('لا يمكن تعديل هذا المستند'))
        return redirect('core:approval_detail', pk=pk)
    
    if request.method == 'POST':
        form = ApprovalDocumentForm(request.POST, request.FILES, instance=document)
        formset = ApprovalDocumentItemFormSet(request.POST, instance=document, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                document = form.save()
                formset.save()
                
                document.total_amount = sum(
                    item.total_amount for item in document.items.all()
                )
                document.save(update_fields=['total_amount'])
                
                messages.success(request, _('تم تحديث المستند'))
                return redirect('core:approval_detail', pk=pk)
    else:
        form = ApprovalDocumentForm(instance=document)
        formset = ApprovalDocumentItemFormSet(instance=document, prefix='items')
    
    context = {
        'title': f'تعديل مستند الاستماد {document.number}',
        'form': form,
        'formset': formset,
        'document': document,
    }
    return render(request, 'mosool/approval_form.html', context)


@login_required
@require_POST
def approval_submit(request, pk):
    """تقديم مستند الاستماد للاعتماد"""
    document = get_object_or_404(ApprovalDocument, pk=pk)
    
    if document.submit_for_approval():
        messages.success(request, _('تم تقديم المستند للاعتماد'))
    else:
        messages.error(request, _('لا يمكن تقديم هذا المستند'))
    
    return redirect('core:approval_detail', pk=pk)


@login_required
@require_POST
def approval_action(request, pk):
    """إجراء على مستند الاستماد (موافقة/رفض)"""
    document = get_object_or_404(ApprovalDocument, pk=pk)
    form = ApprovalActionForm(request.POST)
    
    if form.is_valid():
        action = form.cleaned_data['action']
        notes = form.cleaned_data.get('notes', '')
        approved_amount = form.cleaned_data.get('approved_amount')
        
        if action == 'approve':
            success, message = ApprovalDocumentService.approve_document(
                document, request.user, notes, approved_amount
            )
        elif action == 'reject':
            success, message = ApprovalDocumentService.reject_document(
                document, request.user, notes
            )
        else:
            success = False
            message = _('إجراء غير صالح')
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    else:
        messages.error(request, _('بيانات غير صالحة'))
    
    return redirect('core:approval_detail', pk=pk)


@login_required
@require_POST
def approval_cancel(request, pk):
    """إلغاء مستند الاستماد"""
    document = get_object_or_404(ApprovalDocument, pk=pk)
    reason = request.POST.get('reason', '')
    
    if document.cancel(reason):
        messages.success(request, _('تم إلغاء المستند'))
    else:
        messages.error(request, _('لا يمكن إلغاء هذا المستند'))
    
    return redirect('core:approval_detail', pk=pk)


# ==================== التحويل والربط ====================

@login_required
@require_POST
def convert_to_approval(request, pk):
    """تحويل طلب تحضير إلى مستند استماد"""
    preparation = get_object_or_404(PreparationRequest, pk=pk)
    document_type = request.POST.get('document_type', 'pr')
    
    document = PreparationService.convert_to_approval_document(
        preparation, request.user, document_type
    )
    
    if document:
        messages.success(request, _('تم تحويل الطلب إلى مستند استماد'))
        return redirect('core:approval_detail', pk=document.pk)
    else:
        messages.error(request, _('لا يمكن تحويل هذا الطلب'))
        return redirect('core:preparation_detail', pk=pk)


# ==================== API ====================

@login_required
@require_GET
def api_preparation_stats(request):
    """API إحصائيات التحضير"""
    stats = PreparationService.get_statistics()
    return JsonResponse(stats)


@login_required
@require_GET
def api_approval_stats(request):
    """API إحصائيات الاستماد"""
    stats = ApprovalDocumentService.get_statistics()
    return JsonResponse(stats, safe=False)


@login_required
@require_GET
def api_dashboard(request):
    """API لوحة التحكم الشاملة"""
    data = DashboardService.get_combined_dashboard(request.user)
    return JsonResponse(data)


# ==================== التصدير ====================

@login_required
def export_preparations_csv(request):
    """تصدير طلبات التحضير إلى CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="preparations.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'رقم الطلب', 'العنوان', 'النوع', 'الحالة', 'الأولوية',
        'القسم', 'المبلغ التقديري', 'تاريخ الطلب', 'مقدم الطلب'
    ])
    
    preparations = PreparationRequest.objects.select_related(
        'requested_by', 'department'
    ).order_by('-created_at')
    
    for prep in preparations:
        writer.writerow([
            prep.number,
            prep.title,
            prep.get_request_type_display(),
            prep.get_status_display(),
            prep.get_priority_display(),
            prep.department.name if prep.department else '',
            prep.estimated_total,
            prep.request_date,
            prep.requested_by.get_full_name() or prep.requested_by.username,
        ])
    
    return response


@login_required
def export_approvals_csv(request):
    """تصدير مستندات الاستماد إلى CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="approvals.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'رقم المستند', 'العنوان', 'النوع', 'الحالة',
        'المبلغ', 'المبلغ المعتمد', 'القسم', 'تاريخ المستند', 'منشئ المستند'
    ])
    
    documents = ApprovalDocument.objects.select_related(
        'created_by', 'department'
    ).order_by('-created_at')
    
    for doc in documents:
        writer.writerow([
            doc.number,
            doc.title,
            doc.get_document_type_display(),
            doc.get_status_display(),
            doc.total_amount,
            doc.approved_amount,
            doc.department.name if doc.department else '',
            doc.document_date,
            doc.created_by.get_full_name() or doc.created_by.username,
        ])
    
    return response
