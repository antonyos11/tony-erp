from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class TaxSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tax_system'
    verbose_name = _('نظام الضرائب')
