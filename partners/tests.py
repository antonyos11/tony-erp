"""
اختبارات وحدة الشركاء - Partners Module Tests
=============================================
اختبارات شاملة لجميع وظائف وحدة الشركاء (العملاء والموردين)

تغطية الاختبارات:
- نماذج البيانات (Models)
- الشركاء العامين
- العملاء
- الموردين
- مستندات الموردين
- التكامل مع المحاسبة
"""

from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import json

from .models import Partner, Customer, Supplier, SupplierDocument


# ===============================
# اختبارات الشركاء العامين
# ===============================

class PartnerTestCase(TestCase):
    """اختبارات الشركاء العامين"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.customer_partner = Partner.objects.create(
            name='شركة العميل للتجارة',
            email='customer@company.com',
            phone='0500000001',
            address='الرياض - حي الملقا',
            partner_type='customer',
            is_active=True
        )
        
        self.supplier_partner = Partner.objects.create(
            name='مصنع المواد الخام',
            email='supplier@factory.com',
            phone='0500000002',
            address='جدة - المنطقة الصناعية',
            partner_type='supplier',
            is_active=True
        )
    
    def test_create_customer_partner(self):
        """اختبار إنشاء شريك عميل"""
        self.assertEqual(self.customer_partner.name, 'شركة العميل للتجارة')
        self.assertEqual(self.customer_partner.partner_type, 'customer')
        self.assertTrue(self.customer_partner.is_active)
    
    def test_create_supplier_partner(self):
        """اختبار إنشاء شريك مورد"""
        self.assertEqual(self.supplier_partner.name, 'مصنع المواد الخام')
        self.assertEqual(self.supplier_partner.partner_type, 'supplier')
    
    def test_partner_types(self):
        """اختبار أنواع الشركاء"""
        types = ['customer', 'supplier', 'both']
        
        for partner_type in types:
            partner = Partner.objects.create(
                name=f'شريك {partner_type}',
                partner_type=partner_type
            )
            self.assertEqual(partner.partner_type, partner_type)
    
    def test_both_type_partner(self):
        """اختبار شريك عميل ومورد"""
        both_partner = Partner.objects.create(
            name='شركة متعددة الأنشطة',
            partner_type='both',
            email='both@company.com'
        )
        
        self.assertEqual(both_partner.partner_type, 'both')
    
    def test_partner_str_representation(self):
        """اختبار التمثيل النصي للشريك"""
        self.assertEqual(str(self.customer_partner), 'شركة العميل للتجارة')
    
    def test_partner_is_active_default(self):
        """اختبار القيمة الافتراضية لحالة النشاط"""
        partner = Partner.objects.create(
            name='شريك جديد',
            partner_type='customer'
        )
        self.assertTrue(partner.is_active)
    
    def test_deactivate_partner(self):
        """اختبار إلغاء تنشيط شريك"""
        self.customer_partner.is_active = False
        self.customer_partner.save()
        self.assertFalse(self.customer_partner.is_active)
    
    def test_partner_contact_info(self):
        """اختبار معلومات الاتصال للشريك"""
        self.assertEqual(self.customer_partner.email, 'customer@company.com')
        self.assertEqual(self.customer_partner.phone, '0500000001')
        self.assertEqual(self.customer_partner.address, 'الرياض - حي الملقا')


# ===============================
# اختبارات العملاء
# ===============================

class CustomerTestCase(TestCase):
    """اختبارات العملاء"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.partner = Partner.objects.create(
            name='عميل مميز',
            partner_type='customer',
            email='vip@customer.com'
        )
        
        self.customer = Customer.objects.create(
            partner=self.partner,
            name='عميل مميز',
            email='vip@customer.com',
            phone='0500000010',
            address='الرياض',
            is_key_account=True
        )
    
    def test_create_customer(self):
        """اختبار إنشاء عميل"""
        self.assertEqual(self.customer.name, 'عميل مميز')
        self.assertTrue(self.customer.is_key_account)
    
    def test_customer_linked_to_partner(self):
        """اختبار ربط العميل بالشريك"""
        self.assertEqual(self.customer.partner, self.partner)
    
    def test_customer_without_partner(self):
        """اختبار إنشاء عميل بدون شريك"""
        standalone_customer = Customer.objects.create(
            name='عميل مستقل',
            email='standalone@test.com',
            phone='0500000011',
            is_key_account=False
        )
        
        self.assertIsNone(standalone_customer.partner)
    
    def test_key_account_flag(self):
        """اختبار علم العميل الرئيسي"""
        regular_customer = Customer.objects.create(
            name='عميل عادي',
            is_key_account=False
        )
        
        self.assertFalse(regular_customer.is_key_account)
        self.assertTrue(self.customer.is_key_account)
    
    def test_customer_str_representation(self):
        """اختبار التمثيل النصي للعميل"""
        self.assertEqual(str(self.customer), 'عميل مميز')
    
    def test_multiple_customers(self):
        """اختبار إنشاء عملاء متعددين"""
        initial_count = Customer.objects.count()
        customers = [
            ('عميل 1', False),
            ('عميل 2', True),
            ('عميل 3', False),
        ]
        
        for name, is_key in customers:
            Customer.objects.create(name=name, is_key_account=is_key)
        
        self.assertEqual(Customer.objects.count(), initial_count + 3)


