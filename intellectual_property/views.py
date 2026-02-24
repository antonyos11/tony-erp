from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Patent, Trademark, CopyrightWork, IPLicense

@login_required
def dashboard(request):
    """لوحة تحكم الملكية الفكرية"""
    
    patents_count = Patent.objects.count()
    trademarks_count = Trademark.objects.count()
    copyrights_count = CopyrightWork.objects.count()
    licenses_count = IPLicense.objects.count()
    
    # العقود المنتهية قريباً
    from django.utils import timezone
    from datetime import timedelta
    soon = timezone.now().date() + timedelta(days=90)
    
    expiring_patents = Patent.objects.filter(expiry_date__lte=soon)
    expiring_trademarks = Trademark.objects.filter(expiry_date__lte=soon)
    
    context = {
        'page_title': 'لوحة تحكم الملكية الفكرية',
        'patents_count': patents_count,
        'trademarks_count': trademarks_count,
        'copyrights_count': copyrights_count,
        'licenses_count': licenses_count,
        'expiring_patents': expiring_patents,
        'expiring_trademarks': expiring_trademarks,
    }
    return render(request, 'intellectual_property/dashboard.html', context)
