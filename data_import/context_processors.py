# -*- coding: utf-8 -*-
"""
Context Processors لنظام استيراد البيانات
"""


def setup_prompt(request):
    """
    إضافة متغير للتحقق من عرض إشعار الإعداد الأولي
    """
    context = {
        'show_setup_prompt': False,
        'is_new_system': False,
    }
    
    if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
        try:
            # التحقق من وجود session
            if not hasattr(request, 'session'):
                return context
            # التحقق من الجلسة أولاً (أسرع)
            if request.session.get('_show_setup_prompt'):
                context['show_setup_prompt'] = True
                context['is_new_system'] = True
            elif not request.session.get('_system_check_done'):
                # التحقق من قاعدة البيانات
                from data_import.models import SystemInitialization
                from inventory.models import Product
                from partners.models import Customer
                
                init = SystemInitialization.get_instance()
                
                if not init.is_initialized:
                    product_count = Product.objects.count()
                    customer_count = Customer.objects.count()
                    
                    if product_count == 0 and customer_count == 0:
                        context['show_setup_prompt'] = True
                        context['is_new_system'] = True
                        request.session['_show_setup_prompt'] = True
                    
                    request.session['_system_check_done'] = True
        except Exception:
            pass
    
    return context
