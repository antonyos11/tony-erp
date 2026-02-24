"""
Base Workflow Engine
محرك سير العمل الأساسي
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction

from core.security.permissions_service import PermissionService


class WorkflowState(Enum):
    """حالات سير العمل"""
    DRAFT = 'draft'  # مسودة
    PENDING = 'pending'  # معلق - في انتظار الموافقة
    APPROVED = 'approved'  # معتمد
    REJECTED = 'rejected'  # مرفوض
    CANCELLED = 'cancelled'  # ملغي
    POSTED = 'posted'  # مرحّل (للقيود المحاسبية)
    CLOSED = 'closed'  # مقفل


class WorkflowAction(Enum):
    """الإجراءات المتاحة في سير العمل"""
    SUBMIT = 'submit'  # إرسال للاعتماد
    APPROVE = 'approve'  # اعتماد
    REJECT = 'reject'  # رفض
    CANCEL = 'cancel'  # إلغاء
    EDIT = 'edit'  # تعديل
    POST = 'post'  # ترحيل
    CLOSE = 'close'  # إقفال


@dataclass
class WorkflowTransition:
    """انتقال بين حالات سير العمل"""
    from_state: WorkflowState
    to_state: WorkflowState
    action: WorkflowAction
    required_permission: Optional[str] = None
    required_role: Optional[str] = None
    min_approval_level: int = 0
    min_approval_amount: Optional[Decimal] = None
    condition: Optional[Callable] = None  # دالة شرط إضافية


@dataclass
class WorkflowHistory:
    """سجل تغيير حالة في سير العمل"""
    timestamp: datetime
    from_state: WorkflowState
    to_state: WorkflowState
    action: WorkflowAction
    user: User
    comment: str = ''
    metadata: Dict[str, Any] = None


class WorkflowEngine:
    """
    محرك سير العمل العام
    يمكن استخدامه لأي نوع من العمليات التي تحتاج موافقات
    """
    
    def __init__(self, workflow_type: str):
        """
        Args:
            workflow_type: نوع سير العمل (invoice, journal_entry, purchase_order, etc.)
        """
        self.workflow_type = workflow_type
        self.transitions: List[WorkflowTransition] = []
        self.state_handlers: Dict[WorkflowState, Callable] = {}
    
    def add_transition(self, transition: WorkflowTransition):
        """إضافة انتقال لسير العمل"""
        self.transitions.append(transition)
    
    def add_state_handler(self, state: WorkflowState, handler: Callable):
        """
        إضافة معالج يتم تنفيذه عند الدخول لحالة معينة
        
        مثال:
            workflow.add_state_handler(WorkflowState.APPROVED, on_invoice_approved)
        """
        self.state_handlers[state] = handler
    
    def get_available_actions(
        self, 
        current_state: WorkflowState, 
        user: User,
        context: Optional[Dict[str, Any]] = None
    ) -> List[WorkflowAction]:
        """
        الحصول على الإجراءات المتاحة للمستخدم في الحالة الحالية
        
        Args:
            current_state: الحالة الحالية
            user: المستخدم
            context: سياق إضافي (مثل المبلغ، الكائن، إلخ)
        
        Returns:
            قائمة الإجراءات المسموح بها
        """
        available = []
        
        for transition in self.transitions:
            if transition.from_state != current_state:
                continue
            
            if not self._can_perform_transition(user, transition, context):
                continue
            
            available.append(transition.action)
        
        return available
    
    def can_perform_action(
        self,
        current_state: WorkflowState,
        action: WorkflowAction,
        user: User,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str]:
        """
        فحص إذا كان المستخدم يستطيع تنفيذ إجراء معين
        
        Returns:
            (يستطيع/لا يستطيع, رسالة توضيحية)
        """
        # البحث عن الانتقال المناسب
        transition = None
        for t in self.transitions:
            if t.from_state == current_state and t.action == action:
                transition = t
                break
        
        if not transition:
            return False, f'الإجراء {action.value} غير متاح في الحالة {current_state.value}'
        
        # فحص الصلاحيات
        if transition.required_permission:
            module, perm_action = transition.required_permission.split('.')
            if not PermissionService.has_module_permission(user, module, perm_action):
                return False, 'ليس لديك الصلاحية المطلوبة لهذا الإجراء'
        
        # فحص الدور
        if transition.required_role:
            if not PermissionService.has_role(user, transition.required_role):
                return False, 'ليس لديك الدور المطلوب لهذا الإجراء'
        
        # فحص مستوى الموافقة
        if transition.min_approval_level > 0:
            user_level = PermissionService.get_approval_level(user)
            if user_level < transition.min_approval_level:
                return False, f'تحتاج مستوى موافقة {transition.min_approval_level} على الأقل'
        
        # فحص سلطة الموافقة على المبلغ
        if transition.min_approval_amount and context and 'amount' in context:
            amount = Decimal(str(context['amount']))
            if not PermissionService.can_approve_amount(user, amount):
                max_amount = PermissionService.get_max_approval_amount(user)
                return False, f'المبلغ يتجاوز سلطتك ({max_amount})'
        
        # فحص الشرط الإضافي
        if transition.condition:
            try:
                if not transition.condition(user, context):
                    return False, 'لا تتوفر شروط تنفيذ هذا الإجراء'
            except Exception as e:
                return False, f'خطأ في فحص الشروط: {str(e)}'
        
        return True, 'مسموح'
    
    def _can_perform_transition(
        self,
        user: User,
        transition: WorkflowTransition,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """فحص داخلي للانتقال"""
        can, _ = self.can_perform_action(transition.from_state, transition.action, user, context)
        return can
    
    @transaction.atomic
    def perform_action(
        self,
        obj: Any,
        current_state: WorkflowState,
        action: WorkflowAction,
        user: User,
        comment: str = '',
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, WorkflowState, str]:
        """
        تنفيذ إجراء وتغيير الحالة
        
        Args:
            obj: الكائن (فاتورة، قيد، إلخ)
            current_state: الحالة الحالية
            action: الإجراء المطلوب
            user: المستخدم
            comment: تعليق اختياري
            context: سياق إضافي
        
        Returns:
            (نجح/فشل, الحالة الجديدة, رسالة)
        """
        # فحص الصلاحية
        can, message = self.can_perform_action(current_state, action, user, context)
        if not can:
            return False, current_state, message
        
        # البحث عن الانتقال
        transition = None
        for t in self.transitions:
            if t.from_state == current_state and t.action == action:
                transition = t
                break
        
        if not transition:
            return False, current_state, 'انتقال غير موجود'
        
        new_state = transition.to_state
        
        # تنفيذ معالج الحالة الجديدة (إذا وجد)
        if new_state in self.state_handlers:
            try:
                self.state_handlers[new_state](obj, user, comment, context)
            except Exception as e:
                return False, current_state, f'خطأ في معالج الحالة: {str(e)}'
        
        # تسجيل في السجل
        history = WorkflowHistory(
            timestamp=datetime.now(),
            from_state=current_state,
            to_state=new_state,
            action=action,
            user=user,
            comment=comment,
            metadata=context or {}
        )
        
        # حفظ السجل (إذا كان الكائن يدعم ذلك)
        if hasattr(obj, 'workflow_history'):
            if obj.workflow_history is None:
                obj.workflow_history = []
            obj.workflow_history.append({
                'timestamp': history.timestamp.isoformat(),
                'from_state': history.from_state.value,
                'to_state': history.to_state.value,
                'action': history.action.value,
                'user_id': history.user.id,
                'user_name': str(history.user),
                'comment': history.comment,
            })
        
        return True, new_state, f'تم {self._get_action_label(action)} بنجاح'
    
    def _get_action_label(self, action: WorkflowAction) -> str:
        """الحصول على تسمية عربية للإجراء"""
        labels = {
            WorkflowAction.SUBMIT: 'الإرسال',
            WorkflowAction.APPROVE: 'الاعتماد',
            WorkflowAction.REJECT: 'الرفض',
            WorkflowAction.CANCEL: 'الإلغاء',
            WorkflowAction.EDIT: 'التعديل',
            WorkflowAction.POST: 'الترحيل',
            WorkflowAction.CLOSE: 'الإقفال',
        }
        return labels.get(action, action.value)
    
    def get_state_label(self, state: WorkflowState) -> str:
        """الحصول على تسمية عربية للحالة"""
        labels = {
            WorkflowState.DRAFT: 'مسودة',
            WorkflowState.PENDING: 'معلق',
            WorkflowState.APPROVED: 'معتمد',
            WorkflowState.REJECTED: 'مرفوض',
            WorkflowState.CANCELLED: 'ملغي',
            WorkflowState.POSTED: 'مرحّل',
            WorkflowState.CLOSED: 'مقفل',
        }
        return labels.get(state, state.value)


# ============================================================================
# Helper Functions
# ============================================================================

def get_workflow_for_type(workflow_type: str) -> WorkflowEngine:
    """
    الحصول على محرك سير العمل المناسب لنوع معين
    
    Args:
        workflow_type: نوع سير العمل
    
    Returns:
        WorkflowEngine مُعد للنوع المطلوب
    """
    from .invoice_workflow import create_invoice_workflow
    from .journal_workflow import create_journal_workflow
    
    workflows = {
        'invoice': create_invoice_workflow,
        'journal_entry': create_journal_workflow,
        'purchase_order': create_invoice_workflow,  # يمكن استخدام نفس سير عمل الفواتير
    }
    
    creator = workflows.get(workflow_type)
    if not creator:
        raise ValueError(f'نوع سير العمل غير مدعوم: {workflow_type}')
    
    return creator()


