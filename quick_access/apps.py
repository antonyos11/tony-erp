"""
تطبيق الوصول السريع - لوحة تحكم موحدة لتسهيل العمل
Quick Access - Unified dashboard for streamlined operations
"""
from django.apps import AppConfig


class QuickAccessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quick_access'
    verbose_name = 'الوصول السريع'
    verbose_name_plural = 'الوصول السريع'
