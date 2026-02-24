from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import SentNotification, MessageTemplate, NotificationSchedule

@login_required
def dashboard(request):
    """
    لوحة تحكم الإشعارات المتقدمة
    Displays statistics and recent activity for notifications.
    """
    # احصائيات عامة
    total_sent = SentNotification.objects.count()
    total_delivered = SentNotification.objects.filter(status='sent').count()
    total_failed = SentNotification.objects.filter(status='failed').count()
    total_pending = SentNotification.objects.filter(status='pending').count()
    
    # القوالب النشطة
    active_templates = MessageTemplate.objects.filter(is_active=True).count()
    
    # آخر الإشعارات
    recent_notifications = SentNotification.objects.select_related('template', 'recipient').order_by('-created_at')[:10]
    
    context = {
        'title': 'لوحة تحكم الإشعارات',
        'active_tab': 'dashboard',
        'stats': {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_failed': total_failed,
            'total_pending': total_pending,
            'active_templates': active_templates,
        },
        'recent_notifications': recent_notifications,
    }
    return render(request, 'advanced_notifications/dashboard.html', context)