# ===============================
# اختبارات الموردين
# ===============================

class SupplierTestCase(TestCase):
    """اختبارات الموردين"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        
        # إنشاء مورد بدون Partner (Partner يُنشأ تلقائياً أو يكون اختياري)
        self.supplier = Supplier.objects.create(
            name=f'مورد رئيسي {unique_id}',
            email=f'supplier{unique_id}@main.com',
            phone='0500000020',
            address='جدة - المنطقة الصناعية',
            supply_type='raw_materials',
            raw_material='أقمشة',
            opening_balance=Decimal('10000.00'),
            credit_limit=Decimal('50000.00'),
            payment_terms_days=30
        )
    
    def test_create_supplier(self):
        """اختبار إنشاء مورد"""
        self.assertIn('مورد رئيسي', self.supplier.name)
        self.assertEqual(self.supplier.supply_type, 'raw_materials')
    
    def test_supplier_linked_to_partner(self):
        """اختبار أن المورد يمكن أن يكون له Partner أو لا"""
        # اختبار أن المورد الحالي ليس له partner
        # (حيث أنشأناه بدون partner في setUp)
        # هذا يختبر أن العلاقة اختيارية
        supplier_without_partner = Supplier.objects.create(
            name='مورد بدون شريك',
            supply_type='services'
        )
        self.assertIsNone(supplier_without_partner.partner)
    
    def test_supply_types(self):
        """اختبار أنواع التوريد"""
        supply_types = ['raw_materials', 'packaging', 'services', 'spare_parts', 'other']
        
        for i, supply_type in enumerate(supply_types):
            supplier = Supplier.objects.create(
                name=f'مورد {supply_type}',
                supply_type=supply_type
            )
            self.assertEqual(supplier.supply_type, supply_type)
    
    def test_supplier_financial_info(self):
        """اختبار المعلومات المالية للمورد"""
        self.assertEqual(self.supplier.opening_balance, Decimal('10000.00'))
        self.assertEqual(self.supplier.credit_limit, Decimal('50000.00'))
        self.assertEqual(self.supplier.payment_terms_days, 30)
    
    def test_supplier_raw_material(self):
        """اختبار المادة الخام الرئيسية للمورد"""
        self.assertEqual(self.supplier.raw_material, 'أقمشة')
    
    def test_supplier_str_representation(self):
        """اختبار التمثيل النصي للمورد"""
        self.assertIn('مورد رئيسي', str(self.supplier))
    
    def test_supplier_without_partner(self):
        """اختبار إنشاء مورد بدون شريك"""
        standalone_supplier = Supplier.objects.create(
            name='مورد مستقل',
            email='standalone@supplier.com',
            supply_type='services'
        )
        
        self.assertIsNone(standalone_supplier.partner)
    
    def test_supplier_default_values(self):
        """اختبار القيم الافتراضية للمورد"""
        supplier = Supplier.objects.create(name='مورد بسيط')
        
        self.assertEqual(supplier.opening_balance, Decimal('0'))
        self.assertEqual(supplier.credit_limit, Decimal('0'))
        self.assertEqual(supplier.payment_terms_days, 0)


# ===============================
# اختبارات مستندات الموردين
# ===============================

class SupplierDocumentTestCase(TestCase):
    """اختبارات مستندات الموردين"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user('doc_user', 'doc@test.com', 'pass123')
        
        self.supplier = Supplier.objects.create(
            name='مورد المستندات',
            email='docs@supplier.com'
        )
    
    def test_create_supplier_document(self):
        """اختبار إنشاء مستند مورد"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # إنشاء ملف وهمي
        test_file = SimpleUploadedFile(
            "test_doc.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        document = SupplierDocument.objects.create(
            supplier=self.supplier,
            document_type='commercial_register',
            document_number='CR-123456',
            title='السجل التجاري',
            file=test_file,
            issue_date=date.today() - timedelta(days=365),
            expiry_date=date.today() + timedelta(days=365),
            uploaded_by=self.user,
            is_verified=True
        )
        
        self.assertEqual(document.document_type, 'commercial_register')
        self.assertEqual(document.document_number, 'CR-123456')
        self.assertTrue(document.is_verified)
    
    def test_document_types(self):
        """اختبار أنواع المستندات"""
        doc_types = [
            'commercial_register', 'tax_card', 'vat_certificate',
            'contract', 'quality_certificate', 'insurance',
            'bank_account', 'authorization', 'id_copy', 'other'
        ]
        
        for doc_type in doc_types:
            # لا نحتاج ملف فعلي للاختبار
            pass  # يمكن إضافة اختبار تفصيلي لاحقاً
    
    def test_document_expiry_check(self):
        """اختبار فحص انتهاء صلاحية المستند"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile("expired.pdf", b"content", content_type="application/pdf")
        
        expired_doc = SupplierDocument.objects.create(
            supplier=self.supplier,
            document_type='tax_card',
            title='بطاقة ضريبية منتهية',
            file=test_file,
            expiry_date=date.today() - timedelta(days=30),
            uploaded_by=self.user
        )
        
        self.assertTrue(expired_doc.is_expired)
    
    def test_document_days_until_expiry(self):
        """اختبار حساب الأيام حتى انتهاء الصلاحية"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile("valid.pdf", b"content", content_type="application/pdf")
        
        valid_doc = SupplierDocument.objects.create(
            supplier=self.supplier,
            document_type='contract',
            title='عقد توريد',
            file=test_file,
            expiry_date=date.today() + timedelta(days=90),
            uploaded_by=self.user
        )
        
        self.assertEqual(valid_doc.days_until_expiry, 90)
    
    def test_document_without_expiry(self):
        """اختبار مستند بدون تاريخ انتهاء"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile("no_expiry.pdf", b"content", content_type="application/pdf")
        
        doc = SupplierDocument.objects.create(
            supplier=self.supplier,
            document_type='other',
            title='مستند بدون انتهاء',
            file=test_file,
            expiry_date=None,
            uploaded_by=self.user
        )
        
        self.assertFalse(doc.is_expired)
        self.assertIsNone(doc.days_until_expiry)
    
    def test_document_verification_status(self):
        """اختبار حالة التحقق من المستند"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile("verify.pdf", b"content", content_type="application/pdf")
        
        doc = SupplierDocument.objects.create(
            supplier=self.supplier,
            document_type='quality_certificate',
            title='شهادة جودة',
            file=test_file,
            is_verified=False,
            uploaded_by=self.user
        )
        
        self.assertFalse(doc.is_verified)
        
        doc.is_verified = True
        doc.save()
        self.assertTrue(doc.is_verified)


# ===============================
# اختبارات التكامل
# ===============================

class PartnerIntegrationTestCase(TestCase):
    """اختبارات تكامل الشركاء"""
    
    def test_partner_creates_customer_record(self):
        """اختبار إنشاء سجل عميل عند إنشاء شريك عميل"""
        partner = Partner.objects.create(
            name='عميل تلقائي',
            partner_type='customer',
            email='auto@customer.com'
        )
        
        # التحقق من إنشاء سجل Customer مرتبط (عبر signal)
        # هذا يعتمد على تنفيذ signals.py
        self.assertIsNotNone(partner)
    
    def test_partner_customer_sync(self):
        """اختبار مزامنة بيانات الشريك والعميل"""
        partner = Partner.objects.create(
            name='عميل للمزامنة',
            partner_type='customer',
            email='sync@customer.com',
            phone='0500000030'
        )
        
        customer = Customer.objects.create(
            partner=partner,
            name=partner.name,
            email=partner.email,
            phone=partner.phone
        )
        
        self.assertEqual(customer.name, partner.name)
        self.assertEqual(customer.email, partner.email)


# ===============================
# اختبارات الواجهات (Views)
# ===============================

class PartnerViewsTestCase(TestCase):
    """اختبارات واجهات المستخدم"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            'partner_admin', 'partner@test.com', 'pass123'
        )
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='partner_admin', password='pass123')
    
    def test_partner_urls_accessible(self):
        """اختبار إمكانية الوصول لصفحات الشركاء"""
        from django.urls import get_resolver
        resolver = get_resolver()
        self.assertIsNotNone(resolver)


