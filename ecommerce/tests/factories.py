"""
Factory classes for ecommerce tests
"""
import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils.text import slugify


User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = 'محمد'
    last_name = 'أحمد'


class EcommerceSettingsFactory(DjangoModelFactory):
    class Meta:
        model = 'ecommerce.EcommerceSettings'
        django_get_or_create = ('id',)
    
    id = 1
    store_name = 'Tony Store Egypt'
    currency = 'EGP'
    vat_rate = Decimal('14.00')
    products_per_page = 20
    free_shipping_threshold = Decimal('500.00')
    default_shipping_cost = Decimal('50.00')


class ProductCategoryFactory(DjangoModelFactory):
    class Meta:
        model = 'ecommerce.ProductCategory'
    
    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    is_active = True


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = 'ecommerce.Brand'
    
    name = factory.Sequence(lambda n: f'Brand {n}')
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    is_active = True


class InventoryProductFactory(DjangoModelFactory):
    """Factory for inventory Product - required for OnlineProduct"""
    class Meta:
        model = 'inventory.Product'
    
    sku = factory.Sequence(lambda n: f'SKU-{n:05d}')
    internal_code = factory.Sequence(lambda n: f'INTCODE-{n:05d}')
    name = factory.Sequence(lambda n: f'Inventory Product {n}')
    price = Decimal('100.00')
    cost = Decimal('50.00')

    @factory.post_generation
    def create_stock(self, create, extracted, **kwargs):
        """Ensure product has stock for testing (creates a default Location + Stock entry)."""
        if not create:
            return
        from inventory.models import Location, Stock
        loc, _ = Location.objects.get_or_create(
            code='TEST-LOC', defaults={'name': 'Test Location'}
        )
        Stock.objects.get_or_create(
            product=self, location=loc,
            defaults={'quantity': 100}
        )
    

class OnlineProductFactory(DjangoModelFactory):
    class Meta:
        model = 'ecommerce.OnlineProduct'
    
    inventory_item = factory.SubFactory(InventoryProductFactory)
    display_name = factory.Sequence(lambda n: f'Product {n}')
    short_description = 'Test product description'
    custom_price = Decimal('100.00')
    discount_price = None
    is_active = True
    is_featured = False
    category = factory.SubFactory(ProductCategoryFactory)


class PaymentGatewayFactory(DjangoModelFactory):
    class Meta:
        model = 'ecommerce.PaymentGateway'
    
    name = 'Paymob Card'
    gateway_type = 'paymob_card'
    is_active = True
    is_sandbox = True
    api_key = 'test_api_key'
    api_secret = 'test_api_secret'


class CartFactory(DjangoModelFactory):
    class Meta:
        model = 'ecommerce.Cart'
    
    user = factory.SubFactory(UserFactory)
    session_key = factory.Sequence(lambda n: f'session_{n}')


class CartItemFactory(DjangoModelFactory):
    class Meta:
        model = 'ecommerce.CartItem'
    
    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(OnlineProductFactory)
    quantity = 1


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = 'ecommerce.Order'
    
    order_number = factory.Sequence(lambda n: f'ORD-{n:06d}')
    user = factory.SubFactory(UserFactory)
    status = 'pending'
    payment_status = 'pending'
    
    # Customer info
    customer_name = factory.LazyAttribute(lambda obj: obj.user.get_full_name())
    customer_email = factory.LazyAttribute(lambda obj: obj.user.email)
    customer_phone = '01234567890'
    shipping_address = 'شارع المعز، القاهرة'
    shipping_city = 'القاهرة'
    shipping_country = 'مصر'
    
    # Amounts
    subtotal = Decimal('100.00')
    discount = Decimal('0.00')
    shipping_cost = Decimal('50.00')
    tax = Decimal('14.00')  # 14% VAT
    total = Decimal('164.00')
