"""
واجهات عرض الصلاحيات والموافقات المتقدمة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone

from accounts.models_permissions import UserBranchPermission, DataAccessRule, SecurityPolicy
from accounts.models_workflow import ApprovalWorkflow, ApprovalStep, ApprovalRequest, ApprovalAction
from accounts.forms_advanced import (
    UserBranchPermissionForm, DataAccessRuleForm, SecurityPolicyForm,
    ApprovalWorkflowForm, ApprovalStepFormSet, ApprovalActionForm,
)
from accounts.services import PermissionService, ApprovalService


# ──────────────────────────────────────
#  لوحة التحكم الرئيسية
# ──────────────────────────────────────
@login_required
def permissions_dashboard(request):
    """لوحة تحكم الصلاحيات والموافقات"""
    context = {
        'page_title': 'لوحة تحكم الصلاحيات والموافقات',
        'total_permissions': UserBranchPermission.objects.count(),
        'total_rules': DataAccessRule.objects.count(),
        'total_workflows': ApprovalWorkflow.objects.filter(is_active=True).count(),
        'pending_approvals': ApprovalRequest.objects.filter(status='pending').count(),
        'my_pending': ApprovalRequest.objects.filter(
            status='pending',
            current_step__approver_user=request.user
        ).count(),
    }
    return render(request, 'accounts/permissions_dashboard.html', context)


# ──────────────────────────────────────
#  صلاحيات الفروع
# ──────────────────────────────────────
@login_required
def permission_list(request):
    """قائمة صلاحيات المستخدمين على الفروع"""
    perms = UserBranchPermission.objects.select_related('user', 'branch').all()
    q = request.GET.get('q')
    if q:
        perms = perms.filter(
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(branch__name__icontains=q)
        )
    paginator = Paginator(perms, 20)
    perms = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/permission_list.html', {
        'permissions': perms,
        'page_title': 'صلاحيات الفروع',
    })


@login_required
def permission_create(request):
    """إضافة صلاحية فرع لمستخدم"""
    if request.method == 'POST':
        form = UserBranchPermissionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الصلاحية بنجاح')
            return redirect('accounts:permission_list')
    else:
        form = UserBranchPermissionForm()
    return render(request, 'accounts/permission_form.html', {
        'form': form,
        'page_title': 'إضافة صلاحية فرع',
    })


@login_required
def permission_edit(request, pk):
    """تعديل صلاحية"""
    perm = get_object_or_404(UserBranchPermission, pk=pk)
    if request.method == 'POST':
        form = UserBranchPermissionForm(request.POST, instance=perm)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الصلاحية بنجاح')
            return redirect('accounts:permission_list')
    else:
        form = UserBranchPermissionForm(instance=perm)
    return render(request, 'accounts/permission_form.html', {
        'form': form,
        'perm': perm,
        'page_title': f'تعديل صلاحية: {perm.user}',
    })


@login_required
def permission_delete(request, pk):
    """حذف صلاحية"""
    perm = get_object_or_404(UserBranchPermission, pk=pk)
    if request.method == 'POST':
        perm.delete()
        messages.success(request, 'تم حذف الصلاحية بنجاح')
        return redirect('accounts:permission_list')
    return render(request, 'accounts/permission_confirm_delete.html', {
        'perm': perm,
        'page_title': 'حذف صلاحية',
    })


# ──────────────────────────────────────
#  قواعد الوصول للبيانات
# ──────────────────────────────────────
@login_required
def access_rule_list(request):
    """قائمة قواعد الوصول"""
    rules = DataAccessRule.objects.all()
    paginator = Paginator(rules, 20)
    rules = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/access_rule_list.html', {
        'rules': rules,
        'page_title': 'قواعد الوصول للبيانات',
    })


@login_required
def access_rule_create(request):
    if request.method == 'POST':
        form = DataAccessRuleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء قاعدة الوصول بنجاح')
            return redirect('accounts:access_rule_list')
    else:
        form = DataAccessRuleForm()
    return render(request, 'accounts/access_rule_form.html', {
        'form': form,
        'page_title': 'إضافة قاعدة وصول',
    })


@login_required
def access_rule_edit(request, pk):
    rule = get_object_or_404(DataAccessRule, pk=pk)
    if request.method == 'POST':
        form = DataAccessRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث قاعدة الوصول بنجاح')
            return redirect('accounts:access_rule_list')
    else:
        form = DataAccessRuleForm(instance=rule)
    return render(request, 'accounts/access_rule_form.html', {
        'form': form,
        'rule': rule,
        'page_title': f'تعديل قاعدة: {rule.role_name}',
    })


@login_required
def access_rule_delete(request, pk):
    rule = get_object_or_404(DataAccessRule, pk=pk)
    if request.method == 'POST':
        rule.delete()
        messages.success(request, 'تم حذف قاعدة الوصول بنجاح')
        return redirect('accounts:access_rule_list')
    return render(request, 'accounts/confirm_delete.html', {
        'object': rule,
        'object_name': f'قاعدة الوصول: {rule.role_name}',
        'cancel_url': 'accounts:access_rule_list',
        'page_title': 'حذف قاعدة وصول',
    })


# ──────────────────────────────────────
#  سياسة الأمان
# ──────────────────────────────────────
@login_required
def security_policy(request):
    """عرض وتعديل سياسة الأمان"""
    policy, created = SecurityPolicy.objects.get_or_create(pk=1)
    if request.method == 'POST':
        form = SecurityPolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث سياسة الأمان بنجاح')
            return redirect('accounts:security_policy')
    else:
        form = SecurityPolicyForm(instance=policy)
    return render(request, 'accounts/security_policy.html', {
        'form': form,
        'policy': policy,
        'page_title': 'سياسة الأمان',
    })


# ──────────────────────────────────────
#  سير عمل الموافقات
# ──────────────────────────────────────
@login_required
def workflow_list(request):
    """قائمة سير عمل الموافقات"""
    workflows = ApprovalWorkflow.objects.annotate(
        steps_count=Count('steps')
    ).all()
    paginator = Paginator(workflows, 20)
    workflows = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/workflow_list.html', {
        'workflows': workflows,
        'page_title': 'سير عمل الموافقات',
    })


@login_required
def workflow_create(request):
    if request.method == 'POST':
        form = ApprovalWorkflowForm(request.POST)
        formset = ApprovalStepFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            workflow = form.save()
            formset.instance = workflow
            formset.save()
            messages.success(request, f'تم إنشاء سير العمل "{workflow.name}" بنجاح')
            return redirect('accounts:workflow_detail', pk=workflow.pk)
    else:
        form = ApprovalWorkflowForm()
        formset = ApprovalStepFormSet()
    return render(request, 'accounts/workflow_form.html', {
        'form': form,
        'formset': formset,
        'page_title': 'إنشاء سير عمل جديد',
    })


@login_required
def workflow_detail(request, pk):
    workflow = get_object_or_404(ApprovalWorkflow, pk=pk)
    steps = workflow.steps.all().order_by('step_order')
    recent_requests = ApprovalRequest.objects.filter(
        workflow=workflow
    ).order_by('-created_at')[:10]
    return render(request, 'accounts/workflow_detail.html', {
        'workflow': workflow,
        'steps': steps,
        'recent_requests': recent_requests,
        'page_title': f'سير العمل: {workflow.name}',
    })


@login_required
def workflow_edit(request, pk):
    workflow = get_object_or_404(ApprovalWorkflow, pk=pk)
    if request.method == 'POST':
        form = ApprovalWorkflowForm(request.POST, instance=workflow)
        formset = ApprovalStepFormSet(request.POST, instance=workflow)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f'تم تحديث سير العمل "{workflow.name}" بنجاح')
            return redirect('accounts:workflow_detail', pk=workflow.pk)
    else:
        form = ApprovalWorkflowForm(instance=workflow)
        formset = ApprovalStepFormSet(instance=workflow)
    return render(request, 'accounts/workflow_form.html', {
        'form': form,
        'formset': formset,
        'workflow': workflow,
        'page_title': f'تعديل: {workflow.name}',
    })


# ──────────────────────────────────────
#  طلبات الموافقة
# ──────────────────────────────────────
@login_required
def approval_list(request):
    """قائمة طلبات الموافقة"""
    approvals = ApprovalRequest.objects.select_related(
        'workflow', 'requested_by', 'current_step'
    ).all()
    status_filter = request.GET.get('status')
    if status_filter:
        approvals = approvals.filter(status=status_filter)
    paginator = Paginator(approvals.order_by('-created_at'), 20)
    approvals = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/approval_list.html', {
        'approvals': approvals,
        'page_title': 'طلبات الموافقة',
        'current_status': status_filter,
    })


@login_required
def my_approvals(request):
    """الموافقات المعلقة للمستخدم الحالي"""
    pending = ApprovalService.get_pending_approvals(request.user)
    return render(request, 'accounts/my_approvals.html', {
        'approvals': pending,
        'page_title': 'موافقاتي المعلقة',
    })


@login_required
def approval_detail(request, pk):
    """تفاصيل طلب الموافقة"""
    approval = get_object_or_404(
        ApprovalRequest.objects.select_related(
            'workflow', 'requested_by', 'current_step'
        ), pk=pk
    )
    actions = approval.actions.select_related('acted_by', 'step').all()
    action_form = ApprovalActionForm()

    return render(request, 'accounts/approval_detail.html', {
        'approval': approval,
        'actions': actions,
        'action_form': action_form,
        'page_title': f'طلب موافقة #{approval.pk}',
    })


@login_required
def approval_action(request, pk):
    """اتخاذ إجراء على طلب موافقة"""
    approval = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == 'POST':
        form = ApprovalActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data['notes']
            try:
                if action == 'approve':
                    ApprovalService.approve(approval, request.user, notes)
                    messages.success(request, 'تمت الموافقة بنجاح')
                elif action == 'reject':
                    ApprovalService.reject(approval, request.user, notes)
                    messages.warning(request, 'تم رفض الطلب')
                else:
                    messages.info(request, 'تم إرجاع الطلب')
            except Exception as e:
                messages.error(request, f'خطأ: {e}')
        return redirect('accounts:approval_detail', pk=pk)
    return redirect('accounts:approval_detail', pk=pk)
