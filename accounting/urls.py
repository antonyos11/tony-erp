from django.urls import path, re_path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from . import views
from . import views_advanced_reports
from . import views_costing
from . import entry_api  # ميزات نموذج الإيراد/المنصرف
from . import views_advanced  # الميزات المتقدمة الجديدة
from . import financial_analysis  # التحليل المالي
from . import api_views

# DRF REST API Router
accounting_api_router = DefaultRouter()
accounting_api_router.register(r'accounts', api_views.AccountViewSet, basename='api-accounts')
accounting_api_router.register(r'journal-entries', api_views.JournalEntryViewSet, basename='api-journal-entries')
accounting_api_router.register(r'cost-centers', api_views.CostCenterViewSet, basename='api-cost-centers')

app_name = 'accounting'

urlpatterns = [
    # ====== نقاط API للميزات المتقدمة ======
    path('api/autosave/', entry_api.autosave_entry, name='autosave_entry'),
    path('api/invoice/<str:invoice_number>/', entry_api.get_invoice_data, name='get_invoice_data'),
    path('api/supplier/<int:supplier_id>/credit/', entry_api.check_supplier_credit, name='check_supplier_credit'),
    path('api/entry-history/', entry_api.get_entry_history, name='get_entry_history'),
    path('api/accounts/search-advanced/', entry_api.search_accounts, name='search_accounts_advanced'),
    path('api/entry-templates/', entry_api.get_templates, name='get_entry_templates'),
    path('api/entry-templates/save/', entry_api.save_template, name='save_entry_template'),
    path('api/tax-settings/', entry_api.get_tax_settings, name='get_tax_settings'),
    
    # روابط تصدير التقارير المالية
    path('tools/export/trial-balance/excel', views.export_trial_balance_excel, name='export_trial_balance_excel'),
    path('tools/export/trial-balance/pdf', views.export_trial_balance_pdf, name='export_trial_balance_pdf'),
    path('tools/export/balance-sheet/excel', views.export_balance_sheet_excel, name='export_balance_sheet_excel'),
    path('tools/export/income-statement/excel', views.export_income_statement_excel, name='export_income_statement_excel'),
    path('tools/export/cash-flow/excel', views.export_cash_flow_excel, name='export_cash_flow_excel'),
    path('tools/export/general-ledger/excel', views.export_general_ledger_excel, name='export_general_ledger_excel'),

    # روابط تصدير Excel وPDF
    path('tools/export/accounts/excel', views.export_accounts_excel, name='export_accounts_excel'),
    path('tools/export/accounts/pdf', views.export_accounts_pdf, name='export_accounts_pdf'),
    path('tools/export/journal-entries/excel', views.export_journal_entries_excel, name='export_journal_entries_excel'),
    path('tools/export/journal-entries/pdf', views.export_journal_entries_pdf, name='export_journal_entries_pdf'),
    path('tools/export/customers/excel', views.export_customers_excel, name='export_customers_excel'),
    path('tools/export/customers/pdf', views.export_customers_pdf, name='export_customers_pdf'),
    path('tools/export/suppliers/excel', views.export_suppliers_excel, name='export_suppliers_excel'),
    path('tools/export/suppliers/pdf', views.export_suppliers_pdf, name='export_suppliers_pdf'),
    path('tools/export/invoices/excel', views.export_invoices_excel, name='export_invoices_excel'),
    path('tools/export/invoices/pdf', views.export_invoices_pdf, name='export_invoices_pdf'),
    path('tools/export/purchase-bills/excel', views.export_purchase_bills_excel, name='export_purchase_bills_excel'),
    path('tools/export/purchase-bills/pdf', views.export_purchase_bills_pdf, name='export_purchase_bills_pdf'),
    
    # Support trailing slashes for export tools
    path('tools/export/accounts/excel/', views.export_accounts_excel),
    path('tools/export/accounts/pdf/', views.export_accounts_pdf),
    path('tools/export/journal-entries/excel/', views.export_journal_entries_excel),
    path('tools/export/journal-entries/pdf/', views.export_journal_entries_pdf),
    path('tools/export/customers/excel/', views.export_customers_excel),
    path('tools/export/customers/pdf/', views.export_customers_pdf),
    path('tools/export/suppliers/excel/', views.export_suppliers_excel),
    path('tools/export/suppliers/pdf/', views.export_suppliers_pdf),
    path('tools/export/invoices/excel/', views.export_invoices_excel),
    path('tools/export/invoices/pdf/', views.export_invoices_pdf),
    path('tools/export/purchase-bills/excel/', views.export_purchase_bills_excel),
    path('tools/export/purchase-bills/pdf/', views.export_purchase_bills_pdf),

    # روابط تصدير البيانات المحاسبية
    path('tools/export/accounts/', views.export_accounts, name='export_accounts'),
    path('tools/export/journal-entries/', views.export_journal_entries, name='export_journal_entries'),
    path('tools/export/customers/', views.export_customers, name='export_customers'),
    path('tools/export/suppliers/', views.export_suppliers, name='export_suppliers'),
    path('tools/export/invoices/', views.export_invoices, name='export_invoices'),
    path('tools/export/purchase-bills/', views.export_purchase_bills, name='export_purchase_bills'),
    # دعم بدون سلاش
    path('tools/export/accounts', views.export_accounts),
    path('tools/export/journal-entries', views.export_journal_entries),
    path('tools/export/customers', views.export_customers),
    path('tools/export/suppliers', views.export_suppliers),
    path('tools/export/invoices', views.export_invoices),
    path('tools/export/purchase-bills', views.export_purchase_bills),
    
    # لوحة التحكم المحاسبية
    path('', views.accounting_dashboard, name='dashboard'),
    
    # لوحة التحكم الجديدة - البنية المحسّنة
    path('dashboard-new/', views.accounting_dashboard_new, name='dashboard_new'),
    
    # نظرة عامة على الأصول (اختصار متوقع من المستخدمين)
    path('assets/', views.assets_overview, name='assets_overview'),
    path('assets', views.assets_overview),  # دعم بدون سلاش
    
    # إهلاك الأصول (Placeholder أولي لتجنب 404 ويعرض حسابات تقديرية)
    path('assets/depreciation', views.asset_depreciation, name='asset_depreciation'),  # بدون سلاش
    path('assets/depreciation/', views.asset_depreciation),  # مع سلاش
    
    # مسار مختصر متوقع أحياناً لعرض القيود (حل 404 عند طلب /accounting/journal)
    path('journal/', RedirectView.as_view(pattern_name='accounting:journal_entries_list', permanent=False), name='journal_redirect'),
    
    # API endpoints for enhanced functionality
    path('api/badges/', views.badges_view, name='badges_api'),
    path('api/accounts/search/', views.account_search_api, name='account_search_api'),
    path('api/journal-entry/validate/', views.journal_entry_validate_api, name='journal_entry_validate_api'),
    path('api/journal-entry/draft/save/', views.journal_entry_draft_save_api, name='journal_entry_draft_save_api'),
    path('api/templates/', views.journal_templates_api, name='journal_templates_api'),
    
    # تكوين الحسابات (إعدادات)
    path('settings/', views.accounting_settings, name='settings'),
    
    # الحسابات الافتراضية
    path('settings/defaults/', views.accounting_settings_defaults, name='settings_defaults'),
    
    # إعدادات الضرائب
    path('settings/tax/', views.tax_settings, name='tax_settings'),
    
    # إعدادات القيود التلقائية
    path('settings/auto-journal/', views.settings_auto_journal, name='settings_auto_journal'),
    
    # دعم /settings/fiscal-year كاختصار لـ /fiscal-years/create/
    path('settings/fiscal-year/', RedirectView.as_view(pattern_name='accounting:fiscal_year_create', permanent=False)),
    path('settings/fiscal-year', RedirectView.as_view(pattern_name='accounting:fiscal_year_create', permanent=False)),
    
    # السنوات المالية
    path('fiscal-years/', views.fiscal_year_list, name='fiscal_year_list'),
    path('fiscal-years/create/', views.fiscal_year_create, name='fiscal_year_create'),
    path('pending-purchase-invoices/', views.pending_purchase_invoices, name='pending_purchase_invoices'),
    
    # تكامل المبيعات (وصول مباشر)
    path('sales/payments/', views.sales_payments_overview, name='sales_payments_overview'),
    path('sales/statement/', views.sales_customer_statement_sample, name='sales_customer_statement_sample'),
    path('sales/statement/<int:customer_id>/', views.sales_customer_statement, name='sales_customer_statement'),
    
    # كشف حساب مورد
    path('purchases/supplier-statement/<int:supplier_id>/', views.supplier_statement, name='supplier_statement'),
    
    # دليل الحسابات
    path('accounts/', views.chart_of_accounts, name='chart_of_accounts'),
    
    # كشف حساب (دفتر أستاذ الحساب)
    path('accounts/statement/', views.general_ledger, name='account_statement'),
    path('accounts/statement', views.general_ledger),  # دعم بدون سلاش
    
    # دعم /accounts/new كاختصار لـ /accounts/create/
    path('accounts/new/', RedirectView.as_view(pattern_name='accounting:account_create', permanent=False)),
    path('accounts/new', RedirectView.as_view(pattern_name='accounting:account_create', permanent=False)),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/expenses/', views.expense_accounts, name='expense_accounts'),
    path('accounts/<int:pk>/details/', views.account_details, name='account_details'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/delete/', views.account_edit, name='account_delete'),  # Alias
    
    # القيود المحاسبية
    path('journal-entries/', views.journal_entries_list, name='journal_entries_list'),
    path('journal-entries/create/', views.journal_entry_create, name='journal_entry_create'),
    path('journal-entries/<int:pk>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('journal-entries/<int:pk>/edit/', views.journal_entry_detail, name='journal_entry_edit'),  # Alias
    path('journal-entries/<int:pk>/post/', views.post_journal_entry, name='post_journal_entry'),
    path('journal-entries/<int:pk>/post/', views.post_journal_entry, name='journal_entry_post'),  # Alias
    path('journal-entries/<int:pk>/reverse/', views.reverse_journal_entry, name='reverse_journal_entry'),
    
    # قيود غير مرحّلة (مسودة)
    path('journal/drafts/', views.journal_drafts_list, name='journal_drafts_list'),
    path('journal/drafts/bulk-post/', views.journal_drafts_bulk_post, name='journal_drafts_bulk_post'),
    path('journal/drafts', views.journal_drafts_list),  # دعم بدون سلاش
    path('journal/drafts/bulk-post', views.journal_drafts_bulk_post),  # دعم بدون سلاش
    
    # التقارير المحاسبية
    path('general-ledger/', views.general_ledger, name='general_ledger'),
    # اختصار للدفتر الأستاذ العام
    path('ledger/', RedirectView.as_view(pattern_name='accounting:general_ledger', permanent=False), name='ledger_redirect'),
    path('ledger', RedirectView.as_view(pattern_name='accounting:general_ledger', permanent=False)),  # دعم بدون سلاش
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('income-statement/', views.income_statement, name='income_statement'),
    path('cash-flow/', views.cash_flow_statement, name='cash_flow_statement'),
    path('reports/aging/receivables/', views.aging_receivables_report, name='aging_receivables_report'),
    path('reports/aging/payables/', views.aging_payables_report, name='aging_payables_report'),
    path('reports/tax/', views.tax_report_view, name='tax_report_view'),
    # دعم بدون سلاش
    path('reports/aging/receivables', views.aging_receivables_report),
    path('reports/aging/payables', views.aging_payables_report),
    path('reports/tax', views.tax_report_view),
    path('reports/daily-expenses/', views.daily_expenses_report, name='daily_expenses_report'),

    # إعادة توجيه للمسارات القديمة (compatibility)
    path('reports/income', RedirectView.as_view(url='/accounting/income-statement/', permanent=False)),
    path('reports/balance-sheet', RedirectView.as_view(url='/accounting/balance-sheet/', permanent=False)),
    path('reports/cash-flow', RedirectView.as_view(url='/accounting/cash-flow/', permanent=False)),
    path('reports/trial-balance', RedirectView.as_view(url='/accounting/trial-balance/', permanent=False)),
    
    # مراكز التكلفة
    path('cost-centers/', views.cost_centers_list, name='cost_centers_list'),
    path('cost-centers/create/', views.cost_center_create, name='cost_center_create'),
    path('cost-centers/<int:pk>/', views.cost_center_detail, name='cost_center_detail'),
    # تخصيص التكاليف (مسار جديد Placeholder لتجنب 404 مؤقتاً)
    path('cost/allocations/', views.cost_allocations_list, name='cost_allocations_list'),
    path('cost/allocations', views.cost_allocations_list),  # دعم بدون سلاش
    
    # قوالب القيود
    path('journal-templates/', views.journal_templates_list, name='journal_templates_list'),
    path('journal-templates/create/', views.journal_template_create, name='journal_template_create'),
    path('journal-templates/<int:pk>/', views.journal_template_detail, name='journal_template_detail'),
    path('smart-entry/', views.smart_journal_entry_create, name='smart_journal_entry_create'),
    
    # القروض البنكية
    path('loans/', views.loans_dashboard, name='loans_dashboard'),
    path('loans/list/', views.loan_list, name='loan_list'),
    path('loans/create/', views.loan_create, name='loan_create'),
    path('loans/<int:pk>/', views.loan_detail, name='loan_detail'),
    path('loans/<int:loan_id>/payment/', views.loan_payment_create, name='loan_payment_create'),

    # مسار دفع نقدي مختصر (تحويل للمسار القياسي إنشاء قيد)
    path('cash/payment/', RedirectView.as_view(pattern_name='accounting:journal_entry_create', permanent=False), name='cash_payment_create'),
    # مسار إيصال قبض نقدي مختصر (يوجز إلى عرض محاسبي يقوم بالتحقق ثم تحويل دائم لمبيعات)
    path('cash/receipt/', views.cash_receipt_create, name='cash_receipt_create'),
    path('cash/receipt', views.cash_receipt_create),  # دعم طلب بدون سلاش نهائي
    # تحويل نقدي داخلي (خزينة/بنك -> خزينة/بنك) حالياً يعاد توجيهه لإنشاء قيد عام مع معاملات توضيحية
    path('cash/transfer/', views.cash_transfer_create, name='cash_transfer_create'),
    path('cash/transfer', views.cash_transfer_create),  # دعم بدون سلاش

    # تسوية البنك (شاشة مبدئية)
    path('bank/reconcile/', views.bank_reconcile_view, name='bank_reconcile'),
    path('bank/reconciliation/', views.bank_reconcile_view, name='bank_reconciliation'),  # Alias
    path('bank/reconcile', views.bank_reconcile_view),  # دعم بدون سلاش
    path('bank/tx/<int:pk>/toggle/', views.bank_transaction_toggle_reconciled, name='bank_tx_toggle'),
    # استيراد كشف بنكي
    path('bank/import-statement/', views.bank_statement_import, name='bank_statement_import'),
    path('bank/import-statement', views.bank_statement_import),

    # أرصدة الخزينة والبنوك الآن
    path('cash/positions/', views.cash_positions_view, name='cash_positions'),
    path('cash/positions', views.cash_positions_view),  # دعم بدون سلاش

    # الشيكات (حافظة الشيكات)
    path('cheques/', views.cheque_list, name='cheque_list'),
    path('cheques/new/', views.cheque_create, name='cheque_create'),
    path('cheques/<int:pk>/', views.cheque_detail, name='cheque_detail'),
    path('cheques/<int:pk>/delete/', views.cheque_delete, name='cheque_delete'),
    # أدوات / تشخيص
    path('tools/diagnostics/', views.diagnostics_view, name='diagnostics'),
    path('tools/export/', views.export_tools, name='export_tools'),
    path('tools/fixes/', views.tools_fixes, name='tools_fixes'),
    # دعم بدون سلاش
    path('tools/diagnostics', views.diagnostics_view),
    path('tools/export', views.export_tools),
    path('tools/fixes', views.tools_fixes),
    # استيراد قيود يومية (CSV بسيط)
    path('tools/import-journal', views.import_journal_view, name='import_journal'),
    path('tools/import-journal/', views.import_journal_view),

    # إقفالات الفترات والتسويات (مسارات جديدة Placeholder)
    path('period/close-year', views.period_close_year, name='period_close_year'),
    path('period/close-year/', views.period_close_year),  # دعم السلاش
    path('period/close-month', views.period_close_month, name='period_close_month'),
    path('period/close-month/', views.period_close_month),
    path('period/adjustments', views.period_adjustments, name='period_adjustments'),
    path('period/adjustments/', views.period_adjustments),
    path('journal/recurring', views.recurring_journal_entries, name='recurring_journal_entries'),
    path('journal/recurring/', views.recurring_journal_entries),
    
    # Advanced Reports - Phase 1 Implementation
    path('reports/budget-vs-actual/', views_advanced_reports.budget_vs_actual_report, name='budget_vs_actual_report'),
    path('reports/product-profitability/', views_advanced_reports.product_profitability_report, name='product_profitability_report'),
    path('reports/customer-profitability/', views_advanced_reports.customer_profitability_report, name='customer_profitability_report'),
    path('reports/variance-dashboard/', views_advanced_reports.variance_analysis_dashboard, name='variance_dashboard'),
    
    # نظام تكاليف المنتجات (Product Costing)
    path('costing/', views_costing.costing_dashboard, name='costing_dashboard'),
    path('costing/list/', views_costing.costing_list, name='costing_list'),
    path('costing/create/', views_costing.costing_create, name='costing_create'),
    path('costing/create/<int:product_id>/', views_costing.costing_create, name='costing_create'),
    path('costing/<int:pk>/', views_costing.costing_detail, name='costing_detail'),
    path('costing/<int:pk>/edit/', views_costing.costing_edit, name='costing_edit'),
    path('costing/<int:pk>/activate/', views_costing.costing_activate, name='costing_activate'),
    path('costing/<int:costing_id>/component/create/', views_costing.component_create, name='component_create'),
    path('costing/component/<int:pk>/edit/', views_costing.component_edit, name='component_edit'),
    path('costing/component/<int:pk>/delete/', views_costing.component_delete, name='component_delete'),
    path('costing/history/<int:product_id>/', views_costing.costing_history, name='costing_history'),
    path('costing/analysis/', views_costing.costing_analysis, name='costing_analysis'),
    path('costing/bulk-update/', views_costing.bulk_update_costs, name='bulk_update_costs'),
    path('costing/export/', views_costing.costing_export, name='costing_export'),
    
    # =============================
    # تفاصيل القيد المحاسبي (alias)
    # =============================
    path('journal/<int:pk>/', views.journal_entry_detail, name='journal_detail'),

    # =============================
    # تسجيل الحسابات - إيراد ومنصرف
    # =============================
    path('entries/', views.account_entries_list, name='account_entries_list'),
    path('entries/revenue/create/', views.revenue_create, name='revenue_create'),
    path('entries/expense/create/', views.expense_create, name='expense_create'),
    path('entries/<int:pk>/create-journal/', views.create_entry_journal, name='create_entry_journal'),
    # Alias routes for common URLs (without entries/ prefix)
    path('revenue/create/', views.revenue_create, name='revenue_create_alias'),
    path('expense/create/', views.expense_create, name='expense_create_alias'),
    path('entries/recent/', views.get_recent_entries, name='get_recent_entries'),
    path('entries/get-owner-options/', views.get_owner_options, name='get_owner_options'),
    path('entries/revenue/supplier-report/', views.supplier_revenue_report, name='supplier_revenue_report'),
    path('entries/revenue/supplier/<int:supplier_id>/', views.supplier_revenue_detail, name='supplier_revenue_detail'),
    
    # التحليلات المالية
    path('financial-analysis-1/', views.financial_analysis_1_list, name='financial_analysis_1_list'),
    path('financial-analysis-2/', views.financial_analysis_2_list, name='financial_analysis_2_list'),
    
    # دفتر الأستاذ
    path('ledger-accounts/', views.ledger_accounts_list, name='ledger_accounts_list'),
    
    # =============================
    # التقارير الجديدة
    # =============================
    path('reports/ledger-account/', views.ledger_account_report, name='ledger_account_report'),
    path('reports/financial-analysis-1/', views.financial_analysis_1_report, name='financial_analysis_1_report'),
    path('reports/financial-analysis-2/', views.financial_analysis_2_report, name='financial_analysis_2_report'),
    path('reports/cost-center/', views.cost_center_report, name='cost_center_report'),
    path('reports/owner/', views.owner_report, name='owner_report'),
    
    # =============================
    # إدارة الحسابات الإلكترونية
    # =============================
    path('electronic-accounts/', views.electronic_accounts_list, name='electronic_accounts_list'),
    path('electronic-accounts/create/', views.electronic_account_create, name='electronic_account_create'),
    path('electronic-accounts/<int:pk>/edit/', views.electronic_account_edit, name='electronic_account_edit'),
    path('electronic-accounts/<int:pk>/delete/', views.electronic_account_delete, name='electronic_account_delete'),
    
    # =============================
    # إدارة الخزائن
    # =============================
    path('treasuries/', views.treasuries_list, name='treasuries_list'),
    path('treasuries/create/', views.treasury_create, name='treasury_create'),
    path('treasuries/<int:pk>/edit/', views.treasury_edit, name='treasury_edit'),
    path('treasuries/<int:pk>/delete/', views.treasury_delete, name='treasury_delete'),
    
    # =============================
    # إدارة البنوك
    # =============================
    path('banks/', views.banks_list, name='banks_list'),
    path('banks/create/', views.bank_create, name='bank_create'),
    path('banks/<int:pk>/edit/', views.bank_edit, name='bank_edit'),
    path('banks/<int:pk>/delete/', views.bank_delete, name='bank_delete'),
    
    # =============================
    # إدارة ماكينات الفوري
    # =============================
    path('fawry-machines/', views.fawry_machines_list, name='fawry_machines_list'),
    path('fawry-machines/create/', views.fawry_machine_create, name='fawry_machine_create'),
    path('fawry-machines/<int:pk>/edit/', views.fawry_machine_edit, name='fawry_machine_edit'),
    path('fawry-machines/<int:pk>/delete/', views.fawry_machine_delete, name='fawry_machine_delete'),
    
    # =============================
    # إدارة ماكينات الفيزا
    # =============================
    path('visa-machines/', views.visa_machines_list, name='visa_machines_list'),
    path('visa-machines/create/', views.visa_machine_create, name='visa_machine_create'),
    path('visa-machines/<int:pk>/edit/', views.visa_machine_edit, name='visa_machine_edit'),
    path('visa-machines/<int:pk>/delete/', views.visa_machine_delete, name='visa_machine_delete'),
    
    # =============================
    # التحويلات بين الحسابات
    # =============================
    path('transfers/', views.transfers_list, name='transfers_list'),
    path('transfers/create/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:pk>/cancel/', views.transfer_cancel, name='transfer_cancel'),
    
    # ==================== الميزات المتقدمة الجديدة ====================
        # الصفحة الرئيسية للميزات المتقدمة
    path('advanced/', views_advanced.advanced_features_index, name='advanced_features_index'),
        # التسويات البنكية
    path('advanced/bank-reconciliation/', views_advanced.bank_reconciliation_list, name='bank_reconciliation_list'),
    path('advanced/bank-reconciliation/create/', views_advanced.bank_reconciliation_create, name='bank_reconciliation_create'),
    path('advanced/bank-reconciliation/<int:pk>/', views_advanced.bank_reconciliation_detail, name='bank_reconciliation_detail'),
    
    # القيود المتكررة
    path('advanced/recurring-entries/', views_advanced.recurring_entries_list, name='recurring_entries_list'),
    path('advanced/recurring-entries/<int:pk>/execute/', views_advanced.execute_recurring_entry, name='execute_recurring_entry'),
    
    # الموازنات التخطيطية
    path('advanced/budget/', views_advanced.budget_dashboard, name='budget_dashboard'),
    
    # الأصول الثابتة والإهلاك
    path('advanced/assets/', views_advanced.assets_list, name='assets_list_advanced'),
    path('advanced/assets/<int:pk>/', views_advanced.asset_detail, name='asset_detail'),
    path('advanced/assets/depreciation/calculate/', views_advanced.calculate_depreciation, name='calculate_depreciation'),
    path('advanced/assets/depreciation/sum-of-years/', views_advanced.depreciation_sum_of_years, name='depreciation_sum_of_years'),
    path('advanced/assets/depreciation/straight-line/', views_advanced.depreciation_straight_line, name='depreciation_straight_line'),
    path('advanced/assets/depreciation/declining-balance/', views_advanced.depreciation_declining_balance, name='depreciation_declining_balance'),
    path('advanced/assets/depreciation/auto/', views_advanced.calculate_depreciation, name='depreciation_auto'),  # Alias for calculate_depreciation
    
    # القوائم المالية الديناميكية
    path('advanced/financial-statements/balance-sheet/', views_advanced.balance_sheet, name='balance_sheet'),
    path('advanced/financial-statements/income-statement/', views_advanced.income_statement, name='income_statement'),
    
    # التحليل المالي المتقدم
    path('advanced/financial-analysis/', financial_analysis.financial_analysis_dashboard, name='financial_analysis_dashboard'),
    path('advanced/financial-analysis/ratios/', financial_analysis.financial_ratios_report, name='financial_ratios_report'),
    
    # إقفال الفترات
    path('advanced/period-close/', views_advanced.period_close_list, name='period_close_list'),
    
    # تقرير أعمار الديون
    path('advanced/aging-report/', views_advanced.aging_report, name='aging_report'),
    
    # سجل المراجعة
    path('advanced/audit-log/', views_advanced.audit_log, name='audit_log'),
    
    # ==================== القوالب الإضافية ====================
    
    # لوحة CFO التنفيذية
    path('advanced/cfo-dashboard/', views_advanced.cfo_dashboard, name='cfo_dashboard'),
    
    # التقارير المخصصة
    path('advanced/custom-reports/', views_advanced.custom_reports, name='custom_reports'),
    
    # سير عمل الاعتمادات
    path('advanced/approval-workflow/', views_advanced.approval_workflow, name='approval_workflow'),
    path('advanced/approval-workflow/settings/', views_advanced.workflow_settings, name='workflow_settings'),
    path('advanced/approval-workflow/<int:pk>/', views_advanced.approval_detail, name='approval_detail'),
    
    # عمليات التسوية البنكية
    path('advanced/bank-reconciliation/<int:pk>/match/', views_advanced.match_transactions, name='match_transactions'),
    path('advanced/bank-reconciliation/<int:pk>/auto-match/', views_advanced.auto_match, name='auto_match'),
    path('advanced/bank-reconciliation/<int:pk>/complete/', views_advanced.complete_reconciliation, name='complete_reconciliation'),
    
    # المطابقة التلقائية (صفحات عامة)
    path('advanced/bank-reconciliation/auto-match/amount/', views_advanced.auto_match_amount, name='auto_match_amount'),
    path('advanced/bank-reconciliation/auto-match/date/', views_advanced.auto_match_date, name='auto_match_date'),
    path('advanced/bank-reconciliation/auto-match/reference/', views_advanced.auto_match_reference, name='auto_match_reference'),
    path('advanced/bank-reconciliation/auto-match/ai/', views_advanced.auto_match_ai, name='auto_match_ai'),
    
    # الأصول الثابتة - مسارات إضافية
    path('advanced/assets-list/', views_advanced.assets_list, name='assets_list'),
    
    # التحليل المالي
    path('advanced/financial-analysis-page/', views_advanced.financial_analysis_page, name='financial_analysis'),

    # الفترات المحاسبية المتقدمة
    path('periods/', views_advanced.accounting_period_list, name='accounting_period_list'),
    path('periods/create/', views_advanced.accounting_period_create, name='accounting_period_create'),
    path('periods/<int:pk>/', views_advanced.accounting_period_detail, name='accounting_period_detail'),
    path('periods/<int:pk>/edit/', views_advanced.accounting_period_edit, name='accounting_period_edit'),
    path('periods/<int:pk>/close/', views_advanced.accounting_period_close, name='accounting_period_close'),
    path('periods/<int:pk>/reopen/', views_advanced.accounting_period_reopen, name='accounting_period_reopen'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('cheque-edit/<int:pk>/', stub_view, name='cheque_edit'),
    path('cost-allocation-create/', stub_view, name='cost_allocation_create'),
    path('cost-center-delete/<int:pk>/', stub_view, name='cost_center_delete'),
    path('journal-drafts/', stub_view, name='journal_drafts'),
    path('journal-template-edit/<int:pk>/', stub_view, name='journal_template_edit'),
    path('journal-templates/', stub_view, name='journal_templates'),
    path('loan-payment/<int:pk>/', stub_view, name='loan_payment'),
]

# REST API v1 endpoints
urlpatterns += [
    path('api/v1/', include(accounting_api_router.urls)),
]
