"""
Fine-Grained Permissions System
نظام الصلاحيات التفصيلي على مستوى الحقول والعناصر
"""

from typing import List, Dict, Optional, Any, Set
from django.contrib.auth.models import User
from django.db import models

from core.security.permissions_service import PermissionService


# ============================================================================
# Field-Level Permissions (صلاحيات على مستوى الحقول)
# ============================================================================

class FieldPermission:
    """
    تعريف صلاحية حقل
    
    مثال:
        FieldPermission(
            field='cost_price',
            roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER],
            read_only_roles=[ROLE_INV_MANAGER],
            hidden_for=[ROLE_SALES_STAFF, ROLE_CASHIER]
        )
    """
    
    def __init__(
        self,
        field: str,
        roles_allowed: Optional[List[str]] = None,
        read_only_roles: Optional[List[str]] = None,
        hidden_for: Optional[List[str]] = None,
        requires_permission: Optional[str] = None,
        condition: Optional[callable] = None
    ):
        self.field = field
        self.roles_allowed = roles_allowed or []
        self.read_only_roles = read_only_roles or []
        self.hidden_for = hidden_for or []
        self.requires_permission = requires_permission
        self.condition = condition
    
    def can_view(self, user: User) -> bool:
        """فحص إذا المستخدم يستطيع رؤية الحقل"""
        # إذا كان في القائمة المخفية
        user_roles = [role.name for role in PermissionService.get_user_roles(user)]
        if any(role in user_roles for role in self.hidden_for):
            return False
        
        # إذا كان superuser
        if user.is_superuser:
            return True
        
        # فحص الصلاحية المطلوبة
        if self.requires_permission:
            module, action = self.requires_permission.split('.')
            if not PermissionService.has_module_permission(user, module, action):
                return False
        
        # فحص الشرط الإضافي
        if self.condition and not self.condition(user):
            return False
        
        # إذا لم يكن هناك تقييد، السماح
        if not self.roles_allowed:
            return True
        
        # فحص الأدوار المسموحة
        return any(role in user_roles for role in self.roles_allowed)
    
    def can_edit(self, user: User) -> bool:
        """فحص إذا المستخدم يستطيع تعديل الحقل"""
        # أولاً يجب أن يستطيع رؤيته
        if not self.can_view(user):
            return False
        
        # فحص إذا كان read-only
        user_roles = [role.name for role in PermissionService.get_user_roles(user)]
        if any(role in user_roles for role in self.read_only_roles):
            return False
        
        return True


class PageSection:
    """
    قسم في صفحة (مثل بطاقة، جدول، إلخ)
    
    مثال:
        PageSection(
            section_id='financial_info',
            title='المعلومات المالية',
            roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER],
            fields=['cost_price', 'profit_margin', 'total_cost']
        )
    """
    
    def __init__(
        self,
        section_id: str,
        title: str,
        roles_allowed: Optional[List[str]] = None,
        requires_permission: Optional[str] = None,
        fields: Optional[List[str]] = None,
        condition: Optional[callable] = None
    ):
        self.section_id = section_id
        self.title = title
        self.roles_allowed = roles_allowed or []
        self.requires_permission = requires_permission
        self.fields = fields or []
        self.condition = condition
    
    def can_view(self, user: User) -> bool:
        """فحص إذا المستخدم يستطيع رؤية القسم"""
        if user.is_superuser:
            return True
        
        # فحص الصلاحية المطلوبة
        if self.requires_permission:
            module, action = self.requires_permission.split('.')
            if not PermissionService.has_module_permission(user, module, action):
                return False
        
        # فحص الشرط الإضافي
        if self.condition and not self.condition(user):
            return False
        
        # إذا لم يكن هناك تقييد، السماح
        if not self.roles_allowed:
            return True
        
        # فحص الأدوار
        user_roles = [role.name for role in PermissionService.get_user_roles(user)]
        return any(role in user_roles for role in self.roles_allowed)


