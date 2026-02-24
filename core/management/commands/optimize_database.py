"""
أمر إدارة لتحسين قاعدة البيانات
يقوم بفحص وتحسين الأداء وإضافة الفهارس المفقودة

الاستخدام:
    python manage.py optimize_database
    python manage.py optimize_database --analyze
    python manage.py optimize_database --vacuum
    python manage.py optimize_database --reindex
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.apps import apps
from django.utils import timezone
import time


class Command(BaseCommand):
    help = 'تحسين قاعدة البيانات وتحليل الأداء'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='تحليل استخدام الجداول والفهارس',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='تنظيف وضغط قاعدة البيانات (SQLite فقط)',
        )
        parser.add_argument(
            '--reindex',
            action='store_true',
            help='إعادة بناء الفهارس',
        )
        parser.add_argument(
            '--check-indexes',
            action='store_true',
            help='فحص الفهارس المفقودة المقترحة',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='عرض إحصائيات قاعدة البيانات',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='تنفيذ جميع التحسينات',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING('تحسين قاعدة البيانات - Tony ERP'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60 + '\n'))
        
        start_time = time.time()
        
        if options['full']:
            options['analyze'] = True
            options['vacuum'] = True
            options['reindex'] = True
            options['check_indexes'] = True
            options['stats'] = True
        
        if options['stats']:
            self.show_statistics()
        
        if options['analyze']:
            self.analyze_database()
        
        if options['check_indexes']:
            self.check_missing_indexes()
        
        if options['vacuum']:
            self.vacuum_database()
        
        if options['reindex']:
            self.reindex_database()
        
        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f'\n✓ اكتمل في {elapsed:.2f} ثانية'))

    def show_statistics(self):
        """عرض إحصائيات قاعدة البيانات"""
        self.stdout.write(self.style.HTTP_INFO('\n📊 إحصائيات قاعدة البيانات:'))
        self.stdout.write('-' * 50)
        
        # إحصائيات الجداول
        vendor = connection.vendor
        
        if vendor == 'sqlite':
            with connection.cursor() as cursor:
                # حجم قاعدة البيانات
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();")
                size = cursor.fetchone()[0]
                self.stdout.write(f"  حجم القاعدة: {size / 1024 / 1024:.2f} MB")
                
                # عدد الجداول
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
                table_count = cursor.fetchone()[0]
                self.stdout.write(f"  عدد الجداول: {table_count}")
                
                # عدد الفهارس
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='index';")
                index_count = cursor.fetchone()[0]
                self.stdout.write(f"  عدد الفهارس: {index_count}")
        
        # إحصائيات النماذج
        self.stdout.write('\n📋 إحصائيات النماذج الرئيسية:')
        self.stdout.write('-' * 50)
        
        main_models = [
            ('accounting.Account', 'الحسابات'),
            ('accounting.JournalEntry', 'القيود المحاسبية'),
            ('inventory.Product', 'المنتجات'),
            ('inventory.Stock', 'المخزون'),
            ('sales.Invoice', 'الفواتير'),
            ('purchases.PurchaseBill', 'فواتير الشراء'),
            ('hr.Employee', 'الموظفين'),
            ('partners.Customer', 'العملاء'),
            ('partners.Supplier', 'الموردين'),
        ]
        
        for model_path, name in main_models:
            try:
                Model = apps.get_model(model_path)
                count = Model.objects.count()
                self.stdout.write(f"  {name}: {count:,}")
            except Exception:
                pass

    def analyze_database(self):
        """تحليل قاعدة البيانات"""
        self.stdout.write(self.style.HTTP_INFO('\n🔍 تحليل قاعدة البيانات:'))
        self.stdout.write('-' * 50)
        
        vendor = connection.vendor
        
        if vendor == 'sqlite':
            with connection.cursor() as cursor:
                self.stdout.write('  تشغيل ANALYZE...')
                cursor.execute('ANALYZE;')
                self.stdout.write(self.style.SUCCESS('  ✓ تم تحليل القاعدة'))
        elif vendor == 'postgresql':
            with connection.cursor() as cursor:
                self.stdout.write('  تشغيل ANALYZE...')
                cursor.execute('ANALYZE;')
                self.stdout.write(self.style.SUCCESS('  ✓ تم تحليل القاعدة'))
        elif vendor == 'mysql':
            with connection.cursor() as cursor:
                self.stdout.write('  تحليل الجداول...')
                cursor.execute("SHOW TABLES;")
                tables = cursor.fetchall()
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f'ANALYZE TABLE {table_name};')
                self.stdout.write(self.style.SUCCESS(f'  ✓ تم تحليل {len(tables)} جدول'))

    def check_missing_indexes(self):
        """فحص الفهارس المفقودة المقترحة"""
        self.stdout.write(self.style.HTTP_INFO('\n🔎 فحص الفهارس المقترحة:'))
        self.stdout.write('-' * 50)
        
        # قائمة الفهارس المقترحة للحقول الأكثر استخداماً
        suggested_indexes = [
            ('accounting_journalentry', ['date', 'is_posted']),
            ('accounting_journalentry', ['entry_type']),
            ('sales_invoice', ['customer_id', 'date']),
            ('sales_invoice', ['due_date']),
            ('purchases_purchasebill', ['supplier_id', 'date']),
            ('inventory_stock', ['product_id', 'location_id']),
            ('inventory_product', ['sku']),
            ('inventory_product', ['barcode']),
            ('hr_employee', ['status']),
            ('hr_employee', ['department_id']),
            ('partners_customer', ['name']),
            ('partners_supplier', ['name']),
        ]
        
        existing_indexes = self._get_existing_indexes()
        missing_count = 0
        
        for table, columns in suggested_indexes:
            index_name = f"idx_{table}_{'_'.join(columns)}"
            if index_name not in existing_indexes:
                self.stdout.write(self.style.WARNING(f"  ⚠ فهرس مقترح: {table} ({', '.join(columns)})"))
                missing_count += 1
        
        if missing_count == 0:
            self.stdout.write(self.style.SUCCESS('  ✓ جميع الفهارس المقترحة موجودة'))
        else:
            self.stdout.write(f'\n  إجمالي الفهارس المفقودة: {missing_count}')

    def _get_existing_indexes(self):
        """الحصول على قائمة الفهارس الموجودة"""
        indexes = set()
        vendor = connection.vendor
        
        with connection.cursor() as cursor:
            if vendor == 'sqlite':
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
                indexes = {row[0] for row in cursor.fetchall()}
            elif vendor == 'postgresql':
                cursor.execute("""
                    SELECT indexname FROM pg_indexes 
                    WHERE schemaname = 'public';
                """)
                indexes = {row[0] for row in cursor.fetchall()}
        
        return indexes

    def vacuum_database(self):
        """تنظيف وضغط قاعدة البيانات"""
        self.stdout.write(self.style.HTTP_INFO('\n🧹 تنظيف قاعدة البيانات:'))
        self.stdout.write('-' * 50)
        
        vendor = connection.vendor
        
        if vendor == 'sqlite':
            with connection.cursor() as cursor:
                # الحجم قبل التنظيف
                cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size();")
                size_before = cursor.fetchone()[0]
                
                self.stdout.write('  تشغيل VACUUM...')
                cursor.execute('VACUUM;')
                
                # الحجم بعد التنظيف
                cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size();")
                size_after = cursor.fetchone()[0]
                
                saved = size_before - size_after
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ تم تنظيف القاعدة (توفير {saved / 1024:.1f} KB)'
                ))
        elif vendor == 'postgresql':
            with connection.cursor() as cursor:
                self.stdout.write('  تشغيل VACUUM ANALYZE...')
                cursor.execute('VACUUM ANALYZE;')
                self.stdout.write(self.style.SUCCESS('  ✓ تم تنظيف القاعدة'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ VACUUM غير مدعوم لهذا النوع من القواعد'))

    def reindex_database(self):
        """إعادة بناء الفهارس"""
        self.stdout.write(self.style.HTTP_INFO('\n🔄 إعادة بناء الفهارس:'))
        self.stdout.write('-' * 50)
        
        vendor = connection.vendor
        
        if vendor == 'sqlite':
            with connection.cursor() as cursor:
                self.stdout.write('  تشغيل REINDEX...')
                cursor.execute('REINDEX;')
                self.stdout.write(self.style.SUCCESS('  ✓ تم إعادة بناء الفهارس'))
        elif vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public';")
                indexes = cursor.fetchall()
                self.stdout.write(f'  إعادة بناء {len(indexes)} فهرس...')
                cursor.execute('REINDEX DATABASE;')
                self.stdout.write(self.style.SUCCESS('  ✓ تم إعادة بناء الفهارس'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ REINDEX غير مدعوم لهذا النوع من القواعد'))
