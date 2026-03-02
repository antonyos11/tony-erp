"""
URLs تطبيق الصلاحيات — RITA ERP
"""
from django.urls import path
from apps.authorization import views

app_name = 'authorization'

urlpatterns = [
    # الأدوار القديمة
    path("roles/", views.RoleListView.as_view(), name="role_list"),
    path("roles/create/", views.RoleCreateView.as_view(), name="role_create"),
    path("roles/<int:pk>/", views.RoleDetailView.as_view(), name="role_detail"),

    # تعيين الأدوار القديمة
    path("assign-role/", views.UserRoleAssignView.as_view(), name="assign_role"),

    # سجل التدقيق
    path("audit-log/", views.AuditLogView.as_view(), name="audit_log"),

    # التفويضات
    path("delegations/", views.DelegationListView.as_view(), name="delegation_list"),
    path("delegations/create/", views.DelegationCreateView.as_view(), name="delegation_create"),

    # Sprint 22A Part 2 - الادوار النظامية الجديدة
    path("system-roles/", views.SystemRoleListView.as_view(), name="system_role_list"),
    path("system-roles/<int:pk>/", views.SystemRoleDetailView.as_view(), name="system_role_detail"),
    path("assign-system-role/", views.AssignSystemRoleView.as_view(), name="assign_system_role"),
    path("revoke-system-role/<int:pk>/", views.RevokeSystemRoleView.as_view(), name="revoke_system_role"),

    # سجل الامان
    path("security-violations/", views.SecurityViolationLogView.as_view(), name="security_violations"),

    # Sprint 23 — طلبات الاعتماد
    path("approvals/", views.ApprovalListView.as_view(), name="approval_list"),
    path("approvals/my/", views.MyRequestsView.as_view(), name="my_requests"),
    path("approvals/<int:pk>/", views.ApprovalDetailView.as_view(), name="approval_detail"),
    path("approvals/<int:pk>/process/", views.ApprovalProcessView.as_view(), name="approval_process"),
]
