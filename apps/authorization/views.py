"""
واجهات الصلاحيات والهيكل الإداري — RITA ERP
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, View

from apps.authorization.decorators import PermissionRequiredMixin
from apps.authorization.models import (
    Role, Permission, UserRole, AuditLog, Delegation,
    # Sprint 22A
    SystemPermission, SystemRole, UserRoleAssignment, SecurityViolationLog,
    # Sprint 23
    ApprovalRequest,
)
from apps.authorization.services.audit import log_action, get_client_ip
from apps.authorization.services.permission_engine import PermissionEngine
from apps.core.models import User


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class RoleForm(forms.ModelForm):
    """فورم إنشاء/تعديل دور"""
    class Meta:
        model = Role
        fields = [
            'name', 'level', 'description', 'max_discount_percentage',
            'can_see_cost', 'can_see_profit', 'can_see_other_branches',
            'can_delete', 'can_modify_prices', 'can_approve_entries',
            'can_create_users', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'can_see_cost': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_see_profit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_see_other_branches': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_delete': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_modify_prices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_approve_entries': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_create_users': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserRoleForm(forms.Form):
    """فورم تعيين دور لمستخدم"""
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'username'),
        label='المستخدم',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True).order_by('name'),
        label='الدور',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    is_primary = forms.BooleanField(
        required=False, initial=False,
        label='دور أساسي',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )


class DelegationForm(forms.ModelForm):
    """فورم إنشاء تفويض"""
    class Meta:
        model = Delegation
        fields = ['delegate', 'role', 'start_date', 'end_date', 'reason']
        widgets = {
            'delegate': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'
            }),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'delegate': 'المفوَّض إليه',
            'role': 'الدور المفوَّض',
            'start_date': 'بداية التفويض',
            'end_date': 'نهاية التفويض',
            'reason': 'السبب',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delegate'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'username')
        self.fields['role'].queryset = Role.objects.filter(
            is_active=True
        ).order_by('name')


# ══════════════════════════════════════════════════════
# الأدوار
# ══════════════════════════════════════════════════════

class RoleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """قائمة الأدوار"""
    permission_module = 'settings'
    permission_action = 'view'
    model = Role
    template_name = 'authorization/role_list.html'
    context_object_name = 'roles'

    def get_queryset(self):
        return Role.objects.filter(is_deleted=False).order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'الأدوار الوظيفية'
        for role in ctx['roles']:
            role.user_count = UserRole.objects.filter(role=role, is_active=True).count()
            role.permission_count = Permission.objects.filter(role=role, is_allowed=True).count()
        return ctx


class RoleCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إنشاء دور جديد مع صلاحياته"""
    permission_module = 'settings'
    permission_action = 'create'
    template_name = 'authorization/role_form.html'

    def get(self, request):
        form = RoleForm()
        return render(request, self.template_name, {
            'form': form,
            'title': 'إنشاء دور جديد',
            'modules': Permission.MODULES,
            'actions': Permission.ACTIONS,
        })

    def post(self, request):
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save(commit=False)
            role.created_by = request.user
            role.updated_by = request.user
            role.save()

            # حفظ الصلاحيات
            for mod_code, mod_name in Permission.MODULES:
                for act_code, act_name in Permission.ACTIONS:
                    key = f'perm_{mod_code}_{act_code}'
                    is_allowed = request.POST.get(key) == 'on'
                    Permission.objects.create(
                        role=role,
                        module=mod_code,
                        action=act_code,
                        is_allowed=is_allowed,
                        created_by=request.user,
                        updated_by=request.user,
                    )

            log_action(
                user=request.user,
                action='create',
                module='settings',
                model_name='Role',
                object_id=role.pk,
                description=f'إنشاء دور: {role.name}',
                ip_address=get_client_ip(request),
            )

            messages.success(request, f'تم إنشاء الدور "{role.name}" بنجاح')
            return redirect('authorization:role_detail', pk=role.pk)

        return render(request, self.template_name, {
            'form': form,
            'title': 'إنشاء دور جديد',
            'modules': Permission.MODULES,
            'actions': Permission.ACTIONS,
        })


class RoleDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """تفاصيل الدور وصلاحياته"""
    permission_module = 'settings'
    permission_action = 'view'
    model = Role
    template_name = 'authorization/role_detail.html'
    context_object_name = 'role'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        role = self.object
        ctx['title'] = f'دور: {role.name}'
        ctx['users'] = UserRole.objects.filter(
            role=role, is_active=True
        ).select_related('user').order_by('user__first_name')

        # بناء مصفوفة الصلاحيات
        permissions = Permission.objects.filter(role=role)
        perm_matrix = {}
        for mod_code, mod_name in Permission.MODULES:
            perm_matrix[mod_code] = {
                'name': mod_name,
                'actions': {}
            }
            for act_code, act_name in Permission.ACTIONS:
                perm = permissions.filter(module=mod_code, action=act_code).first()
                perm_matrix[mod_code]['actions'][act_code] = {
                    'name': act_name,
                    'allowed': perm.is_allowed if perm else False,
                }
        ctx['perm_matrix'] = perm_matrix
        ctx['actions'] = Permission.ACTIONS
        return ctx


# ══════════════════════════════════════════════════════
# تعيين الأدوار
# ══════════════════════════════════════════════════════

class UserRoleAssignView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تعيين دور لمستخدم"""
    permission_module = 'settings'
    permission_action = 'create'
    template_name = 'authorization/assign_role.html'

    def get(self, request):
        form = UserRoleForm()
        assignments = UserRole.objects.filter(
            is_active=True, is_deleted=False
        ).select_related('user', 'role').order_by('user__first_name')
        return render(request, self.template_name, {
            'form': form,
            'assignments': assignments,
            'title': 'تعيين الأدوار',
        })

    def post(self, request):
        form = UserRoleForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            role = form.cleaned_data['role']
            is_primary = form.cleaned_data.get('is_primary', False)

            user_role, created = UserRole.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    'is_primary': is_primary,
                    'is_active': True,
                    'created_by': request.user,
                    'updated_by': request.user,
                },
            )

            if not created:
                user_role.is_active = True
                user_role.is_primary = is_primary
                user_role.updated_by = request.user
                user_role.save()

            log_action(
                user=request.user,
                action='create',
                module='settings',
                model_name='UserRole',
                object_id=user_role.pk,
                description=f'تعيين دور "{role.name}" للمستخدم "{user}"',
                ip_address=get_client_ip(request),
            )

            messages.success(request, f'تم تعيين الدور "{role.name}" للمستخدم "{user}" بنجاح')
            return redirect('authorization:assign_role')

        assignments = UserRole.objects.filter(
            is_active=True, is_deleted=False
        ).select_related('user', 'role').order_by('user__first_name')
        return render(request, self.template_name, {
            'form': form,
            'assignments': assignments,
            'title': 'تعيين الأدوار',
        })


# ══════════════════════════════════════════════════════
# سجل التدقيق
# ══════════════════════════════════════════════════════

class AuditLogView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """سجل التدقيق"""
    permission_module = 'settings'
    permission_action = 'view'
    model = AuditLog
    template_name = 'authorization/audit_log.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user', 'branch').order_by('-timestamp')

        user_id = self.request.GET.get('user', '')
        action = self.request.GET.get('action', '')
        module = self.request.GET.get('module', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if user_id:
            qs = qs.filter(user_id=user_id)
        if action:
            qs = qs.filter(action=action)
        if module:
            qs = qs.filter(module=module)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'سجل التدقيق'
        ctx['users'] = User.objects.filter(is_active=True).order_by('first_name', 'username')
        ctx['action_types'] = AuditLog.ACTION_TYPES
        ctx['modules'] = Permission.MODULES
        ctx['filter_params'] = self.request.GET.dict()
        return ctx


# ══════════════════════════════════════════════════════
# التفويضات
# ══════════════════════════════════════════════════════

class DelegationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """قائمة التفويضات"""
    permission_module = 'settings'
    permission_action = 'view'
    model = Delegation
    template_name = 'authorization/delegation_list.html'
    context_object_name = 'delegations'
    paginate_by = 25

    def get_queryset(self):
        return Delegation.objects.filter(
            is_deleted=False
        ).select_related(
            'delegator', 'delegate', 'role'
        ).order_by('-start_date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'التفويضات'
        ctx['now'] = timezone.now()
        return ctx


class DelegationCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إنشاء تفويض جديد"""
    permission_module = 'settings'
    permission_action = 'create'
    template_name = 'authorization/delegation_form.html'

    def get(self, request):
        form = DelegationForm()
        return render(request, self.template_name, {
            'form': form,
            'title': 'إنشاء تفويض جديد',
        })

    def post(self, request):
        form = DelegationForm(request.POST)
        if form.is_valid():
            delegation = form.save(commit=False)
            delegation.delegator = request.user
            delegation.created_by = request.user
            delegation.updated_by = request.user
            delegation.save()

            log_action(
                user=request.user,
                action='create',
                module='settings',
                model_name='Delegation',
                object_id=delegation.pk,
                description=f'تفويض من {request.user} إلى {delegation.delegate} — دور: {delegation.role.name}',
                ip_address=get_client_ip(request),
            )

            messages.success(request, 'تم إنشاء التفويض بنجاح')
            return redirect('authorization:delegation_list')

        return render(request, self.template_name, {
            'form': form,
            'title': 'إنشاء تفويض جديد',
        })