class ActionButton:
    """
    زر أو عملية في صفحة
    
    مثال:
        ActionButton(
            action_id='delete_invoice',
            label='حذف',
            roles_allowed=[ROLE_OWNER, ROLE_FIN_MANAGER],
            requires_permission='sales.delete',
            danger=True
        )
    """
    
    def __init__(
        self,
        action_id: str,
        label: str,
        url: Optional[str] = None,
        roles_allowed: Optional[List[str]] = None,
        requires_permission: Optional[str] = None,
        min_approval_level: int = 0,
        condition: Optional[callable] = None,
        danger: bool = False,
        icon: Optional[str] = None
    ):
        self.action_id = action_id
        self.label = label
        self.url = url
        self.roles_allowed = roles_allowed or []
        self.requires_permission = requires_permission
        self.min_approval_level = min_approval_level
        self.condition = condition
        self.danger = danger
        self.icon = icon
    
    def can_execute(self, user: User, context: Optional[Dict] = None) -> tuple[bool, str]:
        """فحص إذا المستخدم يستطيع تنفيذ العملية"""
        if user.is_superuser:
            return True, 'مسموح'
        
        # فحص الصلاحية المطلوبة
        if self.requires_permission:
            module, action = self.requires_permission.split('.')
            if not PermissionService.has_module_permission(user, module, action):
                return False, 'ليس لديك الصلاحية المطلوبة'
        
        # فحص الأدوار
        if self.roles_allowed:
            user_roles = [role.name for role in PermissionService.get_user_roles(user)]
            if not any(role in user_roles for role in self.roles_allowed):
                return False, 'ليس لديك الدور المطلوب'
        
        # فحص مستوى الموافقة
        if self.min_approval_level > 0:
            user_level = PermissionService.get_approval_level(user)
            if user_level < self.min_approval_level:
                return False, f'تحتاج مستوى موافقة {self.min_approval_level} على الأقل'
        
        # فحص الشرط الإضافي
        if self.condition:
            try:
                if not self.condition(user, context):
                    return False, 'لا تتوفر شروط تنفيذ هذا الإجراء'
            except Exception as e:
                return False, f'خطأ في فحص الشروط: {str(e)}'
        
        return True, 'مسموح'


# ============================================================================
# Page Configuration (تكوين الصفحة)
# ============================================================================

class PagePermissionConfig:
    """
    تكوين صلاحيات صفحة كاملة
    
    مثال:
        config = PagePermissionConfig(
            page_id='product_detail',
            title='تفاصيل الصنف',
            requires_permission='inventory.view'
        )
        config.add_field(FieldPermission('cost_price', hidden_for=[ROLE_SALES_STAFF]))
        config.add_section(PageSection('financial', 'المعلومات المالية', ...))
        config.add_action(ActionButton('delete', 'حذف', ...))
    """
    
    def __init__(
        self,
        page_id: str,
        title: str,
        requires_permission: Optional[str] = None,
        roles_allowed: Optional[List[str]] = None
    ):
        self.page_id = page_id
        self.title = title
        self.requires_permission = requires_permission
        self.roles_allowed = roles_allowed or []
        
        self.fields: Dict[str, FieldPermission] = {}
        self.sections: Dict[str, PageSection] = {}
        self.actions: Dict[str, ActionButton] = {}
    
    def add_field(self, field_perm: FieldPermission):
        """إضافة صلاحية حقل"""
        self.fields[field_perm.field] = field_perm
    
    def add_section(self, section: PageSection):
        """إضافة قسم"""
        self.sections[section.section_id] = section
    
    def add_action(self, action: ActionButton):
        """إضافة عملية"""
        self.actions[action.action_id] = action
    
    def can_access_page(self, user: User) -> tuple[bool, str]:
        """فحص إذا المستخدم يستطيع الوصول للصفحة"""
        if user.is_superuser:
            return True, 'مسموح'
        
        # فحص الصلاحية المطلوبة
        if self.requires_permission:
            module, action = self.requires_permission.split('.')
            if not PermissionService.has_module_permission(user, module, action):
                return False, 'ليس لديك صلاحية الوصول لهذه الصفحة'
        
        # فحص الأدوار
        if self.roles_allowed:
            user_roles = [role.name for role in PermissionService.get_user_roles(user)]
            if not any(role in user_roles for role in self.roles_allowed):
                return False, 'ليس لديك الدور المطلوب لهذه الصفحة'
        
        return True, 'مسموح'
    
    def get_visible_fields(self, user: User) -> List[str]:
        """الحصول على الحقول المرئية للمستخدم"""
        visible = []
        for field_name, field_perm in self.fields.items():
            if field_perm.can_view(user):
                visible.append(field_name)
        return visible
    
    def get_editable_fields(self, user: User) -> List[str]:
        """الحصول على الحقول القابلة للتعديل"""
        editable = []
        for field_name, field_perm in self.fields.items():
            if field_perm.can_edit(user):
                editable.append(field_name)
        return editable
    
    def get_visible_sections(self, user: User) -> List[PageSection]:
        """الحصول على الأقسام المرئية"""
        visible = []
        for section in self.sections.values():
            if section.can_view(user):
                visible.append(section)
        return visible
    
    def get_available_actions(self, user: User, context: Optional[Dict] = None) -> List[ActionButton]:
        """الحصول على العمليات المتاحة"""
        available = []
        for action in self.actions.values():
            can, _ = action.can_execute(user, context)
            if can:
                available.append(action)
        return available


