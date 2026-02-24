from django.urls import path
from . import views

app_name = 'advanced_notifications'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
