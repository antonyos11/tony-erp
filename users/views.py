from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from typing import Optional, Tuple
import json

from .models import (
    UserRole, UserProfile, UserSession, UserActivity, SecurityAlert, ModulePermission, ResourcePermission
)
from functools import wraps

from core.security.permissions_service import PermissionService
from core.security.role_definitions import (
    ROLE_OWNER,
    ROLE_SYS_ADMIN,
    ROLE_BRANCHES_MANAGER,
    ROLE_BRANCH_MANAGER,
    ROLE_BRANCH_VICE_MANAGER,
    ROLE_BRANCH_SUPERVISOR,
    ROLE_BRANCH_ACCOUNTANT,
    ROLE_BRANCH_STORE_KEEPER,
    ROLE_WAREHOUSE_WORKER,
    ROLE_FIN_MANAGER,
    ROLE_SENIOR_ACCOUNTANT,
    ROLE_ACCOUNTANT,
    ROLE_COST_ACCOUNTANT,
    ROLE_TREASURY_OFFICER,
    ROLE_BRANCH_ACCOUNTANT,
    ROLE_INTERNAL_AUDITOR,
    ROLE_HR_MANAGER,
    ROLE_HR_RECRUITER,
    ROLE_HR_PAYROLL,
    ROLE_HR_ATTENDANCE,
    ROLE_HR_TRAINING,
    ROLE_HR_GOV_RELATIONS,
    ROLE_HR_STAFF,
    ROLE_PROCUREMENT_MANAGER,
    ROLE_PROCUREMENT_LEAD,
    ROLE_PROCUREMENT_OFFICER,
    ROLE_PO_OFFICER,
    ROLE_SUPPLIER_FOLLOWUP,
    ROLE_WAREHOUSE_MANAGER,
    ROLE_STORE_SUPERVISOR,
    ROLE_STORE_KEEPER,
    ROLE_INVENTORY_CONTROLLER,
    ROLE_IT_MANAGER,
    ROLE_IT_DEVELOPER,
    ROLE_IT_NETWORK,
    ROLE_IT_SUPPORT,
    ROLE_SALES_MARKETING_MANAGER,
    ROLE_MARKETING_MANAGER,
    ROLE_CAMPAIGN_TEAM,
    ROLE_GRAPHIC_DESIGNER,
    ROLE_CONTENT_CREATOR,
    ROLE_SOCIAL_MEDIA_SPECIALIST,
    ROLE_SALES_MANAGER,
    ROLE_SALES_SUPERVISOR,
    ROLE_SALES_REP_INTERNAL,
    ROLE_SALES_REP_EXTERNAL,
    ROLE_CASHIER,
    ROLE_PRICING_OFFICER,
    ROLE_QUALITY_MANAGER,
    ROLE_QUALITY_INSPECTOR,
    ROLE_CUSTOMER_CARE_LEAD,
    ROLE_CUSTOMER_SERVICE_LEAD,
    ROLE_CS_AGENT,
    ROLE_CS_ORDER_FOLLOWUP,
    ROLE_CS_COMPLAINTS,
    ROLE_OPERATIONS_MANAGER,
    ROLE_FACTORY_MANAGER,
    ROLE_FACTORY_VICE_MANAGER,
    ROLE_PROD_MANAGER,
    ROLE_PRODUCTION_SUPERVISOR,
    ROLE_FOAM_LINE_SUPERVISOR,
    ROLE_SPRING_LINE_SUPERVISOR,
    ROLE_UPHOLSTERY_SUPERVISOR,
    ROLE_SHIFT_LEAD,
    ROLE_PROD_TECHNICIAN,
    ROLE_PROD_STAFF,
    ROLE_PACKAGING_WORKER,
    ROLE_DISPATCH_CONTROLLER,
    ROLE_MAINTENANCE_MANAGER,
    ROLE_MECH_TECH,
    ROLE_ELEC_TECH,
    ROLE_LINE_MAINT_TECH,
    ROLE_SPAREPARTS_CONTROLLER,
    ROLE_QA_LAB_CHEMIST,
    ROLE_QA_RAW_TESTER,
    ROLE_QA_FINAL_TESTER,
    ROLE_QA_SPEC_MATCHER,
    ROLE_HSE_OFFICER,
    ROLE_HSE_SUPERVISOR,
    ROLE_HSE_EMERGENCY,
    ROLE_RAW_STORE_KEEPER,
    ROLE_SEMI_STORE_KEEPER,
    ROLE_FG_STORE_KEEPER,
    ROLE_LABOR_CONTROLLER,
    ROLE_PORTER,
    ROLE_TEA_BOY,
    ROLE_CLEANER,
    ROLE_SECURITY_GUARD,
)


