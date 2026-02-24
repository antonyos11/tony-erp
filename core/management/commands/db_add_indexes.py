# -*- coding: utf-8 -*-
"""
أداة إضافة الفهارس
Database Index Management Tool
"""

import time
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'إضافة فهارس الأداء للجداول'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='فحص الفهارس المفقودة فقط',
        )
        parser.add_argument(
            '--create',
            action='store_true',
            help='إنشاء الفهارس المفقودة',
        )
        parser.add_argument(
            '--drop',
            type=str,
            help='حذف فهرس محدد',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='عرض جميع الفهارس',
        )
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='تحليل استخدام الفهارس',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('   📇 إدارة فهارس قاعدة البيانات'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if options['list']:
            self.list_indexes()
        elif options['check']:
            self.check_missing_indexes()
        elif options['create']:
            self.create_missing_indexes()
        elif options['drop']:
            self.drop_index(options['drop'])
        elif options['analyze']:
            self.analyze_indexes()
        else:
            self.check_missing_indexes()

    def get_suggested_indexes(self):
        """قائمة الفهارس المقترحة"""
        return [
            # المحاسبة
            {
                'name': 'idx_je_date_posted',
                'table': 'accounting_journalentry',
                'columns': ['date', 'is_posted'],
                'description': 'تسريع البحث في القيود حسب التاريخ والحالة'
            },
            {
                'name': 'idx_je_entry_type',
                'table': 'accounting_journalentry',
                'columns': ['entry_type'],
                'description': 'تسريع الفلترة حسب نوع القيد'
            },
            {
                'name': 'idx_je_user_date',
                'table': 'accounting_journalentry',
                'columns': ['created_by_id', 'date'],
                'description': 'تسريع البحث حسب المستخدم والتاريخ'
            },
            {
                'name': 'idx_acc_type',
                'table': 'accounting_account',
                'columns': ['account_type'],
                'description': 'تسريع الفلترة حسب نوع الحساب'
            },
            {
                'name': 'idx_acc_parent',
                'table': 'accounting_account',
                'columns': ['parent_id'],
                'description': 'تسريع استعلامات الشجرة'
            },
            
            # المبيعات
            {
                'name': 'idx_inv_customer_date',
                'table': 'sales_invoice',
                'columns': ['customer_id', 'date'],
                'description': 'تسريع البحث في فواتير العميل'
            },
            {
                'name': 'idx_inv_due_date',
                'table': 'sales_invoice',
                'columns': ['due_date'],
                'description': 'تسريع البحث في الفواتير المستحقة'
            },
            {
                'name': 'idx_inv_status',
                'table': 'sales_invoice',
                'columns': ['status'],
                'description': 'تسريع الفلترة حسب الحالة'
            },
            {
                'name': 'idx_invitem_invoice',
                'table': 'sales_invoiceitem',
                'columns': ['invoice_id'],
                'description': 'تسريع جلب بنود الفاتورة'
            },
            {
                'name': 'idx_invitem_product',
                'table': 'sales_invoiceitem',
                'columns': ['product_id'],
                'description': 'تسريع البحث في المنتجات المباعة'
            },
            
            # المشتريات
            {
                'name': 'idx_pb_supplier_date',
                'table': 'purchases_purchasebill',
                'columns': ['supplier_id', 'date'],
                'description': 'تسريع البحث في فواتير المورد'
            },
            {
                'name': 'idx_pb_status',
                'table': 'purchases_purchasebill',
                'columns': ['status'],
                'description': 'تسريع الفلترة حسب الحالة'
            },
            
            # المخزون
            {
                'name': 'idx_stock_prod_loc',
                'table': 'inventory_stock',
                'columns': ['product_id', 'location_id'],
                'description': 'تسريع جلب أرصدة المخزون'
            },
            {
                'name': 'idx_prod_sku',
                'table': 'inventory_product',
                'columns': ['sku'],
                'description': 'تسريع البحث بالـ SKU'
            },
            {
                'name': 'idx_prod_barcode',
                'table': 'inventory_product',
                'columns': ['barcode'],
                'description': 'تسريع البحث بالباركود'
            },
            {
                'name': 'idx_prod_category',
                'table': 'inventory_product',
                'columns': ['category_id'],
                'description': 'تسريع الفلترة حسب الفئة'
            },
            {
                'name': 'idx_sm_prod_date',
                'table': 'inventory_stockmovement',
                'columns': ['product_id', 'date'],
                'description': 'تسريع تقارير حركة المخزون'
            },
            
            # الموارد البشرية
            {
                'name': 'idx_emp_status',
                'table': 'hr_employee',
                'columns': ['status'],
                'description': 'تسريع الفلترة حسب حالة الموظف'
            },
            {
                'name': 'idx_emp_dept',
                'table': 'hr_employee',
                'columns': ['department_id'],
                'description': 'تسريع الفلترة حسب القسم'
            },
            {
                'name': 'idx_att_emp_date',
                'table': 'hr_attendance',
                'columns': ['employee_id', 'date'],
                'description': 'تسريع البحث في سجلات الحضور'
            },
            
            # الشركاء
            {
                'name': 'idx_cust_name',
                'table': 'partners_customer',
                'columns': ['name'],
                'description': 'تسريع البحث في أسماء العملاء'
            },
            {
                'name': 'idx_supp_name',
                'table': 'partners_supplier',
                'columns': ['name'],
                'description': 'تسريع البحث في أسماء الموردين'
            },
        ]

    def list_indexes(self):
        """عرض جميع الفهارس"""
        self.stdout.write('\n   📋 قائمة الفهارس الموجودة:')
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name, tbl_name, sql 
                FROM sqlite_master 
                WHERE type='index' AND sql IS NOT NULL
                ORDER BY tbl_name, name
            """)
            
            indexes = cursor.fetchall()
            
            current_table = None
            for name, table, sql in indexes:
                if table != current_table:
                    self.stdout.write(f'\n   📊 {table}:')
                    current_table = table
                
                # استخراج الأعمدة
                cols = sql.split('(')[-1].replace(')', '').strip()
                self.stdout.write(f'      • {name}: ({cols})')
        
        self.stdout.write(f'\n   📊 إجمالي الفهارس: {len(indexes)}')

    def check_missing_indexes(self):
        """فحص الفهارس المفقودة"""
        self.stdout.write('\n   🔍 فحص الفهارس المفقودة...')
        
        suggested = self.get_suggested_indexes()
        missing = []
        existing = []
        
        with connection.cursor() as cursor:
            for idx in suggested:
                # تحقق من وجود الجدول
                cursor.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='{idx['table']}'
                """)
                if not cursor.fetchone():
                    continue
                
                # تحقق من وجود الفهرس
                cursor.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='{idx['name']}'
                """)
                
                if cursor.fetchone():
                    existing.append(idx)
                else:
                    # تحقق من وجود فهرس مشابه
                    cols_str = ', '.join(idx['columns'])
                    cursor.execute(f"""
                        SELECT name, sql FROM sqlite_master 
                        WHERE type='index' AND tbl_name='{idx['table']}' AND sql IS NOT NULL
                    """)
                    
                    has_similar = False
                    for name, sql in cursor.fetchall():
                        if sql and all(col in sql for col in idx['columns']):
                            has_similar = True
                            break
                    
                    if not has_similar:
                        missing.append(idx)
        
        self.stdout.write(f'\n   ✅ فهارس موجودة: {len(existing)}')
        self.stdout.write(f'   ⚠️ فهارس مفقودة: {len(missing)}')
        
        if missing:
            self.stdout.write('\n   📝 الفهارس المفقودة:')
            for idx in missing:
                cols = ', '.join(idx['columns'])
                self.stdout.write(f'      • {idx["table"]}: {cols}')
                self.stdout.write(f'        💡 {idx["description"]}')
        
        return missing

    def create_missing_indexes(self):
        """إنشاء الفهارس المفقودة"""
        missing = self.check_missing_indexes()
        
        if not missing:
            self.stdout.write('\n   ✅ جميع الفهارس موجودة!')
            return
        
        self.stdout.write(f'\n   🔨 إنشاء {len(missing)} فهرس...')
        
        created = 0
        failed = 0
        
        with connection.cursor() as cursor:
            for idx in missing:
                cols = ', '.join(idx['columns'])
                sql = f'CREATE INDEX IF NOT EXISTS {idx["name"]} ON {idx["table"]} ({cols})'
                
                try:
                    start = time.time()
                    cursor.execute(sql)
                    elapsed = (time.time() - start) * 1000
                    
                    created += 1
                    self.stdout.write(f'   ✅ {idx["name"]} ({elapsed:.0f}ms)')
                    
                except Exception as e:
                    failed += 1
                    self.stdout.write(f'   ❌ {idx["name"]}: {e}')
        
        self.stdout.write(f'\n   📊 النتيجة: {created} نجح، {failed} فشل')

    def drop_index(self, index_name):
        """حذف فهرس"""
        self.stdout.write(f'\n   🗑️ حذف الفهرس: {index_name}')
        
        with connection.cursor() as cursor:
            try:
                cursor.execute(f'DROP INDEX IF EXISTS {index_name}')
                self.stdout.write('   ✅ تم الحذف بنجاح')
            except Exception as e:
                self.stdout.write(f'   ❌ فشل الحذف: {e}')

    def analyze_indexes(self):
        """تحليل استخدام الفهارس"""
        self.stdout.write('\n   📊 تحليل الفهارس...')
        
        with connection.cursor() as cursor:
            # إحصائيات عامة
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='index' AND sql IS NOT NULL
            """)
            total_indexes = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            total_tables = cursor.fetchone()[0]
            
            self.stdout.write(f'\n   📈 إحصائيات عامة:')
            self.stdout.write(f'      • إجمالي الجداول: {total_tables}')
            self.stdout.write(f'      • إجمالي الفهارس: {total_indexes}')
            self.stdout.write(f'      • معدل الفهارس/جدول: {total_indexes/total_tables:.2f}')
            
            # تحليل حسب الجدول
            cursor.execute("""
                SELECT tbl_name, COUNT(*) as cnt
                FROM sqlite_master 
                WHERE type='index' AND sql IS NOT NULL
                GROUP BY tbl_name
                ORDER BY cnt DESC
                LIMIT 10
            """)
            
            self.stdout.write(f'\n   📋 الجداول الأكثر فهرسة:')
            for table, count in cursor.fetchall():
                self.stdout.write(f'      • {table}: {count} فهرس')
            
            # اختبار أداء الفهارس
            self.stdout.write(f'\n   ⏱️ اختبار أداء الفهارس:')
            
            test_queries = [
                ('sales_invoice', 'SELECT * FROM sales_invoice WHERE status = "paid" LIMIT 100'),
                ('inventory_product', 'SELECT * FROM inventory_product WHERE sku = "TEST" LIMIT 1'),
                ('hr_employee', 'SELECT * FROM hr_employee WHERE status = "active" LIMIT 50'),
            ]
            
            for table, query in test_queries:
                try:
                    # مع فهرس
                    start = time.time()
                    cursor.execute(query)
                    cursor.fetchall()
                    with_index = (time.time() - start) * 1000
                    
                    self.stdout.write(f'      • {table}: {with_index:.2f}ms')
                except Exception:
                    pass
