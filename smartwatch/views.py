"""
Views لتكامل الساعات الذكية
"""

import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import (
    WatchDevice, WatchNotification, QuickAction,
    WatchActionLog, WatchDashboardWidget, WatchUserSettings
)


@login_required
def dashboard(request):
    """لوحة إدارة الساعات الذكية"""
    devices = WatchDevice.objects.filter(user=request.user)
    
    # الإعدادات
    settings, _ = WatchUserSettings.objects.get_or_create(user=request.user)
    
    # الإجراءات السريعة
    quick_actions = QuickAction.objects.filter(
        models.Q(is_global=True) | models.Q(available_for=request.user),
        is_active=True
    ).distinct()[:8]
    
    # آخر الإجراءات
    recent_actions = WatchActionLog.objects.filter(
        device__user=request.user
    ).order_by('-created_at')[:10]
    
    return render(request, 'smartwatch/dashboard.html', {
        'devices': devices,
        'settings': settings,
        'quick_actions': quick_actions,
        'recent_actions': recent_actions,
    })


@login_required
@require_http_methods(['POST'])
def register_device(request):
    """تسجيل جهاز جديد"""
    try:
        data = json.loads(request.body)
        
        device, created = WatchDevice.objects.update_or_create(
            device_id=data.get('device_id'),
            defaults={
                'user': request.user,
                'name': data.get('name', 'ساعة ذكية'),
                'device_type': data.get('device_type', 'other'),
                'is_active': True,
                'is_connected': True,
                'last_sync': timezone.now(),
            }
        )
        
        return JsonResponse({
            'success': True,
            'device_id': device.id,
            'created': created
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def unregister_device(request, device_id):
    """إلغاء تسجيل جهاز"""
    device = get_object_or_404(WatchDevice, id=device_id, user=request.user)
    device.delete()
    
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(['POST'])
def sync_device(request, device_id):
    """مزامنة الجهاز"""
    try:
        # التحقق من الجهاز
        device = get_object_or_404(WatchDevice, device_id=device_id)
        device.last_sync = timezone.now()
        device.is_connected = True
        device.save()
        
        # الإشعارات غير المرسلة
        notifications = WatchNotification.objects.filter(
            device=device,
            is_sent=False
        ).order_by('-created_at')[:20]
        
        notif_data = [{
            'id': n.id,
            'type': n.notification_type,
            'priority': n.priority,
            'title': n.title,
            'body': n.body,
            'action_url': n.action_url,
            'action_buttons': n.action_buttons,
            'created_at': n.created_at.isoformat()
        } for n in notifications]
        
        # تحديث حالة الإرسال
        notifications.update(is_sent=True, sent_at=timezone.now())
        
        # الإجراءات السريعة
        actions = QuickAction.objects.filter(
            models.Q(is_global=True) | models.Q(available_for=device.user),
            is_active=True
        ).distinct()[:8]
        
        action_data = [{
            'id': a.id,
            'name': a.name,
            'type': a.action_type,
            'icon': a.icon,
            'color': a.color
        } for a in actions]
        
        return JsonResponse({
            'success': True,
            'notifications': notif_data,
            'quick_actions': action_data,
            'server_time': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(['POST'])
def execute_action(request, device_id):
    """تنفيذ إجراء من الساعة"""
    try:
        data = json.loads(request.body)
        device = get_object_or_404(WatchDevice, device_id=device_id)
        
        action_id = data.get('action_id')
        action_type = data.get('action_type')
        
        action = None
        if action_id:
            action = QuickAction.objects.filter(id=action_id).first()
        
        # تنفيذ الإجراء
        result = {'success': True, 'message': 'تم تنفيذ الإجراء'}
        
        if action_type == 'check_in':
            # تسجيل حضور
            result['message'] = f'تم تسجيل الحضور في {timezone.now().strftime("%H:%M")}'
            
        elif action_type == 'check_out':
            # تسجيل انصراف
            result['message'] = f'تم تسجيل الانصراف في {timezone.now().strftime("%H:%M")}'
            
        elif action_type == 'approve':
            # موافقة
            result['message'] = 'تمت الموافقة بنجاح'
            
        elif action_type == 'reject':
            # رفض
            result['message'] = 'تم الرفض'
        
        # تسجيل الإجراء
        WatchActionLog.objects.create(
            device=device,
            action=action,
            action_name=action.name if action else action_type,
            action_type=action_type,
            is_success=True,
            response_data=result,
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        # تسجيل الخطأ
        if 'device' in locals():
            WatchActionLog.objects.create(
                device=device,
                action_name=data.get('action_type', 'unknown'),
                action_type=data.get('action_type', 'unknown'),
                is_success=False,
                error_message=str(e)
            )
        
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def update_settings(request):
    """تحديث الإعدادات"""
    try:
        data = json.loads(request.body)
        
        settings, _ = WatchUserSettings.objects.get_or_create(user=request.user)
        
        settings.notify_on_task = data.get('notify_on_task', True)
        settings.notify_on_message = data.get('notify_on_message', True)
        settings.notify_on_approval = data.get('notify_on_approval', True)
        settings.notify_on_reminder = data.get('notify_on_reminder', True)
        settings.vibration_enabled = data.get('vibration_enabled', True)
        settings.sound_enabled = data.get('sound_enabled', True)
        settings.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_quick_actions(request):
    """الحصول على الإجراءات السريعة"""
    from django.db import models
    
    actions = QuickAction.objects.filter(
        models.Q(is_global=True) | models.Q(available_for=request.user),
        is_active=True
    ).distinct().order_by('order')
    
    return JsonResponse({
        'actions': [{
            'id': a.id,
            'name': a.name,
            'type': a.action_type,
            'icon': a.icon,
            'color': a.color
        } for a in actions]
    })


@login_required
def send_notification(request):
    """إرسال إشعار للساعة"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        devices = WatchDevice.objects.filter(
            user=request.user,
            is_active=True,
            notification_enabled=True
        )
        
        for device in devices:
            WatchNotification.objects.create(
                device=device,
                notification_type=data.get('type', 'alert'),
                priority=data.get('priority', 'normal'),
                title=data.get('title', ''),
                body=data.get('body', ''),
                action_url=data.get('action_url', ''),
                action_buttons=data.get('action_buttons', []),
                data=data.get('data', {})
            )
        
        return JsonResponse({'success': True, 'devices_notified': devices.count()})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# استيراد models للاستخدام في sync_device و get_quick_actions
from django.db import models
