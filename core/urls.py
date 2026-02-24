from django.urls import path
from . import views
from . import health_views
from . import system_api
from . import diagnostic_view
from . import api_search # Import the new module
from . import code_generator_api
from .help_api import ContextualHelpAPIView, KeyboardShortcutsAPIView, HelpSearchAPIView, HelpTooltipsAPIView
from .views_sidebar import sidebar_badges_api

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('offline/', views.offline_page, name='offline'),  # PWA offline page
    path('debug-sidebar/', views.debug_sidebar_links, name='debug_sidebar_links'),  # Debug page
    # تم تعطيل مسارات تبديل الواجهة لمنع الرجوع للواجهة القديمة
    path('server-qr/', views.server_qr, name='server_qr'),
    path('network-diagnose/', views.network_diagnose, name='network_diagnose'),
    path('company/', views.company_settings, name='company_settings'),
    path('company/factory-reset/', views.factory_reset, name='factory_reset'),
    path('logout/', views.logout_view, name='logout'),
    path('switch-account/', views.switch_account, name='switch_account'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),

    # صفحة التشخيص
    path('diagnostic/', diagnostic_view.diagnostic_page, name='diagnostic'),

    # صفحة "قريباً" للميزات التي لم تُبنى بعد
    path('coming-soon/', views.coming_soon, name='coming_soon'),
    path('coming-soon/<str:feature>/', views.coming_soon, name='coming_soon_feature'),
    
    # API النظام - شريط الأدوات والصيانة
    path('api/system/clear-cache/', system_api.clear_cache, name='api_clear_cache'),
    path('api/system/backup/', system_api.create_backup, name='api_create_backup'),
    path('api/system/download-backup/<str:filename>/', system_api.download_backup, name='api_download_backup'),
    path('api/system/maintenance/', system_api.maintenance_action, name='api_maintenance'),
    path('api/notifications/recent/', system_api.recent_notifications, name='api_recent_notifications'),
    path('api/dashboard/daily-profit/', system_api.daily_profit_summary, name='api_daily_profit'),
    path('api/dashboard/hr-attendance/', views.get_hr_attendance_data, name='api_hr_attendance'),
    path('api/dashboard/periodic-updates/', system_api.periodic_updates_status, name='api_periodic_updates_status'),
    path('api/dashboard/run-updates/', system_api.run_periodic_updates, name='api_run_updates'),
    path('api/dashboard/run-updates/', system_api.run_periodic_updates, name='api_run_updates'),
    path('api/reports/profit-by-category/', system_api.profit_by_category, name='api_profit_by_category'),
    
    # Global Search API
    path('api/global-search/', api_search.global_search, name='global_search'),
    
    # Sidebar v3 Badge API
    path('api/sidebar-badges/', sidebar_badges_api, name='sidebar_badges_api'),
    
    # API توليد الأكواد التلقائية
    path('api/generate-code/', code_generator_api.generate_code, name='api_generate_code'),
    path('api/generate-code/models/', code_generator_api.get_available_models, name='api_generate_code_models'),
    
    # إدارة العملات
    path('currencies/', views.currency_settings, name='currency_settings'),
    path('currencies/add/', views.currency_add, name='currency_add'),
    path('currencies/<int:currency_id>/edit/', views.currency_edit, name='currency_edit'),
    path('currencies/<int:currency_id>/delete/', views.currency_delete, name='currency_delete'),
    path('currencies/<int:currency_id>/set-default/', views.currency_set_default, name='currency_set_default'),
    path('currencies/exchange-rates/', views.currency_exchange_rates, name='currency_exchange_rates'),
    
    # إدارة الفروع
    path('branches/', views.branch_list, name='branch_list'),
    path('branches/create/', views.branch_create, name='branch_create'),
    path('branches/<int:pk>/edit/', views.branch_edit, name='branch_edit'),
    path('branches/<int:pk>/delete/', views.branch_delete, name='branch_delete'),
    
    # إدارة الدول
    path('countries/', views.country_list, name='country_list'),
    path('countries/create/', views.country_create, name='country_create'),
    path('countries/<int:pk>/edit/', views.country_edit, name='country_edit'),
    path('countries/<int:pk>/delete/', views.country_delete, name='country_delete'),
    path('countries/<int:country_id>/states/', views.states_by_country, name='states_by_country'),
    
    # إدارة المحافظات
    path('states/', views.state_list, name='state_list'),
    path('states/create/', views.state_create, name='state_create'),
    path('states/<int:pk>/edit/', views.state_edit, name='state_edit'),
    path('states/<int:pk>/delete/', views.state_delete, name='state_delete'),
    
    # إدارة الصفحات
    path('pages/', views.page_list, name='page_list'),
    path('pages/create/', views.page_create, name='page_create'),
    path('pages/<int:pk>/edit/', views.page_edit, name='page_edit'),
    path('pages/<int:pk>/delete/', views.page_delete, name='page_delete'),
    
    # لوحات التحكم الموحدة (Enterprise)
    path('unified-dashboard/', views.unified_dashboard, name='unified_dashboard'),
    path('mrp-dashboard/', views.mrp_dashboard, name='mrp_dashboard'),
    path('costing-dashboard/', views.costing_dashboard, name='costing_dashboard'),
    path('distribution-dashboard/', views.distribution_dashboard, name='distribution_dashboard'),
    path('integration-dashboard/', views.integration_dashboard, name='integration_dashboard'),
    
    # Health Check endpoints - مُفعّلة
    path('health/live/', health_views.health_live, name='health_live'),
    path('health/ready/', health_views.health_ready, name='health_ready'),
    path('status/', health_views.system_status, name='system_status'),
    
    # API المساعدة السياقية
    path('api/help/', ContextualHelpAPIView.as_view(), name='api_help'),
    path('api/keyboard-shortcuts/', KeyboardShortcutsAPIView.as_view(), name='api_keyboard_shortcuts'),
    path('api/help/search/', HelpSearchAPIView.as_view(), name='api_help_search'),
    path('api/help/tooltips/', HelpTooltipsAPIView.as_view(), name='api_help_tooltips'),
    
    # صفحات التحسينات الجديدة
    path('enhanced-dashboard/', views.enhanced_dashboard, name='enhanced_dashboard'),
    path('shortcuts/', views.keyboard_shortcuts, name='keyboard_shortcuts'),
    path('help/', views.help_page, name='help'),
    path('settings/improvements/', views.improvements_settings, name='improvements_settings'),
]
