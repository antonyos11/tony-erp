"""
محرك الاعتماد — Sprint 23
═══════════════════════════
يتحقق من سقف الصلاحية
لو المبلغ أكبر — يُنشئ طلب اعتماد تلقائي
يُبلّغ المسؤول الأعلى
"""
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class ApprovalEngine:

    @classmethod
    def check_and_approve(cls, user, request_type, amount, source_model, source_id,
                          description, branch=None):
        """
        فحص سقف الاعتماد:
        - لو ضمن السقف → اعتماد فوري
        - لو فوق السقف → طلب اعتماد معلّق

        Returns: (is_auto_approved: bool, approval_request_or_None)
        """
        from apps.authorization.models import ApprovalRequest
        from apps.authorization.services.permission_engine import PermissionEngine
        from apps.notifications.services.notification_engine import NotificationEngine

        limit_map = {
            'invoice': 'invoice',
            'return': 'return',
            'expense': 'expense',
            'purchase': 'invoice',
        }

        limit_type = limit_map.get(request_type, 'invoice')
        is_within, max_limit = PermissionEngine.check_approval_limit(user, limit_type, amount)

        if is_within:
            return True, None

        # إنشاء طلب اعتماد
        request_obj = ApprovalRequest.objects.create(
            request_type=request_type,
            requested_by=user,
            branch=branch,
            source_model=source_model,
            source_id=source_id,
            description=f"{description}\nالمبلغ: {amount} — سقف المستخدم: {max_limit}",
            amount=amount,
        )

        # إبلاغ المسؤولين الأعلى
        approvers = cls._find_approvers(request_type, amount)
        for approver in approvers:
            NotificationEngine.notify(
                user=approver,
                title=f'🔔 طلب اعتماد — {request_obj.get_request_type_display()}',
                message=(
                    f'{user.get_full_name() or user.username} يطلب اعتماد '
                    f'{description} — المبلغ: {amount}'
                ),
                notification_type='warning',
                category='general',
                source_model='ApprovalRequest',
                source_id=str(request_obj.id),
                action_url=f'/authorization/approvals/{request_obj.id}/',
            )

        return False, request_obj

    @classmethod
    def approve(cls, approval_request, approver, user=None):
        """اعتماد الطلب"""
        from apps.notifications.services.notification_engine import NotificationEngine

        approval_request.status = 'approved'
        approval_request.approved_by = approver
        approval_request.processed_at = timezone.now()
        approval_request.save()

        # إبلاغ الطالب
        NotificationEngine.notify(
            user=approval_request.requested_by,
            title='✅ تم اعتماد طلبك',
            message=(
                f'تم اعتماد {approval_request.get_request_type_display()} '
                f'بواسطة {approver.get_full_name() or approver.username}'
            ),
            notification_type='success',
            category='general',
            source_model='ApprovalRequest',
            source_id=str(approval_request.id),
        )
        return approval_request

    @classmethod
    def reject(cls, approval_request, approver, reason='', user=None):
        """رفض الطلب"""
        from apps.notifications.services.notification_engine import NotificationEngine

        approval_request.status = 'rejected'
        approval_request.approved_by = approver
        approval_request.processed_at = timezone.now()
        approval_request.rejection_reason = reason
        approval_request.save()

        NotificationEngine.notify(
            user=approval_request.requested_by,
            title='❌ تم رفض طلبك',
            message=(
                f'تم رفض {approval_request.get_request_type_display()}'
                + (f': {reason}' if reason else '')
            ),
            notification_type='danger',
            category='general',
            source_model='ApprovalRequest',
            source_id=str(approval_request.id),
        )
        return approval_request

    @classmethod
    def _find_approvers(cls, request_type, amount):
        """إيجاد المسؤولين القادرين على اعتماد هذا المبلغ"""
        from apps.authorization.models import UserRoleAssignment

        limit_field_map = {
            'invoice': 'role__invoice_approval_limit',
            'purchase': 'role__invoice_approval_limit',
            'return': 'role__return_approval_limit',
            'expense': 'role__expense_approval_limit',
        }

        field = limit_field_map.get(request_type, 'role__invoice_approval_limit')

        assignments = UserRoleAssignment.objects.filter(
            is_active=True,
            **{f'{field}__gte': amount}
        ).select_related('user')

        approvers = list({a.user for a in assignments if a.user.is_active})

        # لو مفيش أحد مؤهل — أرسل للـ super admins
        if not approvers:
            approvers = list(User.objects.filter(is_superuser=True, is_active=True))

        return approvers
