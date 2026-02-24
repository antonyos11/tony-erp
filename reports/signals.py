from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

@receiver(post_migrate)
def ensure_report_permissions(sender, **kwargs):
    if sender.label != 'reports':
        return
    try:
        ct, _ = ContentType.objects.get_or_create(app_label='reports', model='reportsmeta')
        for codename, name in [
            ('view_reports', 'Can view aggregated reports'),
            ('export_reports', 'Can export report data'),
        ]:
            Permission.objects.get_or_create(codename=codename, name=name, content_type=ct)
    except Exception:
        pass
