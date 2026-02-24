"""
URLs for ZATCA Integration Module
"""

from django.urls import path
from . import views

app_name = 'zatca'

urlpatterns = [
    path('', views.zatca_dashboard, name='dashboard'),
    path('invoices/', views.invoices_list, name='invoices_list'),
    path('config/', views.zatca_config, name='config'),
]
