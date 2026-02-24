from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'

    def ready(self):  # noqa: D401
        # استيراد signals لضمان تفعيلها
        from . import signals  # noqa: F401
