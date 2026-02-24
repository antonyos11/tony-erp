"""
واجهات لوحة خط أنابيب الإنتاج العالمي
Global Production Pipeline Dashboard Views
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone

from production.models import ProductionOrder, ProductionWorkCenter
from production.models_pipeline import (
    PipelineBoard, PipelineStageEntry, PipelinePrintJob,
    PipelineStageStatus,
)
from production.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)


def _user_can_act_on_work_center(user, work_center):
    """
    RBAC: التحقق من صلاحية المستخدم للتحكم في مركز عمل معين.
    المشرف المعيّن على مركز العمل أو المدراء فقط.
    """
    # Admins/superusers can do anything
    if user.is_superuser:
        return True

    # Check if user is supervisor of this work center
    if hasattr(work_center, 'supervisor') and work_center.supervisor:
        try:
            from hr.models import Employee
            employee = Employee.objects.filter(user=user).first()
            if employee and work_center.supervisor_id == employee.id:
                return True
        except Exception:
            pass

    # Check group-based access
    allowed_groups = {'Production Managers', 'Supervisors', 'مدراء الإنتاج', 'المشرفين'}
    user_groups = set(user.groups.values_list('name', flat=True))
    if user_groups & allowed_groups:
        return True

    return False


@login_required
def pipeline_dashboard(request):
    """
    لوحة خط أنابيب الإنتاج العالمي - العرض الرئيسي
    """
    dashboard_data = PipelineService.get_pipeline_dashboard_data()

    # Prepare RBAC info: which work centers can this user act on
    user_allowed_wc_ids = []
    for col in dashboard_data['columns']:
        try:
            wc = ProductionWorkCenter.objects.get(id=col['id'])
            if _user_can_act_on_work_center(request.user, wc):
                user_allowed_wc_ids.append(col['id'])
        except ProductionWorkCenter.DoesNotExist:
            pass

    context = {
        'dashboard_data_json': json.dumps(dashboard_data, ensure_ascii=False),
        'columns': dashboard_data['columns'],
        'boards': dashboard_data['boards'],
        'user_allowed_wc_ids': json.dumps(user_allowed_wc_ids),
        'user_id': request.user.id,
        'page_title': 'خط أنابيب الإنتاج العالمي',
        'failure_categories': [
            ('machine_breakdown', 'عطل ماكينة'),
            ('material_shortage', 'نقص مواد'),
            ('quality_issue', 'مشكلة جودة'),
            ('power_outage', 'انقطاع كهرباء'),
            ('labor_shortage', 'نقص عمالة'),
            ('other', 'أخرى'),
        ],
    }

    return render(request, 'production/pipeline/dashboard.html', context)


@login_required
@require_POST
def pipeline_create_board(request, order_id):
    """إنشاء لوحة أنابيب لأمر إنتاج"""
    order = get_object_or_404(ProductionOrder, id=order_id)
    success, msg, board = PipelineService.create_board_for_order(order)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': msg,
            'board_id': board.id if board else None,
        })

    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)

    return redirect('production:pipeline_dashboard')


@login_required
@require_POST
def pipeline_start_stage(request, stage_id):
    """بدء مرحلة في خط الأنابيب"""
    stage = get_object_or_404(
        PipelineStageEntry.objects.select_related('work_center', 'board__production_order'),
        id=stage_id
    )

    if not _user_can_act_on_work_center(request.user, stage.work_center):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'ليس لديك صلاحية للتحكم في هذا المركز',
            }, status=403)
        messages.error(request, 'ليس لديك صلاحية للتحكم في هذا المركز')
        return redirect('production:pipeline_dashboard')

    success, msg = PipelineService.start_stage(stage, request.user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': msg})

    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect('production:pipeline_dashboard')


@login_required
@require_POST
def pipeline_complete_stage(request, stage_id):
    """إكمال مرحلة في خط الأنابيب"""
    stage = get_object_or_404(
        PipelineStageEntry.objects.select_related('work_center', 'board__production_order'),
        id=stage_id
    )

    if not _user_can_act_on_work_center(request.user, stage.work_center):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'ليس لديك صلاحية للتحكم في هذا المركز',
            }, status=403)
        messages.error(request, 'ليس لديك صلاحية للتحكم في هذا المركز')
        return redirect('production:pipeline_dashboard')

    success, msg, details = PipelineService.complete_stage(stage, request.user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': msg,
            'details': details,
        })

    if success:
        messages.success(request, msg)
        if details.get('is_final'):
            messages.info(request, 'تم إطلاق طباعة الباركود تلقائياً')
    else:
        messages.error(request, msg)
    return redirect('production:pipeline_dashboard')


@login_required
@require_POST
def pipeline_fail_stage(request, stage_id):
    """تسجيل عطل في مرحلة"""
    stage = get_object_or_404(
        PipelineStageEntry.objects.select_related('work_center', 'board__production_order'),
        id=stage_id
    )

    if not _user_can_act_on_work_center(request.user, stage.work_center):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'ليس لديك صلاحية',
            }, status=403)
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('production:pipeline_dashboard')

    reason = request.POST.get('reason', '')
    category = request.POST.get('category', 'other')

    success, msg = PipelineService.fail_stage(stage, request.user, reason, category)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': msg})

    if success:
        messages.warning(request, msg)
    else:
        messages.error(request, msg)
    return redirect('production:pipeline_dashboard')


@login_required
@require_POST
def pipeline_reprint(request, stage_id):
    """إعادة طباعة الباركود"""
    stage = get_object_or_404(
        PipelineStageEntry.objects.select_related('work_center', 'board__production_order'),
        id=stage_id
    )

    success, msg, job = PipelineService.reprint_barcodes(stage, request.user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': msg,
            'print_job_id': str(job.id) if job else None,
        })

    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect('production:pipeline_dashboard')


@login_required
@require_GET
def pipeline_api_data(request):
    """API endpoint for fetching pipeline data (AJAX fallback)"""
    data = PipelineService.get_pipeline_dashboard_data()
    return JsonResponse(data)
