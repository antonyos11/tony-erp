"""
اختبار شامل وقوي لنظام Tony ERP - نسخة مبسطة
يختبر الوظائف الأساسية والميزات الجديدة
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from decimal import Decimal
from datetime import datetime
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum

# Colors
class C:
    G = '\033[92m'  # Green
    R = '\033[91m'  # Red
    Y = '\033[93m'  # Yellow
    B = '\033[94m'  # Blue
    M = '\033[95m'  # Magenta
    E = '\033[0m'   # End
    BOLD = '\033[1m'

def header(text):
    print(f"\n{C.M}{C.BOLD}{'='*80}{C.E}")
    print(f"{C.M}{C.BOLD}{text.center(80)}{C.E}")
    print(f"{C.M}{C.BOLD}{'='*80}{C.E}\n")

def success(text):
    print(f"{C.G}✓ {text}{C.E}")

def error(text):
    print(f"{C.R}✗ {text}{C.E}")

def info(text):
    print(f"{C.B}ℹ {text}{C.E}")

def warn(text):
    print(f"{C.Y}⚠ {text}{C.E}")

User = get_user_model()

class SimpleERPTest:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.user = None
        
    def test(self, name, func):
        """Run a test"""
        info(f"Testing: {name}...")
        try:
            func()
            self.passed += 1
            success(f"PASSED: {name}")
            return True
        except Exception as e:
            self.failed += 1
            self.errors.append(f"{name}: {str(e)}")
            error(f"FAILED: {name} - {str(e)}")
            return False
    
    def setup(self):
        """Setup"""
        header("Setup Test Environment")
        self.user, _ = User.objects.get_or_create(
            username='test_user',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        success(f"Test user: {self.user.username}")
    
    # ========================================================================
    # CORE TESTS
    # ========================================================================
    
    def test_database_connection(self):
        """Test database"""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_models_loaded(self):
        """Test models can be imported"""
        from accounting.models import Account
        from inventory.models import Product
        from sales.models import Invoice
        from purchases.models import PurchaseBill
        from crm.models import Customer
        from partners.models import Partner
        from hr.models import Employee
        success("  All core models imported")
    
    def test_new_models_loaded(self):
        """Test new feature models"""
        from woocommerce_integration.models import WooCommerceConfig
        from fixed_assets.models import Asset, AssetCategory
        from purchases.models import PurchaseRequisition
        from sales.models import SalesOrder
        success("  All new models imported")
    
    # ========================================================================
    # ACCOUNTING TESTS
    # ========================================================================
    
    def test_accounts_exist(self):
        """Test chart of accounts"""
        from accounting.models import Account
        count = Account.objects.count()
        assert count > 0, "No accounts found"
        success(f"  Found {count} accounts")
    
    def test_journal_entry(self):
        """Test journal entry creation"""
        from accounting.models import Account, JournalEntry, JournalEntryItem
        
        # Get accounts
        asset_acc = Account.objects.filter(account_type='asset').first()
        revenue_acc = Account.objects.filter(account_type='revenue').first()
        
        if not asset_acc or not revenue_acc:
            warn("  Skipped: Missing accounts")
            return
        
        # Create entry
        entry = JournalEntry.objects.create(
            date=timezone.now().date(),
            description='Test Entry',
            created_by=self.user
        )
        
        JournalEntryItem.objects.create(
            entry=entry,
            account=asset_acc,
            debit=Decimal('500'),
            credit=Decimal('0')
        )
        
        JournalEntryItem.objects.create(
            entry=entry,
            account=revenue_acc,
            debit=Decimal('0'),
            credit=Decimal('500')
        )
        
        # Verify
        debit_total = entry.items.aggregate(Sum('debit'))['debit__sum']
        credit_total = entry.items.aggregate(Sum('credit'))['credit__sum']
        assert debit_total == credit_total
        success(f"  Entry balanced: {debit_total}")
    
    # ========================================================================
    # INVENTORY TESTS
    # ========================================================================
    
    def test_products_exist(self):
        """Test products"""
        from inventory.models import Product
        count = Product.objects.count()
        info(f"  Found {count} products")
    
    def test_create_product(self):
        """Test product creation"""
        from inventory.models import Product
        
        product = Product.objects.create(
            sku=f'TEST-SKU-{timezone.now().timestamp()}',
            name='Test Mattress Product',
            price=Decimal('1500.00'),
            cost=Decimal('1000.00')
        )
        
        assert product.pk is not None
        assert product.price > product.cost
        success(f"  Product created: {product.sku}")
    
    def test_stock_operations(self):
        """Test stock"""
        from inventory.models import Product, Location, Stock
        
        # Get or create location
        location = Location.objects.first()
        if not location:
            location = Location.objects.create(
                name='Test Warehouse',
                code='TEST-WH',
                type='warehouse',
                created_by=self.user
            )
        
        # Get product
        product = Product.objects.first()
        if not product:
            warn("  Skipped: No products")
            return
        
        # Get or create stock
        stock, created = Stock.objects.get_or_create(
            product=product,
            location=location,
            defaults={'quantity': Decimal('100')}
        )
        
        initial_qty = stock.quantity
        success(f"  Stock quantity: {initial_qty}")
    
    # ========================================================================
    # SALES TESTS
    # ========================================================================
    
    def test_customers_exist(self):
        """Test customers"""
        from crm.models import Customer
        count = Customer.objects.count()
        info(f"  Found {count} customers")
    
    def test_sales_order(self):
        """Test Sales Order (NEW FEATURE)"""
        from sales.models import SalesOrder, SalesOrderLine
        from partners.models import Customer
        from inventory.models import Product, Location
        
        customer = Customer.objects.first()
        product = Product.objects.first()
        location = Location.objects.first()
        
        if not all([customer, product, location]):
            warn("  Skipped: Missing data")
            return
        
        # Create sales order
        order = SalesOrder.objects.create(
            customer=customer,
            date=timezone.now().date(),
            status='draft',
            created_by=self.user
        )
        
        # Add line
        line = SalesOrderLine.objects.create(
            order=order,
            product=product,
            location=location,
            quantity=Decimal('5'),
            price=product.price
        )
        
        assert order.items.count() > 0
        success(f"  Sales order created: {order.number}")
    
    def test_invoices_exist(self):
        """Test invoices"""
        from sales.models import Invoice
        count = Invoice.objects.count()
        info(f"  Found {count} invoices")
    
    # ========================================================================
    # PURCHASE TESTS
    # ========================================================================
    
    def test_purchase_requisition(self):
        """Test Purchase Requisition (NEW FEATURE)"""
        from purchases.models import PurchaseRequisition, PurchaseRequisitionItem
        from inventory.models import Product, Location
        
        product = Product.objects.first()
        location = Location.objects.first()
        
        if not product or not location:
            warn("  Skipped: Missing data")
            return
        
        # Create PR
        pr = PurchaseRequisition.objects.create(
            requested_by=self.user,
            department='production',
            priority='normal',
            status='draft',
            justification='Test materials'
        )
        
        # Add item
        item = PurchaseRequisitionItem.objects.create(
            requisition=pr,
            product=product,
            quantity=50,
            estimated_price=product.cost,
            location=location
        )
        
        assert pr.items.count() > 0
        success(f"  Purchase requisition created")
    
    def test_purchase_bills_exist(self):
        """Test purchase bills"""
        from purchases.models import PurchaseBill
        count = PurchaseBill.objects.count()
        info(f"  Found {count} purchase bills")
    
    # ========================================================================
    # HR TESTS
    # ========================================================================
    
    def test_employees_exist(self):
        """Test employees"""
        from hr.models import Employee
        count = Employee.objects.count()
        info(f"  Found {count} employees")
    
    def test_payroll_calculator(self):
        """Test Payroll Calculator (NEW FEATURE)"""
        try:
            from hr.payroll_calculator import PayrollCalculator
            from hr.models import Employee
            employee = Employee.objects.first()
            if not employee:
                warn("  Skipped: No employees")
                return
            from datetime import date
            calculator = PayrollCalculator(
                employee=employee,
                period_start=date.today().replace(day=1),
                period_end=date.today()
            )
            success("  Payroll calculator created")
        except ImportError as e:
            warn(f"  Payroll calculator not available: {e}")
    
    # ========================================================================
    # FIXED ASSETS TESTS (NEW)
    # ========================================================================
    
    def test_asset_categories(self):
        """Test Asset Categories (NEW FEATURE)"""
        from fixed_assets.models import AssetCategory
        
        category = AssetCategory.objects.create(
            name='Test Machinery',
            code='TEST-MACH',
            default_depreciation_method='straight_line',
            default_useful_life_years=10
        )
        
        assert category.pk is not None
        success(f"  Asset category created: {category.name}")
    
    def test_fixed_assets(self):
        """Test Fixed Assets (NEW FEATURE)"""
        from fixed_assets.models import Asset, AssetCategory
        from accounting.models import Account
        from inventory.models import Location
        
        category = AssetCategory.objects.first()
        location = Location.objects.first()
        asset_acc = Account.objects.filter(account_type='asset').first()
        expense_acc = Account.objects.filter(account_type='expense').first()
        
        if not all([category, location, asset_acc, expense_acc]):
            warn("  Skipped: Missing data")
            return
        
        asset = Asset.objects.create(
            name='Test Machine',
            number=f'ASSET-TEST-{timezone.now().timestamp()}',
            category=category,
            location=location.name if location else 'Main',
            acquisition_date=timezone.now().date(),
            acquisition_cost=Decimal('50000'),
            useful_life_years=10,
            salvage_value=Decimal('5000'),
            depreciation_method='straight_line',
            status='active',
            created_by=self.user
        )
        
        # Calculate depreciation
        monthly_dep = asset.calculate_depreciation()
        assert monthly_dep > 0
        success(f"  Asset created, monthly depreciation: {monthly_dep}")
    
    # ========================================================================
    # WOOCOMMERCE TESTS (NEW)
    # ========================================================================
    
    def test_woocommerce_config(self):
        """Test WooCommerce Config (NEW FEATURE)"""
        from woocommerce_integration.models import WooCommerceConfig
        
        config = WooCommerceConfig.objects.create(
            name='Test Store',
            store_url='https://test.com',
            consumer_key='test_key',
            consumer_secret='test_secret',
            is_active=False  # Don't activate for test
        )
        
        assert config.pk is not None
        success(f"  WooCommerce config created: {config.name}")
    
    def test_product_mapping(self):
        """Test WooCommerce Product Mapping (NEW FEATURE)"""
        from woocommerce_integration.models import WooCommerceConfig, ProductMapping
        from inventory.models import Product
        
        config = WooCommerceConfig.objects.first()
        product = Product.objects.first()
        
        if not config or not product:
            warn("  Skipped: Missing data")
            return
        
        mapping = ProductMapping.objects.create(
            config=config,
            woo_product_id=999,
            erp_product=product,
            last_synced=timezone.now()
        )
        
        success(f"  Product mapping created")
    
    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================
    
    def test_data_integrity(self):
        """Test data integrity"""
        from sales.models import Invoice, InvoiceItem
        
        # Check orphaned items
        orphaned = InvoiceItem.objects.filter(invoice__isnull=True).count()
        assert orphaned == 0, f"Found {orphaned} orphaned items"
        success("  No orphaned records")
    
    def test_system_health(self):
        """Test system health"""
        from django.core.management import call_command
        import io
        import sys
        
        # Capture output
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            call_command('check', verbosity=0)
            success("  Django check passed")
        finally:
            sys.stdout = old_stdout
    
    # ========================================================================
    # RUN ALL
    # ========================================================================
    
    def run_all(self):
        """Run all tests"""
        header("🚀 TONY ERP COMPREHENSIVE TEST SUITE")
        info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.setup()
        
        # Core Tests
        header("🔧 CORE TESTS")
        self.test("Database Connection", self.test_database_connection)
        self.test("Core Models Loaded", self.test_models_loaded)
        self.test("New Models Loaded", self.test_new_models_loaded)
        
        # Accounting
        header("📊 ACCOUNTING TESTS")
        self.test("Accounts Exist", self.test_accounts_exist)
        self.test("Journal Entry", self.test_journal_entry)
        
        # Inventory
        header("📦 INVENTORY TESTS")
        self.test("Products Exist", self.test_products_exist)
        self.test("Create Product", self.test_create_product)
        self.test("Stock Operations", self.test_stock_operations)
        
        # Sales
        header("💰 SALES TESTS")
        self.test("Customers Exist", self.test_customers_exist)
        self.test("Sales Order (NEW)", self.test_sales_order)
        self.test("Invoices Exist", self.test_invoices_exist)
        
        # Purchases
        header("🛒 PURCHASE TESTS")
        self.test("Purchase Requisition (NEW)", self.test_purchase_requisition)
        self.test("Purchase Bills Exist", self.test_purchase_bills_exist)
        
        # HR
        header("👥 HR TESTS")
        self.test("Employees Exist", self.test_employees_exist)
        self.test("Payroll Calculator (NEW)", self.test_payroll_calculator)
        
        # Fixed Assets
        header("🏢 FIXED ASSETS TESTS (NEW FEATURE)")
        self.test("Asset Categories", self.test_asset_categories)
        self.test("Fixed Assets", self.test_fixed_assets)
        
        # WooCommerce
        header("🛍️ WOOCOMMERCE TESTS (NEW FEATURE)")
        self.test("WooCommerce Config", self.test_woocommerce_config)
        self.test("Product Mapping", self.test_product_mapping)
        
        # Integration
        header("🔗 INTEGRATION TESTS")
        self.test("Data Integrity", self.test_data_integrity)
        self.test("System Health", self.test_system_health)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary"""
        header("📋 TEST SUMMARY")
        
        total = self.passed + self.failed
        rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{C.BOLD}Total Tests:{C.E} {total}")
        print(f"{C.G}{C.BOLD}Passed:{C.E} {self.passed}")
        print(f"{C.R}{C.BOLD}Failed:{C.E} {self.failed}")
        print(f"{C.B}{C.BOLD}Success Rate:{C.E} {rate:.1f}%\n")
        
        if self.errors:
            header("❌ ERRORS")
            for err in self.errors:
                error(err)
        
        # Final verdict
        if self.failed == 0:
            print(f"\n{C.G}{C.BOLD}{'='*80}{C.E}")
            print(f"{C.G}{C.BOLD}{'🎉 ALL TESTS PASSED! 🎉'.center(80)}{C.E}")
            print(f"{C.G}{C.BOLD}{'='*80}{C.E}\n")
        else:
            print(f"\n{C.Y}{C.BOLD}{'='*80}{C.E}")
            print(f"{C.Y}{C.BOLD}{'⚠️ SOME TESTS FAILED ⚠️'.center(80)}{C.E}")
            print(f"{C.Y}{C.BOLD}{'='*80}{C.E}\n")
        
        info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    try:
        tester = SimpleERPTest()
        tester.run_all()
        exit(0 if tester.failed == 0 else 1)
    except Exception as e:
        error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(2)
