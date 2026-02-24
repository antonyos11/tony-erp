"""
WooCommerce API Client
Wrapper around WooCommerce REST API for Python
"""

from typing import Dict, List, Optional, Any
import requests
from requests.auth import HTTPBasicAuth
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WooCommerceAPIError(Exception):
    """Custom exception for WooCommerce API errors"""
    pass


class WooCommerceClient:
    """WooCommerce REST API Client"""
    
    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str, version: str = 'wc/v3'):
        """
        Initialize WooCommerce API Client
        
        Args:
            store_url: WooCommerce store URL (e.g., 'https://example.com')
            consumer_key: WooCommerce Consumer Key
            consumer_secret: WooCommerce Consumer Secret
            version: API version (default: 'wc/v3')
        """
        self.store_url = store_url.rstrip('/')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.version = version
        self.base_url = f"{self.store_url}/wp-json/{version}"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """
        Make API request
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/products')
            params: Query parameters
            data: Request body data
            
        Returns:
            Response JSON
            
        Raises:
            WooCommerceAPIError: If API request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"WooCommerce API Error: {method} {url} - {str(e)}")
            raise WooCommerceAPIError(f"API request failed: {str(e)}")
    
    # ========== Products ==========
    
    def get_products(self, per_page: int = 100, page: int = 1, **filters) -> List[Dict]:
        """Get products from WooCommerce"""
        params = {'per_page': per_page, 'page': page, **filters}
        return self._request('GET', '/products', params=params)
    
    def get_product(self, product_id: int) -> Dict:
        """Get single product by ID"""
        return self._request('GET', f'/products/{product_id}')
    
    def create_product(self, product_data: Dict) -> Dict:
        """Create new product"""
        return self._request('POST', '/products', data=product_data)
    
    def update_product(self, product_id: int, product_data: Dict) -> Dict:
        """Update existing product"""
        return self._request('PUT', f'/products/{product_id}', data=product_data)
    
    def delete_product(self, product_id: int, force: bool = False) -> Dict:
        """Delete product"""
        params = {'force': force}
        return self._request('DELETE', f'/products/{product_id}', params=params)
    
    def update_product_stock(self, product_id: int, stock_quantity: int) -> Dict:
        """Update product stock quantity"""
        data = {
            'stock_quantity': stock_quantity,
            'manage_stock': True,
            'stock_status': 'instock' if stock_quantity > 0 else 'outofstock'
        }
        return self.update_product(product_id, data)
    
    # ========== Orders ==========
    
    def get_orders(self, per_page: int = 100, page: int = 1, **filters) -> List[Dict]:
        """Get orders from WooCommerce"""
        params = {'per_page': per_page, 'page': page, **filters}
        return self._request('GET', '/orders', params=params)
    
    def get_order(self, order_id: int) -> Dict:
        """Get single order by ID"""
        return self._request('GET', f'/orders/{order_id}')
    
    def update_order(self, order_id: int, order_data: Dict) -> Dict:
        """Update existing order"""
        return self._request('PUT', f'/orders/{order_id}', data=order_data)
    
    def update_order_status(self, order_id: int, status: str) -> Dict:
        """Update order status"""
        return self.update_order(order_id, {'status': status})
    
    # ========== Customers ==========
    
    def get_customers(self, per_page: int = 100, page: int = 1, **filters) -> List[Dict]:
        """Get customers from WooCommerce"""
        params = {'per_page': per_page, 'page': page, **filters}
        return self._request('GET', '/customers', params=params)
    
    def get_customer(self, customer_id: int) -> Dict:
        """Get single customer by ID"""
        return self._request('GET', f'/customers/{customer_id}')
    
    def create_customer(self, customer_data: Dict) -> Dict:
        """Create new customer"""
        return self._request('POST', '/customers', data=customer_data)
    
    def update_customer(self, customer_id: int, customer_data: Dict) -> Dict:
        """Update existing customer"""
        return self._request('PUT', f'/customers/{customer_id}', data=customer_data)
    
    # ========== Webhooks ==========
    
    def get_webhooks(self) -> List[Dict]:
        """Get all webhooks"""
        return self._request('GET', '/webhooks')
    
    def create_webhook(self, webhook_data: Dict) -> Dict:
        """Create webhook"""
        return self._request('POST', '/webhooks', data=webhook_data)
    
    def delete_webhook(self, webhook_id: int, force: bool = True) -> Dict:
        """Delete webhook"""
        params = {'force': force}
        return self._request('DELETE', f'/webhooks/{webhook_id}', params=params)
    
    # ========== System Status ==========
    
    def get_system_status(self) -> Dict:
        """Get WooCommerce system status"""
        return self._request('GET', '/system_status')
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            self.get_system_status()
            return True
        except WooCommerceAPIError:
            return False
