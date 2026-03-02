"""
باني القوائم الديناميكي — RITA ERP
═══════════════════════════════════
يبني Sidebar حسب صلاحيات المستخدم
ما ليس له صلاحية عليه = غير موجود أصلاً في القائمة
"""
from django.urls import reverse, NoReverseMatch
from apps.authorization.services.permission_engine import PermissionEngine


def _safe_url(url_name, url_fallback=None):
    """يحوّل url_name إلى URL حقيقي — يعيد '#' إن لم يُعرَّف بعد"""
    if not url_name:
        return url_fallback or '#'
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return url_fallback or '#'


class MenuBuilder:
    """
    يبني القائمة الجانبية ديناميكياً حسب صلاحيات المستخدم
    """

    MENU_STRUCTURE = [
        {
            'id': 'dashboard',
            'title': 'لوحة التحكم',
            'icon': '🏠',
            'url_name': 'core:dashboard',
            'module': 'dashboard',
            'action': 'view',
            'children': [],
        },
        {
            'id': 'accounts',
            'title': 'المحاسبة',
            'icon': '📊',
            'module': 'accounts',
            'children': [
                {'title': 'دليل الحسابات', 'url_name': 'accounts:chart_of_accounts', 'action': 'view'},
                {'title': 'القيود المحاسبية', 'url_name': 'accounts:journal_list', 'action': 'view'},
                {'title': 'قيد يدوي جديد', 'url_name': 'accounts:journal_create', 'action': 'create'},
                {'title': 'ميزان المراجعة', 'url_name': 'accounts:trial_balance', 'action': 'view'},
                {'title': 'قائمة الدخل', 'url_name': 'accounts:income_statement', 'action': 'view'},
                {'title': 'المركز المالي', 'url_name': 'accounts:balance_sheet', 'action': 'view'},
                {'title': 'كشف حساب', 'url_name': 'accounts:account_statement', 'action': 'view'},
                {'title': '📊 WIP (تحت التشغيل)', 'url_name': 'accounts:wip_summary', 'action': 'view'},
                {'title': '💰 الميزانيات', 'url_name': 'accounts:budget_list', 'action': 'view'},
                {'title': '🏢 مراكز التكلفة', 'url_name': 'accounts:cost_center_list', 'action': 'view'},
                {'title': 'السنوات المالية', 'url_name': 'accounts:fiscal_year_list', 'action': 'view'},
            ],
        },
        {
            'id': 'inventory',
            'title': 'المخزون',
            'icon': '📦',
            'module': 'inventory',
            'children': [
                {'title': 'المنتجات', 'url_name': 'inventory:product_list', 'action': 'view'},
                {'title': 'إضافة منتج', 'url_name': 'inventory:product_create', 'action': 'create'},
                {'title': 'أرصدة المخزون', 'url_name': 'inventory:stock_levels', 'action': 'view'},
                {'title': 'حركات المخزون', 'url_name': 'inventory:stock_moves', 'action': 'view'},
                {'title': 'استلام مخزون', 'url_name': 'inventory:stock_receive', 'action': 'receive'},
                {'title': 'تحويل مخزون', 'url_name': 'inventory:stock_transfer', 'action': 'transfer'},
                {'title': 'تسوية جرد', 'url_name': 'inventory:stock_adjustment', 'action': 'adjust'},
                {'title': 'مخزون منخفض', 'url_name': 'inventory:low_stock', 'action': 'view'},
                {
                    'title': 'تقييم المخزون',
                    'url_name': 'inventory:valuation',
                    'action': 'view',
                    'extra_permission': ('inventory', 'view_cost'),
                },
                {'title': 'قوائم المواد (BOM)', 'url_name': 'inventory:bom_list', 'action': 'view'},
                {'title': 'التصنيفات', 'url_name': 'inventory:category_list', 'action': 'view'},
                {'title': 'الجرد المخزني', 'url_name': 'inventory:stock_count', 'action': 'count'},
            ],
        },
        {
            'id': 'production',
            'title': 'الإنتاج',
            'icon': '🏭',
            'module': 'production',
            'children': [
                {'title': 'أوامر الإنتاج', 'url_name': 'production:order_list', 'action': 'view'},
                {'title': 'أمر إنتاج جديد', 'url_name': 'production:order_create', 'action': 'create'},
                {
                    'title': 'تقرير التكاليف',
                    'url_name': 'production:cost_report',
                    'action': 'view',
                    'extra_permission': ('production', 'view_cost'),
                },
                {'title': 'شاشة الإنتاج', 'url_name': 'production:production_display', 'action': 'view'},
            ],
        },
        {
            'id': 'sales',
            'title': 'المبيعات',
            'icon': '🛒',
            'module': 'sales',
            'children': [
                {'title': 'الفواتير', 'url_name': 'sales:invoice_list', 'action': 'view'},
                {'title': 'فاتورة جديدة', 'url_name': 'sales:invoice_create', 'action': 'create'},
                {'title': 'العملاء', 'url_name': 'sales:customer_list', 'action': 'view'},
                {'title': 'المرتجعات', 'url_name': 'sales:return_list', 'action': 'view'},
                {'title': 'قوائم الأسعار', 'url_name': 'sales:price_lists', 'action': 'view'},
            ],
        },
        {
            'id': 'crm',
            'title': 'إدارة العملاء (CRM)',
            'icon': '🎯',
            'module': 'crm',
            'children': [
                {'title': 'لوحة CRM', 'url_name': 'crm:dashboard', 'action': 'view'},
                {'title': 'العملاء المحتملين', 'url_name': 'crm:lead_list', 'action': 'view'},
                {'title': 'Pipeline', 'url_name': 'crm:lead_kanban', 'action': 'view'},
                {'title': 'Lead جديد', 'url_name': 'crm:lead_create', 'action': 'create'},
                {'title': 'بحث عميل', 'url_name': 'crm:customer_search', 'action': 'view'},
                {'title': 'سجل التفاعلات', 'url_name': 'crm:interaction_list', 'action': 'view'},
                {'title': 'المتابعات', 'url_name': 'crm:follow_up_list', 'action': 'view'},
                {'title': 'الشكاوى', 'url_name': 'crm:complaint_list', 'action': 'view'},
                {'title': 'المهام', 'url_name': 'crm:task_list', 'action': 'view'},
                {'title': 'تصنيف العملاء', 'url_name': 'crm:rating_report', 'action': 'view'},
            ],
        },
        {
            'id': 'quotations',
            'title': 'عروض الأسعار',
            'icon': '📝',
            'module': 'quotations',
            'children': [
                {'title': 'عروض الأسعار', 'url_name': 'quotations:quotation_list', 'action': 'view'},
                {'title': 'عرض سعر جديد', 'url_name': 'quotations:quotation_create', 'action': 'create'},
                {'title': 'لوحة العروض', 'url_name': 'quotations:quotation_dashboard', 'action': 'view'},
            ],
        },
        {
            'id': 'purchases',
            'title': 'المشتريات',
            'icon': '📋',
            'module': 'purchases',
            'children': [
                {'title': 'أوامر الشراء', 'url_name': 'purchases:order_list', 'action': 'view'},
                {'title': 'أمر شراء جديد', 'url_name': 'purchases:order_create', 'action': 'create'},
                {'title': 'الموردين', 'url_name': 'purchases:supplier_list', 'action': 'view'},
            ],
        },
        {
            'id': 'hr',
            'title': 'الموارد البشرية',
            'icon': '👥',
            'module': 'hr',
            'children': [
                {'title': 'الموظفون', 'url_name': 'hr:employee_list', 'action': 'view'},
                {'title': 'إضافة موظف', 'url_name': 'hr:employee_create', 'action': 'create'},
                {'title': 'الحضور والانصراف', 'url_name': 'hr:attendance_list', 'action': 'view'},
                {'title': 'تسجيل حضور', 'url_name': 'hr:attendance_bulk', 'action': 'create'},
                {'title': 'الإجازات', 'url_name': 'hr:leave_list', 'action': 'view'},
                {'title': 'الجزاءات والمكافآت', 'url_name': 'hr:penalty_list', 'action': 'view'},
                {'title': 'السلف', 'url_name': 'hr:advance_list', 'action': 'view'},
                {'title': 'مسيّرات الرواتب', 'url_name': 'hr:payroll_list', 'action': 'payroll'},
                {'title': 'عمل بالقطعة', 'url_name': 'hr:piece_work_list', 'action': 'view'},
                {'title': 'الأقسام', 'url_name': 'hr:department_list', 'action': 'view'},
            ],
        },
        {
            'id': 'expenses',
            'title': 'المصروفات',
            'icon': '💸',
            'module': 'expenses',
            'children': [
                {'title': 'المصروفات', 'url_name': 'expenses:expense_list', 'action': 'view'},
                {'title': 'مصروف جديد', 'url_name': 'expenses:expense_create', 'action': 'create'},
                {'title': 'سندات الصرف', 'url_name': 'expenses:pv_list', 'action': 'view'},
                {'title': 'سند صرف جديد', 'url_name': 'expenses:pv_create', 'action': 'create'},
                {'title': 'سندات القبض', 'url_name': 'expenses:rv_list', 'action': 'view'},
                {'title': 'سند قبض جديد', 'url_name': 'expenses:rv_create', 'action': 'create'},
                {'title': 'العهد النثرية', 'url_name': 'expenses:petty_cash_list', 'action': 'view'},
                {'title': 'مصروفات دورية', 'url_name': 'expenses:recurring_list', 'action': 'view'},
                {'title': 'تقرير الميزانية', 'url_name': 'expenses:budget_report', 'action': 'view'},
            ],
        },
        {
            'id': 'treasury',
            'title': 'الخزينة والبنوك',
            'icon': '🏦',
            'module': 'treasury',
            'children': [
                {'title': 'الحسابات البنكية', 'url_name': 'treasury:bank_account_list', 'action': 'view'},
                {'title': 'الخزن', 'url_name': 'treasury:cashbox_list', 'action': 'view'},
                {'title': 'الشيكات', 'url_name': 'treasury:check_list', 'action': 'view'},
                {'title': 'التحويلات', 'url_name': 'treasury:transfer_list', 'action': 'view'},
                {'title': 'المطابقة البنكية', 'url_name': 'treasury:bank_reconciliation', 'action': 'view'},
            ],
        },
        {
            'id': 'reports',
            'title': 'التقارير',
            'icon': '📈',
            'module': 'reports',
            'children': [
                {'title': 'ملخص المبيعات', 'url_name': 'reports:sales_summary', 'action': 'view'},
                {
                    'title': 'الربحية',
                    'url_name': 'reports:profitability',
                    'action': 'view',
                    'extra_permission': ('reports', 'view_profit'),
                },
                {
                    'title': 'تكلفة المنتج',
                    'url_name': 'reports:product_cost',
                    'action': 'view',
                    'extra_permission': ('reports', 'view_cost'),
                },
                {'title': 'أداء الفروع', 'url_name': 'reports:branch_scorecard', 'action': 'view'},
                {'title': 'أعمار الديون', 'url_name': 'reports:aging', 'action': 'view'},
                {'title': 'مخزون راكد', 'url_name': 'reports:dead_stock', 'action': 'view'},
                {'title': 'تقرير ضريبي', 'url_name': 'reports:vat_report', 'action': 'view'},
            ],
        },
        {
            'id': 'authorization',
            'title': 'الصلاحيات',
            'icon': '🔐',
            'module': 'authorization',
            'children': [
                {'title': 'الأدوار (قديم)', 'url_name': 'authorization:role_list', 'action': 'view'},
                {'title': 'تعيين دور (قديم)', 'url_name': 'authorization:assign_role', 'action': 'manage_users'},
                {'title': 'الأدوار النظامية', 'url_name': 'authorization:system_role_list', 'action': 'view'},
                {'title': 'تعيين دور نظامي', 'url_name': 'authorization:assign_system_role', 'action': 'manage_users'},
                {'title': 'سجل المراجعة', 'url_name': 'authorization:audit_log', 'action': 'audit_log'},
                {'title': 'سجل الأمان', 'url_name': 'authorization:security_violations', 'action': 'audit_log'},
                {'title': 'التفويضات', 'url_name': 'authorization:delegation_list', 'action': 'view'},
                # Sprint 23
                {'title': '📋 طلبات الاعتماد', 'url_name': 'authorization:approval_list', 'action': 'view'},
                {'title': '🙋 طلباتي', 'url_name': 'authorization:my_requests', 'action': 'view'},
            ],
        },
        {
            'id': 'settings',
            'title': 'الإعدادات',
            'icon': '⚙️',
            'module': 'settings',
            'children': [
                {'title': 'الفروع', 'url_name': 'core:branch_list', 'action': 'view'},
                {'title': 'المخازن', 'url_name': 'core:warehouse_list', 'action': 'view'},
                {'title': 'المستخدمون', 'url_name': 'core:user_list', 'action': 'manage_users'},
                {'title': 'لوحة الإدارة', 'url_name': None, 'url': '/admin/', 'action': 'manage_users'},
            ],
        },
    ]

    @classmethod
    def build_menu(cls, user):
        """
        بناء القائمة الجانبية حسب صلاحيات المستخدم
        Returns: list of menu sections with only permitted items
        """
        if not user or not user.is_authenticated:
            return []

        user_modules = set(PermissionEngine.get_user_modules(user))
        is_super = user.is_superuser

        menu = []

        for section in cls.MENU_STRUCTURE:
            module = section.get('module', '')

            # Dashboard — الكل يشوفه
            if section['id'] == 'dashboard':
                dash = dict(section)
                dash['href'] = _safe_url(section.get('url_name'), '/')
                menu.append(dash)
                continue

            # هل المستخدم له صلاحية في هذا القسم؟
            if not is_super and module not in user_modules:
                continue

            # فلترة العناصر الفرعية
            if section.get('children'):
                visible_children = []
                for child in section['children']:
                    child_action = child.get('action', 'view')

                    if is_super or PermissionEngine.has_permission(user, module, child_action):
                        extra = child.get('extra_permission')
                        if extra:
                            if not is_super and not PermissionEngine.has_permission(
                                    user, extra[0], extra[1]):
                                continue
                        visible_children.append(child)

                if visible_children:
                    section_copy = dict(section)
                    section_copy['children'] = visible_children
                    # pre-compute hrefs
                    for child in section_copy['children']:
                        if 'href' not in child:
                            child['href'] = _safe_url(
                                child.get('url_name'), child.get('url', '#')
                            )
                    menu.append(section_copy)
            else:
                if is_super or PermissionEngine.has_permission(user, module, 'view'):
                    menu.append(section)

        return menu
