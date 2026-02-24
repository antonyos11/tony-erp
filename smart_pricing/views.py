"""
Views for Smart Pricing Module
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PricingRule, SmartQuote, ProductionLineRecommendation, AutoMaterialRelease


@login_required
def pricing_rules_list(request):
    """قائمة قواعد التسعير"""
    rules = PricingRule.objects.filter(is_active=True).order_by('-created_at')
    context = {
        'rules': rules,
        'title': 'قواعد التسعير الذكي',
    }
    return render(request, 'smart_pricing/rules_list.html', context)


@login_required
def smart_quotes_list(request):
    """قائمة عروض الأسعار الذكية"""
    quotes = SmartQuote.objects.all().order_by('-created_at')
    context = {
        'quotes': quotes,
        'title': 'عروض الأسعار الذكية',
    }
    return render(request, 'smart_pricing/quotes_list.html', context)


@login_required
def material_releases_list(request):
    """قائمة أوامر صرف المواد"""
    releases = AutoMaterialRelease.objects.all().order_by('-created_at')
    context = {
        'releases': releases,
        'title': 'أوامر صرف المواد الآلية',
    }
    return render(request, 'smart_pricing/releases_list.html', context)
