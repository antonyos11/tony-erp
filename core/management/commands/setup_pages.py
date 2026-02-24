"""
أمر لإعداد الصفحات الأساسية للنظام
"""
from django.core.management.base import BaseCommand
from core.models import Page


class Command(BaseCommand):
    help = 'إعداد الصفحات الأساسية للنظام'

    def handle(self, *args, **options):
        pages_data = [
            # لوحة التحكم
            {'name': 'لوحة التحكم', 'code': 'dashboard', 'url': '/dashboard/', 'module': 'dashboard', 'icon': 'bi-speedometer2', 'order': 1},
            
            # الحسابات
            {'name': 'شجرة الحسابات', 'code': 'accounts_tree', 'url': '/accounting/accounts/', 'module': 'accounting', 'icon': 'bi-diagram-3', 'order': 1},
            {'name': 'دليل الحسابات', 'code': 'chart_of_accounts', 'url': '/accounting/chart/', 'module': 'accounting', 'icon': 'bi-list-nested', 'order': 2},
            {'name': 'القيود اليومية', 'code': 'journal_entries', 'url': '/accounting/journal-entries/', 'module': 'accounting', 'icon': 'bi-journal-text', 'order': 3},
            {'name': 'السنوات المالية', 'code': 'fiscal_years', 'url': '/accounting/fiscal-years/', 'module': 'accounting', 'icon': 'bi-calendar-range', 'order': 4},
            {'name': 'مراكز التكلفة', 'code': 'cost_centers', 'url': '/accounting/cost-centers/', 'module': 'accounting', 'icon': 'bi-bullseye', 'order': 5},
            {'name': 'التقارير المالية', 'code': 'financial_reports', 'url': '/accounting/reports/', 'module': 'accounting', 'icon': 'bi-file-earmark-bar-graph', 'order': 6},
            
            # المخزون
            {'name': 'المنتجات', 'code': 'products', 'url': '/inventory/products/', 'module': 'inventory', 'icon': 'bi-box', 'order': 1},
            {'name': 'المخازن', 'code': 'warehouses', 'url': '/inventory/warehouses/', 'module': 'inventory', 'icon': 'bi-building', 'order': 2},
            {'name': 'التصنيفات', 'code': 'categories', 'url': '/inventory/categories/', 'module': 'inventory', 'icon': 'bi-tags', 'order': 3},
            {'name': 'حركات المخزون', 'code': 'stock_movements', 'url': '/inventory/movements/', 'module': 'inventory', 'icon': 'bi-arrow-left-right', 'order': 4},
            {'name': 'الجرد', 'code': 'stock_count', 'url': '/inventory/stock-count/', 'module': 'inventory', 'icon': 'bi-clipboard-check', 'order': 5},
            {'name': 'تقارير المخزون', 'code': 'inventory_reports', 'url': '/inventory/reports/', 'module': 'inventory', 'icon': 'bi-file-earmark-spreadsheet', 'order': 6},
            
            # المبيعات
            {'name': 'فواتير المبيعات', 'code': 'sales_invoices', 'url': '/sales/invoices/', 'module': 'sales', 'icon': 'bi-receipt', 'order': 1},
            {'name': 'عروض الأسعار', 'code': 'quotations', 'url': '/sales/quotations/', 'module': 'sales', 'icon': 'bi-file-earmark-text', 'order': 2},
            {'name': 'أوامر البيع', 'code': 'sales_orders', 'url': '/sales/orders/', 'module': 'sales', 'icon': 'bi-cart-check', 'order': 3},
            {'name': 'المرتجعات', 'code': 'sales_returns', 'url': '/sales/returns/', 'module': 'sales', 'icon': 'bi-arrow-return-left', 'order': 4},
            {'name': 'تقارير المبيعات', 'code': 'sales_reports', 'url': '/sales/reports/', 'module': 'sales', 'icon': 'bi-graph-up', 'order': 5},
            
            # المشتريات
            {'name': 'فواتير المشتريات', 'code': 'purchase_invoices', 'url': '/purchases/invoices/', 'module': 'purchases', 'icon': 'bi-receipt-cutoff', 'order': 1},
            {'name': 'أوامر الشراء', 'code': 'purchase_orders', 'url': '/purchases/orders/', 'module': 'purchases', 'icon': 'bi-bag-check', 'order': 2},
            {'name': 'طلبات الشراء', 'code': 'purchase_requests', 'url': '/purchases/requests/', 'module': 'purchases', 'icon': 'bi-file-earmark-plus', 'order': 3},
            {'name': 'الموردين', 'code': 'suppliers', 'url': '/partners/suppliers/', 'module': 'purchases', 'icon': 'bi-truck', 'order': 4},
            {'name': 'تقارير المشتريات', 'code': 'purchase_reports', 'url': '/purchases/reports/', 'module': 'purchases', 'icon': 'bi-file-earmark-bar-graph', 'order': 5},
            
            # الموارد البشرية
            {'name': 'الموظفين', 'code': 'employees', 'url': '/hr/employees/', 'module': 'hr', 'icon': 'bi-people', 'order': 1},
            {'name': 'الأقسام', 'code': 'departments', 'url': '/hr/departments/', 'module': 'hr', 'icon': 'bi-diagram-2', 'order': 2},
            {'name': 'الحضور والانصراف', 'code': 'attendance', 'url': '/hr/attendance/', 'module': 'hr', 'icon': 'bi-clock-history', 'order': 3},
            {'name': 'الإجازات', 'code': 'leaves', 'url': '/hr/leaves/', 'module': 'hr', 'icon': 'bi-calendar-x', 'order': 4},
            {'name': 'الرواتب', 'code': 'payroll', 'url': '/hr/payroll/', 'module': 'hr', 'icon': 'bi-wallet2', 'order': 5},
            {'name': 'تقارير الموارد البشرية', 'code': 'hr_reports', 'url': '/hr/reports/', 'module': 'hr', 'icon': 'bi-file-earmark-person', 'order': 6},
            
            # العملاء CRM
            {'name': 'العملاء', 'code': 'customers', 'url': '/partners/customers/', 'module': 'crm', 'icon': 'bi-person-badge', 'order': 1},
            {'name': 'جهات الاتصال', 'code': 'contacts', 'url': '/crm/contacts/', 'module': 'crm', 'icon': 'bi-person-lines-fill', 'order': 2},
            {'name': 'الفرص البيعية', 'code': 'opportunities', 'url': '/crm/opportunities/', 'module': 'crm', 'icon': 'bi-star', 'order': 3},
            {'name': 'المهام', 'code': 'tasks', 'url': '/crm/tasks/', 'module': 'crm', 'icon': 'bi-check2-square', 'order': 4},
            
            # الإنتاج
            {'name': 'أوامر الإنتاج', 'code': 'production_orders', 'url': '/production/orders/', 'module': 'production', 'icon': 'bi-gear', 'order': 1},
            {'name': 'خطوط الإنتاج', 'code': 'production_lines', 'url': '/production/lines/', 'module': 'production', 'icon': 'bi-layers', 'order': 2},
            {'name': 'قوائم المواد', 'code': 'bom', 'url': '/production/bom/', 'module': 'production', 'icon': 'bi-list-ul', 'order': 3},
            {'name': 'تقارير الإنتاج', 'code': 'production_reports', 'url': '/production/reports/', 'module': 'production', 'icon': 'bi-clipboard-data', 'order': 4},
            
            # الأسطول
            {'name': 'المركبات', 'code': 'vehicles', 'url': '/fleet/vehicles/', 'module': 'fleet', 'icon': 'bi-truck-front', 'order': 1},
            {'name': 'السائقين', 'code': 'drivers', 'url': '/fleet/drivers/', 'module': 'fleet', 'icon': 'bi-person-badge-fill', 'order': 2},
            {'name': 'الوقود', 'code': 'fuel', 'url': '/fleet/fuel/', 'module': 'fleet', 'icon': 'bi-fuel-pump', 'order': 3},
            {'name': 'الصيانة', 'code': 'fleet_maintenance', 'url': '/fleet/maintenance/', 'module': 'fleet', 'icon': 'bi-wrench', 'order': 4},
            {'name': 'تقارير الأسطول', 'code': 'fleet_reports', 'url': '/fleet/reports/', 'module': 'fleet', 'icon': 'bi-file-earmark-ruled', 'order': 5},
            
            # نقاط البيع
            {'name': 'شاشة البيع', 'code': 'pos_screen', 'url': '/pos/', 'module': 'pos', 'icon': 'bi-display', 'order': 1},
            {'name': 'الفواتير', 'code': 'pos_invoices', 'url': '/pos/invoices/', 'module': 'pos', 'icon': 'bi-receipt', 'order': 2},
            {'name': 'الورديات', 'code': 'pos_shifts', 'url': '/pos/shifts/', 'module': 'pos', 'icon': 'bi-clock', 'order': 3},
            {'name': 'تقارير نقطة البيع', 'code': 'pos_reports', 'url': '/pos/reports/', 'module': 'pos', 'icon': 'bi-bar-chart', 'order': 4},
            
            # التقارير
            {'name': 'التقارير العامة', 'code': 'general_reports', 'url': '/reports/', 'module': 'reports', 'icon': 'bi-file-earmark-text', 'order': 1},
            {'name': 'تقارير مخصصة', 'code': 'custom_reports', 'url': '/reports/custom/', 'module': 'reports', 'icon': 'bi-file-earmark-code', 'order': 2},
            {'name': 'لوحة البيانات', 'code': 'analytics', 'url': '/reports/analytics/', 'module': 'reports', 'icon': 'bi-graph-up-arrow', 'order': 3},
            
            # المشاريع
            {'name': 'قائمة المشاريع', 'code': 'projects_list', 'url': '/projects/', 'module': 'projects', 'icon': 'bi-kanban', 'order': 1},
            {'name': 'أنواع المشاريع', 'code': 'project_types', 'url': '/projects/types/', 'module': 'projects', 'icon': 'bi-folder', 'order': 2},
            {'name': 'المقاولين', 'code': 'contractors', 'url': '/projects/contractors/', 'module': 'projects', 'icon': 'bi-person-workspace', 'order': 3},
            {'name': 'تقارير المشاريع', 'code': 'project_reports', 'url': '/projects/reports/', 'module': 'projects', 'icon': 'bi-file-earmark-ruled', 'order': 4},
            
            # المقاولات
            {'name': 'العقود', 'code': 'contracts', 'url': '/contracting/contracts/', 'module': 'contracting', 'icon': 'bi-file-earmark-check', 'order': 1},
            {'name': 'المستخلصات', 'code': 'extracts', 'url': '/contracting/extracts/', 'module': 'contracting', 'icon': 'bi-file-earmark-diff', 'order': 2},
            {'name': 'خطابات الضمان', 'code': 'guarantees', 'url': '/contracting/guarantees/', 'module': 'contracting', 'icon': 'bi-shield-check', 'order': 3},
            
            # الشحن
            {'name': 'طلبات الشحن', 'code': 'shipping_orders', 'url': '/shipping/orders/', 'module': 'shipping', 'icon': 'bi-box-seam', 'order': 1},
            {'name': 'شركات الشحن', 'code': 'shipping_companies', 'url': '/shipping/companies/', 'module': 'shipping', 'icon': 'bi-truck', 'order': 2},
            {'name': 'تتبع الشحنات', 'code': 'shipment_tracking', 'url': '/shipping/tracking/', 'module': 'shipping', 'icon': 'bi-geo-alt', 'order': 3},
            
            # الخدمات الإلكترونية
            {'name': 'الخدمات', 'code': 'eservices_list', 'url': '/eservices/', 'module': 'eservices', 'icon': 'bi-globe', 'order': 1},
            {'name': 'طلبات الخدمات', 'code': 'service_requests', 'url': '/eservices/requests/', 'module': 'eservices', 'icon': 'bi-file-earmark-plus', 'order': 2},
            
            # الإعدادات
            {'name': 'إعدادات النظام', 'code': 'system_settings', 'url': '/settings/', 'module': 'settings', 'icon': 'bi-gear', 'order': 1},
            {'name': 'المستخدمين', 'code': 'users', 'url': '/users/list/', 'module': 'settings', 'icon': 'bi-people', 'order': 2},
            {'name': 'الأدوار', 'code': 'roles', 'url': '/users/roles/', 'module': 'settings', 'icon': 'bi-shield', 'order': 3},
            {'name': 'الصلاحيات', 'code': 'permissions', 'url': '/users/permissions/', 'module': 'settings', 'icon': 'bi-key', 'order': 4},
            {'name': 'الفروع', 'code': 'branches', 'url': '/branches/', 'module': 'settings', 'icon': 'bi-building', 'order': 5},
            {'name': 'العملات', 'code': 'currencies', 'url': '/currencies/', 'module': 'settings', 'icon': 'bi-currency-exchange', 'order': 6},
            {'name': 'الدول', 'code': 'countries', 'url': '/countries/', 'module': 'settings', 'icon': 'bi-globe2', 'order': 7},
            {'name': 'المحافظات', 'code': 'states', 'url': '/states/', 'module': 'settings', 'icon': 'bi-map', 'order': 8},
            {'name': 'سجل النظام', 'code': 'audit_log', 'url': '/audit-log/', 'module': 'settings', 'icon': 'bi-journal-text', 'order': 9},
            {'name': 'النسخ الاحتياطي', 'code': 'backup', 'url': '/backup/', 'module': 'settings', 'icon': 'bi-cloud-download', 'order': 10},
        ]

        created_count = 0
        updated_count = 0
        
        for page_data in pages_data:
            page, created = Page.objects.update_or_create(
                code=page_data['code'],
                defaults={
                    'name': page_data['name'],
                    'url': page_data['url'],
                    'module': page_data['module'],
                    'icon': page_data['icon'],
                    'order': page_data['order'],
                    'is_active': True,
                    'is_menu_item': True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'تم إضافة {created_count} صفحة جديدة وتحديث {updated_count} صفحة موجودة'
        ))
