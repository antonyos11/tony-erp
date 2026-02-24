"""
محرك القوائم الديناميكي
Menu Engine - Dynamic Menu Generation Based on Permissions
"""

from typing import Dict, List, Optional, Any
from django.contrib.auth.models import User
from django.urls import reverse, NoReverseMatch

from core.security.permissions_service import PermissionService
from .menu_config import MAIN_MENU_STRUCTURE, ROLE_DASHBOARDS


class MenuEngine:
    """
    محرك القوائم الديناميكي
    يقوم بتوليد القوائم بناءً على صلاحيات المستخدم
    """
    
    @staticmethod
    def get_menu_for_user(user: User) -> List[Dict[str, Any]]:
        """
        الحصول على القائمة الكاملة للمستخدم بناءً على صلاحياته
        
        Args:
            user: المستخدم
        
        Returns:
            قائمة البنود المسموح بها للمستخدم
        """
        if not user or not user.is_authenticated:
            return []
        
        filtered_menu = []
        
        for item in MAIN_MENU_STRUCTURE:
            filtered_item = MenuEngine._filter_menu_item(user, item)
            if filtered_item:
                filtered_menu.append(filtered_item)
        
        return filtered_menu
    
    @staticmethod
    def _filter_menu_item(user: User, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        فلترة بند قائمة واحد بناءً على صلاحيات المستخدم
        
        Args:
            user: المستخدم
            item: بند القائمة
        
        Returns:
            البند المفلتر أو None إذا لم يكن مسموحاً
        """
        # نسخ البند حتى لا نعدل الأصل
        filtered_item = item.copy()
        
        # فحص الأدوار المحددة (إذا كانت موجودة)
        if 'roles_only' in item:
            user_roles = PermissionService.get_user_roles(user)
            user_role_codes = [role.name for role in user_roles]
            
            # إذا كان المستخدم ليس super admin ولا يملك أي من الأدوار المطلوبة
            if not user.is_superuser and not any(role in user_role_codes for role in item['roles_only']):
                return None
        
        # فحص الصلاحيات (إذا كانت موجودة)
        if item.get('permission'):
            perm = item['permission']
            module = perm.get('module')
            action = perm.get('action', 'view')
            
            if module and not PermissionService.has_module_permission(user, module, action):
                return None
        
        # فلترة البنود الفرعية (children)
        if 'children' in item and item['children']:
            filtered_children = []
            
            for child in item['children']:
                filtered_child = MenuEngine._filter_menu_item(user, child)
                if filtered_child:
                    filtered_children.append(filtered_child)
            
            # إذا لم يتبق أي بنود فرعية، لا نعرض البند الرئيسي
            if not filtered_children:
                return None
            
            filtered_item['children'] = filtered_children
        
        # محاولة تحويل URL name إلى URL فعلي
        if filtered_item.get('url') and ':' in str(filtered_item['url']):
            try:
                filtered_item['url_resolved'] = reverse(filtered_item['url'])
            except NoReverseMatch:
                filtered_item['url_resolved'] = '#'
        else:
            filtered_item['url_resolved'] = filtered_item.get('url', '#')
        
        return filtered_item
    
    @staticmethod
    def get_breadcrumbs(user: User, current_url: str) -> List[Dict[str, str]]:
        """
        الحصول على breadcrumbs (مسار التصفح) للصفحة الحالية
        
        Args:
            user: المستخدم
            current_url: عنوان الصفحة الحالية
        
        Returns:
            قائمة breadcrumbs
        """
        breadcrumbs = [
            {'label': 'الرئيسية', 'url': reverse('core:dashboard') if user.is_authenticated else '/'}
        ]
        
        # البحث في القائمة عن الصفحة الحالية
        menu = MenuEngine.get_menu_for_user(user)
        found_path = MenuEngine._find_item_path(menu, current_url)
        
        if found_path:
            breadcrumbs.extend(found_path)
        
        return breadcrumbs
    
    @staticmethod
    def _find_item_path(menu: List[Dict], target_url: str, path: Optional[List] = None) -> Optional[List]:
        """
        البحث عن مسار بند في القائمة
        """
        if path is None:
            path = []
        
        for item in menu:
            current_path = path + [{'label': item['label'], 'url': item.get('url_resolved', '#')}]
            
            if item.get('url_resolved') == target_url:
                return current_path
            
            if 'children' in item:
                found = MenuEngine._find_item_path(item['children'], target_url, current_path)
                if found:
                    return found
        
        return None
    
    @staticmethod
    def get_quick_actions(user: User) -> List[Dict[str, Any]]:
        """
        الحصول على الإجراءات السريعة للمستخدم
        
        Returns:
            قائمة الإجراءات السريعة المسموح بها
        """
        quick_actions = []
        
        # فاتورة بيع جديدة
        if PermissionService.can_add(user, 'sales'):
            quick_actions.append({
                'label': 'فاتورة بيع',
                'icon': 'fas fa-file-invoice',
                'url': 'sales:invoice_add',
                'color': 'primary',
            })
        
        # قيد محاسبي جديد
        if PermissionService.can_add(user, 'accounting'):
            quick_actions.append({
                'label': 'قيد يومية',
                'icon': 'fas fa-book',
                'url': 'accounting:journal_add',
                'color': 'success',
            })
        
        # إذن استلام
        if PermissionService.can_add(user, 'inventory'):
            quick_actions.append({
                'label': 'إذن استلام',
                'icon': 'fas fa-dolly',
                'url': 'inventory:receive_add',
                'color': 'info',
            })
        
        # إذن صرف
        if PermissionService.can_add(user, 'inventory'):
            quick_actions.append({
                'label': 'إذن صرف',
                'icon': 'fas fa-box-open',
                'url': 'inventory:issue_add',
                'color': 'warning',
            })
        
        # أمر شراء
        if PermissionService.can_add(user, 'purchases'):
            quick_actions.append({
                'label': 'أمر شراء',
                'icon': 'fas fa-shopping-basket',
                'url': 'purchases:order_add',
                'color': 'secondary',
            })
        
        return quick_actions
    
    @staticmethod
    def get_dashboard_config(user: User) -> Dict[str, Any]:
        """
        الحصول على إعداد لوحة التحكم للمستخدم بناءً على دوره
        
        Args:
            user: المستخدم
        
        Returns:
            إعداد لوحة التحكم
        """
        if not user or not user.is_authenticated:
            return {
                'template': 'dashboards/guest_dashboard.html',
                'widgets': [],
            }
        
        if user.is_superuser:
            from core.security.role_definitions import ROLE_OWNER
            return ROLE_DASHBOARDS.get(ROLE_OWNER, {
                'template': 'dashboards/default_dashboard.html',
                'widgets': ['overview'],
            })
        
        # الحصول على الدور الرئيسي للمستخدم
        user_roles = PermissionService.get_user_roles(user)
        
        if not user_roles:
            return {
                'template': 'dashboards/default_dashboard.html',
                'widgets': ['overview'],
            }
        
        # استخدام لوحة التحكم للدور الأول (الرئيسي)
        primary_role = user_roles[0]
        dashboard_config = ROLE_DASHBOARDS.get(primary_role.name, {
            'template': 'dashboards/default_dashboard.html',
            'widgets': ['overview'],
        })
        
        return dashboard_config


# ============================================================================
# Shortcut Functions (دوال مختصرة)
# ============================================================================

def get_user_menu(user: User) -> List[Dict[str, Any]]:
    """
    دالة مختصرة للحصول على قائمة المستخدم
    
    الاستخدام في القالب:
        {% load menu_tags %}
        {% get_user_menu request.user %}
    """
    return MenuEngine.get_menu_for_user(user)


def get_dashboard_for_role(user: User) -> Dict[str, Any]:
    """
    دالة مختصرة للحصول على لوحة التحكم حسب الدور
    """
    return MenuEngine.get_dashboard_config(user)


def get_user_quick_actions(user: User) -> List[Dict[str, Any]]:
    """
    دالة مختصرة للحصول على الإجراءات السريعة
    """
    return MenuEngine.get_quick_actions(user)


