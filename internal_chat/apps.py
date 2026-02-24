from django.apps import AppConfig


class InternalChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'internal_chat'
    verbose_name = 'الدردشة الداخلية'
    
    def ready(self):
        import internal_chat.signals  # noqa
