"""
مسارات تطبيق الشركاء (العملاء والموردين)
"""
from django.urls import path
from . import views

app_name = 'partners'

urlpatterns = [
    # الصفحة الرئيسية
    path('', views.dashboard, name='dashboard'),

    # إدارة الشركاء
    path('list/', views.partners_list, name='partners_list'),
    path('create/', views.partner_create, name='partner_create'),
    path('add/', views.partner_create, name='partner_add'),  # مسار بديل

    # العملاء
    path('customers/', views.customers_list, name='customers_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/add/', views.customer_create, name='customer_add'),  # مسار بديل

    # الموردين
    path('suppliers/', views.suppliers_list, name='suppliers_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/add/', views.supplier_create, name='supplier_add'),  # مسار بديل
    path('suppliers/<int:pk>/detail/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # مستندات الموردين
    path('suppliers/<int:supplier_id>/documents/', views.supplier_documents, name='supplier_documents'),
    path('suppliers/<int:supplier_id>/documents/add/', views.supplier_document_add, name='supplier_document_add'),
    path('suppliers/<int:supplier_id>/documents/upload/', views.supplier_document_upload, name='supplier_document_upload'),
    path('documents/<int:document_id>/delete/', views.supplier_document_delete, name='supplier_document_delete'),
    path('documents/<int:document_id>/download/', views.supplier_document_download, name='supplier_document_download'),

    # منتجات الموردين (أسعار الشراء)
    path('supplier-products/', views.all_supplier_products, name='all_supplier_products'),
    path('supplier-products/quick-update/', views.quick_price_update, name='quick_price_update'),
    path('suppliers/<int:supplier_id>/products/', views.supplier_products, name='supplier_products'),
    path('suppliers/<int:supplier_id>/products/add/', views.supplier_product_add, name='supplier_product_add'),
    path('suppliers/<int:supplier_id>/products/add-ajax/', views.supplier_product_add_ajax, name='supplier_product_add_ajax'),
    path('supplier-products/<int:supplier_product_id>/edit/', views.supplier_product_edit, name='supplier_product_edit'),
    path('supplier-products/<int:supplier_product_id>/delete/', views.supplier_product_delete, name='supplier_product_delete'),

    # حسابات المورد (الفواتير والدفعات)
    path('suppliers/<int:supplier_id>/account/', views.supplier_account, name='supplier_account'),

    # التقارير
    path('reports/', views.partners_reports, name='reports'),
    path('reports/customers/', views.customers_report, name='customers_report'),
    path('reports/suppliers/', views.suppliers_report, name='suppliers_report'),

    # مسارات الشركاء العامة (يجب أن تكون في النهاية لتجنب التعارض)
    path('<int:pk>/', views.partner_detail, name='partner_detail'),
    path('<int:pk>/edit/', views.partner_edit, name='partner_edit'),
    path('<int:pk>/delete/', views.partner_delete, name='partner_delete'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('customer-detail/<int:pk>/', stub_view, name='customer_detail'),
    path('supplier-list/', stub_view, name='supplier_list'),
]
