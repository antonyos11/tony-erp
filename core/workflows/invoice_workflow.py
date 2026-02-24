"""
Invoice Workflow
سير عمل الفواتير (بيع، شراء)
"""

from decimal import Decimal
from core.security.role_definitions import ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_SALES_MANAGER
from .base_workflow import (
    WorkflowEngine,
    WorkflowState,
    WorkflowAction,
    WorkflowTransition,
)


def create_invoice_workflow() -> WorkflowEngine:
    """
    إنشاء سير عمل الفواتير
    
    سير العمل:
    1. DRAFT → موظف يُنشئ فاتورة
    2. DRAFT → PENDING → إرسال للاعتماد
    3. PENDING → APPROVED → مدير يعتمد
    4. PENDING → REJECTED → مدير يرفض
    5. APPROVED → POSTED → ترحيل محاسبي
    6. APPROVED → CANCELLED → إلغاء (بصلاحيات خاصة)
    """
    workflow = WorkflowEngine('invoice')
    
    # من مسودة إلى معلق (إرسال للاعتماد)
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.DRAFT,
        to_state=WorkflowState.PENDING,
        action=WorkflowAction.SUBMIT,
        required_permission='sales.add',  # أي شخص يستطيع إضافة فواتير
    ))
    
    # من معلق إلى معتمد (الموافقة)
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.PENDING,
        to_state=WorkflowState.APPROVED,
        action=WorkflowAction.APPROVE,
        required_permission='sales.approve',
        min_approval_level=2,  # يحتاج مستوى 2 على الأقل
        min_approval_amount=None,  # سيتم فحصه من context
    ))
    
    # من معلق إلى مرفوض
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.PENDING,
        to_state=WorkflowState.REJECTED,
        action=WorkflowAction.REJECT,
        required_permission='sales.approve',
        min_approval_level=2,
    ))
    
    # من معتمد إلى مرحّل (ترحيل محاسبي)
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.APPROVED,
        to_state=WorkflowState.POSTED,
        action=WorkflowAction.POST,
        required_permission='accounting.approve',
        min_approval_level=3,  # محاسب على الأقل
    ))
    
    # من معتمد إلى ملغي (إلغاء فاتورة معتمدة - عملية حرجة)
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.APPROVED,
        to_state=WorkflowState.CANCELLED,
        action=WorkflowAction.CANCEL,
        required_role=ROLE_FIN_MANAGER,  # فقط المدير المالي أو المالك
        min_approval_level=4,
    ))
    
    # من مرفوض إلى مسودة (إعادة للتعديل)
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.REJECTED,
        to_state=WorkflowState.DRAFT,
        action=WorkflowAction.EDIT,
        required_permission='sales.change',
    ))
    
    # من مسودة إلى ملغي (إلغاء قبل الإرسال)
    workflow.add_transition(WorkflowTransition(
        from_state=WorkflowState.DRAFT,
        to_state=WorkflowState.CANCELLED,
        action=WorkflowAction.CANCEL,
        required_permission='sales.delete',
    ))
    
    # إضافة معالجات للحالات
    workflow.add_state_handler(WorkflowState.APPROVED, on_invoice_approved)
    workflow.add_state_handler(WorkflowState.POSTED, on_invoice_posted)
    workflow.add_state_handler(WorkflowState.CANCELLED, on_invoice_cancelled)
    
    return workflow


# ============================================================================
# State Handlers (معالجات الحالات)
# ============================================================================

def on_invoice_approved(obj, user, comment, context):
    """
    عند اعتماد الفاتورة
    - تحديث حالة المخزون (إذا كانت فاتورة بيع)
    - إرسال إشعار
    """
    from users.models import UserActivity
    
    # تسجيل النشاط
    UserActivity.objects.create(
        user=user,
        action='اعتماد',
        module='المبيعات',
        object_id=str(obj.id) if hasattr(obj, 'id') else '',
        description=f'اعتماد فاتورة رقم {obj.id}',
        ip_address='',
        success=True,
    )
    
    # هنا يمكن إضافة:
    # - تحديث المخزون
    # - إرسال إشعار للعميل
    # - تنبيه المحاسب للترحيل
    print(f"✅ تم اعتماد الفاتورة {obj.id} بواسطة {user.username}")


def on_invoice_posted(obj, user, comment, context):
    """
    عند ترحيل الفاتورة محاسبياً
    - إنشاء القيود المحاسبية
    """
    from users.models import UserActivity
    
    UserActivity.objects.create(
        user=user,
        action='ترحيل',
        module='المحاسبة',
        object_id=str(obj.id) if hasattr(obj, 'id') else '',
        description=f'ترحيل فاتورة رقم {obj.id}',
        ip_address='',
        success=True,
    )
    
    print(f"📊 تم ترحيل الفاتورة {obj.id} محاسبياً بواسطة {user.username}")


def on_invoice_cancelled(obj, user, comment, context):
    """
    عند إلغاء الفاتورة
    - إنشاء قيد عكسي (إذا كانت مرحلة)
    - استرجاع المخزون
    - تنبيه أمني
    """
    from users.models import UserActivity, SecurityAlert
    
    UserActivity.objects.create(
        user=user,
        action='إلغاء',
        module='المبيعات',
        object_id=str(obj.id) if hasattr(obj, 'id') else '',
        description=f'إلغاء فاتورة رقم {obj.id} - السبب: {comment}',
        ip_address='',
        success=True,
    )
    
    # تنبيه أمني للعمليات الحرجة
    SecurityAlert.objects.create(
        alert_type='permission_violation',  # أو نوع خاص بالإلغاء
        user=user,
        description=f'إلغاء فاتورة معتمدة رقم {obj.id}',
    )
    
    print(f"⚠️ تم إلغاء الفاتورة {obj.id} بواسطة {user.username}")


# التوافق مع الاستيراد القديم في __init__
# الاختبارات تتوقع وجود InvoiceWorkflow في الحزمة، لذلك نوفر نسخة جاهزة من سير العمل.
InvoiceWorkflow = create_invoice_workflow()


