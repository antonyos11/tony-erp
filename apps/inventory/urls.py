"""
URLs تطبيق المخزون — RITA ERP
"""
from django.urls import path
from apps.inventory.views import (
    ProductListView, ProductCreateView, ProductDetailView, ProductUpdateView,
    StockLevelListView, StockMoveListView,
    StockReceiveView, StockIssueView, StockTransferView, StockAdjustmentView,
    LowStockView, InventoryValuationView,
    BOMListView, BOMCreateView, BOMDetailView, BOMUpdateView, BOMDeleteView,
    BOMDuplicateView, BOMExplodeView, BOMMaterialCheckView,
    CategoryListView, CategoryCreateView, CategoryUpdateView,
    CategoryDeleteView, CategoryQuickCreateView,
    StockCountListView, StockCountCreateView, StockCountDetailView, StockCountApplyView,
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

    # قوائم المواد (BOM)
    path('bom/', BOMListView.as_view(), name='bom_list'),
    path('bom/create/', BOMCreateView.as_view(), name='bom_create'),
    path('bom/<int:pk>/', BOMDetailView.as_view(), name='bom_detail'),
    path('bom/<int:pk>/edit/', BOMUpdateView.as_view(), name='bom_update'),
    path('bom/<int:pk>/delete/', BOMDeleteView.as_view(), name='bom_delete'),
    path('bom/<int:pk>/duplicate/', BOMDuplicateView.as_view(), name='bom_duplicate'),
    path('bom/<int:pk>/explode/', BOMExplodeView.as_view(), name='bom_explode'),
    path('bom/<int:pk>/check-materials/', BOMMaterialCheckView.as_view(), name='bom_check_materials'),

    # الجرد المخزني
    path('stock-count/', StockCountListView.as_view(), name='stock_count_list'),
    path('stock-count/create/', StockCountCreateView.as_view(), name='stock_count_create'),
    path('stock-count/<int:pk>/', StockCountDetailView.as_view(), name='stock_count_detail'),
    path('stock-count/<int:pk>/apply/', StockCountApplyView.as_view(), name='stock_count_apply'),

    # التصنيفات — literal paths قبل المعرَّفات بـ pk
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/create/', CategoryCreateView.as_view(), name='category_create'),
    path('categories/quick-create/', CategoryQuickCreateView.as_view(), name='category_quick_create'),
    path('categories/<int:pk>/edit/', CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),
]
