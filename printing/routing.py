"""WebSocket URL routing for the printing app."""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Print agent connects here (from Windows/Linux machine)
    re_path(r'ws/print-agent/$', consumers.UnifiedPrintAgentConsumer.as_asgi()),
    # Browser clients subscribe for print status updates
    re_path(r'ws/print-status/$', consumers.PrintStatusConsumer.as_asgi()),
]
