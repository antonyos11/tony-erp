"""
URLs لإدارة المشاريع
"""
from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Projects CRUD
    path('list/', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    
    # Project Types
    path('types/', views.type_list, name='type_list'),
    path('types/create/', views.type_create, name='type_create'),
    
    # Project Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    
    # Adjustments
    path('adjustments/', views.adjustment_list, name='adjustment_list'),
    
    # BOQ - Bill of Quantities
    path('boq/', views.boq_list, name='boq_list'),
    
    # Plans
    path('plans/', views.project_plans, name='plans'),
    
    # Quantities
    path('quantities/', views.project_quantities, name='quantities'),
    
    # Owner Statements
    path('owner-statements/', views.owner_statements, name='owner_statements'),
    
    # Purchase Orders
    path('purchase-orders/', views.purchase_orders, name='purchase_orders'),
    
    # Estimations
    path('estimations/', views.estimations, name='estimations'),
    
    # Contracts
    path('contracts/', views.contracts, name='contracts'),
    
    # Contractors
    path('contractors/', views.contractor_list, name='contractor_list'),
    path('contractors/create/', views.contractor_create, name='contractor_create'),
    path('contractors/contracts/', views.contractor_contracts, name='contractor_contracts'),
    path('contractors/statements/', views.contractor_statements, name='contractor_statements'),
    
    # Labour
    path('labour/', views.labour_list, name='labour_list'),
    path('labour/attendance/', views.labour_attendance, name='labour_attendance'),
    path('labour/attendance/create/', views.labour_attendance_create, name='labour_attendance_create'),
    path('labour/attendance/report/', views.labour_attendance_report, name='labour_attendance_report'),
    
    # Finance
    path('finance/mandates/', views.finance_mandates, name='finance_mandates'),
    path('finance/expenses/', views.finance_expenses, name='finance_expenses'),
    path('finance/invoices/', views.finance_invoices, name='finance_invoices'),
    
    # Reports
    path('reports/overview/', views.reports_overview, name='reports_overview'),
    path('reports/stats/', views.reports_stats, name='reports_stats'),
    path('reports/progress/', views.reports_progress, name='reports_progress'),
    path('reports/costs/', views.reports_costs, name='reports_costs'),
    path('reports/contractors/', views.reports_contractors, name='reports_contractors'),
    path('reports/labour-statements/', views.reports_labour_statements, name='reports_labour_statements'),
]
