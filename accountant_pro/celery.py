"""
تكوين Celery لنظام Tony ERP
"""
import os
from celery import Celery
from django.conf import settings

# تعيين إعدادات Django الافتراضية لبرنامج Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

app = Celery('tony_erp')

# استخدام إعدادات Django، والبحث عن إعدادات Celery في CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# تحميل مهام من جميع التطبيقات المسجلة
app.autodiscover_tasks()

# إعدادات إضافية
app.conf.update(
    # استخدام UTC للتوقيتات
    enable_utc=True,
    timezone=settings.TIME_ZONE,
    
    # إعدادات المهام
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # إعدادات الأداء
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # إعدادات أمان
    worker_hijack_root_logger=False,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    
    # إعدادات المراقبة
    task_send_sent_event=True,
    task_track_started=True,
    result_expires=3600,  # ساعة واحدة
)

@app.task(bind=True)
def debug_task(self):
    """مهمة اختبار"""
    print(f'Request: {self.request!r}')