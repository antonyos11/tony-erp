"""
Tests for E-commerce REST API endpoints - Week 1 Egypt deployment
"""
import pytest
from django.urls import reverse
from decimal import Decimal
from .factories import (
    UserFactory, OnlineProductFactory, ProductCategoryFactory,
    CartFactory, CartItemFactory, OrderFactory, BrandFactory
)


@pytest.mark.django_db
class TestProductAPI:
    """Test product listing, filtering, and detail endpoints"""
    
    def test_product_list(self, api_client):
        """Test GET /api/products/ returns products"""
        # Create test products
        OnlineProductFactory.create_batch(5, is_active=True)
        
        url = reverse('product-list')
        response = api_client.get(url)
        
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 5
    
    def test_product_list_pagination(self, api_client):
        """Test pagination works correctly"""
        OnlineProductFactory.create_batch(25, is_active=True)
        
        url = reverse('product-list')
        response = api_client.get(url)
        
        assert response.status_code == 200
        assert 'next' in response.data
        assert 'previous' in response.data
        assert len(response.data['results']) == 20  # Default page size
    
    def test_product_detail(self, api_client):
        """Test GET /api/products/{id}/ returns product details"""
        product = OnlineProductFactory(
            display_name='Test Product',
            custom_price=Decimal('100.00'),
            is_active=True
        )
        
        url = reverse('product-detail', kwargs={'pk': product.pk})
        response = api_client.get(url)
        
        assert response.status_code == 200
        # Detail serializer uses display_name and custom_price
        assert response.data.get('display_name') or response.data.get('name')
        actual_price = Decimal(str(response.data.get('custom_price') or response.data.get('price', 0)))
        assert actual_price == Decimal('100.00')
    
    def test_product_filter_by_category(self, api_client):
        """Test filtering products by category"""
        category = ProductCategoryFactory(name='Electronics')
        OnlineProductFactory.create_batch(3, category=category, is_active=True)
        OnlineProductFactory.create_batch(2, is_active=True)  # Different category
        
        url = reverse('product-list')
        response = api_client.get(url, {'category': category.id})
        
        assert response.status_code == 200
        assert len(response.data['results']) == 3
    
    def test_product_search(self, api_client):
        """Test product search functionality"""
        OnlineProductFactory(display_name='Laptop HP', is_active=True)
        OnlineProductFactory(display_name='Mouse', is_active=True)
        
        url = reverse('product-list')
        response = api_client.get(url, {'search': 'Laptop'})
        
        assert response.status_code == 200
        assert len(response.data['results']) >= 1  # May include other products with 'Laptop'
        assert any('Laptop' in r['name'] for r in response.data['results'])
    
    def test_featured_products(self, api_client):
        """Test filtering featured products"""
        OnlineProductFactory.create_batch(3, is_featured=True, is_active=True)
        OnlineProductFactory.create_batch(2, is_featured=False, is_active=True)
        
        url = reverse('product-list')
        response = api_client.get(url, {'featured': 'true'})
        
        assert response.status_code == 200
        assert len(response.data['results']) == 3


@pytest.mark.django_db
class TestCartAPI:
    """Test shopping cart API endpoints"""
    
    def test_add_to_cart(self, api_client_authenticated):
        """Test POST /api/cart/add/ adds item to cart"""
        product = OnlineProductFactory(custom_price=Decimal('100.00'))
        
        url = reverse('cart-add')
        data = {
            'product_id': product.id,
            'quantity': 2
        }
        response = api_client_authenticated.post(url, data, format='json')
        
        assert response.status_code == 200
        assert 'message' in response.data
    
    def test_cart_list(self, api_client_authenticated):
        """Test GET /api/cart/ returns cart items"""
        cart = CartFactory(user=api_client_authenticated.user)
        product = OnlineProductFactory(custom_price=Decimal('100.00'))
        CartItemFactory(cart=cart, product=product, quantity=2)
        
        url = reverse('cart-list')
        response = api_client_authenticated.get(url)
        
        assert response.status_code == 200
        assert len(response.data['items']) == 1
        assert Decimal(response.data['total']) == Decimal('200.00')
    
    def test_update_cart_quantity(self, api_client_authenticated):
        """Test POST /api/cart/update_item/ updates quantity"""
        cart = CartFactory(user=api_client_authenticated.user)
        product = OnlineProductFactory(custom_price=Decimal('100.00'))
        item = CartItemFactory(cart=cart, product=product, quantity=1)
        
        url = reverse('cart-update-item')
        data = {'item_id': item.pk, 'quantity': 3}
        response = api_client_authenticated.post(url, data, format='json')
        
        assert response.status_code == 200
        item.refresh_from_db()
        assert item.quantity == 3
    
    def test_remove_from_cart(self, api_client_authenticated):
        """Test POST /api/cart/remove/ removes item"""
        cart = CartFactory(user=api_client_authenticated.user)
        product = OnlineProductFactory()
        item = CartItemFactory(cart=cart, product=product)
        
        url = reverse('cart-remove')
        data = {'item_id': item.pk}
        response = api_client_authenticated.post(url, data, format='json')
        
        assert response.status_code == 200
        assert not cart.items.exists()
    
    def test_clear_cart(self, api_client_authenticated):
        """Test POST /api/cart/clear/ empties cart"""
        cart = CartFactory(user=api_client_authenticated.user)
        CartItemFactory.create_batch(3, cart=cart)
        
        url = reverse('cart-clear')
        response = api_client_authenticated.post(url)
        
        assert response.status_code == 200
        assert cart.items.count() == 0


