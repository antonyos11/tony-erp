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

    # الفواتير
    path('invoices/', views.SalesInvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.SalesInvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/', views.SalesInvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/confirm/', views.ConfirmInvoiceView.as_view(), name='invoice_confirm'),
    path('invoices/<int:pk>/payment/', views.RecordPaymentView.as_view(), name='record_payment'),

    # المرتجعات
    path('returns/', views.SalesReturnListView.as_view(), name='return_list'),
    path('returns/create/', views.SalesReturnCreateView.as_view(), name='return_create'),

    # قوائم الأسعار
    path('price-lists/', views.PriceListView.as_view(), name='price_lists'),
]
