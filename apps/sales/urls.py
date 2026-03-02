"""
URLs تطبيق المبيعات — RITA ERP
"""
from django.urls import path
from apps.sales import views

app_name = 'sales'

urlpatterns = [
    # العملاء
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/statement/', views.CustomerStatementView.as_view(), name='customer_statement'),

    # الفواتير
    path('invoices/', views.SalesInvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.SalesInvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/', views.SalesInvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='invoice_update'),
    path('invoices/<int:pk>/confirm/', views.ConfirmInvoiceView.as_view(), name='invoice_confirm'),
    path('invoices/<int:pk>/cancel/', views.InvoiceCancelView.as_view(), name='invoice_cancel'),
    path('invoices/<int:pk>/payment/', views.RecordPaymentView.as_view(), name='record_payment'),
    path('invoices/<int:pk>/print/', views.InvoicePrintView.as_view(), name='invoice_print'),
    path('invoices/<int:pk>/print/thermal/', views.InvoiceThermalView.as_view(), name='invoice_thermal'),

    # المرتجعات
    path('returns/', views.SalesReturnListView.as_view(), name='return_list'),
    path('returns/create/', views.SalesReturnCreateView.as_view(), name='return_create'),

    # قوائم الأسعار
    path('price-lists/', views.PriceListView.as_view(), name='price_lists'),
    path('price-lists/create/', views.PriceListCreateView.as_view(), name='price_list_create'),
    path('price-lists/<int:pk>/', views.PriceListDetailView.as_view(), name='price_list_detail'),
    path('price-lists/<int:pk>/edit/', views.PriceListUpdateView.as_view(), name='price_list_update'),

    # إضافة سريعة (AJAX)
    path('customers/quick-add/', views.quick_add_customer, name='quick_add_customer'),
]
