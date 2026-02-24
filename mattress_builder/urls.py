"""
URLs لنظام بناء المراتب المخصصة
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'mattress_builder'

# Router for API endpoints
router = DefaultRouter()
router.register(r'sizes', views.MattressSizeViewSet, basename='size')
router.register(r'categories', views.MattressComponentCategoryViewSet, basename='category')
router.register(r'components', views.MattressComponentViewSet, basename='component')
router.register(r'templates', views.MattressTemplateViewSet, basename='template')
router.register(r'designs', views.CustomMattressDesignViewSet, basename='design')
router.register(r'feelings', views.MattressFeelingTypeViewSet, basename='feeling')
router.register(r'ai-recommendations', views.AIRecommendationViewSet, basename='ai-recommendation')
router.register(r'orders', views.MattressOrderViewSet, basename='mattress-order')
router.register(r'community', views.CommunityDesignViewSet, basename='community-design')
router.register(r'commissions', views.DesignerCommissionViewSet, basename='commission')

urlpatterns = [
    # API Endpoints
    path('api/', include(router.urls)),
    
    # Frontend Pages - Builder
    path('', views.builder_home, name='home'),
    path('builder/', views.builder_page, name='builder'),
    
    # تصميماتي
    path('my-designs/', views.my_designs, name='my_designs'),
    path('design/<int:design_id>/', views.design_detail, name='design_detail'),
    
    # تصميمات المجتمع
    path('community/', views.community_designs, name='community_designs'),
    path('community/<int:design_id>/', views.community_design_detail, name='community_design_detail'),
    
    # الطلبات والدفع
    path('checkout/<int:design_id>/', views.checkout_design, name='checkout_design'),
    path('place-order/<int:design_id>/', views.place_mattress_order, name='place_mattress_order'),
    path('orders/', views.my_orders, name='my_orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # العمولات
    path('my-commissions/', views.my_commissions, name='my_commissions'),
]
