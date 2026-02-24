"""
أمر فحص شامل للنظام - يجمع بين الفحوصات الأمنية والتقنية والوظيفية
"""
import os
import sys
import shutil
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'فحص شامل لصحة النظام وأمانه'

    PASS = '✅'
    FAIL = '❌'
    WARN = '⚠️'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='محاولة إصلاح المشاكل التلقائية',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='إخراج النتائج بصيغة JSON',
        )

    def handle(self, *args, **options):
        self.results = []
        self.errors = 0
        self.warnings = 0
        self.passed = 0
        self.auto_fix = options.get('fix', False)
        self.json_output = options.get('json', False)

        self.stdout.write(self.style.HTTP_INFO('\n' + '=' * 60))
        self.stdout.write(self.style.HTTP_INFO('  فحص شامل للنظام - Tony ERP'))
        self.stdout.write(self.style.HTTP_INFO('=' * 60 + '\n'))

        # === الفحوصات ===
        self._check_database()
        self._check_cache()
        self._check_disk_space()
        self._check_migrations()
        self._check_required_dirs()
        self._check_security()
        self._check_environment()
        self._check_installed_apps()
        self._check_backup_files()
        self._check_debug_mode()

        # === التقرير النهائي ===
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            f'  النتائج: {self.PASS} {self.passed} نجح | '
            f'{self.WARN} {self.warnings} تحذير | '
            f'{self.FAIL} {self.errors} خطأ'
        )
        self.stdout.write('=' * 60 + '\n')

        if self.json_output:
            import json
            self.stdout.write(json.dumps(self.results, ensure_ascii=False, indent=2))

        if self.errors > 0:
            sys.exit(1)

    # ------------------------------------------------------------------
    def _record(self, category, name, status, detail=''):
        icon = {0: self.PASS, 1: self.WARN, 2: self.FAIL}[status]
        if status == 0:
            self.passed += 1
        elif status == 1:
            self.warnings += 1
        else:
            self.errors += 1
        self.stdout.write(f'  {icon} [{category}] {name}: {detail}')
        self.results.append({
            'category': category,
            'name': name,
            'status': ['pass', 'warn', 'fail'][status],
            'detail': detail,
        })

    # ------------------------------------------------------------------
    def _check_database(self):
        cat = 'قاعدة البيانات'
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            engine = settings.DATABASES['default']['ENGINE']
            if 'sqlite' in engine:
                self._record(cat, 'المحرك', 1, f'SQLite - لا يناسب الإنتاج ({engine})')
            else:
                self._record(cat, 'المحرك', 0, engine.split('.')[-1])
            self._record(cat, 'الاتصال', 0, 'متصل')
        except Exception as e:
            self._record(cat, 'الاتصال', 2, str(e))

    def _check_cache(self):
        cat = 'ذاكرة التخزين المؤقت'
        try:
            from django.core.cache import cache
            cache.set('_system_check_', 'ok', 10)
            val = cache.get('_system_check_')
            cache.delete('_system_check_')
            if val == 'ok':
                backend = settings.CACHES.get('default', {}).get('BACKEND', '')
                if 'Redis' in backend or 'redis' in backend:
                    self._record(cat, 'Redis', 0, 'يعمل')
                elif 'Memcached' in backend:
                    self._record(cat, 'Memcached', 0, 'يعمل')
                elif 'Locmem' in backend or 'dummy' in backend.lower():
                    self._record(cat, 'Cache', 1, 'LocMem/Dummy - لا يناسب الإنتاج')
                else:
                    self._record(cat, 'Cache', 0, 'يعمل')
            else:
                self._record(cat, 'Cache', 2, 'فشل في القراءة/الكتابة')
        except Exception as e:
            self._record(cat, 'Cache', 1, f'غير متوفر ({e})')

    def _check_disk_space(self):
        cat = 'مساحة القرص'
        usage = shutil.disk_usage('/')
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        pct_used = (usage.used / usage.total) * 100
        if pct_used > 90:
            self._record(cat, 'المساحة', 2, f'{pct_used:.0f}% مستخدم ({free_gb:.1f}GB متاح)')
        elif pct_used > 75:
            self._record(cat, 'المساحة', 1, f'{pct_used:.0f}% مستخدم ({free_gb:.1f}GB متاح)')
        else:
            self._record(cat, 'المساحة', 0, f'{pct_used:.0f}% مستخدم ({free_gb:.1f}GB من {total_gb:.1f}GB)')

    def _check_migrations(self):
        cat = 'الترحيلات'
        try:
            from django.core.management import call_command
            from io import StringIO
            out = StringIO()
            call_command('showmigrations', '--plan', stdout=out)
            output = out.getvalue()
            unapplied = [l for l in output.strip().split('\n') if l.strip().startswith('[ ]')]
            if unapplied:
                self._record(cat, 'معلقة', 1, f'{len(unapplied)} ترحيلة غير مطبقة')
            else:
                self._record(cat, 'الحالة', 0, 'كل الترحيلات مطبقة')
        except Exception as e:
            self._record(cat, 'الحالة', 2, str(e))

    def _check_required_dirs(self):
        cat = 'المجلدات'
        required = {
            'media': getattr(settings, 'MEDIA_ROOT', 'media'),
            'static': getattr(settings, 'STATIC_ROOT', 'staticfiles'),
            'logs': os.path.join(settings.BASE_DIR, 'logs'),
            'backups': os.path.join(settings.BASE_DIR, 'backups'),
        }
        for name, path in required.items():
            if os.path.isdir(path):
                self._record(cat, name, 0, 'موجود')
            else:
                if self.auto_fix:
                    os.makedirs(path, exist_ok=True)
                    self._record(cat, name, 0, 'تم إنشاؤه (--fix)')
                else:
                    self._record(cat, name, 1, 'غير موجود')

    def _check_security(self):
        cat = 'الأمان'
        # SECRET_KEY
        key = getattr(settings, 'SECRET_KEY', '')
        if not key or len(key) < 30:
            self._record(cat, 'SECRET_KEY', 2, 'قصير أو فارغ')
        elif key.startswith('django-insecure'):
            self._record(cat, 'SECRET_KEY', 2, 'يستخدم القيمة الافتراضية غير الآمنة')
        else:
            self._record(cat, 'SECRET_KEY', 0, f'طوله {len(key)} حرف')

        # ALLOWED_HOSTS
        hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        if '*' in hosts:
            self._record(cat, 'ALLOWED_HOSTS', 1, 'يسمح بكل النطاقات (*)')
        elif not hosts:
            self._record(cat, 'ALLOWED_HOSTS', 2, 'فارغ')
        else:
            self._record(cat, 'ALLOWED_HOSTS', 0, f'{len(hosts)} نطاق')

        # CSRF
        middleware = getattr(settings, 'MIDDLEWARE', [])
        if 'django.middleware.csrf.CsrfViewMiddleware' in middleware:
            self._record(cat, 'CSRF', 0, 'مفعّل')
        else:
            self._record(cat, 'CSRF', 2, 'غير مفعّل!')

        # Default passwords check
        try:
            from django.contrib.auth.models import User
            weak = ['admin123', 'password', '123456', 'admin', 'changeme', '12345678']
            for pwd in weak:
                for user in User.objects.filter(is_superuser=True):
                    if user.check_password(pwd):
                        self._record(cat, 'كلمات المرور', 2,
                                     f'المستخدم {user.username} يستخدم كلمة مرور ضعيفة')
                        return
            self._record(cat, 'كلمات المرور', 0, 'لا توجد كلمات مرور ضعيفة مكتشفة')
        except Exception:
            self._record(cat, 'كلمات المرور', 1, 'تعذر الفحص')

    def _check_environment(self):
        cat = 'البيئة'
        env_file = os.path.join(settings.BASE_DIR, '.env')
        if os.path.exists(env_file):
            self._record(cat, '.env', 0, 'موجود')
        else:
            self._record(cat, '.env', 1, 'غير موجود - الإعدادات مدمجة في الكود')

        # Python version
        py_ver = f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'
        if sys.version_info < (3, 10):
            self._record(cat, 'Python', 1, f'{py_ver} - يفضل 3.10+')
        else:
            self._record(cat, 'Python', 0, py_ver)

    def _check_installed_apps(self):
        cat = 'التطبيقات'
        apps = getattr(settings, 'INSTALLED_APPS', [])
        third_party = [a for a in apps if not a.startswith('django.')]
        self._record(cat, 'المثبتة', 0, f'{len(apps)} تطبيق ({len(third_party)} مخصص)')

        # Check for apps without models
        empty_count = 0
        from django.apps import apps as django_apps
        for app_config in django_apps.get_app_configs():
            if app_config.name.startswith('django.'):
                continue
            models = list(app_config.get_models())
            if not models:
                empty_count += 1
        if empty_count > 10:
            self._record(cat, 'فارغة', 1, f'{empty_count} تطبيق بدون موديلات')
        elif empty_count > 0:
            self._record(cat, 'فارغة', 0, f'{empty_count} تطبيق بدون موديلات')

    def _check_backup_files(self):
        cat = 'ملفات النسخ'
        base = settings.BASE_DIR
        backup_patterns = []
        backup_extensions = ('.backup', '.bak', '.old', '.orig', '.dump', '.sql.gz')
        for f in os.listdir(base):
            fpath = os.path.join(base, f)
            if not os.path.isfile(fpath):
                continue
            # ملفات بامتداد نسخ احتياطي
            if any(f.endswith(ext) for ext in backup_extensions):
                backup_patterns.append(f)
            # ملفات sqlite backup
            elif f.startswith('db.sqlite3.backup'):
                backup_patterns.append(f)
        if backup_patterns:
            if self.auto_fix:
                for f in backup_patterns:
                    os.remove(os.path.join(base, f))
                self._record(cat, 'تنظيف', 0, f'تم حذف {len(backup_patterns)} ملف نسخة (--fix)')
            else:
                self._record(cat, 'ملفات', 1,
                             f'{len(backup_patterns)} ملف نسخة في المجلد الرئيسي')
        else:
            self._record(cat, 'نظافة', 0, 'لا توجد ملفات نسخة في المجلد الرئيسي')

    def _check_debug_mode(self):
        cat = 'وضع التصحيح'
        debug = getattr(settings, 'DEBUG', False)
        if debug:
            self._record(cat, 'DEBUG', 1, 'مفعل - يجب تعطيله في الإنتاج')
        else:
            self._record(cat, 'DEBUG', 0, 'معطّل')
