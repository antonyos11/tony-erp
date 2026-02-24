"""
Context Processors للمتجر الإلكتروني
يوفر البيانات المشتركة لجميع صفحات المتجر
"""
import datetime
import logging
from .models import (
    EcommerceSettings, ProductCategory, SocialAuthProvider,
    Cart, Wishlist
)

logger = logging.getLogger(__name__)


def store_context(request):
    """سياق عام لجميع صفحات المتجر"""
    # التحقق من أن الطلب هو لصفحات المتجر أو الخدمات المنزلية (بما في ذلك إدارة المتجر)
    store_paths = ('/store', '/home-services', '/ecommerce')
    if not any(request.path.startswith(p) for p in store_paths):
        return {
            'store_settings': EcommerceSettings.get_settings() if ('store' in request.path or 'ecommerce' in request.path) else None,
        }
    
    try:
        settings = EcommerceSettings.get_settings()
        nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
        all_categories = ProductCategory.objects.filter(is_active=True)
        
        # مزودي تسجيل الدخول الاجتماعي النشطين
        social_providers = SocialAuthProvider.objects.filter(is_active=True).order_by('sort_order')
        
        # سلة التسوق
        cart = None
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
        elif hasattr(request, 'session') and request.session.session_key:
            session_key = request.session.session_key
            cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
        
        # قائمة الأمنيات للمستخدم
        wishlist_ids = []
        if request.user.is_authenticated:
            wishlist_ids = list(Wishlist.objects.filter(
                user=request.user
            ).values_list('product_id', flat=True))
        
        return {
            'store_settings': settings,
            'settings': settings,  # للتوافق مع القوالب القديمة
            'nav_categories': nav_categories,
            'all_categories': all_categories,
            'store_cart': cart,
            'wishlist_ids': wishlist_ids,
            'social_providers': social_providers,
            'current_year': datetime.datetime.now().year,
        }
    except Exception as e:
        logger.error(f"Error in store_context: {str(e)}", exc_info=True)
        # إرجاع سياق أدنى للحفاظ على عمل الموقع
        return {
            'store_settings': EcommerceSettings(),
            'settings': EcommerceSettings(),
            'nav_categories': [],
            'all_categories': [],
            'store_cart': None,
            'wishlist_ids': [],
            'social_providers': [],
            'current_year': datetime.datetime.now().year,
        }
