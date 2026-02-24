"""
عروض نظام الخدمات الإلكترونية - Tony ERP
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
import uuid

from .models import (
    ServiceCategory, ServiceProvider, EService, MobileOperator,
    RechargePackage, BillType, ServiceTransaction, MobileRecharge,
    BillPayment, MoneyTransfer, ServiceReport
)
from .forms import (
    ServiceCategoryForm, ServiceProviderForm, EServiceForm,
    MobileOperatorForm, RechargePackageForm, BillTypeForm,
    MobileRechargeForm, BillPaymentForm, MoneyTransferForm
)


def generate_transaction_id():
    """توليد رقم معاملة فريد"""
    return f"TXN-{uuid.uuid4().hex[:12].upper()}"


@login_required
def dashboard(request):
    """لوحة تحكم الخدمات الإلكترونية"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # إحصائيات اليوم
    today_transactions = ServiceTransaction.objects.filter(created_at__date=today)
    today_stats = today_transactions.aggregate(
        count=Count('id'),
        total=Sum('total'),
        fees=Sum('fee')
    )
    
    # إحصائيات الأسبوع
    week_transactions = ServiceTransaction.objects.filter(created_at__date__gte=week_ago)
    week_stats = week_transactions.aggregate(
        count=Count('id'),
        total=Sum('total')
    )
    
    # معاملات معلقة
    pending_count = ServiceTransaction.objects.filter(status='pending').count()
    
    # أحدث المعاملات
    recent_transactions = ServiceTransaction.objects.select_related(
        'service', 'user'
    ).order_by('-created_at')[:10]
    
    # الخدمات الأكثر استخداماً
    top_services = EService.objects.annotate(
        usage_count=Count('transactions')
    ).order_by('-usage_count')[:5]
    
    # الفئات
    categories = ServiceCategory.objects.filter(is_active=True).order_by('order')
    
    context = {
        'today_stats': today_stats,
        'week_stats': week_stats,
        'pending_count': pending_count,
        'recent_transactions': recent_transactions,
        'top_services': top_services,
        'categories': categories,
    }
    return render(request, 'eservices/dashboard.html', context)


# ==================== الفئات ====================

