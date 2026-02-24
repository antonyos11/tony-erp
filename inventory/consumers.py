"""
WebSocket consumers for inventory real-time updates
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class InventoryConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for inventory real-time updates"""
    
    async def connect(self):
        # Get user from scope
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
            
        # Join inventory updates group
        self.inventory_group_name = 'inventory_updates'
        
        await self.channel_layer.group_add(
            self.inventory_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current low stock items
        low_stock_items = await self.get_low_stock_items()
        if low_stock_items:
            await self.send(text_data=json.dumps({
                'type': 'low_stock_alert',
                'items': low_stock_items,
                'count': len(low_stock_items)
            }))

    async def disconnect(self, close_code):
        # Leave inventory group
        await self.channel_layer.group_discard(
            self.inventory_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', '')
            
            if message_type == 'get_stock_status':
                product_id = text_data_json.get('product_id')
                stock_info = await self.get_product_stock(product_id)
                await self.send(text_data=json.dumps({
                    'type': 'stock_status',
                    'product_id': product_id,
                    'stock_info': stock_info
                }))
                
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'خطأ في معالجة الرسالة: {str(e)}'
            }))

    # Handle inventory update
    async def inventory_update(self, event):
        """Send inventory update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'inventory_update',
            'update': event['update']
        }))

    # Handle low stock alert
    async def low_stock_alert(self, event):
        """Send low stock alert to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'low_stock_alert',
            'alert': event['alert']
        }))

    @database_sync_to_async
    def get_low_stock_items(self):
        """Get current low stock items"""
        try:
            from inventory.models import Product
            from django.conf import settings
            
            threshold = getattr(settings, 'LOW_STOCK_THRESHOLD_DEFAULT', 10)
            
            low_stock_items = []
            products = Product.objects.filter(current_stock__lte=threshold)
            
            for product in products:
                low_stock_items.append({
                    'id': product.id,
                    'name': product.name,
                    'current_stock': product.current_stock,
                    'min_stock': product.min_stock_level or threshold,
                    'location': product.location.name if product.location else 'غير محدد'
                })
            
            return low_stock_items
        except Exception:
            return []

    @database_sync_to_async
    def get_product_stock(self, product_id):
        """Get specific product stock information"""
        try:
            from inventory.models import Product
            
            if not product_id:
                return None
                
            product = Product.objects.get(id=product_id)
            return {
                'id': product.id,
                'name': product.name,
                'current_stock': product.current_stock,
                'min_stock': product.min_stock_level,
                'max_stock': product.max_stock_level,
                'location': product.location.name if product.location else 'غير محدد',
                'status': 'low' if product.current_stock <= (product.min_stock_level or 10) else 'normal'
            }
        except Exception:
            return None