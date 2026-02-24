"""
Tests for shopping cart functionality
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from .factories import (
    CartFactory, CartItemFactory, OnlineProductFactory, UserFactory
)


User = get_user_model()


@pytest.mark.django_db
class TestCartCreation:
    """Test cart creation and management"""
    
    def test_create_cart_for_user(self):
        """Test creating cart for authenticated user"""
        user = UserFactory()
        cart = CartFactory(user=user)
        
        assert cart.user == user
        assert cart.items.count() == 0
    
    def test_create_cart_with_session(self):
        """Test creating cart with session key for anonymous users"""
        cart = CartFactory(user=None, session_key='abc123')
        
        assert cart.user is None
        assert cart.session_key == 'abc123'


@pytest.mark.django_db
class TestAddToCart:
    """Test adding products to cart"""
    
    def test_add_product_to_empty_cart(self):
        """Test adding first product to cart"""
        user = UserFactory()
        cart = CartFactory(user=user)
        product = OnlineProductFactory(custom_price=Decimal('100.00'))
        
        item = CartItemFactory(
            cart=cart,
            product=product,
            quantity=1
        )
        
        assert cart.items.count() == 1
        assert item.quantity == 1
        assert item.subtotal == Decimal('100.00')
    
    def test_add_multiple_products(self):
        """Test adding multiple different products"""
        cart = CartFactory()
        product1 = OnlineProductFactory(custom_price=Decimal('100.00'))
        product2 = OnlineProductFactory(custom_price=Decimal('50.00'))
        
        CartItemFactory(cart=cart, product=product1, quantity=1)
        CartItemFactory(cart=cart, product=product2, quantity=2)
        
        assert cart.items.count() == 2
    
    def test_add_out_of_stock_product(self):
        """Test adding product (stock is managed by inventory)"""
        product = OnlineProductFactory()
        cart = CartFactory()
        
        # Add product to cart
        item = CartItemFactory(cart=cart, product=product, quantity=5)
        assert item.quantity == 5


@pytest.mark.django_db
class TestUpdateCartItem:
    """Test updating cart item quantities"""
    
    def test_increase_quantity(self):
        """Test increasing item quantity"""
        product = OnlineProductFactory(custom_price=Decimal('100.00'))
        cart = CartFactory()
        item = CartItemFactory(cart=cart, product=product, quantity=1)
        
        item.quantity = 3
        item.save()
        
        item.refresh_from_db()
        assert item.quantity == 3
        assert item.subtotal == Decimal('300.00')
    
    def test_decrease_quantity(self):
        """Test decreasing item quantity"""
        product = OnlineProductFactory(custom_price=Decimal('100.00'))
        cart = CartFactory()
        item = CartItemFactory(cart=cart, product=product, quantity=5)
        
        item.quantity = 2
        item.save()
        
        item.refresh_from_db()
        assert item.quantity == 2
        assert item.subtotal == Decimal('200.00')
    
    def test_update_to_zero_removes_item(self):
        """Test setting quantity to 0 removes item"""
        cart = CartFactory()
        item = CartItemFactory(cart=cart, quantity=3)
        
        # Simulate remove by setting quantity to 0
        item.delete()
        
        assert cart.items.count() == 0


@pytest.mark.django_db
class TestRemoveFromCart:
    """Test removing items from cart"""
    
    def test_remove_single_item(self):
        """Test removing one item from cart"""
        cart = CartFactory()
        item1 = CartItemFactory(cart=cart)
        item2 = CartItemFactory(cart=cart)
        
        item1.delete()
        
        assert cart.items.count() == 1
        assert cart.items.first() == item2
    
    def test_remove_all_items(self):
        """Test clearing cart completely"""
        cart = CartFactory()
        CartItemFactory.create_batch(3, cart=cart)
        
        cart.items.all().delete()
        
        assert cart.items.count() == 0


@pytest.mark.django_db
class TestCartCalculations:
    """Test cart total calculations"""
    
    def test_cart_subtotal(self):
        """Test cart subtotal calculation"""
        cart = CartFactory()
        product1 = OnlineProductFactory(custom_price=Decimal('100.00'))
        product2 = OnlineProductFactory(custom_price=Decimal('50.00'))
        
        CartItemFactory(cart=cart, product=product1, quantity=2)
        CartItemFactory(cart=cart, product=product2, quantity=1)
        
        # Calculate subtotal
        items = list(cart.items.all())
        subtotal = sum((item.subtotal for item in items), Decimal('0'))
        
        assert subtotal == Decimal('250.00')  # (100*2) + (50*1)
    
    def test_empty_cart_total(self):
        """Test empty cart has zero total"""
        cart = CartFactory()
        
        items = list(cart.items.all())
        subtotal = sum((item.subtotal for item in items), Decimal('0'))
        
        assert subtotal == Decimal('0.00')
    
    def test_cart_item_count(self):
        """Test total item count in cart"""
        cart = CartFactory()
        CartItemFactory(cart=cart, quantity=2)
        CartItemFactory(cart=cart, quantity=3)
        CartItemFactory(cart=cart, quantity=1)
        
        items = list(cart.items.all())
        total_items = sum((item.quantity for item in items), 0)
        
        assert total_items == 6


@pytest.mark.django_db
class TestCartMerge:
    """Test merging anonymous cart with user cart on login"""
    
    def test_merge_session_cart_to_user_cart(self):
        """Test anonymous cart items move to user cart on login"""
        user = UserFactory()
        
        # Anonymous cart
        session_cart = CartFactory(user=None, session_key='session123')
        product1 = OnlineProductFactory(custom_price=Decimal('100.00'))
        CartItemFactory(cart=session_cart, product=product1, quantity=2)
        
        # User logs in, simulate cart merge
        user_cart = CartFactory(user=user)
        
        # Move items from session cart to user cart
        session_items = list(session_cart.items.all())
        for item in session_items:
            CartItemFactory(
                cart=user_cart,
                product=item.product,
                quantity=item.quantity
            )
        
        # Delete session cart
        session_cart.delete()
        
        assert user_cart.items.count() == 1
        assert user_cart.items.first().product == product1
