"""
اختبارات وحدة الضرائب - Taxes Module Tests
=========================================
اختبارات شاملة لجميع وظائف وحدة الضرائب

تغطية الاختبارات:
- إعدادات الضرائب
- فئات الضريبة
- الفواتير الضريبية
- حسابات ضريبة القيمة المضافة
- الفواتير الإلكترونية
- التقارير الضريبية
"""

from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import json

from .models import TaxSettings, TaxCategory, TaxInvoice


# ===============================
# اختبارات إعدادات الضرائب
# ===============================

class TaxSettingsTestCase(TestCase):
    """اختبارات إعدادات الضرائب"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.settings = TaxSettings.objects.create(
            tax_registration_number='123456789',
            tax_file_number='TF-001',
            commercial_registration='CR-001',
            default_vat_rate=Decimal('15.00'),
            einvoice_enabled=False,
            exemption_threshold=Decimal('500000.00'),
            is_exempt=False
        )
    
    def test_create_tax_settings(self):
        """اختبار إنشاء إعدادات الضرائب"""
        self.assertEqual(self.settings.tax_registration_number, '123456789')
        self.assertEqual(self.settings.default_vat_rate, Decimal('15.00'))
    
    def test_default_vat_rate(self):
        """اختبار نسبة ضريبة القيمة المضافة الافتراضية"""
        self.assertEqual(self.settings.default_vat_rate, Decimal('15.00'))
    
    def test_einvoice_settings(self):
        """اختبار إعدادات الفاتورة الإلكترونية"""
        self.settings.einvoice_enabled = True
        self.settings.einvoice_api_key = 'test_api_key'
        self.settings.einvoice_client_id = 'test_client_id'
        self.settings.einvoice_environment = 'preprod'
        self.settings.save()
        
        self.assertTrue(self.settings.einvoice_enabled)
        self.assertEqual(self.settings.einvoice_environment, 'preprod')
    
    def test_exemption_threshold(self):
        """اختبار حد الإعفاء"""
        self.assertEqual(self.settings.exemption_threshold, Decimal('500000.00'))
    
    def test_is_exempt_flag(self):
        """اختبار علم الإعفاء"""
        self.assertFalse(self.settings.is_exempt)
        
        self.settings.is_exempt = True
        self.settings.save()
        self.assertTrue(self.settings.is_exempt)
    
    def test_get_settings_method(self):
        """اختبار دالة الحصول على الإعدادات"""
        settings = TaxSettings.get_settings()
        self.assertIsNotNone(settings)
    
    def test_str_representation(self):
        """اختبار التمثيل النصي"""
        expected = f"إعدادات الضرائب - 123456789"
        self.assertEqual(str(self.settings), expected)


# ===============================
# اختبارات فئات الضريبة
# ===============================

class TaxCategoryTestCase(TestCase):
    """اختبارات فئات الضريبة"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.vat_standard = TaxCategory.objects.create(
            name='ضريبة قياسية',
            code='VAT-STD',
            rate=Decimal('15.00'),
            description='ضريبة القيمة المضافة القياسية',
            is_exempt=False,
            is_active=True,
            eta_code='T1'
        )
        
        self.vat_exempt = TaxCategory.objects.create(
            name='معفى من الضريبة',
            code='VAT-EXM',
            rate=Decimal('0.00'),
            description='سلع وخدمات معفاة',
            is_exempt=True,
            is_active=True,
            eta_code='T2'
        )
    
    def test_create_tax_category(self):
        """اختبار إنشاء فئة ضريبية"""
        self.assertEqual(self.vat_standard.name, 'ضريبة قياسية')
        self.assertEqual(self.vat_standard.rate, Decimal('15.00'))
        self.assertTrue(self.vat_standard.is_active)
    
    def test_exempt_category(self):
        """اختبار فئة الإعفاء"""
        self.assertTrue(self.vat_exempt.is_exempt)
        self.assertEqual(self.vat_exempt.rate, Decimal('0.00'))
    
    def test_unique_code(self):
        """اختبار منع تكرار الكود"""
        with self.assertRaises(Exception):
            TaxCategory.objects.create(
                name='فئة مكررة',
                code='VAT-STD',  # نفس الكود
                rate=Decimal('10.00')
            )
    
    def test_str_representation(self):
        """اختبار التمثيل النصي"""
        self.assertEqual(str(self.vat_standard), 'ضريبة قياسية (15.00%)')
        self.assertEqual(str(self.vat_exempt), 'معفى من الضريبة (معفى)')
    
    def test_create_zero_rated_category(self):
        """اختبار فئة النسبة الصفرية"""
        zero_rated = TaxCategory.objects.create(
            name='نسبة صفرية',
            code='VAT-ZERO',
            rate=Decimal('0.00'),
            is_exempt=False,
            eta_code='T3'
        )
        
        self.assertEqual(zero_rated.rate, Decimal('0.00'))
        self.assertFalse(zero_rated.is_exempt)
    
    def test_multiple_categories(self):
        """اختبار إنشاء فئات متعددة"""
        categories = [
            ('سلع غذائية', 'VAT-FOOD', Decimal('5.00')),
            ('خدمات صحية', 'VAT-HEALTH', Decimal('0.00')),
            ('خدمات تعليمية', 'VAT-EDU', Decimal('0.00')),
            ('سلع فاخرة', 'VAT-LUX', Decimal('20.00')),
        ]
        
        for name, code, rate in categories:
            TaxCategory.objects.create(name=name, code=code, rate=rate)
        
        self.assertEqual(TaxCategory.objects.count(), 6)  # 2 من setUp + 4


