"""
Views لنظام التقسيط الذكي
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F, Avg
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import json

from .models import (
    InstallmentPlan, InstallmentContract, Installment,
    InstallmentPayment, Guarantor, InstallmentSettings,
    EarlySettlement, ContractReschedule, ContractTransfer,
    CustomerCreditScore, CollectionAction, InstallmentWaiver
)
from .forms import (
    InstallmentPlanForm, InstallmentContractForm, GuarantorForm,
    InstallmentPaymentForm, ContractCalculatorForm
)


# ============ لوحة التحكم ============

@login_required
def dashboard(request):
    """لوحة تحكم التقسيط"""
    today = date.today()
    
    # إحصائيات عامة
    stats = {
        'total_contracts': InstallmentContract.objects.filter(status__in=['active', 'completed']).count(),
        'active_contracts': InstallmentContract.objects.filter(status='active').count(),
        'defaulted_contracts': InstallmentContract.objects.filter(status='defaulted').count(),
        'total_financed': InstallmentContract.objects.filter(
            status__in=['active', 'completed']
        ).aggregate(total=Sum('financed_amount'))['total'] or 0,
    }
    
    # الأقساط المستحقة اليوم
    due_today = Installment.objects.filter(
        due_date=today,
        status__in=['pending', 'partially_paid']
    ).select_related('contract', 'contract__customer')[:10]
    
    # الأقساط المتأخرة
    overdue = Installment.objects.filter(
        status='overdue'
    ).select_related('contract', 'contract__customer').order_by('due_date')[:10]
    
    # إجمالي المتأخرات
    overdue_stats = Installment.objects.filter(status='overdue').aggregate(
        total_amount=Sum('amount'),
        total_late_fees=Sum('late_fee'),
        count=Count('id')
    )
    
    # الأقساط القادمة (7 أيام)
    upcoming = Installment.objects.filter(
        due_date__gt=today,
        due_date__lte=today + timedelta(days=7),
        status='pending'
    ).select_related('contract', 'contract__customer').order_by('due_date')[:10]
    
    # آخر المدفوعات
    recent_payments = InstallmentPayment.objects.select_related(
        'installment__contract__customer'
    ).order_by('-payment_date')[:10]
    
    context = {
        'stats': stats,
        'due_today': due_today,
        'overdue': overdue,
        'overdue_stats': overdue_stats,
        'upcoming': upcoming,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'installments/dashboard.html', context)


# ============ خطط التقسيط ============

@login_required
def plan_list(request):
    """قائمة خطط التقسيط"""
    plans = InstallmentPlan.objects.all().order_by('duration_months')
    return render(request, 'installments/plan_list.html', {'plans': plans})


@login_required
@permission_required('installments.add_installmentplan')
def plan_create(request):
    """إنشاء خطة تقسيط جديدة"""
    if request.method == 'POST':
        form = InstallmentPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.created_by = request.user
            plan.save()
            messages.success(request, 'تم إنشاء خطة التقسيط بنجاح')
            return redirect('installments:plan_list')
    else:
        form = InstallmentPlanForm()
    
    return render(request, 'installments/plan_form.html', {'form': form})


@login_required
@permission_required('installments.change_installmentplan')
def plan_edit(request, pk):
    """تعديل خطة تقسيط"""
    plan = get_object_or_404(InstallmentPlan, pk=pk)
    
    if request.method == 'POST':
        form = InstallmentPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث خطة التقسيط بنجاح')
            return redirect('installments:plan_list')
    else:
        form = InstallmentPlanForm(instance=plan)
    
    return render(request, 'installments/plan_form.html', {'form': form, 'plan': plan})


# ============ عقود التقسيط ============

@login_required
def contract_list(request):
    """قائمة عقود التقسيط"""
    contracts = InstallmentContract.objects.select_related(
        'customer', 'plan', 'showroom'
    ).order_by('-created_at')
    
    # فلترة
    status = request.GET.get('status')
    if status:
        contracts = contracts.filter(status=status)
    
    search = request.GET.get('q')
    if search:
        contracts = contracts.filter(
            Q(contract_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(phone__icontains=search) |
            Q(national_id__icontains=search)
        )
    
    # التصفح
    paginator = Paginator(contracts, 20)
    page = request.GET.get('page')
    contracts = paginator.get_page(page)
    
    context = {
        'contracts': contracts,
        'status_choices': InstallmentContract.CONTRACT_STATUS,
    }
    
    return render(request, 'installments/contract_list.html', context)


@login_required
def contract_detail(request, pk):
    """تفاصيل عقد التقسيط"""
    contract = get_object_or_404(
        InstallmentContract.objects.select_related('customer', 'plan', 'showroom', 'invoice'),
        pk=pk
    )
    
    installments = contract.installments.all().order_by('installment_number')
    guarantors = contract.guarantors.all()
    payments = InstallmentPayment.objects.filter(
        installment__contract=contract
    ).order_by('-payment_date')
    
    context = {
        'contract': contract,
        'installments': installments,
        'guarantors': guarantors,
        'payments': payments,
    }
    
    return render(request, 'installments/contract_detail.html', context)


@login_required
@permission_required('installments.add_installmentcontract')
def contract_create(request):
    """إنشاء عقد تقسيط جديد"""
    if request.method == 'POST':
        form = InstallmentContractForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                contract = form.save(commit=False)
                contract.created_by = request.user
                
                # حساب التفاصيل من الخطة
                details = contract.plan.calculate_monthly_payment(
                    contract.principal_amount,
                    contract.down_payment
                )
                
                contract.financed_amount = details['financed_amount']
                contract.admin_fee = details['admin_fee']
                contract.total_interest = details['total_interest']
                contract.monthly_payment = details['monthly_payment']
                contract.total_amount = details['total_amount']
                
                contract.save()
                
                messages.success(request, f'تم إنشاء العقد رقم {contract.contract_number} بنجاح')
                return redirect('installments:contract_detail', pk=contract.pk)
    else:
        form = InstallmentContractForm()
    
    plans = InstallmentPlan.objects.filter(is_active=True)
    
    return render(request, 'installments/contract_form.html', {
        'form': form,
        'plans': plans,
    })


@login_required
@permission_required('installments.change_installmentcontract')
def contract_approve(request, pk):
    """اعتماد عقد التقسيط"""
    contract = get_object_or_404(InstallmentContract, pk=pk)
    
    if contract.status not in ['draft', 'pending_approval']:
        messages.error(request, 'لا يمكن اعتماد هذا العقد')
        return redirect('installments:contract_detail', pk=pk)
    
    # التحقق من الضامنين إذا كانت الخطة تتطلب ذلك
    if contract.plan.requires_guarantor:
        if contract.guarantors.count() < contract.plan.min_guarantors:
            messages.error(
                request,
                f'يجب إضافة {contract.plan.min_guarantors} ضامن على الأقل'
            )
            return redirect('installments:contract_detail', pk=pk)
    
    with transaction.atomic():
        contract.status = 'approved'
        contract.approved_by = request.user
        contract.approved_at = timezone.now()
        contract.save()
        
        # توليد جدول الأقساط
        contract.generate_installments()
        
        contract.status = 'active'
        contract.save()
    
    messages.success(request, 'تم اعتماد العقد وتوليد جدول الأقساط بنجاح')
    return redirect('installments:contract_detail', pk=pk)


# ============ الأقساط ============

@login_required
def installment_list(request):
    """قائمة الأقساط"""
    installments = Installment.objects.select_related(
        'contract', 'contract__customer'
    ).order_by('due_date')
    
    # فلترة
    status = request.GET.get('status')
    if status:
        installments = installments.filter(status=status)
    
    due_from = request.GET.get('due_from')
    due_to = request.GET.get('due_to')
    if due_from:
        installments = installments.filter(due_date__gte=due_from)
    if due_to:
        installments = installments.filter(due_date__lte=due_to)
    
    # التصفح
    paginator = Paginator(installments, 50)
    page = request.GET.get('page')
    installments = paginator.get_page(page)
    
    return render(request, 'installments/installment_list.html', {
        'installments': installments,
        'status_choices': Installment.INSTALLMENT_STATUS,
    })


@login_required
def overdue_installments(request):
    """الأقساط المتأخرة"""
    installments = Installment.objects.filter(
        status='overdue'
    ).select_related(
        'contract', 'contract__customer'
    ).order_by('due_date')
    
    # حساب الإجماليات
    totals = installments.aggregate(
        total_amount=Sum('amount'),
        total_paid=Sum('paid_amount'),
        total_late_fees=Sum('late_fee'),
        count=Count('id')
    )
    
    # تجميع حسب العقد
    by_contract = installments.values(
        'contract__contract_number',
        'contract__customer__name'
    ).annotate(
        count=Count('id'),
        total=Sum('amount'),
        late_fees=Sum('late_fee')
    )
    
    context = {
        'installments': installments,
        'totals': totals,
        'by_contract': by_contract,
    }
    
    return render(request, 'installments/overdue_list.html', context)


# ============ تسجيل الدفعات ============

@login_required
@permission_required('installments.add_installmentpayment')
def pay_installment(request, pk):
    """تسجيل دفعة على قسط"""
    installment = get_object_or_404(
        Installment.objects.select_related('contract', 'contract__customer'),
        pk=pk
    )
    
    if installment.status == 'paid':
        messages.warning(request, 'هذا القسط مدفوع بالفعل')
        return redirect('installments:contract_detail', pk=installment.contract.pk)
    
    if request.method == 'POST':
        form = InstallmentPaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data.get('payment_method')
            payment_reference = form.cleaned_data.get('payment_reference', '')
            notes = form.cleaned_data.get('notes', '')
            
            with transaction.atomic():
                # إنشاء الدفعة
                payment = InstallmentPayment.objects.create(
                    installment=installment,
                    amount=amount,
                    payment_method=payment_method,
                    payment_reference=payment_reference,
                    notes=notes,
                    received_by=request.user
                )
                
                # تحديث القسط
                installment.paid_amount += amount
                installment.payment_date = timezone.now().date()
                installment.payment_method = payment_method
                installment.payment_reference = payment_reference
                
                if installment.paid_amount >= installment.amount + installment.late_fee:
                    installment.status = 'paid'
                elif installment.paid_amount > 0:
                    installment.status = 'partially_paid'
                
                installment.save()
                
                # تحديث حالة العقد
                contract = installment.contract
                if not contract.installments.exclude(status='paid').exists():
                    contract.status = 'completed'
                    contract.save()
            
            messages.success(request, f'تم تسجيل الدفعة بنجاح - إيصال رقم: {payment.receipt_number}')
            return redirect('installments:contract_detail', pk=installment.contract.pk)
    else:
        form = InstallmentPaymentForm(initial={
            'amount': installment.remaining_amount
        })
    
    context = {
        'form': form,
        'installment': installment,
    }
    
    return render(request, 'installments/pay_installment.html', context)


# ============ الضامنين ============

@login_required
@permission_required('installments.add_guarantor')
def add_guarantor(request, contract_pk):
    """إضافة ضامن للعقد"""
    contract = get_object_or_404(InstallmentContract, pk=contract_pk)
    
    if request.method == 'POST':
        form = GuarantorForm(request.POST, request.FILES)
        if form.is_valid():
            guarantor = form.save(commit=False)
            guarantor.contract = contract
            guarantor.save()
            messages.success(request, 'تم إضافة الضامن بنجاح')
            return redirect('installments:contract_detail', pk=contract_pk)
    else:
        form = GuarantorForm()
    
    return render(request, 'installments/guarantor_form.html', {
        'form': form,
        'contract': contract,
    })


# ============ الحاسبة ============

@login_required
def calculator(request):
    """حاسبة التقسيط"""
    plans = InstallmentPlan.objects.filter(is_active=True)
    result = None
    
    if request.method == 'POST':
        form = ContractCalculatorForm(request.POST)
        if form.is_valid():
            plan = form.cleaned_data['plan']
            amount = form.cleaned_data['amount']
            down_payment = form.cleaned_data.get('down_payment', Decimal('0'))
            
            result = plan.calculate_monthly_payment(amount, down_payment)
            result['plan'] = plan
    else:
        form = ContractCalculatorForm()
    
    return render(request, 'installments/calculator.html', {
        'form': form,
        'plans': plans,
        'result': result,
    })


# ============ API Endpoints ============

@login_required
@require_http_methods(['GET'])
def api_calculate(request):
    """API لحساب التقسيط"""
    try:
        plan_id = request.GET.get('plan_id')
        amount = Decimal(request.GET.get('amount', '0'))
        down_payment = Decimal(request.GET.get('down_payment', '0'))
        
        plan = InstallmentPlan.objects.get(pk=plan_id, is_active=True)
        result = plan.calculate_monthly_payment(amount, down_payment)
        
        return JsonResponse({
            'success': True,
            'data': {
                'principal_amount': str(result['principal_amount']),
                'down_payment': str(result['down_payment']),
                'financed_amount': str(result['financed_amount']),
                'admin_fee': str(result['admin_fee']),
                'total_interest': str(result['total_interest']),
                'monthly_payment': str(result['monthly_payment']),
                'total_amount': str(result['total_amount']),
                'duration_months': result['duration_months'],
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['GET'])
def api_contract_stats(request, pk):
    """API لإحصائيات العقد"""
    contract = get_object_or_404(InstallmentContract, pk=pk)
    
    installments = contract.installments.all()
    
    return JsonResponse({
        'contract_number': contract.contract_number,
        'status': contract.status,
        'principal_amount': str(contract.principal_amount),
        'total_amount': str(contract.total_amount),
        'paid_amount': str(contract.paid_amount),
        'remaining_amount': str(contract.remaining_amount),
        'overdue_amount': str(contract.overdue_amount),
        'progress_percentage': contract.progress_percentage,
        'total_installments': installments.count(),
        'paid_installments': installments.filter(status='paid').count(),
        'overdue_installments': contract.overdue_count,
    })


# ============ التقارير ============

@login_required
def report_overview(request):
    """تقرير نظرة عامة"""
    from datetime import datetime
    
    # الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = date.today().replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = date.today()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # العقود في الفترة
    contracts = InstallmentContract.objects.filter(
        contract_date__gte=start_date,
        contract_date__lte=end_date
    )
    
    contract_stats = contracts.aggregate(
        count=Count('id'),
        total_financed=Sum('financed_amount'),
        total_interest=Sum('total_interest'),
        total_admin_fees=Sum('admin_fee')
    )
    
    # المدفوعات في الفترة
    payments = InstallmentPayment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    )
    
    payment_stats = payments.aggregate(
        count=Count('id'),
        total=Sum('amount')
    )
    
    # توزيع حسب الحالة
    status_distribution = InstallmentContract.objects.values('status').annotate(
        count=Count('id'),
        total=Sum('financed_amount')
    )
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'contract_stats': contract_stats,
        'payment_stats': payment_stats,
        'status_distribution': status_distribution,
    }
    
    return render(request, 'installments/reports/overview.html', context)


@login_required
def report_aging(request):
    """تقرير أعمار الديون"""
    today = date.today()
    
    # تصنيف الأقساط حسب العمر
    aging_buckets = {
        '0-30': {'min': 0, 'max': 30, 'installments': [], 'total': Decimal('0')},
        '31-60': {'min': 31, 'max': 60, 'installments': [], 'total': Decimal('0')},
        '61-90': {'min': 61, 'max': 90, 'installments': [], 'total': Decimal('0')},
        '90+': {'min': 91, 'max': 9999, 'installments': [], 'total': Decimal('0')},
    }
    
    overdue_installments = Installment.objects.filter(
        status='overdue'
    ).select_related('contract', 'contract__customer')
    
    for installment in overdue_installments:
        days = (today - installment.due_date).days
        amount = installment.remaining_amount
        
        for bucket_name, bucket in aging_buckets.items():
            if bucket['min'] <= days <= bucket['max']:
                bucket['installments'].append(installment)
                bucket['total'] += amount
                break
    
    return render(request, 'installments/reports/aging.html', {
        'aging_buckets': aging_buckets,
        'today': today,
    })


# ============ الطباعة ============

@login_required
def print_contract(request, pk):
    """طباعة عقد التقسيط"""
    contract = get_object_or_404(
        InstallmentContract.objects.select_related('customer', 'plan', 'showroom'),
        pk=pk
    )
    
    installments = contract.installments.all().order_by('installment_number')
    guarantors = contract.guarantors.all()
    
    context = {
        'contract': contract,
        'installments': installments,
        'guarantors': guarantors,
        'print_date': timezone.now(),
    }
    
    return render(request, 'installments/print/contract.html', context)


@login_required
def print_schedule(request, pk):
    """طباعة جدول الأقساط"""
    contract = get_object_or_404(
        InstallmentContract.objects.select_related('customer'),
        pk=pk
    )
    
    installments = contract.installments.all().order_by('installment_number')
    
    context = {
        'contract': contract,
        'installments': installments,
        'print_date': timezone.now(),
    }
    
    return render(request, 'installments/print/schedule.html', context)


@login_required
def print_receipt(request, pk):
    """طباعة إيصال دفعة"""
    payment = get_object_or_404(
        InstallmentPayment.objects.select_related(
            'installment__contract__customer'
        ),
        pk=pk
    )
    
    context = {
        'payment': payment,
        'print_date': timezone.now(),
    }
    
    return render(request, 'installments/print/receipt.html', context)


# ============ Views إضافية للقوالب الجديدة ============

@login_required
def contract_edit(request, pk):
    """تعديل عقد التقسيط"""
    contract = get_object_or_404(InstallmentContract, pk=pk)
    
    if request.method == 'POST':
        form = InstallmentContractForm(request.POST, request.FILES, instance=contract)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث العقد بنجاح')
            return redirect('installments:contract_detail', pk=pk)
    else:
        form = InstallmentContractForm(instance=contract)
    
    return render(request, 'installments/contract_form.html', {
        'form': form,
        'contract': contract,
    })


@login_required
def collection(request):
    """صفحة التحصيل والمتابعة"""
    today = date.today()
    
    # أقساط اليوم
    today_installments = Installment.objects.filter(
        due_date=today,
        status__in=['pending', 'partially_paid']
    ).select_related('contract', 'contract__customer').order_by('contract__customer__name')
    
    # الأقساط المتأخرة
    overdue_installments = Installment.objects.filter(
        status='overdue'
    ).select_related('contract', 'contract__customer').order_by('due_date')
    
    # الأقساط القادمة (7 أيام)
    upcoming_installments = Installment.objects.filter(
        due_date__gt=today,
        due_date__lte=today + timedelta(days=7),
        status='pending'
    ).select_related('contract', 'contract__customer').order_by('due_date')
    
    # إحصائيات
    today_collected = InstallmentPayment.objects.filter(
        payment_date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    context = {
        'today_installments': today_installments,
        'overdue_installments': overdue_installments,
        'upcoming_installments': upcoming_installments,
        'today_count': today_installments.count(),
        'overdue_count': overdue_installments.count(),
        'upcoming_count': upcoming_installments.count(),
        'today_collected': today_collected,
    }
    return render(request, 'installments/collection.html', context)


@login_required
@require_http_methods(['POST'])
def pay_installment_ajax(request, pk):
    """تسجيل دفع قسط (AJAX)"""
    installment = get_object_or_404(Installment, pk=pk)
    
    if installment.status == 'paid':
        return JsonResponse({
            'success': False,
            'error': 'هذا القسط مدفوع بالفعل'
        })
    
    try:
        data = json.loads(request.body)
        amount = Decimal(data.get('amount', str(installment.amount)))
        payment_method = data.get('payment_method', 'cash')
        
        with transaction.atomic():
            payment = InstallmentPayment.objects.create(
                installment=installment,
                amount=amount,
                payment_method=payment_method,
                payment_date=date.today(),
                collected_by=request.user
            )
            
            # تحديث حالة القسط
            if amount >= installment.remaining_amount:
                installment.status = 'paid'
            else:
                installment.status = 'partially_paid'
            installment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'تم تسجيل الدفع بنجاح',
            'paid_date': payment.payment_date.strftime('%Y-%m-%d'),
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(['POST'])
def send_reminder(request, pk):
    """إرسال تذكير للعميل"""
    installment = get_object_or_404(Installment, pk=pk)
    
    # TODO: تنفيذ إرسال الرسالة فعلياً (SMS/WhatsApp)
    
    return JsonResponse({
        'success': True,
        'message': 'تم إرسال التذكير بنجاح'
    })


@login_required
def customer_list(request):
    """قائمة عملاء التقسيط"""
    from partners.models import Customer
    
    customers = Customer.objects.filter(
        installment_contracts__isnull=False
    ).distinct().annotate(
        contracts_count=Count('installment_contracts'),
        active_contracts=Count('installment_contracts', filter=Q(installment_contracts__status='active')),
        total_amount=Sum('installment_contracts__financed_amount'),
    ).order_by('-contracts_count')
    
    search = request.GET.get('search')
    if search:
        customers = customers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search)
        )
    
    paginator = Paginator(customers, 20)
    page = request.GET.get('page', 1)
    customers = paginator.get_page(page)
    
    context = {
        'customers': customers,
    }
    return render(request, 'installments/customers.html', context)


@login_required
def reports(request):
    """صفحة التقارير الرئيسية"""
    today = date.today()
    
    # تحديد الفترة
    period = request.GET.get('period', 'this_month')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    if period == 'this_month':
        start = today.replace(day=1)
        end = today
    elif period == 'last_month':
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        start = last_month_end.replace(day=1)
        end = last_month_end
    elif period == 'this_quarter':
        quarter = (today.month - 1) // 3
        start = date(today.year, quarter * 3 + 1, 1)
        end = today
    elif period == 'this_year':
        start = date(today.year, 1, 1)
        end = today
    elif period == 'custom' and from_date and to_date:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
    else:
        start = today.replace(day=1)
        end = today
    
    # KPIs
    from django.db.models.functions import TruncMonth
    
    kpi = {
        'total_contracts': InstallmentContract.objects.filter(
            created_at__date__gte=start,
            created_at__date__lte=end
        ).count(),
        'total_collected': InstallmentPayment.objects.filter(
            payment_date__gte=start,
            payment_date__lte=end
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'pending_amount': Installment.objects.filter(
            status__in=['pending', 'partially_paid']
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'overdue_amount': Installment.objects.filter(
            status='overdue'
        ).aggregate(total=Sum('amount'))['total'] or 0,
    }
    
    # بيانات الرسم البياني
    months_data = InstallmentPayment.objects.filter(
        payment_date__gte=date(today.year, 1, 1)
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        collected=Sum('amount')
    ).order_by('month')
    
    months_labels = []
    collection_data = []
    month_names = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                   'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
    
    for item in months_data:
        if item['month']:
            months_labels.append(month_names[item['month'].month - 1])
            collection_data.append(float(item['collected'] or 0))
    
    # توزيع الحالات
    status_counts = InstallmentContract.objects.values('status').annotate(count=Count('id'))
    status_data = [0, 0, 0]  # active, completed, defaulted
    for item in status_counts:
        if item['status'] == 'active':
            status_data[0] = item['count']
        elif item['status'] == 'completed':
            status_data[1] = item['count']
        elif item['status'] == 'defaulted':
            status_data[2] = item['count']
    
    # أفضل العملاء
    from partners.models import Customer
    top_customers = Customer.objects.filter(
        installment_contracts__isnull=False
    ).annotate(
        contracts_count=Count('installment_contracts'),
        total_installments=Sum('installment_contracts__financed_amount'),
        total_paid=Sum('installment_contracts__installments__payments__amount')
    ).order_by('-total_paid')[:10]
    
    for customer in top_customers:
        if customer.total_installments and customer.total_paid:
            customer.commitment_rate = (customer.total_paid / customer.total_installments) * 100
        else:
            customer.commitment_rate = 0
    
    context = {
        'kpi': kpi,
        'period': period,
        'from_date': start,
        'to_date': end,
        'months_labels': json.dumps(months_labels),
        'collection_data': json.dumps(collection_data),
        'due_data': json.dumps([0] * len(collection_data)),
        'status_data': json.dumps(status_data),
        'top_customers': top_customers,
    }
    return render(request, 'installments/reports.html', context)


@login_required
def reports_export(request):
    """تصدير التقارير"""
    export_format = request.GET.get('export', 'excel')
    messages.info(request, 'جاري تطوير خاصية التصدير')
    return redirect('installments:reports')


@login_required
def report_collection(request):
    """تقرير التحصيل"""
    context = {}
    return render(request, 'installments/reports/collection.html', context)


@login_required
def report_overdue(request):
    """تقرير المتأخرات"""
    context = {}
    return render(request, 'installments/reports/overdue.html', context)


@login_required
def report_customers(request):
    """تقرير العملاء"""
    context = {}
    return render(request, 'installments/reports/customers.html', context)


@login_required
def report_forecast(request):
    """تقرير التوقعات"""
    context = {}
    return render(request, 'installments/reports/forecast.html', context)


# ============ التسوية المبكرة ============

@login_required
def early_settlement_list(request):
    """قائمة طلبات التسوية المبكرة"""
    settlements = EarlySettlement.objects.select_related(
        'contract', 'contract__customer'
    ).order_by('-request_date')
    
    status = request.GET.get('status')
    if status:
        settlements = settlements.filter(status=status)
    
    paginator = Paginator(settlements, 20)
    page = request.GET.get('page')
    settlements = paginator.get_page(page)
    
    return render(request, 'installments/early_settlement_list.html', {
        'settlements': settlements,
        'status_choices': EarlySettlement.STATUS_CHOICES,
    })


@login_required
@permission_required('installments.add_earlysettlement')
def early_settlement_create(request, contract_pk):
    """إنشاء طلب تسوية مبكرة"""
    contract = get_object_or_404(InstallmentContract, pk=contract_pk)
    
    if contract.status != 'active':
        messages.error(request, 'لا يمكن إنشاء تسوية لعقد غير نشط')
        return redirect('installments:contract_detail', pk=contract_pk)
    
    if request.method == 'POST':
        discount_percent = Decimal(request.POST.get('discount_percentage', '0'))
        reason = request.POST.get('reason', '')
        
        settlement = EarlySettlement(
            contract=contract,
            reason=reason,
            requested_by=request.user
        )
        settlement.calculate_settlement(discount_percent)
        settlement.save()
        
        messages.success(request, 'تم إنشاء طلب التسوية المبكرة بنجاح')
        return redirect('installments:early_settlement_detail', pk=settlement.pk)
    
    # حساب المبالغ للعرض
    unpaid = contract.installments.filter(status__in=['pending', 'partially_paid', 'overdue'])
    remaining = sum(i.amount - i.paid_amount for i in unpaid)
    
    context = {
        'contract': contract,
        'remaining_amount': remaining,
        'unpaid_count': unpaid.count(),
    }
    
    return render(request, 'installments/early_settlement_form.html', context)


@login_required
def early_settlement_detail(request, pk):
    """تفاصيل طلب التسوية المبكرة"""
    settlement = get_object_or_404(
        EarlySettlement.objects.select_related('contract', 'contract__customer'),
        pk=pk
    )
    
    return render(request, 'installments/early_settlement_detail.html', {
        'settlement': settlement,
    })


@login_required
@permission_required('installments.change_earlysettlement')
def early_settlement_approve(request, pk):
    """الموافقة على التسوية المبكرة"""
    settlement = get_object_or_404(EarlySettlement, pk=pk)
    
    if settlement.status != 'pending':
        messages.error(request, 'لا يمكن الموافقة على هذا الطلب')
        return redirect('installments:early_settlement_detail', pk=pk)
    
    with transaction.atomic():
        settlement.status = 'approved'
        settlement.approved_by = request.user
        settlement.save()
    
    messages.success(request, 'تم الموافقة على طلب التسوية')
    return redirect('installments:early_settlement_detail', pk=pk)


@login_required
@permission_required('installments.change_earlysettlement')
def early_settlement_complete(request, pk):
    """إتمام التسوية المبكرة"""
    settlement = get_object_or_404(EarlySettlement, pk=pk)
    
    if settlement.status != 'approved':
        messages.error(request, 'يجب الموافقة على الطلب أولاً')
        return redirect('installments:early_settlement_detail', pk=pk)
    
    with transaction.atomic():
        # تحديث الأقساط المتبقية
        settlement.contract.installments.filter(
            status__in=['pending', 'partially_paid', 'overdue']
        ).update(status='paid', paid_amount=F('amount'))
        
        # تحديث العقد
        settlement.contract.status = 'completed'
        settlement.contract.save()
        
        # تحديث التسوية
        settlement.status = 'completed'
        settlement.settlement_date = timezone.now().date()
        settlement.save()
    
    messages.success(request, 'تم إتمام التسوية المبكرة بنجاح')
    return redirect('installments:contract_detail', pk=settlement.contract.pk)


# ============ إعادة الجدولة ============

@login_required
def reschedule_list(request):
    """قائمة طلبات إعادة الجدولة"""
    reschedules = ContractReschedule.objects.select_related(
        'contract', 'contract__customer'
    ).order_by('-request_date')
    
    status = request.GET.get('status')
    if status:
        reschedules = reschedules.filter(status=status)
    
    paginator = Paginator(reschedules, 20)
    page = request.GET.get('page')
    reschedules = paginator.get_page(page)
    
    return render(request, 'installments/reschedule_list.html', {
        'reschedules': reschedules,
    })


@login_required
@permission_required('installments.add_contractreschedule')
def reschedule_create(request, contract_pk):
    """إنشاء طلب إعادة جدولة"""
    contract = get_object_or_404(InstallmentContract, pk=contract_pk)
    
    if contract.status not in ['active', 'defaulted']:
        messages.error(request, 'لا يمكن إعادة جدولة هذا العقد')
        return redirect('installments:contract_detail', pk=contract_pk)
    
    if request.method == 'POST':
        new_duration = int(request.POST.get('new_duration_months', 12))
        new_start_date = request.POST.get('new_start_date')
        reason = request.POST.get('reason', '')
        additional_interest = Decimal(request.POST.get('additional_interest', '0'))
        
        # حساب المبلغ المتبقي
        unpaid = contract.installments.filter(status__in=['pending', 'partially_paid', 'overdue'])
        remaining = sum(i.amount - i.paid_amount for i in unpaid)
        
        new_monthly = ((remaining + additional_interest) / new_duration).quantize(Decimal('0.01'))
        
        reschedule = ContractReschedule.objects.create(
            contract=contract,
            original_monthly_payment=contract.monthly_payment,
            original_remaining_months=unpaid.count(),
            original_remaining_amount=remaining,
            new_monthly_payment=new_monthly,
            new_duration_months=new_duration,
            new_start_date=new_start_date,
            additional_interest=additional_interest,
            reason=reason,
            requested_by=request.user
        )
        
        messages.success(request, 'تم إنشاء طلب إعادة الجدولة بنجاح')
        return redirect('installments:reschedule_detail', pk=reschedule.pk)
    
    # حساب البيانات للعرض
    unpaid = contract.installments.filter(status__in=['pending', 'partially_paid', 'overdue'])
    remaining = sum(i.amount - i.paid_amount for i in unpaid)
    
    context = {
        'contract': contract,
        'remaining_amount': remaining,
        'remaining_months': unpaid.count(),
    }
    
    return render(request, 'installments/reschedule_form.html', context)


@login_required
def reschedule_detail(request, pk):
    """تفاصيل طلب إعادة الجدولة"""
    reschedule = get_object_or_404(
        ContractReschedule.objects.select_related('contract', 'contract__customer'),
        pk=pk
    )
    
    return render(request, 'installments/reschedule_detail.html', {
        'reschedule': reschedule,
    })


@login_required
@permission_required('installments.change_contractreschedule')
def reschedule_approve(request, pk):
    """الموافقة على إعادة الجدولة وتطبيقها"""
    reschedule = get_object_or_404(ContractReschedule, pk=pk)
    
    if reschedule.status != 'pending':
        messages.error(request, 'لا يمكن الموافقة على هذا الطلب')
        return redirect('installments:reschedule_detail', pk=pk)
    
    with transaction.atomic():
        reschedule.status = 'approved'
        reschedule.approved_by = request.user
        reschedule.save()
        
        reschedule.apply_reschedule()
    
    messages.success(request, 'تم الموافقة على إعادة الجدولة وتطبيقها بنجاح')
    return redirect('installments:contract_detail', pk=reschedule.contract.pk)


# ============ نقل الملكية ============

@login_required
def transfer_list(request):
    """قائمة طلبات نقل الملكية"""
    transfers = ContractTransfer.objects.select_related(
        'contract', 'original_customer', 'new_customer'
    ).order_by('-request_date')
    
    status = request.GET.get('status')
    if status:
        transfers = transfers.filter(status=status)
    
    paginator = Paginator(transfers, 20)
    page = request.GET.get('page')
    transfers = paginator.get_page(page)
    
    return render(request, 'installments/transfer_list.html', {
        'transfers': transfers,
    })


@login_required
@permission_required('installments.add_contracttransfer')
def transfer_create(request, contract_pk):
    """إنشاء طلب نقل ملكية"""
    from partners.models import Customer
    
    contract = get_object_or_404(InstallmentContract, pk=contract_pk)
    
    if contract.status != 'active':
        messages.error(request, 'لا يمكن نقل ملكية عقد غير نشط')
        return redirect('installments:contract_detail', pk=contract_pk)
    
    if request.method == 'POST':
        new_customer_id = request.POST.get('new_customer')
        transfer_fee = Decimal(request.POST.get('transfer_fee', '0'))
        reason = request.POST.get('reason', '')
        
        new_customer = get_object_or_404(Customer, pk=new_customer_id)
        
        transfer = ContractTransfer.objects.create(
            contract=contract,
            original_customer=contract.customer,
            new_customer=new_customer,
            transfer_fee=transfer_fee,
            reason=reason,
            requested_by=request.user
        )
        
        messages.success(request, 'تم إنشاء طلب نقل الملكية بنجاح')
        return redirect('installments:transfer_detail', pk=transfer.pk)
    
    customers = Customer.objects.exclude(pk=contract.customer.pk).order_by('name')
    
    context = {
        'contract': contract,
        'customers': customers,
    }
    
    return render(request, 'installments/transfer_form.html', context)


@login_required
def transfer_detail(request, pk):
    """تفاصيل طلب نقل الملكية"""
    transfer = get_object_or_404(
        ContractTransfer.objects.select_related(
            'contract', 'original_customer', 'new_customer'
        ),
        pk=pk
    )
    
    return render(request, 'installments/transfer_detail.html', {
        'transfer': transfer,
    })


@login_required
@permission_required('installments.change_contracttransfer')
def transfer_approve(request, pk):
    """الموافقة على نقل الملكية"""
    transfer = get_object_or_404(ContractTransfer, pk=pk)
    
    if transfer.status != 'pending':
        messages.error(request, 'لا يمكن الموافقة على هذا الطلب')
        return redirect('installments:transfer_detail', pk=pk)
    
    with transaction.atomic():
        transfer.status = 'approved'
        transfer.approved_by = request.user
        transfer.save()
        
        transfer.complete_transfer()
    
    messages.success(request, 'تم نقل الملكية بنجاح')
    return redirect('installments:contract_detail', pk=transfer.contract.pk)


# ============ التقييم الائتماني ============

@login_required
def credit_score_list(request):
    """قائمة التقييمات الائتمانية"""
    scores = CustomerCreditScore.objects.select_related('customer').order_by('-score')
    
    level = request.GET.get('level')
    if level:
        scores = scores.filter(level=level)
    
    search = request.GET.get('search')
    if search:
        scores = scores.filter(customer__name__icontains=search)
    
    paginator = Paginator(scores, 20)
    page = request.GET.get('page')
    scores = paginator.get_page(page)
    
    # إحصائيات
    stats = CustomerCreditScore.objects.aggregate(
        avg_score=Avg('score'),
        total_customers=Count('id'),
        excellent=Count('id', filter=Q(level='excellent')),
        good=Count('id', filter=Q(level='good')),
        fair=Count('id', filter=Q(level='fair')),
        poor=Count('id', filter=Q(level='poor')),
        bad=Count('id', filter=Q(level='bad')),
    )
    
    return render(request, 'installments/credit_score_list.html', {
        'scores': scores,
        'stats': stats,
        'level_choices': CustomerCreditScore.SCORE_LEVEL,
    })


@login_required
def credit_score_detail(request, customer_pk):
    """تفاصيل التقييم الائتماني للعميل"""
    from partners.models import Customer
    
    customer = get_object_or_404(Customer, pk=customer_pk)
    
    # الحصول أو إنشاء التقييم
    score, created = CustomerCreditScore.objects.get_or_create(customer=customer)
    
    if created or request.GET.get('refresh'):
        score.calculate_score()
    
    # عقود العميل
    contracts = InstallmentContract.objects.filter(customer=customer).order_by('-created_at')
    
    # سجل الدفعات
    payments = InstallmentPayment.objects.filter(
        installment__contract__customer=customer
    ).order_by('-payment_date')[:20]
    
    context = {
        'customer': customer,
        'score': score,
        'contracts': contracts,
        'payments': payments,
    }
    
    return render(request, 'installments/credit_score_detail.html', context)


@login_required
@permission_required('installments.change_customercreditscore')
def credit_score_refresh(request, customer_pk):
    """تحديث التقييم الائتماني"""
    from partners.models import Customer
    
    customer = get_object_or_404(Customer, pk=customer_pk)
    score, created = CustomerCreditScore.objects.get_or_create(customer=customer)
    score.calculate_score()
    
    messages.success(request, f'تم تحديث التقييم الائتماني: {score.score} نقطة')
    return redirect('installments:credit_score_detail', customer_pk=customer_pk)


# ============ إجراءات التحصيل ============

@login_required
def collection_actions_list(request):
    """قائمة إجراءات التحصيل"""
    actions = CollectionAction.objects.select_related(
        'installment__contract', 'installment__contract__customer', 'performed_by'
    ).order_by('-action_date')
    
    action_type = request.GET.get('action_type')
    if action_type:
        actions = actions.filter(action_type=action_type)
    
    result = request.GET.get('result')
    if result:
        actions = actions.filter(result=result)
    
    # فقط التي تحتاج متابعة
    pending_followup = request.GET.get('pending_followup')
    if pending_followup:
        actions = actions.filter(
            follow_up_date__lte=date.today(),
            follow_up_done=False
        )
    
    paginator = Paginator(actions, 30)
    page = request.GET.get('page')
    actions = paginator.get_page(page)
    
    return render(request, 'installments/collection_actions_list.html', {
        'actions': actions,
        'action_types': CollectionAction.ACTION_TYPE,
        'result_choices': CollectionAction.RESULT_CHOICES,
    })


@login_required
@permission_required('installments.add_collectionaction')
def collection_action_create(request, installment_pk):
    """تسجيل إجراء تحصيل"""
    installment = get_object_or_404(
        Installment.objects.select_related('contract', 'contract__customer'),
        pk=installment_pk
    )
    
    if request.method == 'POST':
        action = CollectionAction.objects.create(
            installment=installment,
            action_type=request.POST.get('action_type'),
            result=request.POST.get('result', ''),
            promise_date=request.POST.get('promise_date') or None,
            promise_amount=Decimal(request.POST.get('promise_amount', '0')) or None,
            notes=request.POST.get('notes', ''),
            follow_up_date=request.POST.get('follow_up_date') or None,
            performed_by=request.user
        )
        
        messages.success(request, 'تم تسجيل إجراء التحصيل بنجاح')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'id': action.id})
        
        return redirect('installments:contract_detail', pk=installment.contract.pk)
    
    context = {
        'installment': installment,
        'action_types': CollectionAction.ACTION_TYPE,
        'result_choices': CollectionAction.RESULT_CHOICES,
    }
    
    return render(request, 'installments/collection_action_form.html', context)


# ============ الإعفاءات ============

@login_required
def waiver_list(request):
    """قائمة الإعفاءات"""
    waivers = InstallmentWaiver.objects.select_related(
        'installment__contract', 'installment__contract__customer'
    ).order_by('-request_date')
    
    status = request.GET.get('status')
    if status:
        waivers = waivers.filter(status=status)
    
    paginator = Paginator(waivers, 20)
    page = request.GET.get('page')
    waivers = paginator.get_page(page)
    
    return render(request, 'installments/waiver_list.html', {
        'waivers': waivers,
        'status_choices': InstallmentWaiver.STATUS_CHOICES,
    })


@login_required
@permission_required('installments.add_installmentwaiver')
def waiver_create(request, installment_pk):
    """إنشاء طلب إعفاء"""
    installment = get_object_or_404(
        Installment.objects.select_related('contract', 'contract__customer'),
        pk=installment_pk
    )
    
    if request.method == 'POST':
        waiver_type = request.POST.get('waiver_type')
        waiver_amount = Decimal(request.POST.get('waiver_amount', '0'))
        reason = request.POST.get('reason', '')
        
        waiver = InstallmentWaiver.objects.create(
            installment=installment,
            waiver_type=waiver_type,
            waiver_amount=waiver_amount,
            reason=reason,
            requested_by=request.user
        )
        
        messages.success(request, 'تم إنشاء طلب الإعفاء بنجاح')
        return redirect('installments:waiver_detail', pk=waiver.pk)
    
    context = {
        'installment': installment,
        'waiver_types': InstallmentWaiver.WAIVER_TYPE,
    }
    
    return render(request, 'installments/waiver_form.html', context)


@login_required
def waiver_detail(request, pk):
    """تفاصيل طلب الإعفاء"""
    waiver = get_object_or_404(
        InstallmentWaiver.objects.select_related(
            'installment__contract', 'installment__contract__customer'
        ),
        pk=pk
    )
    
    return render(request, 'installments/waiver_detail.html', {
        'waiver': waiver,
    })


@login_required
@permission_required('installments.change_installmentwaiver')
def waiver_approve(request, pk):
    """الموافقة على الإعفاء"""
    waiver = get_object_or_404(InstallmentWaiver, pk=pk)
    
    if waiver.status != 'pending':
        messages.error(request, 'لا يمكن الموافقة على هذا الطلب')
        return redirect('installments:waiver_detail', pk=pk)
    
    with transaction.atomic():
        waiver.status = 'approved'
        waiver.approved_by = request.user
        waiver.save()
        
        waiver.apply_waiver()
    
    messages.success(request, 'تم الموافقة على الإعفاء وتطبيقه')
    return redirect('installments:contract_detail', pk=waiver.installment.contract.pk)


# ============ إعدادات النظام ============

@login_required
@permission_required('installments.change_installmentsettings')
def settings_view(request):
    """إعدادات نظام التقسيط"""
    settings = InstallmentSettings.get_settings()
    
    if request.method == 'POST':
        settings.auto_reminders_enabled = request.POST.get('auto_reminders_enabled') == 'on'
        settings.reminder_days_before = int(request.POST.get('reminder_days_before', 3))
        settings.overdue_reminder_interval = int(request.POST.get('overdue_reminder_interval', 7))
        settings.max_reminders_per_installment = int(request.POST.get('max_reminders_per_installment', 5))
        settings.sms_enabled = request.POST.get('sms_enabled') == 'on'
        settings.whatsapp_enabled = request.POST.get('whatsapp_enabled') == 'on'
        settings.email_enabled = request.POST.get('email_enabled') == 'on'
        settings.push_enabled = request.POST.get('push_enabled') == 'on'
        settings.default_after_days = int(request.POST.get('default_after_days', 90))
        settings.upcoming_message_template = request.POST.get('upcoming_message_template', '')
        settings.due_message_template = request.POST.get('due_message_template', '')
        settings.overdue_message_template = request.POST.get('overdue_message_template', '')
        settings.save()
        
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
        return redirect('installments:settings')
    
    return render(request, 'installments/settings.html', {
        'settings': settings,
    })


# ============ API للتقييم الائتماني ============

@login_required
@require_http_methods(['GET'])
def api_check_credit(request, customer_pk):
    """API للتحقق من الائتمان المتاح للعميل"""
    from partners.models import Customer
    
    try:
        customer = Customer.objects.get(pk=customer_pk)
        score, created = CustomerCreditScore.objects.get_or_create(customer=customer)
        
        if created:
            score.calculate_score()
        
        return JsonResponse({
            'success': True,
            'customer_name': customer.name,
            'score': score.score,
            'level': score.level,
            'level_display': score.get_level_display(),
            'max_credit_limit': str(score.max_credit_limit),
            'available_credit': str(score.available_credit),
            'can_get_credit': score.available_credit > 0,
        })
    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'العميل غير موجود'
        })


@login_required
@require_http_methods(['GET'])
def api_contract_summary(request, pk):
    """API لملخص العقد"""
    contract = get_object_or_404(InstallmentContract, pk=pk)
    
    installments = contract.installments.all()
    
    return JsonResponse({
        'contract_number': contract.contract_number,
        'customer_name': contract.customer.name,
        'status': contract.status,
        'status_display': contract.get_status_display(),
        'principal_amount': str(contract.principal_amount),
        'down_payment': str(contract.down_payment),
        'financed_amount': str(contract.financed_amount),
        'monthly_payment': str(contract.monthly_payment),
        'total_amount': str(contract.total_amount),
        'paid_amount': str(contract.paid_amount),
        'remaining_amount': str(contract.remaining_amount),
        'progress_percentage': contract.progress_percentage,
        'overdue_amount': str(contract.overdue_amount),
        'overdue_count': contract.overdue_count,
        'total_installments': installments.count(),
        'paid_installments': installments.filter(status='paid').count(),
        'pending_installments': installments.filter(status='pending').count(),
        'next_installment': {
            'number': contract.next_installment.installment_number if contract.next_installment else None,
            'due_date': contract.next_installment.due_date.isoformat() if contract.next_installment else None,
            'amount': str(contract.next_installment.amount) if contract.next_installment else None,
        } if contract.next_installment else None,
    })
