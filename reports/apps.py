from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'

    def ready(self):
        # Register signals only (avoid DB queries here)
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
