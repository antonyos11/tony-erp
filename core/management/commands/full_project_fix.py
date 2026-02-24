"""
فحص شامل للمشروع - يشغل جميع الفحوصات مرة واحدة
الاستخدام: python manage.py full_project_fix
"""
import importlib
import os
import sys

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.apps import apps
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'فحص شامل للمشروع وتقرير بالمشاكل'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true',
            help='محاولة إصلاح المشاكل المكتشفة',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('🔍 فحص شامل للمشروع'))
        self.stdout.write(self.style.WARNING('=' * 70))

        total_issues = 0

        # 1. فحص Django System Check
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write('1️⃣  Django System Check')
        self.stdout.write('─' * 60)
        try:
            call_command('check', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  ✅ اجتاز فحص النظام'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ فشل: {e}'))
            total_issues += 1

        # 2. فحص Migrations
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write('2️⃣  فحص Migrations')
        self.stdout.write('─' * 60)
        from io import StringIO
        out = StringIO()
        call_command('showmigrations', '--plan', stdout=out)
        plan = out.getvalue()
        unapplied = [line for line in plan.strip().split('\n') if line.strip().startswith('[ ]')]
        if unapplied:
            self.stdout.write(self.style.WARNING(f'  ⚠️ {len(unapplied)} migration غير مطبق:'))
            for m in unapplied[:10]:
                self.stdout.write(f'    {m.strip()}')
            if len(unapplied) > 10:
                self.stdout.write(f'    ... و {len(unapplied) - 10} آخرين')
            total_issues += len(unapplied)

            if options.get('fix'):
                self.stdout.write(self.style.WARNING('  🔧 تطبيق migrations...'))
                call_command('migrate', '--no-input')
                self.stdout.write(self.style.SUCCESS('  ✅ تم تطبيق Migrations'))
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ كل Migrations مطبقة'))

        # 3. فحص التطبيقات
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write('3️⃣  فحص التطبيقات المسجلة')
        self.stdout.write('─' * 60)
        app_issues = 0
        for app_config in apps.get_app_configs():
            try:
                importlib.import_module(app_config.name)
            except ImportError as e:
                self.stdout.write(self.style.ERROR(f'  ❌ {app_config.label}: {e}'))
                app_issues += 1
                total_issues += 1
        if app_issues == 0:
            self.stdout.write(self.style.SUCCESS(
                f'  ✅ {len(list(apps.get_app_configs()))} تطبيق محمل بنجاح'
            ))

        # 4. فحص الجداول
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write('4️⃣  فحص جداول قاعدة البيانات')
        self.stdout.write('─' * 60)
        db_tables = set(connection.introspection.table_names())
        table_issues = 0
        for model in apps.get_models():
            table = model._meta.db_table
            if table not in db_tables and not model._meta.managed is False:
                self.stdout.write(self.style.ERROR(
                    f'  ❌ جدول مفقود: {table} ({model._meta.label})'
                ))
                table_issues += 1
                total_issues += 1
        if table_issues == 0:
            self.stdout.write(self.style.SUCCESS(
                f'  ✅ {len(list(apps.get_models()))} model، كل الجداول موجودة'
            ))

        # 5. فحص ملفات Views و URLs الأساسية
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write('5️⃣  فحص ملفات التطبيقات')
        self.stdout.write('─' * 60)
        file_issues = 0
        important_files = ['views.py', 'urls.py', 'models.py']
        base_dir = settings.BASE_DIR
        # استبعاد المجلدات التي تحتوي على حزم خارجية
        exclude_dirs = ('site-packages', 'dist-packages', 'venv', '.venv', 'env')

        for app_config in apps.get_app_configs():
            app_path_str = str(getattr(app_config, 'path', ''))
            if str(base_dir) in app_path_str and not any(ex in app_path_str for ex in exclude_dirs):
                for f in important_files:
                    fpath = os.path.join(app_config.path, f)
                    if f == 'views.py' and not os.path.exists(fpath):
                        # views.py ليس مطلوباً لكل التطبيقات
                        pass
                    elif f == 'urls.py' and not os.path.exists(fpath):
                        pass  # urls.py أيضاً اختياري
                    elif f == 'models.py' and not os.path.exists(fpath):
                        models_dir = os.path.join(app_config.path, 'models')
                        if not os.path.isdir(models_dir):
                            self.stdout.write(self.style.WARNING(
                                f'  ⚠️ {app_config.label}: models.py مفقود'
                            ))
                            file_issues += 1

        if file_issues == 0:
            self.stdout.write(self.style.SUCCESS('  ✅ كل ملفات التطبيقات الأساسية موجودة'))
        else:
            total_issues += file_issues

        # 6. فحص Settings
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write('6️⃣  فحص الإعدادات')
        self.stdout.write('─' * 60)
        settings_issues = []

        if settings.DEBUG:
            settings_issues.append('  ⚠️ DEBUG = True (مقبول للتطوير)')
        if settings.SECRET_KEY == 'django-insecure-*':
            settings_issues.append('  ⚠️ SECRET_KEY غير آمن')

        db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        if 'sqlite3' in db_engine:
            settings_issues.append('  ⚠️ قاعدة البيانات SQLite (مقبول للتطوير)')

        if settings_issues:
            for issue in settings_issues:
                self.stdout.write(self.style.WARNING(issue))
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ الإعدادات سليمة'))

        # 7. فحص Static Files
        self.stdout.write('\n' + '─' * 60)
        self.stdout.write('7️⃣  فحص Static Files')
        self.stdout.write('─' * 60)
        static_dirs = getattr(settings, 'STATICFILES_DIRS', [])
        static_ok = True
        for sd in static_dirs:
            if not os.path.isdir(sd):
                self.stdout.write(self.style.WARNING(f'  ⚠️ مجلد static مفقود: {sd}'))
                static_ok = False

        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root:
            self.stdout.write(f'  📁 STATIC_ROOT: {static_root}')
        else:
            self.stdout.write(self.style.WARNING('  ⚠️ STATIC_ROOT غير محدد'))

        if static_ok:
            self.stdout.write(self.style.SUCCESS('  ✅ إعدادات Static Files سليمة'))

        # التقرير النهائي
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('📋 التقرير النهائي')
        self.stdout.write('=' * 70)

        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS('🎉 المشروع سليم! لا توجد مشاكل حرجة.'))
        else:
            self.stdout.write(self.style.ERROR(f'🔴 تم اكتشاف {total_issues} مشكلة'))
            if not options.get('fix'):
                self.stdout.write('💡 استخدم --fix لمحاولة الإصلاح التلقائي')

        self.stdout.write('=' * 70)
