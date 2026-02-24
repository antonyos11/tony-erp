"""
Paymob (Accept) Payment Gateway Integration
For Egypt market - cards, wallets, installments
Official documentation: https://accept.paymob.com/docs/
"""
import requests
import hashlib
import hmac
from typing import Dict, Any, Optional
from decimal import Decimal
from .base import PaymentGatewayBase


class PaymobGateway(PaymentGatewayBase):
    """
    Paymob (Accept) payment gateway for Egypt
    Supports: Cards, Mobile Wallets, ValU, Souhoola installments
    """
    
    def __init__(self, api_key: str, integration_ids: Dict[str, str], 
                 iframe_id: str, hmac_secret: str, is_sandbox: bool = True):
        """
        Initialize Paymob gateway
        
        Args:
            api_key: Paymob API key
            integration_ids: Dict of integration IDs {'card': 'id', 'wallet': 'id', 'valu': 'id'}
            iframe_id: iFrame ID for embedded payment form
            hmac_secret: HMAC secret key for webhook verification
            is_sandbox: Whether to use sandbox mode
        """
        super().__init__(api_key, is_sandbox)
        self.integration_ids = integration_ids
        self.iframe_id = iframe_id
        self.hmac_secret = hmac_secret
        self.auth_token = None
    
    def get_base_url(self) -> str:
        """Get Paymob API base URL"""
        # Paymob uses same URL for both sandbox and production
        # Test mode is controlled by integration IDs
        return "https://accept.paymob.com/api"
    
    def authenticate(self) -> Optional[str]:
        """
        Authenticate with Paymob and get auth token
        
        Returns:
            Authentication token string or None
        """
        url = f"{self.base_url}/auth/tokens"
        payload = {
            "api_key": self.api_key
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            self.auth_token = data.get('token')
            self.log_info(f"Paymob authentication successful")
            return self.auth_token
            
        except requests.exceptions.RequestException as e:
            self.log_error("Paymob authentication failed", e)
            return None
    
    def register_order(self, order_id: int, amount_cents: int, 
                      currency: str = 'EGP') -> Optional[str]:
        """
        Register order with Paymob
        
        Args:
            order_id: Order ID from database
            amount_cents: Amount in cents (e.g., 100.00 EGP = 10000 cents)
            currency: Currency code
        
        Returns:
            Paymob order ID or None
        """
        if not self.auth_token:
            self.authenticate()
        
        if not self.auth_token:
            return None
        
        url = f"{self.base_url}/ecommerce/orders"
        payload = {
            "auth_token": self.auth_token,
            "delivery_needed": "false",
            "amount_cents": str(amount_cents),
            "currency": currency,
            "merchant_order_id": str(order_id),
            "items": []
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            paymob_order_id = data.get('id')
            self.log_info(f"Paymob order registered: {paymob_order_id}")
            return str(paymob_order_id)
            
        except requests.exceptions.RequestException as e:
            self.log_error("Paymob order registration failed", e)
            return None
    
    def generate_payment_key(self, paymob_order_id: str, amount_cents: int,
                            integration_id: str, billing_data: Dict[str, str],
                            currency: str = 'EGP') -> Optional[str]:
        """
        Generate payment key for checkout
        
        Args:
            paymob_order_id: Order ID from Paymob
            amount_cents: Amount in cents
            integration_id: Integration ID for payment method
            billing_data: Customer billing information
            currency: Currency code
        
        Returns:
            Payment token or None
        """
        if not self.auth_token:
            self.authenticate()
        
        if not self.auth_token:
            return None
        
        url = f"{self.base_url}/acceptance/payment_keys"
        
        # Default billing data if not provided
        default_billing = {
            "apartment": "NA",
            "email": billing_data.get('email', 'customer@example.com'),
            "floor": "NA",
            "first_name": billing_data.get('first_name', 'Customer'),
            "street": billing_data.get('street', 'NA'),
            "building": "NA",
            "phone_number": billing_data.get('phone', '+201000000000'),
            "shipping_method": "NA",
            "postal_code": "NA",
            "city": billing_data.get('city', 'Cairo'),
            "country": billing_data.get('country', 'Egypt'),
            "last_name": billing_data.get('last_name', 'Name'),
            "state": "NA"
        }
        
        payload = {
            "auth_token": self.auth_token,
            "amount_cents": str(amount_cents),
            "expiration": 3600,  # 1 hour
            "order_id": paymob_order_id,
            "billing_data": default_billing,
            "currency": currency,
            "integration_id": integration_id
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            payment_token = data.get('token')
            self.log_info(f"Paymob payment key generated")
            return payment_token
            
        except requests.exceptions.RequestException as e:
            self.log_error("Paymob payment key generation failed", e)
            return None
    
    def create_payment(self, order_id: int, amount: Decimal, currency: str = 'EGP',
                      customer_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create payment session with Paymob
        
        Args:
            order_id: Order ID
            amount: Amount in EGP
            currency: Currency code
            customer_data: Customer information
        
        Returns:
            Dict with iframe_url and payment_token
        """
        # Convert amount to cents
        amount_cents = self.format_amount(amount, cents=True)
        
        # Step 1: Authenticate
        if not self.authenticate():
            return {'error': 'Authentication failed'}
        
        # Step 2: Register order
        paymob_order_id = self.register_order(order_id, amount_cents, currency)
        if not paymob_order_id:
            return {'error': 'Order registration failed'}
        
        # Prepare billing data
        billing_data = {}
        if customer_data:
            billing_data = {
                'first_name': customer_data.get('name', '').split()[0] if customer_data.get('name') else 'Customer',
                'last_name': ' '.join(customer_data.get('name', '').split()[1:]) if len(customer_data.get('name', '').split()) > 1 else 'Name',
                'email': customer_data.get('email', 'customer@example.com'),
                'phone': customer_data.get('phone', '+201000000000'),
                'city': customer_data.get('city', 'Cairo'),
                'country': customer_data.get('country', 'Egypt'),
                'street': customer_data.get('address', 'NA')
            }
        
        # Step 3: Generate payment key (use card integration by default)
        integration_id = self.integration_ids.get('card', '')
        payment_token = self.generate_payment_key(
            paymob_order_id, amount_cents, integration_id, billing_data, currency
        )
        
        if not payment_token:
            return {'error': 'Payment key generation failed'}
        
        # Step 4: Build iFrame URL
        iframe_url = self.build_iframe_url(payment_token)
        
        return {
            'success': True,
            'iframe_url': iframe_url,
            'payment_token': payment_token,
            'paymob_order_id': paymob_order_id
        }
    
    def build_iframe_url(self, payment_token: str) -> str:
        """
        Build iFrame URL for embedded payment form
        
        Args:
            payment_token: Payment token from Paymob
        
        Returns:
            Full iFrame URL
        """
        return f"https://accept.paymob.com/api/acceptance/iframes/{self.iframe_id}?payment_token={payment_token}"
    
    def verify_hmac(self, callback_data: Dict[str, Any], received_hmac: str) -> bool:
        """
        Verify HMAC signature from Paymob callback
        
        Args:
            callback_data: Callback data dict
            received_hmac: HMAC received in callback
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Paymob HMAC calculation (order matters!)
            obj = callback_data.get('obj', {})
            
            # Concatenate specific fields in order
            concat_string = (
                str(obj.get('amount_cents', '')) +
                str(obj.get('created_at', '')) +
                str(obj.get('currency', '')) +
                str(obj.get('error_occured', '')).lower() +
                str(obj.get('has_parent_transaction', '')).lower() +
                str(obj.get('id', '')) +
                str(obj.get('integration_id', '')) +
                str(obj.get('is_3d_secure', '')).lower() +
                str(obj.get('is_auth', '')).lower() +
                str(obj.get('is_capture', '')).lower() +
                str(obj.get('is_refunded', '')).lower() +
                str(obj.get('is_standalone_payment', '')).lower() +
                str(obj.get('is_voided', '')).lower() +
                str(obj.get('order', {}).get('id', '')) +
                str(obj.get('owner', '')) +
                str(obj.get('pending', '')).lower() +
                str(obj.get('source_data', {}).get('pan', '')) +
                str(obj.get('source_data', {}).get('sub_type', '')) +
                str(obj.get('source_data', {}).get('type', '')) +
                str(obj.get('success', '')).lower()
            )
            
            # Calculate HMAC SHA512
            calculated_hmac = hmac.new(
                self.hmac_secret.encode('utf-8'),
                concat_string.encode('utf-8'),
                hashlib.sha512
            ).hexdigest()
            
            is_valid = calculated_hmac == received_hmac
            
            if is_valid:
                self.log_info("Paymob HMAC verification successful")
            else:
                self.log_error(f"Paymob HMAC verification failed. Expected: {calculated_hmac[:20]}..., Got: {received_hmac[:20]}...")
            
            return is_valid
            
        except Exception as e:
            self.log_error("Paymob HMAC verification error", e)
            return False
    
    def verify_callback(self, callback_data: Dict[str, Any]) -> bool:
        """
        Verify Paymob callback authenticity
        
        Args:
            callback_data: Full callback data
        
        Returns:
            True if valid
        """
        received_hmac = callback_data.get('hmac', '')
        return self.verify_hmac(callback_data, received_hmac)
    
    def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Paymob callback and extract payment info
        
        Args:
            callback_data: Raw callback data
        
        Returns:
            Processed payment information
        """
        obj = callback_data.get('obj', {})
        
        success = obj.get('success', False)
        transaction_id = str(obj.get('id', ''))
        amount_cents = int(obj.get('amount_cents', 0))
        amount = Decimal(amount_cents) / 100
        
        # Get order ID
        order_data = obj.get('order', {})
        merchant_order_id = order_data.get('merchant_order_id', '')
        
        # Payment method
        source_data = obj.get('source_data', {})
        payment_method = source_data.get('type', 'unknown')
        
        # Status
        if success and not obj.get('pending', False):
            status = 'paid'
        elif obj.get('pending', False):
            status = 'pending'
        else:
            status = 'failed'
        
        return {
            'success': success,
            'transaction_id': transaction_id,
            'merchant_order_id': merchant_order_id,
            'amount': amount,
            'status': status,
            'payment_method': payment_method,
            'raw_data': callback_data
        }
    
    def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get payment status from Paymob
        
        Args:
            transaction_id: Paymob transaction ID
        
        Returns:
            Payment status dict
        """
        if not self.auth_token:
            self.authenticate()
        
        url = f"{self.base_url}/acceptance/transactions/{transaction_id}"
        
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': data.get('success', False),
                'status': 'paid' if data.get('success') else 'failed',
                'amount': Decimal(data.get('amount_cents', 0)) / 100,
                'data': data
            }
            
        except requests.exceptions.RequestException as e:
            self.log_error("Paymob status check failed", e)
            return {'success': False, 'error': str(e)}
