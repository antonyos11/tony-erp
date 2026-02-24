# -*- coding: utf-8 -*-
"""
أداة الهجرة إلى PostgreSQL
Migration Tool to PostgreSQL
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.db import connection
import io


class Command(BaseCommand):
    help = 'الهجرة من SQLite إلى PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='فحص المتطلبات فقط',
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='تصدير البيانات فقط',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='تنفيذ الهجرة الكاملة',
        )
        parser.add_argument(
            '--pg-host',
            type=str,
            default='localhost',
            help='PostgreSQL host',
        )
        parser.add_argument(
            '--pg-port',
            type=str,
            default='5432',
            help='PostgreSQL port',
        )
        parser.add_argument(
            '--pg-db',
            type=str,
            default='tony_erp',
            help='PostgreSQL database name',
        )
        parser.add_argument(
            '--pg-user',
            type=str,
            default='postgres',
            help='PostgreSQL username',
        )
        parser.add_argument(
            '--pg-password',
            type=str,
            default='',
            help='PostgreSQL password',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            help='مجلد الإخراج',
        )

    def handle(self, *args, **options):
        self.output_dir = Path(options.get('output_dir') or settings.BASE_DIR / 'migration_data')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.pg_config = {
            'host': options['pg_host'],
            'port': options['pg_port'],
            'database': options['pg_db'],
            'user': options['pg_user'],
            'password': options['pg_password'],
        }
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('   🚀 أداة الهجرة إلى PostgreSQL'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if options['check']:
            self.check_requirements()
        elif options['export']:
            self.export_data()
        elif options['full']:
            self.full_migration()
        else:
            # عرض التعليمات
            self.show_instructions()

    def show_instructions(self):
        """عرض تعليمات الهجرة"""
        self.stdout.write('''
   📋 خطوات الهجرة إلى PostgreSQL:
   ===============================

   1️⃣  التحقق من المتطلبات:
       python manage.py migrate_to_postgresql --check

   2️⃣  تثبيت PostgreSQL:
       • تحميل من: https://www.postgresql.org/download/
       • أو: choco install postgresql (Windows)

   3️⃣  تثبيت psycopg2:
       pip install psycopg2-binary

   4️⃣  إنشاء قاعدة البيانات:
       CREATE DATABASE tony_erp;
       CREATE USER tony_user WITH PASSWORD 'your_password';
       GRANT ALL PRIVILEGES ON DATABASE tony_erp TO tony_user;

   5️⃣  تصدير البيانات:
       python manage.py migrate_to_postgresql --export

   6️⃣  تحديث settings.py:
       • غيّر DB_ENGINE إلى 'postgresql'
       • أضف بيانات الاتصال

   7️⃣  تنفيذ الهجرات:
       python manage.py migrate

   8️⃣  استيراد البيانات:
       python manage.py loaddata migration_data/full_export.json

   💡 أو استخدم الهجرة الكاملة:
       python manage.py migrate_to_postgresql --full \\
           --pg-host localhost \\
           --pg-db tony_erp \\
           --pg-user postgres \\
           --pg-password your_password
''')

    def check_requirements(self):
        """فحص المتطلبات"""
        self.stdout.write('\n   🔍 فحص المتطلبات...')
        
        requirements = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
        # 1. فحص psycopg2
        try:
            import psycopg2  # type: ignore[import-not-found]
            requirements['passed'].append({
                'name': 'psycopg2',
                'message': f'مثبت (الإصدار: {psycopg2.__version__})'
            })
        except ImportError:
            requirements['failed'].append({
                'name': 'psycopg2',
                'message': 'غير مثبت. قم بتشغيل: pip install psycopg2-binary'
            })
        
        # 2. فحص قاعدة البيانات الحالية
        db_settings = settings.DATABASES['default']
        if 'sqlite' in db_settings.get('ENGINE', ''):
            db_path = db_settings.get('NAME')
            if os.path.exists(db_path):
                size_mb = os.path.getsize(db_path) / (1024 * 1024)
                requirements['passed'].append({
                    'name': 'قاعدة SQLite',
                    'message': f'موجودة ({size_mb:.2f} MB)'
                })
                
                # تحذير إذا كانت كبيرة جداً
                if size_mb > 500:
                    requirements['warnings'].append({
                        'name': 'حجم القاعدة',
                        'message': f'القاعدة كبيرة ({size_mb:.2f} MB). الهجرة قد تستغرق وقتاً'
                    })
            else:
                requirements['failed'].append({
                    'name': 'قاعدة SQLite',
                    'message': 'ملف القاعدة غير موجود'
                })
        else:
            requirements['warnings'].append({
                'name': 'نوع القاعدة',
                'message': 'القاعدة الحالية ليست SQLite'
            })
        
        # 3. فحص الاتصال بـ PostgreSQL
        try:
            import psycopg2  # type: ignore[import-not-found]
            conn = psycopg2.connect(
                host=self.pg_config['host'],
                port=self.pg_config['port'],
                user=self.pg_config['user'],
                password=self.pg_config['password'],
                database='postgres'  # قاعدة افتراضية
            )
            conn.close()
            requirements['passed'].append({
                'name': 'اتصال PostgreSQL',
                'message': f'نجح الاتصال بـ {self.pg_config["host"]}:{self.pg_config["port"]}'
            })
        except Exception as e:
            requirements['warnings'].append({
                'name': 'اتصال PostgreSQL',
                'message': f'فشل الاتصال: {str(e)[:50]}'
            })
        
        # 4. فحص مساحة القرص
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.output_dir)
            free_gb = free / (1024 ** 3)
            if free_gb < 1:
                requirements['warnings'].append({
                    'name': 'مساحة القرص',
                    'message': f'المساحة المتاحة قليلة ({free_gb:.2f} GB)'
                })
            else:
                requirements['passed'].append({
                    'name': 'مساحة القرص',
                    'message': f'{free_gb:.2f} GB متاحة'
                })
        except Exception:
            pass
        
        # عرض النتائج
        self.stdout.write('\n   ✅ تم التحقق:')
        for item in requirements['passed']:
            self.stdout.write(f'      ✓ {item["name"]}: {item["message"]}')
        
        if requirements['warnings']:
            self.stdout.write('\n   ⚠️ تحذيرات:')
            for item in requirements['warnings']:
                self.stdout.write(f'      ⚡ {item["name"]}: {item["message"]}')
        
        if requirements['failed']:
            self.stdout.write('\n   ❌ فشل:')
            for item in requirements['failed']:
                self.stdout.write(f'      ✗ {item["name"]}: {item["message"]}')
        
        # الخلاصة
        if requirements['failed']:
            self.stdout.write('\n   🔴 الهجرة غير ممكنة حالياً. قم بإصلاح المشاكل أعلاه.')
            return False
        else:
            self.stdout.write('\n   🟢 جاهز للهجرة!')
            return True

    def export_data(self):
        """تصدير البيانات"""
        self.stdout.write('\n   📤 تصدير البيانات...')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. تصدير كامل
        full_export_file = self.output_dir / f'full_export_{timestamp}.json'
        self.stdout.write('   📦 تصدير البيانات الكاملة...')
        
        output = io.StringIO()
        try:
            call_command('dumpdata',
                        '--natural-foreign',
                        '--natural-primary',
                        '--indent', '2',
                        exclude=[
                            'contenttypes',
                            'auth.permission',
                            'sessions',
                            'admin.logentry'
                        ],
                        stdout=output)
            
            with open(full_export_file, 'w', encoding='utf-8') as f:
                f.write(output.getvalue())
            
            size_mb = os.path.getsize(full_export_file) / (1024 * 1024)
            self.stdout.write(f'   ✅ تم: {full_export_file.name} ({size_mb:.2f} MB)')
            
        except Exception as e:
            self.stdout.write(f'   ❌ خطأ: {e}')
            return None
        
        # 2. تصدير حسب التطبيق (للاستعادة الجزئية)
        apps_to_export = [
            'core', 'users', 'accounting', 'inventory', 
            'sales', 'purchases', 'hr', 'partners', 'crm'
        ]
        
        self.stdout.write('\n   📦 تصدير التطبيقات بشكل منفصل...')
        
        for app in apps_to_export:
            try:
                app_file = self.output_dir / f'{app}_{timestamp}.json'
                output = io.StringIO()
                call_command('dumpdata', app,
                            '--natural-foreign',
                            '--natural-primary',
                            '--indent', '2',
                            stdout=output)
                
                with open(app_file, 'w', encoding='utf-8') as f:
                    f.write(output.getvalue())
                
                self.stdout.write(f'      ✓ {app}')
            except Exception:
                pass
        
        # 3. إنشاء ملف المعلومات
        info_file = self.output_dir / f'export_info_{timestamp}.json'
        info = {
            'timestamp': datetime.now().isoformat(),
            'source_database': settings.DATABASES['default'].get('NAME'),
            'source_engine': 'SQLite',
            'target_engine': 'PostgreSQL',
            'files': [
                str(f.name) for f in self.output_dir.glob(f'*_{timestamp}.json')
            ],
            'instructions': [
                'قم بتحديث settings.py لاستخدام PostgreSQL',
                'نفذ: python manage.py migrate',
                'نفذ: python manage.py loaddata <full_export_file>',
            ]
        }
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(f'\n   ✅ تم تصدير البيانات إلى: {self.output_dir}')
        
        return full_export_file

    def full_migration(self):
        """الهجرة الكاملة"""
        self.stdout.write('\n   🚀 بدء الهجرة الكاملة...')
        
        # 1. فحص المتطلبات
        if not self.check_requirements():
            raise CommandError('فشل فحص المتطلبات')
        
        # 2. تصدير البيانات
        export_file = self.export_data()
        if not export_file:
            raise CommandError('فشل تصدير البيانات')
        
        # 3. إنشاء ملف إعدادات PostgreSQL
        self.stdout.write('\n   ⚙️ إنشاء ملف الإعدادات...')
        
        pg_settings = f'''
# PostgreSQL Configuration
# أضف هذه الإعدادات إلى ملف .env أو settings.py

DB_ENGINE=postgresql
POSTGRES_HOST={self.pg_config['host']}
POSTGRES_PORT={self.pg_config['port']}
POSTGRES_DB={self.pg_config['database']}
POSTGRES_USER={self.pg_config['user']}
POSTGRES_PASSWORD={self.pg_config['password']}
'''
        
        env_file = self.output_dir / 'postgresql.env'
        with open(env_file, 'w') as f:
            f.write(pg_settings)
        
        self.stdout.write(f'   ✅ تم إنشاء: {env_file}')
        
        # 4. إنشاء سكريبت SQL لإنشاء القاعدة
        sql_script = f'''-- PostgreSQL Database Setup Script
-- قم بتنفيذ هذا السكريبت في psql أو pgAdmin

-- إنشاء المستخدم (إذا لم يكن موجوداً)
-- CREATE USER {self.pg_config['user']} WITH PASSWORD '{self.pg_config['password']}';

-- إنشاء قاعدة البيانات
CREATE DATABASE {self.pg_config['database']}
    WITH OWNER = {self.pg_config['user']}
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- منح الصلاحيات
GRANT ALL PRIVILEGES ON DATABASE {self.pg_config['database']} TO {self.pg_config['user']};

-- الاتصال بالقاعدة الجديدة
\\c {self.pg_config['database']}

-- تفعيل الإضافات المفيدة
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
'''
        
        sql_file = self.output_dir / 'create_database.sql'
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(sql_script)
        
        self.stdout.write(f'   ✅ تم إنشاء: {sql_file}')
        
        # 5. إنشاء سكريبت الاستيراد
        import_script = f'''@echo off
REM PostgreSQL Data Import Script
REM سكريبت استيراد البيانات إلى PostgreSQL

echo Setting environment variables...
set DB_ENGINE=postgresql
set POSTGRES_HOST={self.pg_config['host']}
set POSTGRES_PORT={self.pg_config['port']}
set POSTGRES_DB={self.pg_config['database']}
set POSTGRES_USER={self.pg_config['user']}
set POSTGRES_PASSWORD={self.pg_config['password']}

echo Running migrations...
python manage.py migrate

echo Importing data...
python manage.py loaddata {export_file}

echo Done!
pause
'''
        
        import_file = self.output_dir / 'import_to_postgresql.bat'
        with open(import_file, 'w') as f:
            f.write(import_script)
        
        self.stdout.write(f'   ✅ تم إنشاء: {import_file}')
        
        # 6. الخلاصة
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('   📋 الخطوات التالية:')
        self.stdout.write('=' * 60)
        self.stdout.write(f'''
   1. قم بتثبيت PostgreSQL إذا لم يكن مثبتاً

   2. نفذ سكريبت إنشاء القاعدة:
      psql -U postgres -f {sql_file}

   3. حدث متغيرات البيئة:
      نسخ محتوى {env_file} إلى .env

   4. نفذ سكريبت الاستيراد:
      {import_file}

   أو يدوياً:
      set DB_ENGINE=postgresql
      python manage.py migrate
      python manage.py loaddata {export_file}
''')

    def generate_comparison_report(self):
        """إنشاء تقرير مقارنة"""
        report = {
            'sqlite': {
                'pros': [
                    'لا يحتاج خادم منفصل',
                    'سهل النقل والنسخ',
                    'مناسب للتطوير',
                    'لا يحتاج إعداد',
                ],
                'cons': [
                    'أداء محدود مع البيانات الكبيرة',
                    'لا يدعم الاتصالات المتعددة جيداً',
                    'ميزات محدودة',
                    'لا يدعم التحكم بالوصول',
                ],
                'best_for': 'التطوير، التطبيقات الصغيرة، الاختبار'
            },
            'postgresql': {
                'pros': [
                    'أداء ممتاز مع البيانات الكبيرة',
                    'دعم كامل للـ ACID',
                    'ميزات متقدمة (JSON, Full-text search)',
                    'تحكم دقيق بالصلاحيات',
                    'يدعم الاتصالات المتعددة',
                    'نسخ احتياطي متقدم',
                ],
                'cons': [
                    'يحتاج خادم منفصل',
                    'إعداد أكثر تعقيداً',
                    'استهلاك موارد أكبر',
                ],
                'best_for': 'الإنتاج، التطبيقات الكبيرة، البيانات الحساسة'
            }
        }
        
        return report
