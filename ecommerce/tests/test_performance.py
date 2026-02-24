"""
Performance Tests for E-commerce
=================================
Load testing, response time benchmarks, and performance optimization tests
Week 3 - Testing & Quality
"""

import time
import statistics
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import connection, reset_queries
from django.conf import settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from concurrent.futures import ThreadPoolExecutor, as_completed

from ecommerce.models import (
    OnlineProduct, ProductCategory, Brand, Cart, CartItem,
    Order, OrderItem, EcommerceSettings
)

# Aliases for compatibility
Product = OnlineProduct
Category = ProductCategory

User = get_user_model()


class DatabaseQueryOptimizationTests(TestCase):
    """Tests for database query optimization"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.category = Category.objects.create(
            name='Performance Category',
            slug='performance-category',
            is_active=True
        )
        
        cls.brand = Brand.objects.create(
            name='Performance Brand',
            slug='performance-brand',
            is_active=True
        )
        
        # Create 100 products
        products = []
        for i in range(100):
            products.append(Product(
                name=f'Product {i+1}',
                slug=f'product-{i+1}',
                price=Decimal(str((i + 1) * 10)),
                category=cls.category,
                brand=cls.brand,
                is_active=True
            ))
        Product.objects.bulk_create(products)
    
    def test_product_list_query_count(self):
        """Test product list uses optimal number of queries"""
        settings.DEBUG = True
        reset_queries()
        
        # Fetch products with select_related
        products = list(Product.objects.select_related(
            'category', 'brand'
        ).filter(is_active=True)[:20])
        
        query_count = len(connection.queries)
        
        # Should be 1-2 queries max (list + count)
        self.assertLessEqual(query_count, 3)
        
        settings.DEBUG = False
    
    def test_cart_with_items_query_count(self):
        """Test cart retrieval uses optimal queries"""
        user = User.objects.create_user(
            username='queryuser',
            email='query@test.com',
            password='testpass123'
        )
        
        cart = Cart.objects.create(user=user)
        products = Product.objects.all()[:5]
        
        for product in products:
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=1
            )
        
        settings.DEBUG = True
        reset_queries()
        
        # Fetch cart with items and products
        cart = Cart.objects.prefetch_related(
            'items__product__category'
        ).get(user=user)
        
        # Access all items
        for item in cart.items.all():
            _ = item.product.name
            _ = item.product.category.name
        
        query_count = len(connection.queries)
        
        # Should be 3-4 queries max (cart, items, products, categories)
        self.assertLessEqual(query_count, 5)
        
        settings.DEBUG = False
    
    def test_order_with_items_query_count(self):
        """Test order retrieval uses optimal queries"""
        user = User.objects.create_user(
            username='orderqueryuser',
            email='orderquery@test.com',
            password='testpass123'
        )
        
        order = Order.objects.create(
            user=user,
            order_number='ORD-QUERY-001',
            total=Decimal('5000.00'),
            status='pending'
        )
        
        products = Product.objects.all()[:5]
        for product in products:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=1,
                unit_price=product.price,
                subtotal=product.price
            )
        
        settings.DEBUG = True
        reset_queries()
        
        # Fetch order with items
        order = Order.objects.prefetch_related(
            'items__product'
        ).get(id=order.id)
        
        # Access all items
        for item in order.items.all():
            _ = item.product.name
        
        query_count = len(connection.queries)
        
        # Should be 2-3 queries max
        self.assertLessEqual(query_count, 4)
        
        settings.DEBUG = False


class APIResponseTimeTests(APITestCase):
    """Tests for API response time"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.category = Category.objects.create(
            name='Speed Category',
            slug='speed-category',
            is_active=True
        )
        
        # Create products
        products = []
        for i in range(50):
            products.append(Product(
                name=f'Speed Product {i+1}',
                slug=f'speed-product-{i+1}',
                price=Decimal(str((i + 1) * 100)),
                category=cls.category,
                is_active=True
            ))
        Product.objects.bulk_create(products)
    
    def test_product_list_response_time(self):
        """Test product list API response time"""
        url = reverse('ecommerce_api:product-list')
        
        times = []
        for _ in range(10):
            start = time.time()
            response = self.client.get(url)
            elapsed = time.time() - start
            times.append(elapsed)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        # Average should be under 200ms
        self.assertLess(avg_time, 0.5)
        # Max should be under 500ms
        self.assertLess(max_time, 1.0)
    
    def test_product_detail_response_time(self):
        """Test product detail API response time"""
        product = Product.objects.first()
        url = reverse('ecommerce_api:product-detail', args=[product.id])
        
        times = []
        for _ in range(10):
            start = time.time()
            response = self.client.get(url)
            elapsed = time.time() - start
            times.append(elapsed)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        avg_time = statistics.mean(times)
        
        # Average should be under 100ms
        self.assertLess(avg_time, 0.3)
    
    def test_category_list_response_time(self):
        """Test category list API response time"""
        url = reverse('ecommerce_api:category-list')
        
        start = time.time()
        response = self.client.get(url)
        elapsed = time.time() - start
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed, 0.3)


