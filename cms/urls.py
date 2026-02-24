"""
URLs لنظام إدارة المحتوى
"""

from django.urls import path
from . import views

app_name = 'cms'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # الصفحات
    path('pages/', views.page_list, name='page_list'),
    path('pages/create/', views.page_create, name='page_create'),
    path('pages/<int:page_id>/edit/', views.page_edit, name='page_edit'),
    path('pages/<int:page_id>/delete/', views.page_delete, name='page_delete'),
    
    # الوسائط
    path('media/', views.media_library, name='media_library'),
    
    # القوائم
    path('menus/', views.menu_manager, name='menu_manager'),
    path('menus/save/', views.menu_save, name='menu_create'),
    path('menus/<int:menu_id>/save/', views.menu_save, name='menu_save'),
    
    # التصنيفات
    path('categories/', views.category_manager, name='category_manager'),
    
    # التعليقات
    path('comment/<int:page_id>/', views.add_comment, name='add_comment'),
]

# URLs العامة للصفحات
public_urlpatterns = [
    path('page/<slug:slug>/', views.page_view, name='page_view'),
]
