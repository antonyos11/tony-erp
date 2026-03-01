"""
URLs تطبيق الصلاحيات — RITA ERP
"""
from django.urls import path
from apps.authorization import views

app_name = 'authorization'

urlpatterns = [
    # الأدوار
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/create/', views.RoleCreateView.as_view(), name='role_create'),
    path('roles/<int:pk>/', views.RoleDetailView.as_view(), name='role_detail'),

    # تعيين الأدوار
    path('assign-role/', views.UserRoleAssignView.as_view(), name='assign_role'),

    # سجل التدقيق
    path('audit-log/', views.AuditLogView.as_view(), name='audit_log'),

    # التفويضات
    path('delegations/', views.DelegationListView.as_view(), name='delegation_list'),
    path('delegations/create/', views.DelegationCreateView.as_view(), name='delegation_create'),
]
