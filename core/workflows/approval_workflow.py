"""
Generic Approval Workflow
سير عمل الموافقات العام
يمكن استخدامه لأي عملية تحتاج موافقة بسيطة
"""

from .base_workflow import (
    WorkflowEngine,
    WorkflowState,
    WorkflowAction,
    WorkflowTransition,
)


def create_approval_workflow(
    workflow_type: str,
    module: str,
    min_approval_level: int = 2
) -> WorkflowEngine:
    """
    إنشاء سير عمل موافقة بسيط
    
    Args:
        workflow_type: نوع سير العمل
        module: الوحدة (للصلاحيات)
        min_approval_level: أدنى مستوى موافقة مطلوب
    
    Returns:
        WorkflowEngine مُعد
    """
    workflow = WorkflowEngine(workflow_type)
    
    # من مسودة إلى معلق
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.DRAFT,
        to_state=WorkflowState.PENDING,
        action=WorkflowAction.SUBMIT,
        required_permission=f'{module}.add',
    ))
    
    # من معلق إلى معتمد
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.PENDING,
        to_state=WorkflowState.APPROVED,
        action=WorkflowAction.APPROVE,
        required_permission=f'{module}.approve',
        min_approval_level=min_approval_level,
    ))
    
    # من معلق إلى مرفوض
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.PENDING,
        to_state=WorkflowState.REJECTED,
        action=WorkflowAction.REJECT,
        required_permission=f'{module}.approve',
        min_approval_level=min_approval_level,
    ))
    
    # من مرفوض إلى مسودة
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.REJECTED,
        to_state=WorkflowState.DRAFT,
        action=WorkflowAction.EDIT,
        required_permission=f'{module}.change',
    ))
    
    # من مسودة إلى ملغي
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.DRAFT,
        to_state=WorkflowState.CANCELLED,
        action=WorkflowAction.CANCEL,
        required_permission=f'{module}.delete',
    ))
    
    return workflow


class ApprovalWorkflow:
    """
    كلاس مساعد لإنشاء workflows الموافقات بسهولة
    """
    
    @staticmethod
    def for_purchase_order() -> WorkflowEngine:
        """سير عمل أوامر الشراء"""
        return create_approval_workflow('purchase_order', 'purchases', min_approval_level=3)
    
    @staticmethod
    def for_production_order() -> WorkflowEngine:
        """سير عمل أوامر الإنتاج"""
        return create_approval_workflow('production_order', 'production', min_approval_level=3)
    
    @staticmethod
    def for_leave_request() -> WorkflowEngine:
        """سير عمل طلبات الإجازات"""
        return create_approval_workflow('leave_request', 'hr', min_approval_level=2)
    
    @staticmethod
    def for_expense_claim() -> WorkflowEngine:
        """سير عمل طلبات المصروفات"""
        return create_approval_workflow('expense_claim', 'accounting', min_approval_level=3)


