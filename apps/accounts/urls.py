"""
URLs تطبيق المحاسبة — RITA ERP
"""
from django.urls import path
from apps.accounts.views import (
    ChartOfAccountsView,
    AccountCreateView,
    JournalEntryListView,
    JournalEntryDetailView,
    JournalEntryCreateView,
    TrialBalanceView,
    IncomeStatementView,
    BalanceSheetView,
    AccountStatementView,
    FiscalYearListView,
)

app_name = 'accounts'

urlpatterns = [
    # دليل الحسابات
    path('', ChartOfAccountsView.as_view(), name='chart_of_accounts'),
    path('account/create/', AccountCreateView.as_view(), name='account_create'),

    # القيود المحاسبية
    path('journals/', JournalEntryListView.as_view(), name='journal_list'),
    path('journals/create/', JournalEntryCreateView.as_view(), name='journal_create'),
    path('journals/<int:pk>/', JournalEntryDetailView.as_view(), name='journal_detail'),

    # التقارير المالية
    path('reports/trial-balance/', TrialBalanceView.as_view(), name='trial_balance'),
    path('reports/income-statement/', IncomeStatementView.as_view(), name='income_statement'),
    path('reports/balance-sheet/', BalanceSheetView.as_view(), name='balance_sheet'),
    path('reports/account-statement/', AccountStatementView.as_view(), name='account_statement'),

    # السنوات المالية
    path('fiscal-years/', FiscalYearListView.as_view(), name='fiscal_year_list'),
]
