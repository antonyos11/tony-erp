"""
أمر استرداد النسخة الاحتياطية
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command
import os
import shutil
import zipfile
import subprocess
from pathlib import Path
import tempfile


class Command(BaseCommand):
    help = 'استرداد نسخة احتياطية للنظام'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_path',
            type=str,
            help='مسار ملف النسخة الاحتياطية'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='تأكيد الاستعادة بدون سؤال'
        )
        parser.add_argument(
            '--database-only',
            action='store_true',
            help='استرداد قاعدة البيانات فقط'
        )
        parser.add_argument(
            '--skip-media',
            action='store_true',
            help='تخطي استرداد ملفات الميديا'
        )

    def handle(self, *args, **options):
        backup_path = Path(options['backup_path'])
        
        if not backup_path.exists():
            self.stdout.write(self.style.ERROR(f"ملف النسخة الاحتياطية غير موجود: {backup_path}"))
            return
        
        if not backup_path.suffix.lower() == '.zip':
            self.stdout.write(self.style.ERROR("يجب أن يكون ملف النسخة الاحتياطية من نوع ZIP"))
            return
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING("تحذير: استرداد النسخة الاحتياطية"))
        self.stdout.write("="*60)
        self.stdout.write("هذه العملية ستقوم بـ:")
        self.stdout.write("- استبدال قاعدة البيانات الحالية")
        if not options['database_only'] and not options['skip_media']:
            self.stdout.write("- استبدال ملفات الميديا")
        self.stdout.write("- قد تفقد البيانات الحالية غير المحفوظة")
        self.stdout.write("="*60 + "\n")
        
        if not options['confirm']:
            confirm = input("هل أنت متأكد من المتابعة؟ اكتب 'نعم' للتأكيد: ")
            if confirm.lower() not in ['نعم', 'yes', 'y']:
                self.stdout.write(self.style.WARNING("تم إلغاء العملية"))
                return
        
        try:
            self.stdout.write(self.style.SUCCESS("بدء استرداد النسخة الاحتياطية..."))
            
            # استخراج النسخة الاحتياطية
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_path = Path(temp_dir) / 'extracted'
                extract_path.mkdir()
                
                self.stdout.write("استخراج النسخة الاحتياطية...")
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(extract_path)
                
                # البحث عن المجلد الفرعي
                backup_contents = list(extract_path.iterdir())
                if len(backup_contents) == 1 and backup_contents[0].is_dir():
                    backup_root = backup_contents[0]
                else:
                    backup_root = extract_path
                
                # استرداد قاعدة البيانات
                self.stdout.write("استرداد قاعدة البيانات...")
                self.restore_database(backup_root)
                
                if not options['database_only']:
                    # استرداد الملفات
                    self.stdout.write("استرداد الملفات...")
                    self.restore_files(backup_root)
                    
                    # استرداد ملفات الميديا
                    if not options['skip_media']:
                        self.stdout.write("استرداد ملفات الميديا...")
                        self.restore_media_files(backup_root)
                
                # تطبيق المهاجرات إذا لزم الأمر
                self.stdout.write("تطبيق المهاجرات...")
                call_command('migrate', verbosity=0)
                
                # جمع الملفات الثابتة
                self.stdout.write("جمع الملفات الثابتة...")
                call_command('collectstatic', verbosity=0, interactive=False)
            
            self.stdout.write("\n" + "="*60)
            self.stdout.write(self.style.SUCCESS("تم استرداد النسخة الاحتياطية بنجاح"))
            self.stdout.write("="*60)
            self.stdout.write("يُنصح بإعادة تشغيل الخادم الآن")
            self.stdout.write("="*60 + "\n")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطأ في استرداد النسخة الاحتياطية: {e}"))
            raise

    def restore_database(self, backup_root):
        """استرداد قاعدة البيانات"""
        db_backup_path = backup_root / 'database'
        
        if not db_backup_path.exists():
            raise Exception("لم يتم العثور على نسخة قاعدة البيانات في النسخة الاحتياطية")
        
        db_config = settings.DATABASES['default']
        
        if db_config['ENGINE'] == 'django.db.backends.sqlite3':
            # استرداد SQLite
            backup_db_file = db_backup_path / 'db.sqlite3'
            if backup_db_file.exists():
                current_db_file = Path(db_config['NAME'])
                
                # إنشاء نسخة احتياطية من قاعدة البيانات الحالية
                if current_db_file.exists():
                    backup_current = current_db_file.with_suffix('.sqlite3.backup')
                    shutil.copy2(current_db_file, backup_current)
                
                # نسخ قاعدة البيانات المسترجعة
                shutil.copy2(backup_db_file, current_db_file)
                self.stdout.write(self.style.SUCCESS("تم استرداد قاعدة بيانات SQLite"))
            else:
                raise Exception("ملف قاعدة بيانات SQLite غير موجود في النسخة الاحتياطية")
        
        elif db_config['ENGINE'] == 'django.db.backends.postgresql':
            # استرداد PostgreSQL
            dump_file = db_backup_path / 'postgres_dump.sql'
            if dump_file.exists():
                # حذف قاعدة البيانات الحالية وإعادة إنشائها
                self.recreate_postgres_database(db_config)
                
                # استرداد البيانات
                cmd = [
                    'psql',
                    '-h', db_config['HOST'],
                    '-p', str(db_config['PORT']),
                    '-U', db_config['USER'],
                    '-d', db_config['NAME'],
                    '-f', str(dump_file),
                    '--quiet'
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = db_config['PASSWORD']
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode == 0:
                    self.stdout.write(self.style.SUCCESS("تم استرداد قاعدة بيانات PostgreSQL"))
                else:
                    raise Exception(f"فشل استرداد PostgreSQL: {result.stderr}")
            else:
                raise Exception("ملف تصدير PostgreSQL غير موجود في النسخة الاحتياطية")
        
        elif db_config['ENGINE'] == 'django.db.backends.mysql':
            # استرداد MySQL
            dump_file = db_backup_path / 'mysql_dump.sql'
            if dump_file.exists():
                cmd = [
                    'mysql',
                    '-h', db_config['HOST'],
                    '-P', str(db_config['PORT']),
                    '-u', db_config['USER'],
                    f'-p{db_config["PASSWORD"]}',
                    db_config['NAME']
                ]
                
                with open(dump_file, 'r') as f:
                    result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
                    
                if result.returncode == 0:
                    self.stdout.write(self.style.SUCCESS("تم استرداد قاعدة بيانات MySQL"))
                else:
                    raise Exception(f"فشل استرداد MySQL: {result.stderr}")
            else:
                raise Exception("ملف تصدير MySQL غير موجود في النسخة الاحتياطية")

    def recreate_postgres_database(self, db_config):
        """إعادة إنشاء قاعدة بيانات PostgreSQL"""
        try:
            # الاتصال بقاعدة بيانات postgres للتحكم
            cmd_drop = [
                'psql',
                '-h', db_config['HOST'],
                '-p', str(db_config['PORT']),
                '-U', db_config['USER'],
                '-d', 'postgres',
                '-c', f"DROP DATABASE IF EXISTS {db_config['NAME']};"
            ]
            
            cmd_create = [
                'psql',
                '-h', db_config['HOST'],
                '-p', str(db_config['PORT']),
                '-U', db_config['USER'],
                '-d', 'postgres',
                '-c', f"CREATE DATABASE {db_config['NAME']};"
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            # حذف قاعدة البيانات
            subprocess.run(cmd_drop, env=env, capture_output=True)
            
            # إنشاء قاعدة البيانات
            result = subprocess.run(cmd_create, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"فشل إنشاء قاعدة البيانات: {result.stderr}")
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"تحذير: {e}"))

    def restore_files(self, backup_root):
        """استرداد الملفات المهمة"""
        config_path = backup_root / 'config'
        
        if config_path.exists():
            base_path = Path(settings.BASE_DIR)
            
            # استرداد ملفات التكوين
            files_to_restore = ['requirements.txt']  # تجنب استرداد .env لأسباب أمنية
            
            for filename in files_to_restore:
                source_file = config_path / filename
                if source_file.exists():
                    dest_file = base_path / filename
                    shutil.copy2(source_file, dest_file)
            
            self.stdout.write(self.style.SUCCESS("تم استرداد الملفات المهمة"))

    def restore_media_files(self, backup_root):
        """استرداد ملفات الميديا"""
        media_backup_path = backup_root / 'media'
        
        if media_backup_path.exists():
            media_root = Path(settings.MEDIA_ROOT)
            
            # إنشاء نسخة احتياطية من ملفات الميديا الحالية
            if media_root.exists():
                media_backup = media_root.parent / f"{media_root.name}_backup"
                if media_backup.exists():
                    shutil.rmtree(media_backup)
                shutil.move(str(media_root), str(media_backup))
            
            # نسخ ملفات الميديا المسترجعة
            shutil.copytree(media_backup_path, media_root)
            self.stdout.write(self.style.SUCCESS("تم استرداد ملفات الميديا"))
        else:
            self.stdout.write(self.style.WARNING("لم يتم العثور على ملفات الميديا في النسخة الاحتياطية"))