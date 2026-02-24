from django.urls import path
from . import views

app_name = 'intellectual_property'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
