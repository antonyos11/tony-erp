"""
ASGI config for accountant_pro project with WebSocket support.
"""

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import WebSocket consumers
from core.consumers import NotificationConsumer
from inventory.consumers import InventoryConsumer
from showrooms.consumers import ShowroomKPIConsumer
from production.consumers import ProductionDashboardConsumer
from production.consumers_pipeline import PipelineDashboardConsumer, PrintAgentConsumer
from printing.consumers import UnifiedPrintAgentConsumer, PrintStatusConsumer

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi()),
    path('ws/inventory/', InventoryConsumer.as_asgi()),
    path('ws/showrooms/<int:showroom_id>/kpi/', ShowroomKPIConsumer.as_asgi()),
    path('ws/production/tv-dashboard/', ProductionDashboardConsumer.as_asgi()),
    path('ws/production/pipeline/', PipelineDashboardConsumer.as_asgi()),
    path('ws/production/print-agent/', PrintAgentConsumer.as_asgi()),
    # Unified Print System
    path('ws/print-agent/', UnifiedPrintAgentConsumer.as_asgi()),
    path('ws/print-status/', PrintStatusConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})