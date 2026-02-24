"""
خدمة الرسائل التلقائية
Auto Messaging Service

دعم:
- SMS
- WhatsApp
- إشعارات داخلية
"""
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class MessageTemplates:
    """قوالب الرسائل المختلفة"""
    
    TEMPLATES = {
        'order_confirmed': {
            'ar': 'عزيزنا {customer_name}، تم تأكيد طلبك رقم {order_number}. الإجمالي: {total} ج.م',
            'en': 'Dear {customer_name}, your order {order_number} is confirmed. Total: {total} EGP',
            'whatsapp': True,
            'sms': True,
            'category': 'orders'
        },
        'order_ready': {
            'ar': 'طلبك {order_number} جاهز للاستلام من معرض {showroom}. شكراً لثقتك',
            'en': 'Your order {order_number} is ready for pickup at {showroom}. Thank you!',
            'whatsapp': True,
            'sms': True,
            'category': 'orders'
        },
        'production_started': {
            'ar': 'بدأ تصنيع طلبك {order_number}. التسليم المتوقع: {delivery_date}',
            'en': 'Your order {order_number} production has started. Expected delivery: {delivery_date}',
            'whatsapp': True,
            'sms': False,
            'category': 'production'
        },
        'production_completed': {
            'ar': 'تم الانتهاء من تصنيع طلبك {order_number}. سيصل خلال 24 ساعة',
            'en': 'Your order {order_number} production is completed. Will arrive within 24 hours',
            'whatsapp': True,
            'sms': True,
            'category': 'production'
        },
        'payment_reminder': {
            'ar': 'تذكير: قسط بقيمة {amount} ج.م مستحق في {due_date}',
            'en': 'Reminder: Installment of {amount} EGP is due on {due_date}',
            'whatsapp': True,
            'sms': True,
            'category': 'payments'
        },
        'payment_received': {
            'ar': 'تم استلام دفعة {amount} ج.م. المتبقي: {remaining} ج.م. شكراً',
            'en': 'Payment of {amount} EGP received. Remaining: {remaining} EGP. Thank you!',
            'whatsapp': True,
            'sms': True,
            'category': 'payments'
        },
        'warranty_reminder': {
            'ar': 'الضمان على منتج {product} ينتهي في {days} يوم. للتجديد تواصل معنا',
            'en': 'Warranty on {product} expires in {days} days. Contact us to renew',
            'whatsapp': True,
            'sms': False,
            'category': 'warranty'
        },
        'feedback_request': {
            'ar': 'نأمل أن تكون راضي عن منتجنا. شاركنا رأيك: {feedback_url}',
            'en': 'We hope you are satisfied with our product. Share your feedback: {feedback_url}',
            'whatsapp': True,
            'sms': False,
            'category': 'feedback'
        }
    }
    
    @classmethod
    def get_template(cls, template_name: str, language: str = 'ar') -> Optional[str]:
        """الحصول على قالب رسالة"""
        template = cls.TEMPLATES.get(template_name)
        if not template:
            return None
        return template.get(language)
    
    @classmethod
    def format_message(cls, template_name: str, context: Dict[str, Any], 
                      language: str = 'ar') -> Optional[str]:
        """تنسيق رسالة من قالب"""
        template = cls.get_template(template_name, language)
        if not template:
            return None
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.error(f"Missing key in message template {template_name}: {e}")
            return None


