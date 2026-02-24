"""
تكوين تطبيق التكامل البنكي
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BankIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bank_integration'
    verbose_name = _('التكامل البنكي')
    
    def ready(self):
        import bank_integration.signals  # noqa
