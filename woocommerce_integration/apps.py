from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WoocommerceIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'woocommerce_integration'
    verbose_name = _('تكامل WooCommerce')

    def ready(self):
        import woocommerce_integration.signals  # noqa
