from django.urls import path
from . import views
from . import views_preventive

app_name = 'maintenance'

urlpatterns = [
    # الصفحة الرئيسية للصيانة
    path('', views.maintenance_dashboard, name='dashboard'),
    
    # الماكينات
    path('machines/', views.machine_list, name='machine_list'),
    path('machines/add/', views.machine_add, name='machine_add'),
    path('machines/<int:pk>/', views.machine_detail, name='machine_detail'),
    path('machines/<int:pk>/edit/', views.machine_edit, name='machine_edit'),
    path('machines/<int:pk>/delete/', views.machine_delete, name='machine_delete'),
    path('machines/<int:pk>/qr-code/', views.machine_qr_code, name='machine_qr_code'),
    
    # فئات الماكينات
    path('machine-categories/', views.machine_category_list, name='machine_category_list'),
    path('machine-categories/add/', views.machine_category_add, name='machine_category_add'),
    path('machine-categories/<int:pk>/edit/', views.machine_category_edit, name='machine_category_edit'),
    
    # قطع الغيار
    path('spare-parts/', views.spare_part_list, name='spare_part_list'),
    path('spare-parts/add/', views.spare_part_add, name='spare_part_add'),
    path('spare-parts/<int:pk>/', views.spare_part_detail, name='spare_part_detail'),
    path('spare-parts/<int:pk>/edit/', views.spare_part_edit, name='spare_part_edit'),
    path('spare-parts/<int:pk>/delete/', views.spare_part_delete, name='spare_part_delete'),
    path('spare-parts/low-stock/', views.spare_part_low_stock, name='spare_part_low_stock'),
    
    # أنواع الصيانة
    path('maintenance-types/', views.maintenance_type_list, name='maintenance_type_list'),
    path('maintenance-types/add/', views.maintenance_type_add, name='maintenance_type_add'),
    path('maintenance-types/<int:pk>/edit/', views.maintenance_type_edit, name='maintenance_type_edit'),
    
    # طلبات الصيانة
    path('requests/', views.maintenance_request_list, name='maintenance_request_list'),
    path('requests/list/', views.maintenance_request_list, name='requests_list'),
    path('requests/add/', views.maintenance_request_add, name='maintenance_request_add'),
    path('requests/<int:pk>/', views.maintenance_request_detail, name='maintenance_request_detail'),
    path('requests/<int:pk>/edit/', views.maintenance_request_edit, name='maintenance_request_edit'),
    path('requests/<int:pk>/approve/', views.maintenance_request_approve, name='maintenance_request_approve'),
    path('requests/<int:pk>/start/', views.maintenance_request_start, name='maintenance_request_start'),
    path('requests/<int:pk>/complete/', views.maintenance_request_complete, name='maintenance_request_complete'),
    path('requests/<int:pk>/cancel/', views.maintenance_request_cancel, name='maintenance_request_cancel'),
    
    # جدولة الصيانة
    path('schedules/', views.maintenance_schedule_list, name='maintenance_schedule_list'),
    path('schedules/add/', views.maintenance_schedule_add, name='maintenance_schedule_add'),
    path('schedules/<int:pk>/', views.maintenance_schedule_detail, name='maintenance_schedule_detail'),
    path('schedules/<int:pk>/edit/', views.maintenance_schedule_edit, name='maintenance_schedule_edit'),
    path('schedules/generate-requests/', views.generate_maintenance_requests, name='generate_maintenance_requests'),
    
    # سجلات الصيانة
    path('records/', views.maintenance_record_list, name='maintenance_record_list'),
    path('records/add/', views.maintenance_record_add, name='maintenance_record_add'),
    path('records/<int:pk>/', views.maintenance_record_detail, name='maintenance_record_detail'),
    path('records/<int:pk>/edit/', views.maintenance_record_edit, name='maintenance_record_edit'),
    path('records/<int:pk>/print/', views.maintenance_record_print, name='maintenance_record_print'),
    
    # قوائم الفحص
    path('checklists/', views.maintenance_checklist_list, name='maintenance_checklist_list'),
    path('checklists/add/', views.maintenance_checklist_add, name='maintenance_checklist_add'),
    path('checklists/<int:pk>/edit/', views.maintenance_checklist_edit, name='maintenance_checklist_edit'),
    
    # التقارير
    path('reports/', views.maintenance_reports, name='reports'),
    path('reports/machine-history/<int:machine_id>/', views.machine_maintenance_history, name='machine_maintenance_history'),
    path('reports/cost-analysis/', views.maintenance_cost_analysis, name='maintenance_cost_analysis'),
    path('reports/performance/', views.maintenance_performance_report, name='maintenance_performance_report'),
    path('reports/spare-parts-usage/', views.spare_parts_usage_report, name='spare_parts_usage_report'),
    
    # التنبيهات
    path('alerts/', views.maintenance_alerts, name='alerts'),
    path('alerts/overdue/', views.overdue_maintenance, name='overdue_maintenance'),
    path('alerts/upcoming/', views.upcoming_maintenance, name='upcoming_maintenance'),
    
    # API endpoints
    path('api/machines/search/', views.api_machine_search, name='api_machine_search'),
    path('api/spare-parts/search/', views.api_spare_part_search, name='api_spare_part_search'),
    path('api/maintenance/calendar/', views.api_maintenance_calendar, name='api_maintenance_calendar'),
    
    # نظام الصيانة الوقائية المتقدم (المرحلة 2)
    path('preventive/', views_preventive.preventive_maintenance_dashboard, name='preventive_dashboard'),
    path('preventive/generate-requests/', views_preventive.generate_maintenance_requests_view, name='generate_requests'),
    path('preventive/schedules/', views_preventive.maintenance_schedules_list, name='schedules_list'),
    path('preventive/schedules/create/', views_preventive.create_maintenance_schedule, name='create_schedule'),
    path('preventive/machine/<int:machine_id>/history/', views_preventive.machine_maintenance_history, name='machine_history'),
    path('preventive/cost-report/', views_preventive.maintenance_cost_report, name='cost_report'),
    path('preventive/cost-report/export/', views_preventive.export_cost_report_csv, name='cost_report_csv'),
    path('preventive/alerts/', views_preventive.alerts_notifications_view, name='alerts_notifications'),
    path('preventive/efficiency-report/', views_preventive.machine_efficiency_report, name='efficiency_report'),
    path('preventive/api/update-schedule-status/', views_preventive.update_schedule_status_ajax, name='update_schedule_status'),
]
# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('machine-category-delete/<int:pk>/', stub_view, name='machine_category_delete'),
    path('maintenance-request-create/', stub_view, name='maintenance_request_create'),
    path('spare-part-adjust-stock/', stub_view, name='spare_part_adjust_stock'),
    path('spare-part-create/', stub_view, name='spare_part_create'),
    path('spare-part-import/', stub_view, name='spare_part_import'),
]