def require_permission(module, action='view', resource=None):
    """مُزخرف لفحص صلاحية وحدة أو مورد قبل تنفيذ العرض.
    إذا تم تحديد resource يتم استخدام user.has_resource_permission، خلاف ذلك has_module_permission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect('/login/?next=' + request.path)
            allowed = False
            if resource:
                allowed = user.has_resource_permission(module, resource, action)
            else:
                allowed = user.has_module_permission(module, action)
            if not allowed:
                return HttpResponseForbidden('غير مسموح لك بالوصول لهذه الصفحة')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# ============================================================================
# Helpers for scoped management
# ============================================================================

MANAGER_SCOPES = {
    ROLE_BRANCHES_MANAGER: {
        'managed_roles': [
            ROLE_BRANCH_MANAGER,
            ROLE_BRANCH_VICE_MANAGER,
            ROLE_BRANCH_SUPERVISOR,
            ROLE_BRANCH_ACCOUNTANT,
            ROLE_BRANCH_STORE_KEEPER,
            ROLE_WAREHOUSE_WORKER,
            ROLE_SALES_REP_INTERNAL,
            ROLE_SALES_REP_EXTERNAL,
            ROLE_CASHIER,
        ],
        'modules': ['sales', 'pos', 'inventory', 'accounting'],
    },
    ROLE_FIN_MANAGER: {
        'managed_roles': [
            ROLE_SENIOR_ACCOUNTANT,
            ROLE_ACCOUNTANT,
            ROLE_COST_ACCOUNTANT,
            ROLE_TREASURY_OFFICER,
            ROLE_BRANCH_ACCOUNTANT,
            ROLE_INTERNAL_AUDITOR,
        ],
        'modules': ['accounting'],
    },
    ROLE_HR_MANAGER: {
        'managed_roles': [
            ROLE_HR_RECRUITER,
            ROLE_HR_PAYROLL,
            ROLE_HR_ATTENDANCE,
            ROLE_HR_TRAINING,
            ROLE_HR_GOV_RELATIONS,
            ROLE_HR_STAFF,
        ],
        'modules': ['hr'],
    },
    ROLE_PROCUREMENT_MANAGER: {
        'managed_roles': [
            ROLE_PROCUREMENT_LEAD,
            ROLE_PROCUREMENT_OFFICER,
            ROLE_PO_OFFICER,
            ROLE_SUPPLIER_FOLLOWUP,
        ],
        'modules': ['purchases'],
    },
    ROLE_WAREHOUSE_MANAGER: {
        'managed_roles': [
            ROLE_STORE_SUPERVISOR,
            ROLE_STORE_KEEPER,
            ROLE_BRANCH_STORE_KEEPER,
            ROLE_INVENTORY_CONTROLLER,
            ROLE_WAREHOUSE_WORKER,
        ],
        'modules': ['inventory'],
    },
    ROLE_IT_MANAGER: {
        'managed_roles': [
            ROLE_IT_DEVELOPER,
            ROLE_IT_NETWORK,
            ROLE_IT_SUPPORT,
        ],
        'modules': ['core'],
    },
    ROLE_SALES_MARKETING_MANAGER: {
        'managed_roles': [
            ROLE_MARKETING_MANAGER,
            ROLE_CAMPAIGN_TEAM,
            ROLE_GRAPHIC_DESIGNER,
            ROLE_CONTENT_CREATOR,
            ROLE_SOCIAL_MEDIA_SPECIALIST,
            ROLE_SALES_MANAGER,
            ROLE_SALES_SUPERVISOR,
            ROLE_SALES_REP_INTERNAL,
            ROLE_SALES_REP_EXTERNAL,
            ROLE_CASHIER,
            ROLE_PRICING_OFFICER,
        ],
        'modules': ['sales', 'pos'],
    },
    ROLE_SALES_MANAGER: {
        'managed_roles': [
            ROLE_SALES_SUPERVISOR,
            ROLE_SALES_REP_INTERNAL,
            ROLE_SALES_REP_EXTERNAL,
            ROLE_CASHIER,
            ROLE_PRICING_OFFICER,
        ],
        'modules': ['sales', 'pos'],
    },
    ROLE_MARKETING_MANAGER: {
        'managed_roles': [
            ROLE_CAMPAIGN_TEAM,
            ROLE_GRAPHIC_DESIGNER,
            ROLE_CONTENT_CREATOR,
            ROLE_SOCIAL_MEDIA_SPECIALIST,
        ],
        'modules': ['sales'],
    },
    ROLE_QUALITY_MANAGER: {
        'managed_roles': [ROLE_QUALITY_INSPECTOR, ROLE_CUSTOMER_CARE_LEAD],
        'modules': ['production', 'sales', 'inventory'],
    },
    ROLE_CUSTOMER_SERVICE_LEAD: {
        'managed_roles': [ROLE_CS_AGENT, ROLE_CS_ORDER_FOLLOWUP, ROLE_CS_COMPLAINTS],
        'modules': ['sales'],
    },
    ROLE_OPERATIONS_MANAGER: {
        'managed_roles': [
            ROLE_FACTORY_MANAGER,
            ROLE_FACTORY_VICE_MANAGER,
            ROLE_PROD_MANAGER,
            ROLE_PRODUCTION_SUPERVISOR,
            ROLE_FOAM_LINE_SUPERVISOR,
            ROLE_SPRING_LINE_SUPERVISOR,
            ROLE_UPHOLSTERY_SUPERVISOR,
            ROLE_SHIFT_LEAD,
            ROLE_PROD_TECHNICIAN,
            ROLE_PROD_STAFF,
            ROLE_PACKAGING_WORKER,
            ROLE_DISPATCH_CONTROLLER,
            ROLE_MAINTENANCE_MANAGER,
            ROLE_MECH_TECH,
            ROLE_ELEC_TECH,
            ROLE_LINE_MAINT_TECH,
            ROLE_SPAREPARTS_CONTROLLER,
            ROLE_QA_LAB_CHEMIST,
            ROLE_QA_RAW_TESTER,
            ROLE_QA_FINAL_TESTER,
            ROLE_QA_SPEC_MATCHER,
            ROLE_HSE_OFFICER,
            ROLE_HSE_SUPERVISOR,
            ROLE_HSE_EMERGENCY,
            ROLE_RAW_STORE_KEEPER,
            ROLE_SEMI_STORE_KEEPER,
            ROLE_FG_STORE_KEEPER,
            ROLE_LABOR_CONTROLLER,
            ROLE_PORTER,
            ROLE_TEA_BOY,
            ROLE_CLEANER,
            ROLE_SECURITY_GUARD,
        ],
        'modules': ['production', 'maintenance', 'inventory'],
    },
    ROLE_FACTORY_MANAGER: {
        'managed_roles': [
            ROLE_FACTORY_VICE_MANAGER,
            ROLE_PROD_MANAGER,
            ROLE_PRODUCTION_SUPERVISOR,
            ROLE_FOAM_LINE_SUPERVISOR,
            ROLE_SPRING_LINE_SUPERVISOR,
            ROLE_UPHOLSTERY_SUPERVISOR,
            ROLE_SHIFT_LEAD,
            ROLE_PROD_TECHNICIAN,
            ROLE_PROD_STAFF,
            ROLE_PACKAGING_WORKER,
            ROLE_DISPATCH_CONTROLLER,
            ROLE_MAINTENANCE_MANAGER,
            ROLE_MECH_TECH,
            ROLE_ELEC_TECH,
            ROLE_LINE_MAINT_TECH,
            ROLE_SPAREPARTS_CONTROLLER,
            ROLE_QA_LAB_CHEMIST,
            ROLE_QA_RAW_TESTER,
            ROLE_QA_FINAL_TESTER,
            ROLE_QA_SPEC_MATCHER,
            ROLE_HSE_OFFICER,
            ROLE_HSE_SUPERVISOR,
            ROLE_HSE_EMERGENCY,
            ROLE_RAW_STORE_KEEPER,
            ROLE_SEMI_STORE_KEEPER,
            ROLE_FG_STORE_KEEPER,
            ROLE_LABOR_CONTROLLER,
            ROLE_PORTER,
            ROLE_TEA_BOY,
            ROLE_CLEANER,
            ROLE_SECURITY_GUARD,
        ],
        'modules': ['production', 'maintenance', 'inventory'],
    },
}


def _get_management_scope(user) -> Tuple[str, Optional[dict]]:
    """Return (scope_type, scope) where scope_type in {'admin','manager','none'}."""
    if not user.is_authenticated:
        return 'none', None
    if user.is_superuser or PermissionService.has_role(user, ROLE_OWNER) or PermissionService.has_role(user, ROLE_SYS_ADMIN):
        return 'admin', None
    for role_code, scope in MANAGER_SCOPES.items():
        if PermissionService.has_role(user, role_code):
            return 'manager', scope
    return 'none', None


def _filter_users_for_scope(queryset, actor: User, scope_type: str, scope: Optional[dict]):
    """Limit queryset to what the actor is allowed to manage."""
    if scope_type == 'manager' and scope:
        # بعض الـ querysets تعتمد على user (مثل UserSession)، لذلك نحدد المسار المناسب
        model_field_names = {field.name for field in queryset.model._meta.get_fields()}
        prefix = 'profile__'
        if 'user' in model_field_names and queryset.model is not User:
            prefix = 'user__profile__'

        return queryset.filter(
            **{
                f'{prefix}managed_by': actor,
                f'{prefix}role__name__in': scope.get('managed_roles', []),
            }
        )
    return queryset


def _is_target_manageable(actor: User, target_profile: Optional[UserProfile], scope_type: str, scope: Optional[dict]) -> bool:
    if scope_type == 'admin':
        return True
    if scope_type == 'manager' and target_profile and scope:
        if target_profile.is_managed_by(actor) and target_profile.role.name in scope.get('managed_roles', []):
            return True
        if target_profile.managed_by_id is None and target_profile.role.name in scope.get('managed_roles', []):
            return True
    return False


def _allowed_roles_queryset(scope_type: str, scope: Optional[dict]):
    roles_qs = UserRole.objects.filter(is_active=True)
    if scope_type == 'manager' and scope:
        roles_qs = roles_qs.filter(name__in=scope.get('managed_roles', []))
    return roles_qs

def user_login(request):
    """صفحة تسجيل الدخول"""
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/dashboard/')
            return redirect(next_url)
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')
    
    return render(request, 'registration/login.html')


@login_required
def dashboard(request):
    """لوحة تحكم المستخدم الرئيسية"""
    user = request.user
    profile = get_user_profile(user)
    
    context = {
        'user': user,
        'profile': profile,
        'recent_activities': UserActivity.objects.filter(
            user=user
        ).order_by('-timestamp')[:10],
        'active_sessions': UserSession.objects.filter(
            user=user,
            is_active=True
        ).count(),
        'security_alerts': SecurityAlert.objects.filter(
            user=user,
            is_resolved=False
        ).count(),
    }
    
    return render(request, 'users/dashboard.html', context)


@login_required
def user_list(request):
    """قائمة المستخدمين"""
    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        messages.error(request, 'ليس لديك صلاحية لعرض المستخدمين')
        return redirect('core:dashboard')

    users = User.objects.select_related('profile', 'profile__role').all()
    users = _filter_users_for_scope(users, request.user, scope_type, scope)
    allowed_roles = _allowed_roles_queryset(scope_type, scope)
    
    # البحث والتصفية
    search = request.GET.get('search', '')
    role_id = request.GET.get('role', '')
    is_active = request.GET.get('is_active', '')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(profile__arabic_name__icontains=search) |
            Q(profile__employee_id__icontains=search)
        )
    
    if role_id:
        if allowed_roles.filter(id=role_id).exists():
            users = users.filter(profile__role_id=role_id)
        else:
            messages.warning(request, 'لا يمكنك التصفية على دور خارج نطاق صلاحياتك')
    
    if is_active == 'true':
        users = users.filter(is_active=True)
    elif is_active == 'false':
        users = users.filter(is_active=False)
    
    # ترقيم الصفحات
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'roles': allowed_roles,
        'search': search,
        'selected_role': role_id,
        'selected_active': is_active,
        'scope_type': scope_type,
    }
    
    return render(request, 'users/user_list.html', context)


@login_required
def user_profile(request):
    """تحديث الملف الشخصي"""
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'arabic_name': request.user.get_full_name() or request.user.username,
            'employee_id': f'EMP{request.user.id:04d}',
            'role': UserRole.objects.filter(name='viewer').first()
        }
    )
    
    if request.method == 'POST':
        # تحديث المعلومات الأساسية
        new_username = request.POST.get('username', '').strip()
        if new_username and new_username != request.user.username:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                messages.error(request, 'اسم المستخدم موجود بالفعل، اختر اسم آخر')
                return render(request, 'users/profile.html', {'profile': profile})
            request.user.username = new_username
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # تحديث الملف الشخصي
        profile.arabic_name = request.POST.get('arabic_name', '')
        profile.phone = request.POST.get('phone', '')
        profile.position = request.POST.get('position', '')
        profile.save()
        
        messages.success(request, 'تم تحديث الملف الشخصي بنجاح')
        return redirect('users:profile')
    
    return render(request, 'users/profile.html', {'profile': profile})


@login_required
def change_password(request):
    """تغيير كلمة المرور"""
    if request.method == 'POST':
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        errors = []
        
        # التحقق من كلمة المرور الحالية
        if not request.user.check_password(old_password):
            error_msg = 'كلمة المرور الحالية غير صحيحة'
            errors.append(error_msg)
            if not is_ajax:
                messages.error(request, error_msg)
        
        # التحقق من تطابق كلمتي المرور الجديدتين
        if new_password1 != new_password2:
            error_msg = 'كلمتا المرور الجديدتان غير متطابقتان'
            errors.append(error_msg)
            if not is_ajax:
                messages.error(request, error_msg)
        
        # التحقق من قوة كلمة المرور
        if len(new_password1) < 8:
            error_msg = 'يجب أن تحتوي كلمة المرور على 8 أحرف على الأقل'
            errors.append(error_msg)
            if not is_ajax:
                messages.error(request, error_msg)
        
        if errors:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': ' - '.join(errors)
                })
            return render(request, 'users/change_password.html')
        
        # تغيير كلمة المرور
        request.user.set_password(new_password1)
        request.user.save()
        
        # تحديث حالة الملف الشخصي
        try:
            profile = request.user.profile
            profile.must_change_password = False
            profile.password_last_changed = timezone.now()
            profile.save()
        except UserProfile.DoesNotExist:
            # إنشاء ملف شخصي جديد إذا لم يكن موجوداً
            UserProfile.objects.get_or_create(
                user=request.user,
                defaults={
                    'must_change_password': False,
                    'password_last_changed': timezone.now()
                }
            )
        
        # تحديث الجلسة
        update_session_auth_hash(request, request.user)
        
        # تسجيل النشاط
        UserActivity.objects.create(
            user=request.user,
            action='تغيير كلمة المرور',
            module='إدارة المستخدمين',
            description='تم تغيير كلمة المرور بنجاح',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        success_msg = 'تم تغيير كلمة المرور بنجاح'
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': success_msg,
                'redirect': '/users/profile/' if not request.user.get_profile().must_change_password else '/'
            })
        
        messages.success(request, success_msg)
        return redirect('users:profile')
    
    return render(request, 'users/change_password.html')


@login_required
def activity_log(request):
    """سجل أنشطة المستخدمين"""
    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        messages.error(request, 'ليس لديك صلاحية لعرض السجل')
        return redirect('users:list')

    activities = UserActivity.objects.select_related('user', 'user__profile', 'user__profile__role').order_by('-timestamp')
    activities = _filter_users_for_scope(activities, request.user, scope_type, scope)
    
    # تصفية حسب المستخدم
    user_id = request.GET.get('user')
    if user_id:
        activities = activities.filter(user_id=user_id)
    
    # تصفية حسب الوحدة
    module = request.GET.get('module')
    if module:
        activities = activities.filter(module=module)
    
    # ترقيم الصفحات
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': _filter_users_for_scope(User.objects.filter(is_active=True).select_related('profile', 'profile__role'), request.user, scope_type, scope),
        'selected_user': user_id,
        'selected_module': module,
    }
    
    return render(request, 'users/activity_log.html', context)


@login_required
def security_alerts(request):
    """عرض التنبيهات الأمنية"""
    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        messages.error(request, 'ليس لديك صلاحية لعرض التنبيهات')
        return redirect('users:list')

    alerts = SecurityAlert.objects.select_related('user', 'user__profile', 'user__profile__role', 'resolved_by').order_by('-timestamp')
    alerts = _filter_users_for_scope(alerts, request.user, scope_type, scope)
    
    # تصفية حسب النوع
    alert_type = request.GET.get('type')
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    
    # تصفية حسب الحالة
    resolved = request.GET.get('resolved')
    if resolved == 'true':
        alerts = alerts.filter(is_resolved=True)
    elif resolved == 'false':
        alerts = alerts.filter(is_resolved=False)
    
    paginator = Paginator(alerts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'users/security_alerts.html', {
        'page_obj': page_obj,
        'alert_types': SecurityAlert.ALERT_TYPES,
        'selected_type': alert_type,
        'selected_resolved': resolved,
    })


@login_required
def resolve_alert(request, alert_id):
    """حل تنبيه أمني"""
    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        messages.error(request, 'ليس لديك صلاحية لمعالجة التنبيهات')
        return redirect('users:security_alerts')

    alert = get_object_or_404(SecurityAlert.objects.select_related('user', 'user__profile', 'user__profile__role'), pk=alert_id)
    if alert.user and not _is_target_manageable(request.user, get_user_profile(alert.user), scope_type, scope):
        messages.error(request, 'لا يمكنك تعديل تنبيه لمستخدم خارج نطاق صلاحياتك')
        return redirect('users:security_alerts')
    alert.is_resolved = True
    alert.resolved_by = request.user
    alert.save()
    
    messages.success(request, 'تم حل التنبيه بنجاح')
    return redirect('users:security_alerts')


@login_required
def session_management(request):
    """إدارة جلسات المستخدمين"""
    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        messages.error(request, 'ليس لديك صلاحية لإدارة الجلسات')
        return redirect('users:list')

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user')
        
        if action == 'terminate_all':
            sessions = UserSession.objects.filter(is_active=True)
            if user_id:
                sessions = sessions.filter(user_id=user_id)
            sessions = _filter_users_for_scope(sessions, request.user, scope_type, scope)
            count = sessions.update(is_active=False)
            messages.success(request, f'تم إنهاء {count} جلسة')
            
        elif action == 'terminate_inactive':
            cutoff_time = timezone.now() - timedelta(hours=2)
            sessions = UserSession.objects.filter(
                is_active=True,
                last_activity__lt=cutoff_time
            )
            if user_id:
                sessions = sessions.filter(user_id=user_id)
            sessions = _filter_users_for_scope(sessions, request.user, scope_type, scope)
            count = sessions.update(is_active=False)
            messages.success(request, f'تم إنهاء {count} جلسة غير نشطة')
        
        return redirect('users:sessions')
    
    # قائمة الجلسات النشطة
    active_sessions = UserSession.objects.filter(
        is_active=True
    ).select_related('user', 'user__profile', 'user__profile__role')
    active_sessions = _filter_users_for_scope(active_sessions, request.user, scope_type, scope)
    active_sessions = active_sessions.order_by('-last_activity')[:50]
    
    return render(request, 'users/session_management.html', {
        'active_sessions': active_sessions,
        'users': _filter_users_for_scope(User.objects.filter(is_active=True).select_related('profile', 'profile__role'), request.user, scope_type, scope),
    })


@login_required
def user_permissions_api(request, user_id):
    """API لعرض صلاحيات المستخدم"""
    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        return JsonResponse({'error': 'غير مسموح'}, status=403)

    user = get_object_or_404(User, pk=user_id)
    target_profile = get_user_profile(user)
    if not _is_target_manageable(request.user, target_profile, scope_type, scope):
        return JsonResponse({'error': 'غير مسموح'}, status=403)
    
    permissions = {}
    profile = None
    try:
        profile = user.profile
        all_roles = profile.get_all_roles()
        
        for role in all_roles:
            role_permissions = ModulePermission.objects.filter(role=role, is_allowed=True)
            for perm in role_permissions:
                if perm.module not in permissions:
                    permissions[perm.module] = []
                if perm.action not in permissions[perm.module]:
                    permissions[perm.module].append(perm.action)
    except UserProfile.DoesNotExist:
        pass
    
    return JsonResponse({
        'user': {
            'id': user.pk,
            'name': user.get_full_name() or user.username,
            'role': profile.role.display_name if hasattr(user, 'profile') and user.profile else None,
        },
        'permissions': permissions
    })


def get_client_ip(request):
    """الحصول على عنوان IP الحقيقي للعميل"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def permissions_manager(request):
    """إدارة الصلاحيات"""
    # فحص صلاحية المستخدم
    if not (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role.name == 'super_admin')):
        messages.error(request, 'غير مسموح لك بالوصول لهذه الصفحة')
        return redirect('core:dashboard')
    
    roles = UserRole.objects.all().order_by('approval_level', 'name')
    modules = ModulePermission.MODULE_CHOICES
    actions = ModulePermission.ACTION_CHOICES
    
    if request.method == 'POST':
        role_id = request.POST.get('role_id')
        module = request.POST.get('module')
        action = request.POST.get('action')
        is_allowed = request.POST.get('is_allowed') == 'true'
        
        if role_id and module and action:
            try:
                role = UserRole.objects.get(id=role_id)
                permission, created = ModulePermission.objects.get_or_create(
                    role=role,
                    module=module,
                    action=action,
                    defaults={'is_allowed': is_allowed}
                )
                
                if not created:
                    permission.is_allowed = is_allowed
                    permission.save()
                
                # تسجيل النشاط
                UserActivity.objects.create(
                    user=request.user,
                    action='تعديل صلاحيات',
                    module='إدارة المستخدمين',
                    description=f'تعديل صلاحية {role.display_name} في {module} - {action}: {"مسموح" if is_allowed else "ممنوع"}',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
                
                return JsonResponse({'success': True, 'message': 'تم تحديث الصلاحية'})
                
            except UserRole.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'الدور غير موجود'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'خطأ: {str(e)}'})
        
        return JsonResponse({'success': False, 'message': 'بيانات غير مكتملة'})
    
    # جلب الصلاحيات الحالية
    permissions = {}
    for role in roles:
        permissions[role.id] = {}
        for module_code, module_name in modules:
            permissions[role.id][module_code] = {}
            for action_code, action_name in actions:
                perm = ModulePermission.objects.filter(
                    role=role, module=module_code, action=action_code
                ).first()
                permissions[role.id][module_code][action_code] = perm.is_allowed if perm else False
    
    context = {
        'roles': roles,
        'modules': modules,
        'actions': actions,
        'permissions': permissions,
        'permission_stats': get_permission_stats(roles, modules, actions, permissions),
    }
    return render(request, 'users/permissions_manager.html', context)


