"""
Tony ERP - Monitoring and Health Check System
نظام المراقبة والفحص الصحي
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import logging
from datetime import datetime
import psutil
import os

logger = logging.getLogger(__name__)


class HealthCheckManager:
    """مدير الفحص الصحي للنظام"""
    
    @staticmethod
    def check_database() -> dict:
        """فحص الاتصال بقاعدة البيانات"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {'status': 'healthy', 'message': 'Database connection successful'}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def check_cache() -> dict:
        """فحص الذاكرة المؤقتة"""
        try:
            test_key = 'health_check_test'
            test_value = 'test_value'
            
            cache.set(test_key, test_value, 10)
            retrieved_value = cache.get(test_key)
            
            if retrieved_value == test_value:
                cache.delete(test_key)
                return {'status': 'healthy', 'message': 'Cache is working'}
            else:
                return {'status': 'unhealthy', 'message': 'Cache read/write mismatch'}
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def check_disk_space() -> dict:
        """فحص المساحة المتاحة على القرص"""
        try:
            disk = psutil.disk_usage('/')
            percent_used = disk.percent
            
            if percent_used > 90:
                status = 'critical'
                message = f'Disk usage critical: {percent_used}%'
            elif percent_used > 75:
                status = 'warning'
                message = f'Disk usage high: {percent_used}%'
            else:
                status = 'healthy'
                message = f'Disk usage normal: {percent_used}%'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': percent_used
                }
            }
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {'status': 'unknown', 'message': str(e)}
    
    @staticmethod
    def check_memory() -> dict:
        """فحص استخدام الذاكرة"""
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            
            if percent_used > 90:
                status = 'critical'
                message = f'Memory usage critical: {percent_used}%'
            elif percent_used > 75:
                status = 'warning'
                message = f'Memory usage high: {percent_used}%'
            else:
                status = 'healthy'
                message = f'Memory usage normal: {percent_used}%'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': percent_used
                }
            }
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {'status': 'unknown', 'message': str(e)}
    
    @staticmethod
    def check_cpu() -> dict:
        """فحص استخدام المعالج"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 90:
                status = 'critical'
                message = f'CPU usage critical: {cpu_percent}%'
            elif cpu_percent > 75:
                status = 'warning'
                message = f'CPU usage high: {cpu_percent}%'
            else:
                status = 'healthy'
                message = f'CPU usage normal: {cpu_percent}%'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count()
                }
            }
        except Exception as e:
            logger.error(f"CPU check failed: {e}")
            return {'status': 'unknown', 'message': str(e)}
    
    @classmethod
    def full_health_check(cls) -> dict:
        """فحص صحي شامل للنظام"""
        checks = {
            'database': cls.check_database(),
            'cache': cls.check_cache(),
            'disk': cls.check_disk_space(),
            'memory': cls.check_memory(),
            'cpu': cls.check_cpu(),
        }
        
        # تحديد الحالة الإجمالية
        statuses = [check['status'] for check in checks.values()]
        
        if 'unhealthy' in statuses or 'critical' in statuses:
            overall_status = 'unhealthy'
        elif 'warning' in statuses:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        return {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': checks
        }


def health_check_view(request):
    """عرض الفحص الصحي"""
    health_data = HealthCheckManager.full_health_check()
    
    # تحديد كود الاستجابة HTTP
    if health_data['status'] == 'unhealthy':
        status_code = 503
    elif health_data['status'] == 'warning':
        status_code = 200
    else:
        status_code = 200
    
    return JsonResponse(health_data, status=status_code)


def readiness_check_view(request):
    """فحص الجاهزية - للـ Kubernetes"""
    try:
        # فحص أساسي سريع
        db_check = HealthCheckManager.check_database()
        
        if db_check['status'] == 'healthy':
            return JsonResponse({'status': 'ready'}, status=200)
        else:
            return JsonResponse({'status': 'not ready'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=503)


def liveness_check_view(request):
    """فحص الحياة - للـ Kubernetes"""
    return JsonResponse({'status': 'alive'}, status=200)


class MetricsCollector:
    """جامع المقاييس"""
    
    @staticmethod
    def collect_request_metrics() -> dict:
        """جمع مقاييس الطلبات"""
        # يمكن استخدام prometheus_client هنا
        return {
            'total_requests': 0,
            'error_count': 0,
            'avg_response_time': 0
        }
    
    @staticmethod
    def collect_database_metrics() -> dict:
        """جمع مقاييس قاعدة البيانات"""
        from django.db import connection
        
        return {
            'total_queries': len(connection.queries),
            'slow_queries': len([q for q in connection.queries if float(q['time']) > 0.1])
        }
    
    @staticmethod
    def collect_business_metrics() -> dict:
        """جمع المقاييس التجارية"""
        try:
            from sales.models import Invoice
            from datetime import date, timedelta
            
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            return {
                'invoices_today': Invoice.objects.filter(date=today).count(),
                'invoices_yesterday': Invoice.objects.filter(date=yesterday).count(),
                'total_invoices': Invoice.objects.count()
            }
        except Exception as e:
            logger.error(f"Failed to collect business metrics: {e}")
            return {}


def metrics_view(request):
    """عرض المقاييس"""
    metrics = {
        'system': {
            'disk': HealthCheckManager.check_disk_space(),
            'memory': HealthCheckManager.check_memory(),
            'cpu': HealthCheckManager.check_cpu(),
        },
        'application': {
            'requests': MetricsCollector.collect_request_metrics(),
            'database': MetricsCollector.collect_database_metrics(),
            'business': MetricsCollector.collect_business_metrics(),
        },
        'timestamp': datetime.now().isoformat()
    }
    
    return JsonResponse(metrics)
