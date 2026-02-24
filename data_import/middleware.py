# -*- coding: utf-8 -*-
"""
Middleware للكشف عن النظام الجديد وتوجيه المستخدم لصفحة الإعداد
تم تحسين الأداء: يتحقق مرة واحدة فقط في الجلسة (وليس كل request)
"""
import logging

logger = logging.getLogger('tony_erp')


class NewSystemSetupMiddleware:
    """
    Middleware للكشف عن النظام الجديد
    إذا كان النظام جديداً ولم يتم تهيئته، يظهر إشعار للمستخدم
    
    تحسينات الأداء:
    - يتحقق مرة واحدة فقط في الجلسة عبر session flag
    - يستخدم الكاش لتقليل استعلامات قاعدة البيانات
    - المسارات المستثناة تعود فوراً بدون أي فحص
    """

    EXCLUDED_PATHS = [
        '/data-import/',
        '/admin/',
        '/static/',
        '/media/',
        '/api/',
        '/health/',
        '/login/',
        '/logout/',
        '/metrics/',
        '/__debug__/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # تخطي المسارات المستثناة - فحص سريع
        path = request.path
        for excluded_path in self.EXCLUDED_PATHS:
            if path.startswith(excluded_path):
                return self.get_response(request)

        # فقط للمستخدمين المسجلين والمشرفين - حماية ضد AnonymousUser
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False) and getattr(user, 'is_staff', False):
            # ✅ تحسين: التحقق مرة واحدة فقط في الجلسة
            if not request.session.get('_system_check_done'):
                try:
                    # محاولة استخدام الكاش أولاً
                    setup_result = self._check_with_cache(user)
                    
                    if setup_result is not None:
                        request.session['_show_setup_prompt'] = setup_result
                    else:
                        # fallback: فحص قاعدة البيانات
                        self._check_from_db(request)

                    request.session['_system_check_done'] = True
                except Exception as e:
                    # لو حصل أي خطأ، نعلّم إنه اتفحص عشان ما نكرر
                    logger.warning(f"Setup middleware error: {e}")
                    request.session['_system_check_done'] = True

        response = self.get_response(request)
        return response

    def _check_with_cache(self, user):
        """
        فحص حالة الإعداد عبر الكاش - تجنب DB queries
        Returns: True/False for show_setup_prompt, or None if cache miss
        """
        try:
            from django.core.cache import cache
            cache_key = f'system_setup_status_{user.pk}'
            return cache.get(cache_key)
        except Exception:
            return None

    def _check_from_db(self, request):
        """
        فحص حالة الإعداد من قاعدة البيانات (fallback)
        يخزن النتيجة في الكاش لمدة ساعة
        """
        try:
            from data_import.models import SystemInitialization
            from inventory.models import Product
            from partners.models import Customer

            init = SystemInitialization.get_instance()

            # النظام جديد إذا لم يتم تهيئته ولا توجد بيانات
            if not init.is_initialized:
                product_count = Product.objects.count()
                customer_count = Customer.objects.count()

                if product_count == 0 and customer_count == 0:
                    request.session['_show_setup_prompt'] = True
                    show_prompt = True
                else:
                    # بيانات موجودة = النظام مبدئ فعلياً
                    request.session['_show_setup_prompt'] = False
                    show_prompt = False
            else:
                request.session['_show_setup_prompt'] = False
                show_prompt = False

            # حفظ في الكاش لمدة ساعة
            try:
                from django.core.cache import cache
                cache_key = f'system_setup_status_{request.user.pk}'
                cache.set(cache_key, show_prompt, 3600)
            except Exception:
                pass

        except Exception:
            request.session['_show_setup_prompt'] = False
