"""
URLs تطبيق المصروفات والسندات — RITA ERP
"""
from django.urls import path
from apps.expenses import views

app_name = 'expenses'

urlpatterns = [
    # ── المصروفات ─────────────────────────────────────
    path('', views.ExpenseListView.as_view(), name='expense_list'),
    path('create/', views.ExpenseCreateView.as_view(), name='expense_create'),
    path('<int:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('<int:pk>/approve/', views.ExpenseApproveView.as_view(), name='expense_approve'),

    # ── المصروفات الدورية ─────────────────────────────
    path('recurring/', views.RecurringExpenseListView.as_view(), name='recurring_list'),
    path('recurring/create/', views.RecurringExpenseCreateView.as_view(), name='recurring_create'),

    # ── سندات الصرف ───────────────────────────────────
    path('payment-vouchers/', views.PaymentVoucherListView.as_view(), name='pv_list'),
    path('payment-vouchers/create/', views.PaymentVoucherCreateView.as_view(), name='pv_create'),
    path('payment-vouchers/<int:pk>/', views.PaymentVoucherDetailView.as_view(), name='pv_detail'),
    path('payment-vouchers/<int:pk>/approve/', views.PaymentVoucherApproveView.as_view(), name='pv_approve'),
    path('payment-vouchers/<int:pk>/print/', views.PaymentVoucherPrintView.as_view(), name='pv_print'),

    # ── سندات القبض ───────────────────────────────────
    path('receipt-vouchers/', views.ReceiptVoucherListView.as_view(), name='rv_list'),
    path('receipt-vouchers/create/', views.ReceiptVoucherCreateView.as_view(), name='rv_create'),
    path('receipt-vouchers/<int:pk>/', views.ReceiptVoucherDetailView.as_view(), name='rv_detail'),
    path('receipt-vouchers/<int:pk>/approve/', views.ReceiptVoucherApproveView.as_view(), name='rv_approve'),
    path('receipt-vouchers/<int:pk>/print/', views.ReceiptVoucherPrintView.as_view(), name='rv_print'),

    # ── العهد النثرية ─────────────────────────────────
    path('petty-cash/', views.PettyCashListView.as_view(), name='petty_cash_list'),
    path('petty-cash/<int:pk>/', views.PettyCashDetailView.as_view(), name='petty_cash_detail'),
    path('petty-cash/<int:pk>/replenish/', views.PettyCashReplenishView.as_view(), name='petty_cash_replenish'),
    path('petty-cash/<int:pk>/spend/', views.PettyCashSpendView.as_view(), name='petty_cash_spend'),

    # ── التقارير ──────────────────────────────────────
    path('budget/', views.ExpenseBudgetView.as_view(), name='budget_report'),

    # ── تصنيفات المصروفات Sprint 22C ──────────────────
    path('categories/', views.ExpenseCategoryListView.as_view(), name='expense_category_list'),
    path('categories/create/', views.ExpenseCategoryCreateView.as_view(), name='expense_category_create'),
    path('categories/<int:pk>/edit/', views.ExpenseCategoryUpdateView.as_view(), name='expense_category_update'),
]
