"""
Views لإشعارات الخصم من الموردين - Supplier Discount Notes Views
================================================================
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

from .models_discount import SupplierDiscountNote
from .models import PurchaseBill
from .forms_discount import SupplierDiscountNoteForm, SupplierDiscountNoteSearchForm
from partners.models import Supplier


@login_required
def supplier_discount_list(request):
    """قائمة إشعارات الخصم المكتسبة"""
    queryset = SupplierDiscountNote.objects.select_related('supplier', 'bill').all()
    
    # فلترة
    search_form = SupplierDiscountNoteSearchForm(request.GET or None)
    if search_form.is_valid():
        supplier = search_form.cleaned_data.get('supplier')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        if supplier:
            queryset = queryset.filter(supplier=supplier)
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
    
    return render(request, 'purchases/discount/supplier_discount_list.html', {
        'notes': notes,
        'search_form': search_form,
        'stats': stats,
    })


@login_required
def supplier_discount_create(request):
    """إنشاء إشعار خصم مكتسب جديد"""
    if request.method == 'POST':
        form = SupplierDiscountNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.created_by = request.user
            
            # إذا كانت نسبة مئوية، احسب المبلغ
            if note.is_percentage and note.bill:
                note.amount = (note.bill.total * note.percentage_value) / Decimal('100')
            
            note.save()
            messages.success(request, _('تم إنشاء إشعار الخصم بنجاح: {}').format(note.number))
            return redirect('purchases:supplier_discount_detail', pk=note.pk)
    else:
        initial = {'date': timezone.now().date()}
        supplier_id = request.GET.get('supplier')
        bill_id = request.GET.get('bill')
        
        if supplier_id:
            initial['supplier'] = supplier_id
        if bill_id:
            initial['bill'] = bill_id
        
        form = SupplierDiscountNoteForm(initial=initial)
    
    # احتساب ملخص الأثر المالي
    supplier_id = request.GET.get('supplier') or request.POST.get('supplier')
    financial_summary = None
    if supplier_id:
        try:
            supplier = Supplier.objects.get(pk=supplier_id)
            from .models import PurchaseBill, SupplierPayment
            
            bills_total = PurchaseBill.objects.filter(supplier=supplier, is_deleted=False).aggregate(
                total=Sum('paid')
            )
            # حساب إجمالي الفواتير
            all_bills = PurchaseBill.objects.filter(supplier=supplier, is_deleted=False)
            total_bills = Decimal('0')
            for bill in all_bills:
                total_bills += bill.total
            
            # المدفوعات
            paid_total = PurchaseBill.objects.filter(supplier=supplier, is_deleted=False).aggregate(
                total=Sum('paid')
            )['total'] or Decimal('0')
            
            # الخصومات المكتسبة المرحّلة
            posted_discounts = SupplierDiscountNote.objects.filter(
                supplier=supplier, status='posted'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            financial_summary = {
                'current_balance': total_bills - paid_total - posted_discounts,
                'total_discounts': posted_discounts,
                'expected_balance': total_bills - paid_total - posted_discounts,
            }
        except Supplier.DoesNotExist:
            pass
    
    return render(request, 'purchases/discount/supplier_discount_form.html', {
        'form': form,
        'is_new': True,
        'financial_summary': financial_summary,
    })


@login_required
def supplier_discount_detail(request, pk):
    """تفاصيل إشعار الخصم"""
    note = get_object_or_404(SupplierDiscountNote.objects.select_related(
        'supplier', 'bill', 'created_by', 'posted_by', 'journal_entry'
    ), pk=pk)
    
    return render(request, 'purchases/discount/supplier_discount_detail.html', {
        'note': note,
    })


@login_required
def supplier_discount_edit(request, pk):
    """تعديل إشعار الخصم"""
    note = get_object_or_404(SupplierDiscountNote, pk=pk)
    
    if not note.is_editable:
        messages.error(request, _('لا يمكن تعديل إشعار مرحّل أو ملغى'))
        return redirect('purchases:supplier_discount_detail', pk=pk)
    
    if request.method == 'POST':
        form = SupplierDiscountNoteForm(request.POST, instance=note)
        if form.is_valid():
            note = form.save(commit=False)
            if note.is_percentage and note.bill:
                note.amount = (note.bill.total * note.percentage_value) / Decimal('100')
            note.save()
            messages.success(request, _('تم تحديث إشعار الخصم بنجاح'))
            return redirect('purchases:supplier_discount_detail', pk=pk)
    else:
        form = SupplierDiscountNoteForm(instance=note)
    
    return render(request, 'purchases/discount/supplier_discount_form.html', {
        'form': form,
        'note': note,
        'is_new': False,
    })


@login_required
@permission_required('purchases.can_post_supplier_discount', raise_exception=True)
def supplier_discount_post(request, pk):
    """ترحيل إشعار الخصم"""
    note = get_object_or_404(SupplierDiscountNote, pk=pk)
    
    if note.status != 'draft':
        messages.error(request, _('لا يمكن ترحيل إشعار غير مسودة'))
        return redirect('purchases:supplier_discount_detail', pk=pk)
    
    try:
        je = note.post(user=request.user)
        if je:
            messages.success(request, _('تم ترحيل إشعار الخصم وإنشاء القيد المحاسبي'))
        else:
            messages.warning(request, _('تم الترحيل ولكن لم يتم إنشاء قيد محاسبي'))
    except Exception as e:
        messages.error(request, _('خطأ في الترحيل: {}').format(str(e)))
    
    return redirect('purchases:supplier_discount_detail', pk=pk)


@login_required
@permission_required('purchases.can_cancel_supplier_discount', raise_exception=True)
def supplier_discount_cancel(request, pk):
    """إلغاء إشعار الخصم"""
    note = get_object_or_404(SupplierDiscountNote, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if note.cancel(user=request.user, reason=reason):
            messages.success(request, _('تم إلغاء إشعار الخصم'))
        else:
            messages.error(request, _('لا يمكن إلغاء هذا الإشعار'))
    
    return redirect('purchases:supplier_discount_detail', pk=pk)


@login_required
def supplier_bills_ajax(request):
    """جلب فواتير المورد عبر AJAX"""
    supplier_id = request.GET.get('supplier_id')
    if not supplier_id:
        return JsonResponse({'bills': []})
    
    bills = PurchaseBill.objects.filter(
        supplier_id=supplier_id,
        is_deleted=False
    ).order_by('-date')[:50]
    
    data = [{
        'id': bill.id,
        'number': bill.number,
        'date': bill.date.strftime('%Y-%m-%d'),
        'total': float(bill.total),
        'remaining': float(bill.remaining),
    } for bill in bills]
    
    return JsonResponse({'bills': data})


@login_required
def supplier_balance_ajax(request):
    """جلب ملخص رصيد المورد عبر AJAX"""
    supplier_id = request.GET.get('supplier_id')
    if not supplier_id:
        return JsonResponse({'error': 'No supplier'}, status=400)
    
    try:
        supplier = Supplier.objects.get(pk=supplier_id)
        
        all_bills = PurchaseBill.objects.filter(supplier=supplier, is_deleted=False)
        total_bills = Decimal('0')
        for bill in all_bills:
            total_bills += bill.total
        
        paid_total = PurchaseBill.objects.filter(supplier=supplier, is_deleted=False).aggregate(
            total=Sum('paid')
        )['total'] or Decimal('0')
        
        posted_discounts = SupplierDiscountNote.objects.filter(
            supplier=supplier, status='posted'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        current_balance = total_bills - paid_total - posted_discounts
        
        return JsonResponse({
            'current_balance': float(current_balance),
            'total_discounts': float(posted_discounts),
        })
    except Supplier.DoesNotExist:
        return JsonResponse({'error': 'Supplier not found'}, status=404)
