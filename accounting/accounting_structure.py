"""
البنية المحسّنة لقائمة المحاسبة مع التبويبات الأربعة
=========================================================

هذا الملف يحتوي على التكوين الجديد المنظم للمحاسبة
مقسم إلى 4 تبويبات رئيسية
"""

from django.utils.translation import gettext_lazy as _


# تعريف التبويبات (Tabs)
ACCOUNTING_TABS = {
    'daily_basics': {
        'id': 'daily_basics',
        'label': _('الأساسيات اليومية'),
        'icon': 'bi-pencil-square',
        'color': '#3b82f6',  # أزرق
        'order': 1,
    },
    'invoices_movement': {
        'id': 'invoices_movement',
        'label': _('الفواتير والحركة'),
        'icon': 'bi-file-text',
        'color': '#10b981',  # أخضر
        'order': 2,
    },
    'review_adjustments': {
        'id': 'review_adjustments',
        'label': _('المراجعة والتسويات'),
        'icon': 'bi-check2-square',
        'color': '#f59e0b',  # برتقالي
        'order': 3,
    },
    'reports_statements': {
        'id': 'reports_statements',
        'label': _('التقارير والميزانيات'),
        'icon': 'bi-graph-up-arrow',
        'color': '#8b5cf6',  # بنفسجي
        'order': 4,
    },
}