# ============================================================================
# Fine-Grained Permission Service (الخدمة الرئيسية)
# ============================================================================

class FineGrainedPermissionService:
    """
    خدمة الصلاحيات التفصيلية
    """
    
    # تخزين تكوينات الصفحات
    _page_configs: Dict[str, PagePermissionConfig] = {}
    
    @classmethod
    def register_page_config(cls, config: PagePermissionConfig):
        """تسجيل تكوين صفحة"""
        cls._page_configs[config.page_id] = config
    
    @classmethod
    def get_page_config(cls, page_id: str) -> Optional[PagePermissionConfig]:
        """الحصول على تكوين صفحة"""
        return cls._page_configs.get(page_id)
    
    @classmethod
    def can_view_field(cls, user: User, page_id: str, field_name: str) -> bool:
        """فحص إذا المستخدم يستطيع رؤية حقل"""
        config = cls.get_page_config(page_id)
        if not config:
            return True  # إذا لم يكن هناك تكوين، السماح
        
        field_perm = config.fields.get(field_name)
        if not field_perm:
            return True  # إذا لم يكن الحقل معرّف، السماح
        
        return field_perm.can_view(user)
    
    @classmethod
    def can_edit_field(cls, user: User, page_id: str, field_name: str) -> bool:
        """فحص إذا المستخدم يستطيع تعديل حقل"""
        config = cls.get_page_config(page_id)
        if not config:
            return True
        
        field_perm = config.fields.get(field_name)
        if not field_perm:
            return True
        
        return field_perm.can_edit(user)
    
    @classmethod
    def can_view_section(cls, user: User, page_id: str, section_id: str) -> bool:
        """فحص إذا المستخدم يستطيع رؤية قسم"""
        config = cls.get_page_config(page_id)
        if not config:
            return True
        
        section = config.sections.get(section_id)
        if not section:
            return True
        
        return section.can_view(user)
    
    @classmethod
    def can_execute_action(cls, user: User, page_id: str, action_id: str, context: Optional[Dict] = None) -> tuple[bool, str]:
        """فحص إذا المستخدم يستطيع تنفيذ عملية"""
        config = cls.get_page_config(page_id)
        if not config:
            return True, 'مسموح'
        
        action = config.actions.get(action_id)
        if not action:
            return True, 'مسموح'
        
        return action.can_execute(user, context)
    
    @classmethod
    def filter_model_fields(cls, user: User, page_id: str, model_instance: models.Model) -> Dict[str, Any]:
        """
        فلترة حقول model بناءً على الصلاحيات
        
        Returns:
            dict من الحقول المسموح برؤيتها فقط
        """
        config = cls.get_page_config(page_id)
        if not config:
            # إرجاع كل الحقول
            return {f.name: getattr(model_instance, f.name) for f in model_instance._meta.fields}
        
        visible_fields = config.get_visible_fields(user)
        
        result = {}
        for field in model_instance._meta.fields:
            if not visible_fields or field.name in visible_fields:
                result[field.name] = getattr(model_instance, field.name)
        
        return result


# ============================================================================
# Utility Functions
# ============================================================================

def create_field_permission_from_role_list(
    field: str,
    view_roles: List[str],
    edit_roles: Optional[List[str]] = None
) -> FieldPermission:
    """
    دالة مساعدة لإنشاء صلاحية حقل بسرعة
    
    مثال:
        cost_perm = create_field_permission_from_role_list(
            'cost_price',
            view_roles=[ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_INV_MANAGER],
            edit_roles=[ROLE_OWNER, ROLE_FIN_MANAGER]
        )
    """
    all_roles = [
        'super_admin', 'accounting_manager', 'accounting_staff',
        'inventory_manager', 'inventory_staff', 'sales_manager',
        'sales_staff', 'cashier', 'production_manager', 'hr_staff',
        'system_admin', 'viewer'
    ]
    
    hidden_for = [role for role in all_roles if role not in view_roles]
    read_only = [role for role in view_roles if edit_roles and role not in edit_roles]
    
    return FieldPermission(
        field=field,
        roles_allowed=view_roles,
        read_only_roles=read_only,
        hidden_for=hidden_for
    )


