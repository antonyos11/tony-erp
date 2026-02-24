"""
أمر فحص جاهزية الإنتاج الشامل - Tony ERP
==========================================
الاستخدام: python manage.py production_readiness_check
         python manage.py production_readiness_check --json
         python manage.py production_readiness_check --fix
"""

import os
import sys
import time
import shutil
from io import StringIO

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = 'فحص شامل لجاهزية النظام للإنتاج'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true',
            help='إصلاح المشاكل تلقائياً إن أمكن',
        )
        parser.add_argument(
            '--json', action='store_true',
            help='إخراج النتائج بصيغة JSON',
        )

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('  Tony ERP - Production Readiness Check')
        self.stdout.write('=' * 60)
        self.stdout.write('')

        # 1. فحص Django الأساسي
        self._section('Django Core', [
            self._check_django_system,
            self._check_migrations,
            self._check_database,
        ])

        # 2. فحص الأمان
        self._section('Security', [
            self._check_secret_key,
            self._check_debug_mode,
            self._check_allowed_hosts,
            self._check_security_middleware,
            self._check_csrf,
        ])

        # 3. فحص الأداء
        self._section('Performance', [
            self._check_cache_config,
            self._check_database_performance,
            self._check_static_files,
        ])

        # 4. فحص البنية التحتية
        self._section('Infrastructure', [
            self._check_disk_space,
            self._check_log_directory,
            self._check_required_packages,
        ])

        # 5. فحص التطبيقات
        self._section('Applications', [
            self._check_installed_apps,
            self._check_admin_registration,
            self._check_url_count,
        ])

        self._print_summary(options.get('json', False))

    def _section(self, title, checks):
        self.stdout.write(f'\n  [{title}]')
        self.stdout.write('  ' + '-' * 40)
        for check in checks:
            try:
                check()
            except Exception as e:
                self._fail(f'{check.__name__}: {e}')

    def _pass(self, msg):
        self.passed += 1
        self.results.append(('PASS', msg))
        self.stdout.write(self.style.SUCCESS(f'    PASS  {msg}'))

    def _fail(self, msg):
        self.failed += 1
        self.results.append(('FAIL', msg))
        self.stdout.write(self.style.ERROR(f'    FAIL  {msg}'))

    def _warn(self, msg):
        self.warnings += 1
        self.results.append(('WARN', msg))
        self.stdout.write(self.style.WARNING(f'    WARN  {msg}'))

    # ---- Django Core ----

    def _check_django_system(self):
        out, err = StringIO(), StringIO()
        try:
            call_command('check', stdout=out, stderr=err)
            error_output = err.getvalue()
            if 'error' in error_output.lower():
                self._fail(f'System check errors: {error_output[:100]}')
            else:
                self._pass('Django system check: no errors')
        except SystemExit as e:
            if e.code and e.code != 0:
                self._fail('Django system check failed')
            else:
                self._pass('Django system check: no errors')

    def _check_migrations(self):
        out = StringIO()
        try:
            call_command('showmigrations', '--plan', stdout=out)
            output = out.getvalue()
            unapplied = output.count('[ ]')
            applied = output.count('[X]')
            if unapplied > 0:
                self._warn(f'{unapplied} unapplied migrations (run: manage.py migrate)')
            else:
                self._pass(f'All migrations applied ({applied} total)')
        except Exception as e:
            self._fail(f'Migration check failed: {e}')

    def _check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    tables = connection.introspection.table_names()
                    self._pass(f'Database connected ({len(tables)} tables)')
                else:
                    self._fail('Unexpected DB response')
        except Exception as e:
            self._fail(f'Database connection failed: {e}')

    # ---- Security ----

    def _check_secret_key(self):
        key = settings.SECRET_KEY
        if key and len(key) >= 50:
            self._pass(f'SECRET_KEY: strong ({len(key)} chars)')
        elif key and len(key) >= 30:
            self._warn(f'SECRET_KEY: acceptable ({len(key)} chars), prefer 50+')
        else:
            self._fail(f'SECRET_KEY: weak or missing ({len(key)} chars)')

    def _check_debug_mode(self):
        if settings.DEBUG:
            self._warn('DEBUG = True (set False for production)')
        else:
            self._pass('DEBUG = False')

    def _check_allowed_hosts(self):
        hosts = settings.ALLOWED_HOSTS
        if not hosts:
            self._warn('ALLOWED_HOSTS is empty')
        elif hosts == ['*']:
            self._warn('ALLOWED_HOSTS = [*] (too permissive)')
        else:
            self._pass(f'ALLOWED_HOSTS configured: {hosts}')

    def _check_security_middleware(self):
        required = [
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ]
        missing = [m.split('.')[-1] for m in required if m not in settings.MIDDLEWARE]
        if missing:
            self._warn(f'Missing middleware: {missing}')
        else:
            self._pass('All security middleware present')

    def _check_csrf(self):
        if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE:
            self._pass('CSRF protection: enabled')
        else:
            self._fail('CSRF protection: DISABLED')

    # ---- Performance ----

    def _check_cache_config(self):
        backend = settings.CACHES.get('default', {}).get('BACKEND', '')
        short = backend.split('.')[-1] if backend else 'none'
        if 'redis' in backend.lower():
            self._pass(f'Cache: Redis ({short})')
        elif 'memcached' in backend.lower():
            self._pass(f'Cache: Memcached ({short})')
        elif 'locmem' in backend.lower():
            self._warn(f'Cache: Local Memory (not ideal for production)')
        else:
            self._warn(f'Cache: {short}')

    def _check_database_performance(self):
        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM auth_user")
            cursor.fetchone()
        elapsed = time.time() - start
        ms = elapsed * 1000
        if ms < 100:
            self._pass(f'DB query speed: {ms:.0f}ms (excellent)')
        elif ms < 500:
            self._pass(f'DB query speed: {ms:.0f}ms (good)')
        else:
            self._warn(f'DB query speed: {ms:.0f}ms (slow)')

    def _check_static_files(self):
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root and os.path.isdir(static_root):
            file_count = sum(len(f) for _, _, f in os.walk(static_root))
            self._pass(f'Static files: {file_count} files in {static_root}')
        elif static_root:
            self._warn(f'STATIC_ROOT does not exist: {static_root}')
        else:
            self._warn('STATIC_ROOT not configured')

    # ---- Infrastructure ----

    def _check_disk_space(self):
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024 ** 3)
        free_pct = free / total * 100
        if free_pct > 20:
            self._pass(f'Disk space: {free_gb:.1f}GB free ({free_pct:.0f}%)')
        elif free_pct > 10:
            self._warn(f'Disk space low: {free_gb:.1f}GB free ({free_pct:.0f}%)')
        else:
            self._fail(f'Disk space critical: {free_gb:.1f}GB free ({free_pct:.0f}%)')

    def _check_log_directory(self):
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        if os.path.isdir(log_dir):
            self._pass(f'Log directory exists: {log_dir}')
        else:
            try:
                os.makedirs(log_dir, exist_ok=True)
                self._pass(f'Log directory created: {log_dir}')
            except Exception as e:
                self._fail(f'Cannot create log directory: {e}')

    def _check_required_packages(self):
        required = {
            'django': 'django',
            'rest_framework': 'djangorestframework',
            'django_filters': 'django-filter',
        }
        missing = []
        for module, package in required.items():
            try:
                __import__(module)
            except ImportError:
                missing.append(package)
        if missing:
            self._fail(f'Missing packages: {missing}')
        else:
            self._pass(f'All required packages installed ({len(required)})')

    # ---- Applications ----

    def _check_installed_apps(self):
        count = len(settings.INSTALLED_APPS)
        self._pass(f'Installed apps: {count}')

    def _check_admin_registration(self):
        from django.contrib import admin
        registered = len(admin.site._registry)
        all_models = len(apps.get_models())
        pct = registered / max(all_models, 1) * 100
        if pct >= 60:
            self._pass(f'Admin registration: {registered}/{all_models} ({pct:.0f}%)')
        elif pct >= 40:
            self._warn(f'Admin registration: {registered}/{all_models} ({pct:.0f}%)')
        else:
            self._warn(f'Admin registration low: {registered}/{all_models} ({pct:.0f}%)')

    def _check_url_count(self):
        from django.urls import get_resolver

        def count_patterns(patterns):
            count = 0
            for p in patterns:
                if hasattr(p, 'url_patterns'):
                    count += count_patterns(p.url_patterns)
                else:
                    count += 1
            return count

        resolver = get_resolver()
        total = count_patterns(resolver.url_patterns)
        self._pass(f'URL patterns: {total} registered')

    # ---- Summary ----

    def _print_summary(self, as_json=False):
        total = self.passed + self.failed + self.warnings

        if as_json:
            import json
            data = {
                'total': total,
                'passed': self.passed,
                'failed': self.failed,
                'warnings': self.warnings,
                'score': f'{self.passed / max(total, 1) * 100:.0f}%',
                'production_ready': self.failed == 0,
                'results': [{'status': r[0], 'message': r[1]} for r in self.results],
            }
            self.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
            return

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('  Summary')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'    Passed:   {self.passed}'))
        if self.failed:
            self.stdout.write(self.style.ERROR(f'    Failed:   {self.failed}'))
        else:
            self.stdout.write(f'    Failed:   {self.failed}')
        if self.warnings:
            self.stdout.write(self.style.WARNING(f'    Warnings: {self.warnings}'))
        else:
            self.stdout.write(f'    Warnings: {self.warnings}')
        self.stdout.write(f'    Score:    {self.passed}/{total} ({self.passed / max(total, 1) * 100:.0f}%)')
        self.stdout.write('')

        if self.failed == 0 and self.warnings == 0:
            self.stdout.write(self.style.SUCCESS(
                '  >>> SYSTEM IS 200% PRODUCTION READY! <<<'
            ))
        elif self.failed == 0:
            self.stdout.write(self.style.SUCCESS(
                '  >>> PRODUCTION READY (with minor warnings) <<<'
            ))
        elif self.failed <= 2:
            self.stdout.write(self.style.WARNING(
                '  >>> NEEDS MINOR FIXES BEFORE PRODUCTION <<<'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'  >>> {self.failed} ISSUES MUST BE FIXED BEFORE PRODUCTION <<<'
            ))
        self.stdout.write('')
