import json
import os
import shutil
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
from django.core.management import call_command
from importlib import import_module


class Command(BaseCommand):
    help = "فحص صحي سريع للنظام (DB / Migrations / Media / Static / Cache / Disk / Superuser)"

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='إخراج النتائج بصيغة JSON')
        parser.add_argument('--perf', action='store_true', help='قياس مؤشرات أداء بسيطة (عدد استعلامات/زمن)')

    def handle(self, *args, **options):
        report = {}
        # DB
        try:
            with connection.cursor() as c:
                c.execute('SELECT 1')
                c.fetchone()
            report['database'] = {'ok': True}
        except Exception as e:
            report['database'] = {'ok': False, 'error': str(e)}

        # Pending migrations
        try:
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(targets)
            report['migrations'] = {'ok': len(plan) == 0, 'pending': len(plan)}
        except Exception as e:
            report['migrations'] = {'ok': False, 'error': str(e)}

        # Static & media dirs
        static_root = settings.STATIC_ROOT
        media_root = settings.MEDIA_ROOT
        report['paths'] = {
            'static_root_exists': bool(static_root and static_root.exists()),
            'media_root_exists': bool(media_root and media_root.exists()),
        }

        # Cache
        cache_status = {'configured': 'default' in settings.CACHES}
        try:
            from django.core.cache import caches
            caches['default'].set('__hc__', '1', 5)
            cache_status['ok'] = caches['default'].get('__hc__') == '1'
        except Exception as e:
            cache_status['ok'] = False
            cache_status['error'] = str(e)
        report['cache'] = cache_status

        # Disk usage
        try:
            total, used, free = shutil.disk_usage(str(settings.BASE_DIR))
            usage_pct = round((used / total) * 100, 2)
            report['disk'] = {'ok': usage_pct < 90, 'usage_percent': usage_pct}
        except Exception as e:
            report['disk'] = {'ok': False, 'error': str(e)}

        # Superuser existence
        try:
            from django.contrib.auth import get_user_model
            su_exists = get_user_model().objects.filter(is_superuser=True).exists()
            report['superuser'] = {'ok': su_exists}
            if not su_exists:
                report['superuser']['hint'] = 'إنشاء مستخدم خارق: python manage.py createsuperuser'
        except Exception as e:
            report['superuser'] = {'ok': False, 'error': str(e)}

        # Critical apps presence
        critical_apps = ['inventory', 'sales', 'purchases', 'accounting']
        normalized_installed = set()
        for app_label in settings.INSTALLED_APPS:
            base = app_label.split('.')[0]
            normalized_installed.add(base)
            normalized_installed.add(app_label)
        apps_missing = [a for a in critical_apps if a not in normalized_installed]
        report['critical_apps'] = {'ok': len(apps_missing) == 0, 'missing': apps_missing}

        # Celery (اختبار وسريع اختياري)
        try:
            import_module('celery')
            report['celery'] = {'configured': True}
        except Exception:
            report['celery'] = {'configured': False}

        # Performance metrics (اختياري)
        if options.get('perf'):
            from time import perf_counter
            from django.apps import apps
            perf_info = {}
            model_specs = [
                ('inventory', 'Product'),
                ('partners', 'Customer'),
                ('sales', 'Invoice'),
                ('purchases', 'PurchaseBill'),
                ('accounting', 'JournalEntry'),
            ]
            start_queries = len(getattr(connection, 'queries', [])) if settings.DEBUG else None
            start = perf_counter()
            counts: dict[str, int] = {}
            for app_label, model_name in model_specs:
                try:
                    Model = apps.get_model(app_label, model_name)
                    counts[f"{app_label}.{model_name}"] = Model.objects.count()
                except Exception:
                    continue
            duration = perf_counter() - start
            end_queries = len(getattr(connection, 'queries', [])) if settings.DEBUG else None
            perf_info['duration_ms'] = round(duration * 1000, 2)
            perf_info['model_counts'] = counts
            if start_queries is not None and end_queries is not None:
                perf_info['query_count'] = end_queries - start_queries
                # Threshold check
                try:
                    max_q = int(os.environ.get('PERF_MAX_QUERIES', '0'))
                except ValueError:
                    max_q = 0
                if max_q > 0 and perf_info['query_count'] > max_q:
                    perf_info['query_warning'] = f"query_count {perf_info['query_count']} تجاوز الحد {max_q}"
            else:
                perf_info['query_count'] = 'n/a (DEBUG=False)'
            report['performance'] = perf_info

        if options['json']:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            for key, data in report.items():
                status = 'OK' if data.get('ok', False) else 'FAIL'
                self.stdout.write(f"[{status}] {key}: {data}")

        # Exit non‑zero if something critical failed
        critical_fail = not report['database']['ok'] or not report['migrations']['ok']
        if critical_fail:
            self.exit_code = 1
