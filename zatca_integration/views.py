"""
Views for ZATCA Integration Module
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import ZATCAConfiguration, EInvoice


@login_required
def zatca_dashboard(request):
    """لوحة تحكم ZATCA"""
    config = ZATCAConfiguration.objects.first()
    recent_invoices = EInvoice.objects.all().order_by('-created_at')[:10]
    
    context = {
        'config': config,
        'recent_invoices': recent_invoices,
        'title': 'الفوترة الإلكترونية ZATCA',
    }
    return render(request, 'zatca_integration/dashboard.html', context)


@login_required
def invoices_list(request):
    """قائمة الفواتير الإلكترونية"""
    invoices = EInvoice.objects.all().order_by('-invoice_date')
    context = {
        'invoices': invoices,
        'title': 'الفواتير الإلكترونية',
    }
    return render(request, 'zatca_integration/invoices_list.html', context)


@login_required
def zatca_config(request):
    """إعدادات ZATCA"""
    if not request.user.is_staff:
        messages.error(request, 'غير مصرح لك بالوصول لهذه الصفحة')
        return redirect('zatca:dashboard')
    
    config = ZATCAConfiguration.objects.first()
    context = {
        'config': config,
        'title': 'إعدادات ZATCA',
    }
    return render(request, 'zatca_integration/config.html', context)
