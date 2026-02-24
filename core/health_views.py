"""
System Health Check Endpoint
"""
import os
import redis
from django.http import JsonResponse
from django.db import connection
from django.utils import timezone


def system_health(request):
    health = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health['checks']['database'] = {'status': 'up', 'engine': connection.vendor}
    except Exception as e:
        health['checks']['database'] = {'status': 'down', 'error': str(e)}
        health['status'] = 'unhealthy'

    # Redis check
    try:
        r = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'))
        r.ping()
        health['checks']['redis'] = {'status': 'up'}
    except Exception as e:
        health['checks']['redis'] = {'status': 'down', 'error': str(e)}

    # Disk check
    try:
        import shutil
        total, used, free = shutil.disk_usage('/')
        health['checks']['disk'] = {
            'status': 'up',
            'total_gb': round(total / (1024**3), 1),
            'free_gb': round(free / (1024**3), 1),
            'usage_percent': round(used / total * 100, 1)
        }
    except Exception as e:
        health['checks']['disk'] = {'status': 'error', 'error': str(e)}

    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)


def health_live(request):
    """Liveness check - is the app running?"""
    return JsonResponse({'status': 'alive', 'timestamp': timezone.now().isoformat()})


def health_ready(request):
    """Readiness check - can the app serve requests?"""
    checks = {}
    status = 'ready'
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = 'up'
    except Exception as e:
        checks['database'] = f'down: {e}'
        status = 'not_ready'

    # Redis check
    try:
        r = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'))
        r.ping()
        checks['redis'] = 'up'
    except Exception as e:
        checks['redis'] = f'down: {e}'
    
    status_code = 200 if status == 'ready' else 503
    return JsonResponse({'status': status, 'checks': checks, 'timestamp': timezone.now().isoformat()}, status=status_code)


# Alias for URL compatibility
health_detailed = system_health

# Alias for URL compatibility
system_status = system_health
