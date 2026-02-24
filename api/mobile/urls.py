"""
Mobile API URLs
مسارات API الموبايل

ربط جميع endpoints الموبايل
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .mobile import auth, dashboard, pos, inventory, production

# إنشاء Router
router = DefaultRouter()

# تسجيل ViewSets
router.register(r'auth', auth.MobileAuthViewSet, basename='mobile-auth')
router.register(r'dashboard', dashboard.MobileDashboardViewSet, basename='mobile-dashboard')
router.register(r'pos', pos.MobilePOSViewSet, basename='mobile-pos')
router.register(r'inventory', inventory.MobileInventoryViewSet, basename='mobile-inventory')
router.register(r'production', production.MobileProductionViewSet, basename='mobile-production')

app_name = 'mobile_api'

urlpatterns = [
    path('', include(router.urls)),
]
