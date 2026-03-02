"""
خدمة سجل التدقيق — RITA ERP
"""
from apps.authorization.models import AuditLog


def get_client_ip(request):
    """استخراج عنوان IP من الـ request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_user_agent(request) -> str:
    """استخراج بيانات المتصفح"""
    return request.META.get('HTTP_USER_AGENT', '')[:512]


def log_action(user, action, module, model_name='', object_id='',
               description='', old_value=None, new_value=None,
               ip_address=None, branch=None, user_agent=''):
    """تسجيل حركة في سجل التدقيق"""
    return AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        model_name=model_name,
        object_id=str(object_id) if object_id else '',
        description=description,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent,
        branch=branch,
    )


def log_action_from_request(request, action, module, model_name='', object_id='',
                             description='', old_value=None, new_value=None):
    """
    تسجيل حركة في سجل التدقيق مع استخلاص البيانات من الـ request تلقائيًا
    """
    return log_action(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        module=module,
        model_name=model_name,
        object_id=object_id,
        description=description,
        old_value=old_value,
        new_value=new_value,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        branch=getattr(request.user, 'branch', None) if request.user.is_authenticated else None,
    )



def get_audit_log(filters=None):
    """استعلام سجل التدقيق مع فلاتر"""
    qs = AuditLog.objects.select_related('user', 'branch').order_by('-timestamp')

    if not filters:
        return qs

    if filters.get('user_id'):
        qs = qs.filter(user_id=filters['user_id'])
    if filters.get('action'):
        qs = qs.filter(action=filters['action'])
    if filters.get('module'):
        qs = qs.filter(module=filters['module'])
    if filters.get('model_name'):
        qs = qs.filter(model_name=filters['model_name'])
    if filters.get('date_from'):
        qs = qs.filter(timestamp__date__gte=filters['date_from'])
    if filters.get('date_to'):
        qs = qs.filter(timestamp__date__lte=filters['date_to'])
    if filters.get('branch_id'):
        qs = qs.filter(branch_id=filters['branch_id'])
    if filters.get('ip_address'):
        qs = qs.filter(ip_address=filters['ip_address'])

    return qs
