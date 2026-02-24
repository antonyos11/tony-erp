"""
صفحات فحص صحة النظام - Tony ERP
نقطة مركزية واحدة لجميع فحوصات الصحة

Endpoints:
    /health/live/     - Liveness probe (سريع)
    /health/ready/    - Readiness probe (شامل)
    /health/detailed/ - تفصيلي للمشرفين فقط
"""
import time
import logging
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.conf import settings
import json
import os
from pathlib import Path

# psutil اختياري: إن لم يتوفر نستبدل الفحوصات بقيم تحذيرية
try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None

# redis اختياري
try:
    import redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore

logger = logging.getLogger('tony_erp')


@csrf_exempt
@never_cache
@require_http_methods(["GET"])
def health_live(request):
    """
    نقطة فحص الحيوية - فحص أساسي سريع
    يستخدم لفحص حالة التطبيق (liveness probe)
    """
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'service': 'Tony ERP'
    }, status=200)


@csrf_exempt
@never_cache
@require_http_methods(["GET"])
def health_ready(request):
    """
    نقطة فحص الجاهزية - فحص شامل
    يستخدم لفحص جاهزية النظام لاستقبال الطلبات (readiness probe)
    """
    from django.utils import timezone
    
    health_data = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'Tony ERP',
        'version': '2.0.0',
        'environment': getattr(settings, 'ENVIRONMENT', 'unknown'),
        'checks': {}
    }
    
    overall_healthy = True
    
    # فحص قاعدة البيانات
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        health_data['checks']['database'] = {
            'status': 'healthy',
            'message': 'الاتصال بقاعدة البيانات سليم',
            'details': {
                'engine': settings.DATABASES['default'].get('ENGINE', '').split('.')[-1],
                'test_query': 'SELECT 1',
                'result': result[0] if result else None
            }
        }
    except Exception as e:
        overall_healthy = False
        health_data['checks']['database'] = {
            'status': 'unhealthy',
            'message': f'خطأ في الاتصال بقاعدة البيانات: {str(e)}',
            'details': {'error': str(e)}
        }
    
    # فحص المهاجرات
    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if plan:
            overall_healthy = False
            health_data['checks']['migrations'] = {
                'status': 'unhealthy',
                'message': f'يوجد {len(plan)} مهاجرة معلقة',
                'details': {
                    'pending_migrations': len(plan),
                    'suggestion': 'شغّل python manage.py migrate'
                }
            }
        else:
            health_data['checks']['migrations'] = {
                'status': 'healthy',
                'message': 'جميع المهاجرات مطبقة',
                'details': {'pending_migrations': 0}
            }
    except Exception as e:
        overall_healthy = False
        health_data['checks']['migrations'] = {
            'status': 'unhealthy',
            'message': f'خطأ في فحص المهاجرات: {str(e)}',
            'details': {'error': str(e)}
        }
    
    # فحص Redis
    try:
        if redis is None:
            raise RuntimeError('redis package غير مثبت')
        redis_url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/1')
        redis_client = redis.from_url(redis_url)
        redis_client.ping()
        health_data['checks']['redis'] = {
            'status': 'healthy',
            'message': 'Redis متاح ويعمل',
            'details': {
                'url': redis_url,
                'ping': 'success'
            }
        }
    except Exception as e:
        # Redis ليس مطلوباً بشكل حاسم في وضع التطوير
        health_data['checks']['redis'] = {
            'status': 'warning',
            'message': f'Redis غير متاح: {str(e)}',
            'details': {
                'error': str(e),
                'impact': 'سيعمل النظام بدون Redis في وضع التطوير'
            }
        }
    
    # فحص الذاكرة
    try:
        if psutil is None:
            raise RuntimeError('psutil غير مثبت')
        memory = psutil.virtual_memory()
        memory_mb = memory.available / (1024 * 1024)
        min_memory = getattr(settings, 'HEALTH_CHECK', {}).get('MEMORY_MIN', 100)
        
        if memory_mb < min_memory:
            overall_healthy = False
            health_data['checks']['memory'] = {
                'status': 'unhealthy',
                'message': f'ذاكرة منخفضة: {memory_mb:.1f} MB متاحة',
                'details': {
                    'available_mb': round(memory_mb, 1),
                    'minimum_required_mb': min_memory,
                    'percentage_used': memory.percent
                }
            }
        else:
            health_data['checks']['memory'] = {
                'status': 'healthy',
                'message': f'الذاكرة متاحة: {memory_mb:.1f} MB',
                'details': {
                    'available_mb': round(memory_mb, 1),
                    'percentage_used': memory.percent
                }
            }
    except Exception as e:
        health_data['checks']['memory'] = {
            'status': 'warning',
            'message': f'لا يمكن فحص الذاكرة: {str(e)}',
            'details': {'error': str(e)}
        }
    
    # فحص المساحة التخزينية
    try:
        if psutil is None:
            raise RuntimeError('psutil غير مثبت')
        disk = psutil.disk_usage(settings.BASE_DIR)
        disk_usage_percent = (disk.used / disk.total) * 100
        max_disk_usage = getattr(settings, 'HEALTH_CHECK', {}).get('DISK_USAGE_MAX', 90)
        
        if disk_usage_percent > max_disk_usage:
            overall_healthy = False
            health_data['checks']['disk'] = {
                'status': 'unhealthy',
                'message': f'مساحة تخزينية منخفضة: {disk_usage_percent:.1f}% مستخدمة',
                'details': {
                    'usage_percent': round(disk_usage_percent, 1),
                    'free_gb': round(disk.free / (1024**3), 1),
                    'total_gb': round(disk.total / (1024**3), 1)
                }
            }
        else:
            health_data['checks']['disk'] = {
                'status': 'healthy',
                'message': f'مساحة تخزينية كافية: {disk_usage_percent:.1f}% مستخدمة',
                'details': {
                    'usage_percent': round(disk_usage_percent, 1),
                    'free_gb': round(disk.free / (1024**3), 1),
                    'total_gb': round(disk.total / (1024**3), 1)
                }
            }
    except Exception as e:
        health_data['checks']['disk'] = {
            'status': 'warning',
            'message': f'لا يمكن فحص المساحة التخزينية: {str(e)}',
            'details': {'error': str(e)}
        }
    
    # فحص الملفات المهمة
    important_paths = [
        (settings.STATIC_ROOT, 'static_files', 'الملفات الثابتة'),
        (settings.MEDIA_ROOT, 'media_files', 'ملفات الميديا'),
        (settings.BASE_DIR / 'logs', 'logs', 'مجلد السجلات'),
    ]
    
    for path, check_name, display_name in important_paths:
        try:
            path_obj = Path(path)
            if path_obj.exists():
                health_data['checks'][check_name] = {
                    'status': 'healthy',
                    'message': f'{display_name} متاح',
                    'details': {
                        'path': str(path),
                        'exists': True,
                        'writable': os.access(path, os.W_OK)
                    }
                }
            else:
                overall_healthy = False
                health_data['checks'][check_name] = {
                    'status': 'unhealthy',
                    'message': f'{display_name} غير موجود',
                    'details': {
                        'path': str(path),
                        'exists': False,
                        'suggestion': f'أنشئ المجلد: mkdir -p {path}'
                    }
                }
        except Exception as e:
            health_data['checks'][check_name] = {
                'status': 'warning',
                'message': f'خطأ في فحص {display_name}: {str(e)}',
                'details': {'error': str(e)}
            }
    
    # تحديد الحالة العامة
    if overall_healthy:
        health_data['status'] = 'healthy'
        status_code = 200
    else:
        health_data['status'] = 'unhealthy'
        status_code = 503  # Service Unavailable
    
    return JsonResponse(health_data, status=status_code, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@csrf_exempt
@never_cache
@require_http_methods(["GET"])  
def system_status(request):
    """
    حالة النظام التفصيلية - واجهة HTML
    """
    from django.shortcuts import render
    from django.utils import timezone
    import platform
    
    try:
        # معلومات النظام
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'django_version': __import__('django').get_version(),
            'current_time': timezone.now(),
            'debug_mode': settings.DEBUG,
            'environment': getattr(settings, 'ENVIRONMENT', 'unknown'),
        }
        
        # إحصائيات قاعدة البيانات
        db_stats = {}
        try:
            with connection.cursor() as cursor:
                # عدد الجداول (يختلف حسب نوع قاعدة البيانات)
                if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                elif 'postgresql' in settings.DATABASES['default']['ENGINE']:
                    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
                elif 'mysql' in settings.DATABASES['default']['ENGINE']:
                    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", [settings.DATABASES['default']['NAME']])
                
                db_stats['tables_count'] = cursor.fetchone()[0]
                
        except Exception as e:
            db_stats['error'] = str(e)
        
        context = {
            'system_info': system_info,
            'db_stats': db_stats,
        }
        
        return render(request, 'core/system_status.html', context)
        
    except Exception as e:
        return JsonResponse({
            'error': 'خطأ في جلب معلومات النظام',
            'details': str(e)
        }, status=500)


