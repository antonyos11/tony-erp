from django.test import TestCase, Client
from decimal import Decimal

from .models import WooCommerceConfig, ProductMapping
from inventory.models import Product


class WooCommerceConfigTests(TestCase):
    """اختبارات أساسية لتأكد من إعدادات WooCommerce والتربطات."""

    def setUp(self):
        self.client = Client()

    def test_single_default_config_validation(self):
        first = WooCommerceConfig.objects.create(
            name="Store 1",
            store_url="https://example.com",
            consumer_key="k1",
            consumer_secret="s1",
            is_default=True,
        )
        second = WooCommerceConfig(
            name="Store 2",
            store_url="https://example2.com",
            consumer_key="k2",
            consumer_secret="s2",
            is_default=True,
        )
        with self.assertRaises(Exception):
            second.full_clean()

    def test_product_mapping_basic_fields(self):
        cfg = WooCommerceConfig.objects.create(
            name="Store",
            store_url="https://example.com",
            consumer_key="k1",
            consumer_secret="s1",
        )
        product = Product.objects.create(sku="SKU1", name="P1", price=Decimal("10.00"), cost=Decimal("5.00"))
        mapping = ProductMapping.objects.create(
            config=cfg,
            erp_product=product,
            woo_product_id=123,
        )
        self.assertEqual(mapping.erp_product.name, "P1")

    def test_config_list_view_requires_login(self):
        response = self.client.get("/woocommerce/config/")
        # من المتوقع إعادة توجيه لصفحة تسجيل الدخول
        self.assertEqual(response.status_code, 302)

