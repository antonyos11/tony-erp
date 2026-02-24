"""
اختبارات التكامل بين الوحدات
============================
تختبر تكامل العمليات عبر وحدات مختلفة من النظام
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta


# ===============================
# اختبارات تكامل المبيعات والمخزون
# ===============================

class SalesInventoryIntegrationTestCase(TransactionTestCase):
    """اختبارات تكامل المبيعات مع المخزون"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('sales_user', 'sales@test.com', 'pass123')
        
        from inventory.models import Product, Category, Location, Stock
        self.category = Category.objects.create(name='منتجات مبيعات')
        self.product = Product.objects.create(
            name='منتج للبيع',
            sku='SALES-INT-001',
            category=self.category,
            cost=Decimal('100'),
            price=Decimal('150')
        )
        
        self.location = Location.objects.create(name='مخزن المبيعات', code='WH-SALES-INT')
        self.stock = Stock.objects.create(
            product=self.product,
            location=self.location,
            quantity=Decimal('100')
        )
    
    def test_stock_exists(self):
        """اختبار وجود المخزون"""
        from inventory.models import Stock
        stock = Stock.objects.get(product=self.product, location=self.location)
        self.assertEqual(stock.quantity, Decimal('100'))
    
    def test_product_cost_price_set(self):
        """اختبار أن تكلفة المنتج محددة"""
        self.assertEqual(self.product.cost, Decimal('100'))
        self.assertEqual(self.product.price, Decimal('150'))


# ===============================
# اختبارات تكامل الإنتاج والمخزون
# ===============================

class ProductionInventoryIntegrationTestCase(TransactionTestCase):
    """اختبارات تكامل الإنتاج مع المخزون"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('prod_user', 'prod@test.com', 'pass123')
        
        from inventory.models import Product, Category, Location, Stock
        self.category = Category.objects.create(name='منتجات تامة')
        self.raw_category = Category.objects.create(name='مواد خام')
        
        self.finished_product = Product.objects.create(
            name='منتج تام',
            sku='FIN-INT-001',
            category=self.category,
            cost=Decimal('200')
        )
        
        self.raw_material = Product.objects.create(
            name='مادة خام',
            sku='RAW-INT-001',
            category=self.raw_category,
            cost=Decimal('20')
        )
        
        self.location = Location.objects.create(name='مخزن الإنتاج', code='WH-PROD-INT')
        self.raw_stock = Stock.objects.create(
            product=self.raw_material,
            location=self.location,
            quantity=Decimal('500')
        )
        
        from production.models import BillOfMaterials, BOMItem
        self.bom = BillOfMaterials.objects.create(
            product=self.finished_product,
            version='1.0',
            name='وصفة المنتج',
            base_quantity=Decimal('1'),
            is_default=True,
            created_by=self.user
        )
        
        self.bom_item = BOMItem.objects.create(
            bom=self.bom,
            material=self.raw_material,
            quantity=Decimal('5'),
            unit_cost=Decimal('20')
        )
    
    def test_bom_items_created(self):
        """اختبار إنشاء عناصر قائمة المواد"""
        self.assertEqual(self.bom.items.count(), 1)
        self.assertEqual(self.bom_item.quantity, Decimal('5'))
    
    def test_bom_cost_calculation(self):
        """اختبار حساب تكلفة BOM"""
        # تكلفة المواد = 5 * 20 = 100
        total_material_cost = sum(item.total_cost for item in self.bom.items.all())
        self.assertEqual(total_material_cost, Decimal('100'))


# ===============================
# اختبارات تكامل الشركاء
# ===============================

class PartnersIntegrationTestCase(TransactionTestCase):
    """اختبارات تكامل الشركاء"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        from partners.models import Partner, Customer, Supplier
        
        self.customer_partner = Partner.objects.create(
            name='شريك عميل',
            partner_type='customer',
            email='customer_partner@test.com'
        )
        
        self.customer = Customer.objects.create(
            partner=self.customer_partner,
            name='عميل تكامل',
            email='customer_int@test.com'
        )
        
        self.supplier = Supplier.objects.create(
            name='مورد تكامل',
            email='supplier_int@test.com',
            supply_type='raw_materials'
        )
    
    def test_customer_linked_to_partner(self):
        """اختبار ربط العميل بالشريك"""
        self.assertEqual(self.customer.partner, self.customer_partner)
    
    def test_supplier_created(self):
        """اختبار إنشاء المورد"""
        self.assertEqual(self.supplier.supply_type, 'raw_materials')


# ===============================
# اختبارات تكامل الموارد البشرية
# ===============================

