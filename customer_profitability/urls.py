from django.urls import path
from . import views

app_name = 'customer_profitability'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('analyses/', views.analysis_list, name='analysis_list'),
    path('analyses/create/', views.analysis_create, name='analysis_create'),
    path('analyses/<int:pk>/', views.analysis_detail, name='analysis_detail'),
    path('analyses/<int:pk>/delete/', views.analysis_delete, name='analysis_delete'),
]
