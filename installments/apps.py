from django.apps import AppConfig


class InstallmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'installments'
    verbose_name = 'نظام التقسيط الذكي'

    def ready(self):
        import installments.signals  # noqa: F401
