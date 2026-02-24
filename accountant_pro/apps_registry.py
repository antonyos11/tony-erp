"""
سجل التطبيقات المعياري - Tony ERP
Modular Apps Registry

يفصل التطبيقات الأساسية عن الاختيارية لتحسين الأداء وسهولة الصيانة.
يمكن استخدامه لعرض حالة التطبيقات المثبتة.

الاستخدام:
    python manage.py apps_report
    python manage.py apps_report --json
"""
import importlib
import logging

logger = logging.getLogger(__name__)


# =====================================================
# التطبيقات الأساسية (مطلوبة لعمل النظام)
# =====================================================
CORE_APPS = [
    'core',
    'users',
    'accounts',
    'accounting',
    'sales',
    'purchases',
    'inventory',
    'hr',
    'dashboard',
    'reports',
    'notifications',
    'partners',
]

# =====================================================
# تطبيقات الأعمال (اختيارية لكن شائعة)
# =====================================================
BUSINESS_APPS = [
    'crm',
    'production',
    'maintenance',
    'fleet',
    'payments',
    'installments',
    'pos',
    'branches',
    'showrooms',
    'approvals',
    'fixed_assets',
    'contracting',
    'shipping',
    'eservices',
    'projects',
    'ecommerce',
    'taxes',
    'attendance',
    'budgeting',
    'quality_control',
    'loyalty',
    'helpdesk',
    'data_import',
    'exports',
    'printing',
    'bank_reconciliation',
    'home_services',
]

# =====================================================
# تطبيقات متقدمة (Enterprise features)
# =====================================================
ADVANCED_APPS = [
    'bank_integration',
    'risk_management',
    'tax_system',
    'contract_management',
    'advanced_notifications',
    'treasury_management',
    'advanced_crm',
    'business_intelligence',
    'correspondence_management',
    'intellectual_property',
    'sales_forecasting',
    'marketing_campaigns',
    'tender_bidding',
    'warranty_management',
    'customer_profitability',
    'energy_management',
    'complaint_management',
    'license_management',
    'competitive_intelligence',
    'compliance_management',
    'monitoring',
    'smart_pricing',
    'subscriptions',
    'zatca_integration',
    'quick_access',
]

# =====================================================
# تطبيقات إضافية / Plugins
# =====================================================
OPTIONAL_APPS = [
    'ai_assistant',
    'ai_analytics',
    'whatsapp_integration',
    'whatsapp_ai',
    'video_calls',
    'voice_assistant',
    'smartwatch',
    'mattress_builder',
    'shipment_tracking',
    'product_reviews',
    'sound_notifications',
    'theme_system',
    'custom_dashboard',
    'tasks',
    'digital_signatures',
    'report_builder',
    'internal_chat',
    'cloud_backup',
    'collaborative_docs',
    'cms',
]

# =====================================================
# تطبيقات API والتكاملات
# =====================================================
API_APPS = [
    'api',
    'woocommerce_integration',
]


def _is_app_available(app_name):
    """التحقق من أن التطبيق موجود ويمكن استيراده"""
    try:
        importlib.import_module(app_name)
        return True
    except ImportError:
        return False


def get_available_apps(include_optional=True, include_api=True):
    """
    إرجاع قائمة التطبيقات المتاحة فعلياً (التي يمكن استيرادها).

    Args:
        include_optional: تضمين التطبيقات الاختيارية
        include_api: تضمين تطبيقات API

    Returns:
        list: قائمة التطبيقات المتاحة
    """
    available = []

    for app in CORE_APPS:
        if _is_app_available(app):
            available.append(app)
        else:
            logger.warning(f"التطبيق الأساسي '{app}' غير متاح!")

    for app in BUSINESS_APPS:
        if _is_app_available(app):
            available.append(app)

    for app in ADVANCED_APPS:
        if _is_app_available(app):
            available.append(app)

    if include_optional:
        for app in OPTIONAL_APPS:
            if _is_app_available(app):
                available.append(app)

    if include_api:
        for app in API_APPS:
            if _is_app_available(app):
                available.append(app)

    return available


def get_apps_status():
    """إرجاع حالة جميع التطبيقات مصنفة"""
    status = {
        'core': {},
        'business': {},
        'advanced': {},
        'optional': {},
        'api': {},
    }

    for app in CORE_APPS:
        status['core'][app] = _is_app_available(app)
    for app in BUSINESS_APPS:
        status['business'][app] = _is_app_available(app)
    for app in ADVANCED_APPS:
        status['advanced'][app] = _is_app_available(app)
    for app in OPTIONAL_APPS:
        status['optional'][app] = _is_app_available(app)
    for app in API_APPS:
        status['api'][app] = _is_app_available(app)

    return status


def print_apps_report():
    """طباعة تقرير حالة التطبيقات بشكل مقروء"""
    status = get_apps_status()

    category_labels = {
        'core': 'التطبيقات الأساسية (Core)',
        'business': 'تطبيقات الأعمال (Business)',
        'advanced': 'تطبيقات متقدمة (Advanced)',
        'optional': 'تطبيقات اختيارية (Optional)',
        'api': 'تطبيقات API',
    }

    print("\n" + "=" * 60)
    print("  Tony ERP - تقرير حالة التطبيقات")
    print("=" * 60)

    total_available = 0
    total_apps = 0

    for category, apps in status.items():
        total = len(apps)
        available = sum(1 for v in apps.values() if v)
        total_available += available
        total_apps += total

        label = category_labels.get(category, category)
        print(f"\n  {label} ({available}/{total}):")
        for app, is_available in apps.items():
            icon = "  ✅" if is_available else "  ❌"
            print(f"   {icon} {app}")

    print(f"\n  المجموع: {total_available}/{total_apps} تطبيق متاح")
    print("=" * 60 + "\n")
