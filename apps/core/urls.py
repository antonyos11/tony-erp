"""
URLs التطبيق الأساسي — RITA ERP
"""
from django.urls import path
from . import views
from .help_views import HelpIndexView, HelpSectionView, HelpFAQView

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    # Branch Switcher
    path('switch-branch/', views.switch_branch, name='switch_branch'),
    # الفروع
    path('branches/', views.BranchListView.as_view(), name='branch_list'),
    path('branches/create/', views.BranchCreateView.as_view(), name='branch_create'),
    path('branches/<int:pk>/', views.BranchDetailView.as_view(), name='branch_detail'),
    path('branches/<int:pk>/edit/', views.BranchUpdateView.as_view(), name='branch_update'),
    # المخازن
    path('warehouses/', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('warehouses/create/', views.WarehouseCreateView.as_view(), name='warehouse_create'),
    # المستخدمون
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.DelegatedUserCreateView.as_view(), name='user_create'),
    path('users/<str:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<str:pk>/edit/', views.DelegatedUserUpdateView.as_view(), name='user_update'),
    path('users/<str:pk>/toggle/', views.UserToggleActiveView.as_view(), name='user_toggle'),
    path('users/<str:pk>/change-password/', views.AdminChangePasswordView.as_view(), name='user_change_password'),
    # البروفايل الشخصي
    path('profile/', views.MyProfileView.as_view(), name='my_profile'),
    path('profile/change-password/', views.MyChangePasswordView.as_view(), name='my_change_password'),
    # البحث الشامل
    path('search/', views.GlobalSearchView.as_view(), name='global_search'),
    # التوكيلات
    path('franchises/', views.FranchiseManagementView.as_view(), name='franchise_management'),
    # تقرير التفويضات
    path('delegations/report/', views.DelegationReportView.as_view(), name='delegation_report'),
    # إعدادات الشركة (Sprint 24)
    path('settings/', views.CompanySettingsView.as_view(), name='company_settings'),
    # معالج الإعداد الأولي (Sprint 24)
    path('setup/', views.SetupWizardView.as_view(), name='setup_wizard'),

    # ── Sprint 25: نظام المساعدة ──
    path('help/', HelpIndexView.as_view(), name='help_index'),
    path('help/faq/', HelpFAQView.as_view(), name='help_faq'),
    path('help/<str:section>/', HelpSectionView.as_view(), name='help_section'),
]
