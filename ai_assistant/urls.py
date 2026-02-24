from django.urls import path
from . import views
from . import api_views

app_name = 'ai_assistant'

urlpatterns = [
    # Root/index view - redirects to admin dashboard
    path('', views.admin_dashboard, name='index'),
    # New API endpoints
    path('api/chat/', api_views.api_chat, name='api_chat'),
    path('api/session/start/', api_views.api_start_session, name='api_start_session'),
    
    # Existing API endpoints
    path('api/<str:assistant_type>/chat/', views.chat_message, name='chat_message'),
    path('api/<str:assistant_type>/history/', views.get_chat_history, name='chat_history'),
    path('api/<str:assistant_type>/quick-replies/', views.get_quick_replies, name='quick_replies'),
    path('api/<str:assistant_type>/faqs/', views.get_faqs, name='faqs'),
    path('api/<str:assistant_type>/end-session/', views.end_session, name='end_session'),
    path('api/message/<str:message_id>/rate/', views.rate_message, name='rate_message'),
    
    # Admin views
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/settings/<str:assistant_type>/', views.admin_settings, name='admin_settings'),
]
