"""
عروض نظام التصدير والنسخ الاحتياطي
"""
import csv
import json
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .models import BackupRecord, DataExport


@login_required
def export_list(request):
    """قائمة عمليات التصدير"""
    exports = DataExport.objects.filter(requested_by=request.user).order_by('-created_at')[:50]
    backups = BackupRecord.objects.order_by('-created_at')[:20]
    return render(request, 'exports/export_list.html', {
        'title': 'التصدير والتقارير',
        'exports': exports,
        'backups': backups,
    })


@login_required
def export_history(request):
    """سجل عمليات التصدير"""
    exports = DataExport.objects.filter(requested_by=request.user).order_by('-created_at')
    return render(request, 'exports/export_history.html', {
        'title': 'سجل التصدير',
        'exports': exports,
    })


@login_required
@require_POST
def export_create(request):
    """بدء عملية تصدير جديدة"""
    export_type = request.POST.get('export_type', 'all')
    export_format = request.POST.get('format', 'csv')
    name = request.POST.get('name', f'تصدير {export_type} - {timezone.now().strftime("%Y-%m-%d %H:%M")}')

    export_obj = DataExport.objects.create(
        export_name=name,
        export_type=export_type,
        export_format=export_format,
        parameters=json.loads(request.POST.get('parameters', '{}')),
        requested_by=request.user,
    )

    # تشغيل التصدير في الخلفية عبر Celery
    try:
        from .tasks import run_data_export
        run_data_export.delay(export_obj.id)  # type: ignore[attr-defined]
    except Exception:
        # لو Celery مش شغال، نصدّر مباشرة للـ CSV
        if export_format == 'csv':
            return _quick_csv_export(request, export_obj)
        export_obj.status = 'processing'
        export_obj.save(update_fields=['status'])

    return JsonResponse({
        'status': 'success',
        'message': f'تم بدء عملية التصدير: {name}',
        'export_id': export_obj.id,
    })


@login_required
def export_status(request, export_id):
    """حالة عملية تصدير"""
    export_obj = get_object_or_404(DataExport, id=export_id, requested_by=request.user)
    data = {
        'id': export_obj.id,
        'name': export_obj.export_name,
        'status': export_obj.status,
        'format': export_obj.export_format,
        'progress': export_obj.progress,
        'created_at': export_obj.created_at.isoformat(),
        'error_message': export_obj.error_message,
    }
    if export_obj.file_path:
        data['has_file'] = True
    if export_obj.completed_at:
        data['completed_at'] = export_obj.completed_at.isoformat()
    return JsonResponse(data)


@login_required
def export_download(request, export_id):
    """تحميل ملف التصدير"""
    export_obj = get_object_or_404(DataExport, id=export_id, requested_by=request.user, status='completed')
    if not export_obj.file_path:
        raise Http404('الملف غير متاح')

    import os
    if not os.path.exists(export_obj.file_path):
        raise Http404('الملف غير موجود')

    with open(export_obj.file_path, 'rb') as f:
        content = f.read()

    content_types = {
        'csv': 'text/csv; charset=utf-8-sig',
        'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pdf': 'application/pdf',
        'json': 'application/json; charset=utf-8',
    }
    ct = content_types.get(export_obj.export_format, 'application/octet-stream')
    ext = 'xlsx' if export_obj.export_format == 'excel' else export_obj.export_format

    response = HttpResponse(content, content_type=ct)
    response['Content-Disposition'] = f'attachment; filename="{export_obj.export_name}.{ext}"'

    export_obj.download_count += 1
    export_obj.save(update_fields=['download_count'])
    return response


# --- نسخ احتياطي ---

@login_required
def backup_list(request):
    """قائمة النسخ الاحتياطية"""
    backups = BackupRecord.objects.order_by('-created_at')
    return render(request, 'exports/backup_list.html', {
        'title': 'النسخ الاحتياطية',
        'backups': backups,
    })


# --- مساعدات ---

def _quick_csv_export(request, export_obj):
    """تصدير CSV سريع مباشر"""
    export_obj.status = 'processing'
    export_obj.save(update_fields=['status'])

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{export_obj.export_name}.csv"'
    response.write('\ufeff')  # BOM لدعم العربية في Excel

    writer = csv.writer(response)
    writer.writerow(['#', 'نوع البيانات', 'تاريخ التصدير', 'الحالة'])
    writer.writerow([1, export_obj.export_type, export_obj.created_at.strftime('%Y-%m-%d %H:%M'), 'مكتمل'])

    export_obj.mark_completed(file_path='', file_size=0)
    return response
