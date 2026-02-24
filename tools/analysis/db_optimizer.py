#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
أداة تحسين قاعدة البيانات الشاملة
Database Optimization Tool
"""

import os
import sys
import sqlite3
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.db import connection


class DatabaseOptimizer:
    """أداة تحسين قاعدة البيانات"""
    
    def __init__(self, db_path='db.sqlite3'):
        self.db_path = db_path
    
    def optimize_all(self):
        """تنفيذ جميع التحسينات"""
        print('=' * 70)
        print('🚀 بدء تحسين قاعدة البيانات')
        print('=' * 70)
        
        self.analyze_tables()
        self.add_missing_indexes()
        self.vacuum_database()
        self.reindex_database()
        self.clean_expired_sessions()
        self.optimize_pragma()
        
        print('\n' + '=' * 70)
        print('✅ اكتملت جميع التحسينات')
        print('=' * 70)
    
    def analyze_tables(self):
        """تحليل الجداول لتحديث الإحصائيات"""
        print('\n📊 تحليل الجداول (ANALYZE)...')
        
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE")
        
        print('   ✅ تم تحليل جميع الجداول')
    
    def add_missing_indexes(self):
        """إضافة الفهارس المقترحة"""
        print('\n🔍 إضافة الفهارس المقترحة...')
        
        indexes_to_add = [
            # سجلات التدقيق
            ('idx_auditlog_timestamp_user', 'core_auditlog', 'timestamp, user_id'),
            ('idx_auditlog_content_type', 'core_auditlog', 'content_type_id'),
            ('idx_auditlog_action', 'core_auditlog', 'action'),
            
            # نشاط المستخدمين
            ('idx_useractivity_user_time', 'users_useractivity', 'user_id, timestamp'),
            ('idx_useractivity_type', 'users_useractivity', 'activity_type'),
            ('idx_useractivity_ip', 'users_useractivity', 'ip_address'),
            
            # الصلاحيات
            ('idx_modulepermission_module', 'users_modulepermission', 'module'),
            ('idx_modulepermission_role', 'users_modulepermission', 'role_id'),
            
            # الجلسات
            ('idx_usersession_user', 'users_usersession', 'user_id'),
            ('idx_usersession_active', 'users_usersession', 'is_active'),
            
            # الأدوار
            ('idx_userrole_code', 'users_userrole', 'code'),
            ('idx_userrole_active', 'users_userrole', 'is_active'),
        ]
        
        added = 0
        with connection.cursor() as cursor:
            for idx_name, table, columns in indexes_to_add:
                try:
                    # التحقق من وجود الجدول
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if not cursor.fetchone():
                        continue
                    
                    # التحقق من وجود الفهرس
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{idx_name}'")
                    if cursor.fetchone():
                        continue
                    
                    # إنشاء الفهرس
                    sql = f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})'
                    cursor.execute(sql)
                    added += 1
                    print(f'   ✅ تم إنشاء: {idx_name}')
                except Exception as e:
                    print(f'   ⚠️ تعذر إنشاء {idx_name}: {e}')
        
        print(f'   📊 تم إضافة {added} فهرس جديد')
    
    def vacuum_database(self):
        """تنظيف وضغط قاعدة البيانات"""
        print('\n🧹 تنظيف قاعدة البيانات (VACUUM)...')
        
        # الحجم قبل
        size_before = os.path.getsize(self.db_path)
        
        # تنفيذ VACUUM
        conn = sqlite3.connect(self.db_path)
        conn.execute("VACUUM")
        conn.close()
        
        # الحجم بعد
        size_after = os.path.getsize(self.db_path)
        saved = size_before - size_after
        
        print(f'   📦 الحجم قبل: {size_before / (1024*1024):.2f} MB')
        print(f'   📦 الحجم بعد: {size_after / (1024*1024):.2f} MB')
        print(f'   💾 تم توفير: {saved / 1024:.2f} KB')
    
    def reindex_database(self):
        """إعادة بناء الفهارس"""
        print('\n🔄 إعادة بناء الفهارس (REINDEX)...')
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("REINDEX")
        conn.close()
        
        print('   ✅ تم إعادة بناء جميع الفهارس')
    
    def clean_expired_sessions(self):
        """تنظيف الجلسات المنتهية"""
        print('\n🗑️ تنظيف الجلسات المنتهية...')
        
        with connection.cursor() as cursor:
            try:
                # حذف جلسات Django المنتهية
                cursor.execute("SELECT COUNT(*) FROM django_session WHERE expire_date < datetime('now')")
                expired_count = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM django_session WHERE expire_date < datetime('now')")
                print(f'   ✅ تم حذف {expired_count} جلسة منتهية')
            except Exception as e:
                print(f'   ⚠️ خطأ في تنظيف الجلسات: {e}')
    
    def optimize_pragma(self):
        """تحسين إعدادات SQLite"""
        print('\n⚙️ تحسين إعدادات SQLite...')
        
        pragmas = [
            ("PRAGMA journal_mode = WAL", "تفعيل وضع WAL"),
            ("PRAGMA synchronous = NORMAL", "تحسين التزامن"),
            ("PRAGMA cache_size = -64000", "زيادة الذاكرة المؤقتة (64MB)"),
            ("PRAGMA temp_store = MEMORY", "تخزين المؤقتات في الذاكرة"),
            ("PRAGMA mmap_size = 268435456", "تفعيل Memory Mapping (256MB)"),
        ]
        
        conn = sqlite3.connect(self.db_path)
        for pragma, desc in pragmas:
            try:
                conn.execute(pragma)
                print(f'   ✅ {desc}')
            except Exception as e:
                print(f'   ⚠️ {desc}: {e}')
        conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='أداة تحسين قاعدة البيانات')
    parser.add_argument('--analyze', action='store_true', help='تحليل الجداول فقط')
    parser.add_argument('--vacuum', action='store_true', help='تنظيف القاعدة فقط')
    parser.add_argument('--reindex', action='store_true', help='إعادة بناء الفهارس فقط')
    parser.add_argument('--indexes', action='store_true', help='إضافة الفهارس فقط')
    parser.add_argument('--clean', action='store_true', help='تنظيف الجلسات فقط')
    parser.add_argument('--all', action='store_true', help='تنفيذ جميع التحسينات')
    
    args = parser.parse_args()
    
    optimizer = DatabaseOptimizer()
    
    if args.all or not any([args.analyze, args.vacuum, args.reindex, args.indexes, args.clean]):
        optimizer.optimize_all()
    else:
        if args.analyze:
            optimizer.analyze_tables()
        if args.indexes:
            optimizer.add_missing_indexes()
        if args.vacuum:
            optimizer.vacuum_database()
        if args.reindex:
            optimizer.reindex_database()
        if args.clean:
            optimizer.clean_expired_sessions()


if __name__ == '__main__':
    main()
