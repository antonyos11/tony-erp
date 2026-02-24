"""
User Management Views - Enhanced
واجهات إدارة المستخدمين والأدوار المحسّنة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.paginator import Paginator
from decimal import Decimal

from core.security.permissions_service import PermissionService, require_permission
from core.security.role_definitions import (
    ROLE_OWNER, ROLE_SYS_ADMIN,
    get_role_display_name,
    get_default_approval_limit,
    get_default_discount_limit,
)
from .models import UserProfile, UserRole, ModulePermission, ResourcePermission, UserActivity, SecurityAlert
from .forms import UserProfileForm, UserRoleForm


# ============================================================================
# User Management Views
# ============================================================================

@login_required
@require_permission('core', 'view')
def user_list(request):
    """
    قائمة المستخدمين
    محصورة في: ROLE_OWNER, ROLE_SYS_ADMIN
    """
    # فحص الصلاحية
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بالوصول لهذه الصفحة')
        return redirect('core:dashboard')
    
    # الفلترة
    search_query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.select_related('profile', 'profile__role').all()
    
    if search_query:
        users = users.filter(
            username__icontains=search_query
        ) | users.filter(
            profile__arabic_name__icontains=search_query
        ) | users.filter(
            profile__employee_id__icontains=search_query
        )
    
    if role_filter:
        users = users.filter(profile__role__name=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True, profile__is_approved=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'pending':
        users = users.filter(profile__is_approved=False)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # قائمة الأدوار للفلتر
    roles = UserRole.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'roles': roles,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'users/user_list.html', context)


@login_required
@require_permission('core', 'view')
def user_detail(request, user_id):
    """
    عرض تفاصيل مستخدم
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بالوصول لهذه الصفحة')
        return redirect('core:dashboard')
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    # آخر الأنشطة
    recent_activities = UserActivity.objects.filter(user=user).order_by('-timestamp')[:10]
    
    # التنبيهات الأمنية
    security_alerts = SecurityAlert.objects.filter(user=user, is_resolved=False)
    
    context = {
        'viewed_user': user,
        'recent_activities': recent_activities,
        'security_alerts': security_alerts,
        'max_approval': PermissionService.get_max_approval_amount(user),
        'max_discount': PermissionService.get_max_discount_percentage(user),
        'approval_level': PermissionService.get_approval_level(user),
    }
    
    return render(request, 'users/user_detail.html', context)


@login_required
@require_permission('core', 'add')
def user_create(request):
    """
    إنشاء مستخدم جديد
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بإنشاء مستخدمين')
        return redirect('users:user_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # إنشاء المستخدم
                username = request.POST.get('username')
                password = request.POST.get('password')
                email = request.POST.get('email', '')
                
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    is_active=True
                )
                
                # إنشاء Profile
                arabic_name = request.POST.get('arabic_name')
                employee_id = request.POST.get('employee_id')
                phone = request.POST.get('phone', '')
                position = request.POST.get('position', '')
                role_id = request.POST.get('role')
                
                role = UserRole.objects.get(id=role_id)
                
                profile, _ = UserProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'arabic_name': arabic_name,
                        'employee_id': employee_id,
                        'phone': phone,
                        'position': position,
                        'role': role,
                        'is_approved': request.POST.get('auto_approve') == 'on',
                        'approved_by': request.user if request.POST.get('auto_approve') == 'on' else None,
                        'must_change_password': True,
                    }
                )
                
                # إضافة أدوار إضافية
                secondary_roles = request.POST.getlist('secondary_roles')
                if secondary_roles:
                    profile.secondary_roles.set(secondary_roles)
                
                messages.success(request, f'تم إنشاء المستخدم {arabic_name} بنجاح')
                return redirect('users:user_detail', user_id=user.id)
                
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء المستخدم: {str(e)}')
    
    roles = UserRole.objects.filter(is_active=True)
    
    context = {
        'roles': roles,
    }
    
    return render(request, 'users/user_create.html', context)


@login_required
@require_permission('core', 'change')
def user_edit(request, user_id):
    """
    تعديل مستخدم
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بتعديل المستخدمين')
        return redirect('users:user_list')
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    profile = user.profile
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # تحديث بيانات User
                user.email = request.POST.get('email', '')
                user.is_active = request.POST.get('is_active') == 'on'
                user.save()
                
                # تحديث Profile
                profile.arabic_name = request.POST.get('arabic_name')
                profile.phone = request.POST.get('phone', '')
                profile.position = request.POST.get('position', '')
                profile.allowed_ips = request.POST.get('allowed_ips', '')
                profile.max_concurrent_sessions = int(request.POST.get('max_concurrent_sessions', 2))
                
                role_id = request.POST.get('role')
                profile.role = UserRole.objects.get(id=role_id)
                
                # أدوار إضافية
                secondary_roles = request.POST.getlist('secondary_roles')
                profile.secondary_roles.set(secondary_roles)
                
                profile.save()
                
                messages.success(request, f'تم تحديث بيانات {profile.arabic_name} بنجاح')
                return redirect('users:user_detail', user_id=user.id)
                
        except Exception as e:
            messages.error(request, f'خطأ في تحديث المستخدم: {str(e)}')
    
    roles = UserRole.objects.filter(is_active=True)
    
    context = {
        'viewed_user': user,
        'roles': roles,
    }
    
    return render(request, 'users/user_edit.html', context)


