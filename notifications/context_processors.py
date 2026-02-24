from __future__ import annotations
from django.contrib.auth.models import AnonymousUser
from django.db.models import Count
from .models import Notification


def unread_notifications(request):
    """Provide unread notifications count for authenticated users.

    Uses a lightweight count query. Wrapped in broad exception handling to avoid
    breaking templates during early migrations or in edge cases.
    """
    user = getattr(request, 'user', None)
    count = 0
    try:
        if user and not isinstance(user, AnonymousUser) and user.is_authenticated:
            count = Notification.objects.filter(user=user, is_read=False).count()
    except Exception:
        # Fail silent to keep UI resilient (e.g. before migrations applied)
        count = 0
    return {'unread_notifications_count': count}
