"""
خدمات الصلاحيات والموافقات - Permission & Approval Services
=============================================================
طبقة خدمات تغلف منطق التحقق من الصلاحيات والموافقات.
"""

from django.db.models import Q
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PermissionService:
    """خدمة التحقق من الصلاحيات"""

    @staticmethod
    def get_user_branches(user):
        """الحصول على الفروع المتاحة للمستخدم"""
        from accounts.models_permissions import UserBranchPermission

        if user.is_superuser:
            from branches.models import Branch
            return Branch.objects.filter(is_active=True)

        branch_ids = UserBranchPermission.objects.filter(
            user=user,
            can_view=True
        ).values_list('branch_id', flat=True)

        from branches.models import Branch
        return Branch.objects.filter(pk__in=branch_ids, is_active=True)

    @staticmethod
    def get_default_branch(user):
        """الحصول على الفرع الافتراضي للمستخدم"""
        from accounts.models_permissions import UserBranchPermission

        try:
            perm = UserBranchPermission.objects.select_related('branch').get(
                user=user,
                is_default_branch=True
            )
            return perm.branch
        except UserBranchPermission.DoesNotExist:
            first_perm = UserBranchPermission.objects.filter(
                user=user,
                can_view=True
            ).select_related('branch').first()
            return first_perm.branch if first_perm else None

    @staticmethod
    def can_user_access_branch(user, branch, action='view'):
        """
        التحقق من إمكانية وصول المستخدم للفرع
        action: view, create, edit, delete, approve, export
        """
        from accounts.models_permissions import UserBranchPermission

        if user.is_superuser:
            return True

        action_field_map = {
            'view': 'can_view',
            'create': 'can_create',
            'edit': 'can_edit',
            'delete': 'can_delete',
            'approve': 'can_approve',
            'export': 'can_export',
        }

        field_name = action_field_map.get(action, 'can_view')

        # Support passing branch_id or branch object
        branch_id = branch.pk if hasattr(branch, 'pk') else branch

        try:
            perm = UserBranchPermission.objects.get(
                user=user,
                branch_id=branch_id
            )
            return getattr(perm, field_name, False)
        except UserBranchPermission.DoesNotExist:
            return False

    @staticmethod
    def check_financial_authority(user, branch, amount):
        """التحقق من الصلاحية المالية"""
        from accounts.models_permissions import UserBranchPermission

        if user.is_superuser:
            return True

        branch_id = branch.pk if hasattr(branch, 'pk') else branch

        try:
            perm = UserBranchPermission.objects.get(
                user=user,
                branch_id=branch_id
            )
            return perm.has_financial_authority(Decimal(str(amount)))
        except UserBranchPermission.DoesNotExist:
            return False

    @staticmethod
    def get_data_access_level(user, module):
        """الحصول على مستوى الوصول للبيانات حسب الوحدة"""
        from accounts.models_permissions import DataAccessRule

        if user.is_superuser:
            return 'all_branches'

        user_groups = user.groups.all()
        rules = DataAccessRule.objects.filter(
            role__in=user_groups,
            module=module,
            is_active=True
        )

        if not rules.exists():
            return 'own_only'

        access_priority = {
            'own_only': 1,
            'own_branch': 2,
            'own_department': 3,
            'selected_branches': 4,
            'all_branches': 5,
        }

        highest = max(rules, key=lambda r: access_priority.get(r.access_level, 0))
        return highest.access_level

    @staticmethod
    def filter_queryset_by_access(queryset, user, module, branch_field='branch'):
        """
        تصفية QuerySet حسب صلاحيات الوصول
        يُستخدم في Views لتقييد البيانات المعروضة
        """
        if user.is_superuser:
            return queryset

        access_level = PermissionService.get_data_access_level(user, module)

        if access_level == 'all_branches':
            return queryset
        elif access_level == 'own_branch':
            default_branch = PermissionService.get_default_branch(user)
            if default_branch:
                return queryset.filter(**{branch_field: default_branch})
            return queryset.none()
        elif access_level == 'own_only':
            if hasattr(queryset.model, 'created_by'):
                return queryset.filter(created_by=user)
            elif hasattr(queryset.model, 'user'):
                return queryset.filter(user=user)
            elif hasattr(queryset.model, 'assigned_to'):
                return queryset.filter(assigned_to=user)
            return queryset.none()
        elif access_level == 'selected_branches':
            user_branches = PermissionService.get_user_branches(user)
            return queryset.filter(**{f'{branch_field}__in': user_branches})

        return queryset.none()


