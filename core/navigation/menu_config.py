"""
تعريف بنية القوائم الرئيسية للنظام
Main Menu Structure Configuration

هذا الملف يحدد كل القوائم والبنود في النظام مع الصلاحيات المطلوبة لكل بند.
"""

from core.security.role_definitions import *

# ============================================================================
# Menu Structure Definition
# ============================================================================

MAIN_MENU_STRUCTURE = [
    {
        'id': 'dashboard',
        'label': 'لوحة التحكم',
        'icon': 'fas fa-tachometer-alt',
        'url': 'core:dashboard',
        'permission': None,  # الكل يرى لوحة التحكم
        'order': 1,
    },
    
    # ==========================================================================
    # المحاسبة
    # ==========================================================================
    {
        'id': 'accounting',
        'label': 'المحاسبة',
        'icon': 'fas fa-calculator',
        'url': None,
        'permission': {'module': 'accounting', 'action': 'view'},
        'order': 2,
        'children': [
            {
                'id': 'accounting_dashboard',
                'label': 'لوحة المحاسبة',
                'url': 'accounting:dashboard',
                'permission': {'module': 'accounting', 'action': 'view'},
            },
            {
                'id': 'chart_of_accounts',
                'label': 'دليل الحسابات',
                'url': 'accounting:chart_of_accounts',
                'permission': {'module': 'accounting', 'action': 'view'},
            },
            {
                'id': 'journal_entries',
                'label': 'القيود اليومية',
                'url': 'accounting:journal_entries_list',
                'permission': {'module': 'accounting', 'action': 'view'},
            },
            {
                'id': 'journal_add',
                'label': 'قيد جديد',
                'url': 'accounting:journal_entry_create',
                'permission': {'module': 'accounting', 'action': 'add'},
            },
            {
                'id': 'cash_flow',
                'label': 'التدفقات النقدية',
                'url': 'accounting:cash_flow_statement',
                'permission': {'module': 'accounting', 'action': 'view'},
            },
            {
                'id': 'trial_balance',
                'label': 'ميزان المراجعة',
                'url': 'accounting:trial_balance',
                'permission': {'module': 'accounting', 'action': 'view'},
            },
            {
                'id': 'income_statement',
                'label': 'قائمة الدخل',
                'url': 'accounting:income_statement',
                'permission': {'module': 'accounting', 'action': 'view'},
                'roles_only': [ROLE_OWNER, ROLE_FIN_MANAGER],  # حساسة
            },
            {
                'id': 'balance_sheet',
                'label': 'الميزانية العمومية',
                'url': 'accounting:balance_sheet',
                'permission': {'module': 'accounting', 'action': 'view'},
                'roles_only': [ROLE_OWNER, ROLE_FIN_MANAGER],
            },
            {
                'id': 'period_closing',
                'label': 'إقفال الفترات',
                'url': 'accounting:period_close_month',
                'permission': {'module': 'accounting', 'action': 'approve'},
                'roles_only': [ROLE_OWNER, ROLE_FIN_MANAGER],
            },
        ],
    },
    
    # ==========================================================================
    # المخزون
    # ==========================================================================
    {
        'id': 'inventory',
        'label': 'المخزون',
        'icon': 'fas fa-boxes',
        'url': None,
        'permission': {'module': 'inventory', 'action': 'view'},
        'order': 3,
        'children': [
            {
                'id': 'inventory_dashboard',
                'label': 'لوحة المخزون',
                'url': 'inventory:dashboard',
                'permission': {'module': 'inventory', 'action': 'view'},
            },
            {
                'id': 'products',
                'label': 'الأصناف',
                'url': 'inventory:product_list',
                'permission': {'module': 'inventory', 'action': 'view'},
            },
            {
                'id': 'product_add',
                'label': 'صنف جديد',
                'url': 'inventory:product_add',
                'permission': {'module': 'inventory', 'action': 'add'},
                'roles_only': [ROLE_OWNER, ROLE_WAREHOUSE_MANAGER, ROLE_STORE_SUPERVISOR, ROLE_BRANCHES_MANAGER],
            },
            {
                'id': 'warehouses',
                'label': 'المخازن',
                'url': 'inventory:location_list',
                'permission': {'module': 'inventory', 'action': 'view'},
            },
            {
                'id': 'stock_movements',
                'label': 'حركات المخزون',
                'url': 'inventory:transfer_list',
                'permission': {'module': 'inventory', 'action': 'view'},
            },
            {
                'id': 'receive_voucher',
                'label': 'إذن استلام',
                'url': 'inventory:receiving_create',
                'permission': {'module': 'inventory', 'action': 'add'},
            },
            {
                'id': 'issue_voucher',
                'label': 'إذن صرف',
                'url': 'inventory:issue_create',
                'permission': {'module': 'inventory', 'action': 'add'},
            },
            {
                'id': 'stock_count',
                'label': 'الجرد',
                'url': 'inventory:stock_management',
                'permission': {'module': 'inventory', 'action': 'approve'},
                'roles_only': [ROLE_OWNER, ROLE_WAREHOUSE_MANAGER, ROLE_STORE_SUPERVISOR, ROLE_BRANCHES_MANAGER],
            },
            {
                'id': 'low_stock_report',
                'label': 'تقرير النواقص',
                'url': 'inventory:stock_management',
                'permission': {'module': 'inventory', 'action': 'view'},
            },
        ],
    },
    
    # ==========================================================================
    # المبيعات
    # ==========================================================================
    {
        'id': 'sales',
        'label': 'المبيعات',
        'icon': 'fas fa-shopping-cart',
        'url': None,
        'permission': {'module': 'sales', 'action': 'view'},
        'order': 4,
        'children': [
            {
                'id': 'sales_dashboard',
                'label': 'لوحة المبيعات',
                'url': 'sales:dashboard',
                'permission': {'module': 'sales', 'action': 'view'},
            },
            {
                'id': 'invoices',
                'label': 'الفواتير',
                'url': 'sales:invoice_list',
                'permission': {'module': 'sales', 'action': 'view'},
            },
            {
                'id': 'invoice_add',
                'label': 'فاتورة جديدة',
                'url': 'sales:invoice_create',
                'permission': {'module': 'sales', 'action': 'add'},
            },
            {
                'id': 'quotations',
                'label': 'عروض الأسعار',
                'url': 'sales:dashboard',
                'permission': {'module': 'sales', 'action': 'view'},
            },
            {
                'id': 'quotation_add',
                'label': 'عرض سعر جديد',
                'url': 'sales:invoice_create',
                'permission': {'module': 'sales', 'action': 'add'},
            },
            {
                'id': 'customers',
                'label': 'العملاء',
                'url': 'partners:customers_list',
                'permission': {'module': 'sales', 'action': 'view'},
            },
            {
                'id': 'sales_report',
                'label': 'تقارير المبيعات',
                'url': 'reports:sales_report',
                'permission': {'module': 'sales', 'action': 'view'},
            },
        ],
    },
    
    # ==========================================================================
    # المشتريات
    # ==========================================================================
    {
        'id': 'purchases',
        'label': 'المشتريات',
        'icon': 'fas fa-truck',
        'url': None,
        'permission': {'module': 'purchases', 'action': 'view'},
        'order': 5,
        'children': [
            {
                'id': 'purchases_dashboard',
                'label': 'لوحة المشتريات',
                'url': 'purchases:purchase_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            # طلبات الشراء (PR)
            {
                'id': 'purchase_requests',
                'label': 'طلبات الشراء',
                'url': 'purchases:pr_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            {
                'id': 'purchase_request_add',
                'label': 'طلب شراء جديد',
                'url': 'purchases:pr_create',
                'permission': {'module': 'purchases', 'action': 'add'},
            },
            # طلب عروض الأسعار (RFQ)
            {
                'id': 'rfq_list',
                'label': 'طلبات عروض الأسعار',
                'url': 'purchases:rfq_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            {
                'id': 'rfq_add',
                'label': 'طلب عروض جديد',
                'url': 'purchases:rfq_create',
                'permission': {'module': 'purchases', 'action': 'add'},
            },
            # عروض الموردين
            {
                'id': 'quotations',
                'label': 'عروض الموردين',
                'url': 'purchases:quotation_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            # أوامر الشراء
            {
                'id': 'purchase_orders',
                'label': 'أوامر الشراء',
                'url': 'purchases:po_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            {
                'id': 'purchase_order_add',
                'label': 'أمر شراء جديد',
                'url': 'purchases:po_create',
                'permission': {'module': 'purchases', 'action': 'add'},
            },
            # الشحنات
            {
                'id': 'shipments',
                'label': 'الشحنات',
                'url': 'purchases:shipment_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            # استلام الواردات
            {
                'id': 'goods_receipts',
                'label': 'سندات الاستلام',
                'url': 'purchases:receipt_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            # الموردين
            {
                'id': 'suppliers',
                'label': 'الموردين',
                'url': 'partners:suppliers_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            # فواتير الشراء
            {
                'id': 'purchase_invoices',
                'label': 'فواتير الشراء',
                'url': 'purchases:purchase_list',
                'permission': {'module': 'purchases', 'action': 'view'},
            },
            # التقارير
            {
                'id': 'purchase_reports',
                'label': 'التقارير',
                'url': None,
                'permission': {'module': 'purchases', 'action': 'view'},
                'children': [
                    {
                        'id': 'supplier_material_prices',
                        'label': 'أسعار المواد الخام لكل مورد',
                        'url': 'purchases:supplier_material_prices',
                        'permission': {'module': 'purchases', 'action': 'view'},
                    },
                    {
                        'id': 'price_comparison',
                        'label': 'مقارنة الأسعار',
                        'url': 'purchases:price_comparison',
                        'permission': {'module': 'purchases', 'action': 'view'},
                    },
                    {
                        'id': 'supplier_performance',
                        'label': 'أداء الموردين',
                        'url': 'purchases:supplier_performance',
                        'permission': {'module': 'purchases', 'action': 'view'},
                    },
                    {
                        'id': 'purchasing_analytics',
                        'label': 'تحليلات المشتريات',
                        'url': 'purchases:purchasing_analytics',
                        'permission': {'module': 'purchases', 'action': 'view'},
                    },
                ],
            },
        ],
    },
    
    # ==========================================================================
    # الإنتاج
    # ==========================================================================
    {
        'id': 'production',
        'label': 'الإنتاج',
        'icon': 'fas fa-industry',
        'url': None,
        'permission': {'module': 'production', 'action': 'view'},
        'order': 6,
        'children': [
            {
                'id': 'production_dashboard',
                'label': 'لوحة الإنتاج',
                'url': 'production:dashboard',
                'permission': {'module': 'production', 'action': 'view'},
            },
            {
                'id': 'production_orders',
                'label': 'أوامر الإنتاج',
                'url': 'production:orders_list',
                'permission': {'module': 'production', 'action': 'view'},
            },
            {
                'id': 'production_order_add',
                'label': 'أمر إنتاج جديد',
                'url': 'production:create_order',
                'permission': {'module': 'production', 'action': 'add'},
            },
            {
                'id': 'product_units',
                'label': 'وحدات المنتجات',
                'url': 'production:unit_list',
                'permission': {'module': 'production', 'action': 'view'},
            },
            {
                'id': 'warranty_verify',
                'label': 'التحقق من الضمان',
                'url': 'production:warranty_verify_unit',
                'permission': {'module': 'production', 'action': 'view'},
            },
            {
                'id': 'bom',
                'label': 'قوائم المواد (BOM)',
                'url': 'production:dashboard',
                'permission': {'module': 'production', 'action': 'view'},
            },
            {
                'id': 'work_centers',
                'label': 'مراكز العمل',
                'url': 'production:work_centers_list',
                'permission': {'module': 'production', 'action': 'view'},
            },
        ],
    },
    
    # ==========================================================================
    # الموارد البشرية
    # ==========================================================================
    {
        'id': 'hr',
        'label': 'الموارد البشرية',
        'icon': 'fas fa-users',
        'url': None,
        # نجعلها مرئية لكل المستخدمين المسجلين الدخول لضمان ظهور قسم السلف
        'permission': None,
        'order': 7,
        'children': [
            {
                'id': 'hr_dashboard',
                'label': 'لوحة الموارد البشرية',
                'url': 'hr:dashboard',
                'permission': None,
            },
            {
                'id': 'employees',
                'label': 'الموظفين',
                'url': 'hr:employee_list',
                'permission': None,
            },
            {
                'id': 'attendance',
                'label': 'الحضور والانصراف',
                'url': 'hr:attendance_records',
                'permission': None,
            },
            {
                'id': 'leave_requests',
                'label': 'طلبات الإجازات',
                'url': 'hr:dashboard',
                'permission': None,
            },
            {
                'id': 'payroll',
                'label': 'كشوف الرواتب',
                'url': 'hr:dashboard',
                'permission': None,
            },
            {
                'id': 'loans',
                'label': 'إدارة السلف',
                'url': 'hr:loans_dashboard',
                'permission': {'module': 'hr', 'action': 'view'},
            },
            {
                'id': 'loans_list',
                'label': 'قائمة السلف',
                'url': 'hr:loans_list',
                'permission': {'module': 'hr', 'action': 'view'},
            },
            {
                'id': 'new_loan',
                'label': 'طلب سلفة جديدة',
                'url': 'hr:loan_request',
                'permission': None,
            },
            {
                'id': 'payroll_report',
                'label': 'كشف الراتب الشامل',
                'url': 'hr:payroll_comprehensive_report',
                'permission': None,
            },
        ],
    },
    
    # ==========================================================================
    # إدارة علاقات العملاء (CRM)
    # ==========================================================================
    {
        'id': 'crm',
        'label': 'علاقات العملاء',
        'icon': 'fas fa-handshake',
        'url': None,
        'permission': {'module': 'crm', 'action': 'view'},
        'order': 8,
        'children': [
            {
                'id': 'crm_dashboard',
                'label': 'لوحة CRM',
                'url': 'crm:dashboard',
                'permission': {'module': 'crm', 'action': 'view'},
            },
            {
                'id': 'leads',
                'label': 'العملاء المحتملين',
                'url': 'crm:customer_list',
                'permission': {'module': 'crm', 'action': 'view'},
            },
            {
                'id': 'opportunities',
                'label': 'الفرص',
                'url': 'crm:opportunity_list',
                'permission': {'module': 'crm', 'action': 'view'},
            },
            {
                'id': 'campaigns',
                'label': 'الحملات التسويقية',
                'url': 'crm:campaign_list',
                'permission': {'module': 'crm', 'action': 'view'},
            },
        ],
    },
    
    # ==========================================================================
    # المتجر الإلكتروني
    # ==========================================================================
    {
        'id': 'ecommerce',
        'label': 'المتجر الإلكتروني',
        'icon': 'fas fa-globe',
        'url': None,
        'permission': {'module': 'sales', 'action': 'view'},
        'order': 8.5,
        'children': [
            {
                'id': 'ecommerce_home',
                'label': 'الصفحة الرئيسية',
                'url': 'ecommerce:store_home',
                'permission': None,
            },
            {
                'id': 'ecommerce_products',
                'label': 'المنتجات',
                'url': 'ecommerce:product_list',
                'permission': None,
            },
            {
                'id': 'ecommerce_orders',
                'label': 'طلبات المتجر',
                'url': 'ecommerce:admin_orders',
                'permission': {'module': 'sales', 'action': 'view'},
            },
            {
                'id': 'warranty_landing',
                'label': 'صفحة الضمان',
                'url': 'ecommerce:warranty_landing',
                'permission': None,
            },
            {
                'id': 'warranty_check',
                'label': 'التحقق من الضمان',
                'url': 'ecommerce:warranty_check',
                'permission': None,
            },
            {
                'id': 'warranty_settings',
                'label': 'إعدادات الضمان',
                'url': 'ecommerce:warranty_settings',
                'permission': {'module': 'sales', 'action': 'edit'},
                'roles_only': [ROLE_OWNER, ROLE_SYS_ADMIN, ROLE_SALES_MANAGER],
            },
        ],
    },
    
    # ==========================================================================
    # نقاط البيع (POS)
    # ==========================================================================
    {
        'id': 'pos',
        'label': 'نقطة البيع',
        'icon': 'fas fa-cash-register',
        'url': 'pos:dashboard',
        'permission': {'module': 'pos', 'action': 'view'},
        'order': 9,
        'roles_only': [ROLE_OWNER, ROLE_SALES_MANAGER, ROLE_CASHIER],
    },
    
    # ==========================================================================
    # المعارض والفروع
    # ==========================================================================
    {
        'id': 'showrooms',
        'label': 'المعارض والفروع',
        'icon': 'fas fa-store-alt',
        'url': None,
        'permission': {'module': 'pos', 'action': 'view'},
        'order': 10,
        'children': [
            {
                'id': 'showrooms_dashboard',
                'label': 'لوحة المؤشرات',
                'url': 'showrooms:dashboard',
                'permission': {'module': 'pos', 'action': 'view'},
            },
            {
                'id': 'showrooms_list',
                'label': 'إدارة المعارض',
                'url': 'showrooms:list',
                'permission': {'module': 'pos', 'action': 'view'},
            },
            {
                'id': 'showrooms_create',
                'label': 'إضافة معرض',
                'url': 'showrooms:create',
                'permission': {'module': 'pos', 'action': 'add'},
                'roles_only': [ROLE_OWNER, ROLE_SYS_ADMIN, ROLE_BRANCHES_MANAGER],
            },
            {
                'id': 'showrooms_employees',
                'label': 'موظفي المعارض',
                'url': 'showrooms:employees_v2',
                'permission': {'module': 'pos', 'action': 'view'},
            },
            {
                'id': 'showrooms_kpis',
                'label': 'مؤشرات الأداء',
                'url': 'showrooms:kpis',
                'permission': {'module': 'pos', 'action': 'view'},
            },
            {
                'id': 'showrooms_pnl',
                'label': 'تقرير الأرباح والخسائر',
                'url': 'showrooms:pnl',
                'permission': {'module': 'pos', 'action': 'view'},
                'roles_only': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_BRANCHES_MANAGER],
            },
        ],
    },
    
    # ==========================================================================
    # الصيانة
    # ==========================================================================
    {
        'id': 'maintenance',
        'label': 'الصيانة',
        'icon': 'fas fa-tools',
        'url': None,
        'permission': {'module': 'maintenance', 'action': 'view'},
        'order': 11,
        'children': [
            {
                'id': 'maintenance_dashboard',
                'label': 'لوحة الصيانة',
                'url': 'maintenance:dashboard',
                'permission': {'module': 'maintenance', 'action': 'view'},
            },
            {
                'id': 'equipment',
                'label': 'المعدات',
                'url': 'maintenance:machine_list',
                'permission': {'module': 'maintenance', 'action': 'view'},
            },
            {
                'id': 'work_orders',
                'label': 'أوامر الصيانة',
                'url': 'maintenance:maintenance_request_list',
                'permission': {'module': 'maintenance', 'action': 'view'},
            },
        ],
    },
    
    # ==========================================================================
    # التقارير
    # ==========================================================================
    {
        'id': 'reports',
        'label': 'التقارير',
        'icon': 'fas fa-chart-bar',
        'url': None,
        'permission': {'module': 'reports', 'action': 'view'},
        'order': 11,
        'children': [
            {
                'id': 'reports_dashboard',
                'label': 'مركز التقارير',
                'url': 'reports:dashboard',
                'permission': {'module': 'reports', 'action': 'view'},
            },
            {
                'id': 'financial_reports',
                'label': 'التقارير المالية',
                'url': 'accounting:trial_balance',
                'permission': {'module': 'reports', 'action': 'view'},
                'roles_only': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_ACCOUNTANT],
            },
            {
                'id': 'sales_reports',
                'label': 'تقارير المبيعات',
                'url': 'reports:sales_report',
                'permission': {'module': 'reports', 'action': 'view'},
            },
            {
                'id': 'inventory_reports',
                'label': 'تقارير المخزون',
                'url': 'reports:inventory_report',
                'permission': {'module': 'reports', 'action': 'view'},
            },
            {
                'id': 'profit_reports',
                'label': 'تقارير الأرباح',
                'url': 'accounting:income_statement',
                'permission': {'module': 'reports', 'action': 'view'},
                'roles_only': [ROLE_OWNER, ROLE_FIN_MANAGER],
            },
        ],
    },
    
    # ==========================================================================
    # الإعدادات
    # ==========================================================================
    {
        'id': 'settings',
        'label': 'الإعدادات',
        'icon': 'fas fa-cog',
        'url': None,
        'permission': None,  # سيتم التحكم حسب البنود الفرعية
        'order': 12,
        'children': [
            {
                'id': 'company_settings',
                'label': 'إعدادات الشركة',
                'url': 'core:company_settings',
                'permission': None,
                'roles_only': [ROLE_OWNER, ROLE_SYS_ADMIN],
            },
            {
                'id': 'user_management',
                'label': 'إدارة المستخدمين',
                'url': 'users:dashboard',
                'permission': None,
                'roles_only': [ROLE_OWNER, ROLE_SYS_ADMIN],
            },
            {
                'id': 'role_management',
                'label': 'إدارة الأدوار',
                'url': 'users:role_list',
                'permission': None,
                'roles_only': [ROLE_OWNER, ROLE_SYS_ADMIN],
            },
            {
                'id': 'security_logs',
                'label': 'سجلات الأمان',
                'url': 'users:activity_log',
                'permission': None,
                'roles_only': [ROLE_OWNER, ROLE_SYS_ADMIN],
            },
            {
                'id': 'backup_restore',
                'label': 'النسخ الاحتياطي',
                'url': 'core:dashboard',
                'permission': None,
                'roles_only': [ROLE_OWNER, ROLE_SYS_ADMIN],
            },
            {
                'id': 'my_profile',
                'label': 'ملفي الشخصي',
                'url': 'users:profile',
                'permission': None,  # الكل يرى ملفه
            },
        ],
    },
]


# ============================================================================
# Dashboard Configurations per Role
# ============================================================================

ROLE_DASHBOARDS = {
    ROLE_OWNER: {
        'template': 'dashboards/owner_dashboard.html',
        'widgets': [
            'revenue_overview',
            'profit_summary',
            'sales_chart',
            'inventory_value',
            'pending_approvals',
            'top_products',
            'top_customers',
            'alerts',
        ],
    },
    
    ROLE_FIN_MANAGER: {
        'template': 'dashboards/financial_manager_dashboard.html',
        'widgets': [
            'accounts_summary',
            'pending_journal_entries',
            'cash_flow',
            'pending_invoices',
            'bank_balances',
            'expense_breakdown',
        ],
    },
    
    ROLE_ACCOUNTANT: {
        'template': 'dashboards/accountant_dashboard.html',
        'widgets': [
            'my_tasks',
            'pending_entries',
            'pending_vouchers',
            'recent_transactions',
            'bank_summary',
        ],
    },
    
    ROLE_WAREHOUSE_MANAGER: {
        'template': 'dashboards/inventory_manager_dashboard.html',
        'widgets': [
            'low_stock_items',
            'stock_movements_today',
            'pending_orders',
            'inventory_value',
            'expiry_alerts',
            'slow_moving_items',
        ],
    },
    
    ROLE_STORE_KEEPER: {
        'template': 'dashboards/store_keeper_dashboard.html',
        'widgets': [
            'pending_receives',
            'pending_issues',
            'today_movements',
            'warehouse_summary',
        ],
    },
    
    ROLE_SALES_MANAGER: {
        'template': 'dashboards/sales_manager_dashboard.html',
        'widgets': [
            'sales_overview',
            'pending_invoices',
            'pending_quotations',
            'team_performance',
            'top_customers',
            'sales_targets',
            'overdue_payments',
        ],
    },
    
    ROLE_SALES_REP_INTERNAL: {
        'template': 'dashboards/sales_staff_dashboard.html',
        'widgets': [
            'my_sales_today',
            'my_quotations',
            'my_targets',
            'my_customers',
            'my_performance',
        ],
    },

    ROLE_SALES_REP_EXTERNAL: {
        'template': 'dashboards/sales_staff_dashboard.html',
        'widgets': [
            'my_sales_today',
            'my_quotations',
            'my_targets',
            'my_customers',
            'my_performance',
        ],
    },
    
    ROLE_CASHIER: {
        'template': 'pos/pos_main.html',  # مباشرة إلى POS
        'redirect_to': 'pos:dashboard',
    },
    
    ROLE_PROD_MANAGER: {
        'template': 'dashboards/production_manager_dashboard.html',
        'widgets': [
            'production_orders_status',
            'materials_needed',
            'production_efficiency',
            'work_centers_status',
            'waste_summary',
        ],
    },
    
    ROLE_HR_STAFF: {
        'template': 'dashboards/hr_staff_dashboard.html',
        'widgets': [
            'pending_leave_requests',
            'attendance_today',
            'payroll_tasks',
            'contract_renewals',
            'birthday_reminders',
        ],
    },
    
    ROLE_SYS_ADMIN: {
        'template': 'dashboards/sys_admin_dashboard.html',
        'widgets': [
            'system_status',
            'active_users',
            'security_alerts',
            'backup_status',
            'disk_usage',
            'error_logs',
        ],
    },
    
    ROLE_VIEWER: {
        'template': 'dashboards/viewer_dashboard.html',
        'widgets': [
            'overview_summary',
            'quick_reports',
        ],
    },
}



