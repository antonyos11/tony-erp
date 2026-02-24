# branches/urls.py
from django.urls import path
from . import views

app_name = 'branches'

urlpatterns = [
    # Dashboard
    path('', views.unified_dashboard, name='unified_dashboard'),
    
    # List & CRUD
    path('list/', views.unified_list, name='unified_list'),
    path('create/', views.create_location, name='create_location'),
    path('<int:pk>/', views.location_detail, name='location_detail'),
    path('<int:pk>/edit/', views.edit_location, name='edit_location'),
    path('<int:pk>/toggle/', views.toggle_status, name='toggle_status'),
    
    # Session
    path('set-current/', views.set_current_location, name='set_current_location'),
    
    # API
    path('api/list/', views.api_locations_list, name='api_locations_list'),
    path('api/<int:pk>/', views.api_location_detail, name='api_location_detail'),
]
