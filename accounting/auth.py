from functools import wraps
from django.core.exceptions import PermissionDenied


def require_perm(perm_name: str):
    """Decorator to enforce a Django permission.

    Usage:
        @require_perm('accounting.post_journal_entry')
        def view(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            if not request.user.has_perm(perm_name):
                raise PermissionDenied(f"Missing permission: {perm_name}")
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
