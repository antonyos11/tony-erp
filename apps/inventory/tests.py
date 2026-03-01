from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.inventory.models import Product, Category, UnitOfMeasure, StockLevel
from apps.inventory.services.stock_engine import StockEngine
from apps.core.models import Branch, Warehouse

User = get_user_model()


class StockEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.branch = Branch.objects.create(name='فرع تجريبي', branch_type='owned', governorate='القاهرة')
        self.warehouse = Warehouse.objects.create(name='مخزن رئيسي', warehouse_type='factory', branch=self.branch)
        self.warehouse2 = Warehouse.objects.create(name='مخزن فرعي', warehouse_type='branch', branch=self.branch)
        self.unit = UnitOfMeasure.objects.create(name='قطعة', symbol='قطعة')
        self.category = Category.objects.create(name='خامات')
        self.product = Product.objects.create(
            code='TEST001', name='إسفنج تجريبي', product_type='raw_material',
            category=self.category, unit=self.unit, cost_price=100, reorder_level=10
        )

    def test_receive_stock(self):
        move = StockEngine.receive_stock(self.product, self.warehouse, Decimal('50'), Decimal('100'), user=self.user)
        self.assertEqual(move.move_type, 'in')
        stock = StockLevel.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(stock.quantity, Decimal('50'))

    def test_issue_stock(self):
        StockEngine.receive_stock(self.product, self.warehouse, Decimal('50'), Decimal('100'), user=self.user)
        move = StockEngine.issue_stock(self.product, self.warehouse, Decimal('20'), user=self.user)
        stock = StockLevel.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(stock.quantity, Decimal('30'))

    def test_issue_insufficient_stock_fails(self):
        StockEngine.receive_stock(self.product, self.warehouse, Decimal('10'), Decimal('100'), user=self.user)
        with self.assertRaises(ValueError):
            StockEngine.issue_stock(self.product, self.warehouse, Decimal('20'), user=self.user)

    def test_transfer_stock(self):
        StockEngine.receive_stock(self.product, self.warehouse, Decimal('50'), Decimal('100'), user=self.user)
        StockEngine.transfer_stock(self.product, self.warehouse, self.warehouse2, Decimal('20'), user=self.user)
        stock1 = StockLevel.objects.get(product=self.product, warehouse=self.warehouse)
        stock2 = StockLevel.objects.get(product=self.product, warehouse=self.warehouse2)
        self.assertEqual(stock1.quantity, Decimal('30'))
        self.assertEqual(stock2.quantity, Decimal('20'))

    def test_average_cost_calculation(self):
        StockEngine.receive_stock(self.product, self.warehouse, Decimal('10'), Decimal('100'), user=self.user)
        StockEngine.receive_stock(self.product, self.warehouse, Decimal('10'), Decimal('200'), user=self.user)
        stock = StockLevel.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(stock.average_cost, Decimal('150'))

    def test_adjust_stock(self):
        StockEngine.receive_stock(self.product, self.warehouse, Decimal('50'), Decimal('100'), user=self.user)
        StockEngine.adjust_stock(self.product, self.warehouse, Decimal('45'), reason='فرق جرد', user=self.user)
        stock = StockLevel.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(stock.quantity, Decimal('45'))

    def test_low_stock_detection(self):
        StockEngine.receive_stock(self.product, self.warehouse, Decimal('5'), Decimal('100'), user=self.user)
        low = StockEngine.get_low_stock_products()
        self.assertEqual(len(low), 1)


class InventoryViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username='testuser', password='test123')
        self.client.login(username='testuser', password='test123')

    def test_product_list_page(self):
        response = self.client.get('/inventory/products/')
        self.assertEqual(response.status_code, 200)

    def test_stock_levels_page(self):
        response = self.client.get('/inventory/stock-levels/')
        self.assertEqual(response.status_code, 200)

    def test_stock_moves_page(self):
        response = self.client.get('/inventory/stock-moves/')
        self.assertEqual(response.status_code, 200)

    def test_low_stock_page(self):
        response = self.client.get('/inventory/low-stock/')
        self.assertEqual(response.status_code, 200)
