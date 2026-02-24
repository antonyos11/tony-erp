"""
E-commerce API URLs
URL routing for REST API endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .api_views import (
    ProductViewSet,
    CategoryViewSet,
    BrandViewSet,
    CartViewSet,
    OrderViewSet,
    WishlistViewSet,
    ProductReviewViewSet,
    CouponViewSet,
)

from .api_views_optimized import (
    api_products_list,
    api_categories_list,
    api_brands_list,
    api_product_search,
    api_product_detail,
    api_homepage_data,
    api_cart_get,
    api_wishlist_get,
)

from .views_push import (
    subscribe_push,
    unsubscribe_push,
    get_vapid_public_key,
    get_notification_preferences,
    update_notification_preferences,
    test_notification,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'reviews', ProductReviewViewSet, basename='review')
router.register(r'coupons', CouponViewSet, basename='coupon')

# API URL patterns
app_name = 'ecommerce_api'

urlpatterns = [
    # JWT Authentication
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Optimized cached endpoints
    path('v2/products/', api_products_list, name='products_list_v2'),
    path('v2/products/search/', api_product_search, name='product_search'),
    path('v2/products/<int:product_id>/', api_product_detail, name='product_detail_v2'),
    path('v2/categories/', api_categories_list, name='categories_list_v2'),
    path('v2/brands/', api_brands_list, name='brands_list_v2'),
    path('v2/homepage/', api_homepage_data, name='homepage_data'),
    path('v2/cart/', api_cart_get, name='cart_get_v2'),
    path('v2/wishlist/', api_wishlist_get, name='wishlist_get_v2'),
    
    # Push Notifications
    path('push/subscribe/', subscribe_push, name='push_subscribe'),
    path('push/unsubscribe/', unsubscribe_push, name='push_unsubscribe'),
    path('push/vapid-key/', get_vapid_public_key, name='vapid_key'),
    path('push/preferences/', get_notification_preferences, name='notification_preferences'),
    path('push/preferences/update/', update_notification_preferences, name='update_notification_preferences'),
    path('push/test/', test_notification, name='test_notification'),
    
    # Router URLs (legacy)
    path('', include(router.urls)),
]
