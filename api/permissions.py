from rest_framework.permissions import DjangoModelPermissions, BasePermission


class DjangoModelViewPermissions(DjangoModelPermissions):
    """Require Django 'view' permission for safe methods (GET/HEAD/OPTIONS)."""
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class RequireAuditViewPerm(BasePermission):
    message = 'You do not have permission to view audit logs.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_perm('core.view_auditlog'))
