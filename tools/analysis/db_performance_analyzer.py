#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
أداة فحص وتحسين أداء قاعدة البيانات
Database Performance Analyzer and Optimizer
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import sqlite3
from datetime import datetime, timedelta
from django.db import connection
from django.apps import apps
from django.db.models import Count, Sum, Avg, F, Q
from collections import defaultdict
import json


class DatabasePerformanceAnalyzer:
    """محلل أداء قاعدة البيانات"""
    
    def __init__(self):
        self.db_path = 'db.sqlite3'
        self.results = {
            'analysis_date': datetime.now().isoformat(),
            'issues': [],
            'recommendations': [],
            'stats': {}
        }
    
    def analyze_all(self):
        """تحليل شامل"""
        print('=' * 70)
        print('🔍 تحليل أداء قاعدة البيانات الشامل')
        print('=' * 70)
        
        self.analyze_table_sizes()
        self.analyze_indexes()
        self.analyze_query_patterns()
        self.analyze_data_distribution()
        self.analyze_relationships()
        self.check_common_issues()
        self.generate_recommendations()
        
        self.save_report()
        return self.results
    
    def analyze_table_sizes(self):
        """تحليل أحجام الجداول"""
        print('\n📊 تحليل أحجام الجداول...')
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            table_stats = []
            for (table_name,) in tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                    count = cursor.fetchone()[0]
                    
                    # تقدير حجم الجدول
                    cursor.execute(f'PRAGMA table_info("{table_name}")')
                    columns = cursor.fetchall()
                    
                    table_stats.append({
                        'name': table_name,
                        'rows': count,
                        'columns': len(columns)
                    })
                except Exception as e:
                    pass
            
            table_stats.sort(key=lambda x: x['rows'], reverse=True)
            self.results['stats']['tables'] = table_stats[:20]
            
            # تحديد الجداول الكبيرة
            large_tables = [t for t in table_stats if t['rows'] > 1000]
            if large_tables:
                self.results['issues'].append({
                    'type': 'large_tables',
                    'severity': 'info',
                    'message': f'يوجد {len(large_tables)} جداول بها أكثر من 1000 سجل',
                    'tables': [t['name'] for t in large_tables]
                })
        
        print(f'   ✅ تم تحليل {len(tables)} جدول')
    
    def analyze_indexes(self):
        """تحليل الفهارس"""
        print('\n🔍 تحليل الفهارس...')
        
        with connection.cursor() as cursor:
            # جمع معلومات الفهارس
            cursor.execute("""
                SELECT tbl_name, name, sql 
                FROM sqlite_master 
                WHERE type='index' AND sql IS NOT NULL
            """)
            indexes = cursor.fetchall()
            
            index_by_table = defaultdict(list)
            for tbl, idx_name, sql in indexes:
                index_by_table[tbl].append({
                    'name': idx_name,
                    'definition': sql
                })
            
            # الجداول الكبيرة بدون فهارس كافية
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            missing_indexes = []
            for (table_name,) in tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cursor.fetchone()[0]
                
                if count > 100 and len(index_by_table.get(table_name, [])) < 2:
                    missing_indexes.append({
                        'table': table_name,
                        'rows': count,
                        'current_indexes': len(index_by_table.get(table_name, []))
                    })
            
            if missing_indexes:
                self.results['issues'].append({
                    'type': 'missing_indexes',
                    'severity': 'warning',
                    'message': f'{len(missing_indexes)} جداول كبيرة تحتاج فهارس',
                    'tables': missing_indexes[:10]
                })
            
            self.results['stats']['index_count'] = len(indexes)
            self.results['stats']['tables_with_indexes'] = len(index_by_table)
        
        print(f'   ✅ تم تحليل {len(indexes)} فهرس')
    
    def analyze_query_patterns(self):
        """تحليل أنماط الاستعلامات الشائعة"""
        print('\n📈 تحليل أنماط البيانات...')
        
        recommendations = []
        
        # تحليل جداول السجلات (Audit/Log tables)
        with connection.cursor() as cursor:
            try:
                # جدول السجلات
                cursor.execute("SELECT COUNT(*) FROM core_auditlog")
                audit_count = cursor.fetchone()[0]
                
                if audit_count > 10000:
                    recommendations.append({
                        'table': 'core_auditlog',
                        'type': 'archiving',
                        'message': f'جدول السجلات كبير ({audit_count:,} سجل). ينصح بأرشفة السجلات القديمة',
                        'action': 'إنشاء جدول أرشيف ونقل السجلات الأقدم من 3 أشهر'
                    })
                
                # تحليل توزيع التواريخ
                cursor.execute("""
                    SELECT DATE(timestamp) as date, COUNT(*) as cnt 
                    FROM core_auditlog 
                    GROUP BY DATE(timestamp) 
                    ORDER BY date DESC 
                    LIMIT 7
                """)
                daily_audit = cursor.fetchall()
                self.results['stats']['audit_daily'] = [
                    {'date': str(d), 'count': c} for d, c in daily_audit
                ]
                
            except Exception as e:
                pass
            
            try:
                # جدول الجلسات
                cursor.execute("SELECT COUNT(*) FROM django_session WHERE expire_date < datetime('now')")
                expired = cursor.fetchone()[0]
                
                if expired > 50:
                    recommendations.append({
                        'table': 'django_session',
                        'type': 'cleanup',
                        'message': f'يوجد {expired} جلسة منتهية الصلاحية',
                        'action': 'تنظيف الجلسات المنتهية: python manage.py clearsessions'
                    })
            except:
                pass
        
        self.results['recommendations'].extend(recommendations)
        print(f'   ✅ تم تحليل أنماط البيانات')
    
    def analyze_data_distribution(self):
        """تحليل توزيع البيانات"""
        print('\n📊 تحليل توزيع البيانات...')
        
        distributions = {}
        
        with connection.cursor() as cursor:
            # تحليل النشاطات حسب المستخدم
            try:
                cursor.execute("""
                    SELECT user_id, COUNT(*) as cnt 
                    FROM users_useractivity 
                    GROUP BY user_id 
                    ORDER BY cnt DESC 
                    LIMIT 5
                """)
                user_activity = cursor.fetchall()
                distributions['top_active_users'] = [
                    {'user_id': u, 'activities': c} for u, c in user_activity
                ]
            except:
                pass
            
            # تحليل الصلاحيات
            try:
                cursor.execute("""
                    SELECT module, COUNT(*) as cnt 
                    FROM users_modulepermission 
                    GROUP BY module 
                    ORDER BY cnt DESC
                """)
                permissions = cursor.fetchall()
                distributions['permissions_by_module'] = [
                    {'module': m, 'count': c} for m, c in permissions
                ]
            except:
                pass
        
        self.results['stats']['distributions'] = distributions
        print('   ✅ تم تحليل التوزيع')
    
    def analyze_relationships(self):
        """تحليل العلاقات بين الجداول"""
        print('\n🔗 تحليل العلاقات...')
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            orphan_records = []
            
            for (table_name,) in tables:
                cursor.execute(f'PRAGMA foreign_key_list("{table_name}")')
                fks = cursor.fetchall()
                
                for fk in fks:
                    # fk = (id, seq, table, from, to, on_update, on_delete, match)
                    ref_table = fk[2]
                    from_col = fk[3]
                    to_col = fk[4]
                    
                    try:
                        # التحقق من وجود سجلات يتيمة
                        query = f'''
                            SELECT COUNT(*) FROM "{table_name}" t
                            WHERE t."{from_col}" IS NOT NULL 
                            AND NOT EXISTS (
                                SELECT 1 FROM "{ref_table}" r 
                                WHERE r."{to_col}" = t."{from_col}"
                            )
                        '''
                        cursor.execute(query)
                        orphan_count = cursor.fetchone()[0]
                        
                        if orphan_count > 0:
                            orphan_records.append({
                                'table': table_name,
                                'column': from_col,
                                'ref_table': ref_table,
                                'orphan_count': orphan_count
                            })
                    except:
                        pass
            
            if orphan_records:
                self.results['issues'].append({
                    'type': 'orphan_records',
                    'severity': 'error',
                    'message': f'يوجد سجلات يتيمة في {len(orphan_records)} علاقة',
                    'details': orphan_records[:10]
                })
        
        print('   ✅ تم تحليل العلاقات')
    
    def check_common_issues(self):
        """فحص المشاكل الشائعة"""
        print('\n⚠️ فحص المشاكل الشائعة...')
        
        with connection.cursor() as cursor:
            # فحص Foreign Keys المعطلة
            cursor.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            
            if not fk_enabled:
                self.results['issues'].append({
                    'type': 'foreign_keys_disabled',
                    'severity': 'warning',
                    'message': 'Foreign Keys معطلة في SQLite'
                })
            
            # فحص الجداول بدون Primary Key
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            tables_without_pk = []
            for (table_name,) in tables:
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                columns = cursor.fetchall()
                has_pk = any(col[5] for col in columns)  # col[5] = pk flag
                if not has_pk:
                    tables_without_pk.append(table_name)
            
            if tables_without_pk:
                self.results['issues'].append({
                    'type': 'missing_primary_key',
                    'severity': 'warning',
                    'message': f'{len(tables_without_pk)} جداول بدون Primary Key',
                    'tables': tables_without_pk[:10]
                })
            
            # فحص التجزئة
            cursor.execute("PRAGMA freelist_count")
            freelist = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            fragmentation = (freelist / page_count * 100) if page_count > 0 else 0
            
            if fragmentation > 10:
                self.results['issues'].append({
                    'type': 'fragmentation',
                    'severity': 'warning',
                    'message': f'نسبة التجزئة عالية ({fragmentation:.1f}%)',
                    'action': 'تنفيذ VACUUM لتقليل التجزئة'
                })
        
        print('   ✅ تم فحص المشاكل الشائعة')
    
    def generate_recommendations(self):
        """توليد التوصيات"""
        print('\n💡 توليد التوصيات...')
        
        # توصيات الفهارس
        suggested_indexes = [
            {
                'table': 'core_auditlog',
                'columns': ['timestamp', 'user_id'],
                'reason': 'تسريع البحث في السجلات حسب التاريخ والمستخدم'
            },
            {
                'table': 'users_useractivity',
                'columns': ['user_id', 'timestamp'],
                'reason': 'تسريع استعلامات نشاط المستخدم'
            },
            {
                'table': 'users_useractivity',
                'columns': ['activity_type'],
                'reason': 'تسريع الفلترة حسب نوع النشاط'
            }
        ]
        
        self.results['recommendations'].extend([
            {
                'type': 'index',
                'priority': 'high',
                'details': idx
            } for idx in suggested_indexes
        ])
        
        # توصيات عامة
        general_recommendations = [
            {
                'type': 'backup',
                'priority': 'critical',
                'message': 'إعداد نسخ احتياطي تلقائي يومي',
                'action': 'استخدام أداة backup_database.py'
            },
            {
                'type': 'monitoring',
                'priority': 'high',
                'message': 'مراقبة حجم قاعدة البيانات',
                'action': 'جدولة تقرير أسبوعي'
            },
            {
                'type': 'maintenance',
                'priority': 'medium',
                'message': 'تنظيف البيانات القديمة',
                'action': 'أرشفة السجلات الأقدم من 6 أشهر'
            }
        ]
        
        self.results['recommendations'].extend(general_recommendations)
        print('   ✅ تم توليد التوصيات')
    
    def save_report(self):
        """حفظ التقرير"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'db_analysis_report_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f'\n📄 تم حفظ التقرير: {filename}')
    
    def print_summary(self):
        """طباعة ملخص"""
        print('\n' + '=' * 70)
        print('📋 ملخص التحليل')
        print('=' * 70)
        
        # المشاكل
        issues_by_severity = defaultdict(list)
        for issue in self.results['issues']:
            issues_by_severity[issue['severity']].append(issue)
        
        print(f'\n🔴 أخطاء: {len(issues_by_severity["error"])}')
        for issue in issues_by_severity['error']:
            print(f'   - {issue["message"]}')
        
        print(f'\n🟡 تحذيرات: {len(issues_by_severity["warning"])}')
        for issue in issues_by_severity['warning']:
            print(f'   - {issue["message"]}')
        
        print(f'\n🔵 معلومات: {len(issues_by_severity["info"])}')
        
        # التوصيات
        print(f'\n💡 التوصيات ({len(self.results["recommendations"])}):')
        for rec in self.results['recommendations'][:5]:
            if 'message' in rec:
                print(f'   - {rec["message"]}')
            elif 'details' in rec:
                d = rec['details']
                print(f'   - إضافة فهرس على {d["table"]}.{d["columns"]}: {d["reason"]}')


def main():
    analyzer = DatabasePerformanceAnalyzer()
    analyzer.analyze_all()
    analyzer.print_summary()


if __name__ == '__main__':
    main()
