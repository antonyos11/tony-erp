"""
Tony ERP - Core API URLs
نقاط نهاية API الأساسية للنظام

Endpoints:
    GET /api/core/           - قائمة API endpoints المتوفرة
    GET /api/core/system/    - معلومات النظام (للمشرفين فقط)
"""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.conf import settings

app_name = 'core-api'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_root(request):
    """نقطة البداية لـ API - تعرض جميع الـ endpoints المتوفرة"""
    endpoints = {
        'health': {
            'live': request.build_absolute_uri('/health/live/'),
            'ready': request.build_absolute_uri('/health/ready/'),
            'detailed': request.build_absolute_uri('/health/detailed/'),
        },
        'auth': {
            'token': request.build_absolute_uri('/api/token/'),
            'refresh': request.build_absolute_uri('/api/token/refresh/'),
            'verify': request.build_absolute_uri('/api/token/verify/'),
        },
    }

    # إضافة endpoints التطبيقات
    app_endpoints = [
        ('accounting', '/accounting/'),
        ('sales', '/sales/'),
        ('crm', '/crm/'),
        ('inventory', '/inventory/'),
        ('hr', '/hr/'),
        ('payments', '/payments/'),
        ('bank_integration', '/bank-integration/'),
        ('tax', '/taxes/'),
        ('reports', '/reports/'),
        ('monitoring', '/monitoring/'),
    ]

    for name, url in app_endpoints:
        try:
            endpoints[name] = request.build_absolute_uri(url)
        except Exception:
            pass

    return Response({
        'service': 'Tony ERP API',
        'version': getattr(settings, 'VERSION', '2.0.0'),
        'endpoints': endpoints,
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_info(request):
    """معلومات النظام - للمشرفين فقط"""
    import platform
    import django

    return Response({
        'system': {
            'python_version': platform.python_version(),
            'django_version': django.get_version(),
            'os': platform.system(),
            'platform': platform.platform(),
        },
        'settings': {
            'debug': settings.DEBUG,
            'environment': getattr(settings, 'ENVIRONMENT', 'unknown'),
            'database_engine': settings.DATABASES['default']['ENGINE'].split('.')[-1],
            'cache_backend': settings.CACHES.get('default', {}).get('BACKEND', 'none').split('.')[-1],
            'installed_apps_count': len(settings.INSTALLED_APPS),
            'middleware_count': len(settings.MIDDLEWARE),
            'redis_available': getattr(settings, 'REDIS_AVAILABLE', False),
        },
    })


urlpatterns = [
    path('', api_root, name='api-root'),
    path('system/', system_info, name='system-info'),
]
