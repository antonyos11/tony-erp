# -*- coding: utf-8 -*-
"""
Views موديول الاستيراد والتصدير
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import csv

from .models import (
    ShippingAgent, ExportOrder, ExportOrderItem, ExportCertificate,
    FinancialApproval, PreExportInvoice,
    CustomsClearance, ImportOrder, ImportOrderItem, ImportCertificate,
    ReleaseOrder, ImportWaiver
)
from .forms import (
    ShippingAgentForm, ExportOrderForm, ExportOrderItemFormSet,
    FinancialApprovalForm, PreExportInvoiceForm, ExportCertificateForm,
    CustomsClearanceForm, ImportOrderForm, ImportOrderItemFormSet,
    ReleaseOrderForm, ImportWaiverForm, ImportCertificateForm
)


# ============= وكلاء الشحن =============

@login_required
def shipping_agent_list(request):
    """قائمة وكلاء الشحن"""
    agents = ShippingAgent.objects.all()
    
    # البحث
    search = request.GET.get('search', '')
    if search:
        agents = agents.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    # الفلترة
    agent_type = request.GET.get('type', '')
    if agent_type:
        agents = agents.filter(agent_type=agent_type)
    
    is_active = request.GET.get('active', '')
    if is_active:
        agents = agents.filter(is_active=(is_active == '1'))
    
    # الترقيم
    paginator = Paginator(agents, 25)
    page = request.GET.get('page', 1)
    agents = paginator.get_page(page)
    
    context = {
        'agents': agents,
        'search': search,
        'agent_types': ShippingAgent.AgentType.choices,
        'selected_type': agent_type,
        'title': _('وكلاء الشحن'),
    }
    return render(request, 'import_export/shipping_agent_list.html', context)


@login_required
def shipping_agent_create(request):
    """إنشاء وكيل شحن جديد"""
    if request.method == 'POST':
        form = ShippingAgentForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            agent.created_by = request.user
            agent.save()
            messages.success(request, _('تم إنشاء وكيل الشحن بنجاح'))
            return redirect('import_export:shipping_agent_list')
    else:
        form = ShippingAgentForm()
    
    return render(request, 'import_export/shipping_agent_form.html', {
        'form': form,
        'title': _('إنشاء وكيل شحن جديد'),
    })


@login_required
def shipping_agent_detail(request, pk):
    """تفاصيل وكيل الشحن"""
    agent = get_object_or_404(ShippingAgent, pk=pk)
    
    # الإحصائيات
    export_orders = ExportOrder.objects.filter(shipping_agent=agent)
    import_orders = ImportOrder.objects.filter(shipping_agent=agent)
    
    context = {
        'agent': agent,
        'export_orders_count': export_orders.count(),
        'import_orders_count': import_orders.count(),
        'total_export_value': export_orders.aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_import_value': import_orders.aggregate(total=Sum('total_cost'))['total'] or 0,
        'recent_exports': export_orders.order_by('-created_at')[:5],
        'recent_imports': import_orders.order_by('-created_at')[:5],
        'title': agent.name,
    }
    return render(request, 'import_export/shipping_agent_detail.html', context)


@login_required
def shipping_agent_edit(request, pk):
    """تعديل وكيل شحن"""
    agent = get_object_or_404(ShippingAgent, pk=pk)
    
    if request.method == 'POST':
        form = ShippingAgentForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث بيانات وكيل الشحن'))
            return redirect('import_export:shipping_agent_detail', pk=pk)
    else:
        form = ShippingAgentForm(instance=agent)
    
    return render(request, 'import_export/shipping_agent_form.html', {
        'form': form,
        'agent': agent,
        'title': _('تعديل وكيل الشحن'),
    })


@login_required
def shipping_agent_delete(request, pk):
    """حذف وكيل شحن"""
    agent = get_object_or_404(ShippingAgent, pk=pk)
    
    if request.method == 'POST':
        try:
            agent.delete()
            messages.success(request, _('تم حذف وكيل الشحن'))
        except Exception as e:
            messages.error(request, _('لا يمكن حذف وكيل الشحن - مرتبط بعمليات'))
        return redirect('import_export:shipping_agent_list')
    
    return render(request, 'import_export/confirm_delete.html', {
        'object': agent,
        'title': _('حذف وكيل الشحن'),
    })


# ============= طلبات التصدير =============

@login_required
def export_order_list(request):
    """قائمة طلبات التصدير"""
    orders = ExportOrder.objects.select_related('customer', 'shipping_agent', 'destination_country')
    
    # البحث
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(reference__icontains=search)
        )
    
    # الفلترة
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    # الترتيب
    orders = orders.order_by('-created_at')
    
    # الترقيم
    paginator = Paginator(orders, 25)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)
    
    # الإحصائيات
    stats = ExportOrder.objects.aggregate(
        total_count=Count('id'),
        total_value=Sum('total_amount'),
        pending_count=Count('id', filter=Q(status='pending')),
        shipped_count=Count('id', filter=Q(status='shipped')),
    )
    
    context = {
        'orders': orders,
        'search': search,
        'statuses': ExportOrder.Status.choices,
        'selected_status': status,
        'stats': stats,
        'title': _('طلبات التصدير'),
    }
    return render(request, 'import_export/export_order_list.html', context)


@login_required
def export_order_create(request):
    """إنشاء طلب تصدير جديد"""
    if request.method == 'POST':
        form = ExportOrderForm(request.POST)
        formset = ExportOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.save()
            
            formset.instance = order
            formset.save()
            
            order.calculate_totals()
            
            messages.success(request, _('تم إنشاء طلب التصدير بنجاح'))
            return redirect('import_export:export_order_detail', pk=order.pk)
    else:
        form = ExportOrderForm()
        formset = ExportOrderItemFormSet()
    
    return render(request, 'import_export/export_order_form.html', {
        'form': form,
        'formset': formset,
        'title': _('طلب تصدير جديد'),
    })


@login_required
def export_order_detail(request, pk):
    """تفاصيل طلب التصدير"""
    order = get_object_or_404(
        ExportOrder.objects.select_related('customer', 'shipping_agent', 'destination_country'),
        pk=pk
    )
    
    context = {
        'order': order,
        'items': order.items.select_related('product'),
        'certificates': order.certificates.all(),
        'financial_approvals': order.financial_approvals.all(),
        'proforma_invoices': order.proforma_invoices.all(),
        'title': f'طلب تصدير {order.number}',
    }
    return render(request, 'import_export/export_order_detail.html', context)


@login_required
def export_order_edit(request, pk):
    """تعديل طلب تصدير"""
    order = get_object_or_404(ExportOrder, pk=pk)
    
    if order.status not in ['draft', 'pending']:
        messages.error(request, _('لا يمكن تعديل طلب تم الموافقة عليه أو شحنه'))
        return redirect('import_export:export_order_detail', pk=pk)
    
    if request.method == 'POST':
        form = ExportOrderForm(request.POST, instance=order)
        formset = ExportOrderItemFormSet(request.POST, instance=order)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            order.calculate_totals()
            
            messages.success(request, _('تم تحديث طلب التصدير'))
            return redirect('import_export:export_order_detail', pk=pk)
    else:
        form = ExportOrderForm(instance=order)
        formset = ExportOrderItemFormSet(instance=order)
    
    return render(request, 'import_export/export_order_form.html', {
        'form': form,
        'formset': formset,
        'order': order,
        'title': _('تعديل طلب التصدير'),
    })


# ============= الموافقة المالية =============

@login_required
def financial_approval_list(request):
    """قائمة الموافقات المالية"""
    approvals = FinancialApproval.objects.select_related('export_order', 'requested_by', 'approved_by')
    
    status = request.GET.get('status', '')
    if status:
        approvals = approvals.filter(status=status)
    
    paginator = Paginator(approvals.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    approvals = paginator.get_page(page)
    
    context = {
        'approvals': approvals,
        'statuses': FinancialApproval.Status.choices,
        'selected_status': status,
        'title': _('الموافقات المالية'),
    }
    return render(request, 'import_export/financial_approval_list.html', context)


@login_required
def financial_approval_create(request, export_order_id=None):
    """إنشاء طلب موافقة مالية"""
    export_order = None
    if export_order_id:
        export_order = get_object_or_404(ExportOrder, pk=export_order_id)
    
    if request.method == 'POST':
        form = FinancialApprovalForm(request.POST)
        if form.is_valid():
            approval = form.save(commit=False)
            approval.requested_by = request.user
            if export_order:
                approval.export_order = export_order
            approval.save()
            messages.success(request, _('تم إنشاء طلب الموافقة المالية'))
            return redirect('import_export:financial_approval_list')
    else:
        initial = {}
        if export_order:
            initial = {
                'export_order': export_order,
                'requested_amount': export_order.total_amount,
                'currency': export_order.currency,
            }
        form = FinancialApprovalForm(initial=initial)
    
    return render(request, 'import_export/financial_approval_form.html', {
        'form': form,
        'export_order': export_order,
        'title': _('طلب موافقة مالية'),
    })


@login_required
def financial_approval_detail(request, pk):
    """تفاصيل الموافقة المالية"""
    approval = get_object_or_404(FinancialApproval, pk=pk)
    
    return render(request, 'import_export/financial_approval_detail.html', {
        'approval': approval,
        'title': f'موافقة مالية {approval.number}',
    })


@login_required
def financial_approval_edit(request, pk):
    """تعديل الموافقة المالية"""
    approval = get_object_or_404(FinancialApproval, pk=pk)
    
    if approval.status == 'approved':
        messages.error(request, _('لا يمكن تعديل موافقة تم اعتمادها'))
        return redirect('import_export:financial_approval_detail', pk=pk)
    
    if request.method == 'POST':
        form = FinancialApprovalForm(request.POST, instance=approval)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الموافقة المالية'))
            return redirect('import_export:financial_approval_detail', pk=pk)
    else:
        form = FinancialApprovalForm(instance=approval)
    
    return render(request, 'import_export/financial_approval_form.html', {
        'form': form,
        'approval': approval,
        'title': _('تعديل الموافقة المالية'),
    })


@login_required
def financial_approval_print(request, pk):
    """طباعة الموافقة المالية"""
    approval = get_object_or_404(FinancialApproval, pk=pk)
    
    return render(request, 'import_export/financial_approval_print.html', {
        'approval': approval,
        'title': f'طباعة موافقة مالية {approval.number}',
    })


@login_required  
def financial_approval_action(request, pk, action):
    """إجراء على الموافقة المالية"""
    approval = get_object_or_404(FinancialApproval, pk=pk)
    
    if action == 'approve':
        approval.status = 'approved'
        approval.approved_by = request.user
        approval.approval_date = timezone.now().date()
        approval.approved_amount = approval.requested_amount
        approval.save()
        messages.success(request, _('تمت الموافقة'))
    elif action == 'reject':
        approval.status = 'rejected'
        approval.approved_by = request.user
        approval.approval_date = timezone.now().date()
        approval.rejection_reason = request.POST.get('reason', '')
        approval.save()
        messages.warning(request, _('تم الرفض'))
    
    return redirect('import_export:financial_approval_detail', pk=pk)


# ============= الفواتير المبدئية =============

@login_required
def pre_export_invoice_list(request):
    """قائمة الفواتير المبدئية"""
    invoices = PreExportInvoice.objects.select_related('export_order', 'created_by')
    
    paginator = Paginator(invoices.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    invoices = paginator.get_page(page)
    
    return render(request, 'import_export/pre_export_invoice_list.html', {
        'invoices': invoices,
        'title': _('الفواتير المبدئية'),
    })


@login_required
def pre_export_invoice_create(request, export_order_id=None):
    """إنشاء فاتورة مبدئية"""
    export_order = None
    if export_order_id:
        export_order = get_object_or_404(ExportOrder, pk=export_order_id)
    
    if request.method == 'POST':
        form = PreExportInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            if export_order:
                invoice.export_order = export_order
                invoice.subtotal = export_order.subtotal
            invoice.save()
            messages.success(request, _('تم إنشاء الفاتورة المبدئية'))
            return redirect('import_export:pre_export_invoice_list')
    else:
        initial = {}
        if export_order:
            initial = {
                'export_order': export_order,
                'subtotal': export_order.subtotal,
                'shipping_cost': export_order.shipping_cost,
                'currency': export_order.currency,
            }
        form = PreExportInvoiceForm(initial=initial)
    
    return render(request, 'import_export/pre_export_invoice_form.html', {
        'form': form,
        'export_order': export_order,
        'title': _('فاتورة مبدئية جديدة'),
    })


@login_required
def pre_export_invoice_detail(request, pk):
    """تفاصيل الفاتورة المبدئية"""
    invoice = get_object_or_404(PreExportInvoice, pk=pk)
    
    return render(request, 'import_export/pre_export_invoice_detail.html', {
        'invoice': invoice,
        'title': f'فاتورة مبدئية {invoice.number}',
    })


# ============= شهادات التصدير =============

@login_required
def export_certificate_list(request):
    """قائمة شهادات التصدير"""
    certificates = ExportCertificate.objects.select_related('export_order')
    
    cert_type = request.GET.get('type', '')
    if cert_type:
        certificates = certificates.filter(certificate_type=cert_type)
    
    paginator = Paginator(certificates.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    certificates = paginator.get_page(page)
    
    return render(request, 'import_export/export_certificate_list.html', {
        'certificates': certificates,
        'certificate_types': ExportCertificate.CertificateType.choices,
        'selected_type': cert_type,
        'title': _('شهادات التصدير'),
    })


@login_required
def export_certificate_create(request, export_order_id=None):
    """إنشاء شهادة تصدير"""
    export_order = None
    if export_order_id:
        export_order = get_object_or_404(ExportOrder, pk=export_order_id)
    
    if request.method == 'POST':
        form = ExportCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            cert = form.save(commit=False)
            if export_order:
                cert.export_order = export_order
            cert.save()
            messages.success(request, _('تم إنشاء الشهادة'))
            return redirect('import_export:export_certificate_list')
    else:
        initial = {'export_order': export_order} if export_order else {}
        form = ExportCertificateForm(initial=initial)
    
    return render(request, 'import_export/export_certificate_form.html', {
        'form': form,
        'export_order': export_order,
        'title': _('شهادة تصدير جديدة'),
    })


# ============= المخلصون الجمركيون =============

@login_required
def customs_clearance_list(request):
    """قائمة المخلصين الجمركيين"""
    clearances = CustomsClearance.objects.all()
    
    search = request.GET.get('search', '')
    if search:
        clearances = clearances.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search) |
            Q(license_number__icontains=search)
        )
    
    paginator = Paginator(clearances, 25)
    page = request.GET.get('page', 1)
    clearances = paginator.get_page(page)
    
    return render(request, 'import_export/customs_clearance_list.html', {
        'clearances': clearances,
        'search': search,
        'title': _('المخلصون الجمركيون'),
    })


@login_required
def customs_clearance_create(request):
    """إنشاء مخلص جمركي"""
    if request.method == 'POST':
        form = CustomsClearanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إنشاء المخلص الجمركي'))
            return redirect('import_export:customs_clearance_list')
    else:
        form = CustomsClearanceForm()
    
    return render(request, 'import_export/customs_clearance_form.html', {
        'form': form,
        'title': _('مخلص جمركي جديد'),
    })


@login_required
def customs_clearance_detail(request, pk):
    """تفاصيل المخلص الجمركي"""
    clearance = get_object_or_404(CustomsClearance, pk=pk)
    
    import_orders = ImportOrder.objects.filter(customs_clearance=clearance)
    
    return render(request, 'import_export/customs_clearance_detail.html', {
        'clearance': clearance,
        'import_orders': import_orders[:10],
        'total_orders': import_orders.count(),
        'title': clearance.name,
    })


@login_required
def customs_clearance_edit(request, pk):
    """تعديل مخلص جمركي"""
    clearance = get_object_or_404(CustomsClearance, pk=pk)
    
    if request.method == 'POST':
        form = CustomsClearanceForm(request.POST, instance=clearance)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث المخلص الجمركي'))
            return redirect('import_export:customs_clearance_detail', pk=pk)
    else:
        form = CustomsClearanceForm(instance=clearance)
    
    return render(request, 'import_export/customs_clearance_form.html', {
        'form': form,
        'clearance': clearance,
        'title': _('تعديل المخلص الجمركي'),
    })


@login_required
def customs_clearance_delete(request, pk):
    """حذف مخلص جمركي"""
    clearance = get_object_or_404(CustomsClearance, pk=pk)
    
    if request.method == 'POST':
        try:
            clearance.delete()
            messages.success(request, _('تم حذف المخلص الجمركي'))
        except Exception as e:
            messages.error(request, _('لا يمكن حذف المخلص الجمركي - مرتبط بعمليات'))
        return redirect('import_export:customs_clearance_list')
    
    return render(request, 'import_export/confirm_delete.html', {
        'object': clearance,
        'title': _('حذف المخلص الجمركي'),
    })


# ============= أوامر الاستيراد =============

@login_required
def import_order_list(request):
    """قائمة أوامر الاستيراد"""
    orders = ImportOrder.objects.select_related('supplier', 'shipping_agent', 'customs_clearance')
    
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(number__icontains=search) |
            Q(supplier__name__icontains=search) |
            Q(bl_number__icontains=search)
        )
    
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    orders = orders.order_by('-created_at')
    
    paginator = Paginator(orders, 25)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)
    
    stats = ImportOrder.objects.aggregate(
        total_count=Count('id'),
        total_value=Sum('total_cost'),
        clearing_count=Count('id', filter=Q(status='clearing')),
        arrived_count=Count('id', filter=Q(status='arrived')),
    )
    
    return render(request, 'import_export/import_order_list.html', {
        'orders': orders,
        'search': search,
        'statuses': ImportOrder.Status.choices,
        'selected_status': status,
        'stats': stats,
        'title': _('أوامر الاستيراد'),
    })


@login_required
def import_order_create(request):
    """إنشاء أمر استيراد"""
    if request.method == 'POST':
        form = ImportOrderForm(request.POST)
        formset = ImportOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.save()
            
            formset.instance = order
            formset.save()
            
            messages.success(request, _('تم إنشاء أمر الاستيراد'))
            return redirect('import_export:import_order_detail', pk=order.pk)
    else:
        form = ImportOrderForm()
        formset = ImportOrderItemFormSet()
    
    return render(request, 'import_export/import_order_form.html', {
        'form': form,
        'formset': formset,
        'title': _('أمر استيراد جديد'),
    })


@login_required
def import_order_detail(request, pk):
    """تفاصيل أمر الاستيراد"""
    order = get_object_or_404(
        ImportOrder.objects.select_related('supplier', 'shipping_agent', 'customs_clearance'),
        pk=pk
    )
    
    return render(request, 'import_export/import_order_detail.html', {
        'order': order,
        'items': order.items.select_related('product'),
        'certificates': order.certificates.all(),
        'release_orders': order.release_orders.all(),
        'waivers': order.waivers.all(),
        'title': f'أمر استيراد {order.number}',
    })


@login_required
def import_order_edit(request, pk):
    """تعديل أمر استيراد"""
    order = get_object_or_404(ImportOrder, pk=pk)
    
    if order.status in ['delivered', 'cancelled']:
        messages.error(request, _('لا يمكن تعديل هذا الأمر'))
        return redirect('import_export:import_order_detail', pk=pk)
    
    if request.method == 'POST':
        form = ImportOrderForm(request.POST, instance=order)
        formset = ImportOrderItemFormSet(request.POST, instance=order)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, _('تم تحديث أمر الاستيراد'))
            return redirect('import_export:import_order_detail', pk=pk)
    else:
        form = ImportOrderForm(instance=order)
        formset = ImportOrderItemFormSet(instance=order)
    
    return render(request, 'import_export/import_order_form.html', {
        'form': form,
        'formset': formset,
        'order': order,
        'title': _('تعديل أمر الاستيراد'),
    })


@login_required
def import_order_delete(request, pk):
    """حذف أمر استيراد"""
    order = get_object_or_404(ImportOrder, pk=pk)
    
    if request.method == 'POST':
        try:
            order.delete()
            messages.success(request, _('تم حذف أمر الاستيراد'))
        except Exception as e:
            messages.error(request, _('لا يمكن حذف أمر الاستيراد'))
        return redirect('import_export:import_order_list')
    
    return render(request, 'import_export/confirm_delete.html', {
        'object': order,
        'title': _('حذف أمر الاستيراد'),
    })


@login_required
def import_order_print(request, pk):
    """طباعة أمر الاستيراد"""
    order = get_object_or_404(
        ImportOrder.objects.select_related('supplier', 'shipping_agent', 'customs_clearance'),
        pk=pk
    )
    
    return render(request, 'import_export/import_order_print.html', {
        'order': order,
        'items': order.items.select_related('product'),
        'title': f'طباعة أمر استيراد {order.number}',
    })


@login_required
def import_order_status(request, pk, status):
    """تغيير حالة أمر الاستيراد"""
    order = get_object_or_404(ImportOrder, pk=pk)
    
    if request.method == 'POST':
        valid_statuses = dict(ImportOrder.Status.choices).keys()
        if status in valid_statuses:
            order.status = status
            order.save()
            messages.success(request, _('تم تحديث حالة الأمر'))
        else:
            messages.error(request, _('حالة غير صالحة'))
    
    return redirect('import_export:import_order_detail', pk=pk)


# ============= شهادات الاستيراد =============

@login_required
def import_certificate_list(request):
    """قائمة شهادات الاستيراد"""
    certificates = ImportCertificate.objects.select_related('import_order')
    
    paginator = Paginator(certificates.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    certificates = paginator.get_page(page)
    
    return render(request, 'import_export/import_certificate_list.html', {
        'certificates': certificates,
        'certificate_types': ImportCertificate.CertificateType.choices,
        'title': _('شهادات الاستيراد'),
    })


@login_required
def import_certificate_create(request, import_order_id=None):
    """إنشاء شهادة استيراد"""
    import_order = None
    if import_order_id:
        import_order = get_object_or_404(ImportOrder, pk=import_order_id)
    
    if request.method == 'POST':
        form = ImportCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            cert = form.save(commit=False)
            if import_order:
                cert.import_order = import_order
            cert.save()
            messages.success(request, _('تم إنشاء الشهادة'))
            return redirect('import_export:import_certificate_list')
    else:
        initial = {'import_order': import_order} if import_order else {}
        form = ImportCertificateForm(initial=initial)
    
    return render(request, 'import_export/import_certificate_form.html', {
        'form': form,
        'import_order': import_order,
        'title': _('شهادة استيراد جديدة'),
    })


# ============= أذون الإفراج =============

@login_required
def release_order_list(request):
    """قائمة أذون الإفراج"""
    orders = ReleaseOrder.objects.select_related('import_order', 'created_by')
    
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    paginator = Paginator(orders.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)
    
    return render(request, 'import_export/release_order_list.html', {
        'orders': orders,
        'statuses': ReleaseOrder.Status.choices,
        'selected_status': status,
        'title': _('أذون الإفراج'),
    })


@login_required
def release_order_create(request, import_order_id=None):
    """إنشاء إذن إفراج"""
    import_order = None
    if import_order_id:
        import_order = get_object_or_404(ImportOrder, pk=import_order_id)
    
    if request.method == 'POST':
        form = ReleaseOrderForm(request.POST)
        if form.is_valid():
            release = form.save(commit=False)
            release.created_by = request.user
            if import_order:
                release.import_order = import_order
            release.save()
            messages.success(request, _('تم إنشاء إذن الإفراج'))
            return redirect('import_export:release_order_list')
    else:
        initial = {'import_order': import_order} if import_order else {}
        form = ReleaseOrderForm(initial=initial)
    
    return render(request, 'import_export/release_order_form.html', {
        'form': form,
        'import_order': import_order,
        'title': _('إذن إفراج جديد'),
    })


@login_required
def release_order_detail(request, pk):
    """تفاصيل إذن الإفراج"""
    release = get_object_or_404(ReleaseOrder, pk=pk)
    
    return render(request, 'import_export/release_order_detail.html', {
        'release': release,
        'title': f'إذن إفراج {release.number}',
    })


# ============= التنازلات =============

@login_required
def import_waiver_list(request):
    """قائمة التنازلات"""
    waivers = ImportWaiver.objects.select_related('import_order', 'created_by')
    
    paginator = Paginator(waivers.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    waivers = paginator.get_page(page)
    
    return render(request, 'import_export/import_waiver_list.html', {
        'waivers': waivers,
        'title': _('التنازلات'),
    })


@login_required
def import_waiver_create(request, import_order_id=None):
    """إنشاء تنازل"""
    import_order = None
    if import_order_id:
        import_order = get_object_or_404(ImportOrder, pk=import_order_id)
    
    if request.method == 'POST':
        form = ImportWaiverForm(request.POST)
        if form.is_valid():
            waiver = form.save(commit=False)
            waiver.created_by = request.user
            if import_order:
                waiver.import_order = import_order
            waiver.save()
            messages.success(request, _('تم إنشاء التنازل'))
            return redirect('import_export:import_waiver_list')
    else:
        initial = {'import_order': import_order} if import_order else {}
        form = ImportWaiverForm(initial=initial)
    
    return render(request, 'import_export/import_waiver_form.html', {
        'form': form,
        'import_order': import_order,
        'title': _('تنازل جديد'),
    })


@login_required
def import_waiver_detail(request, pk):
    """تفاصيل التنازل"""
    waiver = get_object_or_404(ImportWaiver, pk=pk)
    
    return render(request, 'import_export/import_waiver_detail.html', {
        'waiver': waiver,
        'title': f'تنازل {waiver.number}',
    })


# ============= التقارير =============

@login_required
def import_reports(request):
    """تقارير الاستيراد"""
    # إحصائيات عامة
    stats = {
        'total_orders': ImportOrder.objects.count(),
        'total_value': ImportOrder.objects.aggregate(total=Sum('total_cost'))['total'] or 0,
        'pending_clearance': ImportOrder.objects.filter(status__in=['arrived', 'clearing']).count(),
        'total_duties': ImportOrder.objects.aggregate(total=Sum('customs_duties'))['total'] or 0,
    }
    
    # أوامر حسب الحالة
    by_status = ImportOrder.objects.values('status').annotate(
        count=Count('id'),
        total=Sum('total_cost')
    )
    
    # أوامر حسب المورد
    by_supplier = ImportOrder.objects.values('supplier__name').annotate(
        count=Count('id'),
        total=Sum('total_cost')
    ).order_by('-total')[:10]
    
    return render(request, 'import_export/import_reports.html', {
        'stats': stats,
        'by_status': by_status,
        'by_supplier': by_supplier,
        'title': _('تقارير الاستيراد'),
    })


@login_required
def export_reports(request):
    """تقارير التصدير"""
    stats = {
        'total_orders': ExportOrder.objects.count(),
        'total_value': ExportOrder.objects.aggregate(total=Sum('total_amount'))['total'] or 0,
        'shipped': ExportOrder.objects.filter(status='shipped').count(),
        'delivered': ExportOrder.objects.filter(status='delivered').count(),
    }
    
    by_status = ExportOrder.objects.values('status').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    )
    
    by_destination = ExportOrder.objects.values('destination_country__name').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('-total')[:10]
    
    return render(request, 'import_export/export_reports.html', {
        'stats': stats,
        'by_status': by_status,
        'by_destination': by_destination,
        'title': _('تقارير التصدير'),
    })


# ============= تصدير البيانات =============

@login_required
def export_to_csv(request, model_type):
    """تصدير البيانات إلى CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{model_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
    response.write('\ufeff')  # BOM for Excel
    
    writer = csv.writer(response)
    
    if model_type == 'shipping_agents':
        writer.writerow(['الكود', 'الاسم', 'النوع', 'الهاتف', 'البريد', 'المدينة', 'نشط'])
        for agent in ShippingAgent.objects.all():
            writer.writerow([
                agent.code, agent.name, agent.get_agent_type_display(),
                agent.phone, agent.email, agent.city, 'نعم' if agent.is_active else 'لا'
            ])
    
    elif model_type == 'export_orders':
        writer.writerow(['الرقم', 'التاريخ', 'العميل', 'الوجهة', 'الحالة', 'المبلغ'])
        for order in ExportOrder.objects.select_related('customer', 'destination_country'):
            writer.writerow([
                order.number, order.order_date, order.customer.name if order.customer else '',
                order.destination_country.name if order.destination_country else '',
                order.get_status_display(), order.total_amount
            ])
    
    elif model_type == 'import_orders':
        writer.writerow(['الرقم', 'التاريخ', 'المورد', 'المنشأ', 'الحالة', 'التكلفة'])
        for order in ImportOrder.objects.select_related('supplier', 'origin_country'):
            writer.writerow([
                order.number, order.order_date, order.supplier.name if order.supplier else '',
                order.origin_country.name if order.origin_country else '',
                order.get_status_display(), order.total_cost
            ])
    
    return response
