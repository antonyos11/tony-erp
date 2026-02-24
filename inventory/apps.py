from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    verbose_name = 'إدارة المخزون'
    
    def ready(self):
        """Import signals when app is ready. Allow disabling via DISABLE_INVENTORY_SIGNALS for tests."""
        import os
        if os.environ.get('DISABLE_INVENTORY_SIGNALS') == '1':
            return
        try:
            import inventory.signals  # noqa: F401
        except Exception:
            pass
