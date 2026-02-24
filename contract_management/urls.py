from django.urls import path
from . import views

app_name = 'contract_management'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.dashboard, name='home'),
    
    # Contracts
    path('contracts/', views.contracts_list, name='contracts_list'),
    path('contracts/create/', views.contract_create, name='contract_create'),
    path('contracts/<uuid:pk>/', views.contract_detail, name='contract_detail'),
    path('contracts/<uuid:pk>/edit/', views.contract_edit, name='contract_edit'),
    path('contracts/<uuid:pk>/delete/', views.contract_delete, name='contract_delete'),
    
    # Renewals
    path('renewals/alerts/', views.renewal_alerts, name='renewal_alerts'),
    
    # API
    path('api/contracts-chart/', views.api_contracts_chart, name='api_contracts_chart'),
]
