"""
Middleware تحسين الأداء والتتبع
Performance Optimization Middleware
"""

import time
import logging
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class QueryCountMiddleware:
    """
    Middleware لتتبع وتحسين عدد استعلامات قاعدة البيانات
    """
    
    QUERY_WARNING_THRESHOLD = 50
    QUERY_CRITICAL_THRESHOLD = 100
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if not settings.DEBUG:
            return self.get_response(request)
        
        # تسجيل عدد الاستعلامات قبل
        queries_before = len(connection.queries)
        
        response = self.get_response(request)
        
        # حساب عدد الاستعلامات
        queries_count = len(connection.queries) - queries_before
        
        # تسجيل التحذيرات
        if queries_count >= self.QUERY_CRITICAL_THRESHOLD:
            logger.warning(
                f"[PERF CRITICAL] {request.path} executed {queries_count} queries!"
            )
        elif queries_count >= self.QUERY_WARNING_THRESHOLD:
            logger.info(
                f"[PERF WARNING] {request.path} executed {queries_count} queries"
            )
        
        # إضافة header للتطوير
        if settings.DEBUG:
            response['X-Query-Count'] = str(queries_count)
        
        return response


class ResponseTimeMiddleware:
    """
    Middleware لقياس وتحسين زمن الاستجابة
    """
    
    SLOW_REQUEST_THRESHOLD_MS = 1000  # 1 ثانية
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # تسجيل الطلبات البطيئة
        if duration_ms >= self.SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                f"[SLOW REQUEST] {request.method} {request.path} took {duration_ms:.2f}ms"
            )
        
        # إضافة headers للتطوير
        if settings.DEBUG:
            response['X-Response-Time-Ms'] = f"{duration_ms:.2f}"
        
        return response


class CompressionOptimizationMiddleware:
    """
    Middleware لتحسين الضغط والتخزين المؤقت
    """
    
    # أنواع المحتوى القابلة للضغط
    COMPRESSIBLE_TYPES = [
        'text/html',
        'text/css',
        'text/javascript',
        'application/javascript',
        'application/json',
        'application/xml',
        'text/xml',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # إضافة headers للتخزين المؤقت الأمثل
        content_type = response.get('Content-Type', '').split(';')[0]
        
        if content_type in self.COMPRESSIBLE_TYPES:
            # السماح بالضغط
            if 'Content-Encoding' not in response:
                response['Vary'] = 'Accept-Encoding'
        
        # تحسين التخزين المؤقت للملفات الثابتة
        if request.path.startswith('/static/'):
            if 'Cache-Control' not in response:
                response['Cache-Control'] = 'public, max-age=31536000'  # سنة
        
        return response


class PageCacheMiddleware:
    """
    Middleware للتخزين المؤقت للصفحات بالكامل
    """
    
    # الصفحات المستثناة من التخزين
    EXCLUDED_PATHS = [
        '/admin/',
        '/api/',
        '/accounts/',
        '/logout/',
    ]
    
    # مدة التخزين الافتراضية (بالثواني)
    DEFAULT_CACHE_TIMEOUT = 60
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # لا تخزين للمستخدمين المسجلين أو POST requests
        if request.user.is_authenticated or request.method != 'GET':
            return self.get_response(request)
        
        # لا تخزين للمسارات المستثناة
        if any(request.path.startswith(p) for p in self.EXCLUDED_PATHS):
            return self.get_response(request)
        
        # محاولة الحصول من الكاش
        cache_key = f"page_cache:{request.path}:{request.GET.urlencode()}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            response = HttpResponse(
                cached_response['content'],
                content_type=cached_response['content_type'],
                status=cached_response['status']
            )
            response['X-Cache'] = 'HIT'
            return response
        
        response = self.get_response(request)
        
        # تخزين الاستجابات الناجحة فقط
        if response.status_code == 200:
            cache_data = {
                'content': response.content,
                'content_type': response.get('Content-Type', 'text/html'),
                'status': response.status_code,
            }
            cache.set(cache_key, cache_data, self.DEFAULT_CACHE_TIMEOUT)
            response['X-Cache'] = 'MISS'
        
        return response


class LazyLoadMiddleware:
    """
    Middleware لتحسين التحميل الكسول
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # إضافة hints للمتصفح لتحسين التحميل
        if response.get('Content-Type', '').startswith('text/html'):
            # Resource hints
            if 'Link' not in response:
                links = []
                
                # Preconnect لـ CDN
                links.append('<https://cdn.jsdelivr.net>; rel=preconnect')
                links.append('<https://fonts.googleapis.com>; rel=preconnect')
                
                # Preload للموارد المهمة
                links.append('</static/css/ui_v2.css>; rel=preload; as=style')
                links.append('</static/js/app_layout.js>; rel=preload; as=script')
                
                response['Link'] = ', '.join(links)
        
        return response


class SecurityHeadersMiddleware:
    """
    Middleware لإضافة headers الأمان المتقدمة
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Content Security Policy
        if 'Content-Security-Policy' not in response:
            csp = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com https://cdnjs.cloudflare.com",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com",
                "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com",
                "img-src 'self' data: https: blob:",
                "connect-src 'self' ws: wss: ws://localhost:* wss://localhost:* https://cdn.jsdelivr.net https://api.openai.com",
            ]
            response['Content-Security-Policy'] = '; '.join(csp)
        
        # Permissions Policy
        if 'Permissions-Policy' not in response:
            response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Referrer Policy
        if 'Referrer-Policy' not in response:
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
