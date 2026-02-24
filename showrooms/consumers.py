from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Showroom, ShowroomEmployee
import json

class ShowroomKPIConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        self.showroom_id = self.scope['url_route']['kwargs'].get('showroom_id')
        if not self.showroom_id:
            await self.close()
            return
        if not await self._can_access(user, self.showroom_id):
            await self.close()
            return
        self.group_name = f'showroom_{self.showroom_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Initial state push (optional lazy placeholder)
        await self.send(json.dumps({'type': 'init', 'message': 'connected'}))

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Simple ping/pong support
        try:
            if text_data:
                payload = json.loads(text_data)
                if payload.get('action') == 'ping':
                    await self.send(json.dumps({'type': 'pong'}))
        except Exception:
            pass

    async def kpi_message(self, event):
        # Forward broadcasted KPI event
        await self.send(json.dumps({'type': 'kpi', 'data': event.get('data', {})}))

    @database_sync_to_async
    def _can_access(self, user, showroom_id):
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        # Manager or employee assigned
        if Showroom.objects.filter(id=showroom_id, manager=user).exists():
            return True
        assigned = ShowroomEmployee.objects.filter(user=user, showroom_id=showroom_id, active=True)
        if assigned.exists():
            return True
        # cross access to all
        if ShowroomEmployee.objects.filter(user=user, active=True, can_cross_access=True).exists():
            return True
        return False