@login_required
def category_list(request):
    """قائمة فئات الخدمات"""
    categories = ServiceCategory.objects.annotate(
        service_count=Count('services')
    ).order_by('order', 'name')
    return render(request, 'eservices/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    """إضافة فئة"""
    if request.method == 'POST':
        form = ServiceCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة الفئة بنجاح'))
            return redirect('eservices:category_list')
    else:
        form = ServiceCategoryForm()
    return render(request, 'eservices/category_form.html', {'form': form, 'title': _('إضافة فئة')})


@login_required
def category_edit(request, pk):
    """تعديل فئة"""
    category = get_object_or_404(ServiceCategory, pk=pk)
    if request.method == 'POST':
        form = ServiceCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الفئة بنجاح'))
            return redirect('eservices:category_list')
    else:
        form = ServiceCategoryForm(instance=category)
    return render(request, 'eservices/category_form.html', {
        'form': form, 'category': category, 'title': _('تعديل فئة')
    })


# ==================== مزودي الخدمات ====================

@login_required
def provider_list(request):
    """قائمة مزودي الخدمات"""
    providers = ServiceProvider.objects.annotate(
        service_count=Count('services')
    ).order_by('-is_active', 'name')
    return render(request, 'eservices/provider_list.html', {'providers': providers})


@login_required
def provider_create(request):
    """إضافة مزود خدمة"""
    if request.method == 'POST':
        form = ServiceProviderForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة المزود بنجاح'))
            return redirect('eservices:provider_list')
    else:
        form = ServiceProviderForm()
    return render(request, 'eservices/provider_form.html', {'form': form, 'title': _('إضافة مزود خدمة')})


@login_required
def provider_edit(request, pk):
    """تعديل مزود خدمة"""
    provider = get_object_or_404(ServiceProvider, pk=pk)
    if request.method == 'POST':
        form = ServiceProviderForm(request.POST, request.FILES, instance=provider)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث المزود بنجاح'))
            return redirect('eservices:provider_list')
    else:
        form = ServiceProviderForm(instance=provider)
    return render(request, 'eservices/provider_form.html', {
        'form': form, 'provider': provider, 'title': _('تعديل مزود خدمة')
    })


# ==================== الخدمات ====================

@login_required
def service_list(request):
    """قائمة الخدمات"""
    services = EService.objects.select_related('category', 'provider').order_by('category', 'name')
    
    category_id = request.GET.get('category')
    if category_id:
        services = services.filter(category_id=category_id)
    
    categories = ServiceCategory.objects.filter(is_active=True)
    return render(request, 'eservices/service_list.html', {
        'services': services,
        'categories': categories,
    })


@login_required
def service_create(request):
    """إضافة خدمة"""
    if request.method == 'POST':
        form = EServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة الخدمة بنجاح'))
            return redirect('eservices:service_list')
    else:
        form = EServiceForm()
    return render(request, 'eservices/service_form.html', {'form': form, 'title': _('إضافة خدمة')})


@login_required
def service_edit(request, pk):
    """تعديل خدمة"""
    service = get_object_or_404(EService, pk=pk)
    if request.method == 'POST':
        form = EServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الخدمة بنجاح'))
            return redirect('eservices:service_list')
    else:
        form = EServiceForm(instance=service)
    return render(request, 'eservices/service_form.html', {
        'form': form, 'service': service, 'title': _('تعديل خدمة')
    })


# ==================== شحن الرصيد ====================

@login_required
def recharge_dashboard(request):
    """لوحة شحن الرصيد"""
    operators = MobileOperator.objects.filter(is_active=True)
    packages = RechargePackage.objects.filter(is_active=True).select_related('operator')
    
    return render(request, 'eservices/recharge_dashboard.html', {
        'operators': operators,
        'packages': packages,
    })


@login_required
def recharge_create(request):
    """شحن رصيد جديد"""
    if request.method == 'POST':
        form = MobileRechargeForm(request.POST)
        if form.is_valid():
            mobile_number = form.cleaned_data['mobile_number']
            amount = form.cleaned_data['amount']
            operator = form.cleaned_data['operator']
            
            # إنشاء المعاملة
            service = EService.objects.filter(service_type='mobile_recharge').first()
            if not service:
                messages.error(request, _('خدمة شحن الرصيد غير متوفرة'))
                return redirect('eservices:recharge_dashboard')
            
            fee = service.calculate_fee(amount)
            transaction = ServiceTransaction.objects.create(
                transaction_id=generate_transaction_id(),
                service=service,
                user=request.user,
                amount=amount,
                fee=fee,
                total=amount + fee,
                service_number=mobile_number,
                status='processing'
            )
            
            # إنشاء سجل الشحن
            MobileRecharge.objects.create(
                transaction=transaction,
                operator=operator,
                mobile_number=mobile_number,
                package=form.cleaned_data.get('package')
            )
            
            # محاكاة الاتصال بـ API المزود (يمكن استبداله بالاتصال الفعلي لاحقاً)
            # في بيئة الإنتاج، يتم استبدال هذا بـ:
            # response = operator.api_client.recharge(mobile_number, amount)
            # if response.success:
            #     transaction.status = 'completed'
            # else:
            #     transaction.status = 'failed'
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.save()
            
            messages.success(request, _('تم شحن الرصيد بنجاح. رقم المعاملة: ') + transaction.transaction_id)
            return redirect('eservices:transaction_detail', pk=transaction.pk)
    else:
        form = MobileRechargeForm()
    
    operators = MobileOperator.objects.filter(is_active=True)
    return render(request, 'eservices/recharge_form.html', {
        'form': form,
        'operators': operators,
    })


# ==================== دفع الفواتير ====================

@login_required
def bill_dashboard(request):
    """لوحة دفع الفواتير"""
    bill_types = BillType.objects.filter(is_active=True)
    return render(request, 'eservices/bill_dashboard.html', {'bill_types': bill_types})


@login_required
def bill_payment_create(request):
    """دفع فاتورة"""
    if request.method == 'POST':
        form = BillPaymentForm(request.POST)
        if form.is_valid():
            bill_type = form.cleaned_data['bill_type']
            bill_number = form.cleaned_data['bill_number']
            amount = form.cleaned_data['amount']
            
            # إنشاء المعاملة
            service = EService.objects.filter(service_type='bill_payment').first()
            if not service:
                messages.error(request, _('خدمة دفع الفواتير غير متوفرة'))
                return redirect('eservices:bill_dashboard')
            
            fee = bill_type.service_fee
            transaction = ServiceTransaction.objects.create(
                transaction_id=generate_transaction_id(),
                service=service,
                user=request.user,
                amount=amount,
                fee=fee,
                total=amount + fee,
                service_number=bill_number,
                status='processing'
            )
            
            BillPayment.objects.create(
                transaction=transaction,
                bill_type=bill_type,
                bill_number=bill_number,
                customer_name=form.cleaned_data.get('customer_name', ''),
                bill_amount=amount
            )
            
            # محاكاة الاتصال بـ API مزود الخدمة (يمكن استبداله بالاتصال الفعلي لاحقاً)
            # في بيئة الإنتاج:
            # response = bill_type.api_client.pay_bill(bill_number, amount)
            # transaction.status = 'completed' if response.success else 'failed'
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.save()
            
            messages.success(request, _('تم دفع الفاتورة بنجاح'))
            return redirect('eservices:transaction_detail', pk=transaction.pk)
    else:
        form = BillPaymentForm()
    
    bill_types = BillType.objects.filter(is_active=True)
    return render(request, 'eservices/bill_form.html', {
        'form': form,
        'bill_types': bill_types,
    })


# ==================== تحويل الأموال ====================

@login_required
def transfer_dashboard(request):
    """لوحة تحويل الأموال"""
    return render(request, 'eservices/transfer_dashboard.html')


@login_required
def transfer_create(request):
    """تحويل أموال"""
    if request.method == 'POST':
        form = MoneyTransferForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            
            service = EService.objects.filter(service_type='money_transfer').first()
            if not service:
                messages.error(request, _('خدمة تحويل الأموال غير متوفرة'))
                return redirect('eservices:transfer_dashboard')
            
            fee = service.calculate_fee(amount)
            transaction = ServiceTransaction.objects.create(
                transaction_id=generate_transaction_id(),
                service=service,
                user=request.user,
                amount=amount,
                fee=fee,
                total=amount + fee,
                service_number=form.cleaned_data['receiver_phone'],
                status='processing'
            )
            
            MoneyTransfer.objects.create(
                transaction=transaction,
                transfer_type=form.cleaned_data['transfer_type'],
                sender_name=form.cleaned_data['sender_name'],
                sender_phone=form.cleaned_data['sender_phone'],
                receiver_name=form.cleaned_data['receiver_name'],
                receiver_phone=form.cleaned_data['receiver_phone'],
                receiver_account=form.cleaned_data.get('receiver_account', ''),
                notes=form.cleaned_data.get('notes', '')
            )
            
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.save()
            
            messages.success(request, _('تم التحويل بنجاح'))
            return redirect('eservices:transaction_detail', pk=transaction.pk)
    else:
        form = MoneyTransferForm()
    
    return render(request, 'eservices/transfer_form.html', {'form': form})


# ==================== المعاملات ====================

@login_required
def transaction_list(request):
    """قائمة المعاملات"""
    transactions = ServiceTransaction.objects.select_related(
        'service', 'user'
    ).order_by('-created_at')
    
    status = request.GET.get('status')
    service_type = request.GET.get('type')
    search = request.GET.get('search')
    
    if status:
        transactions = transactions.filter(status=status)
    if service_type:
        transactions = transactions.filter(service__service_type=service_type)
    if search:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search) |
            Q(service_number__icontains=search)
        )
    
    paginator = Paginator(transactions, 25)
    page = request.GET.get('page')
    transactions = paginator.get_page(page)
    
    return render(request, 'eservices/transaction_list.html', {
        'transactions': transactions,
        'status_choices': ServiceTransaction.STATUS_CHOICES,
    })


