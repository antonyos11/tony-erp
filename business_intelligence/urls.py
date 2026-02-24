from django.urls import path
from . import views

app_name = 'business_intelligence'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Dashboards
    path('dashboards/', views.dashboard_list, name='dashboard_list'),
    path('dashboards/create/', views.dashboard_create, name='dashboard_create'),
    path('dashboards/<uuid:pk>/', views.dashboard_detail, name='dashboard_detail'),
    
    # Forecasts
    path('forecasts/', views.forecast_list, name='forecast_list'),
    
    # Reports
    path('reports/', views.report_list, name='report_list'),
    
    # API
    path('api/kpis/', views.api_kpis, name='api_kpis'),
]
