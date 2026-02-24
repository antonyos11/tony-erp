"""
Tony ERP - فحص وإصلاح مشاكل الإنتاج

Usage:
    python3 manage.py fix_production --check       # فحص فقط
    python3 manage.py fix_production --fix          # إصلاح تلقائي
    python3 manage.py fix_production --fix -v 2     # إصلاح مفصل
"""
import os
import socket

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'فحص وإصلاح مشاكل الإنتاج - Production Fix & Check'

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true', help='فحص فقط')
        parser.add_argument('--fix', action='store_true', help='إصلاح تلقائي')

    def handle(self, *args, **options):
        do_fix = options.get('fix', False)
        verbosity = options.get('verbosity', 1)

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('  Tony ERP - Production Check'))
        self.stdout.write(f'  Server: {self._get_ip()}')
        self.stdout.write('=' * 60 + '\n')

        issues = []
        fixed = []

        # 1. HTTPS
        self._section('HTTPS')
        ssl_redirect = getattr(settings, 'SECURE_SSL_REDIRECT', False)
        cookie_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        if ssl_redirect or cookie_secure:
            self._ok('HTTPS settings configured')
        else:
            issues.append('HTTPS not configured')
            self._fail('HTTPS not configured - set SECURE_SSL_REDIRECT=True')
            self._hint('Generate SSL: sudo openssl req -x509 -nodes -days 365 '
                       '-newkey rsa:2048 -keyout /etc/ssl/private/tony_erp.key '
                       '-out /etc/ssl/certs/tony_erp.crt -subj "/CN=72.62.176.249"')

        # 2. DEBUG
        self._section('Settings')
        if settings.DEBUG:
            issues.append('DEBUG=True')
            self._fail('DEBUG=True in production!')
            self._hint('Set DEBUG=False in .env')
        else:
            self._ok('DEBUG=False')

        # 3. SECRET_KEY
        key = settings.SECRET_KEY
        if 'insecure' in key.lower() or len(key) < 40:
            issues.append('SECRET_KEY weak')
            self._fail('SECRET_KEY is weak or default')
            self._hint('python3 -c "from django.core.management.utils import '
                       'get_random_secret_key; print(get_random_secret_key())"')
        else:
            self._ok(f'SECRET_KEY strong ({len(key)} chars)')

        # 4. ALLOWED_HOSTS
        hosts = settings.ALLOWED_HOSTS
        if '*' in hosts:
            issues.append('ALLOWED_HOSTS=*')
            self._warn(f'ALLOWED_HOSTS contains * — restrict in production')
        elif hosts:
            self._ok(f'ALLOWED_HOSTS: {", ".join(hosts)}')
        else:
            issues.append('ALLOWED_HOSTS empty')
            self._fail('ALLOWED_HOSTS is empty')

        # 5. Database
        self._section('Database')
        engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        engine_short = engine.split('.')[-1]
        if 'sqlite3' in engine:
            issues.append('SQLite in production')
            self._warn(f'Using {engine_short} — recommend PostgreSQL')
        else:
            self._ok(f'Engine: {engine_short}')

        try:
            with connection.cursor() as c:
                c.execute("SELECT 1")
            self._ok('Database connection: OK')
        except Exception as e:
            issues.append(f'DB error: {e}')
            self._fail(f'Database connection failed: {e}')

        # 6. Directories
        self._section('Directories')
        base = settings.BASE_DIR
        for d in ['logs', 'media', 'staticfiles', 'backups']:
            p = os.path.join(base, d)
            if os.path.exists(p):
                self._ok(f'{d}/')
            elif do_fix:
                os.makedirs(p, exist_ok=True)
                fixed.append(f'Created {d}/')
                self._ok(f'{d}/ (created)')
            else:
                issues.append(f'{d}/ missing')
                self._fail(f'{d}/ does not exist')

        # 7. Migrations
        self._section('Migrations')
        try:
            from django.core.management import call_command
            from io import StringIO
            out = StringIO()
            call_command('showmigrations', '--plan', stdout=out)
            lines = out.getvalue().strip().split('\n')
            pending = [l for l in lines if l.strip().startswith('[ ]')]
            if pending:
                if do_fix:
                    self.stdout.write('  Applying migrations...')
                    call_command('migrate', '--noinput')
                    fixed.append(f'Applied {len(pending)} migrations')
                    self._ok('Migrations applied')
                else:
                    issues.append(f'{len(pending)} pending migrations')
                    self._warn(f'{len(pending)} pending — run: python3 manage.py migrate')
            else:
                self._ok('All migrations applied')
        except Exception as e:
            self._fail(f'Migration check failed: {e}')

        # 8. Static Files
        self._section('Static Files')
        static_dir = os.path.join(base, 'staticfiles')
        if os.path.exists(static_dir) and os.listdir(static_dir):
            count = sum(len(f) for _, _, f in os.walk(static_dir))
            self._ok(f'{count} static files')
        elif do_fix:
            from django.core.management import call_command
            self.stdout.write('  Collecting static files...')
            call_command('collectstatic', '--noinput', verbosity=0)
            fixed.append('Collected static files')
            self._ok('Static files collected')
        else:
            issues.append('Static files not collected')
            self._warn('Run: python3 manage.py collectstatic')

        # 9. Redis
        self._section('Redis')
        cache_backend = settings.CACHES.get('default', {}).get('BACKEND', '')
        if 'redis' in cache_backend.lower():
            try:
                from django.core.cache import cache
                cache.set('_fix_check_', 'ok', 30)
                if cache.get('_fix_check_') == 'ok':
                    self._ok('Redis cache working')
                else:
                    self._warn('Redis cache read failed')
            except Exception as e:
                issues.append(f'Redis error: {e}')
                self._fail(f'Redis: {e}')
        else:
            self._warn(f'Cache: {cache_backend.split(".")[-1]} (Redis recommended)')

        # 10. Health Endpoints
        self._section('Health Endpoints')
        try:
            from django.test import RequestFactory
            factory = RequestFactory()
            from core.health_views import health_live
            req = factory.get('/health/live/')
            resp = health_live(req)
            self._ok(f'/health/live/ -> {resp.status_code}')
        except Exception as e:
            self._warn(f'Health endpoint: {e}')

        # 11. Heartbeat
        try:
            from django.test import RequestFactory
            factory = RequestFactory()
            from core.fixes.heartbeat import heartbeat
            req = factory.get('/heartbeat/')
            resp = heartbeat(req)
            self._ok(f'/heartbeat/ -> {resp.status_code}')
        except Exception as e:
            self._warn(f'Heartbeat: {e}')

        # Summary
        self.stdout.write('\n' + '=' * 60)
        if fixed:
            self.stdout.write(self.style.SUCCESS(
                f'  Fixed: {len(fixed)} issues'))
            for f in fixed:
                self.stdout.write(self.style.SUCCESS(f'    + {f}'))

        if issues:
            self.stdout.write(self.style.ERROR(
                f'  Remaining: {len(issues)} issues'))
            for i in issues:
                self.stdout.write(self.style.ERROR(f'    - {i}'))
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n  System is production-ready!\n'))

        self.stdout.write('=' * 60 + '\n')

    def _section(self, name):
        self.stdout.write(f'\n{name}:')

    def _ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  [OK] {msg}'))

    def _fail(self, msg):
        self.stdout.write(self.style.ERROR(f'  [FAIL] {msg}'))

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(f'  [WARN] {msg}'))

    def _hint(self, msg):
        self.stdout.write(f'        -> {msg}')

    def _get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return 'unknown'
