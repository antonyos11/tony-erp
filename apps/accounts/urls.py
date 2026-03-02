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
    JournalEditView,
    JournalCancelView,
    JournalPostView,
    TrialBalanceView,
    IncomeStatementView,
    BalanceSheetView,
    AccountStatementView,
    FiscalYearListView,
    # Sprint 22B
    CostCenterListView,
    WIPSummaryView,
    ProductionCostDetailView,
    UnitCostComparisonView,
    BudgetListView,
    BudgetCreateView,
    BudgetDetailView,
    BudgetUpdateView,
    BudgetApproveView,
    BudgetVsActualView,
    CostCenterProfitabilityView,
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

    # تعديل واعتماد القيود
    path('journals/<int:pk>/edit/', JournalEditView.as_view(), name='journal_edit'),
    path('journals/<int:pk>/cancel/', JournalCancelView.as_view(), name='journal_cancel'),
    path('journals/<int:pk>/post/', JournalPostView.as_view(), name='journal_post'),

    # السنوات المالية
    path('fiscal-years/', FiscalYearListView.as_view(), name='fiscal_year_list'),

    # Sprint 22B — مراكز التكلفة
    path('cost-centers/', CostCenterListView.as_view(), name='cost_center_list'),
    path('cost-centers/profitability/', CostCenterProfitabilityView.as_view(), name='cost_center_profitability'),

    # Sprint 22B — WIP
    path('wip/', WIPSummaryView.as_view(), name='wip_summary'),
    path('wip/order/<int:pk>/', ProductionCostDetailView.as_view(), name='production_cost_detail'),
    path('wip/unit-cost/<int:product_id>/', UnitCostComparisonView.as_view(), name='unit_cost_comparison'),

    # Sprint 22B — الميزانيات
    path('budgets/', BudgetListView.as_view(), name='budget_list'),
    path('budgets/create/', BudgetCreateView.as_view(), name='budget_create'),
    path('budgets/<int:pk>/', BudgetDetailView.as_view(), name='budget_detail'),
    path('budgets/<int:pk>/edit/', BudgetUpdateView.as_view(), name='budget_update'),
    path('budgets/<int:pk>/approve/', BudgetApproveView.as_view(), name='budget_approve'),
    path('budgets/<int:pk>/report/', BudgetVsActualView.as_view(), name='budget_vs_actual'),
]


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

    # تعديل واعتماد القيود
    path('journals/<int:pk>/edit/', JournalEditView.as_view(), name='journal_edit'),
    path('journals/<int:pk>/cancel/', JournalCancelView.as_view(), name='journal_cancel'),
    path('journals/<int:pk>/post/', JournalPostView.as_view(), name='journal_post'),
    # السنوات المالية
    path('fiscal-years/', FiscalYearListView.as_view(), name='fiscal_year_list'),
]
