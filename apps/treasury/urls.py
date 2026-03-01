"""
URLs تطبيق الخزينة والبنوك — RITA ERP
"""
from django.urls import path
from apps.treasury import views

app_name = 'treasury'

urlpatterns = [
    # ── البنوك ─────────────────────────────────────────────────────
    path('banks/',        views.BankAccountListView.as_view(),   name='bank_account_list'),
    path('banks/create/', views.BankAccountCreateView.as_view(), name='bank_account_create'),

    # ── الخزائن ────────────────────────────────────────────────────
    path('cashboxes/',        views.CashBoxListView.as_view(),   name='cashbox_list'),
    path('cashboxes/create/', views.CashBoxCreateView.as_view(), name='cashbox_create'),

    # ── الشيكات ────────────────────────────────────────────────────
    path('checks/',               views.CheckListView.as_view(),             name='check_list'),
    path('checks/create/',        views.CheckCreateView.as_view(),           name='check_create'),
    path('checks/<int:pk>/<str:action>/', views.CheckActionView.as_view(),  name='check_action'),

    # ── التحويلات ──────────────────────────────────────────────────
    path('transfers/',        views.MoneyTransferListView.as_view(),   name='transfer_list'),
    path('transfers/create/', views.MoneyTransferCreateView.as_view(), name='transfer_create'),

    # ── مطابقة بنكية ───────────────────────────────────────────────
    path('reconciliation/', views.BankReconciliationView.as_view(), name='bank_reconciliation'),
]
