"""
URLs لتحليلات الذكاء الاصطناعي
"""

from django.urls import path
from . import views

app_name = 'ai_analytics'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sales-forecast/', views.sales_forecast, name='sales_forecast'),
    path('churn-prediction/', views.churn_prediction, name='churn_prediction'),
    path('inventory-analysis/', views.inventory_analysis, name='inventory_analysis'),
    path('insights/', views.insights_list, name='insights'),
    path('insights/generate/', views.generate_insights, name='generate_insights'),
    path('insights/<int:insight_id>/read/', views.mark_insight_read, name='mark_read'),
    path('ask/', views.ask_ai, name='ask_ai'),
]
