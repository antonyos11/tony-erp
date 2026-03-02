"""
URLs التقارير — RITA ERP
Sprint 7 + Sprint 22B
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('sales-summary/', views.SalesSummaryView.as_view(), name='sales_summary'),
    path('sales-by-product/', views.SalesByProductView.as_view(), name='sales_by_product'),
    path('sales-by-customer/', views.SalesByCustomerView.as_view(), name='sales_by_customer'),
    path('sales-by-salesperson/', views.SalesBySalespersonView.as_view(), name='sales_by_salesperson'),
    path('profitability/', views.ProfitabilityView.as_view(), name='profitability'),
    path('stock-movement/', views.StockMovementView.as_view(), name='stock_movement'),
    path('dead-stock/', views.DeadStockView.as_view(), name='dead_stock'),
    path('reorder/', views.ReorderView.as_view(), name='reorder'),
    path('product-cost/', views.ProductCostView.as_view(), name='product_cost'),
    path('cost-variance/', views.CostVarianceView.as_view(), name='cost_variance'),
    path('branch-scorecard/', views.BranchScorecardView.as_view(), name='branch_scorecard'),
    path('aging/', views.AgingView.as_view(), name='aging'),
    path('vat/', views.VATReportView.as_view(), name='vat_report'),
    # تقارير Sprint 20
    path('sales-daily/', views.DailySalesView.as_view(), name='sales_daily'),
    path('customer-balance/', views.CustomerBalanceView.as_view(), name='customer_balance'),
    path('supplier-balance/', views.SupplierBalanceView.as_view(), name='supplier_balance'),
    path('cash-flow/', views.CashFlowView.as_view(), name='cash_flow'),
    path('expense-summary/', views.ExpenseSummaryView.as_view(), name='expense_summary'),
    path('production-summary/', views.ProductionSummaryView.as_view(), name='production_summary'),
    path('hr-summary/', views.HRSummaryView.as_view(), name='hr_summary'),
    path('attendance/', views.AttendanceReportView.as_view(), name='attendance_report'),
    # Sprint 22B — أعمار الديون + الربحية متعددة الأبعاد
    path('customer-aging/', views.CustomerAgingView.as_view(), name='customer_aging'),
    path('supplier-aging/', views.SupplierAgingView.as_view(), name='supplier_aging'),
    path('profitability/by-product/', views.ProfitByProductView.as_view(), name='profit_by_product'),
    path('profitability/by-branch/', views.ProfitByBranchView.as_view(), name='profit_by_branch'),
    path('profitability/by-customer/', views.ProfitByCustomerView.as_view(), name='profit_by_customer'),
    path('profitability/by-channel/', views.ProfitByChannelView.as_view(), name='profit_by_channel'),
]
