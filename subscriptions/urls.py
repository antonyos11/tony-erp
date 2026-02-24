"""
URLs for Subscriptions Module
"""

from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.plans_list, name='index'),
    path('plans/', views.plans_list, name='plans_list'),
    path('my-subscription/', views.my_subscription, name='my_subscription'),
    path('manage/', views.subscriptions_list, name='subscriptions_list'),
]
