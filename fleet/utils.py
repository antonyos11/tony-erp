from users.models import UserActivity
from django.utils import timezone

def log_activity(request, action: str, module: str = 'fleet', object_id: str = '', description: str = '', success: bool = True, error_message: str = ''):
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return
    ip = request.META.get('REMOTE_ADDR', '')
    ua = request.META.get('HTTP_USER_AGENT', '')
    try:
        UserActivity.objects.create(
            user=user,
            action=action,
            module=module,
            object_id=str(object_id) if object_id else '',
            description=description[:500],
            ip_address=ip or '0.0.0.0',
            user_agent=ua[:500],
            success=success,
            error_message=error_message[:500]
        )
    except Exception:
        # لا نوقف الطلب بسبب فشل التسجيل
        pass
