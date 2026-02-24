from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class ShowroomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'showrooms'
    verbose_name = _('المعارض / الفروع')

    def ready(self):
        # تأخير الاستيراد لتفادي مشاكل أثناء تحميل التطبيقات
        from django.contrib.auth.signals import user_logged_in
        from django.dispatch import receiver
        from .models import ShowroomEmployee
        from .middleware import SESSION_KEY
        from django.conf import settings
        
        # استيراد signals المزامنة مع Branch
        from . import signals  # noqa: F401

        @receiver(user_logged_in, dispatch_uid="showrooms_auto_set_active")
        def auto_set_active_showroom(sender, user, request, **kwargs):
            try:
                from django.conf import settings as _s
                # Allow deferring automatic showroom selection (tests expect explicit selection)
                if getattr(_s, 'DEFER_AUTO_SHOWROOM', True):
                    return
                # استخدم المفتاح الموحد
                if not request.session.get(SESSION_KEY) and not request.session.get('active_showroom_id'):
                    assigns = list(ShowroomEmployee.objects.filter(user=user, active=True).values_list('showroom_id','can_cross_access'))
                    if len(assigns) == 1:
                        request.session[SESSION_KEY] = assigns[0][0]
                    elif len(assigns) > 1:
                        # لو لديه cross_access لا نفرض واحد
                        if not any(a[1] for a in assigns):
                            # اختر أول واحد (يمكن لاحقاً تحسينها بمعيار آخر)
                            request.session[SESSION_KEY] = assigns[0][0]
                # تنظيف المفتاح القديم إن وُجد ونقل القيمة
                if request.session.get('active_showroom_id') and not request.session.get(SESSION_KEY):
                    request.session[SESSION_KEY] = request.session['active_showroom_id']
                    del request.session['active_showroom_id']
            except Exception:
                pass
