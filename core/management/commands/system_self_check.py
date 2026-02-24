"""
أمر فحص النظام الذاتي وإصلاح المشاكل
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections, connection
from django.conf import settings
from django.contrib.auth.models import User
import os
import sys
import subprocess
import importlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'فحص شامل للنظام مع إصلاح المشاكل تلقائياً'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='إصلاح المشاكل تلقائياً',
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='تشغيل صامت',
        )

    def handle(self, *args, **options):
        self.fix_mode = options.get('fix', False)
        self.quiet = options.get('quiet', False)
        self.issues_found = []
        self.fixes_applied = []
        
    # ملاحظة: استخدم self.safe_write في كل المخرجات لتجنب UnicodeEncodeError
        
        if not self.quiet:
            header = ("\n" + "="*80 + "\n" + "Tony ERP - SYSTEM SELF CHECK\n" + "="*80 + "\n")
            self.safe_write(header, style=self.style.SUCCESS)
        
        # تشغيل جميع فحوصات النظام
        checks = [
            self.check_python_version,
            self.check_django_setup,
            self.check_database,
            self.check_migrations,
            self.check_duplicate_migration_numbers,
            self.check_templates,
            self.check_redis,
            self.check_static_files,
            self.check_media_directories,
            self.check_log_directories,
            self.check_environment_file,
            self.check_superuser,
            self.check_celery,
            self.check_disk_space,
            self.check_dependencies,
        ]
        
        total_checks = len(checks)
        passed_checks = 0
        
        for i, check_func in enumerate(checks, 1):
            check_name = check_func.__name__.replace('check_', '').replace('_', ' ').title()
            if not self.quiet:
                progress_msg = f"[{i}/{total_checks}] CHECK {check_name}..."
                self.safe_write(progress_msg, ending='')
            
            try:
                result = check_func()
                if result:
                    passed_checks += 1
                    if not self.quiet:
                        self.safe_write(" OK", style=self.style.SUCCESS, ending='\n')
                else:
                    if not self.quiet:
                        self.safe_write(" WARN", style=self.style.WARNING, ending='\n')
            except Exception as e:
                if not self.quiet:
                    self.safe_write(f" ERROR {str(e)}", style=self.style.ERROR)
                self.issues_found.append(f"خطأ في فحص {check_name}: {str(e)}")
        
        # عرض النتائج
        self.show_results(passed_checks, total_checks)
        
        # إنهاء الأمر
        if self.issues_found and not self.fix_mode:
            if not self.quiet:
                self.safe_write(
                    "\nTIP: شغل الأمر بالوسيط --fix لإصلاح المشاكل: python manage.py system_self_check --fix\n",
                    style=self.style.WARNING
                )
            sys.exit(1)
        
        if not self.quiet:
            if self.fixes_applied:
                msg = f"\nFIXED {len(self.fixes_applied)} ISSUE(S)\n"
                self.safe_write(msg, style=self.style.SUCCESS)
            else:
                msg = "\nSYSTEM HEALTHY AND READY\n"
                self.safe_write(msg, style=self.style.SUCCESS)

    def check_python_version(self):
        """فحص إصدار Python"""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 11:
            return True
        else:
            self.issues_found.append(f"إصدار Python قديم: {version.major}.{version.minor}, يحتاج 3.11+")
            return False

    def check_django_setup(self):
        """فحص إعدادات Django"""
        try:
            from django.conf import settings
            settings.SECRET_KEY
            return True
        except Exception as e:
            self.issues_found.append(f"مشكلة في إعدادات Django: {str(e)}")
            return False

    def check_database(self):
        """فحص الاتصال بقاعدة البيانات"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception as e:
            self.issues_found.append(f"مشكلة في قاعدة البيانات: {str(e)}")
            if self.fix_mode:
                try:
                    call_command('migrate', verbosity=0)
                    self.fixes_applied.append("تم تطبيق المهاجرات")
                    return True
                except:
                    pass
            return False

    def check_migrations(self):
        """فحص حالة المهاجرات"""
        try:
            # التحقق من وجود مهاجرات معلقة (نفرض UTF-8 لتجنب أخطاء cp1252 في Windows)
            result = subprocess.run([
                sys.executable, 'manage.py', 'showmigrations', '--plan'
            ], capture_output=True, text=True, cwd=settings.BASE_DIR, encoding='utf-8', errors='replace')
            # في مخرجات showmigrations --plan، وجود [ ] يعني مهاجرة غير مطبقة
            stdout = result.stdout or ""
            has_pending = "[ ]" in stdout

            if has_pending:
                if self.fix_mode:
                    try:
                        call_command('makemigrations', verbosity=0)
                        call_command('migrate', verbosity=0)
                        self.fixes_applied.append("تم إنشاء وتطبيق المهاجرات")
                        # بعد الإصلاح نعتبر الفحص ناجحاً
                        return True
                    except Exception as e:
                        self.issues_found.append(f"لا يمكن إصلاح المهاجرات: {str(e)}")
                        return False
                else:
                    self.issues_found.append("يوجد مهاجرات معلقة")
                    return False

            # لا توجد مهاجرات معلقة
            return True
        except Exception as e:
            self.issues_found.append(f"خطأ في فحص المهاجرات: {str(e)}")
            return False

    # ------------------------------------------------------------------
    # فحص ازدواج أرقام المهاجرات داخل كل تطبيق (مثل وجود ملفين 0002_*)
    # ------------------------------------------------------------------
    def check_duplicate_migration_numbers(self):
        """التأكد من عدم وجود أرقام مكررة في ملفات المهاجرات لكل تطبيق.

        لا نحاول الإصلاح تلقائياً (خطير بعد تطبيقها) لكن نُظهر تحذيراً واضحاً.
        """
        from django.conf import settings
        from collections import defaultdict
        import re

        pattern = re.compile(r'^(?P<num>\d{4})_.*\.py$')
        base_dir = settings.BASE_DIR
        duplicates = []
        for app in settings.INSTALLED_APPS:
            if app.startswith('django.'):
                continue
            try:
                module = __import__(app)
                app_path = Path(module.__file__).parent
                mig_dir = app_path / 'migrations'
                if not mig_dir.exists():
                    continue
                per_number = defaultdict(list)
                all_migs = []  # (num, filename)
                for f in mig_dir.iterdir():
                    if f.name == '__init__.py' or not f.name.endswith('.py'):
                        continue
                    m = pattern.match(f.name)
                    if m:
                        num = m.group('num')
                        per_number[num].append(f.name)
                        all_migs.append((num, f.name))
                # Detect merges by importing migration modules and checking dependencies
                merges_after = set()
                try:
                    import importlib
                    for num_str, fname in all_migs:
                        try:
                            mod = importlib.import_module(f"{app}.migrations.{fname[:-3]}")
                            deps = getattr(mod.Migration, 'dependencies', [])
                            same_app_deps = [d for d in deps if isinstance(d, tuple) and len(d) >= 2 and d[0] == app]
                            if len(same_app_deps) >= 2:
                                merges_after.add(num_str)
                        except Exception:
                            continue
                except Exception:
                    pass
                for num, files in per_number.items():
                    if len(files) > 1:
                        # Ignore if a later migration in this app merges branches (multiple same-app deps)
                        later_merge_exists = any(int(mn) >= int(num) for mn in merges_after)
                        if later_merge_exists:
                            continue
                        duplicates.append((app, num, files))
            except Exception:
                continue

        if duplicates:
            for app, num, files in duplicates:
                self.issues_found.append(
                    f"ازدواج رقم مهاجرة في تطبيق {app}: الرقم {num} له الملفات {', '.join(files)}"
                )
            # اقتراح إصلاح (غير تلقائي)
            if self.fix_mode and not self.quiet:
                self.stdout.write(self.style.WARNING(
                    "تحذير: لا يمكن إعادة ترقيم المهاجرات تلقائياً بأمان. أنشئ مهاجرة تعويضية أو أعد الترقيم يدوياً بعد أخذ نسخة احتياطية.") )
            return False
        return True

    # ------------------------------------------------------------------
    # فحص قوالب Django لاكتشاف أخطاء بناء (TemplateSyntaxError) و علامات دمج
    # ------------------------------------------------------------------
    def check_templates(self):
        """تحليل ملفات القوالب .html للتأكد من عدم وجود أخطاء بناء أو بقايا دمج."""
        from django.conf import settings
        from django.template import TemplateSyntaxError
        from django.template.loader import get_template
        import re

        templates_dir = Path(settings.BASE_DIR) / 'templates'
        if not templates_dir.exists():
            return True  # لا توجد قوالب

        # نتحقق من علامات تعارض Git الحقيقية فقط،
        # وليس أي سطر يحتوي على "=======" (لتجنب الإبلاغ الخاطئ عن خطوط الزخرفة).
        conflict_re = re.compile(r'^(<<<<<<<\s|=======$|>>>>>>>)')
        errors = []
        conflict_hits = []
        max_files = 800  # حماية من المشاريع الضخمة جداً
        scanned = 0
        for path in templates_dir.rglob('*.html'):
            scanned += 1
            if scanned > max_files:
                break
            rel = path.relative_to(templates_dir)
            # فحص علامات الدمج
            try:
                with path.open('r', encoding='utf-8', errors='ignore') as fh:
                    for i, line in enumerate(fh, 1):
                        if conflict_re.match(line.strip()):
                            conflict_hits.append(f"{rel} (سطر {i})")
                            break
            except Exception:
                continue
            # محاولة تحميل القالب عبر loader (قد يرمي TemplateSyntaxError)
            try:
                # استخدام الاسم النسبي داخل مجلد templates
                get_template(str(rel))
            except TemplateSyntaxError as e:
                errors.append(f"{rel}: {e}")
            except Exception:
                # أخطاء أخرى (مثل include مفقود) نسجلها كتحذير
                errors.append(f"{rel}: مشكلة تحميل (ربما include مفقود)")

        if conflict_hits:
            self.issues_found.append(
                f"بقايا تعارض دمج في القوالب: {', '.join(conflict_hits[:5])}{' ...' if len(conflict_hits) > 5 else ''}" )
        if errors:
            self.issues_found.append(
                f"أخطاء قوالب: {len(errors)} ملف مع خطأ (أول 3): {', '.join(errors[:3])}" )
            return False
        return True

    def check_redis(self):
        """فحص اتصال Redis (اختياري)"""
        try:
            import redis
            redis_url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1')
            client = redis.from_url(redis_url)
            client.ping()
            return True
        except ImportError:
            # Redis غير مثبت، هذا مقبول
            return True
        except Exception:
            # Redis غير متاح، لكن هذا ليس خطأ فادح
            if not self.quiet:
                self.stdout.write(self.style.WARNING(" (Redis غير متاح)"), ending='')
            return True

    def check_static_files(self):
        """فحص الملفات الثابتة"""
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root and not os.path.exists(static_root):
            if self.fix_mode:
                try:
                    call_command('collectstatic', verbosity=0, interactive=False)
                    self.fixes_applied.append("تم جمع الملفات الثابتة")
                    return True
                except Exception as e:
                    self.issues_found.append(f"لا يمكن جمع الملفات الثابتة: {str(e)}")
                    return False
            else:
                self.issues_found.append("الملفات الثابتة غير محدثة")
                return False
        return True

    def check_media_directories(self):
        """فحص مجلدات الوسائط"""
        required_dirs = [
            settings.MEDIA_ROOT,
            os.path.join(settings.BASE_DIR, 'logs'),
            os.path.join(settings.BASE_DIR, 'backups'),
        ]
        
        missing_dirs = []
        for directory in required_dirs:
            if not os.path.exists(directory):
                missing_dirs.append(directory)
        
        if missing_dirs:
            if self.fix_mode:
                for directory in missing_dirs:
                    os.makedirs(directory, exist_ok=True)
                self.fixes_applied.append(f"تم إنشاء {len(missing_dirs)} مجلد مفقود")
                return True
            else:
                self.issues_found.append(f"مجلدات مفقودة: {', '.join(missing_dirs)}")
                return False
        return True

    def check_log_directories(self):
        """فحص مجلدات السجلات"""
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        if not os.path.exists(logs_dir):
            if self.fix_mode:
                os.makedirs(logs_dir, exist_ok=True)
                self.fixes_applied.append("تم إنشاء مجلد السجلات")
                return True
            else:
                self.issues_found.append("مجلد السجلات مفقود")
                return False
        return True

    def check_environment_file(self):
        """فحص ملف البيئة"""
        env_file = os.path.join(settings.BASE_DIR, '.env')
        env_example = os.path.join(settings.BASE_DIR, '.env.example')
        
        if not os.path.exists(env_file):
            if self.fix_mode and os.path.exists(env_example):
                try:
                    import shutil
                    shutil.copy2(env_example, env_file)
                    self.fixes_applied.append("تم إنشاء ملف .env من .env.example")
                    return True
                except Exception as e:
                    self.issues_found.append(f"لا يمكن إنشاء ملف .env: {str(e)}")
                    return False
            else:
                self.issues_found.append("ملف .env مفقود")
                return False
        return True

    def check_superuser(self):
        """فحص وجود مستخدم إداري"""
        try:
            if not User.objects.filter(is_superuser=True).exists():
                if self.fix_mode:
                    try:
                        # إنشاء مستخدم إداري افتراضي
                        User.objects.create_superuser(
                            username='superadmin',
                            email='admin@tonyerp.com',
                            password='admin123'
                        )
                        self.fixes_applied.append("تم إنشاء مستخدم إداري: superadmin/admin123")
                        return True
                    except Exception as e:
                        self.issues_found.append(f"لا يمكن إنشاء مستخدم إداري: {str(e)}")
                        return False
                else:
                    self.issues_found.append("لا يوجد مستخدم إداري")
                    return False
            return True
        except Exception as e:
            self.issues_found.append(f"خطأ في فحص المستخدمين: {str(e)}")
            return False

    def check_celery(self):
        """فحص إعدادات Celery"""
        try:
            from celery import current_app
            # فحص أساسي لإعدادات Celery
            return True
        except ImportError:
            self.issues_found.append("Celery غير مثبت")
            return False
        except Exception:
            # Celery مثبت لكن قد لا يعمل، هذا مقبول
            return True

    def check_disk_space(self):
        """فحص المساحة المتاحة"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(settings.BASE_DIR)
            free_gb = free // (1024**3)
            
            if free_gb < 1:  # أقل من 1 GB
                self.issues_found.append(f"مساحة القرص منخفضة: {free_gb} GB متاح")
                return False
            return True
        except Exception:
            return True  # لا يمكن فحص المساحة، تجاهل

    def check_dependencies(self):
        """فحص المكتبات المطلوبة"""
        required_packages = [
            'django',
            'djangorestframework',
            'redis',
            'celery',
        ]
        # Conditionally require database drivers
        try:
            default_db = settings.DATABASES.get('default', {})
            engine = default_db.get('ENGINE', '')
            if 'postgresql' in engine:
                required_packages.append('psycopg2')
            elif 'mysql' in engine:
                required_packages.append('mysqlclient')
        except Exception:
            pass
        
        missing_packages = []
        name_to_module = {
            'djangorestframework': 'rest_framework',
            'mysqlclient': 'MySQLdb',
        }
        for package in required_packages:
            module_name = name_to_module.get(package, package.replace('-', '_'))
            try:
                importlib.import_module(module_name)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.issues_found.append(f"مكتبات مفقودة: {', '.join(missing_packages)}")
            if self.fix_mode:
                self.safe_write(
                    f"\nTIP: ثبت المكتبات المفقودة: pip install {' '.join(missing_packages)}\n",
                    style=self.style.WARNING
                )
            return False
        return True

    def show_results(self, passed_checks, total_checks):
        """عرض نتائج الفحص"""
        if self.quiet:
            return

        self.safe_write("\n" + "="*80)
        self.safe_write(f"RESULTS: {passed_checks}/{total_checks} PASSED")
        self.safe_write("="*80)

        if self.issues_found:
            self.safe_write("\nISSUES:", style=self.style.WARNING)
            for i, issue in enumerate(self.issues_found, 1):
                self.safe_write(f"   {i}. {issue}")

        if self.fixes_applied:
            self.safe_write("\nFIXES:", style=self.style.SUCCESS)
            for i, fix in enumerate(self.fixes_applied, 1):
                self.safe_write(f"   {i}. {fix}")

        if not self.issues_found:
            self.safe_write("\nALL CHECKS PASSED", style=self.style.SUCCESS)

        self.safe_write("="*80)

    # ------------------------------------------------------------------
    # طباعة آمنة (تُستخدم في كل مكان)
    # ------------------------------------------------------------------
    def safe_write(self, msg: str, style=None, ending='\n'):
        try:
            if style:
                self.stdout.write(style(msg), ending=ending)
            else:
                self.stdout.write(msg, ending=ending)
        except UnicodeEncodeError:
            ascii_msg = msg.encode('ascii', 'ignore').decode('ascii')
            try:
                if style:
                    self.stdout.write(style(ascii_msg), ending=ending)
                else:
                    self.stdout.write(ascii_msg, ending=ending)
            except Exception:
                pass