@login_required
@require_http_methods(["POST"])
def user_approve(request, user_id):
    """
    الموافقة على مستخدم
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        return JsonResponse({'error': 'غير مسموح'}, status=403)
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    profile = user.profile
    
    from django.utils import timezone
    profile.is_approved = True
    profile.approved_by = request.user
    profile.approval_date = timezone.now()
    profile.save()
    
    messages.success(request, f'تمت الموافقة على المستخدم {profile.arabic_name}')
    return redirect('users:user_detail', user_id=user.id)


@login_required
@require_http_methods(["POST"])
def user_reset_password(request, user_id):
    """
    إعادة تعيين كلمة مرور مستخدم
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        return JsonResponse({'error': 'غير مسموح'}, status=403)
    
    user = get_object_or_404(User, id=user_id)
    new_password = request.POST.get('new_password')
    
    if not new_password:
        messages.error(request, 'يجب إدخال كلمة المرور الجديدة')
        return redirect('users:user_detail', user_id=user.id)
    
    user.set_password(new_password)
    user.save()
    
    profile = user.profile
    profile.must_change_password = True
    profile.save()
    
    messages.success(request, f'تم إعادة تعيين كلمة المرور للمستخدم {profile.arabic_name}')
    return redirect('users:user_detail', user_id=user.id)


# ============================================================================
# Role Management Views
# ============================================================================

@login_required
@require_permission('core', 'view')
def role_list(request):
    """
    قائمة الأدوار
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بالوصول لهذه الصفحة')
        return redirect('core:dashboard')
    
    roles = UserRole.objects.annotate(
        user_count=models.Count('userprofile')
    ).order_by('approval_level', 'name')
    
    context = {
        'roles': roles,
    }
    
    return render(request, 'users/role_list.html', context)


@login_required
@require_permission('core', 'view')
def role_detail(request, role_id):
    """
    تفاصيل دور
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بالوصول لهذه الصفحة')
        return redirect('core:dashboard')
    
    role = get_object_or_404(UserRole, id=role_id)
    
    # صلاحيات الوحدات
    module_permissions = ModulePermission.objects.filter(role=role).order_by('module', 'action')
    
    # صلاحيات الموارد
    resource_permissions = ResourcePermission.objects.filter(role=role).order_by('module', 'resource')
    
    # المستخدمون بهذا الدور
    users_with_role = UserProfile.objects.filter(role=role).select_related('user')
    
    context = {
        'role': role,
        'module_permissions': module_permissions,
        'resource_permissions': resource_permissions,
        'users_with_role': users_with_role,
        'default_approval_limit': get_default_approval_limit(role.name),
        'default_discount_limit': get_default_discount_limit(role.name),
    }
    
    return render(request, 'users/role_detail.html', context)


@login_required
@require_permission('core', 'view')
def role_permissions_matrix(request):
    """
    مصفوفة الصلاحيات - نظرة شاملة على صلاحيات كل الأدوار
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بالوصول لهذه الصفحة')
        return redirect('core:dashboard')
    
    roles = UserRole.objects.filter(is_active=True).order_by('approval_level')
    
    # الوحدات والعمليات
    modules = [
        'accounting', 'inventory', 'sales', 'purchases',
        'production', 'hr', 'crm', 'reports', 'maintenance'
    ]
    
    actions = ['view', 'add', 'change', 'delete', 'approve', 'print', 'export']
    
    # بناء المصفوفة
    matrix = {}
    for role in roles:
        matrix[role.id] = {}
        for module in modules:
            matrix[role.id][module] = {}
            for action in actions:
                try:
                    perm = ModulePermission.objects.get(role=role, module=module, action=action)
                    matrix[role.id][module][action] = perm.is_allowed
                except ModulePermission.DoesNotExist:
                    matrix[role.id][module][action] = False
    
    context = {
        'roles': roles,
        'modules': modules,
        'actions': actions,
        'matrix': matrix,
    }
    
    return render(request, 'users/permissions_matrix.html', context)


# ============================================================================
# Security & Activity Logs
# ============================================================================

@login_required
def security_logs(request):
    """
    سجلات الأمان والتنبيهات
    """
    if not (PermissionService.has_role(request.user, ROLE_OWNER) or 
            PermissionService.has_role(request.user, ROLE_SYS_ADMIN)):
        messages.error(request, 'غير مسموح لك بالوصول لهذه الصفحة')
        return redirect('core:dashboard')
    
    # التنبيهات الأمنية
    alerts = SecurityAlert.objects.all().order_by('-timestamp')[:50]
    
    # نشاط المستخدمين الأخير
    recent_activity = UserActivity.objects.select_related('user').order_by('-timestamp')[:100]
    
    context = {
        'alerts': alerts,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'users/security_logs.html', context)


# استيراد models للاستخدام في بعض الدوال
from django.db import models


