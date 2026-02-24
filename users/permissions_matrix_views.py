"""
Enhanced Permissions Management Views
واجهات محسّنة لإدارة الصلاحيات - متوافقة مع الواجهة الموجودة
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_http_methods

from users.models import UserRole, ModulePermission
from core.security.permissions_service import PermissionService
from core.security.role_definitions import *


# قائمة الوحدات (Modules)
MODULES = [
    ('accounting', 'المحاسبة'),
    ('inventory', 'المخزون'),
    ('sales', 'المبيعات'),
    ('purchases', 'المشتريات'),
    ('production', 'الإنتاج'),
    ('hr', 'الموارد البشرية'),
    ('crm', 'إدارة علاقات العملاء'),
    ('maintenance', 'الصيانة'),
    ('reports', 'التقارير'),
    ('partners', 'الشركاء'),
    ('fleet', 'الأسطول'),
    ('pos', 'نقطة البيع'),
]

# قائمة العمليات (Actions)
ACTIONS = [
    ('view', 'عرض'),
    ('add', 'إضافة'),
    ('change', 'تعديل'),
    ('delete', 'حذف'),
    ('approve', 'موافقة'),
    ('print', 'طباعة'),
    ('export', 'تصدير'),
]


@login_required
def permissions_matrix_view(request):
    """
    واجهة مصفوفة الصلاحيات الشاملة (مثل الصورة)
    """
    # فحص الصلاحية
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بالوصول لهذه الصفحة')
        return redirect('core:dashboard')
    
    # الحصول على كل الأدوار
    roles = UserRole.objects.filter(is_active=True).order_by('approval_level', 'name')
    
    # بناء المصفوفة الكاملة
    matrix = {}
    for role in roles:
        matrix[role.id] = {
            'role': role,
            'permissions': {}
        }
        
        for module_code, module_name in MODULES:
            matrix[role.id]['permissions'][module_code] = {}
            
            for action_code, action_name in ACTIONS:
                # فحص إذا كانت الصلاحية موجودة
                try:
                    perm = ModulePermission.objects.get(
                        role=role,
                        module=module_code,
                        action=action_code
                    )
                    matrix[role.id]['permissions'][module_code][action_code] = {
                        'exists': True,
                        'is_allowed': perm.is_allowed,
                        'id': perm.id
                    }
                except ModulePermission.DoesNotExist:
                    matrix[role.id]['permissions'][module_code][action_code] = {
                        'exists': False,
                        'is_allowed': False,
                        'id': None
                    }
    
    context = {
        'roles': roles,
        'modules': MODULES,
        'actions': ACTIONS,
        'matrix': matrix,
    }
    
    return render(request, 'users/permissions_matrix.html', context)


@login_required
@require_http_methods(['POST'])
def update_permission_ajax(request):
    """
    تحديث صلاحية واحدة عبر AJAX (للنقر على الدوائر)
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        return JsonResponse({'success': False, 'message': 'غير مسموح'}, status=403)
    
    try:
        role_id = request.POST.get('role_id')
        module = request.POST.get('module')
        action = request.POST.get('action')
        is_allowed = request.POST.get('is_allowed') == 'true'
        
        role = UserRole.objects.get(id=role_id)
        
        # تحديث أو إنشاء الصلاحية
        perm, created = ModulePermission.objects.update_or_create(
            role=role,
            module=module,
            action=action,
            defaults={'is_allowed': is_allowed}
        )
        
        # تسجيل التغيير
        from core.security.audit_service import SecurityAuditService
        SecurityAuditService.log_data_modification(
            user=request.user,
            action='تعديل صلاحية',
            module='إدارة النظام',
            object_type='صلاحية',
            object_id=str(perm.id),
            changes={
                'role': {'old': '', 'new': role.display_name},
                'module': {'old': '', 'new': module},
                'action': {'old': '', 'new': action},
                'is_allowed': {'old': not is_allowed, 'new': is_allowed}
            },
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'تم التحديث بنجاح',
            'perm_id': perm.id,
            'is_allowed': perm.is_allowed
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_http_methods(['POST'])
def bulk_update_permissions(request):
    """
    تحديث صلاحيات متعددة دفعة واحدة (زر "حفظ جميع التغييرات")
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        return JsonResponse({'success': False, 'message': 'غير مسموح'}, status=403)
    
    try:
        import json
        permissions_data = json.loads(request.POST.get('permissions', '[]'))
        
        with transaction.atomic():
            updated_count = 0
            
            for perm_data in permissions_data:
                role_id = perm_data['role_id']
                module = perm_data['module']
                action = perm_data['action']
                is_allowed = perm_data['is_allowed']
                
                role = UserRole.objects.get(id=role_id)
                
                ModulePermission.objects.update_or_create(
                    role=role,
                    module=module,
                    action=action,
                    defaults={'is_allowed': is_allowed}
                )
                
                updated_count += 1
            
            messages.success(request, f'تم تحديث {updated_count} صلاحية بنجاح')
            
            return JsonResponse({
                'success': True,
                'message': f'تم تحديث {updated_count} صلاحية',
                'count': updated_count
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def apply_role_template(request, role_id):
    """
    تطبيق قالب صلاحيات افتراضي على دور
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بهذه العملية')
        return redirect('users:permissions_matrix')
    
    role = UserRole.objects.get(id=role_id)
    
    # قوالب الصلاحيات الافتراضية
    templates = {
        ROLE_OWNER: {
            # كل شيء مسموح
            'all_modules': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export']
        },
        ROLE_FIN_MANAGER: {
            'accounting': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
            'sales': ['view', 'approve'],
            'purchases': ['view', 'approve'],
            'reports': ['view', 'print', 'export'],
        },
        ROLE_ACCOUNTANT: {
            'accounting': ['view', 'add', 'change', 'print'],
            'reports': ['view', 'print'],
        },
        ROLE_INV_MANAGER: {
            'inventory': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
            'purchases': ['view', 'add', 'approve'],
            'reports': ['view', 'print'],
        },
        ROLE_SALES_MANAGER: {
            'sales': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
            'crm': ['view', 'add', 'change', 'delete', 'print'],
            'reports': ['view', 'print', 'export'],
        },
        ROLE_SALES_STAFF: {
            'sales': ['view', 'add', 'print'],
            'crm': ['view', 'add', 'change'],
        },
        ROLE_CASHIER: {
            'pos': ['view', 'add', 'print'],
            'sales': ['view', 'add', 'print'],
        },
    }
    
    template = templates.get(role.name)
    if not template:
        messages.warning(request, 'لا يوجد قالب افتراضي لهذا الدور')
        return redirect('users:permissions_matrix')
    
    with transaction.atomic():
        # حذف الصلاحيات القديمة
        ModulePermission.objects.filter(role=role).delete()
        
        # إنشاء الصلاحيات الجديدة
        if 'all_modules' in template:
            # كل الوحدات
            for module_code, _ in MODULES:
                for action in template['all_modules']:
                    ModulePermission.objects.create(
                        role=role,
                        module=module_code,
                        action=action,
                        is_allowed=True
                    )
        else:
            # وحدات محددة
            for module, actions in template.items():
                for action in actions:
                    ModulePermission.objects.create(
                        role=role,
                        module=module,
                        action=action,
                        is_allowed=True
                    )
        
        messages.success(request, f'تم تطبيق القالب الافتراضي على دور {role.display_name}')
    
    return redirect('users:permissions_matrix')


@login_required
def copy_role_permissions(request, from_role_id, to_role_id):
    """
    نسخ صلاحيات من دور إلى آخر
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بهذه العملية')
        return redirect('users:permissions_matrix')
    
    from_role = UserRole.objects.get(id=from_role_id)
    to_role = UserRole.objects.get(id=to_role_id)
    
    with transaction.atomic():
        # حذف صلاحيات الدور المستهدف
        ModulePermission.objects.filter(role=to_role).delete()
        
        # نسخ الصلاحيات
        source_perms = ModulePermission.objects.filter(role=from_role)
        
        for perm in source_perms:
            ModulePermission.objects.create(
                role=to_role,
                module=perm.module,
                action=perm.action,
                is_allowed=perm.is_allowed
            )
        
        messages.success(request, f'تم نسخ الصلاحيات من {from_role.display_name} إلى {to_role.display_name}')
    
    return redirect('users:permissions_matrix')