def get_permission_stats(roles, modules, actions, permissions):
    """إحصائيات الصلاحيات"""
    stats = {
        'roles': {},
        'modules': {},
        'total_permissions': len(modules) * len(actions),
        'total_allowed': 0,
    }
    
    for role in roles:
        role_allowed = 0
        for module_code, module_name in modules:
            for action_code, action_name in actions:
                if permissions.get(role.id, {}).get(module_code, {}).get(action_code, False):
                    role_allowed += 1
                    stats['total_allowed'] += 1
        stats['roles'][role.id] = role_allowed
    
    for module_code, module_name in modules:
        module_allowed = 0
        for role in roles:
            for action_code, action_name in actions:
                if permissions.get(role.id, {}).get(module_code, {}).get(action_code, False):
                    module_allowed += 1
        stats['modules'][module_code] = module_allowed
    
    return stats


@login_required
def bulk_actions(request):
    """تنفيذ الإجراءات المجمعة على المستخدمين"""
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_users = request.POST.getlist('selected_users')
        
        if not action or not selected_users:
            messages.error(request, 'يرجى اختيار إجراء ومستخدمين للتطبيق')
            return redirect('users:list')
        
        scope_type, scope = _get_management_scope(request.user)
        if scope_type == 'none':
            messages.error(request, 'ليس لديك صلاحية لتنفيذ هذا الإجراء')
            return redirect('users:list')
        
        try:
            users = User.objects.select_related('profile', 'profile__role').filter(id__in=selected_users)
            users = _filter_users_for_scope(users, request.user, scope_type, scope)
            count = users.count()

            if count == 0:
                messages.warning(request, 'لم يتم العثور على مستخدمين داخل نطاق صلاحياتك')
                return redirect('users:list')
            
            if action == 'activate':
                users.update(is_active=True)
                messages.success(request, f'تم تفعيل {count} مستخدم بنجاح')
                
            elif action == 'deactivate':
                # منع إلغاء تفعيل المدير الحالي
                if request.user.id in [int(uid) for uid in selected_users]:
                    messages.warning(request, 'لا يمكنك إلغاء تفعيل حسابك الخاص')
                    users = users.exclude(id=request.user.id)
                    count = users.count()

                users.update(is_active=False)
                if count > 0:
                    messages.success(request, f'تم إلغاء تفعيل {count} مستخدم بنجاح')
                    
            elif action == 'approve':
                # تحديث حالة الموافقة في UserProfile
                profiles = UserProfile.objects.filter(user_id__in=users.values_list('id', flat=True))
                profiles.update(is_approved=True)
                messages.success(request, f'تم الموافقة على {count} مستخدم بنجاح')
                
            else:
                messages.error(request, 'إجراء غير صالح')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تنفيذ الإجراء: {str(e)}')
    
    return redirect('users:list')