# البنية الجديدة للمحاسبة
ACCOUNTING_STRUCTURE = {
    'daily_basics': {
        'groups': [
            {
                'id': 'journal_entries',
                'label': _('القيود المحاسبية'),
                'icon': 'bi-journal-text',
                'items': [
                    {
                        'id': 'journal_entry_create',
                        'label': _('قيد جديد'),
                        'url': 'accounting:journal_entry_create',
                        'icon': 'bi-plus-square',
                        'shortcut': 'Ctrl+Alt+J',
                        'roles': ['cashier', 'accountant', 'cfo'],  # من يصل
                        'permissions': ['accounting.add_journalentry'],
                    },
                    {
                        'id': 'journal_entries_list',
                        'label': _('قائمة القيود'),
                        'url': 'accounting:journal_entries_list',
                        'icon': 'bi-list-ul',
                        'roles': ['cashier', 'accountant', 'cfo'],
                        'permissions': ['accounting.view_journalentry'],
                    },
                    {
                        'id': 'journal_drafts',
                        'label': _('قيود مسودة'),
                        'url': '/accounting/journal/drafts',
                        'icon': 'bi-exclamation-circle',
                        'badge_key': 'draft_journal_count',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_journalentry'],
                    },
                    {
                        'id': 'smart_entry',
                        'label': _('قيد ذكي'),
                        'url': 'accounting:smart_journal_entry_create',
                        'icon': 'bi-lightbulb',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.add_journalentry'],
                    },
                    {
                        'id': 'bulk_post',
                        'label': _('ترحيل مجموعة'),
                        'url': '/accounting/journal/drafts/bulk-post',
                        'icon': 'bi-check2-all',
                        'roles': ['cfo'],
                        'permissions': ['accounting.bulk_post_journal_entries'],
                    },
                ],
            },
            {
                'id': 'cash_banks',
                'label': _('الخزينة والبنوك'),
                'icon': 'bi-cash-coin',
                'items': [
                    {
                        'id': 'cash_receipt',
                        'label': _('سند قبض'),
                        'url': '/accounting/cash/receipt',
                        'icon': 'bi-arrow-down-circle',
                        'shortcut': 'Ctrl+Alt+R',
                        'roles': ['cashier', 'accountant', 'cfo'],
                        'permissions': ['accounting.add_cashreceipt'],
                    },
                    {
                        'id': 'cash_payment',
                        'label': _('سند صرف'),
                        'url': '/accounting/cash/payment/',
                        'icon': 'bi-arrow-up-circle',
                        'shortcut': 'Ctrl+Alt+P',
                        'roles': ['cashier', 'accountant', 'cfo'],
                        'permissions': ['accounting.add_cashpayment'],
                    },
                    {
                        'id': 'cash_transfer',
                        'label': _('تحويل نقدي'),
                        'url': '/accounting/cash/transfer',
                        'icon': 'bi-arrow-left-right',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.add_cashtransfer'],
                    },
                    {
                        'id': 'cash_positions',
                        'label': _('أرصدة الآن'),
                        'url': '/accounting/cash/positions',
                        'icon': 'bi-wallet2',
                        'badge_type': 'live',
                        'roles': ['cashier', 'accountant', 'cfo'],
                        'permissions': ['accounting.view_cashposition'],
                    },
                    {
                        'id': 'bank_reconcile',
                        'label': _('تسوية بنك'),
                        'url': '/accounting/bank/reconcile',
                        'icon': 'bi-bank',
                        'badge_key': 'bank_reconcile_pending',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.reconcile_bank'],
                    },
                ],
            },
            {
                'id': 'chart_of_accounts',
                'label': _('دليل الحسابات'),
                'icon': 'bi-diagram-3',
                'items': [
                    {
                        'id': 'accounts_list',
                        'label': _('دليل الحسابات'),
                        'url': 'accounting:chart_of_accounts',
                        'icon': 'bi-tree',
                        'roles': ['cashier', 'accountant', 'cfo'],
                        'permissions': ['accounting.view_account'],
                    },
                    {
                        'id': 'account_create',
                        'label': _('حساب جديد'),
                        'url': 'accounting:account_create',
                        'icon': 'bi-plus-circle',
                        'roles': ['cfo'],
                        'permissions': ['accounting.add_account'],
                    },
                    {
                        'id': 'expense_accounts',
                        'label': _('حسابات المصروفات'),
                        'url': 'accounting:expense_accounts',
                        'icon': 'bi-currency-dollar',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_account'],
                    },
                ],
            },
        ],
    },
    
    'invoices_movement': {
        'groups': [
            {
                'id': 'sales_customers',
                'label': _('المبيعات والعملاء'),
                'icon': 'bi-cart-check',
                'items': [
                    {
                        'id': 'sales_payments',
                        'label': _('مدفوعات المبيعات'),
                        'url': 'accounting:sales_payments_overview',
                        'icon': 'bi-cash-stack',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_sales_payment'],
                    },
                    {
                        'id': 'customer_statement',
                        'label': _('كشف حساب عميل'),
                        'url': '/accounting/sales/statement/',
                        'icon': 'bi-file-person',
                        'shortcut': 'Ctrl+Alt+S',
                        'roles': ['cashier', 'accountant', 'cfo'],
                        'permissions': ['accounting.view_customer_statement'],
                    },
                    {
                        'id': 'pending_invoices',
                        'label': _('فواتير معلقة'),
                        'url': '#',
                        'icon': 'bi-hourglass-split',
                        'badge_key': 'pending_invoices_count',
                        'roles': ['accountant', 'cfo'],
                    },
                ],
            },
            {
                'id': 'purchases_suppliers',
                'label': _('المشتريات والموردين'),
                'icon': 'bi-bag-plus',
                'items': [
                    {
                        'id': 'supplier_statement',
                        'label': _('كشف حساب مورد'),
                        'url': '#',
                        'icon': 'bi-file-person',
                        'roles': ['cashier', 'accountant', 'cfo'],
                        'permissions': ['accounting.view_supplier_statement'],
                    },
                    {
                        'id': 'suppliers_balances',
                        'label': _('أرصدة الموردين'),
                        'url': '#',
                        'icon': 'bi-wallet',
                        'roles': ['accountant', 'cfo'],
                    },
                    {
                        'id': 'pending_purchase_invoices',
                        'label': _('فواتير شراء معلقة'),
                        'url': '/accounting/pending-purchase-invoices/',
                        'icon': 'bi-exclamation-triangle',
                        'badge_key': 'pending_purchase_count',
                        'roles': ['accountant', 'cfo'],
                    },
                ],
            },
            {
                'id': 'cheques_banks',
                'label': _('الشيكات والبنوك'),
                'icon': 'bi-credit-card',
                'items': [
                    {
                        'id': 'cheques_list',
                        'label': _('حافظة الشيكات'),
                        'url': 'accounting:cheque_list',
                        'icon': 'bi-journals',
                        'roles': ['cashier', 'accountant', 'cfo'],
                        'permissions': ['accounting.view_cheque'],
                    },
                    {
                        'id': 'cheque_create',
                        'label': _('شيك جديد'),
                        'url': 'accounting:cheque_create',
                        'icon': 'bi-plus-square',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.add_cheque'],
                    },
                    {
                        'id': 'bank_statement_import',
                        'label': _('استيراد كشف بنك'),
                        'url': '/accounting/bank/import-statement',
                        'icon': 'bi-upload',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.import_bank_statement'],
                    },
                ],
            },
        ],
    },
    
    'review_adjustments': {
        'groups': [
            {
                'id': 'cost_centers',
                'label': _('مراكز التكلفة'),
                'icon': 'bi-building',
                'items': [
                    {
                        'id': 'cost_centers_list',
                        'label': _('قائمة المراكز'),
                        'url': 'accounting:cost_centers_list',
                        'icon': 'bi-list-ul',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_costcenter'],
                    },
                    {
                        'id': 'cost_center_create',
                        'label': _('مركز جديد'),
                        'url': 'accounting:cost_center_create',
                        'icon': 'bi-plus-circle',
                        'roles': ['cfo'],
                        'permissions': ['accounting.add_costcenter'],
                    },
                    {
                        'id': 'cost_allocations',
                        'label': _('توزيع التكاليف'),
                        'url': '/accounting/cost/allocations',
                        'icon': 'bi-pie-chart',
                        'roles': ['cfo'],
                        'permissions': ['accounting.allocate_cost'],
                    },
                ],
            },
            {
                'id': 'fixed_assets',
                'label': _('الأصول الثابتة'),
                'icon': 'bi-building',
                'items': [
                    {
                        'id': 'assets_overview',
                        'label': _('نظرة عامة على الأصول'),
                        'url': 'accounting:assets_overview',
                        'icon': 'bi-grid',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_asset'],
                    },
                    {
                        'id': 'asset_depreciation',
                        'label': _('إهلاك دوري'),
                        'url': '/accounting/assets/depreciation',
                        'icon': 'bi-clock-history',
                        'roles': ['cfo'],
                        'permissions': ['accounting.run_depreciation'],
                    },
                ],
            },
            {
                'id': 'period_closing',
                'label': _('التسويات والإقفالات'),
                'icon': 'bi-lock',
                'items': [
                    {
                        'id': 'period_adjustments',
                        'label': _('تسويات الفترة'),
                        'url': '/accounting/period/adjustments',
                        'icon': 'bi-sliders',
                        'roles': ['cfo'],
                        'permissions': ['accounting.add_period_adjustment'],
                    },
                    {
                        'id': 'recurring_entries',
                        'label': _('قيود متكررة'),
                        'url': '/accounting/journal/recurring',
                        'icon': 'bi-arrow-repeat',
                        'roles': ['cfo'],
                        'permissions': ['accounting.manage_recurring_entries'],
                    },
                    {
                        'id': 'trial_balance',
                        'label': _('ميزان المراجعة'),
                        'url': 'accounting:trial_balance',
                        'icon': 'bi-scale',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_trial_balance'],
                    },
                    {
                        'id': 'close_month',
                        'label': _('إقفال شهر'),
                        'url': '/accounting/period/close-month',
                        'icon': 'bi-calendar-x',
                        'roles': ['cfo'],
                        'permissions': ['accounting.close_month'],
                    },
                    {
                        'id': 'close_year',
                        'label': _('إقفال سنة'),
                        'url': '/accounting/period/close-year',
                        'icon': 'bi-archive',
                        'roles': ['cfo'],
                        'permissions': ['accounting.close_year'],
                    },
                ],
            },
        ],
    },
    
    'reports_statements': {
        'groups': [
            {
                'id': 'financial_statements',
                'label': _('القوائم المالية الأساسية'),
                'icon': 'bi-file-earmark-bar-graph',
                'items': [
                    {
                        'id': 'income_statement',
                        'label': _('قائمة الدخل'),
                        'url': 'accounting:income_statement',
                        'icon': 'bi-graph-up-arrow',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_income_statement'],
                    },
                    {
                        'id': 'balance_sheet',
                        'label': _('الميزانية العمومية'),
                        'url': 'accounting:balance_sheet',
                        'icon': 'bi-clipboard-data',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_balance_sheet'],
                    },
                    {
                        'id': 'cash_flow',
                        'label': _('التدفقات النقدية'),
                        'url': 'accounting:cash_flow_statement',
                        'icon': 'bi-water',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_cash_flow'],
                    },
                    {
                        'id': 'trial_balance_report',
                        'label': _('ميزان المراجعة'),
                        'url': 'accounting:trial_balance',
                        'icon': 'bi-scale',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_trial_balance'],
                    },
                    {
                        'id': 'general_ledger',
                        'label': _('دفتر الأستاذ العام'),
                        'url': 'accounting:general_ledger',
                        'icon': 'bi-book',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_general_ledger'],
                    },
                ],
            },
            {
                'id': 'analytical_reports',
                'label': _('التقارير التحليلية'),
                'icon': 'bi-graph-up',
                'items': [
                    {
                        'id': 'aging_receivables',
                        'label': _('أعمار الذمم المدينة'),
                        'url': '/accounting/reports/aging/receivables',
                        'icon': 'bi-hourglass-split',
                        'badge_key': 'overdue_receivables_count',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_aging_report'],
                    },
                    {
                        'id': 'aging_payables',
                        'label': _('أعمار الذمم الدائنة'),
                        'url': '/accounting/reports/aging/payables',
                        'icon': 'bi-hourglass',
                        'badge_key': 'upcoming_payables_count',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_aging_report'],
                    },
                    {
                        'id': 'tax_report',
                        'label': _('تقرير ضرائب'),
                        'url': '/accounting/reports/tax',
                        'icon': 'bi-receipt',
                        'roles': ['cfo'],
                        'permissions': ['accounting.view_tax_report'],
                    },
                    {
                        'id': 'cash_positions_report',
                        'label': _('المراكز النقدية'),
                        'url': '/accounting/cash/positions',
                        'icon': 'bi-cash-stack',
                        'badge_type': 'live',
                        'roles': ['accountant', 'cfo'],
                    },
                ],
            },
            {
                'id': 'loans_tools',
                'label': _('القروض والأدوات'),
                'icon': 'bi-bank2',
                'items': [
                    {
                        'id': 'loans_dashboard',
                        'label': _('لوحة القروض'),
                        'url': 'accounting:loans_dashboard',
                        'icon': 'bi-speedometer',
                        'roles': ['cfo'],
                        'permissions': ['accounting.view_loan'],
                    },
                    {
                        'id': 'loans_list',
                        'label': _('قائمة القروض'),
                        'url': 'accounting:loan_list',
                        'icon': 'bi-list-ul',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.view_loan'],
                    },
                    {
                        'id': 'import_journal',
                        'label': _('استيراد قيود'),
                        'url': '/accounting/tools/import-journal',
                        'icon': 'bi-upload',
                        'roles': ['cfo'],
                        'permissions': ['accounting.import_journal_entries'],
                    },
                    {
                        'id': 'export_data',
                        'label': _('تصدير بيانات'),
                        'url': '/accounting/tools/export',
                        'icon': 'bi-download',
                        'roles': ['accountant', 'cfo'],
                        'permissions': ['accounting.export_data'],
                    },
                ],
            },
        ],
    },
}


