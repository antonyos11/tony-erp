"""
واجهات عرض الإنتاج المتقدمة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from production.models_advanced import ProductionLine, ProductionSchedule, CostVariance
from production.forms_advanced import ProductionLineForm, ProductionScheduleForm


# ──────────────────────────────────────
#  خطوط الإنتاج
# ──────────────────────────────────────
@login_required
def production_line_list(request):
    lines = ProductionLine.objects.all()
    q = request.GET.get('q')
    if q:
        lines = lines.filter(Q(name__icontains=q) | Q(code__icontains=q))
    paginator = Paginator(lines, 20)
    lines = paginator.get_page(request.GET.get('page'))
    return render(request, 'production/line_list.html', {
        'lines': lines,
        'page_title': 'خطوط الإنتاج',
    })


@login_required
def production_line_create(request):
    if request.method == 'POST':
        form = ProductionLineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء خط الإنتاج بنجاح')
            return redirect('production:production_line_list')
    else:
        form = ProductionLineForm()
    return render(request, 'production/line_form.html', {
        'form': form,
        'page_title': 'إضافة خط إنتاج',
    })


@login_required
def production_line_edit(request, pk):
    line = get_object_or_404(ProductionLine, pk=pk)
    if request.method == 'POST':
        form = ProductionLineForm(request.POST, instance=line)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث خط الإنتاج "{line.name}" بنجاح')
            return redirect('production:production_line_list')
    else:
        form = ProductionLineForm(instance=line)
    return render(request, 'production/line_form.html', {
        'form': form,
        'line': line,
        'page_title': f'تعديل: {line.name}',
    })


@login_required
def production_line_delete(request, pk):
    line = get_object_or_404(ProductionLine, pk=pk)
    if request.method == 'POST':
        line.delete()
        messages.success(request, 'تم حذف خط الإنتاج بنجاح')
        return redirect('production:production_line_list')
    return render(request, 'production/confirm_delete.html', {
        'object': line,
        'object_name': f'خط الإنتاج: {line.name}',
        'cancel_url': 'production:production_line_list',
        'page_title': 'حذف خط إنتاج',
    })


# ──────────────────────────────────────
#  جدولة الإنتاج
# ──────────────────────────────────────
@login_required
def schedule_list(request):
    schedules = ProductionSchedule.objects.select_related(
        'production_order', 'production_line'
    ).all()
    status = request.GET.get('status')
    if status:
        schedules = schedules.filter(status=status)
    paginator = Paginator(schedules.order_by('-planned_start'), 20)
    schedules = paginator.get_page(request.GET.get('page'))
    return render(request, 'production/schedule_list.html', {
        'schedules': schedules,
        'page_title': 'جدولة الإنتاج',
    })


@login_required
def schedule_create(request):
    if request.method == 'POST':
        form = ProductionScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء الجدولة بنجاح')
            return redirect('production:schedule_list')
    else:
        form = ProductionScheduleForm()
    return render(request, 'production/schedule_form.html', {
        'form': form,
        'page_title': 'إنشاء جدولة إنتاج',
    })


@login_required
def schedule_detail(request, pk):
    schedule = get_object_or_404(
        ProductionSchedule.objects.select_related('production_order', 'production_line'),
        pk=pk
    )
    return render(request, 'production/schedule_detail.html', {
        'schedule': schedule,
        'page_title': f'جدولة: {schedule.production_order}',
    })


@login_required
def schedule_edit(request, pk):
    schedule = get_object_or_404(ProductionSchedule, pk=pk)
    if request.method == 'POST':
        form = ProductionScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الجدولة بنجاح')
            return redirect('production:schedule_detail', pk=schedule.pk)
    else:
        form = ProductionScheduleForm(instance=schedule)
    return render(request, 'production/schedule_form.html', {
        'form': form,
        'schedule': schedule,
        'page_title': 'تعديل الجدولة',
    })


# ──────────────────────────────────────
#  تحليل انحرافات التكلفة
# ──────────────────────────────────────
@login_required
def cost_variance_list(request):
    variances = CostVariance.objects.select_related('production_order').all()
    paginator = Paginator(variances.order_by('-analysis_date'), 20)
    variances = paginator.get_page(request.GET.get('page'))
    return render(request, 'production/cost_variance_list.html', {
        'variances': variances,
        'page_title': 'انحرافات التكلفة',
    })


@login_required
def cost_variance_detail(request, pk):
    variance = get_object_or_404(
        CostVariance.objects.select_related('production_order'),
        pk=pk
    )
    return render(request, 'production/cost_variance_detail.html', {
        'variance': variance,
        'page_title': f'انحراف التكلفة: {variance.production_order}',
    })