@login_required
def transaction_detail(request, pk):
    """تفاصيل المعاملة"""
    transaction = get_object_or_404(ServiceTransaction, pk=pk)
    
    # جلب التفاصيل حسب النوع
    recharge = getattr(transaction, 'recharge', None)
    bill_payment = getattr(transaction, 'bill_payment', None)
    money_transfer = getattr(transaction, 'money_transfer', None)
    
    return render(request, 'eservices/transaction_detail.html', {
        'transaction': transaction,
        'recharge': recharge,
        'bill_payment': bill_payment,
        'money_transfer': money_transfer,
    })


# ==================== المشغلين ====================

@login_required
def operator_list(request):
    """قائمة مشغلي الاتصالات"""
    operators = MobileOperator.objects.annotate(
        package_count=Count('packages')
    )
    return render(request, 'eservices/operator_list.html', {'operators': operators})


@login_required
def operator_create(request):
    """إضافة مشغل"""
    if request.method == 'POST':
        form = MobileOperatorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة المشغل بنجاح'))
            return redirect('eservices:operator_list')
    else:
        form = MobileOperatorForm()
    return render(request, 'eservices/operator_form.html', {'form': form, 'title': _('إضافة مشغل')})


# ==================== التقارير ====================

@login_required
def reports_dashboard(request):
    """لوحة التقارير"""
    return render(request, 'eservices/reports_dashboard.html')


