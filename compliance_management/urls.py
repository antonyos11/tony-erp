from django.urls import path
from . import views

app_name = 'compliance_management'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('requirements/', views.requirement_list, name='requirement_list'),
    path('requirements/create/', views.requirement_create, name='requirement_create'),
    path('requirements/<int:pk>/', views.requirement_detail, name='requirement_detail'),
    path('requirements/<int:pk>/edit/', views.requirement_edit, name='requirement_edit'),
    path('requirements/<int:pk>/delete/', views.requirement_delete, name='requirement_delete'),
]
