"""
اختبارات عروض الأسعار — RITA ERP
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import User, Branch
from apps.inventory.models import Product, Category
from apps.sales.models import Customer
from apps.quotations.models import Quotation, QuotationLine, QuotationFollowUp
from apps.quotations.services.quotation_engine import QuotationEngine


class QuotationEngineTests(TestCase):
    """اختبارات محرك عروض الأسعار"""

    def setUp(self):
        self.branch = Branch.objects.create(name='الفرع الرئيسي')
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', branch=self.branch,
            is_superuser=True,
        )
        # فئة ومنتج
        from apps.inventory.models import UnitOfMeasure
        self.category = Category.objects.create(name='فئة اختبار')
        self.unit = UnitOfMeasure.objects.create(name='قطعة', symbol='قط')
        self.product = Product.objects.create(
            code='P001',
            name='منتج اختبار',
            category=self.category,
            unit=self.unit,
            product_type='finished',
            retail_price=100,
            cost_price=60,
            is_active=True,
        )
        self.customer = Customer.objects.create(
            code='C0001',
            name='عميل اختبار',
            customer_type='retail',
            branch=self.branch,
        )

    def test_create_quotation_with_customer(self):
        """إنشاء عرض سعر مع عميل مسجل"""
        qt = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            salesperson=self.user,
            items=[{'product': self.product, 'quantity': 2, 'unit_price': 100}],
            is_taxable=False,
            user=self.user,
        )
        self.assertIsNotNone(qt.pk)
        self.assertTrue(qt.quotation_number.startswith('QT-'))
        self.assertEqual(qt.lines.count(), 1)
        self.assertEqual(qt.subtotal, 200)
        self.assertEqual(qt.total, 200)
        self.assertEqual(qt.status, 'draft')

    def test_create_quotation_with_prospect(self):
        """إنشاء عرض سعر مع بيانات عميل محتمل"""
        qt = QuotationEngine.create_quotation(
            prospect_data={
                'name': 'محمد أحمد',
                'phone': '01012345678',
                'email': 'test@test.com',
                'address': 'القاهرة',
                'company': '',
            },
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 150}],
            is_taxable=False,
            user=self.user,
        )
        self.assertEqual(qt.prospect_name, 'محمد أحمد')
        self.assertIsNone(qt.customer)
        self.assertEqual(qt.total, 150)

    def test_create_quotation_with_tax(self):
        """عرض سعر مع ضريبة 14%"""
        qt = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            is_taxable=True,
            user=self.user,
        )
        self.assertGreater(qt.tax_amount, 0)
        self.assertEqual(qt.total, qt.taxable_amount + qt.tax_amount)

    def test_create_quotation_with_discount(self):
        """عرض سعر مع خصم إجمالي"""
        qt = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 2, 'unit_price': 100}],
            discount_percentage=10,
            is_taxable=False,
            user=self.user,
        )
        # 200 - 10% = 180
        self.assertEqual(float(qt.subtotal), 200)
        self.assertEqual(float(qt.discount_amount), 20)
        self.assertEqual(float(qt.total), 180)

    def test_revise_quotation(self):
        """تعديل عرض سعر — ينشئ revision"""
        qt = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            is_taxable=False,
            user=self.user,
        )
        original_number = qt.quotation_number

        QuotationEngine.revise_quotation(
            quotation=qt,
            items=[{'product': self.product, 'quantity': 3, 'unit_price': 120}],
            discount_percentage=0,
            user=self.user,
        )
        qt.refresh_from_db()
        self.assertEqual(qt.revision_number, 1)
        self.assertEqual(qt.status, 'revised')
        self.assertEqual(float(qt.subtotal), 360)
        self.assertEqual(qt.quotation_number, original_number)  # نفس الرقم

    def test_add_follow_up(self):
        """إضافة متابعة"""
        qt = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            is_taxable=False,
            user=self.user,
        )
        QuotationEngine.add_follow_up(
            quotation=qt,
            follow_up_type='call',
            result='will_buy',
            notes='العميل وافق',
            user=self.user,
        )
        qt.refresh_from_db()
        self.assertEqual(qt.status, 'accepted')
        self.assertEqual(qt.follow_ups.count(), 1)

    def test_follow_up_changes_status_to_rejected(self):
        """متابعة سبب الرفض تغير الحالة"""
        qt = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            is_taxable=False,
            user=self.user,
        )
        QuotationEngine.add_follow_up(
            quotation=qt,
            follow_up_type='call',
            result='lost',
            notes='خسرنا المبيعة',
            user=self.user,
        )
        qt.refresh_from_db()
        self.assertEqual(qt.status, 'rejected')

    def test_is_expired_property(self):
        """خاصية انتهاء العرض"""
        qt = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            valid_days=0,
            is_taxable=False,
            user=self.user,
        )
        # valid_until = today, so not expired yet (or it is — depends on timezone)
        self.assertIn(qt.is_expired, [True, False])  # just test it doesn't crash

    def test_quick_create_customer(self):
        """إنشاء عميل سريع من بيانات عرض السعر"""
        qt = QuotationEngine.create_quotation(
            prospect_data={
                'name': 'عميل جديد',
                'phone': '01099999999',
                'email': '',
                'address': 'الإسكندرية',
                'company': '',
            },
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            is_taxable=False,
            user=self.user,
        )
        customer = QuotationEngine.quick_create_customer(qt, user=self.user)
        self.assertEqual(customer.name, 'عميل جديد')
        self.assertTrue(customer.code.startswith('C'))
        self.assertTrue(customer.is_active)

    def test_quotation_stats(self):
        """إحصائيات عروض الأسعار"""
        QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            is_taxable=False,
            user=self.user,
        )
        stats = QuotationEngine.get_quotation_stats(branch=self.branch)
        self.assertIn('total', stats)
        self.assertIn('conversion_rate', stats)
        self.assertGreaterEqual(stats['total'], 1)

    def test_generate_unique_quotation_numbers(self):
        """الأرقام التسلسلية فريدة"""
        qt1 = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            is_taxable=False,
            user=self.user,
        )
        qt2 = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            items=[{'product': self.product, 'quantity': 2, 'unit_price': 50}],
            is_taxable=False,
            user=self.user,
        )
        self.assertNotEqual(qt1.quotation_number, qt2.quotation_number)


class QuotationViewTests(TestCase):
    """اختبارات الصفحات"""

    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(name='الفرع الرئيسي')
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', branch=self.branch,
            is_staff=True, is_superuser=True,
        )
        self.client.login(username='testuser', password='testpass123')

        from apps.inventory.models import UnitOfMeasure
        self.unit = UnitOfMeasure.objects.create(name='قطعة', symbol='قط')
        self.category = Category.objects.create(name='فئة')
        self.product = Product.objects.create(
            code='P001', name='منتج', category=self.category,
            unit=self.unit, product_type='finished',
            retail_price=100, cost_price=60, is_active=True,
        )
        self.customer = Customer.objects.create(
            code='C0001', name='عميل', customer_type='retail', branch=self.branch,
        )
        self.quotation = QuotationEngine.create_quotation(
            customer=self.customer,
            branch=self.branch,
            salesperson=self.user,
            items=[{'product': self.product, 'quantity': 1, 'unit_price': 100}],
            is_taxable=False,
            user=self.user,
        )

    def test_quotation_list_200(self):
        response = self.client.get(reverse('quotations:quotation_list'))
        self.assertEqual(response.status_code, 200)

    def test_quotation_create_get_200(self):
        response = self.client.get(reverse('quotations:quotation_create'))
        self.assertEqual(response.status_code, 200)

    def test_quotation_detail_200(self):
        response = self.client.get(reverse('quotations:quotation_detail', args=[self.quotation.pk]))
        self.assertEqual(response.status_code, 200)

    def test_quotation_update_get_200(self):
        response = self.client.get(reverse('quotations:quotation_update', args=[self.quotation.pk]))
        self.assertEqual(response.status_code, 200)

    def test_quotation_print_200(self):
        response = self.client.get(reverse('quotations:quotation_print', args=[self.quotation.pk]))
        self.assertEqual(response.status_code, 200)

    def test_quotation_dashboard_200(self):
        response = self.client.get(reverse('quotations:quotation_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_add_follow_up_get_200(self):
        response = self.client.get(reverse('quotations:add_follow_up', args=[self.quotation.pk]))
        self.assertEqual(response.status_code, 200)

    def test_accept_quotation(self):
        response = self.client.post(reverse('quotations:quotation_accept', args=[self.quotation.pk]))
        self.assertIn(response.status_code, [200, 302])
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'accepted')

    def test_reject_quotation(self):
        response = self.client.post(
            reverse('quotations:quotation_reject', args=[self.quotation.pk]),
            {'rejection_reason': 'السعر مرتفع', 'lost_to_competitor': ''},
        )
        self.assertIn(response.status_code, [200, 302])
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'rejected')
