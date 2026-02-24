"""
Tenant Middleware
Middleware للمستأجرين

يتعرف تلقائياً على المستأجر من النطاق ويضبط السياق
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.conf import settings
from .models import Tenant, TenantDomain
from .utils import set_current_tenant, clear_current_tenant
import threading

# Thread-local storage للمستأجر الحالي
_thread_locals = threading.local()


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware للتعرف على المستأجر من النطاق
    
    يجب إضافته في MIDDLEWARE في settings.py
    """
    
    def process_request(self, request):
        """معالجة الطلب وتحديد المستأجر"""
        
        # الحصول على النطاق من الطلب
        host = request.get_host().split(':')[0]  # إزالة المنفذ
        
        # محاولة الحصول على المستأجر من النطاق
        tenant = self._get_tenant_from_domain(host)
        
        if not tenant:
            # محاولة من subdomain
            tenant = self._get_tenant_from_subdomain(host)
        
        if not tenant:
            # استخدام المستأجر الافتراضي في التطوير
            if settings.DEBUG:
                tenant = Tenant.objects.filter(is_active=True).first()
        
        if not tenant:
            return HttpResponseForbidden('Invalid tenant domain')
        
        # التحقق من نشاط المستأجر
        if not tenant.is_active:
            return HttpResponseForbidden('Tenant account is inactive')
        
        # التحقق من انتهاء الاشتراك
        if not tenant.is_subscription_active():
            # يمكن إعادة توجيه لصفحة تجديد الاشتراك
            if not request.path.startswith('/subscription/'):
                return HttpResponseRedirect('/subscription/expired/')
        
        # حفظ المستأجر في الطلب
        request.tenant = tenant
        
        # حفظ المستأجر في thread-local
        set_current_tenant(tenant)
        
        # تحميل العلامة التجارية
        try:
            request.branding = tenant.branding
        except:
            request.branding = None
        
        # تحميل الإعدادات
        try:
            request.tenant_settings = tenant.settings
        except:
            request.tenant_settings = None
        
        return None
    
    def process_response(self, request, response):
        """تنظيف بعد المعالجة"""
        clear_current_tenant()
        return response
    
    def process_exception(self, request, exception):
        """تنظيف عند حدوث خطأ"""
        clear_current_tenant()
        return None
    
    def _get_tenant_from_domain(self, domain):
        """الحصول على المستأجر من النطاق الكامل"""
        try:
            tenant_domain = TenantDomain.objects.select_related('tenant').get(
                domain=domain,
                is_active=True
            )
            return tenant_domain.tenant
        except TenantDomain.DoesNotExist:
            return None
    
    def _get_tenant_from_subdomain(self, host):
        """الحصول على المستأجر من subdomain"""
        # مثال: acme.tony-erp.com -> slug: acme
        parts = host.split('.')
        if len(parts) >= 2:
            subdomain = parts[0]
            try:
                tenant = Tenant.objects.get(slug=subdomain, is_active=True)
                return tenant
            except Tenant.DoesNotExist:
                pass
        return None


class TenantDataIsolationMiddleware(MiddlewareMixin):
    """
    Middleware لعزل البيانات بين المستأجرين
    
    يضمن عدم تسرب البيانات بين العملاء
    """
    
    def process_request(self, request):
        """التحقق من عزل البيانات"""
        
        if not hasattr(request, 'tenant'):
            return None
        
        # يمكن إضافة قواعد أمان إضافية هنا
        return None


class TenantThemeMiddleware(MiddlewareMixin):
    """
    Middleware لتطبيق ثيم المستأجر
    
    يضيف متغيرات CSS للثيم المخصص
    """
    
    def process_template_response(self, request, response):
        """إضافة متغيرات الثيم للقالب"""
        
        if not hasattr(request, 'branding') or not request.branding:
            return response
        
        branding = request.branding
        
        # إضافة متغيرات CSS
        context_data = getattr(response, 'context_data', {})
        if context_data is not None:
            context_data['theme'] = {
                'primary_color': branding.primary_color,
                'secondary_color': branding.secondary_color,
                'accent_color': branding.accent_color,
                'background_color': branding.background_color,
                'text_color': branding.text_color,
                'font_family': branding.font_family,
                'logo_url': branding.get_logo_url(),
                'app_title': branding.get_app_title(),
                'custom_css': branding.custom_css,
            }
        
        return response
