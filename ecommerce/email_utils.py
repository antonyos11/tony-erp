"""
Email utilities for Egypt e-commerce store
==========================================

Week 1 Phase 1 - Egypt Market
Manages email queue with django-post_office and Egyptian Arabic templates
"""

from post_office import mail
from django.conf import settings
from django.template.loader import render_to_string
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class EgyptEmailManager:
    """Manages all e-commerce emails for Egypt market with Arabic templates"""
    
    DEFAULT_PRIORITY = 'now'  # 'now', 'high', 'medium', 'low'
    
    @staticmethod
    def get_shop_context() -> Dict[str, Any]:
        """Get common shop information for all email templates"""
        from ecommerce.models import EcommerceSettings
        
        settings_obj = EcommerceSettings.get_settings()
        return {
            'shop_name': getattr(settings_obj, 'store_name', 'Tony ERP Store'),
            'website_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://tonyerp.com',
            'support_email': getattr(settings_obj, 'support_email', 'support@tonyerp.com'),
            'support_phone': getattr(settings_obj, 'support_phone', '15555'),
            'facebook_url': 'https://facebook.com/tonyerp',  # From settings
            'instagram_url': 'https://instagram.com/tonyerp',
            'whatsapp_url': 'https://wa.me/201234567890',  # Egypt WhatsApp
        }
    
    @classmethod
    def send_order_confirmation(
        cls,
        order,
        recipient_email: str,
        priority: str = DEFAULT_PRIORITY
    ) -> bool:
        """
        Send order confirmation email (Egyptian Arabic)
        
        Args:
            order: Order instance
            recipient_email: Customer email
            priority: Email priority ('now', 'high', 'medium', 'low')
            
        Returns:
            bool: True if email queued successfully
        """
        try:
            context = cls.get_shop_context()
            context.update({
                'customer_name': order.full_name or order.shipping_name,
                'order_number': order.order_number,
                'order_date': order.created_at.strftime('%Y-%m-%d %I:%M %p'),
                'order_items': [
                    {
                        'product_name': item.product.name_ar if hasattr(item.product, 'name_ar') else item.product.name,
                        'quantity': item.quantity,
                        'price': f"{item.unit_price:.2f}",
                        'total': f"{item.total_price:.2f}",
                    }
                    for item in order.items.all()
                ],
                'subtotal': f"{order.subtotal:.2f}",
                'discount': f"{order.discount:.2f}",
                'shipping_cost': f"{order.shipping_cost:.2f}",
                'tax': f"{order.tax:.2f}",
                'total': f"{order.total:.2f}",
                'currency': 'جنيه',  # Egypt currency
                'shipping_name': order.shipping_name,
                'shipping_address': order.shipping_address,
                'shipping_city': order.shipping_city,
                'shipping_country': order.shipping_country or 'مصر',
                'shipping_phone': order.shipping_phone,
                'payment_method': order.get_payment_method_display() if hasattr(order, 'get_payment_method_display') else 'دفع عند الاستلام',
                'order_tracking_url': f"{context['website_url']}/ecommerce/order-tracking/{order.order_number}/",
            })
            
            mail.send(
                recipients=[recipient_email],
                sender=settings.DEFAULT_FROM_EMAIL,
                template='order_confirmation_egypt_ar',
                context=context,
                priority=priority,
                headers={'Reply-To': context['support_email']},
            )
            
            logger.info(f"Order confirmation email queued for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send order confirmation email: {str(e)}")
            return False
    
    @classmethod
    def send_payment_success(
        cls,
        order,
        recipient_email: str,
        transaction_id: str,
        priority: str = DEFAULT_PRIORITY
    ) -> bool:
        """Send payment success confirmation email"""
        try:
            context = cls.get_shop_context()
            context.update({
                'order_number': order.order_number,
                'amount': f"{order.total:.2f}",
                'currency': 'جنيه',
                'payment_method': order.payment_method.name if order.payment_method else 'بطاقة ائتمان',
                'transaction_id': transaction_id,
                'payment_date': order.payment_completed_at.strftime('%Y-%m-%d %I:%M %p') if order.payment_completed_at else '',
                'invoice_url': f"{context['website_url']}/ecommerce/invoice/{order.order_number}/",
                'tracking_url': f"{context['website_url']}/ecommerce/order-tracking/{order.order_number}/",
            })
            
            mail.send(
                recipients=[recipient_email],
                sender=settings.DEFAULT_FROM_EMAIL,
                template='payment_success_ar',
                context=context,
                priority=priority,
            )
            
            logger.info(f"Payment success email queued for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send payment success email: {str(e)}")
            return False
    
    @classmethod
    def send_fawry_instructions(
        cls,
        order,
        recipient_email: str,
        fawry_reference: str,
        priority: str = 'high'  # High priority for payment instructions
    ) -> bool:
        """Send Fawry payment instructions with reference number"""
        try:
            context = cls.get_shop_context()
            context.update({
                'order_number': order.order_number,
                'fawry_reference_number': fawry_reference,
                'total_amount': f"{order.total:.2f}",
                'currency': 'جنيه',
                'valid_days': 7,  # Fawry reference validity
                'fawry_locations_url': 'https://fawry.com/locations',
            })
            
            mail.send(
                recipients=[recipient_email],
                sender=settings.DEFAULT_FROM_EMAIL,
                template='fawry_payment_instructions_ar',
                context=context,
                priority=priority,
            )
            
            logger.info(f"Fawry instructions email queued for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Fawry instructions email: {str(e)}")
            return False
    
    @classmethod
    def send_shipping_notification(
        cls,
        order,
        recipient_email: str,
        tracking_number: str,
        courier_info: Dict[str, str],
        priority: str = 'high'
    ) -> bool:
        """Send shipping notification with tracking number"""
        try:
            context = cls.get_shop_context()
            context.update({
                'customer_name': order.shipping_name,
                'order_number': order.order_number,
                'tracking_number': tracking_number,
                'shipping_company': courier_info.get('company', 'شركة الشحن'),
                'courier_name': courier_info.get('name', 'المندوب'),
                'courier_phone': courier_info.get('phone', ''),
                'order_date': order.created_at.strftime('%Y-%m-%d'),
                'packaging_date': courier_info.get('packaging_date', ''),
                'shipping_date': courier_info.get('shipping_date', ''),
                'estimated_delivery_date': courier_info.get('estimated_delivery', '3-5 أيام عمل'),
                'shipping_address': f"{order.shipping_address}, {order.shipping_city}",
                'tracking_url': f"{context['website_url']}/ecommerce/tracking/{tracking_number}/",
            })
            
            mail.send(
                recipients=[recipient_email],
                sender=settings.DEFAULT_FROM_EMAIL,
                template='shipping_egypt_ar',
                context=context,
                priority=priority,
            )
            
            logger.info(f"Shipping notification email queued for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send shipping notification email: {str(e)}")
            return False
    
    @classmethod
    def send_cod_confirmation(
        cls,
        order,
        recipient_email: str,
        priority: str = DEFAULT_PRIORITY
    ) -> bool:
        """Send COD (Cash on Delivery) confirmation email"""
        try:
            context = cls.get_shop_context()
            context.update({
                'customer_name': order.shipping_name,
                'order_number': order.order_number,
                'total_amount': f"{order.total:.2f}",
                'currency': 'جنيه',
                'order_date': order.created_at.strftime('%Y-%m-%d'),
                'estimated_delivery': '3-5 أيام عمل',
                'shipping_address': f"{order.shipping_address}, {order.shipping_city}",
                'order_tracking_url': f"{context['website_url']}/ecommerce/order-tracking/{order.order_number}/",
                'my_orders_url': f"{context['website_url']}/ecommerce/my-orders/",
            })
            
            mail.send(
                recipients=[recipient_email],
                sender=settings.DEFAULT_FROM_EMAIL,
                template='cod_confirmation_ar',
                context=context,
                priority=priority,
            )
            
            logger.info(f"COD confirmation email queued for order {order.order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send COD confirmation email: {str(e)}")
            return False
    
    @classmethod
    def send_abandoned_cart(
        cls,
        cart,
        recipient_email: str,
        coupon_code: Optional[str] = None,
        discount_percentage: int = 10,
        priority: str = 'medium'
    ) -> bool:
        """Send abandoned cart reminder with optional coupon"""
        try:
            from datetime import datetime, timedelta
            
            context = cls.get_shop_context()
            
            # Calculate cart age
            cart_age = (datetime.now() - cart.updated_at).days if hasattr(cart, 'updated_at') else 1
            
            context.update({
                'customer_name': cart.user.get_full_name() if cart.user else 'عزيزي العميل',
                'items_count': cart.items.count(),
                'days_ago': cart_age,
                'cart_items': [
                    {
                        'name': item.product.name_ar if hasattr(item.product, 'name_ar') else item.product.name,
                        'price': f"{item.product.price:.2f}",
                        'image_url': item.product.get_main_image_url() if hasattr(item.product, 'get_main_image_url') else '',
                    }
                    for item in cart.items.all()[:3]  # Show max 3 items
                ],
                'currency': 'جنيه',
                'has_coupon': bool(coupon_code),
                'coupon_code': coupon_code or '',
                'discount_percentage': discount_percentage,
                'coupon_valid_days': 7,
                'hours_left': 48,  # Urgency
                'cart_url': f"{context['website_url']}/ecommerce/cart/",
                'unsubscribe_url': f"{context['website_url']}/ecommerce/unsubscribe/",
            })
            
            mail.send(
                recipients=[recipient_email],
                sender=settings.DEFAULT_FROM_EMAIL,
                template='abandoned_cart_egypt_ar',
                context=context,
                priority=priority,
            )
            
            logger.info(f"Abandoned cart email queued for cart {cart.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send abandoned cart email: {str(e)}")
            return False
