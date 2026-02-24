from django.apps import AppConfig


class ZatcaIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'zatca_integration'
    verbose_name = 'الفوترة الإلكترونية - ZATCA'

    def ready(self):
        import zatca_integration.signals  # noqa: F401
