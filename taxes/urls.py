from django.urls import path
from . import views

app_name = 'taxes'

urlpatterns = [
    # لوحة التحكم
    path('', views.dashboard, name='dashboard'),
    
    # الإعدادات
    path('settings/', views.settings_view, name='settings'),
    
    # الفئات الضريبية
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # الفواتير الضريبية
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoices/<int:pk>/submit/', views.invoice_submit, name='invoice_submit'),
    
    # الفترات الضريبية
    path('periods/', views.period_list, name='period_list'),
    path('periods/create/', views.period_create, name='period_create'),
    path('periods/<int:pk>/', views.period_detail, name='period_detail'),
    path('periods/<int:pk>/calculate/', views.period_calculate, name='period_calculate'),
    path('periods/<int:pk>/close/', views.period_close, name='period_close'),
    path('periods/<int:pk>/file/', views.period_file, name='period_file'),
    
    # المدفوعات
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    
    # التقارير
    path('reports/summary/', views.report_summary, name='report_summary'),
    path('reports/vat-return/', views.report_vat_return, name='report_vat_return'),
    
    # API
    path('api/calculate/', views.api_calculate_tax, name='api_calculate'),
    path('api/stats/', views.api_invoice_stats, name='api_stats'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('invoice-export/', stub_view, name='invoice_export'),
    path('invoice-print/<int:pk>/', stub_view, name='invoice_print'),
]
