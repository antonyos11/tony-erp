"""
Tony ERP - Heartbeat & Connection Status
حل مشكلة حالة الاتصال - يوفر نقطة فحص بسيطة للجافاسكريبت
"""
import time
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.db import connection

logger = logging.getLogger(__name__)


@csrf_exempt
@require_GET
@never_cache
def heartbeat(request):
    """نبض بسيط - هل السيرفر حي؟"""
    return JsonResponse({
        'status': 'connected',
        'ts': int(time.time()),
    })


@csrf_exempt
@require_GET
@never_cache
def connection_status(request):
    """حالة الاتصال مع تفاصيل"""
    result = {
        'status': 'online',
        'timestamp': timezone.now().isoformat(),
        'server': 'Tony ERP',
    }

    # معلومات المستخدم
    if hasattr(request, 'user') and request.user.is_authenticated:
        result['user'] = {
            'username': request.user.username,
            'is_staff': request.user.is_staff,
            'authenticated': True,
        }
    else:
        result['user'] = {'authenticated': False}

    # فحص DB سريع
    try:
        t0 = time.time()
        with connection.cursor() as c:
            c.execute("SELECT 1")
        result['db'] = {
            'status': 'ok',
            'ms': round((time.time() - t0) * 1000, 1),
        }
    except Exception:
        result['db'] = {'status': 'error'}
        result['status'] = 'degraded'

    return JsonResponse(result)


@csrf_exempt
@require_GET
@never_cache
def server_time(request):
    """وقت السيرفر - للمزامنة"""
    now = timezone.now()
    return JsonResponse({
        'iso': now.isoformat(),
        'unix': int(now.timestamp()),
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M:%S'),
        'timezone': str(timezone.get_current_timezone()),
    })
