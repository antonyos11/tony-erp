"""
اختبارات الأداء
===============
تختبر أداء النظام مع كميات كبيرة من البيانات
"""

import time
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import override_settings
from decimal import Decimal


# ===============================
# اختبارات أداء قاعدة البيانات
# ===============================

class DatabasePerformanceTestCase(TransactionTestCase):
    """اختبارات أداء قاعدة البيانات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        from inventory.models import Category
        self.user = User.objects.create_user('perf_user', 'perf@test.com', 'pass123')
        self.category = Category.objects.create(name='فئة اختبار الأداء')
    
    def test_bulk_product_creation_performance(self):
        """اختبار أداء إنشاء منتجات بكميات كبيرة"""
        from inventory.models import Product
        
        BATCH_SIZE = 100
        
        start_time = time.time()
        
        products = []
        for i in range(BATCH_SIZE):
            products.append(Product(
                name=f'منتج أداء {i}',
                sku=f'PERF-{i:05d}',
                category=self.category,
                cost=Decimal('100'),
                price=Decimal('150')
            ))
        
        Product.objects.bulk_create(products)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # يجب أن يتم الإنشاء في أقل من 5 ثوان
        self.assertLess(execution_time, 5.0, f"إنشاء {BATCH_SIZE} منتج استغرق {execution_time:.2f} ثانية")
        self.assertEqual(Product.objects.filter(sku__startswith='PERF-').count(), BATCH_SIZE)
    
    def test_bulk_stock_creation_performance(self):
        """اختبار أداء إنشاء مخزون بكميات كبيرة"""
        from inventory.models import Product, Location, Stock
        
        BATCH_SIZE = 50
        
        # إنشاء المنتجات والموقع
        products = []
        for i in range(BATCH_SIZE):
            products.append(Product(
                name=f'منتج مخزون {i}',
                sku=f'STK-{i:05d}',
                category=self.category,
                cost=Decimal('50')
            ))
        Product.objects.bulk_create(products)
        
        location = Location.objects.create(name='مخزن أداء', code='WH-PERF')
        
        created_products = Product.objects.filter(sku__startswith='STK-')
        
        start_time = time.time()
        
        stocks = []
        for product in created_products:
            stocks.append(Stock(
                product=product,
                location=location,
                quantity=Decimal('100')
            ))
        
        Stock.objects.bulk_create(stocks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 3.0, f"إنشاء {BATCH_SIZE} سجل مخزون استغرق {execution_time:.2f} ثانية")


class QueryPerformanceTestCase(TestCase):
    """اختبارات أداء الاستعلامات"""
    
    @classmethod
    def setUpTestData(cls):
        """إعداد بيانات الاختبار مرة واحدة"""
        from inventory.models import Product, Category
        
        cls.user = User.objects.create_user('query_user', 'query@test.com', 'pass123')
        cls.category = Category.objects.create(name='فئة استعلام')
        
        BATCH_SIZE = 100
        products = []
        for i in range(BATCH_SIZE):
            products.append(Product(
                name=f'منتج استعلام {i}',
                sku=f'QRY-{i:05d}',
                category=cls.category,
                cost=Decimal(str(50 + i)),
                price=Decimal(str(100 + i))
            ))
        Product.objects.bulk_create(products)
    
    def test_product_filter_performance(self):
        """اختبار أداء فلترة المنتجات"""
        from inventory.models import Product
        
        start_time = time.time()
        
        # فلترة المنتجات
        products = list(Product.objects.filter(
            sku__startswith='QRY-',
            cost__gte=Decimal('50'),
            price__lte=Decimal('200')
        ))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0, f"فلترة المنتجات استغرقت {execution_time:.2f} ثانية")
        self.assertGreater(len(products), 0)
    
    def test_product_aggregation_performance(self):
        """اختبار أداء التجميع"""
        from inventory.models import Product
        from django.db.models import Sum, Avg, Count, Max, Min
        
        start_time = time.time()
        
        aggregates = Product.objects.filter(
            sku__startswith='QRY-'
        ).aggregate(
            total_count=Count('id'),
            avg_cost=Avg('cost'),
            max_price=Max('price'),
            min_cost=Min('cost')
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0, f"التجميع استغرق {execution_time:.2f} ثانية")
        self.assertEqual(aggregates['total_count'], 100)
    
    def test_select_related_performance(self):
        """اختبار أداء select_related"""
        from inventory.models import Product
        
        start_time = time.time()
        
        products = list(Product.objects.filter(
            sku__startswith='QRY-'
        ).select_related('category'))
        
        # الوصول للفئة لكل منتج
        for p in products:
            _ = p.category.name
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0, f"select_related استغرق {execution_time:.2f} ثانية")


class MemoryUsageTestCase(TestCase):
    """اختبارات استخدام الذاكرة"""
    
    def test_large_queryset_iteration(self):
        """اختبار التكرار على مجموعة بيانات كبيرة"""
        from inventory.models import Product, Category
        
        category = Category.objects.create(name='فئة ذاكرة')
        
        # إنشاء منتجات
        products = []
        for i in range(50):
            products.append(Product(
                name=f'منتج ذاكرة {i}',
                sku=f'MEM-{i:05d}',
                category=category
            ))
        Product.objects.bulk_create(products)
        
        start_time = time.time()
        
        # استخدام iterator() للتوفير في الذاكرة
        count = 0
        for product in Product.objects.filter(sku__startswith='MEM-').iterator():
            count += 1
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 2.0)
        self.assertEqual(count, 50)
    
    def test_chunked_processing(self):
        """اختبار المعالجة المجزأة"""
        from inventory.models import Product, Category
        
        category = Category.objects.create(name='فئة مجزأة')
        
        products = []
        for i in range(30):
            products.append(Product(
                name=f'منتج مجزأ {i}',
                sku=f'CHUNK-{i:05d}',
                category=category
            ))
        Product.objects.bulk_create(products)
        
        CHUNK_SIZE = 10
        processed = 0
        
        start_time = time.time()
        
        # معالجة مجزأة
        queryset = Product.objects.filter(sku__startswith='CHUNK-')
        for product in queryset.iterator(chunk_size=CHUNK_SIZE):
            processed += 1
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 2.0)
        self.assertEqual(processed, 30)


class LoadTestCase(TransactionTestCase):
    """اختبارات الحمل"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        from inventory.models import Category
        self.user = User.objects.create_user('load_user', 'load@test.com', 'pass123')
        self.category = Category.objects.create(name='فئة حمل')
    
    def test_concurrent_product_creation_simulation(self):
        """محاكاة إنشاء منتجات متزامنة"""
        from inventory.models import Product
        
        # محاكاة 5 دفعات من المنتجات
        BATCHES = 5
        BATCH_SIZE = 20
        
        start_time = time.time()
        
        for batch in range(BATCHES):
            products = []
            for i in range(BATCH_SIZE):
                products.append(Product(
                    name=f'منتج حمل {batch}_{i}',
                    sku=f'LOAD-{batch:02d}-{i:04d}',
                    category=self.category,
                    cost=Decimal('100')
                ))
            Product.objects.bulk_create(products)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        total_products = Product.objects.filter(sku__startswith='LOAD-').count()
        
        self.assertEqual(total_products, BATCHES * BATCH_SIZE)
        self.assertLess(execution_time, 10.0, f"إنشاء {total_products} منتج استغرق {execution_time:.2f} ثانية")
    
    def test_concurrent_stock_operations_simulation(self):
        """محاكاة عمليات مخزون متزامنة"""
        from inventory.models import Product, Location, Stock
        
        # إنشاء منتجات ومواقع
        products = []
        for i in range(10):
            products.append(Product(
                name=f'منتج عمليات {i}',
                sku=f'OPS-{i:05d}',
                category=self.category
            ))
        Product.objects.bulk_create(products)
        
        locations = []
        for i in range(3):
            locations.append(Location(name=f'مخزن عمليات {i}', code=f'WH-OPS-{i}'))
        Location.objects.bulk_create(locations)
        
        created_products = list(Product.objects.filter(sku__startswith='OPS-'))
        created_locations = list(Location.objects.filter(code__startswith='WH-OPS-'))
        
        start_time = time.time()
        
        # إنشاء سجلات مخزون
        stocks = []
        for product in created_products:
            for location in created_locations:
                stocks.append(Stock(
                    product=product,
                    location=location,
                    quantity=Decimal('50')
                ))
        Stock.objects.bulk_create(stocks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        total_stocks = Stock.objects.filter(product__sku__startswith='OPS-').count()
        
        self.assertEqual(total_stocks, 30)  # 10 منتجات × 3 مواقع
        self.assertLess(execution_time, 5.0)


class IndexPerformanceTestCase(TestCase):
    """اختبارات أداء الفهارس"""
    
    @classmethod
    def setUpTestData(cls):
        """إعداد بيانات الاختبار"""
        from inventory.models import Product, Category
        
        cls.category = Category.objects.create(name='فئة فهرس')
        
        products = []
        for i in range(100):
            products.append(Product(
                name=f'منتج فهرس {i}',
                sku=f'IDX-{i:05d}',
                cost=Decimal(str(i * 10))
            ))
        Product.objects.bulk_create(products)
    
    def test_indexed_field_search_performance(self):
        """اختبار أداء البحث في حقل مفهرس"""
        from inventory.models import Product
        
        start_time = time.time()
        
        # البحث باستخدام SKU (حقل مفهرس عادة)
        for i in range(50):
            Product.objects.filter(sku=f'IDX-{i:05d}').first()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 2.0, f"50 بحث استغرق {execution_time:.2f} ثانية")
    
    def test_range_query_performance(self):
        """اختبار أداء استعلام النطاق"""
        from inventory.models import Product
        
        start_time = time.time()
        
        products = list(Product.objects.filter(
            sku__startswith='IDX-',
            cost__gte=Decimal('100'),
            cost__lte=Decimal('500')
        ))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0)
        self.assertGreater(len(products), 0)


