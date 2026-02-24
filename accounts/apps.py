"""
تكوين تطبيق المصادقة الثنائية (Two-Factor Authentication)
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """تكوين تطبيق accounts"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'المصادقة الثنائية'
    
    def ready(self):
        """استدعاء عند جاهزية التطبيق"""
        # استيراد الإشارات (signals) إن وجدت
        try:
            import accounts.signals  # noqa: F401
        except ImportError:
            pass  # signals file doesn't exist yet
