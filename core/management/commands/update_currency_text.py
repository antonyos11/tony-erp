import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'تحديث نصوص العملة من "ج.م" إلى نظام العملة الجديد'

    def handle(self, *args, **options):
        self.stdout.write('تحديث نصوص العملة في الملفات...')

        # المجلدات المراد البحث فيها
        search_paths = [
            os.path.join(settings.BASE_DIR, 'templates'),
            os.path.join(settings.BASE_DIR, 'hr'),
            os.path.join(settings.BASE_DIR, 'accounting'),
            os.path.join(settings.BASE_DIR, 'crm'),
            os.path.join(settings.BASE_DIR, 'sales'),
            os.path.join(settings.BASE_DIR, 'purchases'),
            os.path.join(settings.BASE_DIR, 'inventory'),
        ]

        replacements = {
            # في ملفات HTML
            r'ج.م سعودي': '{% currency_name %}',
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*ج.م': r'{{ \1|currency_format }}',
            r'>\s*ج.م\s*<': '>{% currency_symbol %}<',
            r'ج.م(?=\s*</span>)': '{% currency_symbol %}',
            r'ج.م(?=\s*$)': '{% currency_symbol %}',
            
            # في ملفات Python (admin.py, models.py)
            r'"ج.م"': '"{% currency_symbol %}"',
            r"'ج.م'": "'{% currency_symbol %}'",
            r'f"\{.*\}\s*ج.م"': r'f"{\1} {% currency_symbol %}"',
        }

        files_updated = 0
        total_replacements = 0

        for search_path in search_paths:
            if os.path.exists(search_path):
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        if file.endswith(('.html', '.py')):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                
                                original_content = content
                                file_replacements = 0
                                
                                for pattern, replacement in replacements.items():
                                    matches = re.findall(pattern, content)
                                    if matches:
                                        content = re.sub(pattern, replacement, content)
                                        file_replacements += len(matches)
                                
                                if content != original_content:
                                    # إضافة currency_tags إذا لم تكن موجودة في ملفات HTML
                                    if file.endswith('.html') and '{% load currency_tags %}' not in content:
                                        if '{% load static %}' in content:
                                            content = content.replace(
                                                '{% load static %}',
                                                '{% load static %}\n{% load currency_tags %}'
                                            )
                                    
                                    with open(file_path, 'w', encoding='utf-8') as f:
                                        f.write(content)
                                    
                                    files_updated += 1
                                    total_replacements += file_replacements
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f'تم تحديث {file_path} - {file_replacements} تغيير'
                                        )
                                    )
                                
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(f'خطأ في معالجة {file_path}: {str(e)}')
                                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nتم الانتهاء!\n'
                f'الملفات المحدثة: {files_updated}\n'
                f'إجمالي التغييرات: {total_replacements}'
            )
        )