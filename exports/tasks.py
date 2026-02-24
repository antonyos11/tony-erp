from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
import csv

# استيراد مهام التنظيف لضمان تسجيلها في Celery
from .tasks_cleanup import cleanup_expired_exports  # noqa: F401
import os
import logging
from pathlib import Path
from .models import DataExport
from inventory.models import Product
from sales.models import Invoice

logger = logging.getLogger(__name__)

EXPORT_TYPE_MAP = {
    'inventory_products': Product,
    'sales_invoices': Invoice,
}

@shared_task
def run_data_export(export_id: int):
    try:
        export = DataExport.objects.get(id=export_id)
    except DataExport.DoesNotExist:
        logger.error("data-export task: object %s missing", export_id)
        return 'missing'

    if export.status not in ('pending', 'processing'):
        return 'skipped'

    export.status = 'processing'
    export.progress = 5
    export.save(update_fields=['status', 'progress'])

    model_cls = EXPORT_TYPE_MAP.get(export.export_type)
    if not model_cls:
        export.mark_failed('unknown export_type')
        return 'failed'

    qs = model_cls.objects.all()
    total = qs.count() or 1
    rows = []
    headers = []
    # Simple heuristic field list (exclude relations heavy fields)
    for f in model_cls._meta.get_fields():
        if getattr(f, 'attname', None) and not f.many_to_many and not f.one_to_many:
            headers.append(f.attname)
    headers = headers[:40]  # cap

    for idx, obj in enumerate(qs.iterator(chunk_size=500)):
        row = []
        for h in headers:
            row.append(getattr(obj, h, ''))
        rows.append(row)
        if idx % 500 == 0:
            export.mark_progress(min(95, int((idx / total) * 90) + 5))

    # Build file
    export_dir = Path(settings.MEDIA_ROOT) / 'exports'
    export_dir.mkdir(parents=True, exist_ok=True)
    filename = f"export_{export.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = export_dir / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    size = file_path.stat().st_size
    export.mark_completed(str(file_path.relative_to(settings.MEDIA_ROOT)), size)
    logger.info("data export %s completed size=%s", export.id, size)
    return 'ok'