class ApprovalService:
    """خدمة إدارة الموافقات"""

    @staticmethod
    def create_approval_request(document_type, document_id, amount, user,
                                branch=None, document_number='', notes=''):
        """إنشاء طلب موافقة جديد لمستند"""
        from accounts.models_workflow import (
            ApprovalWorkflow, ApprovalRequest, ApprovalAction
        )

        workflows = ApprovalWorkflow.objects.filter(
            document_type=document_type,
            is_active=True
        )

        if branch:
            workflows = workflows.filter(
                Q(apply_to_all_branches=True) |
                Q(branches=branch)
            )

        workflow = workflows.first()

        if not workflow:
            logger.info(
                f"لا يوجد سير عمل لـ {document_type}. "
                f"المستند #{document_id} معتمد تلقائياً."
            )
            return None

        required_steps = workflow.get_steps_for_amount(amount)

        if not required_steps:
            logger.info(
                f"لا توجد خطوات مطلوبة لمبلغ {amount} في سير العمل {workflow.name}"
            )
            return None

        first_step = required_steps[0]

        if first_step.should_auto_approve(amount):
            request = ApprovalRequest.objects.create(
                workflow=workflow,
                document_type=document_type,
                document_id=document_id,
                document_number=document_number,
                amount=amount,
                current_step=None,
                status='auto_approved',
                requested_by=user,
                branch=branch,
                notes=notes,
                completed_at=timezone.now()
            )
            ApprovalAction.objects.create(
                request=request,
                step=first_step,
                action='auto_approved',
                notes='موافقة تلقائية - المبلغ أقل من الحد المحدد'
            )
            return request

        request = ApprovalRequest.objects.create(
            workflow=workflow,
            document_type=document_type,
            document_id=document_id,
            document_number=document_number,
            amount=amount,
            current_step=first_step,
            status='pending',
            requested_by=user,
            branch=branch,
            notes=notes
        )

        logger.info(f"تم إنشاء طلب موافقة #{request.pk} للمستند {document_number}")
        return request

    @staticmethod
    def approve(request_id, user, notes=''):
        """اعتماد طلب موافقة"""
        from accounts.models_workflow import ApprovalRequest, ApprovalAction

        try:
            approval_request = ApprovalRequest.objects.select_related(
                'current_step', 'workflow'
            ).get(pk=request_id, status='pending')
        except ApprovalRequest.DoesNotExist:
            return False, 'طلب الموافقة غير موجود أو ليس قيد الانتظار'

        step = approval_request.current_step
        if not step:
            return False, 'لا توجد خطوة حالية'

        if step.approver_user and step.approver_user != user:
            if not user.is_superuser:
                return False, 'ليس لديك صلاحية اعتماد هذه الخطوة'

        if not step.approver_user:
            if not user.groups.filter(pk=step.approver_role_id).exists():
                if not user.is_superuser:
                    return False, 'ليس لديك الدور المطلوب لاعتماد هذه الخطوة'

        ApprovalAction.objects.create(
            request=approval_request,
            step=step,
            action='approved',
            acted_by=user,
            notes=notes
        )

        has_next = approval_request.advance_to_next_step()

        if not has_next and approval_request.status == 'approved':
            logger.info(f"طلب الموافقة #{approval_request.pk} تم اعتماده بالكامل")

        return True, 'تم الاعتماد بنجاح'

    @staticmethod
    def reject(request_id, user, notes=''):
        """رفض طلب موافقة"""
        from accounts.models_workflow import ApprovalRequest, ApprovalAction

        try:
            approval_request = ApprovalRequest.objects.select_related(
                'current_step'
            ).get(pk=request_id, status='pending')
        except ApprovalRequest.DoesNotExist:
            return False, 'طلب الموافقة غير موجود أو ليس قيد الانتظار'

        ApprovalAction.objects.create(
            request=approval_request,
            step=approval_request.current_step,
            action='rejected',
            acted_by=user,
            notes=notes
        )

        approval_request.status = 'rejected'
        approval_request.completed_at = timezone.now()
        approval_request.save(update_fields=['status', 'completed_at'])

        logger.info(f"طلب الموافقة #{approval_request.pk} تم رفضه بواسطة {user}")
        return True, 'تم الرفض'

    @staticmethod
    def get_pending_approvals(user):
        """الحصول على الطلبات المعلقة التي يمكن للمستخدم اعتمادها"""
        from accounts.models_workflow import ApprovalRequest

        if user.is_superuser:
            return ApprovalRequest.objects.filter(
                status='pending'
            ).select_related('workflow', 'current_step', 'requested_by', 'branch')

        user_groups = user.groups.all()
        return ApprovalRequest.objects.filter(
            status='pending'
        ).filter(
            Q(current_step__approver_user=user) |
            Q(current_step__approver_role__in=user_groups)
        ).select_related('workflow', 'current_step', 'requested_by', 'branch')

    @staticmethod
    def check_overdue_requests():
        """فحص الطلبات المتأخرة وتصعيدها"""
        from accounts.models_workflow import ApprovalRequest, ApprovalAction

        overdue_requests = ApprovalRequest.objects.filter(
            status='pending'
        ).select_related('current_step', 'current_step__escalate_to')

        escalated_count = 0
        for approval_request in overdue_requests:
            if approval_request.is_overdue and approval_request.current_step:
                step = approval_request.current_step
                if step.escalate_to:
                    ApprovalAction.objects.create(
                        request=approval_request,
                        step=step,
                        action='escalated',
                        notes=f'تصعيد تلقائي - تجاوز المهلة ({step.timeout_hours} ساعة)'
                    )
                    approval_request.status = 'escalated'
                    approval_request.save(update_fields=['status'])
                    escalated_count += 1
                    logger.warning(
                        f"طلب الموافقة #{approval_request.pk} تم تصعيده "
                        f"إلى {step.escalate_to}"
                    )

        return escalated_count
