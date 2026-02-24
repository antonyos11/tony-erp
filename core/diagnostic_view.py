"""
صفحة تشخيص النظام
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


@login_required
def diagnostic_page(request):
    """صفحة تشخيص النظام"""
    context = {
        'now': timezone.now(),
        'user': request.user,
        'BASE_TEMPLATE': 'base_v2.html',
    }
    return render(request, 'diagnostic.html', context)

