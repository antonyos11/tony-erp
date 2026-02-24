from django.urls import path
from . import views

app_name = 'risk_management'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.dashboard, name='home'),
    
    # Risks
    path('risks/', views.risks_list, name='risks_list'),
    path('risks/<uuid:pk>/', views.risk_detail, name='risk_detail'),
    path('risks/matrix/', views.risk_matrix, name='risk_matrix'),
    
    # Mitigation Plans
    path('mitigation-plans/', views.mitigation_plans_list, name='mitigation_plans_list'),
    
    # API
    path('api/risk-heatmap/', views.api_risk_heatmap, name='api_risk_heatmap'),
    path('api/risk-trend/', views.api_risk_trend, name='api_risk_trend'),
]
