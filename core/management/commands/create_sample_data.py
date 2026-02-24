from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Product, Location, Stock
from partners.models import Customer, Supplier
from sales.models import Invoice, InvoiceItem
from purchases.models import PurchaseBill, PurchaseItem
from accounting.models import Revenue, Expense
from core.models import Company
from decimal import Decimal
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Create sample data for testing the system'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create superuser if not exists
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write('تم إنشاء مستخدم المدير (اسم المستخدم: admin, كلمة المرور: admin123)')
        
        # Create company
        company, created = Company.objects.get_or_create(
            name='شركة التجارة الذكية',
            defaults={
                'address': 'الرياض، المملكة العربية مصر',
                'phone': '+966501234567',
                'tax_id': '1234567890123',
                'invoice_prefix': 'INV'
            }
        )
        if created:
            self.stdout.write('تم إنشاء الشركة')

        # Create locations
        locations_data = [
            {'name': 'المستودع الرئيسي', 'code': 'MAIN001', 'address': 'المستودع الرئيسي - الرياض'},
            {'name': 'فرع الشمال', 'code': 'NORTH01', 'address': 'فرع الشمال - الرياض'},
            {'name': 'فرع الجنوب', 'code': 'SOUTH01', 'address': 'فرع الجنوب - الرياض'},
            {'name': 'متجر الشرق', 'code': 'EAST001', 'address': 'متجر الشرق - الدمام'},
        ]
        
        locations = []
        for loc_data in locations_data:
            location, created = Location.objects.get_or_create(
                code=loc_data['code'],
                defaults=loc_data
            )
            locations.append(location)
            if created:
                self.stdout.write(f'تم إنشاء الموقع: {location.name}')

        # Create products
        products_data = [
            {'sku': 'LAPTOP001', 'name': 'لابتوب ديل إنسبايرون', 'description': 'لابتوب للأعمال والدراسة', 'price': 2500, 'cost': 2000, 'min_stock': 5},
            {'sku': 'MOUSE001', 'name': 'ماوس لوجيتك لاسلكي', 'description': 'ماوس لاسلكي عالي الدقة', 'price': 120, 'cost': 80, 'min_stock': 20},
            {'sku': 'KEYB001', 'name': 'كيبورد مكانيكي', 'description': 'كيبورد مكانيكي للألعاب', 'price': 350, 'cost': 250, 'min_stock': 15},
            {'sku': 'MONITOR01', 'name': 'شاشة سامسونج 24 بوصة', 'description': 'شاشة LED عالية الدقة', 'price': 800, 'cost': 600, 'min_stock': 8},
            {'sku': 'SPEAKER01', 'name': 'سماعات بلوتوث', 'description': 'سماعات لاسلكية عالية الجودة', 'price': 180, 'cost': 120, 'min_stock': 25},
            {'sku': 'TABLET01', 'name': 'تابلت سامسونج', 'description': 'تابلت للقراءة والعمل', 'price': 1200, 'cost': 950, 'min_stock': 10},
            {'sku': 'PHONE001', 'name': 'هاتف ذكي', 'description': 'هاتف ذكي متطور', 'price': 2800, 'cost': 2200, 'min_stock': 12},
            {'sku': 'CABLE001', 'name': 'كابل USB-C', 'description': 'كابل شحن وبيانات', 'price': 45, 'cost': 25, 'min_stock': 50},
            {'sku': 'HDISK001', 'name': 'هارد ديسك خارجي', 'description': 'هارد ديسك 1 تيرا', 'price': 300, 'cost': 220, 'min_stock': 15},
            {'sku': 'ROUTER01', 'name': 'راوتر واي فاي', 'description': 'راوتر لاسلكي عالي السرعة', 'price': 280, 'cost': 200, 'min_stock': 20},
        ]
        
        products = []
        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                sku=prod_data['sku'],
                defaults=prod_data
            )
            products.append(product)
            if created:
                self.stdout.write(f'تم إنشاء المنتج: {product.name}')

        # Create stock for products
        for product in products:
            for location in locations:
                stock_qty = random.randint(0, 50)
                stock, created = Stock.objects.get_or_create(
                    product=product,
                    location=location,
                    defaults={'quantity': stock_qty}
                )
                if created:
                    self.stdout.write(f'تم إنشاء مخزون: {product.name} @ {location.name} = {stock_qty}')

        # Create customers
        customers_data = [
            {'name': 'شركة التقنيات المتطورة', 'email': 'info@techadvanced.sa', 'phone': '+966501111111'},
            {'name': 'مؤسسة الأعمال الرقمية', 'email': 'contact@digitalbiz.sa', 'phone': '+966502222222'},
            {'name': 'شركة الحلول الذكية', 'email': 'sales@smartsolutions.sa', 'phone': '+966503333333'},
            {'name': 'معهد التدريب التقني', 'email': 'orders@techtraining.sa', 'phone': '+966504444444'},
            {'name': 'جامعة المعرفة', 'email': 'procurement@knowledgeuni.sa', 'phone': '+966505555555'},
        ]
        
        customers = []
        for cust_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                name=cust_data['name'],
                defaults=cust_data
            )
            customers.append(customer)
            if created:
                self.stdout.write(f'تم إنشاء العميل: {customer.name}')

        # Create suppliers
        suppliers_data = [
            {'name': 'مورد الإلكترونيات الأول', 'email': 'sales@electronics1.sa', 'phone': '+966506666666'},
            {'name': 'شركة الاستيراد التقني', 'email': 'import@techimport.sa', 'phone': '+966507777777'},
            {'name': 'مؤسسة التوزيع الشامل', 'email': 'wholesale@distribution.sa', 'phone': '+966508888888'},
        ]
        
        suppliers = []
        for supp_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=supp_data['name'],
                defaults=supp_data
            )
            suppliers.append(supplier)
            if created:
                self.stdout.write(f'تم إنشاء المورد: {supplier.name}')

        # Create sample invoices
        for i in range(15):
            invoice_date = date.today() - timedelta(days=random.randint(0, 30))
            customer = random.choice(customers)
            
            invoice, created = Invoice.objects.get_or_create(
                number=f'INV-{str(i+1).zfill(6)}',
                defaults={
                    'customer': customer,
                    'date': invoice_date,
                    'due_date': invoice_date + timedelta(days=30),
                    'discount': Decimal(random.randint(0, 100)),
                    'paid': Decimal(random.randint(0, 1000))
                }
            )
            
            if created:
                # Add random items to invoice
                for j in range(random.randint(1, 4)):
                    product = random.choice(products)
                    location = random.choice(locations)
                    quantity = random.randint(1, 5)
                    
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        location=location,
                        quantity=quantity,
                        price=product.price
                    )
                
                self.stdout.write(f'تم إنشاء الفاتورة: {invoice.number}')

        # Create sample purchase bills
        for i in range(10):
            bill_date = date.today() - timedelta(days=random.randint(0, 60))
            supplier = random.choice(suppliers)
            
            bill, created = PurchaseBill.objects.get_or_create(
                number=f'PB-{str(i+1).zfill(6)}',
                defaults={
                    'supplier': supplier,
                    'date': bill_date,
                    'discount': Decimal(random.randint(0, 50)),
                    'paid': Decimal(random.randint(0, 2000))
                }
            )
            
            if created:
                # Add random items to purchase bill
                for j in range(random.randint(1, 3)):
                    product = random.choice(products)
                    location = random.choice(locations)
                    quantity = random.randint(5, 20)
                    
                    PurchaseItem.objects.create(
                        bill=bill,
                        product=product,
                        location=location,
                        quantity=quantity,
                        cost=product.cost
                    )
                
                self.stdout.write(f'تم إنشاء فاتورة شراء: {bill.number}')

        self.stdout.write(
            self.style.SUCCESS('\nتم إنشاء البيانات التجريبية بنجاح\n')
        )
        self.stdout.write('يمكنك الآن:')
        self.stdout.write('- تسجيل الدخول: admin / admin123')
        self.stdout.write('- استعراض المنتجات والمخزون')
        self.stdout.write('- عرض فواتير المبيعات والمشتريات النموذجية')
        self.stdout.write('- فحص إحصائيات لوحة التحكم')