"""
Payment Gateway Base Class
Abstract base class for all payment gateway integrations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal


class PaymentGatewayBase(ABC):
    """
    Abstract base class for payment gateway integrations
    All payment gateways must implement these methods
    """
    
    def __init__(self, api_key: str, is_sandbox: bool = True):
        """
        Initialize payment gateway
        
        Args:
            api_key: API key for the gateway
            is_sandbox: Whether to use sandbox/test mode
        """
        self.api_key = api_key
        self.is_sandbox = is_sandbox
        self.base_url = self.get_base_url()
    
    @abstractmethod
    def get_base_url(self) -> str:
        """
        Get base URL for API calls (sandbox vs production)
        
        Returns:
            Base URL string
        """
        pass
    
    @abstractmethod
    def authenticate(self) -> Optional[str]:
        """
        Authenticate with payment gateway and get auth token
        
        Returns:
            Authentication token or None if failed
        """
        pass
    
    @abstractmethod
    def create_payment(self, order_id: int, amount: Decimal, currency: str = 'EGP',
                      customer_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a payment/checkout session
        
        Args:
            order_id: Order ID from database
            amount: Amount to charge
            currency: Currency code (default: EGP for Egypt)
            customer_data: Customer information dict
        
        Returns:
            Dict with payment details including payment URL/token
        """
        pass
    
    @abstractmethod
    def verify_callback(self, callback_data: Dict[str, Any]) -> bool:
        """
        Verify callback/webhook authenticity using signature
        
        Args:
            callback_data: Data received from gateway webhook
        
        Returns:
            True if signature is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get payment status by transaction ID
        
        Args:
            transaction_id: Transaction ID from gateway
        
        Returns:
            Dict with payment status and details
        """
        pass
    
    def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process callback data and extract relevant information
        
        Args:
            callback_data: Raw callback data from gateway
        
        Returns:
            Processed payment information
        """
        return {
            'success': False,
            'transaction_id': '',
            'amount': Decimal('0.00'),
            'status': 'unknown',
            'raw_data': callback_data
        }
    
    def format_amount(self, amount: Decimal, cents: bool = False) -> int:
        """
        Format amount for API (some gateways require cents)
        
        Args:
            amount: Decimal amount
            cents: Whether to convert to cents
        
        Returns:
            Formatted amount as integer
        """
        if cents:
            return int(amount * 100)
        return int(amount)
    
    def log_error(self, message: str, exception: Optional[Exception] = None):
        """
        Log error for debugging
        
        Args:
            message: Error message
            exception: Optional exception object
        """
        import logging
        logger = logging.getLogger(f'ecommerce.payments.{self.__class__.__name__.lower()}')
        if exception:
            logger.error(f"{message}: {str(exception)}", exc_info=True)
        else:
            logger.error(message)
    
    def log_info(self, message: str):
        """
        Log info message
        
        Args:
            message: Info message
        """
        import logging
        logger = logging.getLogger(f'ecommerce.payments.{self.__class__.__name__.lower()}')
        logger.info(message)
