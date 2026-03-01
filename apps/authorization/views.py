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