@login_required
def transactions_report(request):
    """تقرير المعاملات"""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    transactions = ServiceTransaction.objects.select_related('service')
    
    if from_date:
        transactions = transactions.filter(created_at__date__gte=from_date)
    if to_date:
        transactions = transactions.filter(created_at__date__lte=to_date)
    
    stats = transactions.aggregate(
        total_count=Count('id'),
        total_amount=Sum('total'),
        total_fees=Sum('fee'),
        completed_count=Count('id', filter=Q(status='completed')),
        failed_count=Count('id', filter=Q(status='failed')),
    )
    
    return render(request, 'eservices/transactions_report.html', {
        'transactions': transactions[:100],
        'stats': stats,
    })


@login_required
def revenue_report(request):
    """تقرير الإيرادات"""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    transactions = ServiceTransaction.objects.filter(status='completed')
    
    if from_date:
        transactions = transactions.filter(created_at__date__gte=from_date)
    if to_date:
        transactions = transactions.filter(created_at__date__lte=to_date)
    
    stats = transactions.aggregate(
        total_amount=Sum('amount'),
        total_fees=Sum('fee'),
        total_revenue=Sum('total'),
    )
    
    # تجميع حسب الخدمة
    by_service = transactions.values(
        'service__name', 'service__service_type'
    ).annotate(
        count=Count('id'),
        amount=Sum('amount'),
        fees=Sum('fee')
    ).order_by('-amount')
    
    return render(request, 'eservices/revenue_report.html', {
        'stats': stats,
        'by_service': by_service,
    })


# =============================
# Views إضافية للمشغلين
# =============================

@login_required
def operator_edit(request, pk):
    """تعديل مشغل خدمات"""
    operator = get_object_or_404(ServiceOperator, pk=pk)
    
    if request.method == 'POST':
        operator.name = request.POST.get('name', operator.name)
        operator.code = request.POST.get('code', operator.code)
        operator.is_active = request.POST.get('is_active') == 'on'
        operator.commission_rate = Decimal(request.POST.get('commission_rate', 0) or 0)
        operator.save()
        messages.success(request, f'تم تحديث المشغل {operator.name}')
        return redirect('eservices:operator_list')
    
    context = {
        'operator': operator,
        'page_title': f'تعديل المشغل: {operator.name}',
    }
    return render(request, 'eservices/operator_edit.html', context)
