"""
WebSocket URL routing for the production app.
"""

from django.urls import path
from . import consumers
from . import consumers_pipeline

websocket_urlpatterns = [
    path('ws/production/tv-dashboard/', consumers.ProductionDashboardConsumer.as_asgi()),
    path('ws/production/pipeline/', consumers_pipeline.PipelineDashboardConsumer.as_asgi()),
    path('ws/production/print-agent/', consumers_pipeline.PrintAgentConsumer.as_asgi()),
]
