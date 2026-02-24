from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'إدارة المستخدمين والصلاحيات'
    
    def ready(self):
        """Import signals when app is ready"""
        import users.signals  # noqa: F401