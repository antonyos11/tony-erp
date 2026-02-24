from django.apps import AppConfig


class SoundNotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sound_notifications'
    verbose_name = 'الإشعارات الصوتية'
    
    def ready(self):
        import sound_notifications.signals  # noqa
