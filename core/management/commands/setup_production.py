"""
Tony ERP - أمر إعداد وفحص بيئة الإنتاج
يفحص جميع الإعدادات والمكونات ويقدم توصيات

الاستخدام:
    python manage.py setup_production --check
    python manage.py setup_production --fix
    python manage.py setup_production --generate-secret-key
    python manage.py setup_production --generate-env
"""
import os
import sys
import secrets
import string

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'فحص وإعداد النظام لبيئة الإنتاج'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='فحص الإعدادات فقط بدون تعديل',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='محاولة إصلاح المشاكل تلقائياً (إنشاء مجلدات ناقصة)',
        )
        parser.add_argument(
            '--generate-secret-key',
            action='store_true',
            help='توليد SECRET_KEY جديد',
        )
        parser.add_argument(
            '--generate-env',
            action='store_true',
            help='توليد ملف .env من القالب',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('  Tony ERP - Production Setup Check'))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))

        if options['generate_secret_key']:
            self._generate_secret_key()
            return

        if options['generate_env']:
            self._generate_env_file()
            return

        issues = []
        warnings = []
        passed = []

        # ============================================
        # 1. فحص SECRET_KEY
        # ============================================
        self.stdout.write('\n[Security]')
        secret_key = settings.SECRET_KEY
        if 'insecure' in secret_key.lower() or 'change' in secret_key.lower() or len(secret_key) < 40:
            issues.append('SECRET_KEY is insecure')
            self.stdout.write(self.style.ERROR('  [X] SECRET_KEY insecure'))
            self.stdout.write('      Fix: python manage.py setup_production --generate-secret-key')
        else:
            passed.append('SECRET_KEY is secure')
            self.stdout.write(self.style.SUCCESS('  [OK] SECRET_KEY is secure'))

        # ============================================
        # 2. فحص DEBUG
        # ============================================
        if settings.DEBUG:
            settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
            if 'production' in settings_module:
                issues.append('DEBUG=True in production settings')
                self.stdout.write(self.style.ERROR('  [X] DEBUG=True in production!'))
            else:
                warnings.append('DEBUG=True (OK for development)')
                self.stdout.write(self.style.WARNING('  [!] DEBUG=True (OK for development)'))
        else:
            passed.append('DEBUG=False')
            self.stdout.write(self.style.SUCCESS('  [OK] DEBUG=False'))

        # ============================================
        # 3. فحص ALLOWED_HOSTS
        # ============================================
        if not settings.ALLOWED_HOSTS or '*' in settings.ALLOWED_HOSTS:
            if not settings.DEBUG:
                issues.append('ALLOWED_HOSTS not configured')
                self.stdout.write(self.style.ERROR('  [X] ALLOWED_HOSTS not configured'))
            else:
                warnings.append('ALLOWED_HOSTS=* (OK for development)')
                self.stdout.write(self.style.WARNING('  [!] ALLOWED_HOSTS=* (OK for development)'))
        else:
            passed.append(f'ALLOWED_HOSTS configured')
            self.stdout.write(self.style.SUCCESS(f'  [OK] ALLOWED_HOSTS configured'))

        # ============================================
        # 4. فحص قاعدة البيانات
        # ============================================
        self.stdout.write('\n[Database]')
        db_engine = settings.DATABASES['default']['ENGINE']

        if 'sqlite3' in db_engine:
            if not settings.DEBUG:
                issues.append('SQLite in production')
                self.stdout.write(self.style.ERROR('  [X] SQLite - not suitable for production'))
            else:
                warnings.append('SQLite (OK for development)')
                self.stdout.write(self.style.WARNING('  [!] SQLite (OK for development only)'))
        elif 'postgresql' in db_engine:
            passed.append('PostgreSQL')
            self.stdout.write(self.style.SUCCESS('  [OK] PostgreSQL'))
        else:
            engine_name = db_engine.split('.')[-1]
            self.stdout.write(self.style.SUCCESS(f'  [OK] {engine_name}'))
            passed.append(engine_name)

        # فحص الاتصال
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            passed.append('Database connection OK')
            self.stdout.write(self.style.SUCCESS('  [OK] Database connection OK'))
        except Exception as e:
            issues.append(f'Database connection failed: {e}')
            self.stdout.write(self.style.ERROR(f'  [X] Connection failed: {e}'))

        # ============================================
        # 5. فحص الكاش
        # ============================================
        self.stdout.write('\n[Cache]')
        cache_backend = settings.CACHES.get('default', {}).get('BACKEND', '')

        if 'redis' in cache_backend.lower():
            try:
                from django.core.cache import cache
                cache.set('production_check', 'ok', 10)
                if cache.get('production_check') == 'ok':
                    passed.append('Redis Cache OK')
                    self.stdout.write(self.style.SUCCESS('  [OK] Redis Cache working'))
                else:
                    warnings.append('Redis Cache not responding correctly')
                    self.stdout.write(self.style.WARNING('  [!] Redis not responding correctly'))
            except Exception as e:
                issues.append(f'Redis unavailable: {e}')
                self.stdout.write(self.style.ERROR(f'  [X] Redis unavailable: {e}'))
        elif 'locmem' in cache_backend.lower() or 'dummy' in cache_backend.lower():
            if not settings.DEBUG:
                warnings.append('Cache not configured for production')
                self.stdout.write(self.style.WARNING('  [!] Cache not configured for production - use Redis'))
            else:
                self.stdout.write(self.style.WARNING('  [!] LocMem/Dummy Cache (OK for development)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  [OK] {cache_backend.split(".")[-1]}'))

        # ============================================
        # 6. فحص HTTPS (production only)
        # ============================================
        self.stdout.write('\n[HTTPS]')
        if not settings.DEBUG:
            https_checks = {
                'SECURE_SSL_REDIRECT': getattr(settings, 'SECURE_SSL_REDIRECT', False),
                'SESSION_COOKIE_SECURE': getattr(settings, 'SESSION_COOKIE_SECURE', False),
                'CSRF_COOKIE_SECURE': getattr(settings, 'CSRF_COOKIE_SECURE', False),
                'SECURE_HSTS_SECONDS': getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0,
            }
            for check_name, check_value in https_checks.items():
                if check_value:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] {check_name}'))
                    passed.append(check_name)
                else:
                    self.stdout.write(self.style.ERROR(f'  [X] {check_name} not enabled'))
                    issues.append(f'{check_name} not enabled')
        else:
            self.stdout.write(self.style.WARNING('  [!] Skipped HTTPS checks in DEBUG mode'))

        # ============================================
        # 7. فحص Migrations
        # ============================================
        self.stdout.write('\n[Migrations]')
        try:
            from django.core.management import call_command
            from io import StringIO
            out = StringIO()
            call_command('showmigrations', '--plan', stdout=out, no_color=True)
            output = out.getvalue()
            unapplied = [line for line in output.strip().split('\n') if line.strip().startswith('[ ]')]
            if unapplied:
                warnings.append(f'{len(unapplied)} unapplied migrations')
                self.stdout.write(self.style.WARNING(f'  [!] {len(unapplied)} unapplied migrations'))
                for m in unapplied[:5]:
                    self.stdout.write(self.style.WARNING(f'      {m.strip()}'))
                if len(unapplied) > 5:
                    self.stdout.write(self.style.WARNING(f'      ... and {len(unapplied) - 5} more'))
            else:
                passed.append('All migrations applied')
                self.stdout.write(self.style.SUCCESS('  [OK] All migrations applied'))
        except Exception as e:
            warnings.append(f'Migration check error: {e}')
            self.stdout.write(self.style.WARNING(f'  [!] Check error: {e}'))

        # ============================================
        # 8. فحص المجلدات
        # ============================================
        self.stdout.write('\n[Directories]')
        base = settings.BASE_DIR
        required_dirs = {
            'logs': base / 'logs' if hasattr(base, '__truediv__') else os.path.join(str(base), 'logs'),
            'media': settings.MEDIA_ROOT,
            'staticfiles': settings.STATIC_ROOT,
        }
        for name, dir_path in required_dirs.items():
            dir_path_str = str(dir_path)
            if os.path.exists(dir_path_str):
                self.stdout.write(self.style.SUCCESS(f'  [OK] {name}: {dir_path_str}'))
                passed.append(f'{name} directory exists')
            else:
                if options.get('fix'):
                    os.makedirs(dir_path_str, exist_ok=True)
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Created {name}: {dir_path_str}'))
                    passed.append(f'{name} directory created')
                else:
                    warnings.append(f'{name} directory missing')
                    self.stdout.write(self.style.WARNING(f'  [!] Missing {name}: {dir_path_str}'))

        # ============================================
        # الملخص النهائي
        # ============================================
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'  Passed:   {len(passed)}'))
        self.stdout.write(self.style.WARNING(f'  Warnings: {len(warnings)}'))
        self.stdout.write(self.style.ERROR(f'  Issues:   {len(issues)}'))

        if not issues and not warnings:
            self.stdout.write(self.style.SUCCESS('\n  System is ready for production!'))
        elif not issues:
            self.stdout.write(self.style.WARNING('\n  System works but has warnings'))
        else:
            self.stdout.write(self.style.ERROR('\n  System NOT ready for production - fix issues first'))

        self.stdout.write('')

    def _generate_secret_key(self):
        """توليد SECRET_KEY جديد وآمن"""
        chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
        key = ''.join(secrets.choice(chars) for _ in range(64))

        self.stdout.write(self.style.SUCCESS('\nNew SECRET_KEY:'))
        self.stdout.write(self.style.WARNING(f'\n  {key}\n'))
        self.stdout.write('Add to .env:')
        self.stdout.write(self.style.SUCCESS(f'  DJANGO_SECRET_KEY={key}\n'))

    def _generate_env_file(self):
        """توليد ملف .env من القالب"""
        base_dir = settings.BASE_DIR
        env_example = os.path.join(str(base_dir), '.env.example')
        env_file = os.path.join(str(base_dir), '.env')

        if os.path.exists(env_file):
            self.stdout.write(self.style.WARNING('[!] .env already exists!'))
            self.stdout.write('Delete it first or edit manually.')
            return

        if os.path.exists(env_example):
            import shutil
            shutil.copy2(env_example, env_file)
            self.stdout.write(self.style.SUCCESS(f'[OK] Created .env from .env.example'))
            self.stdout.write(self.style.WARNING('[!] Remember to update passwords and SECRET_KEY!'))
        else:
            # توليد ملف .env أساسي
            chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
            secret_key = ''.join(secrets.choice(chars) for _ in range(64))

            content = f"""# Tony ERP - Environment Variables
# Auto-generated - update values before production use!

DJANGO_SECRET_KEY={secret_key}
DEBUG=1
ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1,*

# Database
DB_ENGINE=sqlite

# Redis (optional for development)
REDIS_URL=redis://localhost:6379/1

LANGUAGE_CODE=ar
TIME_ZONE=Africa/Cairo
"""
            with open(env_file, 'w') as f:
                f.write(content)

            self.stdout.write(self.style.SUCCESS(f'[OK] Created .env at: {env_file}'))
            self.stdout.write(self.style.WARNING('[!] Update passwords before production!'))
