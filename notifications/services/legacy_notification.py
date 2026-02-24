from typing import Iterable, Optional, Sequence
from django.contrib.auth.models import User
from notifications.models import Notification


def send_notification(user: Optional[User], title: str, message: str, level: str = 'info'):
    return Notification.objects.create(user=user, title=title, message=message, level=level)


def send_bulk(users: Sequence[User], title: str, message: str, level: str = 'info'):
    objs = [Notification(user=u, title=title, message=message, level=level) for u in users]
    return Notification.objects.bulk_create(objs)


def broadcast(title: str, message: str, level: str = 'info'):
    for user in User.objects.filter(is_active=True):
        Notification.objects.create(user=user, title=title, message=message, level=level)


def send_notification_safe(users, title: str, message: str, level: str = 'info'):
    try:
        if users is None:
            broadcast(title, message, level)
        elif isinstance(users, (list, tuple)):
            send_bulk(users, title, message, level)
        else:
            send_notification(users, title, message, level)
    except Exception:
        # Silent fail (يمكن لاحقاً تسجيله في سجل أخطاء خاص)
        pass