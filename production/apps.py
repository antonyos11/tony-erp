from django.apps import AppConfig


class ProductionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'production'
    verbose_name = 'نظام الإنتاج'
    
    def ready(self):
        import production.signals
        import production.signals_pipeline  # noqa: F401