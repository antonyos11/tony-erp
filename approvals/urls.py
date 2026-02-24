from django.urls import path
from . import views

app_name = 'approvals'

urlpatterns = [
    path('', views.approval_list, name='list'),
    path('settings/', views.settings, name='settings'),
    path('<int:pk>/', views.approval_detail, name='detail'),
    path('<int:pk>/approve/', views.approve_request, name='approve'),
    path('<int:pk>/reject/', views.reject_request, name='reject'),
]