from django.urls import path, include
from django.views.generic import RedirectView

from rest_framework.routers import DefaultRouter
from . import views, web_views

router = DefaultRouter()
router.register(r'conversations', views.WhatsAppConversationViewSet, basename='whatsapp-conversation')
router.register(r'products-knowledge', views.ProductKnowledgeViewSet, basename='product-knowledge')
router.register(r'social-conversations', views.SocialConversationViewSet, basename='social-conversation')

app_name = 'whatsapp_ai'

urlpatterns = [
    # ===== Web UI Pages (خارج Admin) =====
    path('', RedirectView.as_view(url='dashboard/'), name='home_redirect'),
    path('dashboard/', web_views.social_dashboard, name='dashboard'),


    path('conversations/', web_views.conversations_list, name='conversations_list'),
    path('conversations/<int:conversation_id>/', web_views.conversation_detail, name='conversation_detail'),
    path('conversations/<int:conversation_id>/convert/', web_views.convert_to_customer, name='convert_to_customer'),
    path('customers/', web_views.customers_list, name='customers_list'),
    path('customers/<int:customer_id>/', web_views.customer_detail, name='customer_detail'),
    path('opportunities/', web_views.opportunities_list, name='opportunities_list'),
    path('opportunities/<int:opportunity_id>/', web_views.opportunity_detail, name='opportunity_detail'),
    path('settings/', web_views.platform_settings, name='platform_settings'),
    path('products/', web_views.products_knowledge, name='products_knowledge'),
    path('products/<int:product_id>/', web_views.product_detail, name='product_detail'),
    path('products/<int:product_id>/edit/', web_views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', web_views.product_delete, name='product_delete'),
    path('products/<int:product_id>/toggle/', web_views.product_toggle, name='product_toggle'),
    path('categories/', web_views.categories_manage, name='categories_manage'),
    path('categories/exclude/', web_views.category_exclude, name='category_exclude'),
    path('categories/include/<int:excluded_id>/', web_views.category_include, name='category_include'),
    path('categories/<str:category_name>/delete-all/', web_views.category_delete_all, name='category_delete_all'),
    path('analytics/', web_views.analytics, name='analytics'),
    
    # ===== API Router URLs =====
    path('api/', include(router.urls)),
    
    # ===== Unified Webhook for All Platforms =====
    # WhatsApp: /api/whatsapp-ai/webhook/whatsapp/
    # Facebook: /api/whatsapp-ai/webhook/facebook/
    # Instagram: /api/whatsapp-ai/webhook/instagram/
    path('webhook/<str:platform>/', views.unified_webhook, name='unified-webhook'),
    
    # Callback from n8n (unified)
    path('callback/social/', views.social_callback, name='social-callback'),
    
    # AI Context for each platform
    path('ai/context/', views.ai_context, name='ai-context'),
    path('ai/context/<str:platform>/', views.social_ai_context, name='social-ai-context'),
    
    # Sync Products
    path('sync/products/', views.sync_products, name='sync-products'),
    
    # ===== Legacy Endpoints (for compatibility) =====
    path('webhook/whatsapp/', views.whatsapp_webhook, name='whatsapp-webhook'),
    path('webhook/n8n-callback/', views.n8n_callback, name='n8n-callback'),
]
