from django.core.management.base import BaseCommand
from users.models import UserRole, ResourcePermission

DEFAULT_RESOURCES = {
    # module: {resource: [actions]}
    'sales': {
        'dashboard': ['view'],
        'invoice_list': ['view', 'export', 'print'],
        'invoice_create': ['add'],
        'pricing_offers': ['change'],
    },
    'fleet': {
        'dashboard': ['view'],
        'vehicle_list': ['view'],
        'driver_list': ['view'],
        'trip_create': ['add'],
    },
    'inventory': {
        'stock_management': ['view'],
        'product_list': ['view', 'export'],
        'product_create': ['add'],
        'receiving_create': ['add'],
        'receiving_list': ['view'],
        'issue_create': ['add'],
        'issue_list': ['view'],
        'count_create': ['add'],
        'count_list': ['view'],
        'warehouse_summary': ['view'],
    },
    'accounting': {
        'dashboard': ['view'],
        'journal_entry_create': ['add'],
        'journal_entries_list': ['view'],
        'journal_templates_list': ['view'],
        'general_ledger': ['view'],
        'trial_balance': ['view'],
        'balance_sheet': ['view'],
        'income_statement': ['view'],
        'cash_flow_statement': ['view'],
    },
    'crm': {
        'dashboard': ['view'],
        'customer_list': ['view'],
        'opportunity_list': ['view'],
        'quotation_list': ['view'],
        'reports_dashboard': ['view'],
    },
    'purchases': {
        'purchase_list': ['view'],
        'purchase_create': ['add'],
        'po_list': ['view'],
        'po_create': ['add'],
    },
    'hr': {
        'dashboard': ['view'],
        'employee_list': ['view'],
        'job_vacancy_create': ['add'],
    },
}

class Command(BaseCommand):
    help = 'مزامنة صلاحيات الموارد الافتراضية للأدوار النشطة'

    def handle(self, *args, **options):
        created_count = 0
        for role in UserRole.objects.filter(is_active=True):
            for module, resources in DEFAULT_RESOURCES.items():
                for resource, actions in resources.items():
                    for action in actions:
                        rp, created = ResourcePermission.objects.get_or_create(
                            role=role,
                            module=module,
                            resource=resource,
                            action=action,
                            defaults={'is_allowed': True, 'description': 'افتراضي'}
                        )
                        if created:
                            created_count += 1
        self.stdout.write(self.style.SUCCESS(f'تم إنشاء {created_count} صلاحيات موارد جديدة'))
