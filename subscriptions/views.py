"""
Views for Subscriptions Module
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SubscriptionPlan, CustomerSubscription


@login_required
def plans_list(request):
    """قائمة باقات الاشتراك"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'monthly_price')
    context = {
        'plans': plans,
        'title': 'باقات الاشتراك',
    }
    return render(request, 'subscriptions/plans_list.html', context)


@login_required
def my_subscription(request):
    """اشتراكي الحالي"""
    try:
        subscription = CustomerSubscription.objects.filter(
            customer=request.user
        ).order_by('-start_date').first()
    except:
        subscription = None
    
    context = {
        'subscription': subscription,
        'title': 'اشتراكي الحالي',
    }
    return render(request, 'subscriptions/my_subscription.html', context)


@login_required
def subscriptions_list(request):
    """قائمة الاشتراكات (للإدارة)"""
    if not request.user.is_staff:
        messages.error(request, 'غير مصرح لك بالوصول لهذه الصفحة')
        return redirect('subscriptions:plans_list')
    
    subscriptions = CustomerSubscription.objects.all().order_by('-start_date')
    context = {
        'subscriptions': subscriptions,
        'title': 'إدارة الاشتراكات',
    }
    return render(request, 'subscriptions/subscriptions_list.html', context)
