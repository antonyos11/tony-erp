"""
WebSocket consumer for real-time production monitoring TV dashboard.
Broadcasts production order updates to all connected factory floor displays.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from decimal import Decimal


class ProductionDashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for the factory floor TV dashboard."""

    PRODUCTION_GROUP = 'production_tv_dashboard'

    async def connect(self):
        """Accept connection and send full dashboard snapshot."""
        await self.channel_layer.group_add(
            self.PRODUCTION_GROUP,
            self.channel_name,
        )
        await self.accept()

        # Send full snapshot on connect
        snapshot = await self.get_dashboard_snapshot()
        await self.send(text_data=json.dumps({
            'type': 'full_snapshot',
            'data': snapshot,
            'timestamp': timezone.now().isoformat(),
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.PRODUCTION_GROUP,
            self.channel_name,
        )

    async def receive(self, text_data):
        """Handle client messages (e.g. manual refresh request)."""
        try:
            message = json.loads(text_data)
            if message.get('action') == 'refresh':
                snapshot = await self.get_dashboard_snapshot()
                await self.send(text_data=json.dumps({
                    'type': 'full_snapshot',
                    'data': snapshot,
                    'timestamp': timezone.now().isoformat(),
                }))
        except (json.JSONDecodeError, KeyError):
            pass

    # ---------- Group message handlers ----------

    async def production_order_updated(self, event):
        """Relay a single-order update to the client."""
        await self.send(text_data=json.dumps({
            'type': 'order_updated',
            'data': event['data'],
            'timestamp': event.get('timestamp', timezone.now().isoformat()),
        }))

    async def production_snapshot_refresh(self, event):
        """Full dashboard refresh triggered server-side."""
        snapshot = await self.get_dashboard_snapshot()
        await self.send(text_data=json.dumps({
            'type': 'full_snapshot',
            'data': snapshot,
            'timestamp': timezone.now().isoformat(),
        }))

    # ---------- Data fetching ----------

    @database_sync_to_async
    def get_dashboard_snapshot(self):
        """Build the complete dashboard payload."""
        from production.models import ProductionOrder, ProductionWorkCenter
        from production.services.inventory_integration import ProductionInventoryService

        orders = (
            ProductionOrder.objects.filter(
                status__in=['draft', 'confirmed', 'in_progress']
            )
            .select_related('product', 'bom')
            .prefetch_related('order_stages__stage__work_center')
            .order_by('-status', 'priority', 'planned_end_date')
        )

        today = timezone.now().date()
        order_list = []

        for order in orders:
            # Progress calculation
            planned = float(order.planned_quantity or 0)
            produced = float(order.produced_quantity or 0)
            progress = (produced / planned * 100) if planned > 0 else 0

            # Work center — derived from the first BOM stage
            work_center_name = '—'
            first_stage = order.order_stages.select_related('stage__work_center').first()
            if first_stage and first_stage.stage and first_stage.stage.work_center:
                work_center_name = first_stage.stage.work_center.name

            # Material availability check
            material_ok = True
            shortage_items = []
            try:
                if order.bom:
                    available, materials_status = (
                        ProductionInventoryService.check_material_availability(order)
                    )
                    material_ok = available
                    if not available:
                        shortage_items = [
                            {
                                'name': m.get('material_name', 'غير معروف'),
                                'sku': m.get('material_code', ''),
                                'shortage': float(m.get('shortage', 0)),
                            }
                            for m in materials_status
                            if not m.get('is_available', False) and 'error' not in m
                        ]
            except Exception:
                material_ok = False

            order_list.append({
                'id': order.id,
                'number': order.number,
                'product_name': order.product.name if order.product else '—',
                'product_sku': order.product.sku if order.product else '—',
                'bom_name': order.bom.name if order.bom else '—',
                'work_center': work_center_name,
                'status': order.status,
                'status_display': order.get_status_display(),
                'priority': order.priority,
                'priority_display': order.get_priority_display(),
                'planned_quantity': planned,
                'produced_quantity': produced,
                'scrap_quantity': float(order.scrap_quantity or 0),
                'progress': round(progress, 1),
                'material_ok': material_ok,
                'shortage_items': shortage_items,
                'planned_start': (
                    order.planned_start_date.isoformat()
                    if order.planned_start_date else None
                ),
                'planned_end': (
                    order.planned_end_date.isoformat()
                    if order.planned_end_date else None
                ),
                'actual_start': (
                    order.actual_start_date.isoformat()
                    if order.actual_start_date else None
                ),
                'is_overdue': (
                    order.planned_end_date is not None
                    and order.planned_end_date < today
                    and order.status != 'completed'
                ),
            })

        # Summary stats
        total = len(order_list)
        in_progress = sum(1 for o in order_list if o['status'] == 'in_progress')
        pending = total - in_progress
        overdue = sum(1 for o in order_list if o.get('is_overdue'))
        shortages = sum(1 for o in order_list if not o['material_ok'])
        avg_progress = (
            sum(o['progress'] for o in order_list if o['status'] == 'in_progress')
            / in_progress
            if in_progress > 0
            else 0
        )

        # Work-center utilisation
        wc_stats = []
        work_centers = ProductionWorkCenter.objects.filter(is_active=True)
        for wc in work_centers:
            active = orders.filter(
                order_stages__stage__work_center=wc,
                status='in_progress',
            ).distinct().count()
            wc_stats.append({
                'id': wc.id,
                'name': wc.name,
                'type': wc.get_work_center_type_display(),
                'active_orders': active,
                'capacity_per_hour': float(wc.capacity_per_hour or 0),
            })

        return {
            'orders': order_list,
            'summary': {
                'total_active': total,
                'in_progress': in_progress,
                'pending': pending,
                'overdue': overdue,
                'shortages': shortages,
                'avg_progress': round(avg_progress, 1),
            },
            'work_centers': wc_stats,
        }
