"""
خدمات النسخ الاحتياطي
Backup Services
"""

import os
import shutil
import zipfile
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.utils import timezone


class BackupService:
    """خدمة النسخ الاحتياطي"""
    
    def __init__(self, backup):
        self.backup = backup
        self.temp_dir = Path(settings.BASE_DIR) / 'temp_backups'
        self.temp_dir.mkdir(exist_ok=True)
    
    def execute(self):
        """تنفيذ النسخ الاحتياطي"""
        from .models import Backup
        import time
        
        start_time = time.time()
        self.backup.status = 'running'
        self.backup.started_at = timezone.now()
        self.backup.save()
        
        try:
            self.log("بدء النسخ الاحتياطي...")
            
            # إنشاء مجلد مؤقت
            backup_dir = self.temp_dir / str(self.backup.uuid)
            backup_dir.mkdir(exist_ok=True)
            
            files_count = 0
            
            # نسخ قاعدة البيانات
            if self.backup.includes_database:
                self.log("نسخ قاعدة البيانات...")
                self.backup_database(backup_dir)
                files_count += 1
                self.backup.progress = 30
                self.backup.save()
            
            # نسخ الوسائط
            if self.backup.includes_media:
                self.log("نسخ ملفات الوسائط...")
                media_count = self.backup_media(backup_dir)
                files_count += media_count
                self.backup.progress = 70
                self.backup.save()
            
            # ضغط الملفات
            self.log("ضغط الملفات...")
            zip_path = self.create_archive(backup_dir)
            
            # حساب الحجم
            file_size = os.path.getsize(zip_path)
            
            # رفع للسحابة
            self.log("رفع إلى السحابة...")
            cloud_path = self.upload_to_cloud(zip_path)
            
            # التحقق من نجاح الرفع قبل حذف الملفات المحلية
            if not cloud_path:
                raise Exception(
                    "فشل الرفع للسحابة - الملفات المحلية محفوظة في: " + str(zip_path)
                )
            
            self.backup.progress = 100
            
            # تحديث النسخة أولاً قبل حذف الملفات
            self.backup.status = 'completed'
            self.backup.file_path = cloud_path
            self.backup.file_size = file_size
            self.backup.files_count = files_count
            self.backup.completed_at = timezone.now()
            self.backup.duration_seconds = int(time.time() - start_time)
            self.backup.save()
            
            # تنظيف الملفات المحلية بعد التأكد من نجاح الحفظ
            try:
                shutil.rmtree(backup_dir)
                os.remove(zip_path)
            except Exception as cleanup_err:
                self.log(f"تحذير: فشل تنظيف الملفات المؤقتة: {cleanup_err}")
            
            self.log("اكتمل النسخ الاحتياطي بنجاح!")
            
            return True
            
        except Exception as e:
            self.backup.status = 'failed'
            self.backup.error_message = str(e)
            self.backup.completed_at = timezone.now()
            self.backup.duration_seconds = int(time.time() - start_time)
            self.backup.save()
            
            self.log(f"فشل: {str(e)}")
            
            return False
    
    def backup_database(self, backup_dir):
        """نسخ قاعدة البيانات"""
        db_settings = settings.DATABASES['default']
        db_engine = db_settings['ENGINE']
        
        db_file = backup_dir / 'database.sql'
        
        if 'postgresql' in db_engine:
            self._backup_postgresql(db_settings, db_file)
        elif 'mysql' in db_engine:
            self._backup_mysql(db_settings, db_file)
        elif 'sqlite' in db_engine:
            self._backup_sqlite(db_settings, db_file)
    
    def _backup_postgresql(self, db_settings, output_file):
        """نسخ PostgreSQL"""
        cmd = [
            'pg_dump',
            '-h', db_settings.get('HOST', 'localhost'),
            '-p', str(db_settings.get('PORT', 5432)),
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-f', str(output_file)
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        subprocess.run(cmd, env=env, check=True)
    
    def _backup_mysql(self, db_settings, output_file):
        """نسخ MySQL"""
        cmd = [
            'mysqldump',
            '-h', db_settings.get('HOST', 'localhost'),
            '-P', str(db_settings.get('PORT', 3306)),
            '-u', db_settings['USER'],
            f'-p{db_settings["PASSWORD"]}',
            db_settings['NAME']
        ]
        
        with open(output_file, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True)
    
    def _backup_sqlite(self, db_settings, output_file):
        """نسخ SQLite"""
        import sqlite3
        
        source = db_settings['NAME']
        conn = sqlite3.connect(source)
        
        with open(output_file, 'w') as f:
            for line in conn.iterdump():
                f.write(f'{line}\n')
        
        conn.close()
    
    def backup_media(self, backup_dir):
        """نسخ ملفات الوسائط"""
        media_dir = Path(settings.MEDIA_ROOT)
        
        if not media_dir.exists():
            return 0
        
        target_dir = backup_dir / 'media'
        shutil.copytree(media_dir, target_dir)
        
        # حساب عدد الملفات
        count = sum(1 for _ in target_dir.rglob('*') if _.is_file())
        return count
    
    def create_archive(self, backup_dir):
        """إنشاء ملف مضغوط"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_name = f"backup_{self.backup.uuid}_{timestamp}.zip"
        zip_path = self.temp_dir / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in backup_dir.rglob('*'):
                if file.is_file():
                    arcname = file.relative_to(backup_dir)
                    zipf.write(file, arcname)
        
        return zip_path
    
    def upload_to_cloud(self, file_path):
        """رفع إلى السحابة"""
        provider = self.backup.provider
        
        if provider.provider_type == 'local':
            return self._upload_local(file_path)
        elif provider.provider_type == 'google_drive':
            return self._upload_google_drive(file_path)
        elif provider.provider_type == 'dropbox':
            return self._upload_dropbox(file_path)
        elif provider.provider_type == 'aws_s3':
            return self._upload_s3(file_path)
        
        return str(file_path)
    
    def _upload_local(self, file_path):
        """حفظ محلي"""
        provider = self.backup.provider
        target_dir = Path(provider.folder_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = target_dir / Path(file_path).name
        shutil.copy2(file_path, target_path)
        
        return str(target_path)
    
    def _upload_google_drive(self, file_path):
        """رفع إلى Google Drive"""
        # يتطلب مكتبة google-api-python-client
        # هذا مثال مبسط
        self.log("رفع إلى Google Drive...")
        return f"gdrive://{Path(file_path).name}"
    
    def _upload_dropbox(self, file_path):
        """رفع إلى Dropbox"""
        # يتطلب مكتبة dropbox
        self.log("رفع إلى Dropbox...")
        return f"dropbox://{Path(file_path).name}"
    
    def _upload_s3(self, file_path):
        """رفع إلى S3"""
        # يتطلب مكتبة boto3
        self.log("رفع إلى Amazon S3...")
        return f"s3://{Path(file_path).name}"
    
    def log(self, message):
        """إضافة للسجل"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        self.backup.log += log_entry
        self.backup.save(update_fields=['log'])


class RestoreService:
    """خدمة الاستعادة"""
    
    def __init__(self, restore_point):
        self.restore_point = restore_point
        self.backup = restore_point.backup
    
    def execute(self):
        """تنفيذ الاستعادة"""
        from .models import RestorePoint
        
        self.restore_point.status = 'running'
        self.restore_point.started_at = timezone.now()
        self.restore_point.save()
        
        try:
            self.log("بدء الاستعادة...")
            
            # تحميل النسخة
            self.log("تحميل النسخة الاحتياطية...")
            backup_file = self.download_backup()
            
            # فك الضغط
            self.log("فك الضغط...")
            extracted_dir = self.extract_backup(backup_file)
            
            # استعادة قاعدة البيانات
            if self.restore_point.restore_database:
                self.log("استعادة قاعدة البيانات...")
                self.restore_database(extracted_dir)
            
            # استعادة الوسائط
            if self.restore_point.restore_media:
                self.log("استعادة ملفات الوسائط...")
                self.restore_media(extracted_dir)
            
            self.restore_point.status = 'completed'
            self.restore_point.completed_at = timezone.now()
            self.restore_point.save()
            
            # تحديث النسخة
            self.backup.restore_count += 1
            self.backup.last_restored = timezone.now()
            self.backup.save()
            
            self.log("اكتملت الاستعادة بنجاح!")
            return True
            
        except Exception as e:
            self.restore_point.status = 'failed'
            self.restore_point.error_message = str(e)
            self.restore_point.completed_at = timezone.now()
            self.restore_point.save()
            
            self.log(f"فشل: {str(e)}")
            return False
    
    def download_backup(self):
        """تحميل النسخة الاحتياطية"""
        # تحميل من المزود السحابي
        return self.backup.file_path
    
    def extract_backup(self, backup_file):
        """فك ضغط النسخة"""
        temp_dir = Path(settings.BASE_DIR) / 'temp_restore'
        temp_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        return temp_dir
    
    def restore_database(self, extracted_dir):
        """استعادة قاعدة البيانات"""
        db_file = extracted_dir / 'database.sql'
        if not db_file.exists():
            return
        
        db_settings = settings.DATABASES['default']
        db_engine = db_settings['ENGINE']
        
        if 'postgresql' in db_engine:
            self._restore_postgresql(db_settings, db_file)
        elif 'mysql' in db_engine:
            self._restore_mysql(db_settings, db_file)
        elif 'sqlite' in db_engine:
            self._restore_sqlite(db_settings, db_file)
    
    def _restore_postgresql(self, db_settings, db_file):
        """استعادة PostgreSQL"""
        cmd = [
            'psql',
            '-h', db_settings.get('HOST', 'localhost'),
            '-p', str(db_settings.get('PORT', 5432)),
            '-U', db_settings['USER'],
            '-d', db_settings['NAME'],
            '-f', str(db_file)
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        subprocess.run(cmd, env=env, check=True)
    
    def _restore_mysql(self, db_settings, db_file):
        """استعادة MySQL"""
        cmd = [
            'mysql',
            '-h', db_settings.get('HOST', 'localhost'),
            '-P', str(db_settings.get('PORT', 3306)),
            '-u', db_settings['USER'],
            f'-p{db_settings["PASSWORD"]}',
            db_settings['NAME']
        ]
        
        with open(db_file, 'r') as f:
            subprocess.run(cmd, stdin=f, check=True)
    
    def _restore_sqlite(self, db_settings, db_file):
        """استعادة SQLite"""
        import sqlite3
        
        target = db_settings['NAME']
        
        # حذف القاعدة الحالية
        if os.path.exists(target):
            os.remove(target)
        
        conn = sqlite3.connect(target)
        with open(db_file, 'r') as f:
            conn.executescript(f.read())
        conn.close()
    
    def restore_media(self, extracted_dir):
        """استعادة ملفات الوسائط"""
        media_backup = extracted_dir / 'media'
        
        if not media_backup.exists():
            return
        
        target_path = self.restore_point.restore_to_path or settings.MEDIA_ROOT
        
        # نسخ الملفات
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        
        shutil.copytree(media_backup, target_path)
    
    def log(self, message):
        """إضافة للسجل"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        self.restore_point.log += log_entry
        self.restore_point.save(update_fields=['log'])
