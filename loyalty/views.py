from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from .models import LoyaltyProgram, CustomerLoyalty, PointsTransaction, LoyaltyReward
from .forms import LoyaltyProgramForm, LoyaltyRewardForm

@login_required
def dashboard(request):
    """Loyalty dashboard"""
    programs = LoyaltyProgram.objects.filter(is_active=True)
    total_members = CustomerLoyalty.objects.count()
    total_points = CustomerLoyalty.objects.aggregate(total=Sum('current_points'))['total'] or 0
    recent_transactions = PointsTransaction.objects.select_related('loyalty_account__customer').order_by('-created_at')[:20]
    
    context = {
        'programs': programs,
        'total_members': total_members,
        'total_points': total_points,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'loyalty/dashboard.html', context)

@login_required
def program_list(request):
    """List loyalty programs"""
    programs = LoyaltyProgram.objects.all()
    return render(request, 'loyalty/program_list.html', {'programs': programs})

@login_required
@permission_required('loyalty.add_loyaltyprogram')
def program_create(request):
    """Create loyalty program"""
    if request.method == 'POST':
        form = LoyaltyProgramForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء البرنامج بنجاح')
            return redirect('loyalty:program_list')
    else:
        form = LoyaltyProgramForm()
    return render(request, 'loyalty/program_form.html', {'form': form, 'title': 'برنامج ولاء جديد'})

@login_required
def member_list(request):
    """List loyalty members"""
    members = CustomerLoyalty.objects.all().select_related('customer', 'program', 'current_tier')
    return render(request, 'loyalty/member_list.html', {'members': members})

@login_required
def member_detail(request, pk):
    """Member detail with transactions"""
    member = get_object_or_404(CustomerLoyalty.objects.select_related('customer', 'program', 'current_tier'), pk=pk)
    transactions = member.transactions.order_by('-created_at')[:50]
    return render(request, 'loyalty/member_detail.html', {'member': member, 'transactions': transactions})

@login_required
def reward_list(request):
    """List rewards"""
    rewards = LoyaltyReward.objects.filter(is_active=True).select_related('program')
    return render(request, 'loyalty/reward_list.html', {'rewards': rewards})

@login_required
@permission_required('loyalty.add_loyaltyreward')
def reward_create(request):
    """Create reward"""
    if request.method == 'POST':
        form = LoyaltyRewardForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء المكافأة بنجاح')
            return redirect('loyalty:reward_list')
    else:
        form = LoyaltyRewardForm()
    return render(request, 'loyalty/reward_form.html', {'form': form, 'title': 'مكافأة جديدة'})

@login_required
def transaction_list(request):
    """List all transactions"""
    transactions = PointsTransaction.objects.all().select_related('loyalty_account__customer').order_by('-created_at')
    return render(request, 'loyalty/transaction_list.html', {'transactions': transactions})