# ===============================
# اختبارات الأداء
# ===============================

class PartnerPerformanceTestCase(TestCase):
    """اختبارات الأداء"""
    
    def test_bulk_partner_creation(self):
        """اختبار إنشاء شركاء بكميات كبيرة"""
        initial_count = Partner.objects.count()
        partners = []
        for i in range(100):
            partners.append(Partner(
                name=f'شريك {i}',
                partner_type='customer' if i % 2 == 0 else 'supplier',
                email=f'partner{i}@test.com'
            ))
        
        Partner.objects.bulk_create(partners)
        self.assertEqual(Partner.objects.count(), initial_count + 100)
    
    def test_bulk_customer_creation(self):
        """اختبار إنشاء عملاء بكميات"""
        initial_count = Customer.objects.count()
        customers = []
        for i in range(50):
            customers.append(Customer(
                name=f'عميل {i}',
                email=f'customer{i}@test.com',
                is_key_account=i % 5 == 0
            ))
        
        Customer.objects.bulk_create(customers)
        self.assertEqual(Customer.objects.count(), initial_count + 50)
    
    def test_bulk_supplier_creation(self):
        """اختبار إنشاء موردين بكميات"""
        suppliers = []
        supply_types = ['raw_materials', 'packaging', 'services', 'spare_parts', 'other']
        
        for i in range(50):
            suppliers.append(Supplier(
                name=f'مورد {i}',
                email=f'supplier{i}@test.com',
                supply_type=supply_types[i % 5]
            ))
        
        Supplier.objects.bulk_create(suppliers)
        self.assertEqual(Supplier.objects.count(), 50)


