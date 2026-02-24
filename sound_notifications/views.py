"""
Views للإشعارات الصوتية
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .models import SoundTheme, NotificationSound, UserSoundPreference, SoundLog


@login_required
def sound_settings(request):
    """إعدادات الأصوات"""
    preferences, created = UserSoundPreference.objects.get_or_create(user=request.user)
    themes = SoundTheme.objects.filter(is_active=True)
    
    if request.method == 'POST':
        preferences.is_enabled = request.POST.get('is_enabled') == 'on'
        preferences.master_volume = int(request.POST.get('master_volume', 80))
        preferences.do_not_disturb = request.POST.get('do_not_disturb') == 'on'
        
        theme_id = request.POST.get('theme')
        if theme_id:
            preferences.theme = SoundTheme.objects.filter(id=theme_id).first()
        
        # تفضيلات الأنواع
        preferences.enable_new_order = request.POST.get('enable_new_order') == 'on'
        preferences.enable_payment = request.POST.get('enable_payment') == 'on'
        preferences.enable_low_stock = request.POST.get('enable_low_stock') == 'on'
        preferences.enable_approval = request.POST.get('enable_approval') == 'on'
        preferences.enable_tasks = request.POST.get('enable_tasks') == 'on'
        preferences.enable_messages = request.POST.get('enable_messages') == 'on'
        preferences.enable_reminders = request.POST.get('enable_reminders') == 'on'
        preferences.enable_chat = request.POST.get('enable_chat') == 'on'
        preferences.enable_calls = request.POST.get('enable_calls') == 'on'
        
        preferences.save()
        messages.success(request, 'تم حفظ إعدادات الأصوات بنجاح')
    
    return render(request, 'sound_notifications/settings.html', {
        'preferences': preferences,
        'themes': themes,
    })


@login_required
@require_http_methods(['POST'])
def toggle_sounds(request):
    """تفعيل/إيقاف الأصوات"""
    preferences, _ = UserSoundPreference.objects.get_or_create(user=request.user)
    preferences.is_enabled = not preferences.is_enabled
    preferences.save()
    
    return JsonResponse({
        'success': True,
        'is_enabled': preferences.is_enabled
    })


@login_required
@require_http_methods(['POST'])
def toggle_dnd(request):
    """تفعيل/إيقاف عدم الإزعاج"""
    preferences, _ = UserSoundPreference.objects.get_or_create(user=request.user)
    preferences.do_not_disturb = not preferences.do_not_disturb
    preferences.save()
    
    return JsonResponse({
        'success': True,
        'do_not_disturb': preferences.do_not_disturb
    })


@login_required
def get_sound_url(request, sound_type):
    """الحصول على رابط الصوت"""
    preferences, _ = UserSoundPreference.objects.get_or_create(user=request.user)
    
    if not preferences.is_sound_enabled(sound_type):
        return JsonResponse({'url': None, 'enabled': False})
    
    theme = preferences.theme or SoundTheme.objects.filter(is_default=True).first()
    
    if theme:
        sound = NotificationSound.objects.filter(
            theme=theme,
            sound_type=sound_type,
            is_active=True
        ).first()
        
        if sound:
            # سجل التشغيل
            SoundLog.objects.create(
                user=request.user,
                sound_type=sound_type,
                was_muted=False
            )
            
            return JsonResponse({
                'url': sound.sound_file.url,
                'volume': min(sound.volume, preferences.master_volume) / 100,
                'enabled': True
            })
    
    return JsonResponse({'url': None, 'enabled': True})


@login_required
def test_sound(request, sound_type):
    """اختبار صوت معين"""
    preferences, _ = UserSoundPreference.objects.get_or_create(user=request.user)
    theme = preferences.theme or SoundTheme.objects.filter(is_default=True).first()
    
    if theme:
        sound = NotificationSound.objects.filter(
            theme=theme,
            sound_type=sound_type,
            is_active=True
        ).first()
        
        if sound:
            return JsonResponse({
                'success': True,
                'url': sound.sound_file.url,
                'volume': preferences.master_volume / 100
            })
    
    return JsonResponse({
        'success': False,
        'message': 'لم يتم العثور على صوت لهذا النوع'
    })
