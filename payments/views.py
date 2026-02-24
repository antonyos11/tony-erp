"""
عرض تطبيق المدفوعات والقروض
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from .models import PaymentMethod, Loan, LoanInstallment, PaymentTransaction, PaymentReminder
from .forms import PaymentMethodForm, LoanForm, PaymentForm
from decimal import Decimal


@login_required
def dashboard(request):
    """لوحة تحكم المدفوعات"""
    context = {
        'title': 'لوحة تحكم المدفوعات',
        'active_loans_count': Loan.objects.filter(status='active').count(),
        'overdue_installments_count': LoanInstallment.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'partially_paid']
        ).count(),
        'total_outstanding': LoanInstallment.objects.filter(
            status__in=['pending', 'partially_paid']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0'),
    }
    return render(request, 'payments/dashboard.html', context)


@login_required
def payment_methods_list(request):
    """قائمة طرق الدفع"""
    methods = PaymentMethod.objects.filter(is_active=True)
    
    context = {
        'title': 'طرق الدفع',
        'methods': methods,
    }
    return render(request, 'payments/payment_methods_list.html', context)


@login_required
def payment_method_create(request):
    """إنشاء طريقة دفع جديدة"""
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء طريقة الدفع بنجاح')
            return redirect('payments:payment_methods_list')
    else:
        form = PaymentMethodForm()
    
    context = {
        'title': 'إضافة طريقة دفع',
        'form': form,
    }
    return render(request, 'payments/payment_method_form.html', context)


@login_required
def payment_method_edit(request, pk):
    """تعديل طريقة دفع"""
    method = get_object_or_404(PaymentMethod, pk=pk)
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث طريقة الدفع بنجاح')
            return redirect('payments:payment_methods_list')
    else:
        form = PaymentMethodForm(instance=method)
    
    context = {
        'title': 'تعديل طريقة دفع',
        'form': form,
        'method': method,
    }
    return render(request, 'payments/payment_method_form.html', context)


@login_required
def payment_method_delete(request, pk):
    """حذف طريقة دفع"""
    method = get_object_or_404(PaymentMethod, pk=pk)
    
    if request.method == 'POST':
        method.is_active = False
        method.save()
        messages.success(request, 'تم إلغاء تفعيل طريقة الدفع')
        return redirect('payments:payment_methods_list')
    
    context = {
        'title': 'حذف طريقة دفع',
        'method': method,
    }
    return render(request, 'payments/payment_method_confirm_delete.html', context)


@login_required
def loans_list(request):
    """قائمة القروض"""
    loans = Loan.objects.all().order_by('-created_at')
    
    # فلترة
    status = request.GET.get('status')
    if status:
        loans = loans.filter(status=status)
    
    search = request.GET.get('search')
    if search:
        loans = loans.filter(
            Q(loan_number__icontains=search) |
            Q(borrower__name__icontains=search)
        )
    
    # ترقيم الصفحات
    paginator = Paginator(loans, 20)
    page_number = request.GET.get('page')
    loans_page = paginator.get_page(page_number)
    
    context = {
        'title': 'إدارة القروض',
        'loans': loans_page,
        'status_choices': Loan.LOAN_STATUS,
        'current_status': status,
        'search_query': search,
    }
    return render(request, 'payments/loans_list.html', context)


@login_required
def loan_create(request):
    """إنشاء قرض جديد"""
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.created_by = request.user
            loan.save()
            
            # إنشاء الأقساط
            create_loan_installments(loan)
            
            messages.success(request, 'تم إنشاء القرض بنجاح')
            return redirect('payments:loan_detail', pk=loan.pk)
    else:
        form = LoanForm()
    
    context = {
        'title': 'إضافة قرض جديد',
        'form': form,
    }
    return render(request, 'payments/loan_form.html', context)


@login_required
def loan_detail(request, pk):
    """تفاصيل القرض"""
    loan = get_object_or_404(Loan, pk=pk)
    installments = loan.installments.all().order_by('installment_number')
    
    # إحصائيات
    total_paid = installments.filter(status='paid').aggregate(
        total=Sum('paid_amount'))['total'] or Decimal('0')
    remaining_balance = loan.total_amount - total_paid
    
    context = {
        'title': f'تفاصيل القرض {loan.loan_number}',
        'loan': loan,
        'installments': installments,
        'total_paid': total_paid,
        'remaining_balance': remaining_balance,
    }
    return render(request, 'payments/loan_detail.html', context)


@login_required
def loan_edit(request, pk):
    """تعديل قرض"""
    loan = get_object_or_404(Loan, pk=pk)
    
    if request.method == 'POST':
        form = LoanForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث بيانات القرض')
            return redirect('payments:loan_detail', pk=loan.pk)
    else:
        form = LoanForm(instance=loan)
    
    context = {
        'title': 'تعديل القرض',
        'form': form,
        'loan': loan,
    }
    return render(request, 'payments/loan_form.html', context)


@login_required
def loan_delete(request, pk):
    """حذف قرض"""
    loan = get_object_or_404(Loan, pk=pk)
    
    if request.method == 'POST':
        loan.status = 'cancelled'
        loan.save()
        messages.success(request, 'تم إلغاء القرض')
        return redirect('payments:loans_list')
    
    context = {
        'title': 'إلغاء القرض',
        'loan': loan,
    }
    return render(request, 'payments/loan_confirm_delete.html', context)


@login_required
def installments_list(request):
    """قائمة الأقساط"""
    installments = LoanInstallment.objects.select_related('loan', 'loan__borrower').all()
    
    # فلترة
    status = request.GET.get('status')
    if status:
        installments = installments.filter(status=status)
    elif request.GET.get('overdue'):
        installments = installments.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'partially_paid']
        )
    
    # ترقيم الصفحات
    paginator = Paginator(installments, 25)
    page_number = request.GET.get('page')
    installments_page = paginator.get_page(page_number)
    
    context = {
        'title': 'إدارة الأقساط',
        'installments': installments_page,
        'status_choices': LoanInstallment.INSTALLMENT_STATUS,
    }
    return render(request, 'payments/installments_list.html', context)


@login_required
def installment_pay(request, pk):
    """دفع قسط"""
    installment = get_object_or_404(LoanInstallment, pk=pk)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data['payment_method']
            
            # إنشاء معاملة الدفع
            transaction = PaymentTransaction.objects.create(
                transaction_number=f'PAY{timezone.now().strftime("%Y%m%d%H%M%S")}',
                transaction_type='payment',
                amount=amount,
                payment_method=payment_method,
                installment=installment,
                status='completed',
                processed_by=request.user,
                processed_at=timezone.now()
            )
            
            # تحديث القسط
            installment.paid_amount += amount
            if installment.paid_amount >= installment.amount:
                installment.status = 'paid'
                installment.payment_date = timezone.now().date()
            else:
                installment.status = 'partially_paid'
            installment.save()
            
            messages.success(request, f'تم دفع {amount} بنجاح')
            return redirect('payments:loan_detail', pk=installment.loan.pk)
    else:
        form = PaymentForm(initial={'amount': installment.remaining_amount})
    
    context = {
        'title': f'دفع قسط رقم {installment.installment_number}',
        'installment': installment,
        'form': form,
    }
    return render(request, 'payments/installment_pay.html', context)


@login_required
def installment_detail(request, pk):
    """تفاصيل قسط"""
    installment = get_object_or_404(LoanInstallment, pk=pk)
    
    context = {
        'title': f'تفاصيل القسط رقم {installment.installment_number}',
        'installment': installment,
    }
    return render(request, 'payments/installment_detail.html', context)


@login_required
def transactions_list(request):
    """قائمة المعاملات"""
    transactions = PaymentTransaction.objects.all().order_by('-created_at')
    
    # ترقيم الصفحات
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    transactions_page = paginator.get_page(page_number)
    
    context = {
        'title': 'سجل المعاملات',
        'transactions': transactions_page,
    }
    return render(request, 'payments/transactions_list.html', context)


@login_required
def transaction_detail(request, pk):
    """تفاصيل معاملة"""
    transaction = get_object_or_404(PaymentTransaction, pk=pk)
    
    context = {
        'title': f'تفاصيل المعاملة {transaction.transaction_number}',
        'transaction': transaction,
    }
    return render(request, 'payments/transaction_detail.html', context)


@login_required
def payments_reports(request):
    """تقارير المدفوعات"""
    context = {
        'title': 'تقارير المدفوعات',
    }
    return render(request, 'payments/reports.html', context)


@login_required
def overdue_report(request):
    """تقرير الأقساط المتأخرة"""
    overdue_installments = LoanInstallment.objects.filter(
        due_date__lt=timezone.now().date(),
        status__in=['pending', 'partially_paid']
    ).select_related('loan', 'loan__borrower')
    
    context = {
        'title': 'تقرير الأقساط المتأخرة',
        'overdue_installments': overdue_installments,
    }
    return render(request, 'payments/overdue_report.html', context)


@login_required
def collection_report(request):
    """تقرير المحصلات"""
    # يمكن إضافة منطق التقرير هنا
    context = {
        'title': 'تقرير المحصلات',
    }
    return render(request, 'payments/collection_report.html', context)


def create_loan_installments(loan):
    """إنشاء أقساط القرض"""
    for i in range(1, loan.duration_months + 1):
        due_date = loan.start_date.replace(day=28)  # تجنب مشاكل نهاية الشهر
        due_date = due_date + timezone.timedelta(days=32 * i)
        due_date = due_date.replace(day=loan.start_date.day)
        
        LoanInstallment.objects.create(
            loan=loan,
            installment_number=i,
            due_date=due_date,
            amount=loan.monthly_payment,
            status='pending'
        )