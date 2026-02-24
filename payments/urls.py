"""
مسارات تطبيق المدفوعات والقروض
"""
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # الصفحة الرئيسية
    path('', views.dashboard, name='dashboard'),
    
    # إدارة طرق الدفع
    path('methods/', views.payment_methods_list, name='payment_methods_list'),
    path('methods/create/', views.payment_method_create, name='payment_method_create'),
    path('methods/<int:pk>/edit/', views.payment_method_edit, name='payment_method_edit'),
    path('methods/<int:pk>/delete/', views.payment_method_delete, name='payment_method_delete'),
    
    # إدارة القروض
    path('loans/', views.loans_list, name='loans_list'),
    path('loans/create/', views.loan_create, name='loan_create'),
    path('loans/<int:pk>/', views.loan_detail, name='loan_detail'),
    path('loans/<int:pk>/edit/', views.loan_edit, name='loan_edit'),
    path('loans/<int:pk>/delete/', views.loan_delete, name='loan_delete'),
    
    # الأقساط
    path('installments/', views.installments_list, name='installments_list'),
    path('installments/<int:pk>/pay/', views.installment_pay, name='installment_pay'),
    path('installments/<int:pk>/details/', views.installment_detail, name='installment_detail'),
    
    # المعاملات
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    
    # التقارير
    path('reports/', views.payments_reports, name='reports'),
    path('reports/overdue/', views.overdue_report, name='overdue_report'),
    path('reports/collection/', views.collection_report, name='collection_report'),
]