from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import views_builder

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard, name='dashboard'),
    path('sales/', views.sales_report, name='sales_report'),
    path('inventory/', views.inventory_report, name='inventory_report'),
    path('purchases/', views.purchases_report, name='purchases_report'),
    
    # تقارير عامة - كل تقرير له صفحة مخصصة
    path('account-statement/', views.account_statement_report, name='account_statement'),
    path('customer-debts/', views.customer_debts_report, name='customer_debts'),
    path('supplier-debts/', views.supplier_debts_report, name='supplier_debts'),
    path('sales-representatives/', views.sales_representatives_report, name='sales_representatives'),
    path('top-selling/', views.top_selling_report, name='top_selling_products'),
    path('least-selling/', views.least_selling_report, name='least_selling_products'),
    path('customer-details/', views.customer_details_report, name='customer_details'),
    path('supplier-details/', views.supplier_details_report, name='supplier_details'),
    path('daily-expenses/', views.daily_expenses_report, name='daily_expenses'),
    path('comprehensive/', views.comprehensive_report, name='comprehensive'),
    path('product-price-comparison/', views.price_comparison_report, name='product_price_comparison'),
    path('monthly-sales-comparison/', views.monthly_sales_comparison_report, name='monthly_sales_comparison'),
    path('sales-rep-summary/', views.sales_rep_summary_report, name='sales_rep_summary'),
    path('sales-and-cost/', views.sales_and_cost_report, name='sales_and_cost'),
    path('equipment-usage/', views.equipment_usage_report, name='equipment_usage'),
    path('equipment-maintenance/', views.equipment_maintenance_report, name='equipment_maintenance'),
    path('material-consumption/', views.material_consumption_report, name='material_consumption'),
    
    # Report Builder URLs
    path('builder/', views_builder.report_builder_dashboard, name='builder_dashboard'),
    path('builder/create/', views_builder.create_report_template, name='create_template'),
    path('builder/edit/<int:template_id>/', views_builder.edit_report_template, name='edit_template'),
    path('builder/preview/<int:template_id>/', views_builder.preview_report, name='preview_report'),
    path('builder/execute/<int:template_id>/', views_builder.execute_report, name='execute_report'),
    path('builder/download/<int:execution_id>/', views_builder.download_report, name='download_report'),
    path('builder/history/', views_builder.execution_history, name='execution_history'),
    path('builder/delete/<int:template_id>/', views_builder.delete_template, name='delete_template'),
    path('builder/schedule/<int:template_id>/', views_builder.schedule_report, name='schedule_report'),
    
    # AJAX APIs
    path('api/model-fields/', views_builder.get_model_fields, name='api_model_fields'),
    path('api/validate-config/', views_builder.validate_report_config, name='api_validate_config'),
    path('api/duplicate/<int:template_id>/', views_builder.duplicate_template, name='api_duplicate_template'),
]