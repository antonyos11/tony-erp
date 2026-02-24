from django.urls import path
from . import views

app_name = 'sales_forecasting'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('forecasts/', views.forecast_list, name='forecast_list'),
    path('forecasts/create/', views.forecast_create, name='forecast_create'),
    path('demand-patterns/', views.demand_patterns, name='demand_patterns'),
    path('recommendations/', views.recommendations, name='recommendations'),
]
