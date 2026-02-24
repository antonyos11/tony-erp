"""
Contract Management Views
نظام إدارة العقود - الواجهات الكاملة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Contract


@login_required
def dashboard(request):
    """لوحة تحكم إدارة العقود"""
    
    # الإحصائيات الأساسية
    total_contracts = Contract.objects.count()
    active_contracts = Contract.objects.filter(status='active').count()
    expired_contracts = Contract.objects.filter(status='expired').count()
    
    # القيمة الإجمالية
    total_value = Contract.objects.filter(status='active').aggregate(
        total=Sum('contract_value')
    )['total'] or Decimal('0')
    
    # العقود المنتهية قريباً (30 يوم)
    thirty_days_later = timezone.now().date() + timedelta(days=30)
    expiring_soon = [c for c in Contract.objects.filter(status='active') if c.is_expiring_soon(30)][:10]
    
    # العقود حسب النوع
    contracts_by_type = Contract.objects.values('contract_type').annotate(
        count=Count('id'),
        total_value=Sum('contract_value')
    ).order_by('-count')
    
    # معدل التجديد
    renewal_rate = 0
    
    # أكبر 10 عقود
    top_contracts = Contract.objects.filter(status='active').order_by('-contract_value')[:10]
    
    # العقود الأخيرة
    recent_contracts = Contract.objects.order_by('-created_at')[:10]
    
    context = {
        'page_title': 'لوحة تحكم إدارة العقود',
        'total_contracts': total_contracts,
        'active_contracts': active_contracts,
        'expired_contracts': expired_contracts,
        'total_value': total_value,
        'expiring_soon': expiring_soon,
        'contracts_by_type': contracts_by_type,
        'renewal_rate': round(renewal_rate, 2),
        'top_contracts': top_contracts,
        'recent_contracts': recent_contracts,
    }
    
    return render(request, 'contract_management/dashboard.html', context)


@login_required
def contracts_list(request):
    """قائمة العقود"""
    contracts = Contract.objects.order_by('-start_date')
    
    # الفلاتر
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    search = request.GET.get('search')
    
    if status_filter:
        contracts = contracts.filter(status=status_filter)
    if type_filter:
        contracts = contracts.filter(contract_type=type_filter)
    if search:
        contracts = contracts.filter(
            Q(contract_number__icontains=search) |
            Q(title__icontains=search) |
            Q(party_a__icontains=search) |
            Q(party_b__icontains=search)
        )
    
    context = {
        'page_title': 'العقود',
        'contracts': contracts,
        'status_choices': Contract.STATUS_CHOICES,
        'type_choices': Contract.CONTRACT_TYPE_CHOICES,
    }
    
    return render(request, 'contract_management/contracts_list.html', context)


@login_required
def contract_create(request):
    """إنشاء عقد جديد"""
    if request.method == 'POST':
        try:
            contract = Contract(
                contract_number=request.POST.get('contract_number'),
                contract_type=request.POST.get('contract_type'),
                title=request.POST.get('title'),
                party_a=request.POST.get('party_a'),
                party_b=request.POST.get('party_b'),
                contract_value=request.POST.get('contract_value'),
                currency=request.POST.get('currency', 'EGP'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                status=request.POST.get('status', 'draft'),
                description=request.POST.get('description', ''),
                terms_and_conditions=request.POST.get('terms_and_conditions', ''),
                owner=request.user,
            )
            
            if 'document' in request.FILES:
                contract.document = request.FILES['document']
            if 'attachments' in request.FILES:
                contract.attachments = request.FILES['attachments']
            
            contract.save()
            
            from django.contrib import messages
            messages.success(request, 'تم إنشاء العقد بنجاح')
            return redirect('contract_management:contract_detail', pk=contract.pk)
            
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'عقد جديد',
    }
    return render(request, 'contract_management/contract_form.html', context)


@login_required
def contract_edit(request, pk):
    """تعديل عقد"""
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.method == 'POST':
        try:
            contract.contract_number = request.POST.get('contract_number')
            contract.contract_type = request.POST.get('contract_type')
            contract.title = request.POST.get('title')
            contract.party_a = request.POST.get('party_a')
            contract.party_b = request.POST.get('party_b')
            contract.contract_value = request.POST.get('contract_value')
            contract.currency = request.POST.get('currency', 'EGP')
            contract.start_date = request.POST.get('start_date')
            contract.end_date = request.POST.get('end_date')
            contract.status = request.POST.get('status')
            contract.description = request.POST.get('description', '')
            contract.terms_and_conditions = request.POST.get('terms_and_conditions', '')
            
            if 'document' in request.FILES:
                contract.document = request.FILES['document']
            if 'attachments' in request.FILES:
                contract.attachments = request.FILES['attachments']
            
            contract.save()
            
            from django.contrib import messages
            messages.success(request, 'تم تحديث العقد بنجاح')
            return redirect('contract_management:contract_detail', pk=contract.pk)
            
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'تعديل العقد',
        'contract': contract,
    }
    return render(request, 'contract_management/contract_form.html', context)


@login_required
def contract_delete(request, pk):
    """حذف عقد"""
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.method == 'POST':
        contract.delete()
        from django.contrib import messages
        messages.success(request, 'تم حذف العقد بنجاح')
        return redirect('contract_management:contracts_list')
    
    context = {
        'page_title': 'حذف العقد',
        'contract': contract,
    }
    return render(request, 'contract_management/contract_confirm_delete.html', context)


@login_required
def contract_detail(request, pk):
    """تفاصيل العقد"""
    contract = get_object_or_404(Contract, pk=pk)
    
    # حساب الأيام المتبقية
    if contract.status == 'active':
        days_remaining = (contract.end_date - timezone.now().date()).days
    else:
        days_remaining = None
    
    context = {
        'page_title': f'العقد: {contract.contract_number}',
        'contract': contract,
        'days_remaining': days_remaining,
    }
    
    return render(request, 'contract_management/contract_detail.html', context)


@login_required
def renewal_alerts(request):
    """تنبيهات التجديد"""
    
    # العقود التي تحتاج تجديد (60 يوم)
    needs_renewal = [c for c in Contract.objects.filter(status='active') if c.is_expiring_soon(60)]
    
    context = {
        'page_title': 'تنبيهات التجديد',
        'needs_renewal': needs_renewal,
    }
    
    return render(request, 'contract_management/renewal_alerts.html', context)


from django.db.models.functions import TruncMonth

@login_required
def api_contracts_chart(request):
    """بيانات الرسم البياني للعقود"""
    
    contracts_by_month = Contract.objects.annotate(
        month=TruncMonth('start_date')
    ).values('month').annotate(
        count=Count('id'),
        total_value=Sum('contract_value')
    ).order_by('month')[:12]
    
    data = {
        'months': [item['month'].strftime('%Y-%m') if item['month'] else '' for item in contracts_by_month],
        'counts': [item['count'] for item in contracts_by_month],
        'values': [float(item['total_value'] or 0) for item in contracts_by_month],
    }
    
    return JsonResponse(data)
