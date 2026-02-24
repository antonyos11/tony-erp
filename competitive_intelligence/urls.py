from django.urls import path
from . import views

app_name = 'competitive_intelligence'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('competitors/', views.competitor_list, name='competitor_list'),
    path('competitors/create/', views.competitor_create, name='competitor_create'),
    path('competitors/<int:pk>/', views.competitor_detail, name='competitor_detail'),
    path('competitors/<int:pk>/edit/', views.competitor_edit, name='competitor_edit'),
    path('competitors/<int:pk>/delete/', views.competitor_delete, name='competitor_delete'),
]