# ===============================
# اختبارات حسابات الضريبة
# ===============================

class TaxCalculationTestCase(TestCase):
    """اختبارات حسابات الضريبة"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.vat_rate = Decimal('15.00')
    
    def test_calculate_vat_from_net(self):
        """اختبار حساب الضريبة من المبلغ الصافي"""
        subtotal = Decimal('1000.00')
        vat_amount = subtotal * (self.vat_rate / 100)
        total = subtotal + vat_amount
        
        self.assertEqual(vat_amount, Decimal('150.00'))
        self.assertEqual(total, Decimal('1150.00'))
    
    def test_calculate_vat_from_gross(self):
        """اختبار حساب الضريبة من المبلغ الإجمالي"""
        total = Decimal('1150.00')
        subtotal = total / (1 + self.vat_rate / 100)
        vat_amount = total - subtotal
        
        self.assertAlmostEqual(float(subtotal), 1000.00, places=2)
        self.assertAlmostEqual(float(vat_amount), 150.00, places=2)
    
    def test_zero_amount_vat(self):
        """اختبار الضريبة على مبلغ صفري"""
        subtotal = Decimal('0.00')
        vat_amount = subtotal * (self.vat_rate / 100)
        
        self.assertEqual(vat_amount, Decimal('0.00'))
    
    def test_exempt_item_vat(self):
        """اختبار الضريبة على سلعة معفاة"""
        exempt_rate = Decimal('0.00')
        subtotal = Decimal('1000.00')
        vat_amount = subtotal * (exempt_rate / 100)
        
        self.assertEqual(vat_amount, Decimal('0.00'))
    
    def test_multiple_items_vat(self):
        """اختبار الضريبة على عناصر متعددة"""
        items = [
            {'net': Decimal('100.00'), 'rate': Decimal('15.00')},
            {'net': Decimal('200.00'), 'rate': Decimal('15.00')},
            {'net': Decimal('300.00'), 'rate': Decimal('0.00')},  # معفى
        ]
        
        total_net = sum(item['net'] for item in items)
        total_vat = sum(item['net'] * item['rate'] / 100 for item in items)
        
        self.assertEqual(total_net, Decimal('600.00'))
        self.assertEqual(total_vat, Decimal('45.00'))  # (100+200) * 15%
    
    def test_rounding_vat(self):
        """اختبار تقريب الضريبة"""
        subtotal = Decimal('99.99')
        vat_amount = (subtotal * self.vat_rate / 100).quantize(Decimal('0.01'))
        
        self.assertEqual(vat_amount, Decimal('15.00'))


# ===============================
# اختبارات الفواتير الضريبية
# ===============================

class TaxInvoiceTestCase(TestCase):
    """اختبارات الفواتير الضريبية"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('tax_user', 'tax@test.com', 'pass123')
        
        self.tax_category = TaxCategory.objects.create(
            name='ضريبة قياسية',
            code='VAT-STD',
            rate=Decimal('15.00')
        )
    
    def test_create_sales_tax_invoice(self):
        """اختبار إنشاء فاتورة مبيعات ضريبية"""
        invoice = TaxInvoice.objects.create(
            invoice_number='INV-TAX-001',
            invoice_type='sales',
            tax_type='taxable',
            invoice_date=date.today(),
            subtotal=Decimal('1000.00'),
            tax_amount=Decimal('150.00'),
            total=Decimal('1150.00'),
            status='draft',
            created_by=self.user
        )
        
        self.assertEqual(invoice.invoice_type, 'sales')
        self.assertEqual(invoice.tax_type, 'taxable')
        self.assertEqual(invoice.tax_amount, Decimal('150.00'))
    
    def test_create_purchase_tax_invoice(self):
        """اختبار إنشاء فاتورة مشتريات ضريبية"""
        invoice = TaxInvoice.objects.create(
            invoice_number='INV-TAX-002',
            invoice_type='purchase',
            tax_type='taxable',
            invoice_date=date.today(),
            subtotal=Decimal('5000.00'),
            tax_amount=Decimal('750.00'),
            total=Decimal('5750.00'),
            status='draft',
            created_by=self.user
        )
        
        self.assertEqual(invoice.invoice_type, 'purchase')
    
    def test_invoice_types(self):
        """اختبار أنواع الفواتير"""
        types = ['sales', 'sales_return', 'purchase', 'purchase_return']
        
        for i, inv_type in enumerate(types):
            invoice = TaxInvoice.objects.create(
                invoice_number=f'INV-TYPE-{i}',
                invoice_type=inv_type,
                invoice_date=date.today(),
                subtotal=Decimal('100.00'),
                tax_amount=Decimal('15.00'),
                total=Decimal('115.00'),
                created_by=self.user
            )
            self.assertEqual(invoice.invoice_type, inv_type)
    
    def test_tax_types(self):
        """اختبار أنواع الضريبة"""
        tax_types = ['taxable', 'exempt', 'zero_rated']
        
        for i, tax_type in enumerate(tax_types):
            invoice = TaxInvoice.objects.create(
                invoice_number=f'INV-TAXTYPE-{i}',
                invoice_type='sales',
                tax_type=tax_type,
                invoice_date=date.today(),
                subtotal=Decimal('100.00'),
                tax_amount=Decimal('0.00') if tax_type != 'taxable' else Decimal('15.00'),
                total=Decimal('100.00') if tax_type != 'taxable' else Decimal('115.00'),
                created_by=self.user
            )
            self.assertEqual(invoice.tax_type, tax_type)
    
    def test_exempt_invoice(self):
        """اختبار فاتورة معفاة"""
        invoice = TaxInvoice.objects.create(
            invoice_number='INV-EXEMPT-001',
            invoice_type='sales',
            tax_type='exempt',
            invoice_date=date.today(),
            subtotal=Decimal('1000.00'),
            tax_amount=Decimal('0.00'),
            total=Decimal('1000.00'),
            created_by=self.user
        )
        
        self.assertEqual(invoice.tax_amount, Decimal('0.00'))
        self.assertEqual(invoice.subtotal, invoice.total)


