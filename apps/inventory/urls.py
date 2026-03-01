"""
URLs تطبيق المخزون — RITA ERP
"""
from django.urls import path
from apps.inventory.views import (
    ProductListView, ProductCreateView, ProductDetailView, ProductUpdateView,
    StockLevelListView, StockMoveListView,
    StockReceiveView, StockIssueView, StockTransferView, StockAdjustmentView,
    LowStockView, InventoryValuationView,
    BOMListView, BOMCreateView, BOMDetailView,
    CategoryListView,
)

app_name = 'inventory'

urlpatterns = [
    # المنتجات
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/create/', ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', ProductUpdateView.as_view(), name='product_update'),

    # أرصدة المخزون
    path('stock-levels/', StockLevelListView.as_view(), name='stock_levels'),
    path('stock-moves/', StockMoveListView.as_view(), name='stock_moves'),

    # عمليات المخزون
    path('receive/', StockReceiveView.as_view(), name='stock_receive'),
    path('issue/', StockIssueView.as_view(), name='stock_issue'),
    path('transfer/', StockTransferView.as_view(), name='stock_transfer'),
    path('adjustment/', StockAdjustmentView.as_view(), name='stock_adjustment'),

    # التقارير
    path('low-stock/', LowStockView.as_view(), name='low_stock'),
    path('valuation/', InventoryValuationView.as_view(), name='valuation'),

    # قوائم المواد
    path('bom/', BOMListView.as_view(), name='bom_list'),
    path('bom/create/', BOMCreateView.as_view(), name='bom_create'),
    path('bom/<int:pk>/', BOMDetailView.as_view(), name='bom_detail'),

    # التصنيفات
    path('categories/', CategoryListView.as_view(), name='category_list'),
]
