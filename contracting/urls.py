"""
URLs for Contracting App - مسارات نظام المقاولات
"""

from django.urls import path
from . import views

app_name = 'contracting'

urlpatterns = [
    # Homepage redirect
    path('', views.dashboard, name='index'),
    
    # Dashboard - لوحة التحكم
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Projects - المشاريع
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    
    # Workers - العمال
    path('workers/', views.worker_list, name='worker_list'),
    path('workers/create/', views.worker_create, name='worker_create'),
    path('workers/<int:pk>/', views.worker_detail, name='worker_detail'),
    
    # Attendance - الحضور والانصراف
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/create/', views.attendance_create, name='attendance_create'),
    path('attendance/report/', views.attendance_report, name='attendance_report'),
    
    # Materials - المواد
    path('materials/', views.material_list, name='material_list'),
    path('materials/create/', views.material_create, name='material_create'),
    
    # Equipment - المعدات
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/create/', views.equipment_create, name='equipment_create'),
    
    # Expenses - المصروفات
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    
    # Receipts - المقبوضات
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/create/', views.receipt_create, name='receipt_create'),
    
    # Contracts - العقود
    path('contracts/', views.contract_list, name='contract_list'),
    path('contracts/create/', views.contract_create, name='contract_create'),
    path('contracts/<int:pk>/', views.contract_detail, name='contract_detail'),
    
    # Reports - التقارير
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/daily/', views.daily_report, name='daily_report'),
    path('reports/customers/', views.customers_report, name='customers_report'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('contractor-create/', stub_view, name='contractor_create'),
]
