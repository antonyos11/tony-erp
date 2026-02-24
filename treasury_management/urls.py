from django.urls import path
from . import views

app_name = 'treasury_management'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.dashboard, name='home'),
    
    # Cash Flow
    path('cashflow/forecast/', views.cash_flow_forecast, name='cash_flow_forecast'),
    path('liquidity/analysis/', views.liquidity_analysis, name='liquidity_analysis'),
    
    # Investments
    path('investments/', views.investments_list, name='investments_list'),
    path('investments/<uuid:pk>/', views.investment_detail, name='investment_detail'),
    
    # Targets
    path('targets/', views.treasury_targets, name='treasury_targets'),
    
    # API
    path('api/cashflow-chart/', views.api_cashflow_chart, name='api_cashflow_chart'),
    path('api/investment-performance/', views.api_investment_performance, name='api_investment_performance'),
]
