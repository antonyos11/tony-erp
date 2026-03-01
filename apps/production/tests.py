from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.production.models import ProductionOrder, ProductionLine
from apps.production.services.production_engine import ProductionEngine
from apps.inventory.models import Product, Category, UnitOfMeasure, BillOfMaterials, BOMLine
from apps.inventory.services.stock_engine import StockEngine
from apps.accounts.models import FiscalYear, Account
from apps.core.models import Branch, Warehouse

User = get_user_model()


class ProductionEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.branch = Branch.objects.create(name='المصنع', branch_type='owned', governorate='القاهرة')
        self.wh_raw = Warehouse.objects.create(name='مخزن خامات', warehouse_type='raw_materials', branch=self.branch)
        self.wh_finished = Warehouse.objects.create(name='مخزن منتجات', warehouse_type='finished', branch=self.branch)
        self.unit = UnitOfMeasure.objects.create(name='قطعة', symbol='قطعة')
        self.cat_raw = Category.objects.create(name='خامات')
        self.cat_finished = Category.objects.create(name='منتجات تامة')
        self.line = ProductionLine.objects.create(name='خط إنتاج 1')

        # سنة مالية + حسابات
        self.fy = FiscalYear.objects.create(
            name='2026', start_date='2026-01-01', end_date='2026-12-31', is_active=True
        )
        Account.objects.create(
            code='1141', name='مخزون خامات', account_type='asset',
            nature='debit', is_detail=True, is_system=True
        )
        Account.objects.create(
            code='1142', name='تحت التشغيل', account_type='asset',
            nature='debit', is_detail=True, is_system=True
        )
        Account.objects.create(
            code='1143', name='منتجات تامة', account_type='asset',
            nature='debit', is_detail=True, is_system=True
        )
        Account.objects.create(
            code='215', name='رواتب مستحقة', account_type='liability',
            nature='credit', is_detail=True, is_system=True
        )
        Account.objects.create(
            code='54', name='تكاليف غير مباشرة', account_type='cogs',
            nature='debit', is_detail=True, is_system=True
        )

        # خامة
        self.foam = Product.objects.create(
            code='RM001', name='إسفنج عادي', product_type='raw_material',
            category=self.cat_raw, unit=self.unit, cost_price=50
        )
        # منتج نهائي
        self.mattress = Product.objects.create(
            code='FP001', name='مرتبة سوست 120×200', product_type='finished',
            category=self.cat_finished, unit=self.unit, cost_price=0, retail_price=2000
        )
        # BOM
        self.bom = BillOfMaterials.objects.create(
            product=self.mattress, name='وصفة مرتبة 120', is_default=True
        )
        BOMLine.objects.create(
            bom=self.bom, raw_material=self.foam,
            quantity=Decimal('2'), waste_percentage=Decimal('5')
        )

        # إضافة مخزون خامات
        StockEngine.receive_stock(
            self.foam, self.wh_raw, Decimal('100'), Decimal('50'), user=self.user
        )

    def test_create_production_order(self):
        order = ProductionEngine.create_production_order(
            product=self.mattress, bom=self.bom, quantity=Decimal('10'),
            production_line=self.line, warehouse_raw=self.wh_raw,
            warehouse_finished=self.wh_finished, user=self.user
        )
        self.assertEqual(order.status, 'draft')
        self.assertEqual(order.material_consumptions.count(), 1)

    def test_full_production_cycle(self):
        order = ProductionEngine.create_production_order(
            product=self.mattress, bom=self.bom, quantity=Decimal('10'),
            production_line=self.line, warehouse_raw=self.wh_raw,
            warehouse_finished=self.wh_finished, user=self.user
        )
        ProductionEngine.confirm_order(order, user=self.user)
        self.assertEqual(order.status, 'confirmed')

        ProductionEngine.start_production(order, user=self.user)
        order.refresh_from_db()
        self.assertEqual(order.status, 'in_progress')
        self.assertTrue(order.material_cost > 0)

        ProductionEngine.add_labor_cost(order, Decimal('500'), user=self.user)
        ProductionEngine.add_overhead_cost(order, Decimal('200'), user=self.user)

        ProductionEngine.complete_production(
            order, quantity_produced=Decimal('10'), user=self.user
        )
        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')
        self.assertTrue(order.unit_cost > 0)

    def test_insufficient_materials_raises_error(self):
        with self.assertRaises(ValueError):
            ProductionEngine.create_production_order(
                product=self.mattress, bom=self.bom, quantity=Decimal('1000'),
                production_line=self.line, warehouse_raw=self.wh_raw,
                warehouse_finished=self.wh_finished, user=self.user
            )

    def test_cannot_confirm_non_draft(self):
        order = ProductionEngine.create_production_order(
            product=self.mattress, bom=self.bom, quantity=Decimal('5'),
            production_line=self.line, warehouse_raw=self.wh_raw,
            warehouse_finished=self.wh_finished, user=self.user
        )
        ProductionEngine.confirm_order(order, user=self.user)
        with self.assertRaises(ValueError):
            ProductionEngine.confirm_order(order, user=self.user)

    def test_cost_breakdown(self):
        order = ProductionEngine.create_production_order(
            product=self.mattress, bom=self.bom, quantity=Decimal('5'),
            production_line=self.line, warehouse_raw=self.wh_raw,
            warehouse_finished=self.wh_finished, user=self.user
        )
        bd = ProductionEngine.get_production_cost_breakdown(order)
        self.assertEqual(bd['product'], self.mattress.name)
        self.assertIn('material_details', bd)


class ProductionViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='testuser', password='test123'
        )
        self.client.login(username='testuser', password='test123')

    def test_order_list_page(self):
        response = self.client.get('/production/orders/')
        self.assertEqual(response.status_code, 200)

    def test_order_create_page(self):
        response = self.client.get('/production/orders/create/')
        self.assertEqual(response.status_code, 200)

    def test_cost_report_page(self):
        response = self.client.get('/production/reports/cost/')
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get('/production/orders/')
        self.assertNotEqual(response.status_code, 200)

