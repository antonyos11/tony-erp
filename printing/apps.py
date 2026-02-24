from django.apps import AppConfig


class PrintingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'printing'
    verbose_name = 'نظام الطباعة الموحد'

    def ready(self):
        import printing.signals  # noqa: F401
