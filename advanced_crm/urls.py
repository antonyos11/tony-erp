from django.urls import path
from . import views

app_name = 'advanced_crm'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.dashboard, name='home'),
    
    # Opportunities
    path('opportunities/', views.opportunities_list, name='opportunities_list'),
    path('opportunities/<uuid:pk>/', views.opportunity_detail, name='opportunity_detail'),
    
    # Analytics
    path('analytics/customers/', views.customer_analytics, name='customer_analytics'),
    path('analytics/forecast/', views.sales_forecast, name='sales_forecast'),
    path('analytics/journey/<int:customer_id>/', views.customer_journey, name='customer_journey'),
    
    # API Endpoints
    path('api/pipeline-data/', views.api_pipeline_data, name='api_pipeline_data'),
    path('api/conversion-funnel/', views.api_conversion_funnel, name='api_conversion_funnel'),
]