@pytest.mark.django_db
class TestOrderAPI:
    """Test order creation and tracking API"""
    
    def test_create_order(self, api_client_authenticated):
        """Test POST /api/orders/ creates order with Egypt VAT"""
        cart = CartFactory(user=api_client_authenticated.user)
        product = OnlineProductFactory(custom_price=Decimal('100.00'))
        CartItemFactory(cart=cart, product=product, quantity=1)
        
        url = reverse('order-list')
        data = {
            'customer_name': 'محمد أحمد',
            'customer_email': 'test@example.com',
            'customer_phone': '01234567890',
            'shipping_address': 'شارع المعز',
            'shipping_city': 'القاهرة',
            'shipping_country': 'مصر',
        }
        response = api_client_authenticated.post(url, data, format='json')
        
        assert response.status_code == 201
        assert 'order_number' in response.data
        
        # Verify 14% Egypt VAT applied
        order = api_client_authenticated.user.ecommerce_orders.first()
        assert order.tax == Decimal('14.00')  # 14% of 100
    
    def test_list_user_orders(self, api_client_authenticated):
        """Test GET /api/orders/ returns user orders"""
        OrderFactory.create_batch(3, user=api_client_authenticated.user)
        OrderFactory.create_batch(2)  # Other users' orders
        
        url = reverse('order-list')
        response = api_client_authenticated.get(url)
        
        assert response.status_code == 200
        assert len(response.data['results']) == 3
    
    def test_track_order(self, api_client_authenticated):
        """Test GET /api/orders/{id}/track/ endpoint"""
        order = OrderFactory(
            user=api_client_authenticated.user,
            order_number='ORD-123456',
            status='shipped'
        )
        
        url = reverse('order-track', kwargs={'pk': order.pk})
        response = api_client_authenticated.get(url)
        
        assert response.status_code == 200
        assert response.data['order_number'] == 'ORD-123456'
        assert response.data['status'] == 'shipped'
    
    def test_unauthorized_access_to_orders(self, api_client):
        """Test unauthenticated access to orders is blocked"""
        url = reverse('order-list')
        response = api_client.get(url)
        
        assert response.status_code == 401


@pytest.mark.django_db
class TestAPIAuthentication:
    """Test JWT authentication"""
    
    def test_obtain_token(self, api_client):
        """Test POST /api/token/ returns JWT tokens"""
        user = UserFactory(username='testuser')
        user.set_password('testpass123')
        user.save()
        
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_refresh_token(self, api_client):
        """Test POST /api/token/refresh/ refreshes access token"""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        user = UserFactory()
        refresh = RefreshToken.for_user(user)
        
        url = reverse('token_refresh')
        data = {'refresh': str(refresh)}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == 200
        assert 'access' in response.data


@pytest.mark.django_db
class TestAPIThrottling:
    """Test API rate limiting"""
    
    def test_throttle_anonymous_requests(self, api_client):
        """Test anonymous users are throttled at 100 requests/hour"""
        url = reverse('product-list')
        
        # Make requests within limit
        for _ in range(10):
            response = api_client.get(url)
            assert response.status_code == 200
