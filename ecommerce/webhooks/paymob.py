"""
Paymob Webhook Handler
Processes payment callbacks from Paymob Accept
"""
import logging
from typing import Dict, Any
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from decimal import Decimal

from ..models import Order
from ..payment_gateways.paymob import PaymobGateway

logger = logging.getLogger('ecommerce.payments.paymob')


class PaymobWebhookHandler:
    """Handler for Paymob payment webhooks"""
    
    def __init__(self, gateway: PaymobGateway):
        """
        Initialize webhook handler
        
        Args:
            gateway: Configured PaymobGateway instance
        """
        self.gateway = gateway
    
    def handle(self, request: HttpRequest) -> JsonResponse:
        """
        Handle incoming Paymob webhook
        
        Args:
            request: Django HTTP request object
        
        Returns:
            JsonResponse with status
        """
        try:
            # Get callback data
            callback_data = request.POST.dict() if request.POST else {}
            
            # If empty, try JSON body
            if not callback_data:
                import json
                try:
                    callback_data = json.loads(request.body.decode('utf-8'))
                except:
                    callback_data = {}
            
            logger.info(f"Paymob webhook received")
            
            # Verify HMAC signature
            if not self.gateway.verify_callback(callback_data):
                logger.error("Paymob webhook HMAC verification failed")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid signature'
                }, status=400)
            
            # Process callback
            payment_info = self.gateway.process_callback(callback_data)
            
            # Get order
            merchant_order_id = payment_info.get('merchant_order_id')
            if not merchant_order_id:
                logger.error("No merchant_order_id in callback")
                return JsonResponse({
                    'status': 'error',
                    'message': 'No order ID'
                }, status=400)
            
            try:
                order = Order.objects.get(id=merchant_order_id)
            except Order.DoesNotExist:
                logger.error(f"Order {merchant_order_id} not found")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Order not found'
                }, status=404)
            
            # Check for duplicate processing (idempotency)
            if order.payment_status == 'paid' and order.payment_gateway_transaction_id == payment_info.get('transaction_id'):
                logger.info(f"Order {order.order_number} already processed, skipping")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Already processed'
                })
            
            # Update order based on payment status
            if payment_info['success'] and payment_info['status'] == 'paid':
                # Payment successful
                order.mark_as_paid(
                    transaction_id=payment_info['transaction_id'],
                    reference=payment_info.get('transaction_id', ''),
                    callback_data=payment_info['raw_data']
                )
                
                logger.info(f"Order {order.order_number} marked as paid. Transaction: {payment_info['transaction_id']}")
                
                # Send confirmation email (will be implemented later)
                self._send_confirmation_email(order)
                
                # Create invoice if not exists (link to sales module)
                self._create_invoice(order)
                
            elif payment_info['status'] == 'pending':
                # Payment pending
                order.payment_status = 'pending'
                order.payment_gateway_transaction_id = payment_info['transaction_id']
                order.payment_gateway_callback_data = payment_info['raw_data']
                order.save()
                
                logger.info(f"Order {order.order_number} payment pending")
                
            else:
                # Payment failed
                order.payment_status = 'failed'
                order.payment_gateway_transaction_id = payment_info.get('transaction_id', '')
                order.payment_gateway_callback_data = payment_info['raw_data']
                order.save()
                
                logger.warning(f"Order {order.order_number} payment failed")
            
            return JsonResponse({
                'status': 'success',
                'order_number': order.order_number
            })
            
        except Exception as e:
            logger.error(f"Paymob webhook processing error: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': 'Processing error'
            }, status=500)
    
    def _send_confirmation_email(self, order: Order):
        """
        Send order confirmation email
        
        Args:
            order: Order object
        """
        # TODO: Implement with django-post_office
        # Will be implemented in email system task
        logger.info(f"TODO: Send confirmation email for order {order.order_number}")
    
    def _create_invoice(self, order: Order):
        """
        Create sales invoice from order
        
        Args:
            order: Order object
        """
        # Check if invoice already exists
        if order.invoice:
            return
        
        try:
            # Import here to avoid circular imports
            from sales.models import Invoice, InvoiceItem
            from partners.models import Customer
            
            # Get or create customer
            customer = order.customer
            if not customer and order.user:
                # Try to get customer linked to user
                customer = Customer.objects.filter(email=order.customer_email).first()
            
            # Create invoice
            invoice = Invoice.objects.create(
                customer=customer,
                invoice_type='sales',
                status='paid' if order.payment_status == 'paid' else 'pending',
                subtotal=order.subtotal,
                discount=order.discount,
                tax=order.tax,
                total=order.total,
                notes=f"طلب إلكتروني #{order.order_number}"
            )
            
            # Create invoice items from order items
            for order_item in order.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=order_item.product.inventory_item if hasattr(order_item.product, 'inventory_item') else None,
                    description=order_item.product_name,
                    quantity=order_item.quantity,
                    unit_price=order_item.unit_price,
                    total=order_item.subtotal
                )
            
            # Link invoice to order
            order.invoice = invoice
            order.save()
            
            logger.info(f"Invoice {invoice.invoice_number} created for order {order.order_number}")
            
        except Exception as e:
            logger.error(f"Failed to create invoice for order {order.order_number}: {str(e)}", exc_info=True)


@csrf_exempt
@require_POST
def paymob_webhook(request):
    """
    Paymob webhook endpoint
    URL: /ecommerce/webhooks/paymob/
    """
    from ..models import PaymentGateway
    
    try:
        # Get Paymob gateway configuration
        paymob_gateway_obj = PaymentGateway.objects.filter(
            gateway_type__in=['paymob_card', 'paymob_wallet', 'paymob_valu', 'paymob_souhoola'],
            is_active=True
        ).first()
        
        if not paymob_gateway_obj:
            return JsonResponse({'error': 'Paymob gateway not configured'}, status=500)
        
        # Get credentials
        credentials = paymob_gateway_obj.get_active_credentials() if hasattr(paymob_gateway_obj, 'get_active_credentials') else {
            'api_key': paymob_gateway_obj.api_key,
            'api_secret': paymob_gateway_obj.api_secret
        }
        
        # Get extra settings (integration IDs, iframe ID, HMAC secret)
        extra_settings = paymob_gateway_obj.extra_settings or {}
        integration_ids = extra_settings.get('integration_ids', {})
        iframe_id = extra_settings.get('iframe_id', '')
        hmac_secret = extra_settings.get('hmac_secret', '')
        
        # Initialize gateway
        gateway = PaymobGateway(
            api_key=credentials.get('api_key', ''),
            integration_ids=integration_ids,
            iframe_id=iframe_id,
            hmac_secret=hmac_secret,
            is_sandbox=paymob_gateway_obj.is_sandbox
        )
        
        # Handle webhook
        handler = PaymobWebhookHandler(gateway)
        return handler.handle(request)
        
    except Exception as e:
        logger.error(f"Paymob webhook error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal error'}, status=500)
