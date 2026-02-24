from django.urls import path
from . import views

app_name = 'license_management'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('licenses/', views.license_list, name='license_list'),
    path('licenses/create/', views.license_create, name='license_create'),
    path('licenses/<int:pk>/', views.license_detail, name='license_detail'),
    path('licenses/<int:pk>/edit/', views.license_edit, name='license_edit'),
    path('licenses/<int:pk>/delete/', views.license_delete, name='license_delete'),
]
