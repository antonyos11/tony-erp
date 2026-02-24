# -*- coding: utf-8 -*-
"""
أداة تحليل أداء قاعدة البيانات الشاملة
Database Performance Analyzer Tool
"""

import os
import time
import json
from datetime import datetime, timedelta
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections
from django.conf import settings
from django.apps import apps


class Command(BaseCommand):
    help = 'تحليل شامل لأداء قاعدة البيانات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='تحليل شامل لكل شيء',
        )
        parser.add_argument(
            '--tables',
            action='store_true',
            help='تحليل الجداول',
        )
        parser.add_argument(
            '--indexes',
            action='store_true',
            help='تحليل الفهارس',
        )
        parser.add_argument(
            '--queries',
            action='store_true',
            help='تحليل الاستعلامات البطيئة',
        )
        parser.add_argument(
            '--relations',
            action='store_true',
            help='تحليل العلاقات',
        )
        parser.add_argument(
            '--recommendations',
            action='store_true',
            help='عرض التوصيات فقط',
        )
        parser.add_argument(
            '--export',
            type=str,
            help='تصدير التقرير إلى ملف JSON',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('   🔍 أداة تحليل أداء قاعدة البيانات'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'database_info': {},
            'tables_analysis': {},
            'indexes_analysis': {},
            'relations_analysis': {},
            'slow_queries': [],
            'recommendations': [],
            'statistics': {}
        }
        
        # معلومات قاعدة البيانات الأساسية
        report['database_info'] = self.get_database_info()
        
        run_all = options['full'] or not any([
            options['tables'], options['indexes'], 
            options['queries'], options['relations'],
            options['recommendations']
        ])
        
        if run_all or options['tables']:
            self.stdout.write('\n📊 تحليل الجداول...')
            report['tables_analysis'] = self.analyze_tables()
            
        if run_all or options['indexes']:
            self.stdout.write('\n📇 تحليل الفهارس...')
            report['indexes_analysis'] = self.analyze_indexes()
            
        if run_all or options['relations']:
            self.stdout.write('\n🔗 تحليل العلاقات...')
            report['relations_analysis'] = self.analyze_relations()
            
        if run_all or options['queries']:
            self.stdout.write('\n⏱️ تحليل الاستعلامات...')
            report['slow_queries'] = self.analyze_queries()
        
        # التوصيات دائماً
        self.stdout.write('\n💡 إنشاء التوصيات...')
        report['recommendations'] = self.generate_recommendations(report)
        
        # عرض الملخص
        self.display_summary(report)
        
        # تصدير إلى ملف
        if options['export']:
            self.export_report(report, options['export'])
        
        # لا نرجع شيء لتجنب الخطأ
        return None

    def get_database_info(self):
        """جمع معلومات قاعدة البيانات الأساسية"""
        db_settings = settings.DATABASES['default']
        info = {
            'engine': db_settings.get('ENGINE', ''),
            'name': db_settings.get('NAME', ''),
            'type': 'sqlite' if 'sqlite' in db_settings.get('ENGINE', '') else 'other',
        }
        
        # حجم قاعدة البيانات
        if info['type'] == 'sqlite' and os.path.exists(info['name']):
            size_bytes = os.path.getsize(info['name'])
            info['size_mb'] = round(size_bytes / (1024 * 1024), 2)
            info['size_bytes'] = size_bytes
        
        # إحصائيات SQLite
        with connection.cursor() as cursor:
            cursor.execute("SELECT sqlite_version()")
            info['sqlite_version'] = cursor.fetchone()[0]
            
            # عدد الجداول
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            info['total_tables'] = cursor.fetchone()[0]
            
            # عدد الفهارس
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            info['total_indexes'] = cursor.fetchone()[0]
            
        self.stdout.write(f"   📁 قاعدة البيانات: {info['name']}")
        self.stdout.write(f"   📏 الحجم: {info.get('size_mb', 'N/A')} MB")
        self.stdout.write(f"   📊 عدد الجداول: {info['total_tables']}")
        self.stdout.write(f"   📇 عدد الفهارس: {info['total_indexes']}")
        
        return info

    def analyze_tables(self):
        """تحليل شامل للجداول"""
        tables_info = {}
        
        with connection.cursor() as cursor:
            # جلب جميع الجداول
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                try:
                    # عدد السجلات
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    row_count = cursor.fetchone()[0]
                    
                    # معلومات الأعمدة
                    cursor.execute(f'PRAGMA table_info("{table}")')
                    columns = cursor.fetchall()
                    
                    # حجم الجدول التقريبي
                    cursor.execute(f"""
                        SELECT SUM(pgsize) FROM dbstat 
                        WHERE name='{table}'
                    """)
                    result = cursor.fetchone()
                    table_size = result[0] if result and result[0] else 0
                    
                    tables_info[table] = {
                        'row_count': row_count,
                        'column_count': len(columns),
                        'columns': [
                            {
                                'name': col[1],
                                'type': col[2],
                                'notnull': bool(col[3]),
                                'primary_key': bool(col[5])
                            } for col in columns
                        ],
                        'size_bytes': table_size,
                        'size_kb': round(table_size / 1024, 2) if table_size else 0
                    }
                    
                except Exception as e:
                    tables_info[table] = {'error': str(e)}
            
            # ترتيب حسب عدد السجلات
            sorted_tables = sorted(
                [(k, v) for k, v in tables_info.items() if 'row_count' in v],
                key=lambda x: x[1]['row_count'],
                reverse=True
            )
            
            self.stdout.write(f"\n   📋 أكبر 10 جداول:")
            for table, info in sorted_tables[:10]:
                self.stdout.write(
                    f"      • {table}: {info['row_count']:,} سجل "
                    f"({info['size_kb']} KB)"
                )
                
        return tables_info

    def analyze_indexes(self):
        """تحليل الفهارس"""
        indexes_info = {
            'existing': [],
            'missing': [],
            'unused': [],
            'duplicate': []
        }
        
        with connection.cursor() as cursor:
            # الفهارس الموجودة
            cursor.execute("""
                SELECT name, tbl_name, sql FROM sqlite_master 
                WHERE type='index' AND sql IS NOT NULL
                ORDER BY tbl_name, name
            """)
            
            for row in cursor.fetchall():
                indexes_info['existing'].append({
                    'name': row[0],
                    'table': row[1],
                    'sql': row[2]
                })
            
            # تحليل الفهارس المقترحة
            # جداول المحاسبة
            suggested_indexes = [
                ('accounting_journalentry', ['date', 'is_posted'], 'idx_je_date_posted'),
                ('accounting_journalentry', ['entry_type'], 'idx_je_type'),
                ('accounting_journalentry', ['created_by_id', 'date'], 'idx_je_user_date'),
                ('accounting_account', ['account_type'], 'idx_acc_type'),
                ('accounting_account', ['parent_id'], 'idx_acc_parent'),
                
                # جداول المبيعات
                ('sales_invoice', ['customer_id', 'date'], 'idx_inv_customer_date'),
                ('sales_invoice', ['due_date'], 'idx_inv_due_date'),
                ('sales_invoice', ['status'], 'idx_inv_status'),
                ('sales_invoiceitem', ['invoice_id'], 'idx_invitem_invoice'),
                ('sales_invoiceitem', ['product_id'], 'idx_invitem_product'),
                
                # جداول المشتريات
                ('purchases_purchasebill', ['supplier_id', 'date'], 'idx_pb_supplier_date'),
                ('purchases_purchasebill', ['status'], 'idx_pb_status'),
                
                # جداول المخزون
                ('inventory_stock', ['product_id', 'location_id'], 'idx_stock_prod_loc'),
                ('inventory_product', ['sku'], 'idx_prod_sku'),
                ('inventory_product', ['barcode'], 'idx_prod_barcode'),
                ('inventory_product', ['category_id'], 'idx_prod_category'),
                ('inventory_stockmovement', ['product_id', 'date'], 'idx_sm_prod_date'),
                
                # جداول الموارد البشرية
                ('hr_employee', ['status'], 'idx_emp_status'),
                ('hr_employee', ['department_id'], 'idx_emp_dept'),
                ('hr_attendance', ['employee_id', 'date'], 'idx_att_emp_date'),
                
                # جداول الشركاء
                ('partners_customer', ['name'], 'idx_cust_name'),
                ('partners_supplier', ['name'], 'idx_supp_name'),
            ]
            
            # جمع معلومات الفهارس الموجودة
            existing_index_tables = set()
            for idx in indexes_info['existing']:
                if idx['sql']:
                    try:
                        sql_lower = idx['sql'].lower()
                        if 'on' in sql_lower and '(' in sql_lower:
                            cols_part = sql_lower.split('on')[1].split('(')[1].split(')')[0]
                            cols = tuple(sorted(cols_part.replace(' ', '').split(',')))
                            existing_index_tables.add((idx['table'], cols))
                    except (IndexError, ValueError):
                        pass
            
            for table, columns, suggested_name in suggested_indexes:
                # تحقق من وجود الجدول
                cursor.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='{table}'
                """)
                if not cursor.fetchone():
                    continue
                    
                # تحقق من عدم وجود فهرس مشابه
                has_similar = False
                for idx in indexes_info['existing']:
                    if idx['table'] == table and idx['sql']:
                        idx_cols = idx['sql'].lower()
                        if all(col.lower() in idx_cols for col in columns):
                            has_similar = True
                            break
                
                if not has_similar:
                    indexes_info['missing'].append({
                        'table': table,
                        'columns': columns,
                        'suggested_name': suggested_name,
                        'sql': f'CREATE INDEX IF NOT EXISTS {suggested_name} ON {table} ({", ".join(columns)})'
                    })
            
            self.stdout.write(f"\n   ✅ الفهارس الموجودة: {len(indexes_info['existing'])}")
            self.stdout.write(f"   ⚠️ الفهارس المقترحة: {len(indexes_info['missing'])}")
            
            if indexes_info['missing']:
                self.stdout.write("\n   📝 الفهارس المقترحة:")
                for idx in indexes_info['missing'][:5]:
                    self.stdout.write(f"      • {idx['table']}: {', '.join(idx['columns'])}")
                    
        return indexes_info

    def analyze_relations(self):
        """تحليل العلاقات بين الجداول"""
        relations = {
            'foreign_keys': [],
            'orphan_records': [],
            'cascade_issues': []
        }
        
        with connection.cursor() as cursor:
            # جلب جميع الجداول
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                try:
                    cursor.execute(f'PRAGMA foreign_key_list("{table}")')
                    fks = cursor.fetchall()
                    
                    for fk in fks:
                        relations['foreign_keys'].append({
                            'from_table': table,
                            'from_column': fk[3],
                            'to_table': fk[2],
                            'to_column': fk[4],
                            'on_update': fk[5],
                            'on_delete': fk[6]
                        })
                except Exception:
                    pass
            
            self.stdout.write(f"\n   🔗 العلاقات الخارجية: {len(relations['foreign_keys'])}")
            
            # فحص السجلات اليتيمة (عينة)
            orphan_checks = [
                ('sales_invoice', 'customer_id', 'partners_customer', 'id'),
                ('sales_invoiceitem', 'invoice_id', 'sales_invoice', 'id'),
                ('purchases_purchasebill', 'supplier_id', 'partners_supplier', 'id'),
                ('inventory_stock', 'product_id', 'inventory_product', 'id'),
            ]
            
            for from_table, from_col, to_table, to_col in orphan_checks:
                try:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM "{from_table}" f
                        LEFT JOIN "{to_table}" t ON f.{from_col} = t.{to_col}
                        WHERE t.{to_col} IS NULL AND f.{from_col} IS NOT NULL
                    """)
                    orphan_count = cursor.fetchone()[0]
                    if orphan_count > 0:
                        relations['orphan_records'].append({
                            'table': from_table,
                            'column': from_col,
                            'references': f"{to_table}.{to_col}",
                            'count': orphan_count
                        })
                except Exception:
                    pass
            
            if relations['orphan_records']:
                self.stdout.write(f"   ⚠️ سجلات يتيمة: {len(relations['orphan_records'])}")
                for orphan in relations['orphan_records']:
                    self.stdout.write(
                        f"      • {orphan['table']}.{orphan['column']}: "
                        f"{orphan['count']} سجل يتيم"
                    )
                    
        return relations

    def analyze_queries(self):
        """تحليل الاستعلامات (محاكاة)"""
        slow_queries = []
        
        # اختبارات أداء على الجداول الرئيسية
        test_queries = [
            ("فواتير المبيعات", "SELECT * FROM sales_invoice WHERE date >= date('now', '-30 days')"),
            ("قيود اليومية", "SELECT * FROM accounting_journalentry WHERE is_posted = 1"),
            ("حركات المخزون", "SELECT * FROM inventory_stockmovement ORDER BY date DESC LIMIT 100"),
            ("حضور الموظفين", "SELECT * FROM hr_attendance WHERE date >= date('now', '-7 days')"),
            ("أرصدة المخزون", "SELECT product_id, SUM(quantity) FROM inventory_stock GROUP BY product_id"),
        ]
        
        with connection.cursor() as cursor:
            for name, query in test_queries:
                try:
                    start = time.time()
                    cursor.execute(query)
                    cursor.fetchall()
                    elapsed = (time.time() - start) * 1000  # بالميلي ثانية
                    
                    slow_queries.append({
                        'name': name,
                        'query': query,
                        'time_ms': round(elapsed, 2),
                        'is_slow': elapsed > 100  # أكثر من 100ms يعتبر بطيء
                    })
                except Exception as e:
                    slow_queries.append({
                        'name': name,
                        'query': query,
                        'error': str(e)
                    })
        
        self.stdout.write("\n   ⏱️ أداء الاستعلامات:")
        for q in slow_queries:
            if 'error' not in q:
                status = "🔴" if q['is_slow'] else "🟢"
                self.stdout.write(f"      {status} {q['name']}: {q['time_ms']} ms")
                
        return slow_queries

    def generate_recommendations(self, report):
        """إنشاء التوصيات"""
        recommendations = []
        
        # توصيات الحجم
        if report['database_info'].get('size_mb', 0) > 100:
            recommendations.append({
                'priority': 'high',
                'category': 'performance',
                'title': 'الانتقال إلى PostgreSQL',
                'description': 'حجم قاعدة البيانات كبير. يُنصح بالانتقال إلى PostgreSQL لأداء أفضل.',
                'action': 'استخدم أمر migrate_to_postgresql'
            })
        
        # توصيات الفهارس
        missing_indexes = report.get('indexes_analysis', {}).get('missing', [])
        if missing_indexes:
            recommendations.append({
                'priority': 'high',
                'category': 'indexes',
                'title': f'إضافة {len(missing_indexes)} فهرس',
                'description': 'هناك فهارس مقترحة يمكن أن تحسن الأداء بشكل كبير.',
                'action': 'python manage.py db_add_indexes'
            })
        
        # توصيات السجلات اليتيمة
        orphans = report.get('relations_analysis', {}).get('orphan_records', [])
        if orphans:
            recommendations.append({
                'priority': 'medium',
                'category': 'data_integrity',
                'title': 'إصلاح السجلات اليتيمة',
                'description': f'يوجد {sum(o["count"] for o in orphans)} سجل يتيم.',
                'action': 'python manage.py check_data_integrity --fix'
            })
        
        # توصيات الصيانة الدورية
        recommendations.append({
            'priority': 'medium',
            'category': 'maintenance',
            'title': 'جدولة الصيانة الدورية',
            'description': 'يُنصح بتشغيل VACUUM و ANALYZE أسبوعياً.',
            'action': 'python manage.py optimize_database --full'
        })
        
        # توصيات النسخ الاحتياطي
        recommendations.append({
            'priority': 'high',
            'category': 'backup',
            'title': 'إعداد النسخ الاحتياطي التلقائي',
            'description': 'يجب إعداد نظام نسخ احتياطي يومي.',
            'action': 'python manage.py db_backup --schedule'
        })
        
        # توصيات الجداول الكبيرة
        tables = report.get('tables_analysis', {})
        large_tables = [
            (name, info) for name, info in tables.items()
            if info.get('row_count', 0) > 10000
        ]
        if large_tables:
            recommendations.append({
                'priority': 'medium',
                'category': 'archiving',
                'title': 'أرشفة البيانات القديمة',
                'description': f'{len(large_tables)} جدول يحتوي على أكثر من 10,000 سجل.',
                'action': 'python manage.py db_archive --older-than 365'
            })
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("   💡 التوصيات")
        self.stdout.write("=" * 60)
        
        for rec in sorted(recommendations, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['priority']]):
            priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[rec['priority']]
            self.stdout.write(f"\n   {priority_icon} {rec['title']}")
            self.stdout.write(f"      {rec['description']}")
            self.stdout.write(f"      ⚡ {rec['action']}")
            
        return recommendations

    def display_summary(self, report):
        """عرض ملخص التقرير"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("   📊 ملخص التحليل")
        self.stdout.write("=" * 60)
        
        db_info = report['database_info']
        self.stdout.write(f"\n   📁 قاعدة البيانات: SQLite {db_info.get('sqlite_version', '')}")
        self.stdout.write(f"   📏 الحجم: {db_info.get('size_mb', 'N/A')} MB")
        self.stdout.write(f"   📊 الجداول: {db_info.get('total_tables', 0)}")
        self.stdout.write(f"   📇 الفهارس: {db_info.get('total_indexes', 0)}")
        
        # إحصائيات إضافية
        tables = report.get('tables_analysis', {})
        total_rows = sum(t.get('row_count', 0) for t in tables.values() if isinstance(t, dict))
        self.stdout.write(f"   📝 إجمالي السجلات: {total_rows:,}")
        
        missing_idx = len(report.get('indexes_analysis', {}).get('missing', []))
        self.stdout.write(f"   ⚠️ فهارس مقترحة: {missing_idx}")
        
        recs = report.get('recommendations', [])
        high_priority = len([r for r in recs if r['priority'] == 'high'])
        self.stdout.write(f"   🔴 توصيات عالية الأولوية: {high_priority}")

    def export_report(self, report, filepath):
        """تصدير التقرير"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        self.stdout.write(f"\n   ✅ تم تصدير التقرير إلى: {filepath}")