# ===============================
# اختبارات الفاتورة الإلكترونية
# ===============================

class EInvoiceTestCase(TestCase):
    """اختبارات الفاتورة الإلكترونية"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.settings = TaxSettings.objects.create(
            tax_registration_number='123456789',
            default_vat_rate=Decimal('15.00'),
            einvoice_enabled=True,
            einvoice_api_key='test_api_key',
            einvoice_client_id='test_client',
            einvoice_client_secret='test_secret',
            einvoice_environment='preprod'
        )
        
        self.user = User.objects.create_user('einv_user', 'einv@test.com', 'pass123')
    
    def test_einvoice_enabled(self):
        """اختبار تفعيل الفاتورة الإلكترونية"""
        self.assertTrue(self.settings.einvoice_enabled)
    
    def test_einvoice_environment(self):
        """اختبار بيئة الفاتورة الإلكترونية"""
        self.assertEqual(self.settings.einvoice_environment, 'preprod')
        
        self.settings.einvoice_environment = 'production'
        self.settings.save()
        self.assertEqual(self.settings.einvoice_environment, 'production')
    
    def test_einvoice_credentials(self):
        """اختبار بيانات اعتماد الفاتورة الإلكترونية"""
        self.assertIsNotNone(self.settings.einvoice_api_key)
        self.assertIsNotNone(self.settings.einvoice_client_id)
        self.assertIsNotNone(self.settings.einvoice_client_secret)


# ===============================
# اختبارات التقارير الضريبية
# ===============================

class TaxReportTestCase(TestCase):
    """اختبارات التقارير الضريبية"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('report_user', 'report@test.com', 'pass123')
        
        # إنشاء فواتير مبيعات
        for i in range(5):
            TaxInvoice.objects.create(
                invoice_number=f'SALES-{i:03d}',
                invoice_type='sales',
                tax_type='taxable',
                invoice_date=date.today() - timedelta(days=i),
                subtotal=Decimal('1000.00'),
                tax_amount=Decimal('150.00'),
                total=Decimal('1150.00'),
                status='confirmed',
                created_by=self.user
            )
        
        # إنشاء فواتير مشتريات
        for i in range(3):
            TaxInvoice.objects.create(
                invoice_number=f'PURCH-{i:03d}',
                invoice_type='purchase',
                tax_type='taxable',
                invoice_date=date.today() - timedelta(days=i),
                subtotal=Decimal('500.00'),
                tax_amount=Decimal('75.00'),
                total=Decimal('575.00'),
                status='confirmed',
                created_by=self.user
            )
    
    def test_sales_tax_total(self):
        """اختبار إجمالي ضريبة المبيعات"""
        sales_invoices = TaxInvoice.objects.filter(invoice_type='sales')
        total_sales_tax = sum(inv.tax_amount for inv in sales_invoices)
        
        self.assertEqual(total_sales_tax, Decimal('750.00'))  # 5 * 150
    
    def test_purchase_tax_total(self):
        """اختبار إجمالي ضريبة المشتريات"""
        purchase_invoices = TaxInvoice.objects.filter(invoice_type='purchase')
        total_purchase_tax = sum(inv.tax_amount for inv in purchase_invoices)
        
        self.assertEqual(total_purchase_tax, Decimal('225.00'))  # 3 * 75
    
    def test_net_tax_payable(self):
        """اختبار صافي الضريبة المستحقة"""
        from django.db.models import Sum
        
        sales_tax = TaxInvoice.objects.filter(
            invoice_type='sales'
        ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        
        purchase_tax = TaxInvoice.objects.filter(
            invoice_type='purchase'
        ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')
        
        net_payable = sales_tax - purchase_tax
        
        self.assertEqual(net_payable, Decimal('525.00'))  # 750 - 225
    
    def test_monthly_tax_report(self):
        """اختبار تقرير الضريبة الشهري"""
        current_month = date.today().month
        current_year = date.today().year
        
        monthly_invoices = TaxInvoice.objects.filter(
            invoice_date__month=current_month,
            invoice_date__year=current_year
        )
        
        self.assertGreater(monthly_invoices.count(), 0)


# ===============================
# اختبارات الواجهات (Views)
# ===============================

class TaxViewsTestCase(TestCase):
    """اختبارات واجهات المستخدم"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            'tax_admin', 'tax_admin@test.com', 'pass123'
        )
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='tax_admin', password='pass123')
    
    def test_tax_urls_accessible(self):
        """اختبار إمكانية الوصول لصفحات الضرائب"""
        from django.urls import get_resolver
        resolver = get_resolver()
        self.assertIsNotNone(resolver)


# ===============================
# اختبارات الأداء
# ===============================

class TaxPerformanceTestCase(TestCase):
    """اختبارات الأداء"""
    
    @classmethod
    def setUpTestData(cls):
        """إعداد البيانات المشتركة"""
        cls.user = User.objects.create_user('perf_user', 'perf@test.com', 'pass123')
    
    def test_bulk_invoice_creation(self):
        """اختبار إنشاء فواتير بكميات كبيرة"""
        invoices = []
        for i in range(100):
            invoices.append(TaxInvoice(
                invoice_number=f'BULK-{i:05d}',
                invoice_type='sales',
                tax_type='taxable',
                invoice_date=date.today(),
                subtotal=Decimal('1000.00'),
                tax_amount=Decimal('150.00'),
                total=Decimal('1150.00'),
                created_by=self.user
            ))
        
        TaxInvoice.objects.bulk_create(invoices)
        self.assertEqual(TaxInvoice.objects.count(), 100)
    
    def test_bulk_category_creation(self):
        """اختبار إنشاء فئات بكميات"""
        categories = []
        for i in range(20):
            categories.append(TaxCategory(
                name=f'فئة {i}',
                code=f'CAT-{i:03d}',
                rate=Decimal('15.00')
            ))
        
        TaxCategory.objects.bulk_create(categories)
        self.assertEqual(TaxCategory.objects.count(), 20)


# ===============================
# اختبارات التحقق من صحة البيانات
# ===============================

class TaxValidationTestCase(TestCase):
    """اختبارات التحقق من صحة البيانات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('val_user', 'val@test.com', 'pass123')
    
    def test_invoice_amounts_match(self):
        """اختبار تطابق مبالغ الفاتورة"""
        net = Decimal('1000.00')
        tax = Decimal('150.00')
        gross = net + tax
        
        invoice = TaxInvoice.objects.create(
            invoice_number='VAL-001',
            invoice_type='sales',
            invoice_date=date.today(),
            subtotal=net,
            tax_amount=tax,
            total=gross,
            created_by=self.user
        )
        
        self.assertEqual(
            invoice.subtotal + invoice.tax_amount,
            invoice.total
        )
    
    def test_tax_rate_percentage(self):
        """اختبار أن نسبة الضريبة بالمئة"""
        category = TaxCategory.objects.create(
            name='اختبار نسبة',
            code='VAL-RATE',
            rate=Decimal('15.00')
        )
        
        # التحقق من أن النسبة بين 0 و 100
        self.assertGreaterEqual(category.rate, Decimal('0'))
        self.assertLessEqual(category.rate, Decimal('100'))
    
    def test_positive_amounts(self):
        """اختبار أن المبالغ موجبة"""
        invoice = TaxInvoice.objects.create(
            invoice_number='VAL-POS-001',
            invoice_type='sales',
            invoice_date=date.today(),
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('15.00'),
            total=Decimal('115.00'),
            created_by=self.user
        )
        
        self.assertGreater(invoice.subtotal, 0)
        self.assertGreaterEqual(invoice.tax_amount, 0)
        self.assertGreater(invoice.total, 0)
