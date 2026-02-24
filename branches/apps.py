from django.apps import AppConfig


class BranchesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'branches'
    verbose_name = 'إدارة الفروع'
    
    def ready(self):
        """تحميل الإشارات عند بدء التطبيق"""
        try:
            import branches.signals
        except ImportError:
            pass
