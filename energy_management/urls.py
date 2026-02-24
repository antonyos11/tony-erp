from django.urls import path
from . import views

app_name = 'energy_management'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('meters/', views.meter_list, name='meter_list'),
    path('meters/create/', views.meter_create, name='meter_create'),
    path('meters/<int:pk>/', views.meter_detail, name='meter_detail'),
    path('meters/<int:pk>/edit/', views.meter_edit, name='meter_edit'),
    path('meters/<int:pk>/delete/', views.meter_delete, name='meter_delete'),
    path('readings/', views.reading_list, name='reading_list'),
    path('readings/create/', views.reading_create, name='reading_create'),
]
