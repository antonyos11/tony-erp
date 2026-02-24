"""
Error Monitoring and Logging for E-commerce
=============================================
Sentry integration and custom logging
Week 4 - Final Polish
"""

import logging
import traceback
from functools import wraps
from django.conf import settings
from django.core.mail import mail_admins
from django.http import JsonResponse
from rest_framework import status


# Configure logger
logger = logging.getLogger('ecommerce')


class ErrorMonitor:
    """خدمة مراقبة الأخطاء"""
    
    def __init__(self):
        self.sentry_enabled = getattr(settings, 'SENTRY_DSN', None) is not None
    
    def capture_exception(self, exception, context=None):
        """التقاط الاستثناءات"""
        if self.sentry_enabled:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)
                sentry_sdk.capture_exception(exception)
        
        # Always log locally
        logger.exception(f"Error captured: {str(exception)}", extra=context or {})
    
    def capture_message(self, message, level='info', context=None):
        """التقاط رسائل"""
        if self.sentry_enabled:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)
                sentry_sdk.capture_message(message, level=level)
        
        log_func = getattr(logger, level, logger.info)
        log_func(message, extra=context or {})
    
    def set_user_context(self, user):
        """تعيين سياق المستخدم"""
        if self.sentry_enabled and user and user.is_authenticated:
            import sentry_sdk
            sentry_sdk.set_user({
                'id': user.id,
                'email': user.email,
                'username': user.username
            })
    
    def add_breadcrumb(self, message, category='info', data=None):
        """إضافة breadcrumb للتتبع"""
        if self.sentry_enabled:
            import sentry_sdk
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                data=data or {}
            )


# Global monitor instance
monitor = ErrorMonitor()


def log_payment_event(event_type, order, gateway, success=True, error=None):
    """تسجيل أحداث الدفع"""
    context = {
        'event_type': event_type,
        'order_number': order.order_number if order else None,
        'order_id': order.id if order else None,
        'gateway': gateway,
        'success': success,
        'user_id': order.user_id if order else None,
        'amount': str(order.total) if order else None,
    }
    
    if error:
        context['error'] = str(error)
        logger.error(f"Payment {event_type} failed: {error}", extra=context)
        monitor.capture_message(
            f"Payment {event_type} failed for order {order.order_number if order else 'unknown'}",
            level='error',
            context=context
        )
    else:
        logger.info(f"Payment {event_type} successful", extra=context)


def log_order_event(event_type, order, details=None):
    """تسجيل أحداث الطلبات"""
    context = {
        'event_type': event_type,
        'order_number': order.order_number,
        'order_id': order.id,
        'status': order.status,
        'user_id': order.user_id,
        'total': str(order.total),
    }
    
    if details:
        context.update(details)
    
    logger.info(f"Order event: {event_type}", extra=context)
    
    monitor.add_breadcrumb(
        message=f"Order {event_type}: {order.order_number}",
        category='order',
        data=context
    )


def log_webhook_event(gateway, event_type, payload, success=True, error=None):
    """تسجيل أحداث Webhooks"""
    context = {
        'gateway': gateway,
        'event_type': event_type,
        'success': success,
        'payload_size': len(str(payload)) if payload else 0,
    }
    
    if error:
        context['error'] = str(error)
        logger.error(f"Webhook {gateway} failed: {error}", extra=context)
        monitor.capture_exception(error if isinstance(error, Exception) else Exception(error), context)
    else:
        logger.info(f"Webhook {gateway} received: {event_type}", extra=context)


def log_api_error(request, exception, response_code=500):
    """تسجيل أخطاء API"""
    context = {
        'path': request.path,
        'method': request.method,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'ip_address': get_client_ip(request),
        'response_code': response_code,
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
    }
    
    logger.error(f"API Error: {str(exception)}", extra=context, exc_info=True)
    monitor.capture_exception(exception, context)


def log_security_event(event_type, request, details=None):
    """تسجيل أحداث الأمان"""
    context = {
        'event_type': event_type,
        'path': request.path,
        'method': request.method,
        'ip_address': get_client_ip(request),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'user_id': request.user.id if request.user.is_authenticated else None,
    }
    
    if details:
        context.update(details)
    
    logger.warning(f"Security event: {event_type}", extra=context)
    
    # Alert on suspicious activity
    suspicious_events = [
        'invalid_webhook_signature',
        'brute_force_attempt',
        'sql_injection_attempt',
        'unauthorized_access'
    ]
    
    if event_type in suspicious_events:
        monitor.capture_message(
            f"Suspicious activity detected: {event_type}",
            level='warning',
            context=context
        )


def get_client_ip(request):
    """الحصول على IP العميل"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def error_handler(func):
    """Decorator لمعالجة الأخطاء"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Get request from args (for views)
            request = None
            for arg in args:
                if hasattr(arg, 'path') and hasattr(arg, 'method'):
                    request = arg
                    break
            
            if request:
                log_api_error(request, e)
            else:
                monitor.capture_exception(e)
            
            raise
    
    return wrapper


class LoggingMiddleware:
    """Middleware لتسجيل الطلبات"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Set user context for Sentry
        if request.user.is_authenticated:
            monitor.set_user_context(request.user)
        
        # Process request
        response = self.get_response(request)
        
        # Log errors
        if response.status_code >= 400:
            self._log_error_response(request, response)
        
        return response
    
    def _log_error_response(self, request, response):
        """تسجيل استجابات الأخطاء"""
        if response.status_code >= 500:
            level = 'error'
        elif response.status_code >= 400:
            level = 'warning'
        else:
            return
        
        logger.log(
            logging.WARNING if level == 'warning' else logging.ERROR,
            f"{response.status_code} {request.method} {request.path}",
            extra={
                'status_code': response.status_code,
                'path': request.path,
                'method': request.method,
                'ip_address': get_client_ip(request),
                'user_id': request.user.id if request.user.is_authenticated else None,
            }
        )
    
    def process_exception(self, request, exception):
        """معالجة الاستثناءات"""
        log_api_error(request, exception)
        return None  # Let Django handle the exception


# Sentry configuration helper
def configure_sentry(dsn, environment='production'):
    """إعداد Sentry"""
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        
        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            environment=environment,
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,
            send_default_pii=False,  # Don't send PII
            
            # Filter sensitive data
            before_send=filter_sensitive_data,
        )
        
        logger.info(f"Sentry configured for environment: {environment}")
        
    except ImportError:
        logger.warning("Sentry SDK not installed. Error monitoring disabled.")


def filter_sensitive_data(event, hint):
    """تصفية البيانات الحساسة من Sentry"""
    sensitive_keys = [
        'password', 'token', 'api_key', 'secret',
        'credit_card', 'cvv', 'card_number'
    ]
    
    def filter_dict(d):
        if isinstance(d, dict):
            return {
                k: '[FILTERED]' if any(s in k.lower() for s in sensitive_keys) else filter_dict(v)
                for k, v in d.items()
            }
        elif isinstance(d, list):
            return [filter_dict(item) for item in d]
        return d
    
    if 'extra' in event:
        event['extra'] = filter_dict(event['extra'])
    
    return event


# Django logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/tony_erp/ecommerce.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/tony_erp/ecommerce_errors.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'ecommerce': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'ecommerce.payments': {
            'handlers': ['console', 'file', 'error_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'ecommerce.security': {
            'handlers': ['console', 'file', 'error_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
