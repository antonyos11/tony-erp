from django.urls import path
from . import views

app_name = 'loyalty'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('programs/', views.program_list, name='program_list'),
    path('programs/create/', views.program_create, name='program_create'),
    path('members/', views.member_list, name='member_list'),
    path('members/<int:pk>/', views.member_detail, name='member_detail'),
    path('rewards/', views.reward_list, name='reward_list'),
    path('rewards/create/', views.reward_create, name='reward_create'),
    path('transactions/', views.transaction_list, name='transaction_list'),
]
