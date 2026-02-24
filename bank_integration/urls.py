"""
Bank Integration URLs
روابط التكامل البنكي
"""

from django.urls import path
from . import views

app_name = 'bank_integration'

urlpatterns = [
    path('', views.bank_integration_dashboard, name='dashboard'),
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/<uuid:pk>/', views.account_detail, name='account_detail'),
    path('transactions/', views.transaction_list, name='transaction_list'),
]
