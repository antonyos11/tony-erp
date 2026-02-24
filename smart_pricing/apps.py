from django.apps import AppConfig


class SmartPricingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'smart_pricing'
    verbose_name = 'التسعير الذكي بالذكاء الاصطناعي'
    
    def ready(self):
        """تسجيل الـ signals عند تحميل التطبيق"""
        try:
            from . import signals  # noqa
        except ImportError:
            pass
