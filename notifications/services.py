"""
Notification Services
"""
from typing import List, Optional
from django.contrib.auth.models import User
from notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


def send_notification_safe(users: List[User], title: str, message: str, 
                          level: str = 'info', metadata: dict = None):
    """
    إرسال إشعار آمن للمستخدمين
    
    Args:
        users: قائمة المستخدمين
        title: عنوان الإشعار
        message: نص الإشعار
        level: مستوى الإشعار (info, warning, error, success)
        metadata: بيانات إضافية
    """
    try:
        for user in users:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                level=level,
                metadata=metadata or {}
            )
        logger.info(f"Notification sent to {len(users)} users: {title}")
    except Exception as e:
        logger.error(f"Error sending notification: {e}", exc_info=True)