# الإعدادات المتقدمة (مخفية - للمدير المالي فقط)
ACCOUNTING_ADVANCED_SETTINGS = {
    'id': 'advanced_settings',
    'label': _('الإعدادات المتقدمة'),
    'icon': 'bi-gear',
    'roles': ['cfo'],
    'items': [
        {
            'id': 'accounting_settings',
            'label': _('إعدادات عامة'),
            'url': 'accounting:settings',
            'icon': 'bi-sliders',
            'permissions': ['accounting.manage_settings'],
        },
        {
            'id': 'default_accounts',
            'label': _('الحسابات الافتراضية'),
            'url': 'accounting:settings_defaults',
            'icon': 'bi-link',
            'permissions': ['accounting.manage_default_accounts'],
        },
        {
            'id': 'tax_settings',
            'label': _('إعدادات الضرائب'),
            'url': 'accounting:tax_settings',
            'icon': 'bi-percent',
            'permissions': ['accounting.manage_tax_settings'],
        },
        {
            'id': 'fiscal_year',
            'label': _('السنة المالية'),
            'url': 'accounting:fiscal_year_create',
            'icon': 'bi-calendar',
            'permissions': ['accounting.manage_fiscal_year'],
        },
        {
            'id': 'journal_templates',
            'label': _('قوالب القيود'),
            'url': 'accounting:journal_templates_list',
            'icon': 'bi-file-earmark-code',
            'permissions': ['accounting.view_journal_template'],
        },
        {
            'id': 'quick_fixes',
            'label': _('إصلاحات سريعة'),
            'url': '/accounting/tools/fixes',
            'icon': 'bi-wrench',
            'permissions': ['accounting.run_fixes'],
        },
        {
            'id': 'diagnostics',
            'label': _('تشخيص النظام'),
            'url': '/accounting/tools/diagnostics',
            'icon': 'bi-activity',
            'permissions': ['accounting.run_diagnostics'],
        },
    ],
}


