# branches/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BranchesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'branches'
    verbose_name = _('إدارة الفروع والمعارض')
    
    def ready(self):
        """
        تهيئة الوحدة عند بدء التشغيل
        """
        # استيراد الإشارات إن وجدت
        try:
            from . import signals  # noqa
        except ImportError:
            pass
