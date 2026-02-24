"""
URL Configuration for Accounts App (Two-Factor Authentication)
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
        # Authentication
        path('login/', views.custom_login, name='login'),
        path('verify-2fa/', views.verify_2fa, name='verify_2fa'),

        # Password Reset
        path('password-reset/', auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url='/accounts/password-reset/done/',
        ), name='password_reset'),
        path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ), name='password_reset_done'),
        path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/accounts/password-reset-complete/',
        ), name='password_reset_confirm'),
        path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ), name='password_reset_complete'),
	path('2fa/disable/', views.disable_2fa, name='disable_2fa'),
	path('2fa/setup/', views.setup_2fa, name='setup_2fa'),
	path('2fa/manage/', views.manage_2fa, name='manage_2fa'),
	path('2fa/regenerate-backup-codes/', views.regenerate_backup_codes, name='regenerate_backup_codes'),
	
	# OTP
	path('2fa/send-email-otp/', views.send_email_otp, name='send_email_otp'),
	
	# History
	path('login-history/', views.login_history, name='login_history'),
	
	# AJAX APIs
	path('api/2fa/status/', views.check_2fa_status, name='check_2fa_status'),
	path('api/2fa/verify-totp/', views.verify_totp_ajax, name='verify_totp_ajax'),
]

# --- Advanced Permissions & Workflow URLs ---
from accounts import views_advanced as adv_views  # noqa: E402

urlpatterns += [
    # Dashboard
    path('permissions/', adv_views.permissions_dashboard, name='permissions_dashboard'),

    # Branch Permissions
    path('permissions/list/', adv_views.permission_list, name='permission_list'),
    path('permissions/create/', adv_views.permission_create, name='permission_create'),
    path('permissions/<int:pk>/edit/', adv_views.permission_edit, name='permission_edit'),
    path('permissions/<int:pk>/delete/', adv_views.permission_delete, name='permission_delete'),

    # Data Access Rules
    path('access-rules/', adv_views.access_rule_list, name='access_rule_list'),
    path('access-rules/create/', adv_views.access_rule_create, name='access_rule_create'),
    path('access-rules/<int:pk>/edit/', adv_views.access_rule_edit, name='access_rule_edit'),
    path('access-rules/<int:pk>/delete/', adv_views.access_rule_delete, name='access_rule_delete'),

    # Security Policy
    path('security-policy/', adv_views.security_policy, name='security_policy'),

    # Approval Workflows
    path('workflows/', adv_views.workflow_list, name='workflow_list'),
    path('workflows/create/', adv_views.workflow_create, name='workflow_create'),
    path('workflows/<int:pk>/', adv_views.workflow_detail, name='workflow_detail'),
    path('workflows/<int:pk>/edit/', adv_views.workflow_edit, name='workflow_edit'),

    # Approval Requests
    path('approvals/', adv_views.approval_list, name='approval_list'),
    path('approvals/my/', adv_views.my_approvals, name='my_approvals'),
    path('approvals/<int:pk>/', adv_views.approval_detail, name='approval_detail'),
    path('approvals/<int:pk>/action/', adv_views.approval_action, name='approval_action'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('resend-2fa/', stub_view, name='resend_2fa'),
]
