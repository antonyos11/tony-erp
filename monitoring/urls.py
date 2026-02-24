"""
Monitoring Module URLs
نظام المراقبة وكشف الشذوذات
"""
from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Root/index view - redirects to anomaly dashboard
    path('', views.anomaly_dashboard, name='index'),
    # Anomaly Detection - fix 404
    path('anomaly-detection/', views.anomaly_dashboard, name='anomaly_dashboard'),
    path('anomaly-detection/alerts/', views.anomaly_alerts, name='anomaly_alerts'),
    path('anomaly-detection/config/', views.anomaly_config, name='anomaly_config'),
    path('anomaly-detection/history/', views.anomaly_history, name='anomaly_history'),
    path('anomaly-detection/api/check/', views.run_anomaly_check, name='run_anomaly_check'),
]

