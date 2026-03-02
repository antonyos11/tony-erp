"""
إنشاء كل الصلاحيات والأدوار النظامية — RITA ERP
Sprint 22A
"""
from django.core.management.base import BaseCommand
from apps.authorization.models import SystemPermission, SystemRole


class Command(BaseCommand):
    help = 'إنشاء الصلاحيات والأدوار النظامية'

    def handle(self, *args, **options):
        self._create_permissions()
        self._create_roles()
        self.stdout.write(self.style.SUCCESS('✅ تم إنشاء الصلاحيات والأدوار'))

    def _create_permissions(self):
        """إنشاء كل الصلاحيات"""
        PERMISSIONS = [
            # Dashboard
            ('view_dashboard', 'dashboard', 'view', 'عرض لوحة التحكم', False),

            # المحاسبة
            ('view_accounts', 'accounts', 'view', 'عرض الحسابات', False),
            ('create_journal', 'accounts', 'create', 'إنشاء قيد', False),
            ('edit_journal', 'accounts', 'edit', 'تعديل قيد', False),
            ('post_journal', 'accounts', 'post', 'ترحيل قيد', True),
            ('close_fiscal_year', 'accounts', 'close', 'إقفال سنة مالية', True),
            ('view_cost_price', 'accounts', 'view_cost', 'رؤية سعر التكلفة', True),

            # المخزون
            ('view_inventory', 'inventory', 'view', 'عرض المخزون', False),
            ('create_product', 'inventory', 'create', 'إنشاء منتج', False),
            ('edit_product', 'inventory', 'edit', 'تعديل منتج', False),
            ('receive_stock', 'inventory', 'receive', 'استلام مخزون', False),
            ('issue_stock', 'inventory', 'issue', 'صرف مخزون', False),
            ('transfer_stock', 'inventory', 'transfer', 'تحويل مخزون', False),
            ('adjust_stock', 'inventory', 'adjust', 'تسوية مخزون', True),
            ('count_stock', 'inventory', 'count', 'جرد مخزون', False),

            # الإنتاج
            ('view_production', 'production', 'view', 'عرض الإنتاج', False),
            ('create_production', 'production', 'create', 'إنشاء أمر إنتاج', False),
            ('edit_production', 'production', 'edit', 'تعديل أمر إنتاج', False),
            ('approve_production', 'production', 'approve', 'اعتماد أمر إنتاج', True),
            ('start_production', 'production', 'start', 'بدء إنتاج', False),
            ('complete_production', 'production', 'complete', 'إكمال إنتاج', False),
            ('update_progress', 'production', 'update_progress', 'تحديث تقدم الإنتاج', False),
            ('report_waste', 'production', 'report_waste', 'تسجيل هالك', False),
            ('quality_check', 'production', 'quality_check', 'فحص جودة', False),

            # المبيعات
            ('view_sales', 'sales', 'view', 'عرض المبيعات', False),
            ('create_invoice', 'sales', 'create', 'إنشاء فاتورة', False),
            ('edit_invoice', 'sales', 'edit', 'تعديل فاتورة', False),
            ('approve_invoice', 'sales', 'approve', 'اعتماد فاتورة', True),
            ('cancel_invoice', 'sales', 'cancel', 'إلغاء فاتورة', True),
            ('give_discount', 'sales', 'give_discount', 'منح خصم', False),
            ('view_profit', 'sales', 'view_profit', 'رؤية الربح', True),

            # المشتريات
            ('view_purchases', 'purchases', 'view', 'عرض المشتريات', False),
            ('create_purchase', 'purchases', 'create', 'إنشاء أمر شراء', False),
            ('edit_purchase', 'purchases', 'edit', 'تعديل أمر شراء', False),
            ('approve_purchase', 'purchases', 'approve', 'اعتماد أمر شراء', True),

            # HR
            ('view_hr', 'hr', 'view', 'عرض الموارد البشرية', False),
            ('create_employee', 'hr', 'create', 'إنشاء موظف', False),
            ('edit_employee', 'hr', 'edit', 'تعديل موظف', False),
            ('approve_leave', 'hr', 'approve', 'اعتماد إجازة', False),
            ('manage_payroll', 'hr', 'payroll', 'إدارة الرواتب', True),

            # الخزينة
            ('view_treasury', 'treasury', 'view', 'عرض الخزينة', False),
            ('create_treasury', 'treasury', 'create', 'إنشاء عملية خزينة', False),
            ('approve_treasury', 'treasury', 'approve', 'اعتماد عملية خزينة', True),
            ('collect_payment', 'treasury', 'collect', 'تحصيل', False),

            # المصروفات
            ('view_expenses', 'expenses', 'view', 'عرض المصروفات', False),
            ('create_expense', 'expenses', 'create', 'إنشاء مصروف', False),
            ('approve_expense', 'expenses', 'approve', 'اعتماد مصروف', True),

            # CRM
            ('view_crm', 'crm', 'view', 'عرض CRM', False),
            ('create_crm', 'crm', 'create', 'إنشاء في CRM', False),
            ('edit_crm', 'crm', 'edit', 'تعديل في CRM', False),

            # عروض الأسعار
            ('view_quotations', 'quotations', 'view', 'عرض عروض الأسعار', False),
            ('create_quotation', 'quotations', 'create', 'إنشاء عرض سعر', False),
            ('edit_quotation', 'quotations', 'edit', 'تعديل عرض سعر', False),
            ('approve_quotation', 'quotations', 'approve', 'اعتماد عرض سعر', False),

            # التوصيل
            ('view_delivery', 'delivery', 'view', 'عرض التوصيل', False),
            ('create_delivery', 'delivery', 'create', 'إنشاء أمر توصيل', False),

            # الضمان
            ('view_warranty', 'warranty', 'view', 'عرض الضمان', False),

            # التقارير
            ('view_reports', 'reports', 'view', 'عرض التقارير', False),
            ('export_reports', 'reports', 'export', 'تصدير التقارير', False),

            # الإشعارات
            ('view_notifications', 'notifications', 'view', 'عرض الإشعارات', False),

            # الصلاحيات
            ('view_authorization', 'authorization', 'view', 'عرض الصلاحيات', False),
            ('manage_users', 'authorization', 'manage_users', 'إدارة المستخدمين', True),
            ('view_audit_log', 'authorization', 'audit_log', 'سجل المراجعة', True),

            # الإعدادات
            ('view_settings', 'settings', 'view', 'عرض الإعدادات', False),
            ('edit_settings', 'settings', 'edit', 'تعديل الإعدادات', True),
        ]

        created = 0
        for code, module, action, name, is_sensitive in PERMISSIONS:
            obj, was_created = SystemPermission.objects.get_or_create(
                code=code,
                defaults={
                    'module': module,
                    'action': action,
                    'name': name,
                    'is_sensitive': is_sensitive,
                }
            )
            if was_created:
                created += 1

        self.stdout.write(f"  صلاحيات: {created} جديدة من {len(PERMISSIONS)}")

    def _create_roles(self):
        """إنشاء الأدوار مع صلاحياتها"""

        ROLES = {
            'owner': {
                'name': 'مالك / مجلس إدارة',
                'description': 'رؤية كاملة لكل شيء — بدون تعديل مباشر',
                'scope': 'all',
                'sort_order': 1,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard', 'view_accounts', 'view_inventory', 'view_production',
                    'view_sales', 'view_purchases', 'view_hr', 'view_treasury', 'view_expenses',
                    'view_crm', 'view_quotations', 'view_delivery', 'view_warranty',
                    'view_reports', 'export_reports', 'view_notifications', 'view_authorization',
                    'view_settings', 'view_audit_log', 'view_cost_price', 'view_profit',
                ],
            },
            'ceo': {
                'name': 'مدير عام',
                'description': 'كل الفروع — اعتماد — بدون تدخل محاسبي مباشر',
                'scope': 'all',
                'sort_order': 2,
                'invoice_limit': 250000, 'expense_limit': 50000, 'return_limit': 50000, 'max_discount': 25,
                'permissions': [
                    'view_dashboard', 'view_accounts',
                    'view_inventory', 'create_product', 'edit_product',
                    'view_production', 'create_production', 'approve_production',
                    'view_sales', 'create_invoice', 'edit_invoice', 'approve_invoice', 'cancel_invoice',
                    'give_discount', 'view_profit',
                    'view_purchases', 'create_purchase', 'approve_purchase',
                    'view_hr', 'create_employee', 'edit_employee', 'approve_leave',
                    'view_treasury', 'approve_treasury',
                    'view_expenses', 'create_expense', 'approve_expense',
                    'view_crm', 'create_crm', 'edit_crm',
                    'view_quotations', 'create_quotation', 'edit_quotation', 'approve_quotation',
                    'view_delivery', 'create_delivery',
                    'view_warranty',
                    'view_reports', 'export_reports',
                    'view_notifications',
                    'view_authorization', 'manage_users',
                    'view_settings', 'edit_settings',
                ],
            },
            'cfo': {
                'name': 'مدير مالي',
                'description': 'كل الحسابات — اعتماد — إقفالات',
                'scope': 'all',
                'sort_order': 3,
                'invoice_limit': 999999999, 'expense_limit': 999999999, 'return_limit': 999999999, 'max_discount': 0,
                'permissions': [
                    'view_dashboard', 'view_accounts', 'create_journal', 'edit_journal',
                    'post_journal', 'close_fiscal_year', 'view_cost_price',
                    'view_treasury', 'create_treasury', 'approve_treasury',
                    'view_expenses', 'create_expense', 'approve_expense',
                    'view_reports', 'export_reports', 'view_profit',
                    'view_sales', 'view_purchases', 'view_hr',
                    'view_notifications',
                ],
            },
            'accountant_manager': {
                'name': 'مدير حسابات',
                'description': 'تشغيل الحسابات اليومية — بدون إقفال',
                'scope': 'all',
                'sort_order': 4,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard', 'view_accounts', 'create_journal', 'edit_journal', 'post_journal',
                    'view_treasury', 'create_treasury',
                    'view_expenses', 'create_expense',
                    'view_reports', 'export_reports',
                    'view_sales', 'view_purchases',
                    'view_notifications',
                ],
            },
            'branch_manager': {
                'name': 'مدير فرع',
                'description': 'فرعه فقط — كل العمليات',
                'scope': 'branch',
                'sort_order': 5,
                'invoice_limit': 50000, 'expense_limit': 10000, 'return_limit': 20000, 'max_discount': 15,
                'permissions': [
                    'view_dashboard',
                    'view_sales', 'create_invoice', 'edit_invoice', 'approve_invoice', 'cancel_invoice',
                    'give_discount',
                    'view_inventory', 'transfer_stock',
                    'view_purchases', 'create_purchase',
                    'view_crm', 'create_crm', 'edit_crm',
                    'view_quotations', 'create_quotation', 'edit_quotation', 'approve_quotation',
                    'view_delivery', 'create_delivery',
                    'view_warranty',
                    'view_hr',
                    'view_reports',
                    'view_expenses', 'create_expense',
                    'view_notifications',
                ],
            },
            'production_manager': {
                'name': 'مدير إنتاج',
                'description': 'كل خطوط الإنتاج',
                'scope': 'all',
                'sort_order': 6,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard',
                    'view_production', 'create_production', 'edit_production',
                    'approve_production', 'start_production', 'complete_production',
                    'update_progress', 'report_waste',
                    'view_inventory', 'issue_stock',
                    'view_hr',
                    'view_reports',
                    'view_notifications',
                ],
            },
            'production_supervisor': {
                'name': 'مشرف إنتاج',
                'description': 'خط إنتاجه فقط — إدخال كميات + هالك',
                'scope': 'production_line',
                'sort_order': 7,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard', 'view_production',
                    'update_progress', 'report_waste',
                    'view_inventory',
                    'view_notifications',
                ],
            },
            'production_planner': {
                'name': 'مخطط إنتاج',
                'description': 'تخطيط أوامر الإنتاج + BOM',
                'scope': 'all',
                'sort_order': 8,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard', 'view_production', 'create_production', 'edit_production',
                    'view_inventory',
                    'view_notifications',
                ],
            },
            'qc_inspector': {
                'name': 'مسؤول جودة',
                'description': 'فحص المنتجات + تسجيل هالك',
                'scope': 'all',
                'sort_order': 9,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard', 'view_production',
                    'quality_check', 'report_waste',
                    'view_inventory',
                    'view_notifications',
                ],
            },
            'storekeeper': {
                'name': 'أمين مخزن',
                'description': 'مخزنه فقط — استلام + صرف + جرد — بدون أسعار',
                'scope': 'warehouse',
                'sort_order': 10,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard',
                    'view_inventory', 'receive_stock', 'issue_stock', 'transfer_stock', 'count_stock',
                    'view_notifications',
                    # ❌ لا adjust_stock — الجرد يحتاج اعتماد
                    # ❌ لا view_cost_price
                ],
            },
            'accountant_purchases': {
                'name': 'محاسب مشتريات',
                'description': 'فرع واحد — مشتريات وموردين فقط',
                'scope': 'branch',
                'sort_order': 11,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard',
                    'view_purchases', 'create_purchase', 'edit_purchase',
                    'view_accounts', 'view_inventory',
                    'view_notifications',
                ],
            },
            'accountant_sales': {
                'name': 'محاسب مبيعات',
                'description': 'فرع واحد — مبيعات وعملاء فقط',
                'scope': 'branch',
                'sort_order': 12,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard',
                    'view_sales', 'create_invoice', 'edit_invoice',
                    'view_crm', 'create_crm', 'edit_crm',
                    'view_accounts', 'view_inventory',
                    'view_notifications',
                ],
            },
            'salesperson': {
                'name': 'بائع',
                'description': 'فرعه فقط — فواتير وعروض — بدون تكلفة أو ربح',
                'scope': 'branch',
                'sort_order': 13,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 5,
                'permissions': [
                    'view_dashboard',
                    'view_sales', 'create_invoice', 'give_discount',
                    'view_quotations', 'create_quotation', 'edit_quotation',
                    'view_crm', 'create_crm', 'edit_crm',
                    'view_inventory',
                    'view_notifications',
                    # ❌ لا view_cost_price
                    # ❌ لا view_profit
                    # ❌ لا cancel_invoice
                ],
            },
            'cashier': {
                'name': 'كاشير',
                'description': 'فرعه فقط — فواتير كاش + تحصيل — بدون مرتجع أو إلغاء',
                'scope': 'branch',
                'sort_order': 14,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard',
                    'view_sales', 'create_invoice',
                    'view_treasury', 'collect_payment',
                    'view_notifications',
                    # ❌ لا cancel_invoice
                    # ❌ لا give_discount
                ],
            },
            'delivery_driver': {
                'name': 'سائق توصيل',
                'description': 'أوامر التوصيل المسندة له فقط',
                'scope': 'assigned',
                'sort_order': 15,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard',
                    'view_delivery',
                    'view_notifications',
                ],
            },
            'hr_manager': {
                'name': 'مدير موارد بشرية',
                'description': 'كل الموظفين — رواتب — إجازات',
                'scope': 'all',
                'sort_order': 16,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard',
                    'view_hr', 'create_employee', 'edit_employee', 'approve_leave', 'manage_payroll',
                    'view_notifications',
                ],
            },
            'internal_auditor': {
                'name': 'مراجع داخلي',
                'description': 'رؤية كل شيء + Audit Log — بدون أي تعديل',
                'scope': 'all',
                'sort_order': 17,
                'invoice_limit': 0, 'expense_limit': 0, 'return_limit': 0, 'max_discount': 0,
                'permissions': [
                    'view_dashboard', 'view_accounts', 'view_cost_price',
                    'view_inventory', 'view_production', 'view_sales', 'view_profit',
                    'view_purchases', 'view_hr', 'view_treasury', 'view_expenses',
                    'view_crm', 'view_quotations', 'view_delivery', 'view_warranty',
                    'view_reports', 'export_reports',
                    'view_authorization', 'view_audit_log',
                    'view_settings',
                    'view_notifications',
                ],
            },
        }

        DELEGATION = {
            'owner': [],
            'ceo': ['owner'],
            'cfo': ['owner', 'ceo'],
            'accountant_manager': ['cfo', 'ceo'],
            'branch_manager': ['ceo'],
            'production_manager': ['ceo'],
            'production_supervisor': ['production_manager', 'ceo'],
            'production_planner': ['production_manager', 'ceo'],
            'qc_inspector': ['production_manager', 'ceo'],
            'storekeeper': ['branch_manager', 'ceo'],
            'accountant_purchases': ['cfo', 'accountant_manager', 'ceo'],
            'accountant_sales': ['cfo', 'accountant_manager', 'ceo'],
            'salesperson': ['branch_manager', 'ceo'],
            'cashier': ['branch_manager', 'ceo'],
            'delivery_driver': ['branch_manager', 'ceo'],
            'hr_manager': ['ceo'],
            'internal_auditor': ['owner', 'ceo'],
        }

        created_roles = {}
        for code, data in ROLES.items():
            role, was_created = SystemRole.objects.update_or_create(
                code=code,
                defaults={
                    'name': data['name'],
                    'description': data['description'],
                    'scope': data['scope'],
                    'sort_order': data['sort_order'],
                    'invoice_approval_limit': data['invoice_limit'],
                    'expense_approval_limit': data['expense_limit'],
                    'return_approval_limit': data['return_limit'],
                    'max_discount_percentage': data['max_discount'],
                    'is_system': True,
                    'is_active': True,
                }
            )

            perms = SystemPermission.objects.filter(code__in=data['permissions'])
            role.permissions.set(perms)

            created_roles[code] = role
            status = "✅ أُنشئ" if was_created else "🔄 حُدّث"
            self.stdout.write(f"  {status}: {role.name}")

        # تعيين التفويض الهرمي
        for code, granters in DELEGATION.items():
            if code in created_roles:
                granter_roles = [created_roles[g] for g in granters if g in created_roles]
                created_roles[code].can_be_granted_by.set(granter_roles)

        self.stdout.write(f"  إجمالي الأدوار: {len(ROLES)}")
