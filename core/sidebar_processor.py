"""
Sidebar Context Processor - معالج سياق القائمة الجانبية المنظمة
====================================================================

يستخدم نموذج البيانات من sidebar_config.py لإنشاء قائمة جانبية منظمة
مع دعم الصلاحيات والتجميع حسب الفئات
"""

from django.urls import reverse, NoReverseMatch
from core.sidebar_config import (
    get_sections_sorted,
    group_items_by_category,
    get_category_label,
    CATEGORY_DAILY,
    CATEGORY_MASTER,
    CATEGORY_REPORTS,
)
from core.context_processors import user_permissions as _user_permissions_cp


def sidebar_menu(request):
    """
    Context processor للقائمة الجانبية المنظمة
    يرجع القائمة مقسمة إلى أقسام رئيسية ومجموعات فرعية
    """
    # إذا كان المسار يبدأ بـ /store أو /home-services، لا نعرض sidebar النظام
    if request.path.startswith('/store') or request.path.startswith('/home-services'):
        return {'sidebar_sections': []}
    
    if not request.user.is_authenticated:
        return {'sidebar_sections': []}

    # Helper to validate if a URL exists
    def is_valid_url(url):
        """Check if URL name can be resolved"""
        if not url:
            return False
        # Direct paths are always valid
        if url.startswith('/'):
            return True
        # Try to resolve named URL
        try:
            reverse(url)
            return True
        except NoReverseMatch:
            return False

    # محاولة استخدام التكوين الديناميكي الجديد المبني على user_permissions (يحافظ على الترتيب الكامل)
    try:
        modules_data = _user_permissions_cp(request).get('user_modules', {})
    except Exception:
        modules_data = {}

    if modules_data:
        sections = []
        for module_key, module_config in modules_data.items():
            # نعرض فقط العناصر ذات الروابط الفعلية والصالحة
            raw_items = [i for i in module_config.get('items', []) if i.get('url') and is_valid_url(i.get('url'))]
            # تحويل name إلى label لتتوافق مع template
            items = []
            for item in raw_items:
                item_copy = item.copy()
                if 'name' in item_copy and 'label' not in item_copy:
                    item_copy['label'] = item_copy['name']
                items.append(item_copy)
            grouped_items = {
                CATEGORY_DAILY: items,
                CATEGORY_MASTER: [],
                CATEGORY_REPORTS: [],
            }
            section_active = any(i.get('active') for i in items)
            sections.append({
                'id': module_key,
                'label': module_config.get('name', module_key),
                'icon': module_config.get('icon', 'bi-dot'),
                'active': section_active,
                'items': items,
                'grouped_items': grouped_items,
                'has_daily': bool(items),
                'has_master': False,
                'has_reports': False,
            })

        return {
            'sidebar_sections': sections,
            'category_labels': {
                'daily': get_category_label(CATEGORY_DAILY),
                'master': get_category_label(CATEGORY_MASTER),
                'reports': get_category_label(CATEGORY_REPORTS),
            }
        }
    
    sections = get_sections_sorted()
    accessible_sections = []
    
    # Current path for active state detection
    current_path = getattr(request, 'path', '')
    current_view_name = ''
    try:
        if hasattr(request, 'resolver_match') and request.resolver_match:
            current_view_name = request.resolver_match.view_name or ''
    except Exception:
        current_view_name = ''
    
    # Helper function to check permissions
    def has_permission(item, module_key):
        """Check if user has permission to access an item"""
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
            
        # Items without permission requirement are visible to all
        if item.get('permission') is None:
            return True
        
        # Check module_permission if specified (for special cases like settings)
        if 'module_permission' in item:
            mod, perm = item['module_permission']
            try:
                if perm == 'view_auditlog':
                    return request.user.has_perm(f'{mod}.{perm}')
                return request.user.has_module_permission(mod, perm)
            except Exception:
                return False
        
        # Check resource permission if specified
        resource_key = item.get('resource')
        action_key = item.get('permission', 'view')
        
        if resource_key and module_key:
            try:
                has_resource = request.user.has_resource_permission(
                    module_key, resource_key, action_key
                )
                if has_resource:
                    return True
            except Exception:
                pass
        
        # Check module permission
        if module_key:
            try:
                return request.user.has_module_permission(module_key, action_key)
            except Exception:
                return False
        
        return False
    
    # Helper to check if item is active
    def is_item_active(item):
        """Check if item matches current URL"""
        if 'url' not in item:
            return False
        
        url = item['url']
        
        # Try to resolve URL name
        if not url.startswith('/'):
            try:
                resolved = reverse(url)
            except NoReverseMatch:
                resolved = ''
        else:
            resolved = url
        
        # Normalize paths
        def normalize(p):
            if not p:
                return ''
            return p.rstrip('/') or '/'
        
        norm_current = normalize(current_path)
        norm_resolved = normalize(resolved)
        
        if norm_resolved and norm_current == norm_resolved:
            return True
        
        # Check by view name
        if not url.startswith('/') and current_view_name == url:
            return True
        
        return False
    
    # Process each section
    for section in sections:
        module_key = section.get('module')
        
        # Check if user has access to this module
        has_access = False
        if module_key is None:
            # Sections without module are accessible (like dashboard, settings)
            has_access = True
        elif request.user.is_superuser:
            # Superusers have access to all modules
            has_access = True
        else:
            # Check module permissions
            module_permissions = section.get('permissions', ['view'])
            for perm in module_permissions:
                try:
                    if request.user.has_module_permission(module_key, perm):
                        has_access = True
                        break
                except Exception:
                    continue
        
        if not has_access:
            continue
        
        # Filter items by permissions and valid URLs
        accessible_items = []
        section_active = False
        
        for item in section.get('items', []):
            # Skip items with invalid URLs
            item_url = item.get('url', '')
            if item_url and not is_valid_url(item_url):
                continue
            
            if has_permission(item, module_key):
                # Check if item is active
                if is_item_active(item):
                    item['active'] = True
                    section_active = True
                accessible_items.append(item)
        
        # Group items by category
        grouped_items = group_items_by_category(accessible_items)
        
        # Only add section if it has accessible items
        if accessible_items:
            section_data = {
                'id': section['id'],
                'label': section['label'],
                'icon': section['icon'],
                'active': section_active,
                'items': accessible_items,
                'grouped_items': grouped_items,  # Items grouped by category
                'has_daily': len(grouped_items[CATEGORY_DAILY]) > 0,
                'has_master': len(grouped_items[CATEGORY_MASTER]) > 0,
                'has_reports': len(grouped_items[CATEGORY_REPORTS]) > 0,
            }
            accessible_sections.append(section_data)
    
    return {
        'sidebar_sections': accessible_sections,
        'category_labels': {
            'daily': get_category_label(CATEGORY_DAILY),
            'master': get_category_label(CATEGORY_MASTER),
            'reports': get_category_label(CATEGORY_REPORTS),
        }
    }

