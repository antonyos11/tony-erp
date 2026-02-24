from django.apps import AppConfig


class FleetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fleet'
    verbose_name = 'إدارة الأسطول'

    def ready(self):  # pragma: no cover
        from . import signals  # noqa
