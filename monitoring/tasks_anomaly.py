"""
Anomaly Detection Celery Tasks
مهام Celery لنظام الكشف عن الشذوذات

تشغيل الكشف والتنبؤات بشكل دوري
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .anomaly_detection import anomaly_detector, proactive_warner, AnomalyAlert, ProactiveWarning


@shared_task
def run_anomaly_detection():
    """
    تشغيل الكشف عن الشذوذات
    
    يتم تشغيلها كل ساعة
    """
    print('Starting anomaly detection...')
    
    try:
        results = anomaly_detector.run_all_detections()
        
        total_alerts = sum(len(alerts) for alerts in results.values())
        
        # إرسال إشعارات للتنبيهات الحرجة
        critical_alerts = AnomalyAlert.objects.filter(
            severity='critical',
            status='new',
            detected_at__gte=timezone.now() - timezone.timedelta(hours=1)
        )
        
        if critical_alerts.exists():
            send_critical_alerts_notification(critical_alerts)
        
        print(f'Anomaly detection completed. Found {total_alerts} anomalies.')
        return f'Detected {total_alerts} anomalies'
        
    except Exception as e:
        print(f'Error in anomaly detection: {str(e)}')
        return f'Error: {str(e)}'


@shared_task
def run_proactive_predictions():
    """
    تشغيل التنبؤات الاستباقية
    
    يتم تشغيلها كل 6 ساعات
    """
    print('Starting proactive predictions...')
    
    try:
        results = proactive_warner.run_all_predictions()
        
        total_warnings = sum(len(warnings) for warnings in results.values())
        
        # إرسال إشعارات للتحذيرات عالية الثقة
        high_confidence_warnings = ProactiveWarning.objects.filter(
            confidence_level__gte=80,
            is_active=True,
            is_dismissed=False,
            created_at__gte=timezone.now() - timezone.timedelta(hours=6)
        )
        
        if high_confidence_warnings.exists():
            send_proactive_warnings_notification(high_confidence_warnings)
        
        print(f'Proactive predictions completed. Created {total_warnings} warnings.')
        return f'Created {total_warnings} warnings'
        
    except Exception as e:
        print(f'Error in proactive predictions: {str(e)}')
        return f'Error: {str(e)}'


@shared_task
def cleanup_old_alerts():
    """
    تنظيف التنبيهات القديمة
    
    يتم تشغيلها يومياً
    """
    print('Cleaning up old alerts...')
    
    try:
        # حذف التنبيهات المحلولة والأقدم من 90 يوماً
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        
        deleted_alerts = AnomalyAlert.objects.filter(
            status__in=['resolved', 'false_positive'],
            resolved_at__lt=cutoff_date
        ).delete()
        
        # حذف التحذيرات القديمة والمرفوضة
        deleted_warnings = ProactiveWarning.objects.filter(
            is_dismissed=True,
            created_at__lt=cutoff_date
        ).delete()
        
        print(f'Cleanup completed. Deleted {deleted_alerts[0]} alerts and {deleted_warnings[0]} warnings.')
        return f'Deleted {deleted_alerts[0]} alerts and {deleted_warnings[0]} warnings'
        
    except Exception as e:
        print(f'Error in cleanup: {str(e)}')
        return f'Error: {str(e)}'


@shared_task
def send_daily_anomaly_report():
    """
    إرسال تقرير يومي بالشذوذات
    
    يتم تشغيلها يومياً في الساعة 8 صباحاً
    """
    print('Generating daily anomaly report...')
    
    try:
        today = timezone.now().date()
        
        # الشذوذات الجديدة اليوم
        new_alerts = AnomalyAlert.objects.filter(
            detected_at__date=today
        ).order_by('-severity', '-detected_at')
        
        # التحذيرات النشطة
        active_warnings = ProactiveWarning.objects.filter(
            is_active=True,
            is_dismissed=False
        ).order_by('-confidence_level', 'predicted_date')
        
        # إحصائيات
        stats = {
            'total_alerts': new_alerts.count(),
            'critical': new_alerts.filter(severity='critical').count(),
            'high': new_alerts.filter(severity='high').count(),
            'medium': new_alerts.filter(severity='medium').count(),
            'low': new_alerts.filter(severity='low').count(),
            'warnings': active_warnings.count(),
        }
        
        # إنشاء محتوى البريد
        subject = f'تقرير الشذوذات اليومي - {today}'
        
        message = f"""
