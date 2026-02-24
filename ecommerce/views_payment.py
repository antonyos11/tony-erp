"""
Payment Processing Views
Handles payment initiation, callbacks, and status pages
"""
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.urls import reverse

from .models import Order, PaymentGateway
from .payment_gateways.paymob import PaymobGateway

logger = logging.getLogger('ecommerce.payments')


@login_required
@require_http_methods(["GET", "POST"])
def initiate_payment(request, order_id):
    """
    Initiate payment for an order
    Redirects to payment gateway
    
    URL: /ecommerce/payment/initiate/<order_id>/
    """
    order = get_object_or_404(Order, id=order_id)
    
    # Security check: user must own the order
    if request.user != order.user and not request.user.is_staff:
        return HttpResponse("غير مصرح لك بالوصول لهذا الطلب", status=403)
    
    # Check if order is already paid
    if order.payment_status == 'paid':
        return redirect('ecommerce:order_detail', pk=order.id)
    
    # Get selected payment method
    payment_method_id = request.POST.get('payment_method_id') or request.GET.get('payment_method_id')
    
    if not payment_method_id:
        # Show payment method selection page
        payment_gateways = PaymentGateway.objects.filter(is_active=True).order_by('sort_order')
        
        return render(request, 'ecommerce/payment/select_method.html', {
            'order': order,
            'payment_gateways': payment_gateways
        })
    
    try:
        payment_gateway = PaymentGateway.objects.get(id=payment_method_id, is_active=True)
    except PaymentGateway.DoesNotExist:
        return HttpResponse("طريقة الدفع غير صحيحة", status=400)
    
    # Update order payment method
    order.payment_method = payment_gateway
    order.save()
    
    # Handle different gateway types
    gateway_type = payment_gateway.gateway_type
    
    # COD (Cash on Delivery)
    if gateway_type == 'cod':
        order.payment_status = 'pending'
        order.status = 'confirmed'
        order.save()
        return redirect('ecommerce:payment_success', order_id=order.id)
    
    # Bank Transfer
    elif gateway_type == 'bank_transfer':
        order.payment_status = 'pending'
        order.status = 'pending'
        order.save()
        return render(request, 'ecommerce/payment/bank_transfer_instructions.html', {
            'order': order
        })
    
    # Paymob (Egypt)
    elif gateway_type in ['paymob_card', 'paymob_wallet', 'paymob_valu', 'paymob_souhoola']:
        return _initiate_paymob_payment(request, order, payment_gateway)
    
    # Other gateways (to be implemented)
    else:
        return HttpResponse(f"بوابة الدفع {gateway_type} غير مدعومة حالياً", status=501)


def _initiate_paymob_payment(request, order, payment_gateway):
    """
    Initiate Paymob payment
    
    Args:
        request: HTTP request
        order: Order object
        payment_gateway: PaymentGateway object
    
    Returns:
        Redirect to Paymob iframe or error page
    """
    try:
        # Get credentials
        credentials = payment_gateway.get_active_credentials() if hasattr(payment_gateway, 'get_active_credentials') else {
            'api_key': payment_gateway.api_key,
            'api_secret': payment_gateway.api_secret
        }
        
        # Get extra settings
        extra_settings = payment_gateway.extra_settings or {}
        integration_ids = extra_settings.get('integration_ids', {})
        iframe_id = extra_settings.get('iframe_id', '')
        hmac_secret = extra_settings.get('hmac_secret', '')
        
        # Determine integration ID based on gateway type
        integration_type_map = {
            'paymob_card': 'card',
            'paymob_wallet': 'wallet',
            'paymob_valu': 'valu',
            'paymob_souhoola': 'souhoola'
        }
        integration_type = integration_type_map.get(payment_gateway.gateway_type, 'card')
        
        # Initialize gateway
        gateway = PaymobGateway(
            api_key=credentials.get('api_key', ''),
            integration_ids=integration_ids,
            iframe_id=iframe_id,
            hmac_secret=hmac_secret,
            is_sandbox=payment_gateway.is_sandbox
        )
        
        # Prepare customer data
        customer_data = {
            'name': order.customer_name,
            'email': order.customer_email,
            'phone': order.customer_phone,
            'city': order.shipping_city,
            'country': order.shipping_country,
            'address': order.shipping_address
        }
        
        # Create payment
        result = gateway.create_payment(
            order_id=order.id,
            amount=order.total,
            currency='EGP',
            customer_data=customer_data
        )
        
        if result.get('error'):
            logger.error(f"Paymob payment creation failed for order {order.order_number}: {result['error']}")
            return render(request, 'ecommerce/payment/error.html', {
                'order': order,
                'error_message': 'فشل في إنشاء عملية الدفع. برجاء المحاولة مرة أخرى.'
            })
        
        # Store payment token in session for verification
        request.session[f'payment_token_{order.id}'] = result.get('payment_token')
        
        # Redirect to Paymob iframe
        iframe_url = result.get('iframe_url')
        
        return render(request, 'ecommerce/payment/paymob_iframe.html', {
            'order': order,
            'iframe_url': iframe_url
        })
        
    except Exception as e:
        logger.error(f"Paymob payment initiation error for order {order.order_number}: {str(e)}", exc_info=True)
        return render(request, 'ecommerce/payment/error.html', {
            'order': order,
            'error_message': 'حدث خطأ في معالجة الدفع. برجاء المحاولة مرة أخرى.'
        })


