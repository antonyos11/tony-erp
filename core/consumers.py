"""
WebSocket consumers for real-time notifications
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        # Get user from scope
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
            
        # Create personal notification channel
        self.notification_group_name = f'user_{self.user.id}_notifications'
        
        # Join notification group
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'متصل بنظام الإشعارات المباشرة'
        }))

    async def disconnect(self, close_code):
        # Leave notification group
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', '')
            
            if message_type == 'mark_as_read':
                notification_id = text_data_json.get('notification_id')
                await self.mark_notification_as_read(notification_id)
                
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'خطأ في معالجة الرسالة: {str(e)}'
            }))

    # Handle notification message
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    # Handle system alert
    async def system_alert(self, event):
        """Send system alert to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'system_alert',
            'alert': event['alert']
        }))

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """Mark notification as read in database"""
        try:
            from notifications.models import Notification
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()
            return True
        except Exception:
            return False