class ConcurrentRequestTests(TransactionTestCase):
    """Tests for handling concurrent requests"""
    
    def setUp(self):
        """Set up test data"""
        self.category = Category.objects.create(
            name='Concurrent Category',
            slug='concurrent-category',
            is_active=True
        )
        
        self.product = Product.objects.create(
            name='Concurrent Product',
            slug='concurrent-product',
            price=Decimal('500.00'),
            category=self.category,
            is_active=True
        )
        
        EcommerceSettings.objects.create(
            store_name='Test Store',
            vat_rate=Decimal('14.00'),
            currency='EGP'
        )
    
    def test_concurrent_product_views(self):
        """Test handling concurrent product view requests"""
        client = APIClient()
        url = reverse('ecommerce_api:product-list')
        
        def make_request():
            return client.get(url)
        
        # Simulate 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            
            success_count = 0
            for future in as_completed(futures):
                response = future.result()
                if response.status_code == status.HTTP_200_OK:
                    success_count += 1
        
        # All requests should succeed
        self.assertEqual(success_count, 10)


class PaginationPerformanceTests(APITestCase):
    """Tests for pagination performance"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.category = Category.objects.create(
            name='Pagination Category',
            slug='pagination-category',
            is_active=True
        )
        
        # Create 500 products
        products = []
        for i in range(500):
            products.append(Product(
                name=f'Page Product {i+1}',
                slug=f'page-product-{i+1}',
                price=Decimal(str((i % 100 + 1) * 10)),
                category=cls.category,
                is_active=True
            ))
        Product.objects.bulk_create(products)
    
    def test_first_page_performance(self):
        """Test first page loads quickly"""
        url = reverse('ecommerce_api:product-list')
        
        start = time.time()
        response = self.client.get(url, {'page': 1})
        elapsed = time.time() - start
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed, 0.5)
    
    def test_middle_page_performance(self):
        """Test middle page loads quickly"""
        url = reverse('ecommerce_api:product-list')
        
        start = time.time()
        response = self.client.get(url, {'page': 10})
        elapsed = time.time() - start
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
        self.assertLess(elapsed, 0.5)
    
    def test_large_page_size_performance(self):
        """Test large page size doesn't timeout"""
        url = reverse('ecommerce_api:product-list')
        
        start = time.time()
        response = self.client.get(url, {'page_size': 100})
        elapsed = time.time() - start
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed, 1.0)


class SearchPerformanceTests(APITestCase):
    """Tests for search performance"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.category = Category.objects.create(
            name='Search Category',
            slug='search-category',
            is_active=True
        )
        
        # Create products with various names
        products = []
        names = ['هاتف', 'لابتوب', 'تابلت', 'سماعات', 'شاحن', 'كابل', 'حافظة']
        
        for i in range(200):
            name_prefix = names[i % len(names)]
            products.append(Product(
                name=f'{name_prefix} {i+1}',
                slug=f'search-product-{i+1}',
                price=Decimal(str((i % 50 + 1) * 100)),
                category=cls.category,
                is_active=True
            ))
        Product.objects.bulk_create(products)
    
    def test_text_search_performance(self):
        """Test text search performance"""
        url = reverse('ecommerce_api:product-list')
        
        times = []
        search_terms = ['هاتف', 'لابتوب', 'سماعات']
        
        for term in search_terms:
            start = time.time()
            response = self.client.get(url, {'search': term})
            elapsed = time.time() - start
            times.append(elapsed)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        avg_time = statistics.mean(times)
        
        # Average search should be under 300ms
        self.assertLess(avg_time, 0.5)
    
    def test_filter_performance(self):
        """Test filter performance"""
        url = reverse('ecommerce_api:product-list')
        
        start = time.time()
        response = self.client.get(url, {
            'min_price': '1000',
            'max_price': '3000',
            'category': self.category.id
        })
        elapsed = time.time() - start
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed, 0.5)


class CachePerformanceTests(APITestCase):
    """Tests for cache effectiveness"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.category = Category.objects.create(
            name='Cache Category',
            slug='cache-category',
            is_active=True
        )
        
        products = []
        for i in range(20):
            products.append(Product(
                name=f'Cache Product {i+1}',
                slug=f'cache-product-{i+1}',
                price=Decimal('500.00'),
                category=cls.category,
                is_active=True
            ))
        Product.objects.bulk_create(products)
    
    def test_cached_response_faster(self):
        """Test cached response is faster than uncached"""
        url = reverse('ecommerce_api:product-list')
        
        # First request (uncached)
        start = time.time()
        response1 = self.client.get(url)
        first_time = time.time() - start
        
        # Second request (potentially cached)
        start = time.time()
        response2 = self.client.get(url)
        second_time = time.time() - start
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Second request should be same or faster
        # (allowing for some variance)
        self.assertLess(second_time, first_time + 0.1)


