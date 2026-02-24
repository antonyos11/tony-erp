from django.urls import path
from django.shortcuts import render
from . import views
from . import permissions_matrix_views  # الواجهات المحسّنة الجديدة

app_name = 'users'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # User Management
    path('list/', views.user_list, name='list'),
    path('detail/<int:user_id>/', views.user_detail, name='detail'),
    path('edit/<int:user_id>/', views.user_edit, name='edit'),
    path('delete/<int:user_id>/', views.user_delete, name='delete'),
    path('bulk-actions/', views.bulk_actions, name='bulk_actions'),
    path('create/', views.create_user, name='create_user'),
    path('profile/', views.user_profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Activity & Security
    path('activity-log/', views.activity_log, name='activity_log'),
    path('security-alerts/', views.security_alerts, name='security_alerts'),
    path('resolve-alert/<int:alert_id>/', views.resolve_alert, name='resolve_alert'),
    
    # Session Management
    path('sessions/', views.session_management, name='sessions'),
    
    # Role Management - إدارة الأدوار
    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:pk>/', views.role_detail, name='role_detail'),
    path('roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
    
    # Permissions Management - المحسّن ⭐
    path('permissions/', permissions_matrix_views.permissions_matrix_view, name='permissions_manager'),
    path('permissions/pages/', views.page_permissions, name='page_permissions'),
    path('permissions/update-ajax/', permissions_matrix_views.update_permission_ajax, name='update_permission_ajax'),
    path('permissions/bulk-update/', permissions_matrix_views.bulk_update_permissions, name='bulk_update_permissions'),
    path('permissions/apply-template/<int:role_id>/', permissions_matrix_views.apply_role_template, name='apply_role_template'),
    path('permissions/copy/<int:from_role_id>/<int:to_role_id>/', permissions_matrix_views.copy_role_permissions, name='copy_role_permissions'),
    
    # API Endpoints
    path('api/permissions/<int:user_id>/', views.user_permissions_api, name='user_permissions_api'),
    path('api/details/<int:user_id>/', views.user_details_api, name='user_details_api'),
]
# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('logout/', stub_view, name='logout'),
]
