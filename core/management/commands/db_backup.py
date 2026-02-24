# -*- coding: utf-8 -*-
"""
نظام النسخ الاحتياطي الشامل لقاعدة البيانات
Comprehensive Database Backup System
"""

import os
import shutil
import gzip
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.db import connection
import io


class Command(BaseCommand):
    help = 'نظام نسخ احتياطي شامل لقاعدة البيانات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create',
            action='store_true',
            help='إنشاء نسخة احتياطية جديدة',
        )
        parser.add_argument(
            '--restore',
            type=str,
            help='استعادة من ملف نسخة احتياطية',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='عرض قائمة النسخ الاحتياطية',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='حذف النسخ الاحتياطية القديمة',
        )
        parser.add_argument(
            '--verify',
            type=str,
            help='التحقق من صحة نسخة احتياطية',
        )
        parser.add_argument(
            '--type',
            choices=['full', 'data', 'schema'],
            default='full',
            help='نوع النسخة الاحتياطية',
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            default=True,
            help='ضغط النسخة الاحتياطية',
        )
        parser.add_argument(
            '--keep-days',
            type=int,
            default=30,
            help='عدد أيام الاحتفاظ بالنسخ الاحتياطية',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            help='مجلد حفظ النسخ الاحتياطية',
        )

    def handle(self, *args, **options):
        self.backup_dir = Path(options.get('output_dir') or settings.BASE_DIR / 'backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('   💾 نظام النسخ الاحتياطي'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if options['create']:
            self.create_backup(options['type'], options['compress'])
        elif options['restore']:
            self.restore_backup(options['restore'])
        elif options['list']:
            self.list_backups()
        elif options['cleanup']:
            self.cleanup_old_backups(options['keep_days'])
        elif options['verify']:
            self.verify_backup(options['verify'])
        else:
            # الافتراضي: إنشاء نسخة احتياطية
            self.create_backup(options['type'], options['compress'])

    def create_backup(self, backup_type='full', compress=True):
        """إنشاء نسخة احتياطية"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_settings = settings.DATABASES['default']
        
        self.stdout.write(f'\n   📦 إنشاء نسخة احتياطية ({backup_type})...')
        
        backup_info = {
            'timestamp': datetime.now().isoformat(),
            'type': backup_type,
            'database': {
                'engine': db_settings.get('ENGINE', ''),
                'name': os.path.basename(db_settings.get('NAME', '')),
            },
            'files': [],
            'compressed': compress,
        }
        
        is_sqlite = 'sqlite' in db_settings.get('ENGINE', '')
        
        if is_sqlite:
            # نسخ احتياطي SQLite
            db_path = db_settings.get('NAME')
            if os.path.exists(db_path):
                # نسخة مباشرة من الملف
                if backup_type in ['full', 'data']:
                    backup_file = self.backup_dir / f'db_backup_{timestamp}.sqlite3'
                    
                    # استخدام backup API لضمان الاتساق
                    with connection.cursor() as cursor:
                        cursor.execute('BEGIN IMMEDIATE')
                        try:
                            shutil.copy2(db_path, backup_file)
                        finally:
                            cursor.execute('ROLLBACK')
                    
                    if compress:
                        compressed_file = self._compress_file(backup_file)
                        os.remove(backup_file)
                        backup_file = compressed_file
                    
                    backup_info['files'].append({
                        'name': backup_file.name,
                        'size': os.path.getsize(backup_file),
                        'checksum': self._calculate_checksum(backup_file)
                    })
                    
                    self.stdout.write(f'   ✅ تم إنشاء: {backup_file.name}')
                
                # تصدير البيانات كـ JSON
                if backup_type == 'full':
                    json_file = self.backup_dir / f'db_data_{timestamp}.json'
                    try:
                        self._export_data_json(json_file)
                        
                        if compress:
                            compressed_json = self._compress_file(json_file)
                            os.remove(json_file)
                            json_file = compressed_json
                        
                        backup_info['files'].append({
                            'name': json_file.name,
                            'size': os.path.getsize(json_file),
                            'checksum': self._calculate_checksum(json_file)
                        })
                        
                        self.stdout.write(f'   ✅ تم تصدير البيانات: {json_file.name}')
                    except Exception as e:
                        self.stdout.write(f'   ⚠️ تحذير: فشل تصدير JSON ({e})')
                        self.stdout.write('   📦 النسخة الاحتياطية من ملف SQLite متاحة')
        
        else:
            # PostgreSQL أو MySQL
            json_file = self.backup_dir / f'db_data_{timestamp}.json'
            self._export_data_json(json_file)
            
            if compress:
                compressed_json = self._compress_file(json_file)
                os.remove(json_file)
                json_file = compressed_json
            
            backup_info['files'].append({
                'name': json_file.name,
                'size': os.path.getsize(json_file),
                'checksum': self._calculate_checksum(json_file)
            })
        
        # حفظ معلومات النسخة الاحتياطية
        info_file = self.backup_dir / f'backup_info_{timestamp}.json'
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)
        
        # حساب الحجم الإجمالي
        total_size = sum(f['size'] for f in backup_info['files'])
        self.stdout.write(f'\n   📊 الحجم الإجمالي: {self._format_size(total_size)}')
        self.stdout.write(f'   📁 المجلد: {self.backup_dir}')
        
        return backup_info

    def restore_backup(self, backup_path):
        """استعادة من نسخة احتياطية"""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            # البحث في مجلد النسخ الاحتياطية
            backup_path = self.backup_dir / backup_path
            
        if not backup_path.exists():
            raise CommandError(f'ملف النسخة الاحتياطية غير موجود: {backup_path}')
        
        self.stdout.write(f'\n   ⚠️ تحذير: سيتم استبدال قاعدة البيانات الحالية!')
        self.stdout.write(f'   📦 الملف: {backup_path}')
        
        # التحقق من النوع
        if backup_path.suffix == '.gz':
            # فك الضغط أولاً
            temp_file = backup_path.with_suffix('')
            self._decompress_file(backup_path, temp_file)
            backup_path = temp_file
            cleanup_temp = True
        else:
            cleanup_temp = False
        
        db_settings = settings.DATABASES['default']
        is_sqlite = 'sqlite' in db_settings.get('ENGINE', '')
        
        if backup_path.suffix == '.sqlite3' and is_sqlite:
            # استعادة ملف SQLite مباشرة
            db_path = db_settings.get('NAME')
            
            # إنشاء نسخة احتياطية من القاعدة الحالية
            if os.path.exists(db_path):
                shutil.copy2(db_path, f"{db_path}.before_restore")
                self.stdout.write('   📋 تم إنشاء نسخة من القاعدة الحالية')
            
            # نسخ ملف النسخة الاحتياطية
            shutil.copy2(backup_path, db_path)
            self.stdout.write('   ✅ تم استعادة قاعدة البيانات بنجاح!')
            
        elif backup_path.suffix == '.json':
            # استعادة من JSON
            self._restore_from_json(backup_path)
            self.stdout.write('   ✅ تم استعادة البيانات بنجاح!')
        
        if cleanup_temp and backup_path.exists():
            os.remove(backup_path)

    def list_backups(self):
        """عرض قائمة النسخ الاحتياطية"""
        self.stdout.write('\n   📋 النسخ الاحتياطية المتوفرة:')
        self.stdout.write('   ' + '-' * 50)
        
        backups = []
        
        # البحث عن ملفات المعلومات
        for info_file in sorted(self.backup_dir.glob('backup_info_*.json'), reverse=True):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    backups.append(info)
            except Exception:
                pass
        
        if not backups:
            # البحث عن ملفات النسخ الاحتياطية مباشرة
            for backup_file in sorted(self.backup_dir.glob('db_backup_*'), reverse=True):
                size = os.path.getsize(backup_file)
                mtime = datetime.fromtimestamp(os.path.getmtime(backup_file))
                self.stdout.write(
                    f'   📦 {backup_file.name}'
                    f'\n      📏 {self._format_size(size)}'
                    f'\n      📅 {mtime.strftime("%Y-%m-%d %H:%M:%S")}'
                )
                self.stdout.write('')
            return
        
        for backup in backups:
            timestamp = backup.get('timestamp', 'غير معروف')
            backup_type = backup.get('type', 'full')
            files = backup.get('files', [])
            total_size = sum(f.get('size', 0) for f in files)
            
            self.stdout.write(f'   📦 {timestamp}')
            self.stdout.write(f'      النوع: {backup_type}')
            self.stdout.write(f'      الحجم: {self._format_size(total_size)}')
            self.stdout.write(f'      الملفات: {len(files)}')
            for f in files:
                self.stdout.write(f'         • {f["name"]}')
            self.stdout.write('')
        
        self.stdout.write(f'   📊 إجمالي النسخ: {len(backups)}')

    def cleanup_old_backups(self, keep_days=30):
        """حذف النسخ الاحتياطية القديمة"""
        self.stdout.write(f'\n   🧹 حذف النسخ الأقدم من {keep_days} يوم...')
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_count = 0
        freed_space = 0
        
        for backup_file in self.backup_dir.glob('*'):
            if backup_file.is_file():
                mtime = datetime.fromtimestamp(os.path.getmtime(backup_file))
                if mtime < cutoff_date:
                    size = os.path.getsize(backup_file)
                    os.remove(backup_file)
                    deleted_count += 1
                    freed_space += size
                    self.stdout.write(f'   🗑️ حذف: {backup_file.name}')
        
        self.stdout.write(f'\n   ✅ تم حذف {deleted_count} ملف')
        self.stdout.write(f'   💾 المساحة المُحررة: {self._format_size(freed_space)}')

    def verify_backup(self, backup_path):
        """التحقق من صحة نسخة احتياطية"""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            backup_path = self.backup_dir / backup_path
            
        if not backup_path.exists():
            raise CommandError(f'الملف غير موجود: {backup_path}')
        
        self.stdout.write(f'\n   🔍 التحقق من: {backup_path.name}')
        
        errors = []
        
        # التحقق من الحجم
        size = os.path.getsize(backup_path)
        if size == 0:
            errors.append('الملف فارغ')
        else:
            self.stdout.write(f'   ✅ الحجم: {self._format_size(size)}')
        
        # التحقق من الضغط
        if backup_path.suffix == '.gz':
            try:
                with gzip.open(backup_path, 'rb') as f:
                    f.read(1024)  # قراءة جزء للتحقق
                self.stdout.write('   ✅ الضغط صحيح')
            except Exception as e:
                errors.append(f'خطأ في الضغط: {e}')
        
        # التحقق من SQLite
        if '.sqlite3' in str(backup_path):
            try:
                import sqlite3
                test_path = backup_path
                
                if backup_path.suffix == '.gz':
                    test_path = backup_path.with_suffix('.sqlite3.temp')
                    self._decompress_file(backup_path, test_path)
                
                conn = sqlite3.connect(str(test_path))
                cursor = conn.cursor()
                cursor.execute('PRAGMA integrity_check')
                result = cursor.fetchone()[0]
                conn.close()
                
                if test_path != backup_path:
                    os.remove(test_path)
                
                if result == 'ok':
                    self.stdout.write('   ✅ سلامة قاعدة البيانات: OK')
                else:
                    errors.append(f'مشكلة في سلامة القاعدة: {result}')
                    
            except Exception as e:
                errors.append(f'خطأ في التحقق: {e}')
        
        # التحقق من JSON
        if backup_path.suffix == '.json':
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                self.stdout.write('   ✅ تنسيق JSON صحيح')
            except Exception as e:
                errors.append(f'خطأ في JSON: {e}')
        
        if errors:
            self.stdout.write('\n   ❌ أخطاء:')
            for error in errors:
                self.stdout.write(f'      • {error}')
            return False
        else:
            self.stdout.write('\n   ✅ النسخة الاحتياطية سليمة!')
            return True

    def _export_data_json(self, output_file):
        """تصدير البيانات إلى JSON"""
        output = io.StringIO()
        call_command('dumpdata', 
                    '--natural-foreign', 
                    '--natural-primary',
                    '--indent', '2',
                    exclude=['contenttypes', 'auth.permission', 'sessions'],
                    stdout=output)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output.getvalue())

    def _restore_from_json(self, json_file):
        """استعادة البيانات من JSON"""
        call_command('loaddata', str(json_file))

    def _compress_file(self, file_path):
        """ضغط ملف"""
        compressed_path = Path(str(file_path) + '.gz')
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return compressed_path

    def _decompress_file(self, gz_path, output_path):
        """فك ضغط ملف"""
        with gzip.open(gz_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)  # type: ignore[arg-type]

    def _calculate_checksum(self, file_path):
        """حساب checksum للملف"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _format_size(self, size_bytes):
        """تنسيق حجم الملف"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f'{size_bytes:.2f} {unit}'
            size_bytes /= 1024
        return f'{size_bytes:.2f} TB'