class HRIntegrationTestCase(TransactionTestCase):
    """اختبارات تكامل الموارد البشرية"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('hr_user', 'hr@test.com', 'pass123')
        
        from hr.models import Department, JobPosition, Employee
        
        self.department = Department.objects.create(
            name='قسم الإنتاج',
            code='PROD-DEPT'
        )
        
        self.position = JobPosition.objects.create(
            title='عامل إنتاج',
            code='PROD-WRK-001',
            department=self.department,
            description='عامل في خط الإنتاج',
            requirements='خبرة سنة'
        )
        
        self.employee = Employee.objects.create(
            user=self.user,
            employee_id='EMP-INT-001',
            first_name='محمد',
            last_name='أحمد',
            arabic_name='محمد أحمد',
            national_id='1234567890',
            gender='M',
            birth_date=date(1990, 1, 1),
            marital_status='single',
            phone='0501234567',
            email='mohammed@test.com',
            address='الرياض',
            emergency_contact_name='علي',
            emergency_contact_phone='0509876543',
            department=self.department,
            position=self.position,
            hire_date=date.today() - timedelta(days=365),
            basic_salary=5000
        )
    
    def test_employee_department_assignment(self):
        """اختبار تعيين الموظف للقسم"""
        self.assertEqual(self.employee.department, self.department)
        self.assertEqual(self.employee.position, self.position)
    
    def test_employee_linked_to_user(self):
        """اختبار ربط الموظف بالمستخدم"""
        self.assertEqual(self.employee.user, self.user)


# ===============================
# اختبارات تكامل الضرائب
# ===============================

class TaxIntegrationTestCase(TransactionTestCase):
    """اختبارات تكامل الضرائب"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('tax_user', 'tax@test.com', 'pass123')
        
        from taxes.models import TaxSettings, TaxCategory
        
        self.tax_settings = TaxSettings.objects.create(
            tax_registration_number='123456789',
            default_vat_rate=Decimal('15.00')
        )
        
        self.tax_category = TaxCategory.objects.create(
            name='ضريبة قياسية',
            code='VAT-STD-INT',
            rate=Decimal('15.00')
        )
    
    def test_tax_settings_created(self):
        """اختبار إنشاء إعدادات الضريبة"""
        self.assertEqual(self.tax_settings.default_vat_rate, Decimal('15.00'))
    
    def test_tax_category_rate(self):
        """اختبار معدل فئة الضريبة"""
        self.assertEqual(self.tax_category.rate, Decimal('15.00'))
    
    def test_vat_calculation(self):
        """اختبار حساب ضريبة القيمة المضافة"""
        net_amount = Decimal('1000.00')
        vat_amount = net_amount * self.tax_settings.default_vat_rate / 100
        self.assertEqual(vat_amount, Decimal('150.00'))


# ===============================
# اختبارات التحقق من التكامل
# ===============================

class CrossModuleValidationTestCase(TransactionTestCase):
    """اختبارات التحقق من التكامل عبر الوحدات"""
    
    def test_product_in_bom(self):
        """اختبار استخدام منتج في قائمة مواد"""
        from inventory.models import Product, Category
        from production.models import BillOfMaterials, BOMItem
        
        category = Category.objects.create(name='منتجات تحقق')
        finished = Product.objects.create(
            name='منتج نهائي',
            sku='VALID-FIN-001',
            category=category
        )
        material = Product.objects.create(
            name='مادة خام',
            sku='VALID-RAW-001',
            category=category,
            cost=Decimal('10')
        )
        
        bom = BillOfMaterials.objects.create(
            product=finished,
            version='1.0',
            name='وصفة تحقق'
        )
        
        item = BOMItem.objects.create(
            bom=bom,
            material=material,
            quantity=Decimal('3'),
            unit_cost=Decimal('10')
        )
        
        self.assertEqual(item.total_cost, Decimal('30'))
    
    def test_employee_attendance(self):
        """اختبار حضور الموظف"""
        from hr.models import Department, Employee, AttendanceRecord, JobPosition
        from django.utils import timezone
        
        user = User.objects.create_user('attend_user', 'attend@test.com', 'pass123')
        
        dept = Department.objects.create(name='قسم اختبار', code='TEST-DEPT-ATT')
        
        position = JobPosition.objects.create(
            title='موظف اختبار',
            code='TEST-POS-ATT',
            department=dept,
            description='وصف',
            requirements='متطلبات'
        )
        
        emp = Employee.objects.create(
            user=user,
            employee_id='EMP-ATTEND-001',
            first_name='فهد',
            last_name='علي',
            arabic_name='فهد علي',
            national_id='9876543210',
            gender='M',
            birth_date=date(1995, 5, 15),
            marital_status='single',
            phone='0507654321',
            email='fahad@test.com',
            address='جدة',
            emergency_contact_name='سعد',
            emergency_contact_phone='0501112222',
            department=dept,
            position=position,
            hire_date=date.today(),
            basic_salary=4500
        )
        
        now = timezone.now()
        attendance = AttendanceRecord.objects.create(
            employee=emp,
            date=date.today(),
            time=now.time(),
            record_type='check_in',
            source='manual'
        )
        
        self.assertIsNotNone(attendance.time)
        self.assertEqual(attendance.employee, emp)
        self.assertEqual(attendance.record_type, 'check_in')
