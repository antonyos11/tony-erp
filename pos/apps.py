from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pos'
    verbose_name = _('نقاط البيع (POS)')
    
    def ready(self):
        """تحميل signals عند بدء التطبيق"""
        try:
            import pos.signals  # noqa: F401
        except ImportError:
            pass  # signals file doesn't exist yet
