#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام النسخ الاحتياطي واستعادة قاعدة البيانات
Database Backup and Recovery System
"""

import os
import sys
import shutil
import sqlite3
import hashlib
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()


class BackupManager:
    """مدير النسخ الاحتياطي"""
    
    def __init__(self, db_path='db.sqlite3', backup_dir='backups'):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # إعدادات الاحتفاظ
        self.retention_days = 30
        self.min_backups = 5
        self.max_backups = 50
    
    def create_backup(self, compress=True, description=''):
        """إنشاء نسخة احتياطية"""
        print('=' * 70)
        print('💾 إنشاء نسخة احتياطية')
        print('=' * 70)
        
        if not self.db_path.exists():
            print(f'❌ قاعدة البيانات غير موجودة: {self.db_path}')
            return None
        
        # اسم الملف
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'backup_{timestamp}'
        
        # حساب الـ checksum
        checksum = self._calculate_checksum(self.db_path)
        
        # النسخ
        print(f'\n📦 نسخ قاعدة البيانات...')
        
        if compress:
            backup_file = self.backup_dir / f'{backup_name}.db.gz'
            self._compress_file(self.db_path, backup_file)
        else:
            backup_file = self.backup_dir / f'{backup_name}.db'
            shutil.copy2(self.db_path, backup_file)
        
        # حفظ البيانات الوصفية
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'original_file': str(self.db_path),
            'backup_file': str(backup_file),
            'original_size': self.db_path.stat().st_size,
            'backup_size': backup_file.stat().st_size,
            'checksum': checksum,
            'compressed': compress,
            'description': description,
            'tables_count': self._count_tables(),
            'records_count': self._count_records()
        }
        
        metadata_file = self.backup_dir / f'{backup_name}.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # النتيجة
        print(f'\n✅ تم إنشاء النسخة الاحتياطية:')
        print(f'   📁 الملف: {backup_file}')
        print(f'   📊 الحجم الأصلي: {metadata["original_size"] / (1024*1024):.2f} MB')
        print(f'   📊 الحجم المضغوط: {metadata["backup_size"] / (1024*1024):.2f} MB')
        print(f'   🔐 Checksum: {checksum[:16]}...')
        print(f'   📋 الجداول: {metadata["tables_count"]}')
        print(f'   📋 السجلات: {metadata["records_count"]:,}')
        
        # تنظيف النسخ القديمة
        self._cleanup_old_backups()
        
        return backup_file
    
    def restore_backup(self, backup_file=None, verify=True):
        """استعادة نسخة احتياطية"""
        print('=' * 70)
        print('🔄 استعادة النسخة الاحتياطية')
        print('=' * 70)
        
        # اختيار النسخة
        if backup_file is None:
            backup_file = self._get_latest_backup()
        
        if backup_file is None:
            print('❌ لا توجد نسخ احتياطية متاحة')
            return False
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            print(f'❌ النسخة غير موجودة: {backup_file}')
            return False
        
        print(f'\n📁 النسخة المختارة: {backup_path.name}')
        
        # قراءة البيانات الوصفية
        metadata_file = backup_path.with_suffix('.json')
        if backup_path.suffix == '.gz':
            metadata_file = backup_path.with_name(backup_path.stem).with_suffix('.json')
        
        metadata = None
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            print(f'   📅 تاريخ النسخة: {metadata.get("timestamp", "غير معروف")}')
        
        # إنشاء نسخة احتياطية من الحالية قبل الاستعادة
        print('\n💾 إنشاء نسخة من قاعدة البيانات الحالية...')
        current_backup = self.db_path.with_suffix('.db.before_restore')
        if self.db_path.exists():
            shutil.copy2(self.db_path, current_backup)
        
        # الاستعادة
        print('🔄 جاري الاستعادة...')
        try:
            if backup_path.suffix == '.gz':
                self._decompress_file(backup_path, self.db_path)
            else:
                shutil.copy2(backup_path, self.db_path)
            
            # التحقق
            if verify and metadata:
                print('\n🔍 التحقق من سلامة الاستعادة...')
                current_checksum = self._calculate_checksum(self.db_path)
                
                if current_checksum == metadata.get('checksum'):
                    print('   ✅ Checksum متطابق')
                else:
                    print('   ⚠️ Checksum غير متطابق (قد يكون طبيعياً بعد العمليات)')
                
                current_tables = self._count_tables()
                if current_tables == metadata.get('tables_count'):
                    print(f'   ✅ عدد الجداول متطابق: {current_tables}')
                else:
                    print(f'   ⚠️ عدد الجداول: {current_tables} (المتوقع: {metadata.get("tables_count")})')
            
            print('\n✅ تمت الاستعادة بنجاح!')
            return True
            
        except Exception as e:
            print(f'\n❌ فشل في الاستعادة: {e}')
            
            # استعادة النسخة السابقة
            if current_backup.exists():
                print('🔄 استعادة النسخة السابقة...')
                shutil.copy2(current_backup, self.db_path)
            
            return False
    
    def list_backups(self):
        """عرض قائمة النسخ الاحتياطية"""
        print('=' * 70)
        print('📋 قائمة النسخ الاحتياطية')
        print('=' * 70)
        
        backups = list(self.backup_dir.glob('backup_*.db*'))
        backups = [b for b in backups if b.suffix in ['.db', '.gz']]
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not backups:
            print('\n⚠️ لا توجد نسخ احتياطية')
            return []
        
        print(f'\n📊 إجمالي النسخ: {len(backups)}\n')
        
        results = []
        for i, backup in enumerate(backups, 1):
            size = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            
            # قراءة البيانات الوصفية
            description = ''
            metadata_file = backup.with_name(backup.stem.replace('.db', '') + '.json')
            if backup.suffix == '.gz':
                metadata_file = backup.with_name(backup.name.replace('.db.gz', '.json'))
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        description = meta.get('description', '')
                except:
                    pass
            
            print(f'{i:2}. {backup.name}')
            print(f'    📅 {mtime.strftime("%Y-%m-%d %H:%M:%S")}')
            print(f'    📦 {size:.2f} MB')
            if description:
                print(f'    📝 {description}')
            print()
            
            results.append({
                'file': str(backup),
                'size': size,
                'date': mtime.isoformat(),
                'description': description
            })
        
        return results
    
    def verify_backup(self, backup_file):
        """التحقق من سلامة النسخة الاحتياطية"""
        print('=' * 70)
        print('🔍 التحقق من سلامة النسخة الاحتياطية')
        print('=' * 70)
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            print(f'❌ النسخة غير موجودة: {backup_file}')
            return False
        
        print(f'\n📁 الملف: {backup_path.name}')
        
        # فك الضغط مؤقتاً للتحقق
        temp_file = backup_path.with_suffix('.verify.db')
        
        try:
            if backup_path.suffix == '.gz':
                self._decompress_file(backup_path, temp_file)
            else:
                shutil.copy2(backup_path, temp_file)
            
            # فحص السلامة
            conn = sqlite3.connect(str(temp_file))
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            
            if result == 'ok':
                print('✅ النسخة سليمة')
                
                # إحصائيات
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchone()[0]
                print(f'   📋 الجداول: {tables}')
                
                conn.close()
                return True
            else:
                print(f'❌ النسخة تالفة: {result}')
                conn.close()
                return False
                
        except Exception as e:
            print(f'❌ خطأ في التحقق: {e}')
            return False
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    def _calculate_checksum(self, file_path):
        """حساب checksum للملف"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _compress_file(self, source, dest):
        """ضغط الملف"""
        with open(source, 'rb') as f_in:
            with gzip.open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)  # type: ignore[arg-type]
    
    def _decompress_file(self, source, dest):
        """فك ضغط الملف"""
        with gzip.open(source, 'rb') as f_in:
            with open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)  # type: ignore[arg-type]
    
    def _count_tables(self):
        """حساب عدد الجداول"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def _count_records(self):
        """حساب إجمالي السجلات"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            total = 0
            for (table,) in tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    total += cursor.fetchone()[0]
                except:
                    pass
            
            conn.close()
            return total
        except:
            return 0
    
    def _get_latest_backup(self):
        """الحصول على آخر نسخة احتياطية"""
        backups = list(self.backup_dir.glob('backup_*.db*'))
        backups = [b for b in backups if b.suffix in ['.db', '.gz']]
        
        if not backups:
            return None
        
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return backups[0]
    
    def _cleanup_old_backups(self):
        """تنظيف النسخ القديمة"""
        backups = list(self.backup_dir.glob('backup_*.db*'))
        backups = [b for b in backups if b.suffix in ['.db', '.gz']]
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if len(backups) <= self.min_backups:
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted = 0
        
        for backup in backups[self.min_backups:]:
            if len(backups) - deleted <= self.min_backups:
                break
            
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            
            if mtime < cutoff_date or len(backups) - deleted > self.max_backups:
                # حذف الملف والبيانات الوصفية
                backup.unlink()
                metadata_file = backup.with_name(backup.name.replace('.db.gz', '.json').replace('.db', '.json'))
                if metadata_file.exists():
                    metadata_file.unlink()
                deleted += 1
        
        if deleted > 0:
            print(f'\n🗑️ تم حذف {deleted} نسخة قديمة')


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='نظام النسخ الاحتياطي')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'verify'],
                       help='العملية المطلوبة')
    parser.add_argument('--file', '-f', help='ملف النسخة الاحتياطية')
    parser.add_argument('--no-compress', action='store_true', help='بدون ضغط')
    parser.add_argument('--description', '-d', default='', help='وصف النسخة')
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    if args.action == 'backup':
        manager.create_backup(compress=not args.no_compress, description=args.description)
    
    elif args.action == 'restore':
        manager.restore_backup(args.file)
    
    elif args.action == 'list':
        manager.list_backups()
    
    elif args.action == 'verify':
        if args.file:
            manager.verify_backup(args.file)
        else:
            latest = manager._get_latest_backup()
            if latest:
                manager.verify_backup(str(latest))
            else:
                print('❌ لا توجد نسخ للتحقق منها')


if __name__ == '__main__':
    main()
