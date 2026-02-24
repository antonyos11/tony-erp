from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Import signals to ensure audit logging is connected (skip during migrations)
        import sys
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            from . import signals  # noqa: F401
        # Ensure custom template tag libraries are imported so Django registers them.
        # Normally Django auto-discovers templatetags/* modules, but if the module
        # was added after the dev server started (or cached early), an explicit
        # import avoids "... is not a registered tag library" errors until restart.
        try:  # pragma: no cover - defensive import
            from .templatetags import billing_extras  # noqa: F401
        except Exception as e:  # pragma: no cover
            import logging
            logging.getLogger(__name__).warning("Could not import billing_extras templatetags: %s", e)