class AutoMessagingService:
    """خدمة إرسال الرسائل التلقائية"""
    
    @staticmethod
    def is_enabled(channel: str = 'all') -> bool:
        """التحقق من تفعيل الرسائل"""
        messaging_settings = getattr(settings, 'AUTO_MESSAGING_SETTINGS', {})
        
        if channel == 'all':
            return messaging_settings.get('ENABLED', False)
        elif channel == 'sms':
            return messaging_settings.get('SMS_ENABLED', False)
        elif channel == 'whatsapp':
            return messaging_settings.get('WHATSAPP_ENABLED', False)
        
        return False
    
    @staticmethod
    def send_message(phone: str, message: str, channel: str = 'whatsapp',
                    category: str = 'general', metadata: Dict = None) -> Dict[str, Any]:
        """
        إرسال رسالة واحدة
        
        Args:
            phone: رقم الهاتف
            message: نص الرسالة
            channel: القناة (sms, whatsapp)
            category: التصنيف
            metadata: بيانات إضافية
            
        Returns:
            dict: {success: bool, message_id: str, error: str}
        """
        if not phone:
            return {'success': False, 'error': 'No phone number provided'}
        
        if not AutoMessagingService.is_enabled(channel):
            return {'success': False, 'error': f'{channel} is disabled'}
        
        try:
            if channel == 'sms':
                return AutoMessagingService._send_sms(phone, message, metadata)
            elif channel == 'whatsapp':
                return AutoMessagingService._send_whatsapp(phone, message, metadata)
            else:
                return {'success': False, 'error': f'Unknown channel: {channel}'}
        
        except Exception as e:
            logger.error(f"Error sending {channel} message to {phone}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_sms(phone: str, message: str, metadata: Dict = None) -> Dict[str, Any]:
        """إرسال SMS (تكامل مع Twilio أو أي مزود)"""
        messaging_settings = getattr(settings, 'AUTO_MESSAGING_SETTINGS', {})
        
        provider = messaging_settings.get('SMS_PROVIDER', 'twilio')
        
        if provider == 'twilio':
            return AutoMessagingService._send_via_twilio_sms(phone, message)
        else:
            logger.warning(f"SMS provider {provider} not implemented")
            return {'success': False, 'error': 'SMS provider not configured'}
    
    @staticmethod
    def _send_whatsapp(phone: str, message: str, metadata: Dict = None) -> Dict[str, Any]:
        """إرسال WhatsApp (تكامل مع Twilio WhatsApp أو أي مزود)"""
        messaging_settings = getattr(settings, 'AUTO_MESSAGING_SETTINGS', {})
        
        provider = messaging_settings.get('WHATSAPP_PROVIDER', 'twilio')
        
        if provider == 'twilio':
            return AutoMessagingService._send_via_twilio_whatsapp(phone, message)
        else:
            logger.warning(f"WhatsApp provider {provider} not implemented")
            return {'success': False, 'error': 'WhatsApp provider not configured'}
    
    @staticmethod
    def _send_via_twilio_sms(phone: str, message: str) -> Dict[str, Any]:
        """إرسال SMS عبر Twilio"""
        try:
            from twilio.rest import Client
            
            messaging_settings = getattr(settings, 'AUTO_MESSAGING_SETTINGS', {})
            account_sid = messaging_settings.get('TWILIO_ACCOUNT_SID')
            auth_token = messaging_settings.get('TWILIO_AUTH_TOKEN')
            from_number = messaging_settings.get('TWILIO_PHONE_NUMBER')
            
            if not all([account_sid, auth_token, from_number]):
                return {'success': False, 'error': 'Twilio credentials not configured'}
            
            client = Client(account_sid, auth_token)
            
            # تنسيق الرقم (إضافة +2 لمصر إذا لزم)
            if not phone.startswith('+'):
                phone = f'+2{phone}'
            
            sms = client.messages.create(
                to=phone,
                from_=from_number,
                body=message
            )
            
            return {
                'success': True,
                'message_id': sms.sid,
                'status': sms.status
            }
        
        except ImportError:
            logger.error("Twilio library not installed. Install: pip install twilio")
            return {'success': False, 'error': 'Twilio library not installed'}
        
        except Exception as e:
            logger.error(f"Twilio SMS error: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_via_twilio_whatsapp(phone: str, message: str) -> Dict[str, Any]:
        """إرسال WhatsApp عبر Twilio"""
        try:
            from twilio.rest import Client
            
            messaging_settings = getattr(settings, 'AUTO_MESSAGING_SETTINGS', {})
            account_sid = messaging_settings.get('TWILIO_ACCOUNT_SID')
            auth_token = messaging_settings.get('TWILIO_AUTH_TOKEN')
            from_number = messaging_settings.get('TWILIO_WHATSAPP_NUMBER')
            
            if not all([account_sid, auth_token, from_number]):
                return {'success': False, 'error': 'Twilio WhatsApp not configured'}
            
            client = Client(account_sid, auth_token)
            
            # تنسيق الرقم
            if not phone.startswith('+'):
                phone = f'+2{phone}'
            
            # Twilio WhatsApp يتطلب بادئة whatsapp:
            wa_message = client.messages.create(
                to=f'whatsapp:{phone}',
                from_=f'whatsapp:{from_number}',
                body=message
            )
            
            return {
                'success': True,
                'message_id': wa_message.sid,
                'status': wa_message.status
            }
        
        except ImportError:
            logger.error("Twilio library not installed")
            return {'success': False, 'error': 'Twilio library not installed'}
        
        except Exception as e:
            logger.error(f"Twilio WhatsApp error: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    # ===== دوال مساعدة لسيناريوهات محددة =====
    
    @staticmethod
    def send_order_confirmation(pos_order) -> Dict[str, Any]:
        """إرسال تأكيد طلب POS"""
        if not pos_order.customer or not pos_order.customer.phone:
            return {'success': False, 'error': 'No customer phone'}
        
        message = MessageTemplates.format_message(
            'order_confirmed',
            {
                'customer_name': pos_order.customer.name,
                'order_number': pos_order.number,
                'total': float(pos_order.total)
            }
        )
        
        if not message:
            return {'success': False, 'error': 'Template error'}
        
        # محاولة WhatsApp أولاً، ثم SMS
        result = AutoMessagingService.send_message(
            pos_order.customer.phone,
            message,
            channel='whatsapp',
            category='orders'
        )
        
        if not result['success']:
            # محاولة SMS
            result = AutoMessagingService.send_message(
                pos_order.customer.phone,
                message,
                channel='sms',
                category='orders'
            )
        
        return result
    
    @staticmethod
    def send_production_ready(production_order) -> List[Dict[str, Any]]:
        """إرسال إشعار جاهزية الإنتاج للعملاء المرتبطين"""
        results = []
        
        # البحث عن طلبات POS المرتبطة
        # (يحتاج إضافة حقل reference في ProductionOrder)
        
        # مؤقتاً: لوج فقط
        logger.info(f"Production order {production_order.number} completed - notifications disabled")
        
        return results
    
    @staticmethod
    def send_payment_reminder(installment) -> Dict[str, Any]:
        """إرسال تذكير دفعة قسط"""
        if not installment.contract.customer or not installment.contract.customer.phone:
            return {'success': False, 'error': 'No customer phone'}
        
        message = MessageTemplates.format_message(
            'payment_reminder',
            {
                'amount': float(installment.amount),
                'due_date': installment.due_date.strftime('%Y-%m-%d')
            }
        )
        
        if not message:
            return {'success': False, 'error': 'Template error'}
        
        return AutoMessagingService.send_message(
            installment.contract.customer.phone,
            message,
            channel='whatsapp',
            category='payments'
        )