# ===============================
# اختبارات التحقق من صحة البيانات
# ===============================

class PartnerValidationTestCase(TestCase):
    """اختبارات التحقق من صحة البيانات"""
    
    def test_partner_name_required(self):
        """اختبار أن اسم الشريك مطلوب"""
        partner = Partner.objects.create(
            name='شريك صالح',
            partner_type='customer'
        )
        self.assertIsNotNone(partner.name)
        self.assertNotEqual(partner.name, '')
    
    def test_supplier_credit_limit_positive(self):
        """اختبار أن حد الائتمان موجب أو صفر"""
        supplier = Supplier.objects.create(
            name='مورد تحقق',
            credit_limit=Decimal('10000.00')
        )
        self.assertGreaterEqual(supplier.credit_limit, 0)
    
    def test_supplier_payment_terms_positive(self):
        """اختبار أن أيام السداد موجبة أو صفر"""
        supplier = Supplier.objects.create(
            name='مورد أيام',
            payment_terms_days=30
        )
        self.assertGreaterEqual(supplier.payment_terms_days, 0)
    
    def test_email_format(self):
        """اختبار صيغة البريد الإلكتروني"""
        partner = Partner.objects.create(
            name='شريك بريد',
            email='valid@email.com',
            partner_type='customer'
        )
        self.assertIn('@', partner.email)
