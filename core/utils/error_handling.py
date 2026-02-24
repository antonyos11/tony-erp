"""
أدوات معالجة الأخطاء المحسّنة
Error Handling Utilities - Tony ERB
"""

import logging
import functools
from typing import Any, Callable, Optional, TypeVar, Union
from django.http import JsonResponse
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default: Optional[T] = None,
    log_error: bool = True,
    error_message: str = "",
    **kwargs: Any
) -> Optional[T]:
    """
    تنفيذ آمن لدالة مع معالجة الأخطاء وتسجيلها.
    
    Args:
        func: الدالة المراد تنفيذها
        *args: المعاملات الموضعية
        default: القيمة الافتراضية عند حدوث خطأ
        log_error: تسجيل الخطأ في اللوق
        error_message: رسالة خطأ مخصصة
        **kwargs: المعاملات المُسماة
    
    Returns:
        نتيجة الدالة أو القيمة الافتراضية
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            msg = error_message or f"خطأ في تنفيذ {func.__name__}"
            logger.warning(f"{msg}: {e}", exc_info=True)
        return default


def safe_decimal_convert(value: Any, default: Any = 0) -> Any:
    """
    تحويل آمن للقيم العشرية.
    
    Args:
        value: القيمة المراد تحويلها
        default: القيمة الافتراضية
    
    Returns:
        القيمة المحوّلة أو الافتراضية
    """
    from decimal import Decimal, InvalidOperation
    
    if value is None:
        return Decimal(str(default))
    
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.debug(f"فشل تحويل القيمة {value} إلى Decimal: {e}")
        return Decimal(str(default))


def handle_view_exception(view_func: Callable) -> Callable:
    """
    Decorator لمعالجة الاستثناءات في Views.
    يسجل الأخطاء ويعيد استجابة مناسبة.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(
                f"خطأ في {view_func.__name__}: {e}",
                exc_info=True,
                extra={
                    'request_path': request.path,
                    'user': getattr(request, 'user', None),
                }
            )
            # إذا كان الطلب AJAX، إرجاع JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': _('حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.')
                }, status=500)
            # إعادة رفع الاستثناء للـ Django error handler
            raise
    return wrapper


def handle_api_exception(view_func: Callable) -> Callable:
    """
    Decorator لمعالجة الاستثناءات في API Views.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except ValueError as e:
            logger.warning(f"خطأ في المدخلات - {view_func.__name__}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }, status=400)
        except PermissionError as e:
            logger.warning(f"خطأ في الصلاحيات - {view_func.__name__}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'permission_denied',
                'message': _('ليس لديك صلاحية للقيام بهذا الإجراء')
            }, status=403)
        except Exception as e:
            logger.error(
                f"خطأ في API {view_func.__name__}: {e}",
                exc_info=True
            )
            return JsonResponse({
                'success': False,
                'error': 'server_error',
                'message': _('حدث خطأ في الخادم')
            }, status=500)
    return wrapper


class SilentLogger:
    """
    فئة لتسجيل الأخطاء بصمت بدون رفع استثناءات.
    مفيدة للعمليات غير الحرجة.
    """
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
    
    def log_and_ignore(
        self,
        func: Callable[..., T],
        *args: Any,
        level: int = logging.WARNING,
        message: str = "",
        **kwargs: Any
    ) -> Optional[T]:
        """
        تنفيذ دالة وتسجيل أي خطأ بدون رفعه.
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.logger.log(
                level,
                message or f"خطأ في {func.__name__}: {e}",
                exc_info=(level >= logging.ERROR)
            )
            return None


# نسخة جاهزة للاستخدام
silent_logger = SilentLogger('tony_erb.silent')


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 0.1,
    exceptions: tuple = (Exception,),
    on_failure: Optional[Callable] = None
) -> Callable:
    """
    Decorator لإعادة المحاولة عند الفشل.
    
    Args:
        max_retries: عدد المحاولات الأقصى
        delay: التأخير بين المحاولات (ثواني)
        exceptions: أنواع الاستثناءات للتعامل معها
        on_failure: دالة تُستدعى عند فشل كل المحاولات
    """
    import time
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(
                            f"محاولة {attempt + 1}/{max_retries} فشلت لـ {func.__name__}: {e}"
                        )
                        time.sleep(delay * (attempt + 1))  # تأخير متزايد
            
            logger.warning(
                f"فشلت كل المحاولات ({max_retries}) لـ {func.__name__}: {last_exception}"
            )
            if on_failure:
                return on_failure(last_exception)
            raise last_exception
        return wrapper
    return decorator
