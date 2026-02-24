"""
Security Headers Middleware
إضافة headers أمنية متقدمة لجميع الاستجابات
"""
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    إضافة Security Headers للاستجابات
    """
    
    def process_response(self, request, response):
        """
        إضافة headers أمنية
        """
        # منع clickjacking
        if not response.has_header('X-Frame-Options'):
            response['X-Frame-Options'] = 'SAMEORIGIN'
        
        # منع Content Type Sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # تفعيل XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (Feature Policy سابقاً)
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Strict Transport Security (HTTPS only)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