@login_required
def create_user(request):
    """إنشاء مستخدم جديد عبر AJAX"""
    if request.method == 'POST':
        scope_type, scope = _get_management_scope(request.user)
        if scope_type == 'none':
            return JsonResponse({'success': False, 'error': 'ليس لديك صلاحية لإنشاء مستخدمين'})
        
        try:
            username = request.POST.get('username')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            arabic_name = request.POST.get('arabic_name', '')
            employee_id = request.POST.get('employee_id', '')
            role_id = request.POST.get('role')
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من عدم وجود المستخدم
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'error': 'اسم المستخدم موجود مسبقاً'})
            
            # التحقق من الدور
            allowed_roles = _allowed_roles_queryset(scope_type, scope)
            try:
                role = allowed_roles.get(id=role_id)
            except UserRole.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'الدور غير صالح أو خارج نطاق صلاحياتك'})
            
            # إنشاء المستخدم
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=is_active
            )
            
            # إنشاء الملف الشخصي
            managed_by = None
            if scope_type == 'manager':
                managed_by = request.user
            else:
                managed_by_id = request.POST.get('managed_by')
                if managed_by_id:
                    managed_by = User.objects.filter(id=managed_by_id).first()

            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'arabic_name': arabic_name,
                    'employee_id': employee_id,
                    'role': role,
                    'is_approved': True,
                    'approved_by': request.user,
                    'approval_date': timezone.now(),
                    'managed_by': managed_by,
                }
            )
            
            return JsonResponse({'success': True, 'message': 'تم إنشاء المستخدم بنجاح'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'حدث خطأ: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})


@login_required  
def user_details_api(request, user_id):
    """API لجلب تفاصيل المستخدم"""
    try:
        scope_type, scope = _get_management_scope(request.user)
        if scope_type == 'none':
            return JsonResponse({'error': 'غير مسموح'}, status=403)

        user = get_object_or_404(User, id=user_id)
        profile = get_user_profile(user)

        if not _is_target_manageable(request.user, profile, scope_type, scope):
            return JsonResponse({'error': 'غير مسموح'}, status=403)
        
        data = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'is_active': user.is_active,
            'last_login': user.last_login.strftime('%d/%m/%Y %H:%M') if user.last_login else None,
            'date_joined': user.date_joined.strftime('%d/%m/%Y'),
            'arabic_name': profile.arabic_name if profile else '',
            'employee_id': profile.employee_id if profile else '',
            'role': profile.role.display_name if profile and profile.role else 'غير محدد',
            'is_approved': profile.is_approved if profile else False,
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_user_profile(user):
    """الحصول على ملف تعريف المستخدم"""
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


@login_required
def user_edit(request, user_id):
    """تعديل بيانات مستخدم (نموذج مبسط)."""
    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        messages.error(request, 'ليس لديك صلاحية لتعديل المستخدمين')
        return redirect('users:list')

    user_obj = get_object_or_404(User, pk=user_id)
    profile = UserProfile.objects.filter(user=user_obj).first()
    if profile is None:
        if scope_type == 'manager':
            messages.error(request, 'لا يمكنك تعديل مستخدم بلا ملف صلاحيات محدد')
            return redirect('users:list')
        profile = UserProfile.objects.create(
            user=user_obj,
            arabic_name=user_obj.get_full_name() or user_obj.username,
            employee_id=f'EMP{user_obj.id:04d}',
            role=UserRole.objects.filter(is_active=True).first(),
            is_approved=True,
        )

    if not _is_target_manageable(request.user, profile, scope_type, scope):
        messages.error(request, 'لا يمكنك تعديل مستخدم خارج نطاق صلاحياتك')
        return redirect('users:list')

    if request.method == 'POST':
        # اجمع المدخلات
        username = (request.POST.get('username') or '').strip()
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        arabic_name = (request.POST.get('arabic_name') or '').strip()
        employee_id = (request.POST.get('employee_id') or '').strip()
        role_id = request.POST.get('role')
        is_active = request.POST.get('is_active') == 'on'
        new_password = request.POST.get('new_password') or ''
        confirm_password = request.POST.get('confirm_password') or ''

        # تحقق بسيط
        if not username:
            messages.error(request, 'اسم المستخدم مطلوب')
            return redirect('users:edit', user_id=user_id)
        # تأكد من عدم تعارض اسم المستخدم
        if username != user_obj.username and User.objects.filter(username=username).exists():
            messages.error(request, 'اسم المستخدم مستخدم من قبل')
            return redirect('users:edit', user_id=user_id)

        # تحديث المستخدم
        user_obj.username = username
        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.email = email
        user_obj.is_active = is_active

        # كلمة المرور (اختياري)
        if new_password or confirm_password:
            if new_password != confirm_password:
                messages.error(request, 'كلمتا المرور غير متطابقتين')
                return redirect('users:edit', user_id=user_id)
            if len(new_password) < 8:
                messages.error(request, 'يجب أن تحتوي كلمة المرور على 8 أحرف على الأقل')
                return redirect('users:edit', user_id=user_id)
            user_obj.set_password(new_password)

        user_obj.save()

        # تحديث الملف الشخصي
        profile.arabic_name = arabic_name
        profile.employee_id = employee_id
        if role_id:
            allowed_roles = _allowed_roles_queryset(scope_type, scope)
            try:
                profile.role = allowed_roles.get(pk=role_id)
            except UserRole.DoesNotExist:
                messages.warning(request, 'لم يتم العثور على الدور المحدد أو أنه خارج نطاق صلاحياتك، تم تجاهله')
        profile.save()

        if scope_type == 'manager' and profile.managed_by_id != request.user.id:
            profile.managed_by = request.user
            profile.save(update_fields=['managed_by'])

        # سجل نشاط بسيط
        try:
            UserActivity.objects.create(
                user=request.user,
                action='تعديل مستخدم',
                module='إدارة المستخدمين',
                description=f'تعديل المستخدم {user_obj.username} (#{user_obj.id})',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception:
            pass

        messages.success(request, 'تم حفظ التعديلات')
        return redirect('users:list')

    # GET: أعرض النموذج
    context = {
        'edit_user': user_obj,
        'profile': profile,
        'roles': _allowed_roles_queryset(scope_type, scope).order_by('display_name'),
    }
    return render(request, 'users/user_edit.html', context)


@login_required
def user_detail(request, user_id):
    """عرض تفاصيل المستخدم"""
    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        messages.error(request, 'ليس لديك صلاحية لعرض المستخدمين')
        return redirect('users:list')

    user_obj = get_object_or_404(User, pk=user_id)
    profile = UserProfile.objects.filter(user=user_obj).first()
    
    if not _is_target_manageable(request.user, profile, scope_type, scope):
        messages.error(request, 'ليس لديك صلاحية لعرض هذا المستخدم')
        return redirect('users:list')

    context = {
        'detail_user': user_obj,
        'profile': profile,
    }
    return render(request, 'users/user_detail.html', context)


@login_required
def user_delete(request, user_id):
    """حذف مستخدم"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'}, status=405)

    scope_type, scope = _get_management_scope(request.user)
    if scope_type == 'none':
        return JsonResponse({'success': False, 'error': 'ليس لديك صلاحية لحذف المستخدمين'}, status=403)

    user_obj = get_object_or_404(User, pk=user_id)

    # لا يمكن حذف نفسك
    if user_obj.id == request.user.id:
        return JsonResponse({'success': False, 'error': 'لا يمكنك حذف حسابك الخاص'}, status=400)

    profile = UserProfile.objects.filter(user=user_obj).first()

    if not _is_target_manageable(request.user, profile, scope_type, scope):
        return JsonResponse({'success': False, 'error': 'ليس لديك صلاحية لحذف هذا المستخدم'}, status=403)

    try:
        username = user_obj.username
        user_id_deleted = user_obj.id

        # حذف الملف الشخصي أولاً إن وجد
        if profile:
            profile.delete()

        # حذف المستخدم
        user_obj.delete()

        # سجل نشاط
        try:
            UserActivity.objects.create(
                user=request.user,
                action='حذف مستخدم',
                module='إدارة المستخدمين',
                description=f'حذف المستخدم {username} (#{user_id_deleted})',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception:
            pass

        return JsonResponse({'success': True, 'message': f'تم حذف المستخدم {username} بنجاح'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'حدث خطأ أثناء الحذف: {str(e)}'}, status=500)


# ===== إدارة الأدوار =====
@login_required
def role_list(request):
    """قائمة الأدوار"""
    roles = UserRole.objects.all().order_by('display_name')
    return render(request, 'users/roles/list.html', {'roles': roles})


@login_required
def role_create(request):
    """إنشاء دور جديد"""
    from .forms import UserRoleForm
    
    if request.method == 'POST':
        form = UserRoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء الدور بنجاح')
            return redirect('users:role_list')
    else:
        form = UserRoleForm()
    
    return render(request, 'users/roles/form.html', {
        'form': form,
        'title': 'إضافة دور جديد',
        'page_title': 'إضافة دور جديد',
        'form_title': 'بيانات الدور',
        'cancel_url': '/users/roles/'
    })


@login_required
def role_detail(request, pk):
    """عرض تفاصيل الدور"""
    role = get_object_or_404(UserRole, pk=pk)
    users = User.objects.filter(profile__role=role)
    permissions = role.permissions.all() if hasattr(role, 'permissions') else []
    
    context = {
        'role': role,
        'users': users,
        'permissions': permissions,
    }
    return render(request, 'users/roles/detail.html', context)


@login_required
def role_edit(request, pk):
    """تعديل دور"""
    from .forms import UserRoleForm
    
    role = get_object_or_404(UserRole, pk=pk)
    if request.method == 'POST':
        form = UserRoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الدور بنجاح')
            return redirect('users:role_list')
    else:
        form = UserRoleForm(instance=role)
    
    return render(request, 'users/roles/form.html', {
        'form': form,
        'role': role,
        'title': f'تعديل الدور: {role.display_name}',
        'page_title': 'تعديل الدور',
        'form_title': 'بيانات الدور',
        'cancel_url': '/users/roles/'
    })


@login_required
def role_delete(request, pk):
    """حذف دور"""
    role = get_object_or_404(UserRole, pk=pk)
    if request.method == 'POST':
        if role.users.exists():
            messages.error(request, 'لا يمكن حذف دور له مستخدمين مرتبطين')
        else:
            role.delete()
            messages.success(request, 'تم حذف الدور بنجاح')
        return redirect('users:role_list')
    return render(request, 'users/roles/delete.html', {'role': role})


# ===== صلاحيات الصفحات =====
@login_required
def page_permissions(request):
    """إدارة صلاحيات الصفحات"""
    from core.models import Page, PagePermission
    
    if request.method == 'POST':
        # حفظ الصلاحيات
        try:
            data = json.loads(request.body)
            permissions_data = data.get('permissions', [])
            
            for perm in permissions_data:
                page_id = perm.get('page_id')
                role_id = perm.get('role_id')
                
                page_perm, created = PagePermission.objects.get_or_create(
                    page_id=page_id,
                    role_id=role_id
                )
                page_perm.can_view = perm.get('can_view', False)
                page_perm.can_create = perm.get('can_create', False)
                page_perm.can_edit = perm.get('can_edit', False)
                page_perm.can_delete = perm.get('can_delete', False)
                page_perm.can_export = perm.get('can_export', False)
                page_perm.can_print = perm.get('can_print', False)
                page_perm.save()
            
            return JsonResponse({'success': True, 'message': 'تم حفظ الصلاحيات بنجاح'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    roles = UserRole.objects.filter(is_active=True).order_by('display_name')
    pages = Page.objects.filter(is_active=True).select_related('parent').order_by('module', 'order', 'name')
    
    # جلب الصلاحيات الحالية
    existing_permissions = {}
    for perm in PagePermission.objects.select_related('page', 'role').all():
        key = f"{perm.page_id}_{perm.role_id}"
        existing_permissions[key] = {
            'can_view': perm.can_view,
            'can_create': perm.can_create,
            'can_edit': perm.can_edit,
            'can_delete': perm.can_delete,
            'can_export': perm.can_export,
            'can_print': perm.can_print,
        }
    
    # تجميع الصفحات حسب الموديول
    modules = {}
    for page in pages:
        module = page.module or 'other'
        if module not in modules:
            modules[module] = {
                'name': dict(Page.MODULE_CHOICES).get(module, module),
                'pages': []
            }
        modules[module]['pages'].append(page)
    
    context = {
        'roles': roles,
        'pages': pages,
        'modules': modules,
        'existing_permissions': json.dumps(existing_permissions),
    }
    return render(request, 'users/permissions/pages.html', context)