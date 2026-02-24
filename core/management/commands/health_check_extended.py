"""
فحص صحة النظام الشامل - Extended Health Check
يفحص: قاعدة البيانات، Redis، Celery، المساحة، الذاكرة، Migrations، الأمان

الاستخدام:
    python manage.py health_check_extended
    python manage.py health_check_extended --verbose
    python manage.py health_check_extended --json
    python manage.py health_check_extended --fix
"""
import os
import sys
import json
import time
import shutil
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import connections
from django.core.cache import cache
from django.conf import settings


class Command(BaseCommand):
    help = 'فحص صحة النظام الشامل - Extended Health Check'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            action='store_true',
            help='إخراج النتيجة بصيغة JSON',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل إضافية',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='محاولة إصلاح المشاكل تلقائياً',
        )

    def handle(self, *args, **options):
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {},
        }

        checks = [
            ('database', self.check_database),
            ('redis_cache', self.check_redis),
            ('celery', self.check_celery),
            ('disk_space', self.check_disk_space),
            ('memory', self.check_memory),
            ('migrations', self.check_migrations),
            ('static_files', self.check_static_files),
            ('media_directory', self.check_media),
            ('log_directory', self.check_logs),
            ('secret_key', self.check_secret_key),
            ('debug_mode', self.check_debug_mode),
            ('critical_apps', self.check_critical_apps),
        ]

        for check_name, check_func in checks:
            try:
                result = check_func(options.get('fix', False))
                results['checks'][check_name] = result
                if result['status'] == 'error':
                    results['overall_status'] = 'unhealthy'
                elif result['status'] == 'warning' and results['overall_status'] != 'unhealthy':
                    results['overall_status'] = 'degraded'
            except Exception as e:
                results['checks'][check_name] = {
                    'status': 'error',
                    'message': str(e),
                }
                results['overall_status'] = 'unhealthy'

        if options.get('json'):
            self.stdout.write(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            self._print_report(results, options.get('verbose', False))

        if results['overall_status'] == 'unhealthy':
            sys.exit(1)

    def check_database(self, fix=False):
        """فحص الاتصال بقاعدة البيانات"""
        try:
            start = time.time()
            db_conn = connections['default']
            db_conn.ensure_connection()
            cursor = db_conn.cursor()
            cursor.execute("SELECT 1")
            latency = round((time.time() - start) * 1000, 2)

            engine = settings.DATABASES['default']['ENGINE']
            is_sqlite = 'sqlite' in engine

            result = {
                'status': 'warning' if is_sqlite else 'ok',
                'engine': engine,
                'latency_ms': latency,
            }

            if is_sqlite:
                result['message'] = 'SQLite غير مناسب للإنتاج. استخدم PostgreSQL.'
                result['recommendation'] = 'DB_ENGINE=postgresql في .env'

            return result
        except Exception as e:
            return {'status': 'error', 'message': f'فشل الاتصال: {str(e)}'}

    def check_redis(self, fix=False):
        """فحص اتصال Redis/Cache"""
        try:
            start = time.time()
            cache.set('health_check_test', 'ok', 10)
            value = cache.get('health_check_test')
            latency = round((time.time() - start) * 1000, 2)

            if value == 'ok':
                cache.delete('health_check_test')
                backend = settings.CACHES.get('default', {}).get('BACKEND', '')
                is_redis = 'redis' in backend.lower()
                return {
                    'status': 'ok' if is_redis else 'warning',
                    'backend': backend,
                    'latency_ms': latency,
                    'message': '' if is_redis else 'يُنصح باستخدام Redis في الإنتاج',
                }
            return {'status': 'error', 'message': 'فشل قراءة القيمة من Cache'}
        except Exception as e:
            return {'status': 'warning', 'message': f'Cache غير متاح: {str(e)}'}

    def check_celery(self, fix=False):
        """فحص Celery"""
        try:
            from accountant_pro.celery import app as celery_app
            inspector = celery_app.control.inspect(timeout=3)
            active = inspector.active()
            if active is not None:
                workers = list(active.keys())
                return {
                    'status': 'ok',
                    'workers': len(workers),
                    'worker_names': workers,
                }
            return {
                'status': 'warning',
                'message': 'لا يوجد workers نشطون',
                'recommendation': 'celery -A accountant_pro worker -l INFO',
            }
        except Exception as e:
            return {
                'status': 'warning',
                'message': f'Celery غير متاح: {str(e)}',
                'recommendation': 'تأكد من تشغيل Redis و Celery Worker',
            }

    def check_disk_space(self, fix=False):
        """فحص المساحة المتبقية على القرص"""
        try:
            total, used, free = shutil.disk_usage('/')
            free_gb = free / (1024 ** 3)
            used_percent = (used / total) * 100

            status = 'ok'
            message = ''
            if free_gb < 1:
                status = 'error'
                message = f'مساحة حرة أقل من 1GB! ({free_gb:.1f}GB)'
            elif free_gb < 5:
                status = 'warning'
                message = f'مساحة حرة منخفضة ({free_gb:.1f}GB)'

            return {
                'status': status,
                'total_gb': round(total / (1024 ** 3), 1),
                'used_percent': round(used_percent, 1),
                'free_gb': round(free_gb, 1),
                'message': message,
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_memory(self, fix=False):
        """فحص استخدام الذاكرة"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            status = 'ok'
            message = ''

            if mem.percent > 90:
                status = 'error'
                message = f'استخدام الذاكرة مرتفع جداً: {mem.percent}%'
            elif mem.percent > 75:
                status = 'warning'
                message = f'استخدام الذاكرة مرتفع: {mem.percent}%'

            return {
                'status': status,
                'total_gb': round(mem.total / (1024 ** 3), 1),
                'used_percent': round(mem.percent, 1),
                'available_gb': round(mem.available / (1024 ** 3), 1),
                'message': message,
            }
        except ImportError:
            return {
                'status': 'warning',
                'message': 'psutil غير مثبت. pip install psutil',
            }

    def check_migrations(self, fix=False):
        """فحص المهاجرات المعلقة"""
        try:
            from django.core.management import call_command
            from io import StringIO

            out = StringIO()
            call_command('showmigrations', '--plan', stdout=out)
            output = out.getvalue()

            unapplied = [
                line.strip()
                for line in output.split('\n')
                if line.strip().startswith('[ ]')
            ]

            if unapplied:
                if fix:
                    call_command('migrate', '--noinput')
                    return {
                        'status': 'ok',
                        'message': f'تم تطبيق {len(unapplied)} مهاجرة معلقة',
                        'fixed': True,
                    }
                return {
                    'status': 'warning',
                    'pending_count': len(unapplied),
                    'pending': unapplied[:10],
                    'recommendation': 'python manage.py migrate',
                }

            return {'status': 'ok', 'pending_count': 0}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def check_static_files(self, fix=False):
        """فحص الملفات الثابتة"""
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if not static_root:
            return {'status': 'warning', 'message': 'STATIC_ROOT غير معرّف'}

        if os.path.exists(static_root) and os.listdir(static_root):
            return {'status': 'ok', 'path': str(static_root)}

        if fix:
            from django.core.management import call_command
            call_command('collectstatic', '--noinput')
            return {'status': 'ok', 'message': 'تم جمع الملفات الثابتة', 'fixed': True}

        return {
            'status': 'warning',
            'message': 'الملفات الثابتة غير موجودة أو فارغة',
            'recommendation': 'python manage.py collectstatic',
        }

    def check_media(self, fix=False):
        """فحص مجلد الوسائط"""
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return {'status': 'warning', 'message': 'MEDIA_ROOT غير معرّف'}

        if not os.path.exists(media_root):
            if fix:
                os.makedirs(media_root, exist_ok=True)
                return {'status': 'ok', 'message': 'تم إنشاء مجلد الوسائط', 'fixed': True}
            return {'status': 'warning', 'message': 'مجلد الوسائط غير موجود'}

        if not os.access(media_root, os.W_OK):
            return {'status': 'error', 'message': 'لا توجد صلاحية كتابة على مجلد الوسائط'}

        return {'status': 'ok', 'path': str(media_root)}

    def check_logs(self, fix=False):
        """فحص مجلد السجلات"""
        log_dir = os.path.join(settings.BASE_DIR, 'logs')

        if not os.path.exists(log_dir):
            if fix:
                os.makedirs(log_dir, exist_ok=True)
                return {'status': 'ok', 'message': 'تم إنشاء مجلد السجلات', 'fixed': True}
            return {'status': 'warning', 'message': 'مجلد السجلات غير موجود'}

        total_size = 0
        for f in os.listdir(log_dir):
            fp = os.path.join(log_dir, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)

        size_mb = total_size / (1024 * 1024)

        if size_mb > 500:
            return {
                'status': 'warning',
                'size_mb': round(size_mb, 1),
                'message': f'حجم السجلات كبير ({size_mb:.0f}MB). يُنصح بالتنظيف.',
            }

        return {'status': 'ok', 'size_mb': round(size_mb, 1)}

    def check_secret_key(self, fix=False):
        """فحص SECRET_KEY"""
        from accountant_pro.settings_security import validate_secret_key
        secret_key = getattr(settings, 'SECRET_KEY', '')

        if validate_secret_key(secret_key):
            return {'status': 'ok'}

        return {
            'status': 'error' if not settings.DEBUG else 'warning',
            'message': 'SECRET_KEY غير آمن! قم بتوليد مفتاح جديد.',
            'recommendation': (
                'python -c "from django.core.management.utils import '
                'get_random_secret_key; print(get_random_secret_key())"'
            ),
        }

    def check_debug_mode(self, fix=False):
        """فحص وضع التصحيح"""
        if settings.DEBUG:
            return {
                'status': 'warning',
                'message': 'DEBUG=True. يجب تعطيله في الإنتاج!',
            }
        return {'status': 'ok', 'debug': False}

    def check_critical_apps(self, fix=False):
        """فحص التطبيقات الحرجة"""
        from django.apps import apps

        critical = ['core', 'accounts', 'accounting', 'inventory']
        missing = []

        for app_name in critical:
            try:
                apps.get_app_config(app_name)
            except LookupError:
                missing.append(app_name)

        if missing:
            return {
                'status': 'error',
                'missing_apps': missing,
                'message': f'تطبيقات حرجة مفقودة: {", ".join(missing)}',
            }

        return {'status': 'ok', 'total_apps': len(critical)}

    def _print_report(self, results, verbose=False):
        """طباعة التقرير بشكل مقروء"""
        status_icons = {
            'ok': '✅',
            'warning': '⚠️',
            'error': '❌',
        }

        overall_icon = {
            'healthy': '✅',
            'degraded': '⚠️',
            'unhealthy': '❌',
        }

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  Tony ERP - تقرير صحة النظام الشامل")
        self.stdout.write("=" * 60)
        self.stdout.write(f"\n  التاريخ: {results['timestamp']}")

        icon = overall_icon.get(results['overall_status'], '❓')
        self.stdout.write(f"  الحالة العامة: {icon} {results['overall_status'].upper()}\n")

        for check_name, check_result in results['checks'].items():
            status = check_result.get('status', 'unknown')
            icon = status_icons.get(status, '❓')
            message = check_result.get('message', '')

            line = f"  {icon} {check_name}: {status}"
            if message:
                line += f"\n     └─ {message}"
            self.stdout.write(line)

            if verbose:
                for key, value in check_result.items():
                    if key not in ('status', 'message', 'recommendation'):
                        self.stdout.write(f"     │  {key}: {value}")

            recommendation = check_result.get('recommendation', '')
            if recommendation:
                self.stdout.write(f"     💡 {recommendation}")

        self.stdout.write("\n" + "=" * 60 + "\n")
