"""
أمر إنشاء نسخة احتياطية فورية
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import os
import shutil
import zipfile
import subprocess
from pathlib import Path
import tempfile


class Command(BaseCommand):
    help = 'إنشاء نسخة احتياطية شاملة للنظام'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=None,
            help='مجلد الحفظ (افتراضي: backups/)'
        )
        parser.add_argument(
            '--name',
            type=str,
            default=None,
            help='اسم النسخة الاحتياطية'
        )
        parser.add_argument(
            '--include-media',
            action='store_true',
            default=True,
            help='تضمين ملفات الميديا'
        )
        parser.add_argument(
            '--database-only',
            action='store_true',
            help='قاعدة البيانات فقط (بدون ملفات)'
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("بدء إنشاء النسخة الاحتياطية"))
        self.stdout.write("="*60 + "\n")

        try:
            # تحديد مجلد الحفظ
            if options['output_dir']:
                backup_dir = Path(options['output_dir'])
            else:
                backup_dir = Path(settings.BASE_DIR) / 'backups'

            backup_dir.mkdir(parents=True, exist_ok=True)

            # تحديد اسم النسخة الاحتياطية
            if options['name']:
                backup_name = options['name']
            else:
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"backup_{timestamp}"

            # مسار النسخة الاحتياطية النهائي
            backup_path = backup_dir / f"{backup_name}.zip"

            # إنشاء مجلد مؤقت
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / backup_name
                temp_path.mkdir()

                # نسخ قاعدة البيانات
                self.stdout.write("نسخ قاعدة البيانات...")
                self.backup_database(temp_path)

                if not options['database_only']:
                    # نسخ الملفات المهمة
                    self.stdout.write("نسخ الملفات المهمة...")
                    self.backup_important_files(temp_path)

                    # نسخ ملفات الميديا
                    if options['include_media']:
                        self.stdout.write("نسخ ملفات الميديا...")
                        self.backup_media_files(temp_path)

                # ضغط النسخة الاحتياطية
                self.stdout.write("ضغط النسخة الاحتياطية...")
                self.create_zip_archive(temp_path, backup_path)

            # حفظ سجل النسخة الاحتياطية
            self.record_backup(backup_name, backup_path, options)

            # تنظيف النسخ القديمة
            self.cleanup_old_backups(backup_dir)

            backup_size = backup_path.stat().st_size
            size_mb = backup_size / (1024 * 1024)

            self.stdout.write("\n" + "="*60)
            self.stdout.write(self.style.SUCCESS("تم إنشاء النسخة الاحتياطية بنجاح"))
            self.stdout.write(f"المسار: {backup_path}")
            self.stdout.write(f"الحجم: {size_mb:.2f} MB")
            self.stdout.write("="*60 + "\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطأ في إنشاء النسخة الاحتياطية: {e}"))
            raise

    def backup_database(self, temp_path):
        """نسخ قاعدة البيانات"""
        db_config = settings.DATABASES['default']
        db_backup_path = temp_path / 'database'
        db_backup_path.mkdir()
        
        if db_config['ENGINE'] == 'django.db.backends.sqlite3':
            # نسخ ملف SQLite
            db_file = Path(db_config['NAME'])
            if db_file.exists():
                shutil.copy2(db_file, db_backup_path / 'db.sqlite3')
                self.stdout.write(self.style.SUCCESS("تم نسخ قاعدة بيانات SQLite"))
        
        elif db_config['ENGINE'] == 'django.db.backends.postgresql':
            # تصدير PostgreSQL
            dump_file = db_backup_path / 'postgres_dump.sql'
            cmd = [
                'pg_dump',
                '-h', db_config['HOST'],
                '-p', str(db_config['PORT']),
                '-U', db_config['USER'],
                '-d', db_config['NAME'],
                '-f', str(dump_file),
                '--no-password'
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS("تم تصدير قاعدة بيانات PostgreSQL"))
            else:
                raise Exception(f"فشل تصدير PostgreSQL: {result.stderr}")
        
        elif db_config['ENGINE'] == 'django.db.backends.mysql':
            # تصدير MySQL
            dump_file = db_backup_path / 'mysql_dump.sql'
            cmd = [
                'mysqldump',
                '-h', db_config['HOST'],
                '-P', str(db_config['PORT']),
                '-u', db_config['USER'],
                f'-p{db_config["PASSWORD"]}',
                db_config['NAME']
            ]
            
            with open(dump_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS("تم تصدير قاعدة بيانات MySQL"))
            else:
                raise Exception(f"فشل تصدير MySQL: {result.stderr}")

    def backup_important_files(self, temp_path):
        """نسخ الملفات المهمة"""
        files_to_backup = [
            ('.env', 'config/'),
            ('requirements.txt', 'config/'),
            ('manage.py', 'config/'),
            ('logs/', 'logs/'),
        ]
        
        base_path = Path(settings.BASE_DIR)
        
        for source, dest in files_to_backup:
            source_path = base_path / source
            dest_path = temp_path / dest
            
            if source_path.exists():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                if source_path.is_file():
                    shutil.copy2(source_path, dest_path.parent / source_path.name)
                elif source_path.is_dir():
                    shutil.copytree(source_path, dest_path / source_path.name, dirs_exist_ok=True)

    def backup_media_files(self, temp_path):
        """نسخ ملفات الميديا"""
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            media_backup_path = temp_path / 'media'
            shutil.copytree(media_root, media_backup_path, dirs_exist_ok=True)
            self.stdout.write(self.style.SUCCESS("تم نسخ ملفات الميديا"))

    def create_zip_archive(self, source_path, output_path):
        """إنشاء أرشيف ZIP"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    archive_path = file_path.relative_to(source_path)
                    zipf.write(file_path, archive_path)
        self.stdout.write(self.style.SUCCESS("تم إنشاء الأرشيف المضغوط"))

    def record_backup(self, backup_name, backup_path, options):
        """تسجيل النسخة الاحتياطية في قاعدة البيانات"""
        try:
            from exports.models import BackupRecord
            from django.contrib.auth.models import User
            
            backup_size = backup_path.stat().st_size
            
            BackupRecord.objects.create(
                backup_name=backup_name,
                backup_type='manual',
                file_path=str(backup_path),
                file_size=backup_size,
                status='completed',
                includes_media=options.get('include_media', True),
                includes_database=True,
                created_by=None,  # يمكن تحسين هذا لاحقاً
                completed_at=timezone.now()
            )
            
        except ImportError:
            # إذا لم تكن نماذج exports متاحة بعد
            pass
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"فشل تسجيل النسخة الاحتياطية: {e}"))

    def cleanup_old_backups(self, backup_dir):
        """تنظيف النسخ القديمة"""
        try:
            retention_days = getattr(settings, 'BACKUP_RETENTION_DAYS', 30)
            cutoff_time = timezone.now() - timezone.timedelta(days=retention_days)
            
            deleted_count = 0
            for backup_file in backup_dir.glob('backup_*.zip'):
                file_time = timezone.datetime.fromtimestamp(backup_file.stat().st_mtime, tz=timezone.get_current_timezone())
                if file_time < cutoff_time:
                    backup_file.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                self.stdout.write(self.style.SUCCESS(f"تم حذف {deleted_count} نسخة احتياطية قديمة"))
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"فشل تنظيف النسخ القديمة: {e}"))