# -*- coding: utf-8 -*-
"""
نظام مراقبة قاعدة البيانات
Database Monitoring System
"""

import os
import time
import json
import threading
from datetime import datetime, timedelta
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.conf import settings
from django.core.cache import cache


class Command(BaseCommand):
    help = 'مراقبة أداء قاعدة البيانات في الوقت الفعلي'

    def add_arguments(self, parser):
        parser.add_argument(
            '--live',
            action='store_true',
            help='مراقبة مباشرة في الوقت الفعلي',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='عرض إحصائيات الأداء',
        )
        parser.add_argument(
            '--slow-queries',
            action='store_true',
            help='عرض الاستعلامات البطيئة',
        )
        parser.add_argument(
            '--connections',
            action='store_true',
            help='عرض معلومات الاتصالات',
        )
        parser.add_argument(
            '--health',
            action='store_true',
            help='فحص صحة قاعدة البيانات',
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.1,
            help='عتبة الاستعلام البطيء (بالثانية)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='فترة التحديث للمراقبة المباشرة (بالثانية)',
        )
        parser.add_argument(
            '--export',
            type=str,
            help='تصدير التقرير إلى ملف',
        )

    def handle(self, *args, **options):
        self.threshold = options['threshold']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('   📊 نظام مراقبة قاعدة البيانات'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'database_health': {},
            'performance_stats': {},
            'slow_queries': [],
            'connection_info': {},
            'alerts': []
        }
        
        if options['live']:
            self.live_monitoring(options['interval'])
        elif options['slow_queries']:
            report['slow_queries'] = self.analyze_slow_queries()
        elif options['connections']:
            report['connection_info'] = self.show_connection_info()
        elif options['health']:
            report['database_health'] = self.check_health()
        elif options['stats']:
            report['performance_stats'] = self.show_stats()
        else:
            # الافتراضي: فحص شامل
            report['database_health'] = self.check_health()
            report['performance_stats'] = self.show_stats()
            report['connection_info'] = self.show_connection_info()
        
        if options['export']:
            self.export_report(report, options['export'])
        
        # لا نرجع شيء لتجنب الخطأ
        return None

    def check_health(self):
        """فحص صحة قاعدة البيانات"""
        self.stdout.write('\n   🏥 فحص صحة قاعدة البيانات...')
        
        health = {
            'status': 'healthy',
            'checks': [],
            'score': 100
        }
        
        db_settings = settings.DATABASES['default']
        is_sqlite = 'sqlite' in db_settings.get('ENGINE', '')
        
        with connection.cursor() as cursor:
            # 1. فحص الاتصال
            try:
                cursor.execute('SELECT 1')
                health['checks'].append({
                    'name': 'اتصال قاعدة البيانات',
                    'status': 'pass',
                    'message': 'الاتصال يعمل بشكل صحيح'
                })
            except Exception as e:
                health['checks'].append({
                    'name': 'اتصال قاعدة البيانات',
                    'status': 'fail',
                    'message': str(e)
                })
                health['score'] -= 50
            
            if is_sqlite:
                # 2. فحص سلامة SQLite
                try:
                    cursor.execute('PRAGMA integrity_check')
                    result = cursor.fetchone()[0]
                    if result == 'ok':
                        health['checks'].append({
                            'name': 'سلامة قاعدة البيانات',
                            'status': 'pass',
                            'message': 'لا توجد مشاكل في السلامة'
                        })
                    else:
                        health['checks'].append({
                            'name': 'سلامة قاعدة البيانات',
                            'status': 'warning',
                            'message': result
                        })
                        health['score'] -= 30
                except Exception as e:
                    health['checks'].append({
                        'name': 'سلامة قاعدة البيانات',
                        'status': 'fail',
                        'message': str(e)
                    })
                    health['score'] -= 30
                
                # 3. فحص حجم قاعدة البيانات
                db_path = db_settings.get('NAME')
                if os.path.exists(db_path):
                    size_mb = os.path.getsize(db_path) / (1024 * 1024)
                    if size_mb > 1000:  # أكثر من 1GB
                        health['checks'].append({
                            'name': 'حجم قاعدة البيانات',
                            'status': 'warning',
                            'message': f'الحجم كبير ({size_mb:.2f} MB). يُنصح بالانتقال إلى PostgreSQL'
                        })
                        health['score'] -= 10
                    else:
                        health['checks'].append({
                            'name': 'حجم قاعدة البيانات',
                            'status': 'pass',
                            'message': f'{size_mb:.2f} MB'
                        })
                
                # 4. فحص التجزئة
                try:
                    cursor.execute('PRAGMA freelist_count')
                    freelist = cursor.fetchone()[0]
                    cursor.execute('PRAGMA page_count')
                    page_count = cursor.fetchone()[0]
                    
                    fragmentation = (freelist / page_count * 100) if page_count > 0 else 0
                    
                    if fragmentation > 25:
                        health['checks'].append({
                            'name': 'تجزئة قاعدة البيانات',
                            'status': 'warning',
                            'message': f'التجزئة عالية ({fragmentation:.1f}%). قم بتشغيل VACUUM'
                        })
                        health['score'] -= 15
                    else:
                        health['checks'].append({
                            'name': 'تجزئة قاعدة البيانات',
                            'status': 'pass',
                            'message': f'{fragmentation:.1f}%'
                        })
                except Exception:
                    pass
                
                # 5. فحص الفهارس
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='index' AND sql IS NOT NULL
                """)
                index_count = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                table_count = cursor.fetchone()[0]
                
                ratio = index_count / table_count if table_count > 0 else 0
                
                if ratio < 1:
                    health['checks'].append({
                        'name': 'نسبة الفهارس',
                        'status': 'warning',
                        'message': f'نسبة الفهارس منخفضة ({ratio:.2f}). قد تحتاج إلى إضافة فهارس'
                    })
                    health['score'] -= 10
                else:
                    health['checks'].append({
                        'name': 'نسبة الفهارس',
                        'status': 'pass',
                        'message': f'{index_count} فهرس لـ {table_count} جدول'
                    })
        
        # تحديد الحالة العامة
        if health['score'] >= 90:
            health['status'] = 'excellent'
            status_emoji = '🟢'
        elif health['score'] >= 70:
            health['status'] = 'good'
            status_emoji = '🟡'
        elif health['score'] >= 50:
            health['status'] = 'fair'
            status_emoji = '🟠'
        else:
            health['status'] = 'poor'
            status_emoji = '🔴'
        
        # عرض النتائج
        self.stdout.write(f'\n   {status_emoji} الحالة العامة: {health["status"]} ({health["score"]}/100)')
        
        for check in health['checks']:
            icon = {'pass': '✅', 'warning': '⚠️', 'fail': '❌'}[check['status']]
            self.stdout.write(f'   {icon} {check["name"]}: {check["message"]}')
        
        return health

    def show_stats(self):
        """عرض إحصائيات الأداء"""
        self.stdout.write('\n   📈 إحصائيات الأداء...')
        
        stats = {
            'database': {},
            'tables': [],
            'queries': {}
        }
        
        db_settings = settings.DATABASES['default']
        is_sqlite = 'sqlite' in db_settings.get('ENGINE', '')
        
        with connection.cursor() as cursor:
            if is_sqlite:
                # إحصائيات SQLite
                cursor.execute('PRAGMA page_size')
                page_size = cursor.fetchone()[0]
                
                cursor.execute('PRAGMA page_count')
                page_count = cursor.fetchone()[0]
                
                cursor.execute('PRAGMA cache_size')
                cache_size = cursor.fetchone()[0]
                
                stats['database'] = {
                    'page_size': page_size,
                    'page_count': page_count,
                    'cache_size_pages': abs(cache_size),
                    'cache_size_mb': abs(cache_size) * page_size / (1024 * 1024)
                }
                
                # أكبر 10 جداول
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = cursor.fetchall()
                
                table_stats = []
                for (table,) in tables:
                    try:
                        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                        count = cursor.fetchone()[0]
                        table_stats.append({'name': table, 'rows': count})
                    except Exception:
                        pass
                
                stats['tables'] = sorted(table_stats, key=lambda x: x['rows'], reverse=True)[:10]
        
        # عرض الإحصائيات
        self.stdout.write(f'\n   📊 إحصائيات قاعدة البيانات:')
        self.stdout.write(f'      • حجم الصفحة: {stats["database"].get("page_size", "N/A")} bytes')
        self.stdout.write(f'      • عدد الصفحات: {stats["database"].get("page_count", "N/A"):,}')
        self.stdout.write(f'      • حجم الكاش: {stats["database"].get("cache_size_mb", "N/A"):.2f} MB')
        
        self.stdout.write(f'\n   📋 أكبر 10 جداول:')
        for table in stats['tables']:
            self.stdout.write(f'      • {table["name"]}: {table["rows"]:,} سجل')
        
        return stats

    def show_connection_info(self):
        """عرض معلومات الاتصال"""
        self.stdout.write('\n   🔌 معلومات الاتصال...')
        
        db_settings = settings.DATABASES['default']
        
        info = {
            'engine': db_settings.get('ENGINE', ''),
            'name': db_settings.get('NAME', ''),
            'host': db_settings.get('HOST', 'localhost'),
            'port': db_settings.get('PORT', ''),
            'user': db_settings.get('USER', ''),
        }
        
        is_sqlite = 'sqlite' in info['engine']
        
        if is_sqlite:
            info['type'] = 'SQLite'
            if os.path.exists(info['name']):
                info['file_size'] = os.path.getsize(info['name'])
                info['file_size_mb'] = info['file_size'] / (1024 * 1024)
        else:
            info['type'] = 'PostgreSQL' if 'postgresql' in info['engine'] else 'MySQL'
        
        self.stdout.write(f'\n   📁 نوع قاعدة البيانات: {info["type"]}')
        
        if is_sqlite:
            self.stdout.write(f'   📄 الملف: {info["name"]}')
            self.stdout.write(f'   📏 الحجم: {info.get("file_size_mb", 0):.2f} MB')
        else:
            self.stdout.write(f'   🖥️ المضيف: {info["host"]}:{info["port"]}')
            self.stdout.write(f'   👤 المستخدم: {info["user"]}')
            self.stdout.write(f'   📛 اسم القاعدة: {info["name"]}')
        
        return info

    def analyze_slow_queries(self):
        """تحليل الاستعلامات البطيئة"""
        self.stdout.write('\n   ⏱️ تحليل الاستعلامات البطيئة...')
        
        # اختبار مجموعة من الاستعلامات الشائعة
        test_queries = [
            ("جميع الفواتير", "SELECT * FROM sales_invoice"),
            ("فواتير آخر 30 يوم", "SELECT * FROM sales_invoice WHERE date >= date('now', '-30 days')"),
            ("قيود غير مرحلة", "SELECT * FROM accounting_journalentry WHERE is_posted = 0"),
            ("أرصدة المخزون", "SELECT product_id, SUM(quantity) as total FROM inventory_stock GROUP BY product_id"),
            ("العملاء النشطين", "SELECT * FROM partners_customer WHERE is_active = 1"),
            ("حضور الموظفين", "SELECT * FROM hr_attendance ORDER BY date DESC LIMIT 1000"),
            ("حركات المخزون", "SELECT * FROM inventory_stockmovement ORDER BY date DESC LIMIT 500"),
            ("بنود الفواتير", "SELECT i.*, p.name FROM sales_invoiceitem i LEFT JOIN inventory_product p ON i.product_id = p.id"),
        ]
        
        slow_queries = []
        
        with connection.cursor() as cursor:
            for name, query in test_queries:
                try:
                    start = time.time()
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    elapsed = time.time() - start
                    
                    result = {
                        'name': name,
                        'query': query,
                        'time_seconds': round(elapsed, 4),
                        'time_ms': round(elapsed * 1000, 2),
                        'row_count': len(rows),
                        'is_slow': elapsed > self.threshold
                    }
                    
                    slow_queries.append(result)
                    
                except Exception as e:
                    slow_queries.append({
                        'name': name,
                        'query': query,
                        'error': str(e)
                    })
        
        # ترتيب حسب الوقت
        slow_queries.sort(key=lambda x: x.get('time_seconds', 0), reverse=True)
        
        # عرض النتائج
        self.stdout.write(f'\n   📊 نتائج اختبار الأداء (العتبة: {self.threshold}s):')
        
        for q in slow_queries:
            if 'error' in q:
                self.stdout.write(f'   ❓ {q["name"]}: خطأ - {q["error"][:50]}')
            else:
                icon = '🔴' if q['is_slow'] else '🟢'
                self.stdout.write(
                    f'   {icon} {q["name"]}: {q["time_ms"]} ms '
                    f'({q["row_count"]} سجل)'
                )
        
        # إحصائيات
        successful = [q for q in slow_queries if 'time_seconds' in q]
        if successful:
            avg_time = sum(q['time_seconds'] for q in successful) / len(successful)
            max_time = max(q['time_seconds'] for q in successful)
            slow_count = len([q for q in successful if q['is_slow']])
            
            self.stdout.write(f'\n   📈 ملخص:')
            self.stdout.write(f'      • متوسط الوقت: {avg_time * 1000:.2f} ms')
            self.stdout.write(f'      • أطول استعلام: {max_time * 1000:.2f} ms')
            self.stdout.write(f'      • استعلامات بطيئة: {slow_count}/{len(successful)}')
        
        return slow_queries

    def live_monitoring(self, interval=5):
        """مراقبة مباشرة"""
        self.stdout.write('\n   👁️ بدء المراقبة المباشرة...')
        self.stdout.write(f'   ⏰ فترة التحديث: {interval} ثانية')
        self.stdout.write('   اضغط Ctrl+C للإيقاف\n')
        
        try:
            while True:
                # مسح الشاشة (Windows)
                os.system('cls' if os.name == 'nt' else 'clear')
                
                self.stdout.write(self.style.SUCCESS('=' * 60))
                self.stdout.write(self.style.SUCCESS('   📊 مراقبة قاعدة البيانات - ' + datetime.now().strftime('%H:%M:%S')))
                self.stdout.write(self.style.SUCCESS('=' * 60))
                
                # صحة القاعدة
                health = self.check_health()
                
                # إحصائيات سريعة
                with connection.cursor() as cursor:
                    # عدد الاستعلامات النشطة (للقواعد التي تدعم ذلك)
                    db_settings = settings.DATABASES['default']
                    if 'sqlite' in db_settings.get('ENGINE', ''):
                        db_path = db_settings.get('NAME')
                        if os.path.exists(db_path):
                            size_mb = os.path.getsize(db_path) / (1024 * 1024)
                            self.stdout.write(f'\n   💾 حجم القاعدة: {size_mb:.2f} MB')
                
                self.stdout.write(f'\n   ⏰ التحديث التالي في {interval} ثانية...')
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write('\n\n   ⏹️ تم إيقاف المراقبة')

    def export_report(self, report, filepath):
        """تصدير التقرير"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        self.stdout.write(f'\n   ✅ تم تصدير التقرير إلى: {filepath}')