@csrf_exempt
@never_cache
@require_http_methods(["GET"])
def health_detailed(request):
    """
    فحص مفصل - للمشرفين فقط
    يعطي معلومات تفصيلية عن حالة كل مكونات النظام
    
    يمكن الوصول بـ:
    - مستخدم مسجل دخول (staff)
    - أو عبر X-Health-Key header
    """
    # التحقق من الصلاحيات
    user = getattr(request, 'user', None)
    is_authenticated = user and getattr(user, 'is_authenticated', False)
    
    if not is_authenticated:
        api_key = request.headers.get('X-Health-Key', '')
        expected_key = getattr(settings, 'HEALTH_CHECK_KEY', '')
        if not expected_key or api_key != expected_key:
            return JsonResponse({
                'status': 'unauthorized',
                'message': 'يجب تسجيل الدخول أو إرسال X-Health-Key',
            }, status=401)

    if is_authenticated and not getattr(user, 'is_staff', False):
        return JsonResponse({
            'status': 'forbidden',
            'message': 'يجب أن تكون مشرفاً',
        }, status=403)

    checks = {}
    warnings = []
    errors = []

    # 1. فحص قاعدة البيانات
    db_start = time.time()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

            db_engine = settings.DATABASES['default']['ENGINE']
            db_info = {'engine': db_engine.split('.')[-1]}

            if 'postgresql' in db_engine:
                try:
                    cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                    db_info['active_connections'] = cursor.fetchone()[0]
                except Exception:
                    pass
                try:
                    cursor.execute("SELECT pg_database_size(current_database())")
                    db_size = cursor.fetchone()[0]
                    db_info['database_size_mb'] = round(db_size / (1024 * 1024), 2)
                except Exception:
                    pass
            elif 'sqlite3' in db_engine:
                warnings.append('SQLite غير مناسب للإنتاج - استخدم PostgreSQL')
                db_info['warning'] = 'SQLite - للتطوير فقط'

        db_time = round((time.time() - db_start) * 1000, 2)
        checks['database'] = {'status': 'ok', 'response_time_ms': db_time, **db_info}
    except Exception as e:
        errors.append(f'Database: {str(e)}')
        checks['database'] = {'status': 'error', 'error': str(e)}

    # 2. فحص الكاش
    cache_start = time.time()
    try:
        from django.core.cache import cache
        cache.set('health_detailed_test', 'ok', 30)
        result = cache.get('health_detailed_test')
        cache_time = round((time.time() - cache_start) * 1000, 2)

        cache_backend = settings.CACHES.get('default', {}).get('BACKEND', '')
        if 'redis' in cache_backend.lower():
            cache_type = 'Redis'
        elif 'locmem' in cache_backend.lower():
            cache_type = 'LocMem'
            warnings.append('LocMem Cache - غير مناسب للإنتاج')
        elif 'dummy' in cache_backend.lower():
            cache_type = 'Dummy'
            warnings.append('Dummy Cache - الكاش معطل')
        else:
            cache_type = cache_backend.split('.')[-1]

        checks['cache'] = {
            'status': 'ok' if result == 'ok' else 'degraded',
            'response_time_ms': cache_time,
            'backend': cache_type,
        }
    except Exception as e:
        warnings.append(f'Cache: {str(e)}')
        checks['cache'] = {'status': 'unavailable', 'error': str(e)}

    # 3. فحص إعدادات الأمان
    security_issues = []
    if settings.DEBUG:
        security_issues.append('DEBUG = True')
    if 'insecure' in getattr(settings, 'SECRET_KEY', '').lower():
        security_issues.append('SECRET_KEY غير آمن')
    if not getattr(settings, 'SECURE_SSL_REDIRECT', False) and not settings.DEBUG:
        security_issues.append('SECURE_SSL_REDIRECT معطل')

    checks['security'] = {
        'status': 'ok' if not security_issues else 'warning',
        'debug_mode': settings.DEBUG,
        'issues': security_issues if security_issues else 'لا توجد مشاكل أمنية',
    }
    if security_issues:
        warnings.extend([f'Security: {issue}' for issue in security_issues])

    # 4. فحص التطبيقات المثبتة
    installed_apps = [app for app in settings.INSTALLED_APPS if not app.startswith('django.')]
    checks['applications'] = {
        'status': 'ok',
        'total_apps': len(settings.INSTALLED_APPS),
        'custom_apps': len(installed_apps),
    }

    # 5. معلومات النظام
    import platform
    import django
    checks['system'] = {
        'python_version': platform.python_version(),
        'django_version': django.get_version(),
        'os': platform.system(),
        'platform': platform.platform(),
    }

    # تحديد الحالة العامة
    if errors:
        overall_status = 'unhealthy'
        status_code = 503
    elif warnings:
        overall_status = 'degraded'
        status_code = 200
    else:
        overall_status = 'healthy'
        status_code = 200

    return JsonResponse({
        'status': overall_status,
        'service': 'Tony ERP',
        'version': getattr(settings, 'VERSION', '2.0.0'),
        'timestamp': timezone.now().isoformat(),
        'check': 'detailed',
        'checks': checks,
        'warnings': warnings,
        'errors': errors,
        'summary': {
            'total_checks': len(checks),
            'warnings_count': len(warnings),
            'errors_count': len(errors),
        },
    }, status=status_code, json_dumps_params={'ensure_ascii': False, 'indent': 2})