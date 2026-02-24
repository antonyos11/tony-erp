"""
تطبيق إدارة المخاطر
Risk Management App Config
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RiskManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'risk_management'
    verbose_name = _('إدارة المخاطر والتأمين')
