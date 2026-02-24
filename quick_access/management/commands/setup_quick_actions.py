"""
Management command لإضافة الإجراءات السريعة الافتراضية
"""
from django.core.management.base import BaseCommand
from quick_access.models import QuickAction


class Command(BaseCommand):
    help = 'إضافة الإجراءات السريعة الافتراضية للنظام'

    def handle(self, *args, **options):
        actions = [
            # المبيعات
            {
                'name': 'فاتورة مبيعات جديدة',
                'name_en': 'New Sales Invoice',
                'description': 'إنشاء فاتورة مبيعات جديدة',
                'icon': 'bi-receipt',
                'url': '/sales/new/',
                'category': 'sales',
                'color': '#10b981',
                'keyboard_shortcut': 'Ctrl+Shift+I',
                'permission_required': 'sales.add_invoice',
                'sort_order': 1
            },
            {
                'name': 'عرض أسعار',
                'name_en': 'New Quotation',
                'description': 'إنشاء عرض سعر للعميل',
                'icon': 'bi-file-text',
                'url': '/sales/new/',
                'category': 'sales',
                'color': '#10b981',
                'keyboard_shortcut': 'Ctrl+Shift+Q',
                'permission_required': 'sales.add_quotation',
                'sort_order': 2
            },
            {
                'name': 'قائمة الفواتير',
                'name_en': 'Invoices List',
                'description': 'عرض جميع فواتير المبيعات',
                'icon': 'bi-list-ul',
                'url': '/sales/',
                'category': 'sales',
                'color': '#10b981',
                'keyboard_shortcut': 'Alt+S+L',
                'permission_required': 'sales.view_invoice',
                'sort_order': 3
            },
            
            # المشتريات
            {
                'name': 'فاتورة مشتريات جديدة',
                'name_en': 'New Purchase Bill',
                'description': 'إنشاء فاتورة مشتريات',
                'icon': 'bi-cart-plus',
                'url': '/purchases/new/',
                'category': 'purchases',
                'color': '#3b82f6',
                'keyboard_shortcut': 'Ctrl+Shift+P',
                'permission_required': 'purchases.add_purchasebill',
                'sort_order': 1
            },
            {
                'name': 'قائمة المشتريات',
                'name_en': 'Purchases List',
                'description': 'عرض جميع فواتير المشتريات',
                'icon': 'bi-cart',
                'url': '/purchases/',
                'category': 'purchases',
                'color': '#3b82f6',
                'keyboard_shortcut': 'Alt+P+L',
                'permission_required': 'purchases.view_purchasebill',
                'sort_order': 2
            },
            
            # المخزون
            {
                'name': 'منتج جديد',
                'name_en': 'New Product',
                'description': 'إضافة منتج جديد للمخزون',
                'icon': 'bi-box-seam',
                'url': '/inventory/products/add/',
                'category': 'inventory',
                'color': '#f59e0b',
                'keyboard_shortcut': 'Ctrl+Shift+N',
                'permission_required': 'inventory.add_product',
                'sort_order': 1
            },
            {
                'name': 'جرد المخزون',
                'name_en': 'Stock Count',
                'description': 'إجراء جرد للمخزون',
                'icon': 'bi-clipboard-check',
                'url': '/inventory/count/',
                'category': 'inventory',
                'color': '#f59e0b',
                'keyboard_shortcut': 'Alt+I+C',
                'permission_required': 'inventory.view_stock',
                'sort_order': 2
            },
            {
                'name': 'حركة مخزنية',
                'name_en': 'Stock Movement',
                'description': 'تسجيل حركة مخزنية',
                'icon': 'bi-arrow-left-right',
                'url': '/inventory/transfers/',
                'category': 'inventory',
                'color': '#f59e0b',
                'keyboard_shortcut': 'Ctrl+Shift+M',
                'permission_required': 'inventory.add_stockmovement',
                'sort_order': 3
            },
            {
                'name': 'تقرير المخزون',
                'name_en': 'Stock Report',
                'description': 'عرض تقرير المخزون الحالي',
                'icon': 'bi-graph-up',
                'url': '/inventory/reports/valuation/',
                'category': 'inventory',
                'color': '#f59e0b',
                'keyboard_shortcut': 'Alt+I+R',
                'permission_required': 'inventory.view_stock',
                'sort_order': 4
            },
            
            # المحاسبة
            {
                'name': 'قيد يومية',
                'name_en': 'Journal Entry',
                'description': 'إنشاء قيد يومية محاسبي',
                'icon': 'bi-journal-text',
                'url': '/accounting/journal-entries/create/',
                'category': 'accounting',
                'color': '#8b5cf6',
                'keyboard_shortcut': 'Ctrl+Shift+J',
                'permission_required': 'accounting.add_journalentry',
                'sort_order': 1
            },
            {
                'name': 'دليل الحسابات',
                'name_en': 'Chart of Accounts',
                'description': 'عرض دليل الحسابات',
                'icon': 'bi-list-nested',
                'url': '/accounting/accounts/',
                'category': 'accounting',
                'color': '#8b5cf6',
                'keyboard_shortcut': 'Alt+A+C',
                'permission_required': 'accounting.view_account',
                'sort_order': 2
            },
            {
                'name': 'تقرير الأرباح والخسائر',
                'name_en': 'P&L Report',
                'description': 'قائمة الدخل',
                'icon': 'bi-pie-chart',
                'url': '/accounting/income-statement/',
                'category': 'accounting',
                'color': '#8b5cf6',
                'keyboard_shortcut': 'Alt+A+P',
                'permission_required': 'accounting.view_journalentry',
                'sort_order': 3
            },
            {
                'name': 'الميزانية العمومية',
                'name_en': 'Balance Sheet',
                'description': 'عرض الميزانية العمومية',
                'icon': 'bi-bar-chart',
                'url': '/accounting/balance-sheet/',
                'category': 'accounting',
                'color': '#8b5cf6',
                'keyboard_shortcut': 'Alt+A+B',
                'permission_required': 'accounting.view_journalentry',
                'sort_order': 4
            },
            
            # الموارد البشرية
            {
                'name': 'موظف جديد',
                'name_en': 'New Employee',
                'description': 'إضافة موظف جديد',
                'icon': 'bi-person-plus',
                'url': '/hr/employees/create/',
                'category': 'hr',
                'color': '#ec4899',
                'keyboard_shortcut': 'Ctrl+Shift+E',
                'permission_required': 'hr.add_employee',
                'sort_order': 1
            },
            {
                'name': 'طلب إجازة',
                'name_en': 'Leave Request',
                'description': 'تقديم طلب إجازة',
                'icon': 'bi-calendar-event',
                'url': '/hr/leaves/request/create/',
                'category': 'hr',
                'color': '#ec4899',
                'keyboard_shortcut': 'Ctrl+Shift+L',
                'permission_required': 'hr.add_leaverequest',
                'sort_order': 2
            },
            {
                'name': 'سجل الحضور',
                'name_en': 'Attendance',
                'description': 'عرض سجل الحضور',
                'icon': 'bi-clock',
                'url': '/attendance/',
                'category': 'hr',
                'color': '#ec4899',
                'keyboard_shortcut': 'Alt+H+A',
                'permission_required': 'attendance.view_attendance',
                'sort_order': 3
            },
            
            # إدارة العملاء CRM
            {
                'name': 'عميل جديد',
                'name_en': 'New Lead',
                'description': 'إضافة عميل محتمل',
                'icon': 'bi-person-add',
                'url': '/crm/',
                'category': 'crm',
                'color': '#06b6d4',
                'keyboard_shortcut': 'Ctrl+Shift+C',
                'permission_required': 'crm.add_lead',
                'sort_order': 1
            },
            {
                'name': 'فرصة بيع',
                'name_en': 'New Opportunity',
                'description': 'إنشاء فرصة بيع جديدة',
                'icon': 'bi-trophy',
                'url': '/crm/',
                'category': 'crm',
                'color': '#06b6d4',
                'keyboard_shortcut': 'Ctrl+Shift+O',
                'permission_required': 'crm.add_opportunity',
                'sort_order': 2
            },
            {
                'name': 'لوحة CRM',
                'name_en': 'CRM Dashboard',
                'description': 'لوحة تحكم إدارة العملاء',
                'icon': 'bi-speedometer2',
                'url': '/crm/',
                'category': 'crm',
                'color': '#06b6d4',
                'keyboard_shortcut': 'Alt+C+D',
                'permission_required': 'crm.view_lead',
                'sort_order': 3
            },
            
            # التقارير
            {
                'name': 'تقرير المبيعات',
                'name_en': 'Sales Report',
                'description': 'تقرير شامل للمبيعات',
                'icon': 'bi-file-earmark-bar-graph',
                'url': '/sales/reports/',
                'category': 'reports',
                'color': '#14b8a6',
                'keyboard_shortcut': 'Alt+R+S',
                'permission_required': 'sales.view_invoice',
                'sort_order': 1
            },
            {
                'name': 'تقرير العملاء',
                'name_en': 'Customers Report',
                'description': 'تقرير حسابات العملاء',
                'icon': 'bi-people',
                'url': '/sales/customers/',
                'category': 'reports',
                'color': '#14b8a6',
                'keyboard_shortcut': 'Alt+R+C',
                'permission_required': 'sales.view_customer',
                'sort_order': 2
            },
            {
                'name': 'منشئ التقارير',
                'name_en': 'Report Builder',
                'description': 'إنشاء تقارير مخصصة',
                'icon': 'bi-wrench',
                'url': '/reports/',
                'category': 'reports',
                'color': '#14b8a6',
                'keyboard_shortcut': 'Alt+R+B',
                'permission_required': '',
                'sort_order': 3
            },
            
            # الإعدادات
            {
                'name': 'المستخدمون',
                'name_en': 'Users',
                'description': 'إدارة المستخدمين والصلاحيات',
                'icon': 'bi-person-gear',
                'url': '/users/',
                'category': 'settings',
                'color': '#64748b',
                'keyboard_shortcut': 'Alt+S+U',
                'permission_required': 'auth.view_user',
                'sort_order': 1
            },
            {
                'name': 'إعدادات الشركة',
                'name_en': 'Company Settings',
                'description': 'إعدادات معلومات الشركة',
                'icon': 'bi-building',
                'url': '/dashboard/company-settings/',
                'category': 'settings',
                'color': '#64748b',
                'keyboard_shortcut': 'Alt+S+C',
                'permission_required': 'core.change_company',
                'sort_order': 2
            },
            {
                'name': 'الفروع',
                'name_en': 'Branches',
                'description': 'إدارة فروع الشركة',
                'icon': 'bi-shop',
                'url': '/branches/',
                'category': 'settings',
                'color': '#64748b',
                'keyboard_shortcut': 'Alt+S+B',
                'permission_required': 'branches.view_branch',
                'sort_order': 3
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for action_data in actions:
            action, created = QuickAction.objects.get_or_create(
                name=action_data['name'],
                defaults=action_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء: {action.name}'))
            else:
                # تحديث البيانات الموجودة
                for key, value in action_data.items():
                    setattr(action, key, value)
                action.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'○ تم تحديث: {action.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ تم بنجاح!'))
        self.stdout.write(self.style.SUCCESS(f'   إجراءات جديدة: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'   إجراءات محدثة: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'   الإجمالي: {created_count + updated_count}'))
