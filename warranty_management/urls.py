from django.urls import path
from . import views

app_name = 'warranty_management'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('warranties/', views.warranty_list, name='warranty_list'),
    path('warranties/create/', views.warranty_create, name='warranty_create'),
    path('warranties/<int:pk>/', views.warranty_detail, name='warranty_detail'),
    path('warranties/<int:pk>/edit/', views.warranty_edit, name='warranty_edit'),
    path('warranties/<int:pk>/delete/', views.warranty_delete, name='warranty_delete'),
    path('claims/', views.claim_list, name='claim_list'),
    path('claims/create/', views.claim_create, name='claim_create'),
    path('claims/<int:pk>/', views.claim_detail, name='claim_detail'),
]
