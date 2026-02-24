from django.urls import path
from . import views

app_name = 'budgeting'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('fiscal-years/', views.fiscal_year_list, name='fiscal_year_list'),
    path('fiscal-years/create/', views.fiscal_year_create, name='fiscal_year_create'),
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/create/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/', views.budget_detail, name='budget_detail'),
    path('budgets/<int:pk>/edit/', views.budget_edit, name='budget_edit'),
    path('variance-report/', views.variance_report, name='variance_report'),
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<int:pk>/mark-read/', views.mark_alert_read, name='mark_alert_read'),
]
