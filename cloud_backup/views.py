"""
Views للنسخ الاحتياطي السحابي
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone

from .models import CloudProvider, BackupSchedule, Backup, RestorePoint, BackupSettings
from .services import BackupService, RestoreService


def is_admin(user):
    return user.is_superuser or user.is_staff


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """لوحة النسخ الاحتياطي"""
    providers = CloudProvider.objects.filter(is_active=True)
    schedules = BackupSchedule.objects.filter(is_active=True)
    recent_backups = Backup.objects.order_by('-created_at')[:10]
    
    # إحصائيات
    total_backups = Backup.objects.count()
    successful_backups = Backup.objects.filter(status='completed').count()
    total_size = sum(b.file_size for b in Backup.objects.filter(status='completed'))
    
    stats = {
        'total': total_backups,
        'successful': successful_backups,
        'total_size': format_size(total_size),
        'providers': providers.count(),
    }
    
    return render(request, 'cloud_backup/dashboard.html', {
        'providers': providers,
        'schedules': schedules,
        'recent_backups': recent_backups,
        'stats': stats,
    })


@login_required
@user_passes_test(is_admin)
def providers_list(request):
    """قائمة المزودين"""
    providers = CloudProvider.objects.all()
    
    return render(request, 'cloud_backup/providers.html', {
        'providers': providers,
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(['POST'])
def add_provider(request):
    """إضافة مزود"""
    try:
        data = json.loads(request.body)
        
        provider = CloudProvider.objects.create(
            name=data.get('name'),
            provider_type=data.get('provider_type'),
            credentials=data.get('credentials', {}),
            folder_path=data.get('folder_path', '/backups'),
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'provider_id': provider.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_admin)
def backup_now(request):
    """نسخ احتياطي فوري"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            provider_id = data.get('provider_id')
            provider = CloudProvider.objects.filter(id=provider_id).first()
            
            if not provider:
                provider = CloudProvider.objects.filter(is_default=True).first()
            
            if not provider:
                return JsonResponse({
                    'success': False,
                    'error': 'لا يوجد مزود تخزين'
                })
            
            # إنشاء نسخة احتياطية
            backup = Backup.objects.create(
                provider=provider,
                name=f"نسخة يدوية - {timezone.now().strftime('%Y/%m/%d %H:%M')}",
                backup_type='full',
                includes_database=data.get('include_database', True),
                includes_media=data.get('include_media', True),
                created_by=request.user
            )
            
            # تنفيذ النسخ (يمكن جعله في خلفية)
            service = BackupService(backup)
            success = service.execute()
            
            return JsonResponse({
                'success': success,
                'backup_id': str(backup.uuid)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    providers = CloudProvider.objects.filter(is_active=True)
    
    return render(request, 'cloud_backup/backup_now.html', {
        'providers': providers,
    })


@login_required
@user_passes_test(is_admin)
def backup_detail(request, uuid):
    """تفاصيل النسخة الاحتياطية"""
    backup = get_object_or_404(Backup, uuid=uuid)
    
    return render(request, 'cloud_backup/backup_detail.html', {
        'backup': backup,
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(['POST'])
def restore_backup(request, uuid):
    """استعادة نسخة احتياطية"""
    backup = get_object_or_404(Backup, uuid=uuid, status='completed')
    
    try:
        data = json.loads(request.body)
        
        # تأكيد مزدوج - يجب كتابة RESTORE للتأكيد
        confirmation = data.get('confirmation_text', '')
        if confirmation != 'RESTORE':
            return JsonResponse({
                'success': False,
                'error': 'يجب كتابة كلمة RESTORE للتأكيد على عملية الاستعادة. هذه العملية ستستبدل جميع البيانات الحالية.'
            })
        
        # تسجيل العملية
        import logging
        audit_logger = logging.getLogger('cloud_backup')
        audit_logger.warning(
            f"[RESTORE] المستخدم {request.user.username} (ID: {request.user.id}) "
            f"بدأ استعادة النسخة الاحتياطية {uuid}"
        )
        
        restore_point = RestorePoint.objects.create(
            backup=backup,
            restore_database=data.get('restore_database', True),
            restore_media=data.get('restore_media', True),
            restore_to_path=data.get('restore_to_path', ''),
            initiated_by=request.user
        )
        
        # تنفيذ الاستعادة
        service = RestoreService(restore_point)
        success = service.execute()
        
        return JsonResponse({
            'success': success,
            'restore_id': restore_point.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_admin)
@require_http_methods(['DELETE'])
def delete_backup(request, uuid):
    """حذف نسخة احتياطية"""
    backup = get_object_or_404(Backup, uuid=uuid)
    
    # حذف الملف من السحابة
    # TODO: تنفيذ الحذف من المزود
    
    backup.delete()
    
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_admin)
def schedules_list(request):
    """قائمة الجداول"""
    schedules = BackupSchedule.objects.all()
    
    return render(request, 'cloud_backup/schedules.html', {
        'schedules': schedules,
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(['POST'])
def create_schedule(request):
    """إنشاء جدول"""
    try:
        data = json.loads(request.body)
        
        schedule = BackupSchedule.objects.create(
            name=data.get('name'),
            description=data.get('description', ''),
            provider_id=data.get('provider_id'),
            backup_type=data.get('backup_type', 'full'),
            frequency=data.get('frequency', 'daily'),
            time_of_day=data.get('time_of_day', '02:00'),
            include_database=data.get('include_database', True),
            include_media=data.get('include_media', True),
            retention_days=data.get('retention_days', 30),
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'schedule_id': schedule.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_admin)
@require_http_methods(['POST'])
def toggle_schedule(request, schedule_id):
    """تفعيل/تعطيل جدول"""
    schedule = get_object_or_404(BackupSchedule, id=schedule_id)
    schedule.is_active = not schedule.is_active
    schedule.save()
    
    return JsonResponse({
        'success': True,
        'is_active': schedule.is_active
    })


def format_size(size_bytes):
    """تنسيق الحجم"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"
