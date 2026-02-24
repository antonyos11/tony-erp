from django.urls import path
from . import views

app_name = 'printing'

urlpatterns = [
    # Dashboard - لوحة التحكم
    path('', views.printing_dashboard, name='dashboard'),

    # Printer Settings - إعدادات الطابعات
    path('settings/', views.printer_settings, name='printer_settings'),
    path('settings/set-default/', views.printer_set_default, name='printer_set_default'),

    # Warranty labels (existing) - ملصقات الضمان
    path('warranty/<int:unit_id>/json/', views.warranty_label_json, name='warranty_label_json'),
    path('warranty/<int:unit_id>/zpl/', views.warranty_label_zpl, name='warranty_label_zpl'),
    path('warranty/<int:unit_id>/escpos/', views.warranty_label_escpos, name='warranty_label_escpos'),

    # Unified Print API - واجهة الطباعة الموحدة
    path('api/print/', views.api_print_document, name='api_print_document'),
    path('api/print/trial-balance/', views.api_print_trial_balance, name='api_print_trial_balance'),
    path('api/reprint/<uuid:job_id>/', views.api_reprint_job, name='api_reprint_job'),
    path('api/status/', views.api_agent_status, name='api_agent_status'),
    path('api/job/<uuid:job_id>/', views.api_job_status, name='api_job_status'),
    path('api/download/<uuid:job_id>/', views.api_download_fallback, name='api_download_fallback'),
    path('api/jobs/', views.api_recent_jobs, name='api_recent_jobs'),
    path('api/test-print/', views.api_test_print, name='api_test_print'),

    # Station Mapping — Dynamic dropdown UI + APIs
    path('station-mapping/', views.station_mapping_view, name='station_mapping'),
    path('api/station/<uuid:station_id>/printers/', views.api_station_live_printers, name='api_station_live_printers'),
    path('api/station/<uuid:station_id>/test-printer/', views.api_test_station_printer, name='api_test_station_printer'),
    path('api/station/<uuid:station_id>/save-mapping/', views.api_save_printer_mapping, name='api_save_printer_mapping'),
]