# ══════════════════════════════════════════════════════
# Sprint 22A Part 2 — إدارة الأدوار والصلاحيات الجديدة
# ══════════════════════════════════════════════════════

class AssignSystemRoleForm(forms.Form):
    """فورم تعيين دور نظامي لمستخدم"""
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'username'),
        label='المستخدم',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
    )
    role = forms.ModelChoiceField(
        queryset=SystemRole.objects.filter(is_active=True).order_by('sort_order', 'name'),
        label='الدور',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
    )
    branch = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label='الفرع المحدد (اختياري)',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    is_active = forms.BooleanField(
        required=False, initial=True,
        label='نشط',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from apps.core.models import Branch
            self.fields['branch'].queryset = Branch.objects.filter(
                is_active=True
            ).order_by('name')
        except Exception:
            from django.db import models as db_models
            self.fields['branch'].queryset = User.objects.none()


class SystemRoleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """قائمة الأدوار النظامية"""
    permission_module = 'settings'
    permission_action = 'view'
    model = SystemRole
    template_name = 'authorization/system_role_list.html'
    context_object_name = 'roles'

    def get_queryset(self):
        return SystemRole.objects.prefetch_related('permissions').order_by('sort_order', 'name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'الأدوار النظامية'
        ctx['total_permissions'] = SystemPermission.objects.count()
        ctx['total_assignments'] = UserRoleAssignment.objects.filter(is_active=True).count()
        return ctx


class SystemRoleDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """تفاصيل دور نظامي"""
    permission_module = 'settings'
    permission_action = 'view'
    model = SystemRole
    template_name = 'authorization/system_role_detail.html'
    context_object_name = 'role'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        role = self.get_object()
        # تجميع الصلاحيات حسب القسم
        perms_by_module = {}
        for perm in role.permissions.order_by('module', 'action'):
            perms_by_module.setdefault(perm.get_module_display(), []).append(perm)
        ctx['perms_by_module'] = perms_by_module
        ctx['assignments'] = UserRoleAssignment.objects.filter(
            role=role, is_active=True
        ).select_related('user', 'branch').order_by('user__first_name')
        ctx['title'] = f'دور: {role.name}'
        return ctx


class AssignSystemRoleView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تعيين دور نظامي لمستخدم"""
    permission_module = 'settings'
    permission_action = 'create'
    template_name = 'authorization/assign_system_role.html'

    def get(self, request):
        form = AssignSystemRoleForm(initial={'is_active': True})
        existing = UserRoleAssignment.objects.select_related(
            'user', 'role', 'branch', 'assigned_by'
        ).order_by('-assigned_at')[:50]
        return render(request, self.template_name, {
            'form': form,
            'existing': existing,
            'title': 'تعيين دور نظامي',
        })

    def post(self, request):
        form = AssignSystemRoleForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            role = form.cleaned_data['role']
            branch = form.cleaned_data.get('branch')
            is_active = form.cleaned_data.get('is_active', True)

            # التحقق من صلاحية المانح
            if not PermissionEngine.can_grant_role(request.user, role):
                messages.error(request, f'⛔ لا تملك صلاحية منح دور "{role.name}"')
                return redirect('authorization:assign_system_role')

            assignment, created = UserRoleAssignment.objects.update_or_create(
                user=user,
                role=role,
                defaults={
                    'branch': branch,
                    'assigned_by': request.user,
                    'is_active': is_active,
                },
            )

            action_text = 'إنشاء' if created else 'تحديث'
            log_action(
                user=request.user,
                action='create' if created else 'update',
                module='settings',
                model_name='UserRoleAssignment',
                object_id=assignment.pk,
                description=f'{action_text} تعيين: {user} ← {role.name}',
                ip_address=get_client_ip(request),
            )
            messages.success(request, f'✅ تم تعيين دور "{role.name}" للمستخدم {user.get_full_name() or user.username}')
            return redirect('authorization:assign_system_role')

        existing = UserRoleAssignment.objects.select_related(
            'user', 'role', 'branch', 'assigned_by'
        ).order_by('-assigned_at')[:50]
        return render(request, self.template_name, {
            'form': form,
            'existing': existing,
            'title': 'تعيين دور نظامي',
        })


class RevokeSystemRoleView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إلغاء تعيين دور نظامي"""
    permission_module = 'settings'
    permission_action = 'edit'

    def post(self, request, pk):
        assignment = get_object_or_404(UserRoleAssignment, pk=pk)
        if not PermissionEngine.can_grant_role(request.user, assignment.role):
            messages.error(request, '⛔ لا تملك صلاحية إلغاء هذا الدور')
            return redirect('authorization:assign_system_role')

        assignment.is_active = False
        assignment.save()
        log_action(
            user=request.user,
            action='update',
            module='settings',
            model_name='UserRoleAssignment',
            object_id=assignment.pk,
            description=f'إلغاء تعيين: {assignment.user} ← {assignment.role.name}',
            ip_address=get_client_ip(request),
        )
        messages.success(request, f'تم إلغاء دور "{assignment.role.name}" من {assignment.user}')
        return redirect('authorization:assign_system_role')


class SecurityViolationLogView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """سجل محاولات الاختراق الأمني"""
    permission_module = 'settings'
    permission_action = 'view'
    model = SecurityViolationLog
    template_name = 'authorization/security_violations.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        qs = SecurityViolationLog.objects.select_related('user').order_by('-timestamp')
        user_id = self.request.GET.get('user', '')
        module = self.request.GET.get('module', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if user_id:
            qs = qs.filter(user_id=user_id)
        if module:
            qs = qs.filter(attempted_module=module)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'سجل الأمان — محاولات الوصول غير المصرح'
        ctx['users'] = User.objects.filter(is_active=True).order_by('first_name', 'username')
        ctx['modules'] = SystemPermission.objects.values_list('module', flat=True).distinct().order_by('module')
        ctx['filter_params'] = self.request.GET.dict()
        ctx['total_today'] = SecurityViolationLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).count()
        return ctx


# ══════════════════════════════════════════════════════
# Sprint 23 — نظام الاعتماد والموافقات
# ══════════════════════════════════════════════════════

class ApprovalListView(LoginRequiredMixin, ListView):
    """طلبات الاعتماد الواردة (المعلقة للمستخدم الحالي كمعتمد)"""
    model = ApprovalRequest
    template_name = 'authorization/approval_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        from apps.authorization.services.permission_engine import PermissionEngine
        qs = ApprovalRequest.objects.select_related(
            'requested_by', 'approved_by', 'branch'
        ).order_by('-created_at')

        # فلترة بالحالة
        status = self.request.GET.get('status', 'pending')
        if status:
            qs = qs.filter(status=status)

        # فلترة بالنوع
        req_type = self.request.GET.get('request_type', '')
        if req_type:
            qs = qs.filter(request_type=req_type)

        # غير super admin — يرى فقط ما يستطيع اعتماده
        if not self.request.user.is_superuser:
            # يرى الطلبات المعلقة فقط
            qs = qs.filter(status='pending')

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'طلبات الاعتماد'
        ctx['pending_count'] = ApprovalRequest.objects.filter(status='pending').count()
        ctx['status_choices'] = ApprovalRequest.STATUSES
        ctx['type_choices'] = ApprovalRequest.REQUEST_TYPES
        ctx['current_status'] = self.request.GET.get('status', 'pending')
        ctx['current_type'] = self.request.GET.get('request_type', '')
        return ctx


class ApprovalDetailView(LoginRequiredMixin, DetailView):
    """تفاصيل طلب الاعتماد مع أزرار اعتماد/رفض"""
    model = ApprovalRequest
    template_name = 'authorization/approval_detail.html'
    context_object_name = 'approval'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'طلب اعتماد #{self.object.pk}'
        ctx['can_process'] = (
            self.request.user.is_superuser or
            self.object.status == 'pending'
        )
        return ctx


class ApprovalProcessView(LoginRequiredMixin, View):
    """POST — اعتماد أو رفض طلب"""

    def post(self, request, pk):
        from apps.authorization.services.approval_engine import ApprovalEngine

        approval = get_object_or_404(ApprovalRequest, pk=pk)

        if approval.status != 'pending':
            messages.warning(request, 'هذا الطلب تمت معالجته مسبقاً')
            return redirect('authorization:approval_detail', pk=pk)

        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()

        if action == 'approve':
            ApprovalEngine.approve(approval, approver=request.user)
            log_action(
                user=request.user,
                action='approve',
                module='authorization',
                model_name='ApprovalRequest',
                object_id=approval.pk,
                description=f'اعتماد طلب #{approval.pk} — {approval.get_request_type_display()}',
                ip_address=get_client_ip(request),
            )
            messages.success(request, f'✅ تم اعتماد الطلب #{approval.pk}')

        elif action == 'reject':
            if not reason:
                messages.error(request, 'يجب إدخال سبب الرفض')
                return redirect('authorization:approval_detail', pk=pk)
            ApprovalEngine.reject(approval, approver=request.user, reason=reason)
            log_action(
                user=request.user,
                action='update',
                module='authorization',
                model_name='ApprovalRequest',
                object_id=approval.pk,
                description=f'رفض طلب #{approval.pk}: {reason}',
                ip_address=get_client_ip(request),
            )
            messages.warning(request, f'❌ تم رفض الطلب #{approval.pk}')

        elif action == 'cancel':
            if request.user == approval.requested_by or request.user.is_superuser:
                approval.status = 'cancelled'
                approval.processed_at = timezone.now()
                approval.save()
                messages.info(request, f'تم إلغاء الطلب #{approval.pk}')
            else:
                messages.error(request, '⛔ لا تملك صلاحية إلغاء هذا الطلب')

        return redirect('authorization:approval_list')


class MyRequestsView(LoginRequiredMixin, ListView):
    """طلباتي — الطلبات التي أرسلها المستخدم الحالي"""
    model = ApprovalRequest
    template_name = 'authorization/my_requests.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        return ApprovalRequest.objects.filter(
            requested_by=self.request.user
        ).select_related('approved_by', 'branch').order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'طلباتي للاعتماد'
        ctx['pending_count'] = ApprovalRequest.objects.filter(
            requested_by=self.request.user, status='pending'
        ).count()
        ctx['approved_count'] = ApprovalRequest.objects.filter(
            requested_by=self.request.user, status='approved'
        ).count()
        ctx['rejected_count'] = ApprovalRequest.objects.filter(
            requested_by=self.request.user, status='rejected'
        ).count()
        return ctx

