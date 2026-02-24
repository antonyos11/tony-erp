"""
Bank Integration Views
عرض التكامل البنكي
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from .models import BankAccount, BankTransaction


@login_required
def bank_integration_dashboard(request):
    """لوحة تحكم التكامل البنكي"""
    accounts = BankAccount.objects.all()
    total_balance = accounts.aggregate(total=Sum('current_balance'))['total'] or 0
    active_accounts = accounts.filter(status='active').count()
    
    # آخر المعاملات
    recent_transactions = BankTransaction.objects.all().order_by('-transaction_date')[:10]
    
    context = {
        'accounts': accounts,
        'total_balance': total_balance,
        'active_accounts': active_accounts,
        'recent_transactions': recent_transactions,
        'total_accounts': accounts.count(),
    }
    return render(request, 'bank_integration/dashboard.html', context)


@login_required
def account_list(request):
    """قائمة الحسابات البنكية"""
    accounts = BankAccount.objects.all()
    search = request.GET.get('q')
    if search:
        accounts = accounts.filter(
            Q(bank_name__icontains=search) |
            Q(account_number__icontains=search) |
            Q(account_holder__icontains=search)
        )
    
    context = {
        'accounts': accounts,
        'search': search,
    }
    return render(request, 'bank_integration/account_list.html', context)


@login_required
def account_detail(request, pk):
    """تفاصيل حساب بنكي"""
    account = get_object_or_404(BankAccount, pk=pk)
    transactions = account.transactions.all().order_by('-transaction_date')[:50]
    
    context = {
        'account': account,
        'transactions': transactions,
    }
    return render(request, 'bank_integration/account_detail.html', context)


@login_required
def transaction_list(request):
    """قائمة المعاملات البنكية"""
    transactions = BankTransaction.objects.all().order_by('-transaction_date')
    
    # فلترة
    account_id = request.GET.get('account')
    if account_id:
        transactions = transactions.filter(bank_account_id=account_id)
    
    tx_type = request.GET.get('type')
    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)
    
    context = {
        'transactions': transactions[:200],
        'accounts': BankAccount.objects.all(),
    }
    return render(request, 'bank_integration/transaction_list.html', context)
