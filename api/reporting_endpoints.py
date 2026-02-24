from django.urls import path

from .reporting_views import (
    ReportsOverviewAPI, SalesReportAPI, InventoryReportAPI, PurchasesReportAPI,
    FullSystemReportAPI, ProfitLossReportAPI, ARAgingReportAPI, CRMPipelineReportAPI,
    APAgingReportAPI, BalanceSheetAPI, CashFlowReportAPI, InventoryTurnoverReportAPI, StockAgingReportAPI,
    SnapshotSeriesAPI, ReportsHealthAPI, ReportsVarianceIncidentsAPI
)

# Shared report URL patterns (with and without trailing slash for leniency)
report_urlpatterns = [
    path('reports/overview/', ReportsOverviewAPI.as_view(), name='reports-overview'),
    path('reports/overview', ReportsOverviewAPI.as_view()),
    path('reports/full/', FullSystemReportAPI.as_view(), name='reports-full-system'),
    path('reports/full', FullSystemReportAPI.as_view()),
    path('reports/sales/', SalesReportAPI.as_view(), name='reports-sales'),
    path('reports/sales', SalesReportAPI.as_view()),
    path('reports/inventory/', InventoryReportAPI.as_view(), name='reports-inventory'),
    path('reports/inventory', InventoryReportAPI.as_view()),
    path('reports/purchases/', PurchasesReportAPI.as_view(), name='reports-purchases'),
    path('reports/purchases', PurchasesReportAPI.as_view()),
    path('reports/profit-loss/', ProfitLossReportAPI.as_view(), name='reports-profit-loss'),
    path('reports/profit-loss', ProfitLossReportAPI.as_view()),
    path('reports/ar-aging/', ARAgingReportAPI.as_view(), name='reports-ar-aging'),
    path('reports/ar-aging', ARAgingReportAPI.as_view()),
    path('reports/crm-pipeline/', CRMPipelineReportAPI.as_view(), name='reports-crm-pipeline'),
    path('reports/crm-pipeline', CRMPipelineReportAPI.as_view()),
    path('reports/ap-aging/', APAgingReportAPI.as_view(), name='reports-ap-aging'),
    path('reports/ap-aging', APAgingReportAPI.as_view()),
    path('reports/balance-sheet/', BalanceSheetAPI.as_view(), name='reports-balance-sheet'),
    path('reports/balance-sheet', BalanceSheetAPI.as_view()),
    path('reports/cash-flow/', CashFlowReportAPI.as_view(), name='reports-cash-flow'),
    path('reports/cash-flow', CashFlowReportAPI.as_view()),
    path('reports/inventory-turnover/', InventoryTurnoverReportAPI.as_view(), name='reports-inventory-turnover'),
    path('reports/inventory-turnover', InventoryTurnoverReportAPI.as_view()),
    path('reports/stock-aging/', StockAgingReportAPI.as_view(), name='reports-stock-aging'),
    path('reports/stock-aging', StockAgingReportAPI.as_view()),
    path('reports/snapshots/', SnapshotSeriesAPI.as_view(), name='reports-snapshot-series'),
    path('reports/snapshots', SnapshotSeriesAPI.as_view()),
    path('reports/health/', ReportsHealthAPI.as_view(), name='reports-health'),
    path('reports/health', ReportsHealthAPI.as_view()),
    path('reports/variance-incidents/', ReportsVarianceIncidentsAPI.as_view(), name='reports-variance-incidents'),
    path('reports/variance-incidents', ReportsVarianceIncidentsAPI.as_view()),
]

__all__ = ["report_urlpatterns"]
