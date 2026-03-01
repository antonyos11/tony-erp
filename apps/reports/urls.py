"""
URLs التقارير — RITA ERP
Sprint 7
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
]
