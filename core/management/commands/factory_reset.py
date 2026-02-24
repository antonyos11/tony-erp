from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.apps import apps
import os
import zipfile
from datetime import date


class Command(BaseCommand):
    help = (
        "Factory reset the system: purge operational data while preserving users/auth and migrations.\n"
        "Use with extreme caution."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            type=str,
            help='Must equal exactly: I UNDERSTAND, RESET ALL DATA',
            required=True,
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create a quick ZIP backup of db.sqlite3 and media before reset',
            default=False,
        )

    def handle(self, *args, **options):
        required_phrase = 'I UNDERSTAND, RESET ALL DATA'
        if options['confirm'] != required_phrase:
            raise CommandError(f'Confirmation phrase mismatch. You must pass --confirm "{required_phrase}"')

        backup_path = None
        deleted_counts = []
        try:
            with transaction.atomic():
                # Optional backup
                if options['backup']:
                    backups_dir = os.path.join(os.getcwd(), 'backups')
                    os.makedirs(backups_dir, exist_ok=True)
                    backup_name = f"backup_before_reset_{date.today().isoformat()}.zip"
                    backup_path = os.path.join(backups_dir, backup_name)
                    with zipfile.ZipFile(backup_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        # SQLite database file (best-effort)
                        db_path = os.path.join(os.getcwd(), 'db.sqlite3')
                        if os.path.exists(db_path):
                            zf.write(db_path, arcname='db.sqlite3')
                        # Media directory
                        media_root = getattr(settings, 'MEDIA_ROOT', None) or os.path.join(os.getcwd(), 'media')
                        if os.path.isdir(media_root):
                            for root, _, files in os.walk(media_root):
                                for fname in files:
                                    fpath = os.path.join(root, fname)
                                    arc = os.path.relpath(fpath, media_root)
                                    zf.write(fpath, arcname=f"media/{arc}")

                # Purge data from non-preserved apps/models
                preserve_apps = {'auth', 'admin', 'contenttypes', 'sessions'}
                preserve_models = {('auth', 'User'), ('auth', 'Group'), ('auth', 'Permission')}

                # Try to clear audit logs first (if model exists)
                try:
                    AuditLog = apps.get_model('core', 'AuditLog')
                    AuditLog.objects.all().delete()
                except Exception:
                    pass

                for model in apps.get_models():
                    app_label = model._meta.app_label
                    model_name = model.__name__
                    if app_label in preserve_apps or (app_label, model_name) in preserve_models:
                        continue
                    if app_label == 'migrations' or model_name.lower() == 'migration':
                        continue
                    try:
                        count = model.objects.count()
                        model.objects.all().delete()
                        deleted_counts.append((f"{app_label}.{model_name}", count))
                    except Exception:
                        # Non-critical failures (e.g., PROTECT relations)
                        deleted_counts.append((f"{app_label}.{model_name}", 'skipped'))

                # Recreate core basics
                try:
                    Currency = apps.get_model('core', 'Currency')
                    AppSettings = apps.get_model('core', 'AppSettings')
                    Company = apps.get_model('core', 'Company')
                    if not Currency.objects.exists():
                        Currency.get_default()
                    AppSettings.get()
                    if not Company.objects.exists():
                        Company.objects.create(name='المحاسب الشامل')
                except Exception:
                    pass

        except Exception as e:
            raise CommandError(f'Factory reset failed: {e}')

        # Success summary
        if backup_path:
            self.stdout.write(self.style.SUCCESS(f'Factory reset completed. Backup saved to: {backup_path}'))
        else:
            self.stdout.write(self.style.SUCCESS('Factory reset completed without backup.'))
        # Optional: brief stats
        try:
            total_deleted = sum(c for _, c in deleted_counts if isinstance(c, int))
            self.stdout.write(f'Deleted rows (approx): {total_deleted}')
        except Exception:
            pass