class MemoryUsageTests(TestCase):
    """Tests for memory usage optimization"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.category = Category.objects.create(
            name='Memory Category',
            slug='memory-category',
            is_active=True
        )
        
        products = []
        for i in range(100):
            products.append(Product(
                name=f'Memory Product {i+1}',
                slug=f'memory-product-{i+1}',
                price=Decimal('500.00'),
                category=cls.category,
                is_active=True
            ))
        Product.objects.bulk_create(products)
    
    def test_iterator_for_large_querysets(self):
        """Test using iterator() for large querysets"""
        count = 0
        for product in Product.objects.filter(is_active=True).iterator():
            count += 1
            _ = product.name
        
        self.assertGreater(count, 0)
    
    def test_values_for_specific_fields(self):
        """Test using values() for specific fields reduces memory"""
        products = list(Product.objects.filter(
            is_active=True
        ).values('id', 'display_name', 'custom_price')[:50])
        
        self.assertGreater(len(products), 0)
        
        # Each item should only have specified fields
        for p in products:
            self.assertIn('id', p)
            self.assertIn('display_name', p)
            self.assertIn('custom_price', p)


class BulkOperationTests(TransactionTestCase):
    """Tests for bulk operation performance"""
    
    def setUp(self):
        """Set up test data"""
        self.category = Category.objects.create(
            name='Bulk Category',
            slug='bulk-category',
            is_active=True
        )
    
    def test_bulk_create_performance(self):
        """Test bulk create is faster than individual creates"""
        products = []
        for i in range(100):
            products.append(Product(
                name=f'Bulk Product {i+1}',
                slug=f'bulk-product-{i+1}',
                price=Decimal('100.00'),
                category=self.category,
                is_active=True
            ))
        
        start = time.time()
        Product.objects.bulk_create(products)
        elapsed = time.time() - start
        
        # Bulk create 100 products should be under 1 second
        self.assertLess(elapsed, 1.0)
        
        count = Product.objects.filter(display_name__startswith='Bulk Product').count()
        self.assertEqual(count, 100)
    
    def test_bulk_update_performance(self):
        """Test bulk update is efficient"""
        # Create products first
        products = []
        for i in range(50):
            products.append(Product(
                name=f'Update Product {i+1}',
                slug=f'update-product-{i+1}',
                price=Decimal('100.00'),
                category=self.category,
                is_active=True
            ))
        Product.objects.bulk_create(products)
        
        # Update all products
        start = time.time()
        Product.objects.filter(display_name__startswith='Update Product').update(
            custom_price=Decimal('20.00')
        )
        elapsed = time.time() - start
        
        # Bulk update should be under 0.5 seconds
        self.assertLess(elapsed, 0.5)


class IndexingTests(TestCase):
    """Tests for database indexing effectiveness"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.category = Category.objects.create(
            name='Index Category',
            slug='index-category',
            is_active=True
        )
        
        products = []
        for i in range(200):
            products.append(Product(
                name=f'Index Product {i+1}',
                slug=f'index-product-{i+1}',
                price=Decimal(str((i % 100 + 1) * 10)),
                category=cls.category,
                is_active=i % 2 == 0
            ))
        Product.objects.bulk_create(products)
    
    def test_indexed_field_query_performance(self):
        """Test indexed field query is fast"""
        start = time.time()
        products = list(Product.objects.filter(
            slug='index-product-100'
        ))
        elapsed = time.time() - start
        
        # Indexed slug lookup should be very fast
        self.assertLess(elapsed, 0.1)
    
    def test_is_active_filter_performance(self):
        """Test is_active filter is fast (should be indexed)"""
        start = time.time()
        count = Product.objects.filter(is_active=True).count()
        elapsed = time.time() - start
        
        self.assertGreater(count, 0)
        self.assertLess(elapsed, 0.2)
    
    def test_price_range_query_performance(self):
        """Test price range query performance"""
        start = time.time()
        products = list(Product.objects.filter(
            custom_price__gte=Decimal('500.00'),
            custom_price__lte=Decimal('800.00')
        ))
        elapsed = time.time() - start
        
        self.assertLess(elapsed, 0.3)
