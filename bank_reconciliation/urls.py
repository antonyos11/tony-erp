from django.urls import path
from . import views

app_name = 'bank_reconciliation'

urlpatterns = [
    path('', views.reconciliation_dashboard, name='dashboard'),
    
    # كشوف الحسابات
    path('statements/', views.statement_list, name='statement_list'),
    path('statements/upload/', views.statement_upload, name='statement_upload'),
    path('statements/<int:pk>/', views.statement_detail, name='statement_detail'),
    path('statements/<int:pk>/import/', views.statement_import_csv, name='statement_import'),
    path('statements/<int:pk>/auto-match/', views.auto_match, name='auto_match'),
    path('statements/line/<int:line_id>/match/', views.manual_match, name='manual_match'),
    
    # المطابقات
    path('reconciliations/', views.reconciliation_list, name='reconciliation_list'),
    path('reconciliations/create/', views.reconciliation_create, name='reconciliation_create'),
    path('reconciliations/<int:pk>/', views.reconciliation_detail, name='reconciliation_detail'),
    
    # التقارير
    path('reports/', views.reconciliation_report, name='reconciliation_report'),
]
