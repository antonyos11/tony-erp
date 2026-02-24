from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone

from .models import Customer, Quotation, QuotationItem
from inventory.models import Product


class CRMTrendViewsTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='u', password='p')
		self.client.login(username='u', password='p')

	def test_commissions_trend_page(self):
		url = reverse('crm:commissions_trend')
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)

	def test_commissions_trend_csv(self):
		url = reverse('crm:commissions_trend') + '?export=csv'
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertIn('text/csv', resp['Content-Type'])


class CRMQuotationTotalsTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='sales', password='p')
		self.client.login(username='sales', password='p')
		self.customer = Customer.objects.create(
			customer_code='CUS00001', first_name='Ali', last_name='Saleh', phone='0123456'
		)
		self.p1 = Product.objects.create(sku='SKU1', name='Prod1', price=Decimal('100.00'))
		self.p2 = Product.objects.create(sku='SKU2', name='Prod2', price=Decimal('50.00'))

	def test_per_line_discount_tax_totals(self):
		quo = Quotation.objects.create(
			quotation_number='QUO00001',
			customer=self.customer,
			valid_until=timezone.now().date(),
			prepared_by=self.user,
			discount_percentage=Decimal('10.00'),  # should be ignored because we have per-line
			tax_percentage=Decimal('14.00'),       # should be ignored because we have per-line
		)
		# Item 1: qty 2 x 100 = 200; dp 5% => disc 10; taxable 190; tp 10% => tax 19
		QuotationItem.objects.create(
			quotation=quo, product=self.p1, quantity=Decimal('2'), unit_price=Decimal('100.00'),
			discount_percentage=Decimal('5.00'), tax_percentage=Decimal('10.00'),
		)
		# Item 2: qty 1 x 50 = 50; dp 0% => disc 0; taxable 50; tp 14% => tax 7
		QuotationItem.objects.create(
			quotation=quo, product=self.p2, quantity=Decimal('1'), unit_price=Decimal('50.00'),
			discount_percentage=Decimal('0.00'), tax_percentage=Decimal('14.00'),
		)

		quo.calculate_totals()

		self.assertEqual(quo.subtotal, Decimal('250.00'))
		# per-line totals should be used
		self.assertEqual(quo.discount_amount.quantize(Decimal('0.01')), Decimal('10.00'))  # 200*5% = 10
		self.assertEqual(quo.tax_amount.quantize(Decimal('0.01')), Decimal('26.00'))       # 19 + 7
		self.assertEqual(quo.total_amount.quantize(Decimal('0.01')), Decimal('266.00'))    # 250-10+26

	def test_global_discount_tax_when_no_line_rates(self):
		quo = Quotation.objects.create(
			quotation_number='QUO00002',
			customer=self.customer,
			valid_until=timezone.now().date(),
			prepared_by=self.user,
			discount_percentage=Decimal('10.00'),
			tax_percentage=Decimal('14.00'),
		)
		# Both items have 0 line dp/tp so global should be applied
		QuotationItem.objects.create(
			quotation=quo, product=self.p1, quantity=Decimal('2'), unit_price=Decimal('100.00'),
		)
		QuotationItem.objects.create(
			quotation=quo, product=self.p2, quantity=Decimal('1'), unit_price=Decimal('50.00'),
		)

		quo.calculate_totals()

		self.assertEqual(quo.subtotal, Decimal('250.00'))
		self.assertEqual(quo.discount_amount.quantize(Decimal('0.01')), Decimal('25.00'))  # 10%
		# Tax after discount: (250-25)=225 * 14% = 31.50
		self.assertEqual(quo.tax_amount.quantize(Decimal('0.01')), Decimal('31.50'))
		self.assertEqual(quo.total_amount.quantize(Decimal('0.01')), Decimal('256.50'))


class CRMQuotationDuplicateTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='sales2', password='p')
		self.client.login(username='sales2', password='p')
		self.customer = Customer.objects.create(
			customer_code='CUS00002', first_name='Hana', last_name='Youssef', phone='0987654'
		)
		self.p = Product.objects.create(sku='SKU3', name='Prod3', price=Decimal('10.00'))

	def test_duplicate_copies_line_rates(self):
		orig = Quotation.objects.create(
			quotation_number='QUO10001',
			customer=self.customer,
			valid_until=timezone.now().date(),
			prepared_by=self.user,
			discount_percentage=Decimal('0.00'),
			tax_percentage=Decimal('0.00'),
		)
		QuotationItem.objects.create(
			quotation=orig, product=self.p, quantity=Decimal('3'), unit_price=Decimal('10.00'),
			discount_percentage=Decimal('5.00'), tax_percentage=Decimal('10.00'),
		)
		orig.calculate_totals()

		# Duplicate via view
		url = reverse('crm:quotation_duplicate', args=[orig.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 302)

		# Fetch the duplicated quotation (latest one not the original)
		new_quo = Quotation.objects.exclude(pk=orig.pk).order_by('-id').first()
		self.assertIsNotNone(new_quo)
		self.assertEqual(new_quo.items.count(), orig.items.count())
		new_item = new_quo.items.first()
		self.assertEqual(new_item.discount_percentage.quantize(Decimal('0.01')), Decimal('5.00'))
		self.assertEqual(new_item.tax_percentage.quantize(Decimal('0.01')), Decimal('10.00'))
		# Totals should be calculated on creation
		self.assertGreater(new_quo.total_amount, Decimal('0'))

	def test_acceptance_trend_page(self):
		url = reverse('crm:acceptance_trend')
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)

	def test_acceptance_trend_csv(self):
		url = reverse('crm:acceptance_trend') + '?export=csv'
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertIn('text/csv', resp['Content-Type'])
