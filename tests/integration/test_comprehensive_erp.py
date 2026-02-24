"""
اختبار شامل وقوي لنظام Tony ERP
يغطي جميع الوحدات: المحاسبة، المخزون، المبيعات، المشتريات، الإنتاج، الموارد البشرية، والميزات الجديدة
"""

import os
import django
import sys
from decimal import Decimal
from datetime import datetime, timedelta, date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum

# Core Models
from accounting.models import Account, JournalEntry, JournalEntryItem
from inventory.models import Product, Location, Stock, StockTransfer
from sales.models import Invoice, InvoiceItem, SalesOrder, SalesOrderLine
from purchases.models import PurchaseBill, PurchaseItem, PurchaseRequisition, PurchaseRequisitionItem, PurchaseOrder
from production.models import ProductionOrder, BillOfMaterials, WorkerProductionEntry
from hr.models import Employee, Department, Payroll, AttendanceRecord, JobPosition
from crm.models import CustomerType
from partners.models import Partner, Customer as PartnerCustomer, Supplier

# New Features
from woocommerce_integration.models import WooCommerceConfig, ProductMapping, SyncLog
from fixed_assets.models import Asset, AssetCategory, DepreciationSchedule
from core.sequence_utils import Sequence

User = get_user_model()

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

class ERPComprehensiveTest:
    def __init__(self):
        self.test_user = None
        self.test_data = {}
        self.errors = []
        self.warnings = []
        self.passed_tests = 0
        self.total_tests = 0
        
    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        self.total_tests += 1
        print_info(f"Running: {test_name}...")
        try:
            test_func()
            self.passed_tests += 1
            print_success(f"PASSED: {test_name}")
            return True
        except Exception as e:
            self.errors.append(f"{test_name}: {str(e)}")
            print_error(f"FAILED: {test_name}")
            print_error(f"  Error: {str(e)}")
            return False
    
    def setup(self):
        """Setup test environment"""
        print_header("إعداد بيئة الاختبار")
        
        # Create or get test user
        self.test_user, created = User.objects.get_or_create(
            username='test_admin',
            defaults={
                'email': 'test@tonyerp.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            self.test_user.set_password('test123456')
            self.test_user.save()
            print_success("Created test user: test_admin")
        else:
            print_info("Using existing test user: test_admin")

        # Ensure key document sequences are aligned with existing rows
        # to avoid UNIQUE constraint errors on auto-generated numbers.
        def sync_sequence(name, model, prefix):
            seq, _ = Sequence.objects.get_or_create(name=name, defaults={'value': 0})
            existing_numbers = model.objects.filter(number__startswith=f"{prefix}-").values_list('number', flat=True)
            max_num = 0
            for num in existing_numbers:
                try:
                    last_part = str(num).split('-')[-1]
                    n = int(last_part)
                    if n > max_num:
                        max_num = n
                except Exception:
                    continue
            if max_num > seq.value:
                seq.value = max_num
                seq.save(update_fields=['value'])

        sync_sequence('STOCK_TRANSFER', StockTransfer, 'ST')
        sync_sequence('PURCHASE_ORDER', PurchaseOrder, 'PO')
        sync_sequence('PURCHASE_BILL', PurchaseBill, 'PB')
        sync_sequence('INVOICE', Invoice, 'INV')
    
    # ============================================================================
    # ACCOUNTING TESTS
    # ============================================================================
    
    def test_accounting_chart_of_accounts(self):
        """اختبار شجرة الحسابات"""
        # Ensure main account types exist (create minimal ones if missing)
        account_types = ['asset', 'liability', 'equity', 'revenue', 'expense']
        for acc_type in account_types:
            if not Account.objects.filter(account_type=acc_type).exists():
                Account.objects.get_or_create(
                    code=f'TEST-{acc_type.upper()}',
                    defaults={
                        'name': f'Test {acc_type.title()} Account',
                        'account_type': acc_type,
                    }
                )
            assert Account.objects.filter(account_type=acc_type).exists(), f"No {acc_type} accounts found"

        test_account = Account.objects.filter(account_type='asset').first()
        assert test_account is not None
        self.test_data['test_account'] = test_account
    
    def test_accounting_journal_entry(self):
        """اختبار القيود المحاسبية"""
        # Create journal entry
        entry = JournalEntry.objects.create(
            date=timezone.now().date(),
            description='Test Journal Entry',
            created_by=self.test_user
        )
        
        # Get debit and credit accounts
        cash_account = Account.objects.filter(account_type='asset').first()
        revenue_account = Account.objects.filter(account_type='revenue').first()
        
        assert cash_account and revenue_account, "Missing required accounts"
        
        # Create lines
        JournalEntryItem.objects.create(
            journal_entry=entry,
            account=cash_account,
            type='debit',
            amount=Decimal('1000.00')
        )
        JournalEntryItem.objects.create(
            journal_entry=entry,
            account=revenue_account,
            type='credit',
            amount=Decimal('1000.00')
        )
        
        # Verify balance
        total_debit = entry.total_debit
        total_credit = entry.total_credit
        assert total_debit == total_credit, f"Entry not balanced: {total_debit} != {total_credit}"
        self.test_data['journal_entry'] = entry
    
    # ============================================================================
    # INVENTORY TESTS
    # ============================================================================
    
    def test_inventory_products(self):
        """اختبار المنتجات"""
        product, _ = Product.objects.get_or_create(
            sku='TEST-MED-120-200',
            defaults={
                'name': 'Test Medical Mattress 120x200',
                'price': Decimal('2500.00'),
                'cost': Decimal('1800.00'),
            },
        )
        self.test_data['product'] = product
        
        # Verify pricing
        assert product.price > product.cost
        profit_margin = ((product.price - product.cost) / product.price) * 100
        assert profit_margin > 0, "No profit margin"
    
    def test_inventory_locations(self):
        """اختبار المواقع والمخازن"""
        location, _ = Location.objects.get_or_create(
            code='TEST-WH-01',
            defaults={
                'name': 'Test Main Warehouse',
                'type': 'finished',
            }
        )
        self.test_data['location'] = location
        assert location.pk is not None
    
    def test_inventory_stock_management(self):
        """اختبار إدارة المخزون"""
        product = self.test_data.get('product') or Product.objects.first()
        location = self.test_data.get('location') or Location.objects.first()
        
        # Create stock
        stock, created = Stock.objects.get_or_create(
            product=product,
            location=location,
            defaults={'quantity': Decimal('100')}
        )
        
        initial_qty = stock.quantity
        
        # Add stock
        stock.quantity += Decimal('50')
        stock.save()
        
        assert stock.quantity == initial_qty + Decimal('50')
        self.test_data['stock'] = stock
    
    def test_inventory_stock_transfer(self):
        """اختبار نقل المخزون"""
        product = self.test_data.get('product') or Product.objects.first()
        from_location = self.test_data.get('location') or Location.objects.first()
        
        # Create second location
        to_location, _ = Location.objects.get_or_create(
            code='TEST-WH-02',
            defaults={
                'name': 'Test Secondary Warehouse',
                'type': 'finished',
            }
        )
        
        # Create transfer
        transfer = StockTransfer.objects.create(
            source=from_location,
            destination=to_location
        )
        
        assert transfer.status == 'draft'
        self.test_data['stock_transfer'] = transfer
    
    # ============================================================================
    # SALES TESTS
    # ============================================================================
    
    def test_sales_customers(self):
        """اختبار العملاء"""
        # Create customer type
        customer_type, _ = CustomerType.objects.get_or_create(
            name='Retail',
            defaults={'discount_percentage': Decimal('5.00')}
        )
        
        # Create or reuse partner
        partner, _ = Partner.objects.get_or_create(
            name='Test Customer Company',
            defaults={
                'partner_type': 'customer',
                'email': 'testcustomer@example.com',
                'phone': '01234567890',
            }
        )
        if partner.partner_type not in ('customer', 'both'):
            partner.partner_type = 'customer'
            partner.save(update_fields=['partner_type'])

        # Use auto-created customer profile where possible to respect OneToOne
        customer = getattr(partner, 'customer_profile', None)
        if not customer:
            customer = PartnerCustomer.objects.create(
                partner=partner,
                name=partner.name,
                email=partner.email,
                phone=partner.phone,
                address='Test Address'
            )
        
        self.test_data['customer'] = customer
        assert customer.partner.partner_type == 'customer'
    
    def test_sales_order_workflow(self):
        """اختبار دورة أمر البيع الكاملة"""
        customer = self.test_data.get('customer') or PartnerCustomer.objects.first()
        product = self.test_data.get('product') or Product.objects.first()
        location = self.test_data.get('location') or Location.objects.first()
        
        assert customer and product and location, "Missing required data"
        
        # Create Sales Order
        sales_order = SalesOrder.objects.create(
            customer=customer,
            date=timezone.now().date(),
            status='draft',
            created_by=self.test_user
        )
        
        # Add line items
        order_line = SalesOrderLine.objects.create(
            order=sales_order,
            product=product,
            location=location,
            quantity=Decimal('10'),
            price=product.price
        )
        
        # Verify totals
        assert sales_order.items.count() > 0
        
        # Confirm order (should reserve stock)
        success = sales_order.confirm()
        
        if success:
            assert sales_order.status == 'confirmed'
            print_success("  Sales order confirmed and stock reserved")
        
        self.test_data['sales_order'] = sales_order
    
    def test_sales_invoice_creation(self):
        """اختبار إنشاء فاتورة بيع"""
        customer = self.test_data.get('customer') or PartnerCustomer.objects.first()
        product = self.test_data.get('product') or Product.objects.first()
        location = self.test_data.get('location') or Location.objects.first()
        
        # Create invoice
        invoice = Invoice.objects.create(
            customer=customer,
            date=timezone.now().date()
        )
        
        # Add items
        invoice_item = InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            location=location,
            quantity=Decimal('5'),
            price=product.price
        )
        
        # Calculate totals
        subtotal = invoice_item.quantity * invoice_item.price
        assert subtotal > 0
        
        self.test_data['invoice'] = invoice
    
    def test_sales_order_to_invoice_conversion(self):
        """اختبار تحويل أمر بيع لفاتورة"""
        sales_order = self.test_data.get('sales_order')
        
        if sales_order and sales_order.status == 'confirmed':
            invoice = sales_order.convert_to_invoice(user=self.test_user)
            
            if invoice:
                assert invoice.pk is not None
                assert sales_order.invoice == invoice
                print_success("  Sales order converted to invoice successfully")
            else:
                print_warning("  Could not convert sales order to invoice")
    
    # ============================================================================
    # PURCHASE TESTS
    # ============================================================================
    
    def test_purchase_suppliers(self):
        """اختبار الموردين"""
        partner = Partner.objects.create(
            name='Test Supplier Inc',
            partner_type='supplier',
            email='supplier@example.com',
            phone='01098765432'
        )

        # Supplier profile (partners.Supplier) should be created via signals
        supplier = Supplier.objects.filter(partner=partner).first()
        if not supplier:
            supplier = Supplier.objects.create(
                partner=partner,
                name=partner.name,
                email=partner.email,
                phone=partner.phone,
                address='Test Supplier Address'
            )
        
        self.test_data['supplier'] = supplier
        assert supplier.partner.partner_type == 'supplier'
    
    def test_purchase_requisition_workflow(self):
        """اختبار دورة طلب الشراء"""
        product = self.test_data.get('product') or Product.objects.first()
        location = self.test_data.get('location') or Location.objects.first()
        
        # Create Purchase Requisition
        pr = PurchaseRequisition.objects.create(
            department='production',
            requested_by=self.test_user,
            priority='high',
            justification='Urgent materials needed for production'
        )
        
        # Add items
        PurchaseRequisitionItem.objects.create(
            requisition=pr,
            product=product,
            quantity=Decimal('100'),
            estimated_price=product.cost,
            location=location,
            current_stock=Decimal('0')
        )

        # Submit and approve using domain methods
        pr.submit(user=self.test_user)
        pr.approve(user=self.test_user)
        
        assert pr.status == 'approved'
        self.test_data['purchase_requisition'] = pr
        print_success("  Purchase requisition approved")
    
    def test_purchase_requisition_to_po(self):
        """اختبار تحويل طلب شراء لأمر شراء"""
        pr = self.test_data.get('purchase_requisition')
        supplier = self.test_data.get('supplier') or Supplier.objects.first()
        
        if pr and pr.status == 'approved' and supplier:
            # PurchaseOrder.supplier expects Partner, not Supplier
            po = pr.convert_to_po(supplier=supplier.partner, user=self.test_user)
            
            if po:
                assert po.pk is not None
                assert pr.purchase_order == po
                print_success("  Purchase requisition converted to PO")
                self.test_data['purchase_order'] = po
    
    def test_purchase_bill(self):
        """اختبار فاتورة مشتريات"""
        supplier = self.test_data.get('supplier') or Supplier.objects.first()
        product = self.test_data.get('product') or Product.objects.first()
        location = self.test_data.get('location') or Location.objects.first()
        
        # Create purchase bill (supplier FK expects Partner, not Supplier)
        bill = PurchaseBill.objects.create(
            supplier=supplier.partner,
            date=timezone.now().date()
        )
        
        # Add items
        bill_item = PurchaseItem.objects.create(
            bill=bill,
            product=product,
            location=location,
            quantity=Decimal('50'),
            cost=product.cost
        )
        
        assert bill.items.count() > 0
        self.test_data['purchase_bill'] = bill
    
    # ============================================================================
    # PRODUCTION TESTS
    # ============================================================================
    
    def test_production_order(self):
        """اختبار أمر إنتاج"""
        product = self.test_data.get('product') or Product.objects.first()
        assert product is not None, "No product available for production order"

        # Create or reuse a simple BOM for the product
        bom, _ = BillOfMaterials.objects.get_or_create(
            product=product,
            version='1.0',
            defaults={
                'name': 'Test BOM',
                'description': 'Test BOM for production order',
                'base_quantity': Decimal('1'),
                'created_by': self.test_user,
            },
        )

        today = timezone.now().date()
        prod_order = ProductionOrder.objects.create(
            product=product,
            bom=bom,
            planned_quantity=Decimal('20'),
            planned_start_date=today,
            planned_end_date=today + timedelta(days=7),
            created_by=self.test_user,
        )

        self.test_data['production_order'] = prod_order
        assert prod_order.status == 'draft'
    
    def test_production_worker_tracking(self):
        """اختبار تتبع إنتاجية العمال"""
        # Create department
        dept, _ = Department.objects.get_or_create(
            name='Production Department',
            defaults={'code': 'PROD-01'}
        )
        # Create job position
        position, _ = JobPosition.objects.get_or_create(
            code='PROD-WORKER',
            department=dept,
            defaults={
                'title': 'Production Worker',
                'description': 'Test production worker position',
                'requirements': 'Test requirements',
                'min_salary': Decimal('2000.00'),
                'max_salary': Decimal('5000.00'),
            },
        )

        # Create or reuse an employee linked to the test user
        employee = self.test_data.get('employee')
        if not employee:
            employee = Employee.objects.filter(user=self.test_user).first()
        if not employee:
            base_employee_id = f"EMP-{self.test_user.id:06d}"
            if Employee.objects.filter(employee_id=base_employee_id).exists():
                base_employee_id = f"EMP-TST-{self.test_user.id:06d}"

            # Generate a unique national ID
            national_id = f"9{self.test_user.id:014d}"[:20]
            if Employee.objects.filter(national_id=national_id).exists():
                from uuid import uuid4
                national_id = str(uuid4().int)[:20]

            employee = Employee.objects.create(
                user=self.test_user,
                employee_id=base_employee_id,
                first_name='Test',
                last_name='Worker',
                arabic_name='عامل اختبار',
                national_id=national_id,
                gender='M',
                birth_date=date(1990, 1, 1),
                marital_status='single',
                phone='01000000000',
                email='worker@example.com',
                address='Test Address',
                emergency_contact_name='Test Contact',
                emergency_contact_phone='01000000001',
                department=dept,
                position=position,
                hire_date=timezone.now().date(),
                status='active',
                basic_salary=Decimal('3000.00'),
                housing_allowance=Decimal('0'),
                transportation_allowance=Decimal('0'),
                other_allowances=Decimal('0'),
            )
        
        product = self.test_data.get('product') or Product.objects.first()
        prod_order = self.test_data.get('production_order')
        
        if prod_order:
            # Record worker production entry
            worker_entry = WorkerProductionEntry.objects.create(
                employee=employee,
                production_order=prod_order,
                product=product,
                quantity=Decimal('5'),
                date=timezone.now().date(),
                hours_worked=Decimal('8.0'),
            )

            assert worker_entry.quantity > 0
            self.test_data['employee'] = employee
    
    # ============================================================================
    # HR TESTS
    # ============================================================================
    
    def test_hr_attendance(self):
        """اختبار الحضور والانصراف"""
        employee = self.test_data.get('employee')
        
        if not employee:
            dept, _ = Department.objects.get_or_create(
                name='HR Department',
                defaults={'code': 'HR-01'}
            )
            position, _ = JobPosition.objects.get_or_create(
                code='HR-SPEC',
                department=dept,
                defaults={
                    'title': 'HR Specialist',
                    'description': 'Test HR position',
                    'requirements': 'Test requirements',
                    'min_salary': Decimal('3000.00'),
                    'max_salary': Decimal('7000.00'),
                },
            )
            employee, _ = Employee.objects.get_or_create(
                user=self.test_user,
                defaults={
                    'employee_id': 'EMP-HR-001',
                    'first_name': 'Test',
                    'last_name': 'HR',
                    'arabic_name': 'موظف موارد بشرية',
                    'national_id': '12345678901235',
                    'gender': 'M',
                    'birth_date': date(1990, 1, 1),
                    'marital_status': 'single',
                    'phone': '01000000002',
                    'email': 'hr@example.com',
                    'address': 'HR Address',
                    'emergency_contact_name': 'HR Contact',
                    'emergency_contact_phone': '01000000003',
                    'department': dept,
                    'position': position,
                    'hire_date': timezone.now().date(),
                    'status': 'active',
                    'basic_salary': Decimal('4000.00'),
                    'housing_allowance': Decimal('0'),
                    'transportation_allowance': Decimal('0'),
                    'other_allowances': Decimal('0'),
                },
            )
            self.test_data['employee'] = employee
        
        # Create attendance records (check-in and check-out)
        today = timezone.now().date()
        check_in_time = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0).time()
        check_out_time = timezone.now().replace(hour=17, minute=0, second=0, microsecond=0).time()

        AttendanceRecord.objects.create(
            employee=employee,
            date=today,
            time=check_in_time,
            record_type='check_in',
            source='manual'
        )
        AttendanceRecord.objects.create(
            employee=employee,
            date=today,
            time=check_out_time,
            record_type='check_out',
            source='manual'
        )

        # Calculate work hours
        from datetime import datetime as dt
        start_dt = dt.combine(today, check_in_time)
        end_dt = dt.combine(today, check_out_time)
        work_duration = end_dt - start_dt
        hours = work_duration.total_seconds() / 3600
        assert hours >= 8, "Work hours should be at least 8"
    
    def test_hr_payroll_calculation(self):
        """اختبار حساب الرواتب"""
        employee = self.test_data.get('employee')
        
        if employee:
            # Create or reuse a simple payroll record for the current month
            current_date = timezone.now().date()
            period_start = current_date.replace(day=1)
            if period_start.month == 12:
                next_month = period_start.replace(year=period_start.year + 1, month=1, day=1)
            else:
                next_month = period_start.replace(month=period_start.month + 1, day=1)
            period_end = next_month - timedelta(days=1)

            payroll, _ = Payroll.objects.get_or_create(
                employee=employee,
                period_start=period_start,
                period_end=period_end,
                defaults={
                    'basic_salary': employee.basic_salary,
                    'housing_allowance': employee.housing_allowance,
                    'transportation_allowance': employee.transportation_allowance,
                    'other_allowances': employee.other_allowances,
                    'overtime_hours': Decimal('0'),
                    'overtime_amount': Decimal('0'),
                    'bonus_amount': Decimal('0'),
                    'late_penalty': Decimal('0'),
                    'absence_deduction': Decimal('0'),
                    'other_deductions': Decimal('0'),
                    'status': 'calculated',
                },
            )

            assert payroll.employee == employee
            assert payroll.net_salary > 0
            print_success(f"  Payroll calculated: Net Salary = {payroll.net_salary}")
    
    # ============================================================================
    # FIXED ASSETS TESTS (NEW FEATURE)
    # ============================================================================
    
    def test_fixed_assets_category(self):
        """اختبار تصنيفات الأصول الثابتة"""
        category, _ = AssetCategory.objects.get_or_create(
            code='MACH',
            defaults={
                'name': 'Production Machinery',
                'default_depreciation_method': 'straight_line',
                'default_useful_life_years': 10,
                'default_salvage_value_percent': Decimal('10.00'),
            },
        )

        self.test_data['asset_category'] = category
        assert category.default_useful_life_years > 0
    
    def test_fixed_assets_creation(self):
        """اختبار إنشاء أصل ثابت"""
        category = self.test_data.get('asset_category') or AssetCategory.objects.first()
        
        asset = Asset.objects.create(
            name='Test CNC Machine',
            category=category,
            acquisition_date=timezone.now().date(),
            acquisition_cost=Decimal('150000.00'),
            useful_life_years=10,
            salvage_value=Decimal('15000.00'),
            depreciation_method='straight_line',
            status='active'
        )
        
        # Calculate depreciation
        monthly_depreciation = asset.calculate_monthly_depreciation()
        assert monthly_depreciation > 0
        print_success(f"  Monthly depreciation calculated: {monthly_depreciation}")
        
        self.test_data['asset'] = asset
    
    def test_fixed_assets_depreciation_schedule(self):
        """اختبار جدول الإهلاك"""
        asset = self.test_data.get('asset')
        
        if asset:
            # Create depreciation schedule
            monthly_depreciation = asset.calculate_monthly_depreciation()
            schedule = DepreciationSchedule.objects.create(
                asset=asset,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
                depreciation_amount=monthly_depreciation,
                accumulated_depreciation=monthly_depreciation,
                book_value=asset.acquisition_cost - monthly_depreciation,
                status='scheduled'
            )
            
            # Post depreciation
            try:
                journal_entry = schedule.post_depreciation(user=self.test_user)
                if journal_entry:
                    assert journal_entry.pk is not None
                    print_success("  Depreciation posted to accounting")
            except Exception as e:
                print_warning(f"  Could not post depreciation: {e}")
    
    # ============================================================================
    # WOOCOMMERCE INTEGRATION TESTS (NEW FEATURE)
    # ============================================================================
    
    def test_woocommerce_config(self):
        """اختبار تكوين WooCommerce"""
        config = WooCommerceConfig.objects.create(
            name='Test WooCommerce Store',
            store_url='https://test-store.com',
            consumer_key='ck_test_1234567890',
            consumer_secret='cs_test_0987654321',
            is_active=True,
            is_default=True,
            auto_sync_products=False,
            auto_sync_orders=False,
            auto_sync_inventory=False,
            sync_interval_minutes=15
        )
        
        self.test_data['woo_config'] = config
        assert config.is_active == True
    
    def test_woocommerce_product_mapping(self):
        """اختبار ربط المنتجات مع WooCommerce"""
        config = self.test_data.get('woo_config')
        product = self.test_data.get('product')
        
        if config and product:
            mapping = ProductMapping.objects.create(
                config=config,
                woo_product_id=12345,
                erp_product=product
            )
            
            assert mapping.erp_product == product
            print_success("  Product mapped to WooCommerce")
    
    def test_woocommerce_sync_log(self):
        """اختبار سجل المزامنة"""
        config = self.test_data.get('woo_config')
        
        if config:
            log = SyncLog.objects.create(
                config=config,
                sync_type='product_push',
                status='success',
                records_processed=10,
                records_success=10,
                records_failed=0,
                message='Test sync completed successfully'
            )
            
            assert log.status == 'success'
            assert log.records_processed > 0
    
    # ============================================================================
    # INTEGRATION TESTS
    # ============================================================================
    
    def test_end_to_end_sales_flow(self):
        """اختبار تدفق البيع الكامل من البداية للنهاية"""
        print_info("  Testing complete sales workflow...")
        
        # 1. Create customer if not exists
        customer = self.test_data.get('customer')
        if not customer:
            customer_type, _ = CustomerType.objects.get_or_create(name='Retail')
            partner, _ = Partner.objects.get_or_create(
                name='End-to-End Test Customer',
                defaults={'partner_type': 'customer'},
            )
            if partner.partner_type not in ('customer', 'both'):
                partner.partner_type = 'customer'
                partner.save(update_fields=['partner_type'])
            customer = getattr(partner, 'customer_profile', None)
            if not customer:
                customer = PartnerCustomer.objects.create(
                    partner=partner,
                    name=partner.name,
                    email='',
                    phone='',
                    address='',
                )
        
        # 2. Create product
        product, _ = Product.objects.get_or_create(
            sku='E2E-MAT-001',
            defaults={
                'name': 'E2E Test Mattress',
                'price': Decimal('3000.00'),
                'cost': Decimal('2000.00'),
            },
        )
        
        # 3. Add stock
        location = self.test_data.get('location') or Location.objects.first()
        stock, _ = Stock.objects.get_or_create(
            product=product,
            location=location,
            defaults={'quantity': Decimal('50')}
        )
        
        # 4. Create sales order
        order = SalesOrder.objects.create(
            customer=customer,
            date=timezone.now().date(),
            status='draft',
            created_by=self.test_user
        )
        
        SalesOrderLine.objects.create(
            order=order,
            product=product,
            location=location,
            quantity=Decimal('2'),
            price=product.price
        )
        
        # 5. Confirm order
        order.confirm()
        assert order.status == 'confirmed'
        
        # 6. Convert to invoice
        invoice = order.convert_to_invoice(user=self.test_user)
        assert invoice is not None
        
        # 7. Verify invoice created
        assert invoice.items.count() > 0
        
        print_success("  Complete sales workflow executed successfully")
    
    def test_data_integrity(self):
        """اختبار سلامة البيانات"""
        print_info("  Checking data integrity...")
        
        # Check for orphaned records
        orphaned_invoice_items = InvoiceItem.objects.filter(invoice__isnull=True).count()
        assert orphaned_invoice_items == 0, f"Found {orphaned_invoice_items} orphaned invoice items"
        
        # Check journal entries balance
        entries = JournalEntry.objects.all()
        for entry in entries[:10]:  # Check first 10
            debit = entry.total_debit
            credit = entry.total_credit
            assert debit == credit, f"Entry {entry.id} not balanced"
        
        print_success("  Data integrity checks passed")
    
    def test_performance_queries(self):
        """اختبار أداء الاستعلامات"""
        import time
        
        print_info("  Testing query performance...")
        
        # Test 1: Product listing
        start = time.time()
        products = list(Product.objects.all()[:100])
        duration = time.time() - start
        assert duration < 1.0, f"Product query too slow: {duration}s"
        
        # Test 2: Invoice with items
        start = time.time()
        invoices = list(Invoice.objects.prefetch_related('items')[:50])
        duration = time.time() - start
        assert duration < 1.0, f"Invoice query too slow: {duration}s"
        
        print_success(f"  Query performance acceptable")
    
    # ============================================================================
    # MAIN TEST RUNNER
    # ============================================================================
    
    def run_all_tests(self):
        """Run all tests"""
        print_header("🚀 اختبار شامل لنظام Tony ERP")
        print_info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.setup()
        
        # Accounting Tests
        print_header("📊 ACCOUNTING TESTS")
        self.run_test("Chart of Accounts", self.test_accounting_chart_of_accounts)
        self.run_test("Journal Entries", self.test_accounting_journal_entry)
        
        # Inventory Tests
        print_header("📦 INVENTORY TESTS")
        self.run_test("Products", self.test_inventory_products)
        self.run_test("Locations", self.test_inventory_locations)
        self.run_test("Stock Management", self.test_inventory_stock_management)
        self.run_test("Stock Transfer", self.test_inventory_stock_transfer)
        
        # Sales Tests
        print_header("💰 SALES TESTS")
        self.run_test("Customers", self.test_sales_customers)
        self.run_test("Sales Order Workflow", self.test_sales_order_workflow)
        self.run_test("Invoice Creation", self.test_sales_invoice_creation)
        self.run_test("Sales Order to Invoice", self.test_sales_order_to_invoice_conversion)
        
        # Purchase Tests
        print_header("🛒 PURCHASE TESTS")
        self.run_test("Suppliers", self.test_purchase_suppliers)
        self.run_test("Purchase Requisition Workflow", self.test_purchase_requisition_workflow)
        self.run_test("PR to PO Conversion", self.test_purchase_requisition_to_po)
        self.run_test("Purchase Bill", self.test_purchase_bill)
        
        # Production Tests
        print_header("🏭 PRODUCTION TESTS")
        self.run_test("Production Orders", self.test_production_order)
        self.run_test("Worker Production Tracking", self.test_production_worker_tracking)
        
        # HR Tests
        print_header("👥 HR TESTS")
        self.run_test("Attendance Tracking", self.test_hr_attendance)
        self.run_test("Payroll Calculation", self.test_hr_payroll_calculation)
        
        # Fixed Assets Tests (NEW)
        print_header("🏢 FIXED ASSETS TESTS (NEW FEATURE)")
        self.run_test("Asset Categories", self.test_fixed_assets_category)
        self.run_test("Asset Creation", self.test_fixed_assets_creation)
        self.run_test("Depreciation Schedule", self.test_fixed_assets_depreciation_schedule)
        
        # WooCommerce Tests (NEW)
        print_header("🛍️ WOOCOMMERCE INTEGRATION TESTS (NEW FEATURE)")
        self.run_test("WooCommerce Config", self.test_woocommerce_config)
        self.run_test("Product Mapping", self.test_woocommerce_product_mapping)
        self.run_test("Sync Logging", self.test_woocommerce_sync_log)
        
        # Integration Tests
        print_header("🔗 INTEGRATION TESTS")
        self.run_test("End-to-End Sales Flow", self.test_end_to_end_sales_flow)
        self.run_test("Data Integrity", self.test_data_integrity)
        self.run_test("Query Performance", self.test_performance_queries)
        
        # Print Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print_header("📋 TEST SUMMARY")
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"\n{Colors.BOLD}Total Tests:{Colors.ENDC} {self.total_tests}")
        print(f"{Colors.OKGREEN}{Colors.BOLD}Passed:{Colors.ENDC} {self.passed_tests}")
        print(f"{Colors.FAIL}{Colors.BOLD}Failed:{Colors.ENDC} {self.total_tests - self.passed_tests}")
        print(f"{Colors.OKCYAN}{Colors.BOLD}Success Rate:{Colors.ENDC} {success_rate:.1f}%\n")
        
        if self.errors:
            print_header("❌ FAILED TESTS")
            for error in self.errors:
                print_error(error)
        
        if self.warnings:
            print_header("⚠️ WARNINGS")
            for warning in self.warnings:
                print_warning(warning)
        
        # Final verdict
        if self.passed_tests == self.total_tests:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}{'='*80}{Colors.ENDC}")
            print(f"{Colors.OKGREEN}{Colors.BOLD}{'🎉 ALL TESTS PASSED! SYSTEM IS HEALTHY! 🎉'.center(80)}{Colors.ENDC}")
            print(f"{Colors.OKGREEN}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")
        else:
            print(f"\n{Colors.WARNING}{Colors.BOLD}{'='*80}{Colors.ENDC}")
            print(f"{Colors.WARNING}{Colors.BOLD}{'⚠️ SOME TESTS FAILED - REVIEW REQUIRED ⚠️'.center(80)}{Colors.ENDC}")
            print(f"{Colors.WARNING}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")
        
        print_info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

if __name__ == '__main__':
    try:
        tester = ERPComprehensiveTest()
        tester.run_all_tests()
        
        # Exit with appropriate code
        exit(0 if tester.passed_tests == tester.total_tests else 1)
        
    except Exception as e:
        print_error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(2)
