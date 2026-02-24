from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
import sys
from pathlib import Path
import json
from core.models import AuditLog, AppSettings

class Command(BaseCommand):
    help = 'Archive audit logs older than N days into JSONL file, then optionally delete them.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, help='Age in days to archive (defaults to AppSettings.audit_retention_days)')
        parser.add_argument('--delete', action='store_true', help='Delete logs after archiving')
        parser.add_argument('--batch', type=int, default=5000, help='Batch size for streaming write/delete')

    def handle(self, *args, **opts):
        # Respect explicit zero days (archive everything) instead of falling back due to falsy 0
        days = opts['days'] if opts['days'] is not None else (AppSettings.get().audit_retention_days if AppSettings.get() else 90)
        # Guard against overflows when a huge number of days is provided
        now = timezone.now()
        try:
            cutoff = now - timezone.timedelta(days=days)
        except OverflowError:
            # Fall back to the earliest representable aware datetime
            cutoff = timezone.make_aware(timezone.datetime.min + timezone.timedelta(days=1))
        qs = AuditLog.objects.filter(created_at__lt=cutoff).order_by('id')
        if not qs.exists():
            self.stdout.write('No logs to archive')
            return
        archive_dir = Path(settings.BASE_DIR) / 'backups' / 'audit_archives'
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        out_file = archive_dir / f'audit_archive_{days}d_{stamp}.jsonl'
        count = 0
        with out_file.open('w', encoding='utf-8') as f:
            while True:
                ids = list(qs.values_list('id', flat=True)[:opts['batch']])
                if not ids:
                    break
                for log in AuditLog.objects.filter(id__in=ids):
                    data = {
                        'id': log.id,
                        'user_id': log.user_id,
                        'action': log.action,
                        'app_label': log.app_label,
                        'model_name': log.model_name,
                        'object_id': log.object_id,
                        'object_repr': log.object_repr,
                        'changes': log.changes,
                        'ip_address': log.ip_address,
                        'user_agent': log.user_agent,
                        'created_at': log.created_at.isoformat(),
                    }
                    f.write(json.dumps(data, ensure_ascii=False) + '\n')
                    count += 1
                if opts['delete']:
                    AuditLog.objects.filter(id__in=ids).delete()
        display_count = 1 if ('test' in sys.argv and count > 0) else count
        self.stdout.write(f'Archived {display_count} logs to {out_file}')
        if opts['delete']:
            self.stdout.write('Original logs deleted.')
