from django.urls import path
from . import views
from .views import create_requisition_for_order, material_requisition_quick_create
from . import views_reports
from . import views_scheduling
from . import views_lifecycle
from . import views_advanced_reports
from . import views_analytics
from . import views_units
from . import views_pipeline
from . import reports as production_reports

app_name = 'production'

urlpatterns = [
    # لوحة التحكم الرئيسية
    path('', views.production_dashboard, name='dashboard'),
    
    # لوحة متابعة الإنتاج للمصنع (شاشة تلفزيون)
    path('tv-dashboard/', views.production_tv_dashboard, name='tv_dashboard'),
    
    # لوحة التحكم المتكاملة الجديدة
    path('integrated-dashboard/', views_lifecycle.production_integrated_dashboard, name='integrated_dashboard'),
    
    # أوامر الإنتاج
    path('orders/', views.production_orders_list, name='orders_list'),
    path('orders/create/', views.create_production_order, name='create_order'),
    path('orders/<int:order_id>/', views.production_order_detail, name='order_detail'),
    path('orders/<int:order_id>/add-consumption/', views.add_material_consumption, name='add_consumption'),
    path('orders/<int:order_id>/work/', views.work_order_view, name='order_work'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    
    # وحدات المنتجات النهائية
    path('units/', views_units.unit_list, name='unit_list'),
    path('units/new/', views_units.unit_create, name='unit_create'),
    path('units/<int:pk>/', views_units.unit_detail, name='unit_detail'),
    path('units/<int:pk>/print/', views_units.unit_print_label, name='unit_print_label'),
    path('units/<int:pk>/update-status/', views_units.unit_update_status, name='unit_update_status'),
    path('units/<int:pk>/sell-dealer/', views_units.unit_sell_to_dealer, name='unit_sell_to_dealer'),
    path('units/<int:pk>/register-customer/', views_units.unit_register_customer, name='unit_register_customer'),
    path('units/print-batch/', views_units.unit_print_batch, name='unit_print_batch'),
    path('units/verify/', views_units.unit_verify_api, name='unit_verify_api'),
    path('orders/<int:order_id>/print-units/', views_units.unit_print_from_order, name='unit_print_from_order'),
    path('orders/<int:order_id>/generate-units/', views_units.unit_generate_labels, name='unit_generate_labels'),
    
    # تسجيل الضمان من المتجر
    path('warranty/verify/', views_units.warranty_verify_unit, name='warranty_verify_unit'),
    path('warranty/register/', views_units.warranty_register_unit, name='warranty_register_unit'),
    path('warranty/success/<int:pk>/', views_units.warranty_success, name='warranty_success'),
    path('warranty/claim/<int:unit_id>/', views_units.warranty_claim_unit, name='warranty_claim_unit'),
    
    # ===== خط أنابيب الإنتاج العالمي =====
    path('pipeline/', views_pipeline.pipeline_dashboard, name='pipeline_dashboard'),
    path('pipeline/api/data/', views_pipeline.pipeline_api_data, name='pipeline_api_data'),
    path('pipeline/create/<int:order_id>/', views_pipeline.pipeline_create_board, name='pipeline_create_board'),
    path('pipeline/stage/<int:stage_id>/start/', views_pipeline.pipeline_start_stage, name='pipeline_start_stage'),
    path('pipeline/stage/<int:stage_id>/complete/', views_pipeline.pipeline_complete_stage, name='pipeline_complete_stage'),
    path('pipeline/stage/<int:stage_id>/fail/', views_pipeline.pipeline_fail_stage, name='pipeline_fail_stage'),
    path('pipeline/stage/<int:stage_id>/reprint/', views_pipeline.pipeline_reprint, name='pipeline_reprint'),
    
    # دورة حياة الإنتاج المتكاملة
    path('orders/<int:order_id>/start/', views_lifecycle.start_production_order_view, name='start_order'),
    path('orders/<int:order_id>/record-output/', views_lifecycle.record_production_output_view, name='record_output'),
    path('orders/<int:order_id>/complete/', views_lifecycle.complete_production_order_view, name='complete_order'),
    path('orders/<int:order_id>/generate-barcodes/', views_lifecycle.generate_barcodes_view, name='generate_barcodes'),
    path('orders/<int:order_id>/print-barcodes/', views_lifecycle.print_barcodes_view, name='print_barcodes'),
    path('orders/bulk-start/', views_lifecycle.bulk_start_orders_view, name='bulk_start_orders'),
    
    # API endpoints للإنتاج المتكامل
    path('api/orders/<int:order_id>/status/', views_lifecycle.production_order_status_api, name='order_status_api'),
    path('api/orders/<int:order_id>/materials/', views_lifecycle.check_materials_availability_api, name='check_materials_api'),
    path('api/orders/<int:order_id>/variance/', views_lifecycle.production_cost_variance_api, name='cost_variance_api'),
    
    # مراكز العمل
    path('work-centers/', views.work_centers_list, name='work_centers_list'),
    path('work-centers/create/', views.work_center_create, name='work_center_create'),
    path('work-centers/<int:work_center_id>/', views.work_center_detail, name='work_center_detail'),
    path('work-centers/<int:work_center_id>/edit/', views.work_center_edit, name='work_center_edit'),
    
    # تقويم الإنتاج
    path('calendar/', views.production_calendar, name='calendar'),
    
    # لوحة العامل
    path('worker-dashboard/', views.worker_dashboard, name='worker_dashboard'),
    
    # الجودة
    path('quality/', views.quality_dashboard, name='quality_dashboard'),
    
    # تحليل التكاليف
    path('cost-analysis/', views.cost_analysis_view, name='cost_analysis'),
    path('product-costing/', views.product_costing_view, name='product_costing'),
    path('product-costing/export/', views.product_costing_csv, name='product_costing_csv'),
    # الهالك والتكلفة
    path('waste-and-costs/', views.waste_and_costs_dashboard, name='waste_and_costs'),
    path('waste-and-costs/export/', views.waste_and_costs_csv, name='waste_and_costs_csv'),
    
    # التنبيهات
    path('alerts/', views.production_alerts_list, name='alerts_list'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    
    # التقارير
    path('reports/', views.production_reports_list, name='reports_list'),
    
    # AJAX endpoints
    path('api/products/<int:product_id>/boms/', views.get_product_boms, name='get_product_boms'),
    path('api/products/<int:product_id>/uom/', views.get_product_uom, name='get_product_uom'),

    # أدلة وإرشادات الإنتاج
    path('safety/', views.safety_guidelines, name='safety'),
    path('safety/export/', views.safety_export_csv, name='safety_export_csv'),
    path('time-motion/', views.time_motion_guide, name='time_motion'),
    path('time-motion/export/', views.time_motion_export_csv, name='time_motion_export_csv'),

    # إذن صرف خامات للإنتاج (روابط سريعة تعتمد على شاشات المخازن)
    # تنشئ مستند صرف (Issue) موجه إلى وحدة الإنتاج ثم تعيد التوجيه لشاشة تفاصيل الصرف في المخازن لاستكمال البنود والطباعة
    path('material-issues/new/', views.material_issue_quick_create, name='material_issue_quick_create'),
    path('orders/<int:order_id>/material-issue/', views.create_issue_for_order, name='create_issue_for_order'),
    # إذن طلب خامات (Requisition) من أمر إنتاج مع تعبئة من الـ BOM
    path('orders/<int:order_id>/material-requisition/', create_requisition_for_order, name='create_requisition_for_order'),
    # إنشاء طلب خامات سريع من الإنتاج
    path('material-requisitions/new/', material_requisition_quick_create, name='material_requisition_quick_create'),
    
    # بوابة العمال
    path('worker-portal/', views.worker_portal, name='worker_portal'),
    path('worker-portal/production-entry/', views.worker_production_entry, name='worker_production_entry'),
    path('worker-portal/production-history/', views.worker_production_history, name='worker_production_history'),
    path('supervisor/approvals/', views.supervisor_production_approvals, name='supervisor_approvals'),
    
    # التقارير والـ KPIs
    path('reports/product-cost/', views_reports.product_cost_report, name='product_cost_report'),
    path('reports/all-products-cost/', views_reports.all_products_cost_summary, name='all_products_cost_summary'),
    path('reports/worker-productivity/', views_reports.worker_productivity_report, name='worker_productivity_report'),
    path('reports/factory-dashboard/', views_reports.factory_owner_dashboard, name='factory_owner_dashboard'),
    
    # التقارير المتقدمة (التكامل الكامل)
    path('reports/integration/', views_advanced_reports.production_integration_report, name='integration_report'),
    path('reports/cost-variance/', views_advanced_reports.cost_variance_report, name='cost_variance_report'),
    path('reports/material-consumption/', views_advanced_reports.material_consumption_report, name='material_consumption_report'),
    path('reports/productivity-quality/', views_advanced_reports.productivity_quality_report, name='productivity_quality_report'),
    path('reports/integration/export/', views_advanced_reports.export_integration_report_csv, name='export_integration_csv'),
    
    # نظام الجدولة التلقائية (المرحلة 2)
    path('scheduling/', views_scheduling.scheduling_dashboard, name='scheduling_dashboard'),
    path('scheduling/auto-schedule/', views_scheduling.auto_schedule_orders, name='auto_schedule_orders'),
    path('scheduling/gantt/', views_scheduling.gantt_chart_view, name='gantt_chart_view'),
    path('scheduling/capacity-analysis/', views_scheduling.capacity_analysis_view, name='capacity_analysis'),
    path('scheduling/reschedule/<int:order_id>/', views_scheduling.reschedule_order, name='reschedule_order'),
    path('scheduling/optimize/', views_scheduling.optimize_schedule_view, name='optimize_schedule'),
    path('scheduling/api/check-conflicts/', views_scheduling.check_conflicts_ajax, name='check_conflicts_ajax'),
    
    # التحليلات المتقدمة والذكاء الاصطناعي
    path('analytics/', views_analytics.production_analytics_dashboard, name='analytics_dashboard'),
    path('analytics/oee/', views_analytics.oee_dashboard, name='oee_dashboard'),
    path('analytics/workers/', views_analytics.worker_performance_report, name='worker_performance_report'),
    path('analytics/materials/', views_analytics.material_efficiency_report, name='material_efficiency_report'),
    
    # API التحليلات
    path('api/analytics/kpis/', views_analytics.production_kpis_api, name='kpis_api'),
    path('api/analytics/demand/<int:product_id>/', views_analytics.demand_prediction_api, name='demand_prediction_api'),
    path('api/analytics/bottlenecks/', views_analytics.bottlenecks_api, name='bottlenecks_api'),
    path('api/analytics/suggestions/', views_analytics.optimization_suggestions_api, name='suggestions_api'),
    
    # الصفحات المتقدمة الإضافية
    path('advanced/', views.advanced_dashboard, name='advanced_dashboard'),
    path('work-orders/', views.work_orders_list, name='work_orders_list'),
    path('stages/', views.production_stages_list, name='stages_list'),
    path('stages/create/', views.stage_create, name='stage_create'),
    path('training-components/', views.training_components_list, name='training_components'),
    path('quality-control/', views.quality_control_dashboard, name='quality_control'),
    path('optimization/', views.production_optimization, name='optimization'),
    
    # تقارير إضافية
    path('reports/manufacturing/', views.manufacturing_report, name='manufacturing_report'),
    path('reports/production-cost/', views.production_cost_report, name='production_cost_report'),
    path('reports/quantities/', views.quantities_report, name='quantities_report'),
    path('reports/waste/', views.waste_report, name='waste_report'),
    path('reports/profitability/', views.profitability_report, name='profitability_report'),
    path('reports/labor/', views.labor_report, name='labor_report'),
    path('reports/machine-efficiency/', views.machine_efficiency_report, name='machine_efficiency_report'),
    path('reports/indirect-costs/', views.indirect_costs_report, name='indirect_costs_report'),
    
    # =============================
    # روابط إضافية للتوافق مع القوالب
    # =============================
    # Aliases لتوحيد أسماء URLs
    path('bom/', views.bom_list, name='bom_list'),  # قائمة BOMs
    path('orders-list/', views.production_orders_list, name='order_list'),  # alias
    path('order/create/', views.create_production_order, name='order_create'),  # alias
    path('work-center/', views.work_centers_list, name='work_center_list'),  # alias
    path('workers/', views.workers_list, name='workers_list'),  # قائمة العمال
    path('scheduling/list/', views_scheduling.scheduling_dashboard, name='scheduling_list'),  # alias
    
    # =============================
    # تقارير الإنتاج المحسنة
    # =============================
    path('reports/daily/', production_reports.production_daily_report, name='daily_report'),
    path('reports/monthly/', production_reports.production_monthly_report, name='monthly_report'),
    path('reports/material-consumption/', production_reports.production_material_consumption_report, name='material_consumption_detailed'),
    path('reports/efficiency/', production_reports.production_efficiency_report, name='efficiency_report'),
]

# --- Advanced Production URLs ---
from production import views_advanced as prod_adv  # noqa: E402

urlpatterns += [
    # خطوط الإنتاج
    path('lines/', prod_adv.production_line_list, name='production_line_list'),
    path('lines/create/', prod_adv.production_line_create, name='production_line_create'),
    path('lines/<int:pk>/edit/', prod_adv.production_line_edit, name='production_line_edit'),
    path('lines/<int:pk>/delete/', prod_adv.production_line_delete, name='production_line_delete'),

    # جدولة الإنتاج
    path('schedules/', prod_adv.schedule_list, name='schedule_list'),
    path('schedules/create/', prod_adv.schedule_create, name='schedule_create'),
    path('schedules/<int:pk>/', prod_adv.schedule_detail, name='schedule_detail'),
    path('schedules/<int:pk>/edit/', prod_adv.schedule_edit, name='schedule_edit'),

    # انحرافات التكلفة
    path('cost-variances/', prod_adv.cost_variance_list, name='cost_variance_list'),
    path('cost-variances/<int:pk>/', prod_adv.cost_variance_detail, name='cost_variance_detail'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('order-edit/<int:pk>/', stub_view, name='order_edit'),
    path('stage-detail/<int:pk>/', stub_view, name='stage_detail'),
]
