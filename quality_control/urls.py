from django.urls import path
from . import views

app_name = 'quality_control'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('inspections/', views.inspection_list, name='inspection_list'),
    path('inspections/create/', views.inspection_create, name='inspection_create'),
    path('inspections/<int:pk>/', views.inspection_detail, name='inspection_detail'),
    path('issues/', views.issue_list, name='issue_list'),
    path('issues/create/', views.issue_create, name='issue_create'),
    path('issues/<int:pk>/', views.issue_detail, name='issue_detail'),
    path('standards/', views.standard_list, name='standard_list'),
    path('standards/create/', views.standard_create, name='standard_create'),
    
    # Product Traceability - Fix 404
    path('traceability/', views.traceability_dashboard, name='traceability_dashboard'),
    path('traceability/search/', views.traceability_search, name='traceability_search'),
    path('traceability/batch/<str:batch_number>/', views.batch_trace, name='batch_trace'),
    path('traceability/serial/<str:serial_number>/', views.serial_trace, name='serial_trace'),
]
