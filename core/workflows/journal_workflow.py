"""
Journal Entry Workflow
سير عمل القيود المحاسبية
"""

from core.security.role_definitions import ROLE_OWNER, ROLE_FIN_MANAGER
from .base_workflow import (
    WorkflowEngine,
    WorkflowState,
    WorkflowAction,
    WorkflowTransition,
)


def create_journal_workflow() -> WorkflowEngine:
    """
    إنشاء سير عمل القيود المحاسبية
    
    سير العمل:
    1. DRAFT → محاسب يُدخل قيد
    2. DRAFT → PENDING → إرسال للمراجعة
    3. PENDING → APPROVED → مدير مالي يعتمد
    4. APPROVED → POSTED → ترحيل نهائي
    5. POSTED → CLOSED → إقفال (لا يمكن التعديل بعدها)
    """
    workflow = WorkflowEngine('journal_entry')
    
    # من مسودة إلى معلق
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.DRAFT,
        to_state=WorkflowState.PENDING,
        action=WorkflowAction.SUBMIT,
        required_permission='accounting.add',
    ))
    
    # من معلق إلى معتمد
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.PENDING,
        to_state=WorkflowState.APPROVED,
        action=WorkflowAction.APPROVE,
        required_permission='accounting.approve',
        min_approval_level=3,  # مدير مالي
    ))
    
    # من معلق إلى مرفوض
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.PENDING,
        to_state=WorkflowState.REJECTED,
        action=WorkflowAction.REJECT,
        required_permission='accounting.approve',
        min_approval_level=3,
    ))
    
    # من معتمد إلى مرحّل
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.APPROVED,
        to_state=WorkflowState.POSTED,
        action=WorkflowAction.POST,
        required_permission='accounting.approve',
        min_approval_level=4,  # مدير مالي فقط
    ))
    
    # من مرحّل إلى مقفل (عملية حرجة جداً)
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.POSTED,
        to_state=WorkflowState.CLOSED,
        action=WorkflowAction.CLOSE,
        required_role=ROLE_OWNER,  # المالك فقط
        min_approval_level=5,
    ))
    
    # من مرفوض إلى مسودة (للتعديل)
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.REJECTED,
        to_state=WorkflowState.DRAFT,
        action=WorkflowAction.EDIT,
        required_permission='accounting.change',
    ))
    
    # معالجات الحالات
    workflow.add_state_handler(WorkflowState.POSTED, on_journal_posted)
    workflow.add_state_handler(WorkflowState.CLOSED, on_journal_closed)
    
    return workflow


def on_journal_posted(obj, user, comment, context):
    """عند ترحيل القيد"""
    from users.models import UserActivity
    
    UserActivity.objects.create(
        user=user,
        action='ترحيل',
        module='المحاسبة',
        object_id=str(obj.id) if hasattr(obj, 'id') else '',
        description=f'ترحيل قيد يومية رقم {obj.id}',
        ip_address='',
        success=True,
    )
    
    print(f"📗 تم ترحيل القيد {obj.id} بواسطة {user.username}")


def on_journal_closed(obj, user, comment, context):
    """عند إقفال القيد"""
    from users.models import UserActivity, SecurityAlert
    
    UserActivity.objects.create(
        user=user,
        action='إقفال',
        module='المحاسبة',
        object_id=str(obj.id) if hasattr(obj, 'id') else '',
        description=f'إقفال قيد يومية رقم {obj.id}',
        ip_address='',
        success=True,
    )
    
    # تنبيه أمني
    SecurityAlert.objects.create(
        alert_type='permission_violation',
        user=user,
        description=f'إقفال قيد محاسبي رقم {obj.id} - عملية حرجة',
    )
    
    print(f"🔒 تم إقفال القيد {obj.id} بواسطة {user.username}")


# Export the workflow instance for import
JournalEntryWorkflow = create_journal_workflow()


