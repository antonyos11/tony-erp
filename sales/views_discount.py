"""
Views لإشعارات الخصم للعملاء - Customer Discount Notes Views
============================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal

from .models_discount import CustomerDiscountNote
from .models import Invoice
from .forms_discount import CustomerDiscountNoteForm, CustomerDiscountNoteSearchForm
from partners.models import Customer


@login_required
def customer_discount_list(request):
    """قائمة إشعارات الخصم المسموح بها"""
    queryset = CustomerDiscountNote.objects.select_related('customer', 'invoice').all()
    
    # فلترة
    search_form = CustomerDiscountNoteSearchForm(request.GET or None)
    if search_form.is_valid():
        customer = search_form.cleaned_data.get('customer')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        if customer:
            queryset = queryset.filter(customer=customer)
        if status:
            queryset = queryset.filter(status=status)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
    
    # إحصائيات
    stats = {
        'total_count': queryset.count(),
        'total_amount': queryset.filter(status='posted').aggregate(Sum('amount'))['amount__sum'] or Decimal('0'),
        'draft_count': queryset.filter(status='draft').count(),
        'posted_count': queryset.filter(status='posted').count(),
    }
    
    # ترقيم الصفحات
    paginator = Paginator(queryset, 20)
    page = request.GET.get('page', 1)
    notes = paginator.get_page(page)
    
    return render(request, 'sales/discount/customer_discount_list.html', {
        'notes': notes,
        'search_form': search_form,
        'stats': stats,
    })


@login_required
def customer_discount_create(request):
    """إنشاء إشعار خصم مسموح به جديد"""
    if request.method == 'POST':
        form = CustomerDiscountNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.created_by = request.user
            
            # إذا كانت نسبة مئوية، احسب المبلغ
            if note.is_percentage and note.invoice:
                note.amount = (note.invoice.total * note.percentage_value) / Decimal('100')
            
            note.save()
            messages.success(request, _('تم إنشاء إشعار الخصم بنجاح: {}').format(note.number))
            return redirect('sales:customer_discount_detail', pk=note.pk)
    else:
        initial = {'date': timezone.now().date()}
        customer_id = request.GET.get('customer')
        invoice_id = request.GET.get('invoice')
        
        if customer_id:
            initial['customer'] = customer_id
        if invoice_id:
            initial['invoice'] = invoice_id
        
        form = CustomerDiscountNoteForm(initial=initial)
    
    # احتساب ملخص الأثر المالي
    customer_id = request.GET.get('customer') or request.POST.get('customer')
    financial_summary = None
    if customer_id:
        try:
            customer = Customer.objects.get(pk=customer_id)
            # حساب الرصيد الحالي
            from .models import Invoice, InvoicePayment
            invoices_total = Invoice.objects.filter(customer=customer, is_deleted=False).aggregate(
                total=Sum('cached_total')
            )['total'] or Decimal('0')
            discounts_total = Invoice.objects.filter(customer=customer, is_deleted=False).aggregate(
                total=Sum('discount')
            )['total'] or Decimal('0')
            payments_total = InvoicePayment.objects.filter(invoice__customer=customer).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            # الخصومات المسموح بها المرحّلة
            posted_discounts = CustomerDiscountNote.objects.filter(
                customer=customer, status='posted'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            financial_summary = {
                'current_balance': invoices_total - discounts_total - payments_total - posted_discounts,
                'total_discounts': posted_discounts,
                'expected_balance': invoices_total - discounts_total - payments_total - posted_discounts,
            }
        except Customer.DoesNotExist:
            pass
    
    return render(request, 'sales/discount/customer_discount_form.html', {
        'form': form,
        'is_new': True,
        'financial_summary': financial_summary,
    })


@login_required
def customer_discount_detail(request, pk):
    """تفاصيل إشعار الخصم"""
    note = get_object_or_404(CustomerDiscountNote.objects.select_related(
        'customer', 'invoice', 'created_by', 'posted_by', 'journal_entry'
    ), pk=pk)
    
    return render(request, 'sales/discount/customer_discount_detail.html', {
        'note': note,
    })


@login_required
def customer_discount_edit(request, pk):
    """تعديل إشعار الخصم"""
    note = get_object_or_404(CustomerDiscountNote, pk=pk)
    
    if not note.is_editable:
        messages.error(request, _('لا يمكن تعديل إشعار مرحّل أو ملغى'))
        return redirect('sales:customer_discount_detail', pk=pk)
    
    if request.method == 'POST':
        form = CustomerDiscountNoteForm(request.POST, instance=note)
        if form.is_valid():
            note = form.save(commit=False)
            if note.is_percentage and note.invoice:
                note.amount = (note.invoice.total * note.percentage_value) / Decimal('100')
            note.save()
            messages.success(request, _('تم تحديث إشعار الخصم بنجاح'))
            return redirect('sales:customer_discount_detail', pk=pk)
    else:
        form = CustomerDiscountNoteForm(instance=note)
    
    return render(request, 'sales/discount/customer_discount_form.html', {
        'form': form,
        'note': note,
        'is_new': False,
    })


@login_required
@permission_required('sales.can_post_customer_discount', raise_exception=True)
def customer_discount_post(request, pk):
    """ترحيل إشعار الخصم"""
    note = get_object_or_404(CustomerDiscountNote, pk=pk)
    
    if note.status != 'draft':
        messages.error(request, _('لا يمكن ترحيل إشعار غير مسودة'))
        return redirect('sales:customer_discount_detail', pk=pk)
    
    try:
        je = note.post(user=request.user)
        if je:
            messages.success(request, _('تم ترحيل إشعار الخصم وإنشاء القيد المحاسبي'))
        else:
            messages.warning(request, _('تم الترحيل ولكن لم يتم إنشاء قيد محاسبي'))
    except Exception as e:
        messages.error(request, _('خطأ في الترحيل: {}').format(str(e)))
    
    return redirect('sales:customer_discount_detail', pk=pk)


@login_required
@permission_required('sales.can_cancel_customer_discount', raise_exception=True)
def customer_discount_cancel(request, pk):
    """إلغاء إشعار الخصم"""
    note = get_object_or_404(CustomerDiscountNote, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if note.cancel(user=request.user, reason=reason):
            messages.success(request, _('تم إلغاء إشعار الخصم'))
        else:
            messages.error(request, _('لا يمكن إلغاء هذا الإشعار'))
    
    return redirect('sales:customer_discount_detail', pk=pk)


@login_required
def customer_invoices_ajax(request):
    """جلب فواتير العميل عبر AJAX"""
    customer_id = request.GET.get('customer_id')
    if not customer_id:
        return JsonResponse({'invoices': []})
    
    invoices = Invoice.objects.filter(
        customer_id=customer_id,
        is_deleted=False
    ).order_by('-date')[:50]
    
    data = [{
        'id': inv.id,
        'number': inv.number,
        'date': inv.date.strftime('%Y-%m-%d'),
        'total': float(inv.total),
        'remaining': float(inv.remaining),
    } for inv in invoices]
    
    return JsonResponse({'invoices': data})


@login_required
def customer_balance_ajax(request):
    """جلب ملخص رصيد العميل عبر AJAX"""
    customer_id = request.GET.get('customer_id')
    if not customer_id:
        return JsonResponse({'error': 'No customer'}, status=400)
    
    try:
        customer = Customer.objects.get(pk=customer_id)
        from .models import Invoice, InvoicePayment
        
        invoices_total = Invoice.objects.filter(customer=customer, is_deleted=False).aggregate(
            total=Sum('cached_total')
        )['total'] or Decimal('0')
        discounts_total = Invoice.objects.filter(customer=customer, is_deleted=False).aggregate(
            total=Sum('discount')
        )['total'] or Decimal('0')
        payments_total = InvoicePayment.objects.filter(invoice__customer=customer).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        posted_discounts = CustomerDiscountNote.objects.filter(
            customer=customer, status='posted'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        current_balance = invoices_total - discounts_total - payments_total - posted_discounts
        
        return JsonResponse({
            'current_balance': float(current_balance),
            'total_discounts': float(posted_discounts),
        })
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