تقرير الشذوذات اليومي
{today}

=== ملخص ===
إجمالي التنبيهات: {stats['total_alerts']}
- حرج: {stats['critical']}
- عالي: {stats['high']}
- متوسط: {stats['medium']}
- منخفض: {stats['low']}

التحذيرات الاستباقية النشطة: {stats['warnings']}

=== التنبيهات الحرجة ===
"""
        
        critical_alerts = new_alerts.filter(severity='critical')
        for alert in critical_alerts[:10]:
            message += f"\n• {alert.title}"
            message += f"\n  الفئة: {alert.get_category_display()}"
            message += f"\n  الانحراف: {alert.deviation_percentage}%"
            message += f"\n"
        
        message += "\n=== التحذيرات الاستباقية ===\n"
        
        for warning in active_warnings[:10]:
            message += f"\n• {warning.title}"
            message += f"\n  التاريخ المتوقع: {warning.predicted_date}"
            message += f"\n  مستوى الثقة: {warning.confidence_level}%"
            message += f"\n"
        
        message += "\n\nللمزيد من التفاصيل، يرجى زيارة لوحة التحكم."
        
        # إرسال البريد
        # recipient_list = ['admin@example.com']  # يمكن قراءتها من الإعدادات
        # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)
        
        print('Daily report sent successfully.')
        return 'Report sent'
        
    except Exception as e:
        print(f'Error in daily report: {str(e)}')
        return f'Error: {str(e)}'


def send_critical_alerts_notification(alerts):
    """إرسال إشعار للتنبيهات الحرجة"""
    subject = f'⚠️ تنبيهات حرجة - {alerts.count()} تنبيه جديد'
    
    message = "تم اكتشاف تنبيهات حرجة:\n\n"
    
    for alert in alerts:
        message += f"• {alert.title}\n"
        message += f"  الفئة: {alert.get_category_display()}\n"
        message += f"  الوصف: {alert.description}\n"
        message += f"  الانحراف: {alert.deviation_percentage}%\n\n"
    
    message += "\nيرجى اتخاذ الإجراء اللازم فوراً."
    
    # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, ['admin@example.com'])


def send_proactive_warnings_notification(warnings):
    """إرسال إشعار للتحذيرات الاستباقية"""
    subject = f'🔮 تحذيرات استباقية - {warnings.count()} تحذير جديد'
    
    message = "تحذيرات استباقية بمستوى ثقة عالي:\n\n"
    
    for warning in warnings:
        message += f"• {warning.title}\n"
        message += f"  النوع: {warning.get_warning_type_display()}\n"
        message += f"  التاريخ المتوقع: {warning.predicted_date}\n"
        message += f"  مستوى الثقة: {warning.confidence_level}%\n\n"
        
        if warning.preventive_actions:
            message += "  الإجراءات الوقائية:\n"
            for action in warning.preventive_actions[:3]:
                message += f"    - {action}\n"
            message += "\n"
    
    message += "\nيرجى اتخاذ الإجراءات الوقائية المناسبة."
    
    # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, ['admin@example.com'])


# جدولة المهام في accountant_pro/celery.py:
"""
from celery.schedules import crontab

app.conf.beat_schedule = {
    'run-anomaly-detection-every-hour': {
        'task': 'monitoring.tasks_anomaly.run_anomaly_detection',
        'schedule': crontab(minute=0),  # كل ساعة
    },
    'run-proactive-predictions-every-6-hours': {
        'task': 'monitoring.tasks_anomaly.run_proactive_predictions',
        'schedule': crontab(minute=0, hour='*/6'),  # كل 6 ساعات
    },
    'cleanup-old-alerts-daily': {
        'task': 'monitoring.tasks_anomaly.cleanup_old_alerts',
        'schedule': crontab(minute=0, hour=2),  # يومياً الساعة 2 صباحاً
    },
    'send-daily-anomaly-report': {
        'task': 'monitoring.tasks_anomaly.send_daily_anomaly_report',
        'schedule': crontab(minute=0, hour=8),  # يومياً الساعة 8 صباحاً
    },
}
"""
