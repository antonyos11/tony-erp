"""
اكتشاف وفحص Models المفقودة و URLs المكسورة
الاستخدام: python manage.py fix_missing_models --check
"""
import importlib

from django.core.management.base import BaseCommand
from django.apps import apps
from django.urls import URLResolver, URLPattern, get_resolver


class Command(BaseCommand):
    help = 'اكتشاف Models المفقودة و URLs المكسورة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check', action='store_true',
            help='فحص فقط بدون إصلاح',
        )
        parser.add_argument(
            '--fix', action='store_true',
            help='محاولة إصلاح المشاكل المكتشفة',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('فحص Models المفقودة و URLs المكسورة'))
        self.stdout.write(self.style.WARNING('=' * 70))

        issues = []

        # 1. فحص التطبيقات المسجلة
        self.stdout.write('\n📦 فحص التطبيقات المسجلة...')
        from django.conf import settings
        for app_label in settings.INSTALLED_APPS:
            if app_label.startswith('django.') or app_label.startswith('rest_framework'):
                continue
            if '.' in app_label and not app_label.startswith('core.'):
                continue
            module_name = app_label.split('.')[0] if '.' not in app_label else app_label
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                self.stdout.write(self.style.ERROR(f'  ❌ {app_label}: {e}'))
                issues.append({'type': 'missing_app', 'app': app_label, 'error': str(e)})

        if not issues:
            self.stdout.write(self.style.SUCCESS('  ✅ كل التطبيقات محملة بنجاح'))

        # 2. فحص جداول Models في قاعدة البيانات
        self.stdout.write('\n📊 فحص جداول قاعدة البيانات...')
        from django.db import connection
        db_tables = set(connection.introspection.table_names())
        model_issues = 0
        for model in apps.get_models():
            table = model._meta.db_table
            if model._meta.managed is False:
                continue  # تجاهل النماذج غير المُدارة (managed=False)
            if table not in db_tables:
                self.stdout.write(self.style.ERROR(
                    f'  ❌ الجدول مفقود: {table} (Model: {model._meta.label})'
                ))
                issues.append({'type': 'missing_table', 'model': model._meta.label, 'table': table})
                model_issues += 1

        if model_issues == 0:
            self.stdout.write(self.style.SUCCESS('  ✅ كل الجداول موجودة'))

        # 3. فحص URLs
        self.stdout.write('\n🔗 فحص URLs...')
        broken_urls = self._check_urls(get_resolver())
        for url_info in broken_urls:
            self.stdout.write(self.style.ERROR(f'  ❌ {url_info}'))
            issues.append({'type': 'broken_url', 'url': url_info})

        if not broken_urls:
            self.stdout.write(self.style.SUCCESS('  ✅ كل URLs محملة بنجاح'))

        # الملخص
        self.stdout.write('\n' + '=' * 70)
        if issues:
            self.stdout.write(self.style.ERROR(f'🔴 تم اكتشاف {len(issues)} مشكلة'))
            for i, issue in enumerate(issues, 1):
                desc = issue.get('app', issue.get('model', issue.get('url', '')))
                self.stdout.write(f'  {i}. [{issue["type"]}] {desc}')

            if options.get('fix'):
                self.stdout.write(self.style.WARNING('\n🔧 اقتراحات الإصلاح:'))
                for issue in issues:
                    if issue['type'] == 'missing_table':
                        self.stdout.write(f'  → python manage.py makemigrations && python manage.py migrate')
                        break
        else:
            self.stdout.write(self.style.SUCCESS('✅ لم يتم اكتشاف أي مشاكل!'))

    def _check_urls(self, resolver, prefix=''):
        broken = []
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                try:
                    if hasattr(pattern, 'urlconf_name') and isinstance(pattern.urlconf_name, str):
                        importlib.import_module(pattern.urlconf_name)
                except ImportError as e:
                    broken.append(f'{prefix}{pattern.pattern} → {e}')
                broken.extend(self._check_urls(pattern, prefix=f'{prefix}{pattern.pattern}'))
            elif isinstance(pattern, URLPattern):
                if pattern.callback is None:
                    broken.append(f'{prefix}{pattern.pattern} → callback is None')
        return broken
