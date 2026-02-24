"""
واجهات عرض CRM المتقدمة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from crm.models_advanced import FollowUpRule, FollowUpLog, LeadScore, SupportSLA
from crm.forms_advanced import FollowUpRuleForm, SupportSLAForm


# ──────────────────────────────────────
#  قواعد المتابعة
# ──────────────────────────────────────
@login_required
def followup_rule_list(request):
    rules = FollowUpRule.objects.all()
    paginator = Paginator(rules, 20)
    rules = paginator.get_page(request.GET.get('page'))
    return render(request, 'crm/followup_rule_list.html', {
        'rules': rules,
        'page_title': 'قواعد المتابعة التلقائية',
    })


@login_required
def followup_rule_create(request):
    if request.method == 'POST':
        form = FollowUpRuleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء قاعدة المتابعة بنجاح')
            return redirect('crm:followup_rule_list')
    else:
        form = FollowUpRuleForm()
    return render(request, 'crm/followup_rule_form.html', {
        'form': form,
        'page_title': 'إضافة قاعدة متابعة',
    })


@login_required
def followup_rule_edit(request, pk):
    rule = get_object_or_404(FollowUpRule, pk=pk)
    if request.method == 'POST':
        form = FollowUpRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث قاعدة المتابعة بنجاح')
            return redirect('crm:followup_rule_list')
    else:
        form = FollowUpRuleForm(instance=rule)
    return render(request, 'crm/followup_rule_form.html', {
        'form': form,
        'rule': rule,
        'page_title': f'تعديل: {rule.name}',
    })


@login_required
def followup_rule_delete(request, pk):
    rule = get_object_or_404(FollowUpRule, pk=pk)
    if request.method == 'POST':
        rule.delete()
        messages.success(request, 'تم حذف قاعدة المتابعة بنجاح')
        return redirect('crm:followup_rule_list')
    return render(request, 'crm/confirm_delete.html', {
        'object': rule,
        'object_name': f'قاعدة المتابعة: {rule.name}',
        'cancel_url': 'crm:followup_rule_list',
        'page_title': 'حذف قاعدة متابعة',
    })


# ──────────────────────────────────────
#  سجل المتابعات
# ──────────────────────────────────────
@login_required
def followup_log_list(request):
    logs = FollowUpLog.objects.select_related('rule', 'customer').all()
    status = request.GET.get('status')
    if status:
        logs = logs.filter(status=status)
    paginator = Paginator(logs.order_by('-executed_at'), 20)
    logs = paginator.get_page(request.GET.get('page'))
    return render(request, 'crm/followup_log_list.html', {
        'logs': logs,
        'page_title': 'سجل المتابعات',
    })


# ──────────────────────────────────────
#  تقييم العملاء (Lead Scoring)
# ──────────────────────────────────────
@login_required
def lead_score_list(request):
    scores = LeadScore.objects.select_related('customer').all()
    grade = request.GET.get('grade')
    if grade:
        scores = scores.filter(grade=grade)
    q = request.GET.get('q')
    if q:
        scores = scores.filter(customer__name__icontains=q)
    paginator = Paginator(scores.order_by('-last_calculated'), 20)
    scores = paginator.get_page(request.GET.get('page'))
    return render(request, 'crm/lead_score_list.html', {
        'scores': scores,
        'page_title': 'تقييم العملاء',
    })


@login_required
def lead_score_detail(request, pk):
    score = get_object_or_404(LeadScore.objects.select_related('customer'), pk=pk)
    return render(request, 'crm/lead_score_detail.html', {
        'score': score,
        'page_title': f'تقييم: {score.customer}',
    })


# ──────────────────────────────────────
#  اتفاقيات مستوى الخدمة SLA
# ──────────────────────────────────────
@login_required
def sla_list(request):
    slas = SupportSLA.objects.all()
    paginator = Paginator(slas, 20)
    slas = slas  # عدد قليل لا يحتاج باجينيشن
    return render(request, 'crm/sla_list.html', {
        'slas': slas,
        'page_title': 'اتفاقيات مستوى الخدمة',
    })


@login_required
def sla_create(request):
    if request.method == 'POST':
        form = SupportSLAForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء اتفاقية SLA بنجاح')
            return redirect('crm:sla_list')
    else:
        form = SupportSLAForm()
    return render(request, 'crm/sla_form.html', {
        'form': form,
        'page_title': 'إضافة اتفاقية SLA',
    })


@login_required
def sla_edit(request, pk):
    sla = get_object_or_404(SupportSLA, pk=pk)
    if request.method == 'POST':
        form = SupportSLAForm(request.POST, instance=sla)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الاتفاقية بنجاح')
            return redirect('crm:sla_list')
    else:
        form = SupportSLAForm(instance=sla)
    return render(request, 'crm/sla_form.html', {
        'form': form,
        'sla': sla,
        'page_title': f'تعديل: {sla.name}',
    })