class PerformanceSummaryTestCase(TestCase):
    """ملخص اختبارات الأداء"""
    
    def test_performance_benchmarks(self):
        """اختبار المعايير المرجعية للأداء"""
        # اختبار بسيط للتحقق من أن النظام يعمل
        from inventory.models import Product, Category
        
        category = Category.objects.create(name='فئة معيار')
        
        start_time = time.time()
        
        # إنشاء منتج واحد
        product = Product.objects.create(
            name='منتج معيار',
            sku='BENCH-001',
            category=category
        )
        
        # قراءة المنتج
        retrieved = Product.objects.get(sku='BENCH-001')
        
        # تحديث المنتج
        retrieved.name = 'منتج معيار محدث'
        retrieved.save()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 1.0)
        self.assertEqual(retrieved.name, 'منتج معيار محدث')
    
    def test_query_count_efficiency(self):
        """اختبار كفاءة عدد الاستعلامات"""
        from inventory.models import Product, Category
        from django.test.utils import CaptureQueriesContext
        
        category = Category.objects.create(name='فئة كفاءة')
        
        products = []
        for i in range(10):
            products.append(Product(
                name=f'منتج كفاءة {i}',
                sku=f'EFF-{i:05d}',
                category=category
            ))
        Product.objects.bulk_create(products)
        
        # قياس عدد الاستعلامات
        with CaptureQueriesContext(connection) as context:
            products = list(Product.objects.filter(sku__startswith='EFF-').select_related('category'))
            for p in products:
                _ = p.category.name
        
        # يجب أن يكون عدد الاستعلامات قليل (استعلام واحد مع select_related)
        self.assertLessEqual(len(context.captured_queries), 2)
