from rest_framework.permissions import BasePermission
from .models import ShowroomEmployee
from django.db import models
from django.utils.functional import cached_property

ROLE_BASE_MATRIX = {
    # role: {module: set(actions)}  (baseline)
    'manager': {
        'pos': {'view', 'add', 'change', 'export', 'print'},
        'inventory': {'view', 'add', 'change', 'transfer', 'adjust'},
        'expenses': {'view', 'add', 'change', 'approve'},
        'purchases': {'view', 'add', 'change', 'approve'},
        'payroll': {'view', 'add', 'approve'},
        'hr': {'view', 'add', 'change'},
        'sales': {'view'},
    },
    'supervisor': {
        'pos': {'view', 'add', 'change', 'print'},
        'inventory': {'view', 'add', 'change'},
        'expenses': {'view', 'add', 'change'},
        'purchases': {'view', 'add'},
        'hr': {'view'},
    },
    'cashier': {
        'pos': {'view', 'add', 'change', 'print'},
    },
    'sales': {
        'pos': {'view'},
        'inventory': {'view'},
    },
    'storekeeper': {
        'inventory': {'view', 'add', 'change', 'transfer', 'adjust'},
        'purchases': {'view', 'add', 'change'},
        'expenses': {'view'},
    },
    'warehouse_worker': {
        'inventory': {'view', 'add', 'change', 'transfer'},
    },
    'hr': {
        'hr': {'view', 'add', 'change'},
        'payroll': {'view', 'add', 'approve'},
    },
    'call_center': {
        'pos': {'view'},
    },
    'customer_service': {
        'pos': {'view'},
        'expenses': {'view'},
    },
    'porter': {
        'inventory': {'view'},
    },
    'pantry': {
        'expenses': {'view', 'add'},
    },
    'worker': {
        'inventory': {'view'},
        'pos': {'view'},
    },
}

def showroom_has_action(user, showroom_id, module: str, action: str) -> bool:
    if user.is_superuser:
        return True
    qs = ShowroomEmployee.objects.filter(user=user, active=True)
    if not qs.exists():
        return False
    # global access
    if qs.filter(can_cross_access=True).exists():
        return True
    emp = qs.filter(showroom_id=showroom_id).first()
    if not emp:
        return False
    role_matrix = ROLE_BASE_MATRIX.get(emp.role, {})
    allowed = set()
    for mod, acts in role_matrix.items():
        if mod == module:
            allowed |= set(acts)
    # merge extra_perms list like "pos.add"
    for entry in emp.extra_perms:
        try:
            mod, act = entry.split('.')
            if mod == module:
                allowed.add(act)
        except ValueError:
            continue
    return action in allowed

class HasShowroomAccess(BasePermission):
    """تحقق من أن المستخدم له صلاحية الوصول للمعرض المحدد إما مباشرة أو بصلاحية عامة."""
    message = 'ليست لديك صلاحية للوصول لهذا المعرض'

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_superuser:
                return True
            showroom_id = request.data.get('showroom') or request.data.get('showroom_id') or request.query_params.get('showroom')
            if not showroom_id:
                # بعض العروض (list) يمكن أن تعيد فقط المعارض المسموح بها بدون رفض كامل
                return True
            return ShowroomEmployee.objects.filter(user=request.user, showroom_id=showroom_id, active=True).exists() or \
                   ShowroomEmployee.objects.filter(user=request.user, can_cross_access=True, active=True).exists()
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if hasattr(obj, 'showroom_id'):
            return ShowroomEmployee.objects.filter(user=request.user, active=True).filter(
                models.Q(can_cross_access=True) | models.Q(showroom_id=obj.showroom_id)
            ).exists()
        return False
