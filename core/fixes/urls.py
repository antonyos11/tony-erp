"""
Tony ERP - URLs للإصلاحات
Heartbeat, Connection Status, Dashboard Stats API
"""
from django.urls import path
from core.fixes import heartbeat, dashboard_api

urlpatterns = [
    # Heartbeat
    path('heartbeat/', heartbeat.heartbeat, name='api-heartbeat'),
    path('connection/', heartbeat.connection_status, name='connection-status'),
    path('server-time/', heartbeat.server_time, name='server-time'),

    # Dashboard Stats
    path('dashboard/stats/', dashboard_api.dashboard_stats_api, name='dashboard-stats'),
]
