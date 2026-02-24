"""
اكتشاف وإنشاء Templates المفقودة
الاستخدام: python manage.py fix_missing_templates --check
"""
import os
import re

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'اكتشاف وإنشاء Templates المفقودة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check', action='store_true',
            help='فحص فقط بدون إصلاح',
        )
        parser.add_argument(
            '--fix', action='store_true',
            help='إنشاء Templates المفقودة',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('فحص Templates المفقودة'))
        self.stdout.write(self.style.WARNING('=' * 70))

        base_dir = settings.BASE_DIR
        missing_templates = []
        found_refs = []

        # البحث عن مراجع template_name في views.py
        template_pattern = re.compile(
            r"""(?:template_name\s*=\s*['"]|render\s*\(\s*request\s*,\s*['"]|get_template\s*\(\s*['"])"""
            r"""([a-zA-Z0-9_/\-]+\.html)['"]""",
            re.MULTILINE,
        )

        views_files = []
        for root, dirs, files in os.walk(base_dir):
            # تجاهل المجلدات غير الضرورية
            dirs[:] = [d for d in dirs if d not in (
                '.git', '__pycache__', 'node_modules', 'venv', 'env',
                '.venv', 'staticfiles', 'media', 'static',
            )]
            for f in files:
                if f.endswith('.py'):
                    views_files.append(os.path.join(root, f))

        self.stdout.write(f'\n📂 فحص {len(views_files)} ملف Python...')

        for fpath in views_files:
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                for match in template_pattern.finditer(content):
                    tpl_name = match.group(1)
                    found_refs.append((tpl_name, fpath))
            except (OSError, IOError):
                continue

        # إزالة التكرار
        unique_templates = set()
        for tpl_name, source in found_refs:
            unique_templates.add(tpl_name)

        self.stdout.write(f'  📝 تم العثور على {len(unique_templates)} مرجع template فريد')

        # التحقق من وجود كل template
        from django.template.loader import get_template
        from django.template import TemplateDoesNotExist

        for tpl_name in sorted(unique_templates):
            try:
                get_template(tpl_name)
            except TemplateDoesNotExist:
                missing_templates.append(tpl_name)
                self.stdout.write(self.style.ERROR(f'  ❌ مفقود: {tpl_name}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ خطأ في تحميل {tpl_name}: {e}'))

        # الملخص
        self.stdout.write('\n' + '=' * 70)
        if missing_templates:
            self.stdout.write(self.style.WARNING(
                f'🔴 {len(missing_templates)} template مفقود من أصل {len(unique_templates)}'
            ))

            if options.get('fix'):
                self.stdout.write(self.style.WARNING('\n🔧 إنشاء Templates المفقودة...'))
                created_count = 0
                for tpl_name in missing_templates:
                    parts = tpl_name.split('/')
                    if len(parts) >= 2:
                        app_name = parts[0]
                        tpl_dir = os.path.join(base_dir, app_name, 'templates', os.path.dirname(tpl_name))
                    else:
                        tpl_dir = os.path.join(base_dir, 'templates')

                    os.makedirs(tpl_dir, exist_ok=True)
                    tpl_path = os.path.join(tpl_dir, os.path.basename(tpl_name))

                    if os.path.exists(tpl_path):
                        continue

                    stub_content = self._generate_stub(tpl_name)
                    with open(tpl_path, 'w', encoding='utf-8') as fh:
                        fh.write(stub_content)
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✅ تم إنشاء: {tpl_path}'))

                self.stdout.write(self.style.SUCCESS(f'\n✅ تم إنشاء {created_count} template'))
            else:
                self.stdout.write('💡 استخدم --fix لإنشاء Templates المفقودة')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✅ كل Templates موجودة ({len(unique_templates)} template)'
            ))

    def _generate_stub(self, tpl_name):
        """إنشاء template أساسي"""
        title = tpl_name.replace('/', ' - ').replace('.html', '').replace('_', ' ').title()
        return f"""{{% extends "base.html" %}}

{{% block title %}}{title}{{% endblock %}}

{{% block content %}}
<div class="container mt-4">
    <div class="alert alert-warning">
        <h4>🚧 هذه الصفحة قيد التطوير</h4>
        <p>Template: <code>{tpl_name}</code></p>
    </div>
</div>
{{% endblock %}}
"""