def get_accounting_structure():
    """الحصول على البنية الكاملة للمحاسبة"""
    return {
        'tabs': ACCOUNTING_TABS,
        'structure': ACCOUNTING_STRUCTURE,
        'advanced': ACCOUNTING_ADVANCED_SETTINGS,
    }


def get_user_accounting_tabs(user):
    """
    الحصول على التبويبات المتاحة للمستخدم حسب دوره
    """
    from accounting.permissions import get_user_accounting_role, AccountingRoles
    
    if not user.is_authenticated:
        return []
    
    user_role = get_user_accounting_role(user)
    
    if not user_role:
        return []
    
    # الكاشير يرى فقط التبويب الأول والثاني (مبسط)
    if user_role == AccountingRoles.CASHIER:
        return ['daily_basics', 'invoices_movement']
    
    # المحاسب يرى كل التبويبات
    if user_role == AccountingRoles.ACCOUNTANT:
        return list(ACCOUNTING_TABS.keys())
    
    # المدير المالي يرى كل شيء + الإعدادات
    if user_role == AccountingRoles.CFO:
        return list(ACCOUNTING_TABS.keys())
    
    return []


def filter_items_by_user(items, user):
    """تصفية العناصر حسب صلاحيات المستخدم"""
    from accounting.permissions import get_user_accounting_role
    
    if not user.is_authenticated:
        return []
    
    user_role = get_user_accounting_role(user)
    if not user_role:
        return []
    
    # تحويل اسم الدور من المحاسبة إلى الشكل المستخدم في القوائم
    role_mapping = {
        'accounting_cashier': 'cashier',
        'accounting_accountant': 'accountant',
        'accounting_cfo': 'cfo',
    }
    
    simple_role = role_mapping.get(user_role, '')
    
    filtered_items = []
    for item in items:
        # التحقق من الدور
        if 'roles' in item and simple_role not in item['roles']:
            continue
        
        # التحقق من الصلاحيات
        if 'permissions' in item:
            has_perms = all(user.has_perm(perm) for perm in item['permissions'])
            if not has_perms:
                continue
        
        filtered_items.append(item)
    
    return filtered_items

