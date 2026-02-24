"""
Tony ERP - تكوين المسارات الرئيسية
نظام إدارة الأعمال الشامل
الواجهة العامة: المتجر الإلكتروني
الواجهة الإدارية: /dashboard/ أو /admin/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import RedirectView
from core.views import logout_view, login_view, audit_logs
from core.health_views import health_live, health_ready, health_detailed
from core import system_api
from core import diagnostic_view
from core.help_api import HelpTooltipsAPIView
from django.shortcuts import render

try:  # توثيق API اختياري، لا يكسر المشروع إذا الحزمة غير مثبّتة
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )
    _SPECTACULAR_AVAILABLE = True
except Exception:  # pragma: no cover - اختياري بالكامل
    _SPECTACULAR_AVAILABLE = False

# JWT Authentication endpoints
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


# توجيه الصفحة الرئيسية للمتجر
def homepage_redirect(request):
    """توجيه الصفحة الرئيسية للمتجر للزوار أو للوحة التحكم للموظفين"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('core:dashboard')
    return redirect('ecommerce:store_home')


urlpatterns = [
    # الصفحة الرئيسية -> المتجر للزوار / لوحة التحكم للموظفين
    path('', homepage_redirect, name='home'),
    
    # المتجر الإلكتروني - الواجهة العامة (للزوار والعملاء)
    path('store/', include(('ecommerce.urls', 'ecommerce'), namespace='ecommerce')),
    
    # إعادة توجيه المسارات القديمة للمتجر
    path('ecommerce/', include(('ecommerce.urls', 'ecommerce_legacy'), namespace='ecommerce_legacy')),
    
    # الإدارة والتوثيق
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    
    # فحص صحة النظام (بدون مصادقة)
    path('health/', health_ready, name='health_check'),
    path('health/live/', health_live, name='health_live'),
    path('health/ready/', health_ready, name='health_ready'),
    path('health/detailed/', health_detailed, name='health_detailed'),

    # Heartbeat - حالة الاتصال (لحل مشكلة "غير متصل")
    path('heartbeat/', __import__('core.fixes.heartbeat', fromlist=['heartbeat']).heartbeat, name='heartbeat'),
    path('api/', include('core.fixes.urls')),

    # صفحة التشخيص
    path('diagnostic/', diagnostic_view.diagnostic_page, name='diagnostic'),
    
    # Prometheus Metrics (للمراقبة) - يتم تفعيله تلقائياً إذا كانت الحزمة مثبتة
    
    # API النظام - النسخ الاحتياطي
    path('api/system/download-backup/<str:filename>/', system_api.download_backup, name='api_download_backup'),
    path('api/system/backup/', system_api.create_backup, name='api_create_backup'),
    path('api/system/clear-cache/', system_api.clear_cache, name='api_clear_cache'),
    
    # JWT Authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API help tooltips - root level for contextual_help.js
    path('api/help/tooltips/', HelpTooltipsAPIView.as_view(), name='api_help_tooltips_root'),
    path('api/core/', include(('core.api_urls', 'core-api'), namespace='core-api')),
    path('api/', include('api_app.urls')),
    path('api/fleet/', include('fleet.api_urls')),
    path('api/shipping/', include('shipping.api_urls')),
    path('api/quality-control/', include('quality_control.api_urls')),
    path('api/ecommerce/', include('ecommerce.api_urls')),

    # سجلات التدقيق - متاحة مباشرة للمسار القصير المستخدم في الاختبارات
    path('audit-logs/', audit_logs, name='audit_logs_root'),
    
    # مساعدة الوحدات
    path('help/accounting/', lambda request: __import__('accounting.views', fromlist=['accounting_help']).accounting_help(request), name='accounting_help'),
    
    # التطبيقات الأساسية - نظام الإدارة (للموظفين)
    path('dashboard/', include('core.urls')),
    path('core/', include(('core.urls', 'core_legacy'), namespace='core_legacy')),  # للتوافق مع الروابط القديمة
    path('users/', include('users.urls')),
    path('accounting/', include('accounting.urls')),
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('purchases/', include('purchases.urls')),
    path('production/', include(('production.urls', 'production'), namespace='production')),
    path('hr/', include('hr.urls')),
    path('crm/', include('crm.urls')),
    path('advanced-crm/', include(('advanced_crm.urls', 'advanced_crm'), namespace='advanced_crm')),
    
    # Redirects for new apps root paths
    path('intellectual-property/', RedirectView.as_view(url='dashboard/')),
    path('contract-management/', RedirectView.as_view(url='dashboard/')),
    path('risk-management/', RedirectView.as_view(url='dashboard/')),
    path('treasury-management/', RedirectView.as_view(url='dashboard/')),
    
    path('correspondence-management/', include(('correspondence_management.urls', 'correspondence_management'), namespace='correspondence_management')),
    path('intellectual-property/', include(('intellectual_property.urls', 'intellectual_property'), namespace='intellectual_property')),
    path('contract-management/', include(('contract_management.urls', 'contract_management'), namespace='contract_management')),
    path('risk-management/', include(('risk_management.urls', 'risk_management'), namespace='risk_management')),
    path('treasury-management/', include(('treasury_management.urls', 'treasury_management'), namespace='treasury_management')),
    path('maintenance/', include('maintenance.urls')),
    path('reports/', include('reports.urls')),
    path('fleet/', include('fleet.urls')),
    path('pos/', include('pos.urls')),
    path('showrooms/', include('showrooms.urls_pages')),  # legacy routes
    path('approvals/', include(('approvals.urls', 'approvals'), namespace='approvals')),
    path('notifications/', include(('notifications.urls', 'notifications'), namespace='notifications')),
    path('advanced-notifications/', include(('advanced_notifications.urls', 'advanced_notifications'), namespace='advanced_notifications')),
    path('woocommerce/', include('woocommerce_integration.urls')),
    # المتجر الإلكتروني (تم نقله لـ /store/)
    path('fixed-assets/', include('fixed_assets.urls')),
    path('contracting/', include('contracting.urls')),
    path('shipping/', include('shipping.urls')),
    path('eservices/', include('eservices.urls')),
    path('projects/', include('projects.urls')),
    path('home-services/', include('home_services.urls')),  # خدمات الصيانة والنظافة
    
    # نظام الوصول السريع
    path('quick/', include('quick_access.urls')),
    
    # موصول التحضير والاستماد
    path('mosool/', include(('core.mosool.urls', 'mosool'), namespace='mosool')),
    
    # الاستيراد والتصدير
    path('trade/', include(('core.import_export.urls', 'import_export'), namespace='import_export')),
    
    # استيراد البيانات من Excel
    path('data-import/', include(('data_import.urls', 'data_import'), namespace='data_import')),
    
    # نظام التصدير والنسخ الاحتياطي
    path('exports/', include(('exports.urls', 'exports'), namespace='exports')),
    
    # التطبيقات الإضافية
    path('payments/', include('payments.urls')),
    path('installments/', include(('installments.urls', 'installments'), namespace='installments')),
    path('partners/', include('partners.urls')),
    
    # نظام الحضور والانصراف
    path('attendance/', include(('attendance.urls', 'attendance'), namespace='attendance')),
    
    # مصادقة المستخدمين
    path('accounts/', include('accounts.urls')),
    path('accounts/logout/', logout_view, name='accounts_logout'),
    # path('accounts/login/'...) - تم تعطيله لاستخدام custom_login من accounts.urls
    
    # المساعد الذكي
    path('ai-assistant/', include(('ai_assistant.urls', 'ai_assistant'), namespace='ai_assistant')),
    path('printing/', include(('printing.urls', 'printing'), namespace='printing')),
    
    # نظام الضرائب
    path('taxes/', include(('taxes.urls', 'taxes'), namespace='taxes')),
    
    # الميزات المتقدمة
    path('', include('core.urls_features')),
    
    # الوحدات الجديدة
    path('branches/', include(('branches.urls', 'branches'), namespace='branches')),
    path('smart-pricing/', include(('smart_pricing.urls', 'smart_pricing'), namespace='smart_pricing')),
    path('subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),
    path('zatca/', include(('zatca_integration.urls', 'zatca'), namespace='zatca')),
    path('bank-reconciliation/', include(('bank_reconciliation.urls', 'bank_reconciliation'), namespace='bank_reconciliation')),
    path('bank-integration/', include(('bank_integration.urls', 'bank_integration'), namespace='bank_integration')),
    path('budgeting/', include(('budgeting.urls', 'budgeting'), namespace='budgeting')),
    path('quality-control/', include(('quality_control.urls', 'quality_control'), namespace='quality_control')),
    path('loyalty/', include(('loyalty.urls', 'loyalty'), namespace='loyalty')),
    path('helpdesk/', include(('helpdesk.urls', 'helpdesk'), namespace='helpdesk')),
    
    # System Monitoring - Fix 404
    path('monitoring/', include(('monitoring.urls', 'monitoring'), namespace='monitoring')),
    
    # Dashboard API المحسن
    path('dashboard-api/', include(('dashboard.urls', 'dashboard'), namespace='dashboard')),
    
    # الأنظمة المتقدمة - January 2026
    path('sales-forecasting/', include(('sales_forecasting.urls', 'sales_forecasting'), namespace='sales_forecasting')),
    path('marketing-campaigns/', include(('marketing_campaigns.urls', 'marketing_campaigns'), namespace='marketing_campaigns')),
    path('tender-bidding/', include(('tender_bidding.urls', 'tender_bidding'), namespace='tender_bidding')),
    path('warranty-management/', include(('warranty_management.urls', 'warranty_management'), namespace='warranty_management')),
    path('customer-profitability/', include(('customer_profitability.urls', 'customer_profitability'), namespace='customer_profitability')),
    path('energy-management/', include(('energy_management.urls', 'energy_management'), namespace='energy_management')),
    path('complaint-management/', include(('complaint_management.urls', 'complaint_management'), namespace='complaint_management')),
    path('license-management/', include(('license_management.urls', 'license_management'), namespace='license_management')),
    path('competitive-intelligence/', include(('competitive_intelligence.urls', 'competitive_intelligence'), namespace='competitive_intelligence')),
    path('compliance-management/', include(('compliance_management.urls', 'compliance_management'), namespace='compliance_management')),
    path('business-intelligence/', include(('business_intelligence.urls', 'business_intelligence'), namespace='business_intelligence')),
    
    # ======== الميزات المتقدمة الجديدة ========
    path('sounds/', include(('sound_notifications.urls', 'sound_notifications'), namespace='sound_notifications')),
    path('theme/', include(('theme_system.urls', 'theme_system'), namespace='theme_system')),
    path('voice/', include(('voice_assistant.urls', 'voice_assistant'), namespace='voice_assistant')),
    path('my-dashboard/', include(('custom_dashboard.urls', 'custom_dashboard'), namespace='custom_dashboard')),
    path('tasks/', include(('tasks.urls', 'tasks'), namespace='tasks')),
    path('signatures/', include(('digital_signatures.urls', 'digital_signatures'), namespace='digital_signatures')),
    path('report-builder/', include(('report_builder.urls', 'report_builder'), namespace='report_builder')),
    path('chat/', include(('internal_chat.urls', 'internal_chat'), namespace='internal_chat')),
    path('backup/', include(('cloud_backup.urls', 'cloud_backup'), namespace='cloud_backup')),
    path('ai-analytics/', include(('ai_analytics.urls', 'ai_analytics'), namespace='ai_analytics')),
    path('video/', include(('video_calls.urls', 'video_calls'), namespace='video_calls')),
    path('docs/', include(('collaborative_docs.urls', 'collaborative_docs'), namespace='collaborative_docs')),
    path('cms/', include(('cms.urls', 'cms'), namespace='cms')),
    path('smartwatch/', include(('smartwatch.urls', 'smartwatch'), namespace='smartwatch')),
    # ============================================
    
    # ======== تكامل واتساب و n8n ========
    path('whatsapp/', include(('whatsapp_integration.urls', 'whatsapp_integration'), namespace='whatsapp_integration')),
    path('api/whatsapp-ai/', include(('whatsapp_ai.urls', 'whatsapp_ai'), namespace='whatsapp_ai')),
    path('whatsapp-ai/', include(('whatsapp_ai.urls', 'whatsapp_ai_dashboard'), namespace='whatsapp_ai_dashboard')), # Fix 404
    
    # ======== صفحات السوشيال ميديا (خارج Admin) ========
    path('social-media/', include(('whatsapp_ai.urls', 'whatsapp_ai_web'), namespace='whatsapp_ai_web')),
    # ====================================
    
    # صفحة فحص المستخدم (التطوير فقط)
    path('debug-user/', lambda request: render(request, 'debug_user.html'), name='debug_user'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if _SPECTACULAR_AVAILABLE:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]

# Prometheus Metrics - تفعيل تلقائي إذا كانت الحزمة مثبتة
try:
    import django_prometheus  # noqa: F401
    urlpatterns += [
        path('metrics/', include('django_prometheus.urls')),
    ]
except ImportError:
    pass

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # تمت إزالة debug toolbar (طلب إزالة). لإعادتها أعد الكتلة السابقة.


# ================================
# Custom Error Handlers
# ================================
handler404 = 'core.views.custom_404'
handler403 = 'core.views.custom_403'
handler500 = 'core.views.custom_500'

# --- Stub URL patterns for root-level references (auto-generated) ---
from core.views_stub import stub_view as _stub  # noqa: E402
urlpatterns += [
    path('store/', _stub, name='store_home'),
    path('products/', _stub, name='product_list'),
    path('products/<int:pk>/', _stub, name='product_detail'),
    path('products/category/<int:pk>/', _stub, name='category_products'),
]
