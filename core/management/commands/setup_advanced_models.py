"""
أمر إدارة لإنشاء البيانات الأولية للنماذج المتقدمة
يُستخدم بعد تشغيل makemigrations و migrate
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'إعداد البيانات الأولية للنماذج المتقدمة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='إعادة إنشاء البيانات حتى لو كانت موجودة',
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('إعداد النماذج المتقدمة - Tony ERP')
        self.stdout.write('=' * 60)

        self._setup_security_policy()
        self._setup_sla()
        self._setup_sample_workflow()

        self.stdout.write(self.style.SUCCESS('\n✅ تم الإعداد بنجاح'))

    def _setup_security_policy(self):
        """إنشاء سياسة الأمان الافتراضية"""
        try:
            from accounts.models_permissions import SecurityPolicy
            policy = SecurityPolicy.get_policy()
            self.stdout.write(f'  ✓ سياسة الأمان: موجودة (pk={policy.pk})')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ سياسة الأمان: {e}'))

    def _setup_sla(self):
        """إنشاء إعدادات SLA الافتراضية"""
        try:
            from crm.models_advanced import SupportSLA

            sla_defaults = [
                {
                    'name': 'SLA حرج',
                    'priority': 'critical',
                    'first_response_hours': 1,
                    'resolution_hours': 4,
                    'escalation_after_hours': 2,
                },
                {
                    'name': 'SLA عالي',
                    'priority': 'high',
                    'first_response_hours': 4,
                    'resolution_hours': 8,
                    'escalation_after_hours': 6,
                },
                {
                    'name': 'SLA متوسط',
                    'priority': 'medium',
                    'first_response_hours': 8,
                    'resolution_hours': 24,
                    'escalation_after_hours': 16,
                },
                {
                    'name': 'SLA منخفض',
                    'priority': 'low',
                    'first_response_hours': 24,
                    'resolution_hours': 72,
                    'escalation_after_hours': 48,
                },
            ]

            created = 0
            for sla_data in sla_defaults:
                _, is_new = SupportSLA.objects.get_or_create(
                    priority=sla_data['priority'],
                    defaults=sla_data
                )
                if is_new:
                    created += 1

            self.stdout.write(
                f'  ✓ SLA: {created} جديد، {len(sla_defaults)} إجمالي'
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ SLA: {e}'))

    def _setup_sample_workflow(self):
        """إنشاء سير عمل نموذجي"""
        try:
            from accounts.models_workflow import ApprovalWorkflow, ApprovalStep
            from django.contrib.auth.models import Group

            manager_group, _ = Group.objects.get_or_create(name='مدير')
            finance_group, _ = Group.objects.get_or_create(name='مالي')
            ceo_group, _ = Group.objects.get_or_create(name='مدير عام')

            workflow, created = ApprovalWorkflow.objects.get_or_create(
                document_type='purchase_order',
                defaults={
                    'name': 'موافقة أوامر الشراء',
                    'is_active': True,
                    'apply_to_all_branches': True,
                }
            )

            if created:
                ApprovalStep.objects.create(
                    workflow=workflow,
                    step_order=1,
                    name='موافقة المدير',
                    approver_role=manager_group,
                    min_amount=0,
                    max_amount=50000,
                    timeout_hours=24,
                )
                ApprovalStep.objects.create(
                    workflow=workflow,
                    step_order=2,
                    name='موافقة المالي',
                    approver_role=finance_group,
                    min_amount=10000,
                    timeout_hours=48,
                )
                ApprovalStep.objects.create(
                    workflow=workflow,
                    step_order=3,
                    name='موافقة المدير العام',
                    approver_role=ceo_group,
                    min_amount=50000,
                    timeout_hours=72,
                )
                self.stdout.write(
                    f'  ✓ سير عمل: تم إنشاء "{workflow.name}" مع 3 خطوات'
                )
            else:
                self.stdout.write(f'  ✓ سير عمل: "{workflow.name}" موجود')

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ سير العمل: {e}'))
