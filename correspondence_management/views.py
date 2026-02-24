from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Correspondence, CorrespondenceThread, CorrespondenceArchive

@login_required
def dashboard(request):
    """لوحة تحكم إدارة المراسلات"""
    
    total_count = Correspondence.objects.count()
    incoming_count = Correspondence.objects.filter(correspondence_type='incoming').count()
    outgoing_count = Correspondence.objects.filter(correspondence_type='outgoing').count()
    
    pending_review = Correspondence.objects.filter(status='received').count()
    urgent_count = Correspondence.objects.filter(priority='urgent').count()
    
    recent_correspondence = Correspondence.objects.all().order_by('-created_at')[:10]
    
    context = {
        'page_title': 'لوحة تحكم إدارة المراسلات',
        'total_count': total_count,
        'incoming_count': incoming_count,
        'outgoing_count': outgoing_count,
        'pending_review': pending_review,
        'urgent_count': urgent_count,
        'recent_correspondence': recent_correspondence,
    }
    return render(request, 'correspondence_management/dashboard.html', context)
