"""
Notification Services Package

Contains both legacy notification functions and new messaging services.
"""
# Import from legacy notification system (previously services.py)
from .legacy_notification import (
    send_notification,
    send_bulk,
    broadcast,
    send_notification_safe
)

# Import new messaging services
from .messaging_service import AutoMessagingService, MessageTemplates

__all__ = [
    # Legacy functions
    'send_notification',
    'send_bulk',
    'broadcast',
    'send_notification_safe',
    # New services
    'AutoMessagingService',
    'MessageTemplates',
]
