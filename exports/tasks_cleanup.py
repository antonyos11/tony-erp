from celery import shared_task
from django.conf import settings
from django.utils import timezone
from pathlib import Path
import logging
from .models import DataExport

logger = logging.getLogger(__name__)

@shared_task
def cleanup_expired_exports(batch_size: int = 100):
    """حذف ملفات التصدير المنتهية وتحديث السجلات.
    يتم حذف السجلات التي انتهت صلاحيتها قبل أكثر من 7 أيام للحفاظ على التاريخ القريب.
    """
    if not getattr(settings, 'EXPORT_CLEANUP_ENABLED', True):
        return 'disabled'
    now = timezone.now()
    old_cutoff = now - timezone.timedelta(days=7)
    qs = DataExport.objects.filter(expires_at__lt=now).order_by('expires_at')[:batch_size]
    removed_files = 0
    removed_records = 0
    for exp in qs:
        if exp.file_path:
            p = Path(settings.MEDIA_ROOT) / exp.file_path
            try:
                if p.exists():
                    p.unlink()
                    removed_files += 1
            except Exception as e:
                logger.warning("cannot remove export file %s: %s", p, e)
        # remove record if very old OR failed
        if exp.expires_at and exp.expires_at < old_cutoff:
            exp.delete()
            removed_records += 1
        else:
            # keep record but blank file_path to signal removal
            if exp.file_path:
                exp.file_path = ''
                exp.save(update_fields=['file_path'])
    logger.info("cleanup_expired_exports removed_files=%s removed_records=%s", removed_files, removed_records)
    return {'removed_files': removed_files, 'removed_records': removed_records}
