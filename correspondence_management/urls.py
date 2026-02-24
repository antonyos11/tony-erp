from django.urls import path
from . import views

app_name = 'correspondence_management'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
