from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

class InventoryReportsTests(TestCase):
	def setUp(self):
		# Create a basic user and log in; bypass custom permission system in tests
		User = get_user_model()
		self.user = User.objects.create_user(username='tester', password='pass12345')
		self.client.login(username='tester', password='pass12345')

	def test_valuation_report_page_and_csv(self):
		url = reverse('inventory:valuation_report')
		r = self.client.get(url)
		self.assertEqual(r.status_code, 200)
		r2 = self.client.get(url + '?export=csv')
		self.assertEqual(r2.status_code, 200)
		self.assertIn('text/csv', r2['Content-Type'])

	def test_aging_report_page_and_csv(self):
		url = reverse('inventory:aging_report')
		r = self.client.get(url)
		self.assertEqual(r.status_code, 200)
		r2 = self.client.get(url + '?export=csv')
		self.assertEqual(r2.status_code, 200)
		self.assertIn('text/csv', r2['Content-Type'])

	def test_product_effective_price(self):
		from inventory.models import Product
		p = Product.objects.create(sku='PROMO1', name='منتج عرض', price=100, cost=50, is_promo_active=True, promo_percent=10)
		self.assertEqual(float(p.effective_price), 90.0)
		p.promo_price = 80; p.save(); self.assertEqual(float(p.effective_price), 80.0)
