from django.urls import path
from . import views

app_name = 'fleet'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicles/new/', views.vehicle_create, name='vehicle_create'),
    path('vehicles/<int:pk>/edit/', views.vehicle_update, name='vehicle_update'),
    path('vehicles/<int:pk>/delete/', views.vehicle_delete, name='vehicle_delete'),
    path('drivers/', views.driver_list, name='driver_list'),
    path('drivers/new/', views.driver_create, name='driver_create'),
    path('drivers/<int:pk>/edit/', views.driver_update, name='driver_update'),
    path('drivers/<int:pk>/delete/', views.driver_delete, name='driver_delete'),
    path('trips/', views.trip_list, name='trip_list'),
    path('trips/new/', views.trip_create, name='trip_create'),
    path('trips/<int:pk>/edit/', views.trip_update, name='trip_update'),
    path('trips/<int:pk>/close/', views.trip_close, name='trip_close'),
    path('trips/<int:pk>/delete/', views.trip_delete, name='trip_delete'),
    # maintenance (vehicle maintenance-focused view)
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/new/', views.maintenance_create, name='maintenance_create'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/new/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_update, name='expense_update'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('documents/', views.documents_upload, name='documents_upload'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
    path('performance/drivers/', views.driver_performance, name='driver_performance'),
    path('reports/distance/', views.distance_report, name='distance_report'),
    # violations
    path('violations/', views.violation_list, name='violation_list'),
    path('violations/new/', views.violation_create, name='violation_create'),
    path('violations/<int:pk>/edit/', views.violation_update, name='violation_update'),
    path('violations/<int:pk>/delete/', views.violation_delete, name='violation_delete'),
    # advances
    path('advances/', views.advance_list, name='advance_list'),
    path('advances/new/', views.advance_create, name='advance_create'),
    path('advances/<int:pk>/edit/', views.advance_update, name='advance_update'),
    path('advances/<int:pk>/delete/', views.advance_delete, name='advance_delete'),
        path('advances/<int:pk>/settle/', views.advance_settle, name='advance_settle'),
    
    # أنواع المركبات والإعدادات
    path('vehicle-types/', views.vehicle_type_list, name='vehicle_type_list'),
    path('vehicle-handover/', views.vehicle_handover_list, name='vehicle_handover_list'),
    path('garages/', views.garage_list, name='garage_list'),
    path('holidays/', views.holiday_list, name='holiday_list'),
    path('spare-parts/', views.spare_part_list, name='spare_part_list'),
    path('maintenance-types/', views.maintenance_type_list, name='maintenance_type_list'),
    path('expense-types/', views.expense_type_list, name='expense_type_list'),
    path('unified-expenses/', views.unified_expense_list, name='unified_expense_list'),
    path('maintenance-permissions/', views.maintenance_permission_list, name='maintenance_permission_list'),
    path('spare-parts-permissions/', views.spare_parts_permission_list, name='spare_parts_permission_list'),
    path('oil-types/', views.oil_type_list, name='oil_type_list'),
    path('maintenance-alerts/', views.maintenance_alert_list, name='maintenance_alert_list'),
    path('odometer-adjustments/', views.odometer_adjustment_list, name='odometer_adjustment_list'),
    
    # الوقود
    path('fuel/', views.fuel_list, name='fuel_list'),
    path('fuel/import/', views.fuel_import, name='fuel_import'),
    path('fuel/stations/', views.fuel_station_list, name='fuel_station_list'),
    path('fuel/reports/', views.fuel_reports, name='fuel_reports'),
    
    # النقليات
    path('transfers/bills/', views.transfer_bill_list, name='transfer_bill_list'),
    path('transfers/reports/', views.transfer_reports, name='transfer_reports'),
    
    # الكاوش (الإطارات)
    path('tire-brands/', views.tire_brand_list, name='tire_brand_list'),
    path('tire-inventory/', views.tire_inventory_list, name='tire_inventory_list'),
    path('tire-movements/', views.tire_movement_list, name='tire_movement_list'),
    path('tire-pressure/', views.tire_pressure_list, name='tire_pressure_list'),
    path('tire-maintenance/', views.tire_maintenance_list, name='tire_maintenance_list'),
    path('tire-performance/', views.tire_performance_report, name='tire_performance_report'),
    path('tire-comparison/', views.tire_comparison_report, name='tire_comparison_report'),
    path('tire-low-stock/', views.tire_low_stock, name='tire_low_stock'),
    path('tire-overdue/', views.tire_overdue, name='tire_overdue'),
    
    # تقارير إضافية
    path('reports/fuel/', views.fuel_report, name='fuel_report'),
    path('reports/maintenance/', views.maintenance_report, name='maintenance_report'),
    path('reports/working-days/', views.working_days_report, name='working_days_report'),
    path('reports/driver-performance/', views.driver_performance_report, name='driver_performance_report'),
    path('reports/load-comparison/', views.load_comparison_report, name='load_comparison_report'),
    path('reports/oil-status/', views.oil_status_report, name='oil_status_report'),
]
