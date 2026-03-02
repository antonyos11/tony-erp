"""
تطبيق الصلاحيات والهيكل الإداري — RITA ERP
"""
from django.apps import AppConfig


class AuthorizationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authorization'
    verbose_name = 'الصلاحيات والهيكل الإداري'

    def ready(self):
        # تسجيل إشارات الأمان (Login/Logout/BruteForce)
        import apps.authorization.security  # noqa: F401
