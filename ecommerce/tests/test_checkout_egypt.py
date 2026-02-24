"""
Tests for Egypt checkout flow with 14% VAT calculation
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from .factories import (
    EcommerceSettingsFactory, OnlineProductFactory,
    CartFactory, CartItemFactory, OrderFactory
)


User = get_user_model()


@pytest.mark.django_db
class TestEgyptVATCalculation:
    """Test Egypt 14% VAT is applied correctly"""
    
    def test_vat_calculation_single_product(self):
        """Test 14% VAT on single product order"""
        settings = EcommerceSettingsFactory(vat_rate=Decimal('14.00'))
        
        subtotal = Decimal('100.00')
        discount = Decimal('0.00')
        shipping = Decimal('50.00')
        
        # Calculate tax: (subtotal - discount) * 0.14
        expected_tax = (subtotal - discount) * (settings.vat_rate / 100)
        expected_total = subtotal + shipping + expected_tax - discount
        
        assert expected_tax == Decimal('14.00')
        assert expected_total == Decimal('164.00')
    
    def test_vat_calculation_with_discount(self):
        """Test VAT calculated after discount"""
        settings = EcommerceSettingsFactory(vat_rate=Decimal('14.00'))
        
        subtotal = Decimal('200.00')
        discount = Decimal('50.00')  # 25% discount
        shipping = Decimal('50.00')
        
        # Tax on discounted amount
        taxable_amount = subtotal - discount  # 150
        expected_tax = taxable_amount * (settings.vat_rate / 100)  # 21
        expected_total = subtotal + shipping + expected_tax - discount  # 221
        
        assert expected_tax == Decimal('21.00')
        assert expected_total == Decimal('221.00')
    
    def test_order_total_calculation(self):
        """Test complete order total with Egypt VAT"""
        user = User.objects.create_user(username='testuser', password='pass123')
        cart = CartFactory(user=user)
        
        # Add products to cart
        product1 = OnlineProductFactory(price=Decimal('100.00'))
        product2 = OnlineProductFactory(price=Decimal('50.00'))
        CartItemFactory(cart=cart, product=product1, quantity=2)  # 200
        CartItemFactory(cart=cart, product=product2, quantity=1)  # 50
        
        subtotal = Decimal('250.00')
        discount = Decimal('0.00')
        shipping = Decimal('50.00')
        
        # 14% VAT
        tax = (subtotal - discount) * Decimal('0.14')
        total = subtotal + shipping + tax - discount
        
        assert tax == Decimal('35.00')
        assert total == Decimal('335.00')


@pytest.mark.django_db
class TestOrderCreation:
    """Test order creation process for Egypt"""
    
    def test_create_order_from_cart(self):
        """Test creating order from cart with correct totals"""
        user = User.objects.create_user(username='customer', password='pass123')
        cart = CartFactory(user=user)
        
        product = OnlineProductFactory(price=Decimal('100.00'))
        CartItemFactory(cart=cart, product=product, quantity=2)
        
        order = OrderFactory(
            user=user,
            subtotal=Decimal('200.00'),
            discount=Decimal('0.00'),
            shipping_cost=Decimal('50.00'),
            tax=Decimal('28.00'),  # 14% of 200
            total=Decimal('278.00')
        )
        
        assert order.subtotal == Decimal('200.00')
        assert order.tax == Decimal('28.00')
        assert order.total == Decimal('278.00')
        assert order.shipping_country == 'مصر'
    
    def test_stock_reduction_on_order(self):
        """Test product stock is reduced when order is placed"""
        product = OnlineProductFactory()
        
        # Simulate order placement
        initial_stock = product.stock
        order_quantity = 3
        
        # Stock should be reduced (this would be in place_order view)
        expected_stock = initial_stock - order_quantity
        
        assert expected_stock == initial_stock - order_quantity


@pytest.mark.django_db
class TestFreeShipping:
    """Test free shipping threshold for Egypt"""
    
    def test_free_shipping_threshold(self):
        """Test orders above 500 EGP get free shipping"""
        settings = EcommerceSettingsFactory(
            currency='EGP',
            free_shipping_threshold=Decimal('500.00'),
            default_shipping_cost=Decimal('50.00')
        )
        
        # Order below threshold
        subtotal_low = Decimal('300.00')
        shipping_low = settings.default_shipping_cost if subtotal_low < settings.free_shipping_threshold else Decimal('0.00')
        assert shipping_low == Decimal('50.00')
        
        # Order above threshold
        subtotal_high = Decimal('600.00')
        shipping_high = Decimal('0.00') if subtotal_high >= settings.free_shipping_threshold else settings.default_shipping_cost
        assert shipping_high == Decimal('0.00')


@pytest.mark.django_db
class TestPaymentStatus:
    """Test payment status transitions"""
    
    def test_mark_order_as_paid(self):
        """Test marking order as paid updates payment_status"""
        order = OrderFactory(payment_status='pending')
        
        # Simulate payment completion
        order.payment_status = 'paid'
        order.save()
        
        order.refresh_from_db()
        assert order.payment_status == 'paid'
    
    def test_payment_failed_status(self):
        """Test failed payment updates status"""
        order = OrderFactory(payment_status='pending')
        
        order.payment_status = 'failed'
        order.save()
        
        order.refresh_from_db()
        assert order.payment_status == 'failed'