@require_http_methods(["GET"])
def paymob_response(request):
    """
    Paymob user redirect after payment
    Called when user returns from Paymob iframe
    
    URL: /ecommerce/payment/paymob/response/
    Query params: ?success=true&id=xxx&order=xxx
    """
    # Get query parameters
    success = request.GET.get('success', 'false').lower() == 'true'
    transaction_id = request.GET.get('id', '')
    merchant_order_id = request.GET.get('merchant_order_id') or request.GET.get('order')
    
    logger.info(f"Paymob response: success={success}, transaction={transaction_id}, order={merchant_order_id}")
    
    if not merchant_order_id:
        return render(request, 'ecommerce/payment/error.html', {
            'error_message': 'معلومات الطلب غير موجودة'
        })
    
    try:
        order = Order.objects.get(id=merchant_order_id)
    except Order.DoesNotExist:
        return render(request, 'ecommerce/payment/error.html', {
            'error_message': 'الطلب غير موجود'
        })
    
    # Wait for webhook to process (it should have already updated the order)
    # Check order payment status
    if order.payment_status == 'paid':
        return redirect('ecommerce:payment_success', order_id=order.id)
    elif success:
        # Webhook might not have processed yet, show pending page
        return render(request, 'ecommerce/payment/pending.html', {
            'order': order,
            'message': 'جاري التحقق من الدفع...'
        })
    else:
        return redirect('ecommerce:payment_failed', order_id=order.id)


@require_http_methods(["GET"])
def payment_success(request, order_id):
    """
    Payment success page
    
    URL: /ecommerce/payment/success/<order_id>/
    """
    order = get_object_or_404(Order, id=order_id)
    
    # Security check (allow anyone with order link for better UX)
    # if request.user.is_authenticated and request.user != order.user and not request.user.is_staff:
    #     return HttpResponse("غير مصرح لك بالوصول لهذا الطلب", status=403)
    
    return render(request, 'ecommerce/payment/success.html', {
        'order': order
    })


@require_http_methods(["GET"])
def payment_failed(request, order_id):
    """
    Payment failed page
    
    URL: /ecommerce/payment/failed/<order_id>/
    """
    order = get_object_or_404(Order, id=order_id)
    
    # Security check
    # if request.user.is_authenticated and request.user != order.user and not request.user.is_staff:
    #     return HttpResponse("غير مصرح لك بالوصول لهذا الطلب", status=403)
    
    return render(request, 'ecommerce/payment/failed.html', {
        'order': order
    })


@require_http_methods(["GET"])
def check_payment_status(request, order_id):
    """
    AJAX endpoint to check payment status
    Used for pending payments
    
    URL: /ecommerce/payment/check-status/<order_id>/
    """
    try:
        order = Order.objects.get(id=order_id)
        
        return JsonResponse({
            'status': order.payment_status,
            'order_status': order.status,
            'paid': order.payment_status == 'paid'
        })
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
