#!/usr/bin/env python
"""
مراقب الأداء - Tony ERP
========================
سكربت لمراقبة أداء النظام وقياس سرعة الصفحات والاستعلامات.

الاستخدام:
    python performance_monitor.py              # فحص أداء كامل
    python performance_monitor.py --quick      # فحص سريع
    python performance_monitor.py --db         # فحص قاعدة البيانات فقط
"""

import os
import sys
import time
import django
import requests
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.db import connection
from django.db.models import Count


class PerformanceMonitor:
    """مراقب أداء النظام"""
    
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'pages': [],
            'db_queries': [],
            'summary': {}
        }
    
    def log(self, message, status='info'):
        """طباعة رسالة"""
        icons = {
            'info': '📋',
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'time': '⏱️'
        }
        print(f"{icons.get(status, '•')} {message}")
    
    # ==========================================
    # قياس سرعة الصفحات
    # ==========================================
    def measure_page_speed(self, url, name, num_requests=3):
        """قياس سرعة تحميل صفحة"""
        
        times = []
        errors = 0
        
        for _ in range(num_requests):
            try:
                start = time.time()
                response = self.session.get(f"{self.base_url}{url}", timeout=30)
                elapsed = (time.time() - start) * 1000  # بالمللي ثانية
                
                if response.status_code == 200:
                    times.append(elapsed)
                else:
                    errors += 1
                    
            except Exception:
                errors += 1
        
        if times:
            result = {
                'name': name,
                'url': url,
                'avg_time': statistics.mean(times),
                'min_time': min(times),
                'max_time': max(times),
                'errors': errors,
                'status': 'ok' if errors == 0 else 'warning'
            }
        else:
            result = {
                'name': name,
                'url': url,
                'avg_time': 0,
                'min_time': 0,
                'max_time': 0,
                'errors': errors,
                'status': 'error'
            }
        
        self.results['pages'].append(result)
        return result
    
    def benchmark_pages(self):
        """قياس سرعة الصفحات الرئيسية"""
        
        self.log("قياس سرعة الصفحات الرئيسية...", 'time')
        print("-" * 60)
        
        pages = [
            ('/', 'الصفحة الرئيسية'),
            ('/accounting/', 'المحاسبة'),
            ('/inventory/', 'المخزون'),
            ('/inventory/products/', 'قائمة المنتجات'),
            ('/sales/', 'المبيعات'),
            ('/sales/invoices/', 'الفواتير'),
            ('/purchases/', 'المشتريات'),
            ('/hr/', 'الموارد البشرية'),
            ('/crm/', 'إدارة العملاء'),
            ('/production/', 'الإنتاج'),
            ('/pos/', 'نقاط البيع'),
        ]
        
        for url, name in pages:
            result = self.measure_page_speed(url, name)
            
            if result['status'] == 'ok':
                speed_indicator = '🟢' if result['avg_time'] < 500 else '🟡' if result['avg_time'] < 1000 else '🔴'
                self.log(f"{speed_indicator} {name}: {result['avg_time']:.0f}ms (min: {result['min_time']:.0f}, max: {result['max_time']:.0f})")
            elif result['status'] == 'warning':
                self.log(f"🟡 {name}: {result['errors']} أخطاء", 'warning')
            else:
                self.log(f"🔴 {name}: غير متاح", 'error')
        
        print("-" * 60)
    
    # ==========================================
    # فحص قاعدة البيانات
    # ==========================================
    def benchmark_database(self):
        """فحص أداء قاعدة البيانات"""
        
        self.log("فحص أداء قاعدة البيانات...", 'time')
        print("-" * 60)
        
        from inventory.models import Product, Stock
        from partners.models import Customer
        from sales.models import Invoice
        from accounting.models import JournalEntry
        
        queries = [
            ('عدد المنتجات', lambda: Product.objects.count()),
            ('عدد العملاء', lambda: Customer.objects.count()),
            ('عدد الفواتير', lambda: Invoice.objects.count()),
            ('عدد القيود', lambda: JournalEntry.objects.count()),
            ('مخزون المنتجات', lambda: Stock.objects.select_related('product', 'location').count()),
            ('منتجات مع فئات', lambda: list(Product.objects.select_related('category')[:100])),
            ('تجميع المخزون', lambda: Stock.objects.values('location').annotate(total=Count('id'))),
        ]
        
        for name, query_func in queries:
            try:
                start = time.time()
                result = query_func()
                elapsed = (time.time() - start) * 1000
                
                count = result if isinstance(result, int) else len(list(result)) if hasattr(result, '__len__') else 'N/A'
                
                speed_indicator = '🟢' if elapsed < 50 else '🟡' if elapsed < 200 else '🔴'
                self.log(f"{speed_indicator} {name}: {elapsed:.1f}ms (النتيجة: {count})")
                
                self.results['db_queries'].append({
                    'name': name,
                    'time': elapsed,
                    'result': count
                })
                
            except Exception as e:
                self.log(f"🔴 {name}: خطأ - {e}", 'error')
        
        print("-" * 60)
    
    # ==========================================
    # فحص حجم قاعدة البيانات
    # ==========================================
    def check_database_size(self):
        """فحص حجم قاعدة البيانات والجداول"""
        
        self.log("فحص حجم قاعدة البيانات...", 'info')
        print("-" * 60)
        
        from pathlib import Path
        
        db_path = Path('db.sqlite3')
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            self.log(f"📊 حجم قاعدة البيانات: {size_mb:.2f} MB")
        
        # عدد السجلات في الجداول الرئيسية
        from django.apps import apps
        
        table_counts = []
        for model in apps.get_models():
            try:
                count = model.objects.count()
                if count > 0:
                    table_counts.append((model._meta.verbose_name_plural, count))
            except Exception:
                pass
        
        # ترتيب حسب العدد
        table_counts.sort(key=lambda x: x[1], reverse=True)
        
        self.log("أكبر 10 جداول:")
        for name, count in table_counts[:10]:
            self.log(f"   - {name}: {count:,} سجل")
        
        print("-" * 60)
    
    # ==========================================
    # اختبار الحمل
    # ==========================================
    def load_test(self, url='/', num_requests=20, concurrency=5):
        """اختبار حمل بسيط"""
        
        self.log(f"اختبار الحمل: {num_requests} طلب مع {concurrency} متزامن...", 'time')
        print("-" * 60)
        
        times = []
        errors = 0
        
        def make_request(i):
            try:
                start = time.time()
                response = self.session.get(f"{self.base_url}{url}", timeout=30)
                elapsed = (time.time() - start) * 1000
                return ('ok', elapsed, response.status_code)
            except Exception as e:
                return ('error', 0, str(e))
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            
            for future in as_completed(futures):
                status, elapsed, code = future.result()
                if status == 'ok':
                    times.append(elapsed)
                else:
                    errors += 1
        
        if times:
            self.log(f"📊 متوسط الاستجابة: {statistics.mean(times):.0f}ms")
            self.log(f"📊 أقل استجابة: {min(times):.0f}ms")
            self.log(f"📊 أعلى استجابة: {max(times):.0f}ms")
            self.log(f"📊 معدل النجاح: {(len(times) / num_requests) * 100:.1f}%")
            
            if errors > 0:
                self.log(f"⚠️ عدد الأخطاء: {errors}", 'warning')
        else:
            self.log("❌ فشل جميع الطلبات", 'error')
        
        print("-" * 60)
    
    # ==========================================
    # تقرير الأداء الشامل
    # ==========================================
    def generate_report(self):
        """إنشاء تقرير الأداء"""
        
        print("\n" + "=" * 70)
        print("📊 تقرير الأداء الشامل")
        print("=" * 70)
        
        # ملخص الصفحات
        page_times = [p['avg_time'] for p in self.results['pages'] if p['avg_time'] > 0]
        if page_times:
            avg_page = statistics.mean(page_times)
            print(f"\n⏱️ أداء الصفحات:")
            print(f"   - متوسط الاستجابة: {avg_page:.0f}ms")
            print(f"   - أسرع صفحة: {min(page_times):.0f}ms")
            print(f"   - أبطأ صفحة: {max(page_times):.0f}ms")
            
            # الصفحات البطيئة
            slow_pages = [p for p in self.results['pages'] if p['avg_time'] > 1000]
            if slow_pages:
                print(f"\n   ⚠️ صفحات بطيئة (> 1 ثانية):")
                for p in slow_pages:
                    print(f"      - {p['name']}: {p['avg_time']:.0f}ms")
        
        # ملخص قاعدة البيانات
        db_times = [q['time'] for q in self.results['db_queries']]
        if db_times:
            print(f"\n💾 أداء قاعدة البيانات:")
            print(f"   - متوسط الاستعلام: {statistics.mean(db_times):.1f}ms")
            print(f"   - أسرع استعلام: {min(db_times):.1f}ms")
            print(f"   - أبطأ استعلام: {max(db_times):.1f}ms")
        
        # التقييم العام
        print("\n" + "=" * 70)
        
        overall_avg = statistics.mean(page_times) if page_times else 0
        if overall_avg < 500:
            grade = '🟢 ممتاز'
        elif overall_avg < 1000:
            grade = '🟡 جيد'
        elif overall_avg < 2000:
            grade = '🟠 مقبول'
        else:
            grade = '🔴 يحتاج تحسين'
        
        print(f"📈 التقييم العام: {grade}")
        print(f"⏰ تاريخ الفحص: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")
    
    # ==========================================
    # التشغيل الرئيسي
    # ==========================================
    def run_full_check(self, quick=False):
        """فحص الأداء الكامل"""
        
        print("\n" + "=" * 70)
        print("⚡ مراقب الأداء - Tony ERP")
        print("=" * 70 + "\n")
        
        # فحص قاعدة البيانات أولاً
        self.benchmark_database()
        self.check_database_size()
        
        # فحص الصفحات (يتطلب تشغيل الخادم)
        try:
            response = self.session.get(self.base_url, timeout=5)
            if response.status_code == 200:
                self.benchmark_pages()
                
                if not quick:
                    self.load_test()
        except Exception:
            self.log("⚠️ الخادم غير متاح - تخطي فحص الصفحات", 'warning')
        
        # التقرير النهائي
        self.generate_report()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='مراقب الأداء - Tony ERP')
    parser.add_argument('--quick', '-q', action='store_true', help='فحص سريع')
    parser.add_argument('--db', '-d', action='store_true', help='فحص قاعدة البيانات فقط')
    parser.add_argument('--pages', '-p', action='store_true', help='فحص الصفحات فقط')
    parser.add_argument('--url', type=str, default='http://127.0.0.1:8000', help='رابط الخادم')
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(base_url=args.url)
    
    if args.db:
        monitor.benchmark_database()
        monitor.check_database_size()
    elif args.pages:
        monitor.benchmark_pages()
    else:
        monitor.run_full_check(quick=args.quick)


if __name__ == '__main__':
    main()
