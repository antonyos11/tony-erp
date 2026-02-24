from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from partners.models import Partner
from purchases.models import PurchaseBill, PurchaseItem, SupplierPayment
from inventory.models import Product, Location, Stock
from accounting.models import AccountingSettings


class PurchaseBillWorkflowTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(username='tester', password='pass')
		self.client.login(username='tester', password='pass')
		AccountingSettings.get()
		self.supplier = Partner.objects.create(name='مورد اختبار', partner_type='supplier')
		self.product = Product.objects.create(name='صنف', sku='SKU1', cost=Decimal('10'))
		self.location = Location.objects.create(name='مخزن رئيسي')

	def test_post_bill_and_payment(self):
		bill = PurchaseBill.objects.create(number='PB-000001', supplier=self.supplier)
		PurchaseItem.objects.create(bill=bill, product=self.product, location=self.location, quantity=5, cost=Decimal('10'))
		je = bill.post(user=self.user)
		self.assertIsNotNone(je)
		bill.refresh_from_db()
		self.assertEqual(bill.status, 'posted')
		sp = SupplierPayment.objects.create(supplier=self.supplier, bill=bill, amount=Decimal('20'))
		sp.post(user=self.user)
		bill.refresh_from_db()
		self.assertGreater(bill.paid, 0)
		self.assertEqual(bill.remaining, bill.total - bill.paid)
		stock = Stock.objects.get(product=self.product, location=self.location)
		self.assertEqual(stock.quantity, 5)
