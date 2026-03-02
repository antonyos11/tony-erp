"""
تطبيق عروض الأسعار — RITA ERP
"""
from django.apps import AppConfig


class QuotationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.quotations'
    verbose_name = 'عروض الأسعار'
