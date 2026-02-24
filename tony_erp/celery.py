"""
ملف إعدادات Celery للمهام المجدولة
Celery Configuration for Scheduled Tasks
"""

from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tony_erp.settings')

app = Celery('tony_erp')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


# جدولة المهام الدورية
app.conf.beat_schedule = {
    # فحص الطلبات المتأخرة يومياً في الساعة 9 صباحاً
    'check-delayed-orders-daily': {
        'task': 'notifications.enhanced_service.check_delayed_orders',
        'schedule': crontab(hour=9, minute=0),
    },
    
    # فحص المنتجات قليلة المخزون يومياً في الساعة 8 صباحاً
    'check-low-stock-daily': {
        'task': 'notifications.enhanced_service.check_low_stock',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # إرسال ملخص يومي للمدراء في الساعة 6 مساءً
    'send-daily-summary': {
        'task': 'notifications.enhanced_service.send_daily_summary',
        'schedule': crontab(hour=18, minute=0),
    },
    
    # تنظيف الكاش القديم كل 6 ساعات
    'cleanup-old-cache': {
        'task': 'dashboard.cache_optimizer.cleanup_old_cache',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    
    # تحديث مؤشرات الأداء كل ساعة
    'update-kpis': {
        'task': 'dashboard.enhanced_kpis.update_kpis',
        'schedule': crontab(minute=0),
    },
    
    # إرسال تنبيهات المخزون (كل 4 ساعات)
    'stock-alerts': {
        'task': 'inventory.stock_alerts.StockAlertSystem.send_daily_alert_email',
        'schedule': crontab(minute=0, hour='*/4'),
    },
}

# إعدادات Celery الأخرى
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Riyadh',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 دقيقة
)
