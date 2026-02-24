from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import datetime, timedelta
import json

from .models import (
    TaxSettings, TaxCategory, TaxInvoice, TaxInvoiceLine,
    TaxPeriod, TaxPayment, TaxExemption
)
from .forms import (
    TaxSettingsForm, TaxCategoryForm, TaxInvoiceForm, TaxInvoiceLineForm,
    TaxPeriodForm, TaxPaymentForm, TaxExemptionForm, TaxReportFilterForm
)


# ============ لوحة التحكم ============

@login_required
def dashboard(request):
    """لوحة تحكم الضرائب"""
    
    # إحصائيات سريعة
    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # فواتير الشهر الحالي
    month_invoices = TaxInvoice.objects.filter(invoice_date__gte=month_start)
    
    # ضريبة المخرجات (مبيعات)
    output_tax = month_invoices.filter(
        invoice_type='sales'
    ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
    
    output_returns = month_invoices.filter(
        invoice_type='sales_return'
    ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
    
    net_output_tax = output_tax - output_returns
    
    # ضريبة المدخلات (مشتريات)
    input_tax = month_invoices.filter(
        invoice_type='purchase'
    ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
    
    input_returns = month_invoices.filter(
        invoice_type='purchase_return'
    ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
    
    net_input_tax = input_tax - input_returns
    
    # صافي الضريبة
    net_tax = net_output_tax - net_input_tax
    
    # الفترة الضريبية الحالية
    current_period = TaxPeriod.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).first()
    
    # آخر الفواتير
    recent_invoices = TaxInvoice.objects.order_by('-created_at')[:10]
    
    # فواتير بحاجة لإرسال
    pending_invoices = TaxInvoice.objects.filter(
        status__in=['draft', 'pending']
    ).count()
    
    # فواتير مرفوضة
    rejected_invoices = TaxInvoice.objects.filter(status='rejected').count()
    
    context = {
        'output_tax': net_output_tax,
        'input_tax': net_input_tax,
        'net_tax': net_tax,
        'net_tax_status': 'payable' if net_tax > 0 else 'receivable',
        'current_period': current_period,
        'recent_invoices': recent_invoices,
        'pending_invoices': pending_invoices,
        'rejected_invoices': rejected_invoices,
        'month_name': today.strftime('%B %Y'),
    }
    
    return render(request, 'taxes/dashboard.html', context)


# ============ إعدادات الضرائب ============

@login_required
def settings_view(request):
    """إعدادات الضرائب"""
    settings = TaxSettings.get_settings()
    
    if request.method == 'POST':
        form = TaxSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم حفظ الإعدادات بنجاح'))
            return redirect('taxes:settings')
    else:
        form = TaxSettingsForm(instance=settings)
    
    return render(request, 'taxes/settings.html', {'form': form, 'settings': settings})


# ============ الفئات الضريبية ============

@login_required
def category_list(request):
    """قائمة الفئات الضريبية"""
    categories = TaxCategory.objects.all()
    return render(request, 'taxes/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    """إنشاء فئة ضريبية"""
    if request.method == 'POST':
        form = TaxCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إنشاء الفئة بنجاح'))
            return redirect('taxes:category_list')
    else:
        form = TaxCategoryForm()
    
    return render(request, 'taxes/category_form.html', {'form': form, 'title': _('إنشاء فئة ضريبية')})


@login_required
def category_edit(request, pk):
    """تعديل فئة ضريبية"""
    category = get_object_or_404(TaxCategory, pk=pk)
    
    if request.method == 'POST':
        form = TaxCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الفئة بنجاح'))
            return redirect('taxes:category_list')
    else:
        form = TaxCategoryForm(instance=category)
    
    return render(request, 'taxes/category_form.html', {'form': form, 'category': category, 'title': _('تعديل فئة ضريبية')})


@login_required
def category_delete(request, pk):
    """حذف فئة ضريبية"""
    category = get_object_or_404(TaxCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, _('تم حذف الفئة بنجاح'))
        return redirect('taxes:category_list')
    return render(request, 'taxes/category_confirm_delete.html', {'category': category})


# ============ الفواتير الضريبية ============

@login_required
def invoice_list(request):
    """قائمة الفواتير الضريبية"""
    invoices = TaxInvoice.objects.all()
    
    # الفلترة
    invoice_type = request.GET.get('type')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search = request.GET.get('q')
    
    if invoice_type:
        invoices = invoices.filter(invoice_type=invoice_type)
    if status:
        invoices = invoices.filter(status=status)
    if start_date:
        invoices = invoices.filter(invoice_date__gte=start_date)
    if end_date:
        invoices = invoices.filter(invoice_date__lte=end_date)
    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(partner_name__icontains=search) |
            Q(partner_tax_id__icontains=search)
        )
    
    paginator = Paginator(invoices, 25)
    page = request.GET.get('page')
    invoices = paginator.get_page(page)
    
    context = {
        'invoices': invoices,
        'invoice_types': TaxInvoice.INVOICE_TYPE_CHOICES,
        'statuses': TaxInvoice.STATUS_CHOICES,
    }
    
    return render(request, 'taxes/invoice_list.html', context)


@login_required
def invoice_create(request):
    """إنشاء فاتورة ضريبية"""
    if request.method == 'POST':
        form = TaxInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.save()
            messages.success(request, _('تم إنشاء الفاتورة بنجاح'))
            return redirect('taxes:invoice_detail', pk=invoice.pk)
    else:
        settings = TaxSettings.get_settings()
        form = TaxInvoiceForm(initial={
            'invoice_date': timezone.now().date(),
            'tax_rate': settings.default_vat_rate,
        })
    
    return render(request, 'taxes/invoice_form.html', {'form': form, 'title': _('إنشاء فاتورة ضريبية')})


@login_required
def invoice_detail(request, pk):
    """تفاصيل الفاتورة الضريبية"""
    invoice = get_object_or_404(TaxInvoice, pk=pk)
    lines = invoice.lines.all()
    
    return render(request, 'taxes/invoice_detail.html', {
        'invoice': invoice,
        'lines': lines,
    })


@login_required
def invoice_edit(request, pk):
    """تعديل فاتورة ضريبية"""
    invoice = get_object_or_404(TaxInvoice, pk=pk)
    
    if invoice.status not in ['draft', 'pending', 'rejected']:
        messages.error(request, _('لا يمكن تعديل فاتورة مرسلة أو مقبولة'))
        return redirect('taxes:invoice_detail', pk=pk)
    
    if request.method == 'POST':
        form = TaxInvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الفاتورة بنجاح'))
            return redirect('taxes:invoice_detail', pk=pk)
    else:
        form = TaxInvoiceForm(instance=invoice)
    
    return render(request, 'taxes/invoice_form.html', {
        'form': form,
        'invoice': invoice,
        'title': _('تعديل فاتورة ضريبية')
    })


@login_required
def invoice_delete(request, pk):
    """حذف فاتورة ضريبية"""
    invoice = get_object_or_404(TaxInvoice, pk=pk)
    
    if invoice.status not in ['draft']:
        messages.error(request, _('لا يمكن حذف فاتورة تم إرسالها'))
        return redirect('taxes:invoice_detail', pk=pk)
    
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, _('تم حذف الفاتورة بنجاح'))
        return redirect('taxes:invoice_list')
    
    return render(request, 'taxes/invoice_confirm_delete.html', {'invoice': invoice})


@login_required
def invoice_submit(request, pk):
    """إرسال الفاتورة للضرائب"""
    invoice = get_object_or_404(TaxInvoice, pk=pk)
    
    if invoice.status not in ['draft', 'pending', 'rejected']:
        messages.error(request, _('لا يمكن إرسال هذه الفاتورة'))
        return redirect('taxes:invoice_detail', pk=pk)
    
    # محاكاة الإرسال (سيتم ربطها لاحقاً بـ API الفاتورة الإلكترونية)
    invoice.status = 'submitted'
    invoice.submitted_at = timezone.now()
    invoice.save()
    
    messages.success(request, _('تم إرسال الفاتورة بنجاح'))
    return redirect('taxes:invoice_detail', pk=pk)


# ============ الفترات الضريبية ============

@login_required
def period_list(request):
    """قائمة الفترات الضريبية"""
    periods = TaxPeriod.objects.all()
    return render(request, 'taxes/period_list.html', {'periods': periods})


@login_required
def period_create(request):
    """إنشاء فترة ضريبية"""
    if request.method == 'POST':
        form = TaxPeriodForm(request.POST)
        if form.is_valid():
            period = form.save()
            period.calculate_taxes()
            messages.success(request, _('تم إنشاء الفترة بنجاح'))
            return redirect('taxes:period_detail', pk=period.pk)
    else:
        # اقتراح فترة جديدة
        today = timezone.now().date()
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        due_date = month_end + timedelta(days=30)
        
        form = TaxPeriodForm(initial={
            'name': f"فترة {today.strftime('%B %Y')}",
            'start_date': month_start,
            'end_date': month_end,
            'due_date': due_date,
        })
    
    return render(request, 'taxes/period_form.html', {'form': form, 'title': _('إنشاء فترة ضريبية')})


@login_required
def period_detail(request, pk):
    """تفاصيل الفترة الضريبية"""
    period = get_object_or_404(TaxPeriod, pk=pk)
    
    # فواتير الفترة
    invoices = TaxInvoice.objects.filter(
        invoice_date__gte=period.start_date,
        invoice_date__lte=period.end_date
    )
    
    # تفاصيل
    sales_invoices = invoices.filter(invoice_type='sales')
    sales_returns = invoices.filter(invoice_type='sales_return')
    purchase_invoices = invoices.filter(invoice_type='purchase')
    purchase_returns = invoices.filter(invoice_type='purchase_return')
    
    # المدفوعات
    payments = period.payments.all()
    total_paid = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    context = {
        'period': period,
        'sales_invoices': sales_invoices,
        'sales_returns': sales_returns,
        'purchase_invoices': purchase_invoices,
        'purchase_returns': purchase_returns,
        'payments': payments,
        'total_paid': total_paid,
        'remaining': period.net_tax - total_paid if period.net_tax > 0 else Decimal('0'),
    }
    
    return render(request, 'taxes/period_detail.html', context)


@login_required
def period_calculate(request, pk):
    """إعادة حساب الفترة الضريبية"""
    period = get_object_or_404(TaxPeriod, pk=pk)
    period.calculate_taxes()
    messages.success(request, _('تم إعادة حساب الفترة'))
    return redirect('taxes:period_detail', pk=pk)


@login_required
def period_close(request, pk):
    """إغلاق الفترة الضريبية"""
    period = get_object_or_404(TaxPeriod, pk=pk)
    
    if request.method == 'POST':
        period.status = 'closed'
        period.save()
        messages.success(request, _('تم إغلاق الفترة'))
        return redirect('taxes:period_detail', pk=pk)
    
    return render(request, 'taxes/period_close_confirm.html', {'period': period})


@login_required
def period_file(request, pk):
    """تقديم إقرار الفترة"""
    period = get_object_or_404(TaxPeriod, pk=pk)
    
    if request.method == 'POST':
        reference = request.POST.get('reference_number', '')
        period.status = 'filed'
        period.filed_at = timezone.now()
        period.filed_by = request.user
        period.reference_number = reference
        period.save()
        messages.success(request, _('تم تسجيل تقديم الإقرار'))
        return redirect('taxes:period_detail', pk=pk)
    
    return render(request, 'taxes/period_file_form.html', {'period': period})


# ============ سداد الضرائب ============

@login_required
def payment_list(request):
    """قائمة المدفوعات"""
    payments = TaxPayment.objects.all()
    return render(request, 'taxes/payment_list.html', {'payments': payments})


@login_required
def payment_create(request):
    """تسجيل سداد ضريبة"""
    if request.method == 'POST':
        form = TaxPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            messages.success(request, _('تم تسجيل السداد بنجاح'))
            return redirect('taxes:payment_list')
    else:
        form = TaxPaymentForm(initial={'payment_date': timezone.now().date()})
    
    return render(request, 'taxes/payment_form.html', {'form': form, 'title': _('تسجيل سداد ضريبة')})


# ============ التقارير ============

@login_required
def report_summary(request):
    """تقرير ملخص الضرائب"""
    form = TaxReportFilterForm(request.GET or None)
    
    today = timezone.now().date()
    start_date = request.GET.get('start_date') or today.replace(day=1)
    end_date = request.GET.get('end_date') or today
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    invoices = TaxInvoice.objects.filter(
        invoice_date__gte=start_date,
        invoice_date__lte=end_date
    )
    
    # إحصائيات
    sales = invoices.filter(invoice_type='sales').aggregate(
        count=Count('id'),
        subtotal=Sum('subtotal'),
        tax=Sum('tax_amount'),
        total=Sum('total')
    )
    
    sales_returns = invoices.filter(invoice_type='sales_return').aggregate(
        count=Count('id'),
        subtotal=Sum('subtotal'),
        tax=Sum('tax_amount'),
        total=Sum('total')
    )
    
    purchases = invoices.filter(invoice_type='purchase').aggregate(
        count=Count('id'),
        subtotal=Sum('subtotal'),
        tax=Sum('tax_amount'),
        total=Sum('total')
    )
    
    purchase_returns = invoices.filter(invoice_type='purchase_return').aggregate(
        count=Count('id'),
        subtotal=Sum('subtotal'),
        tax=Sum('tax_amount'),
        total=Sum('total')
    )
    
    # صافي الضريبة
    output_tax = (sales['tax'] or 0) - (sales_returns['tax'] or 0)
    input_tax = (purchases['tax'] or 0) - (purchase_returns['tax'] or 0)
    net_tax = output_tax - input_tax
    
    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'sales': sales,
        'sales_returns': sales_returns,
        'purchases': purchases,
        'purchase_returns': purchase_returns,
        'output_tax': output_tax,
        'input_tax': input_tax,
        'net_tax': net_tax,
    }
    
    return render(request, 'taxes/report_summary.html', context)


@login_required
def report_vat_return(request):
    """تقرير إقرار ضريبة القيمة المضافة"""
    periods = TaxPeriod.objects.all()
    period_id = request.GET.get('period')
    
    period = None
    if period_id:
        period = get_object_or_404(TaxPeriod, pk=period_id)
    
    return render(request, 'taxes/report_vat_return.html', {
        'periods': periods,
        'period': period,
    })


# ============ API ============

@login_required
def api_calculate_tax(request):
    """API لحساب الضريبة"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            subtotal = Decimal(str(data.get('subtotal', 0)))
            discount = Decimal(str(data.get('discount', 0)))
            tax_rate = Decimal(str(data.get('tax_rate', 14)))
            
            net = subtotal - discount
            tax = (net * tax_rate) / 100
            total = net + tax
            
            return JsonResponse({
                'success': True,
                'net': float(net),
                'tax': float(tax),
                'total': float(total),
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_invoice_stats(request):
    """API إحصائيات الفواتير"""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    invoices = TaxInvoice.objects.filter(invoice_date__gte=month_start)
    
    stats = {
        'sales_count': invoices.filter(invoice_type='sales').count(),
        'sales_tax': float(invoices.filter(invoice_type='sales').aggregate(
            total=Sum('tax_amount')
        )['total'] or 0),
        'purchase_count': invoices.filter(invoice_type='purchase').count(),
        'purchase_tax': float(invoices.filter(invoice_type='purchase').aggregate(
            total=Sum('tax_amount')
        )['total'] or 0),
        'pending_count': invoices.filter(status__in=['draft', 'pending']).count(),
    }
    
    return JsonResponse(stats)
