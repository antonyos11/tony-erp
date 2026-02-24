from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'whatsapp_integration'

router = DefaultRouter()
router.register(r'conversations', views.WhatsAppConversationViewSet)
router.register(r'templates', views.WhatsAppTemplateViewSet)
router.register(r'auto-replies', views.AutoReplyRuleViewSet)

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('conversation/<int:pk>/', views.conversation_detail, name='conversation_detail'),
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # n8n Integration Endpoints
    path('api/n8n/incoming/', views.n8n_incoming_message, name='n8n_incoming'),
    path('api/n8n/products/search/', views.n8n_search_products, name='n8n_products_search'),
    path('api/n8n/products/catalog/', views.n8n_get_products_catalog, name='n8n_catalog'),
    path('api/n8n/customer/register/', views.n8n_register_customer, name='n8n_register_customer'),
    path('api/n8n/customer/<str:phone>/', views.n8n_get_customer, name='n8n_get_customer'),
    path('api/n8n/conversation/log/', views.n8n_log_conversation, name='n8n_log_conversation'),
    
    # WhatsApp Webhook
    path('webhook/', views.whatsapp_webhook, name='webhook'),
]
