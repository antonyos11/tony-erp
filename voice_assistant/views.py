"""
Views للمساعد الصوتي
"""

import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone

from .models import VoiceCommand, UserVoicePreference, VoiceShortcut
from .services import VoiceCommandProcessor


@login_required
def voice_dashboard(request):
    """لوحة المساعد الصوتي"""
    preference, _ = UserVoicePreference.objects.get_or_create(user=request.user)
    recent_commands = VoiceCommand.objects.filter(user=request.user)[:10]
    shortcuts = VoiceShortcut.objects.filter(user=request.user, is_active=True)
    
    return render(request, 'voice_assistant/dashboard.html', {
        'preference': preference,
        'recent_commands': recent_commands,
        'shortcuts': shortcuts,
    })


@login_required
def voice_settings(request):
    """إعدادات المساعد الصوتي"""
    preference, _ = UserVoicePreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        preference.is_enabled = request.POST.get('is_enabled') == 'on'
        preference.voice_type = request.POST.get('voice_type', 'female_ar')
        preference.speech_rate = float(request.POST.get('speech_rate', 1.0))
        preference.pitch = float(request.POST.get('pitch', 1.0))
        preference.auto_listen = request.POST.get('auto_listen') == 'on'
        preference.wake_word = request.POST.get('wake_word', 'يا نظام')
        preference.language = request.POST.get('language', 'ar-SA')
        preference.read_responses = request.POST.get('read_responses') == 'on'
        preference.confirm_actions = request.POST.get('confirm_actions') == 'on'
        preference.save()
        
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
    
    return render(request, 'voice_assistant/settings.html', {
        'preference': preference,
    })


@login_required
@require_http_methods(['POST'])
def process_command(request):
    """معالجة الأمر الصوتي"""
    try:
        data = json.loads(request.body)
        command_text = data.get('text', '')
        audio_duration = data.get('duration', 0)
        
        if not command_text:
            return JsonResponse({
                'success': False,
                'response': 'لم يتم استلام نص الأمر'
            })
        
        # معالجة الأمر
        processor = VoiceCommandProcessor(request.user)
        result = processor.process(command_text)
        
        # حفظ الأمر
        VoiceCommand.objects.create(
            user=request.user,
            command_text=command_text,
            command_type=result.get('action', 'query'),
            detected_intent=result.get('action', ''),
            confidence=0.9 if result['success'] else 0.3,
            status='success' if result['success'] else 'failed',
            response_text=result.get('response', ''),
            action_taken=result.get('action', ''),
            redirect_url=result.get('url', ''),
            audio_duration=audio_duration,
            processed_at=timezone.now()
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'response': f'حدث خطأ: {str(e)}'
        })


@login_required
@require_http_methods(['POST'])
def toggle_voice(request):
    """تفعيل/إيقاف المساعد"""
    preference, _ = UserVoicePreference.objects.get_or_create(user=request.user)
    preference.is_enabled = not preference.is_enabled
    preference.save()
    
    return JsonResponse({
        'success': True,
        'is_enabled': preference.is_enabled
    })


@login_required
def shortcuts_list(request):
    """قائمة الاختصارات الصوتية"""
    shortcuts = VoiceShortcut.objects.filter(user=request.user)
    
    return render(request, 'voice_assistant/shortcuts.html', {
        'shortcuts': shortcuts,
    })


@login_required
@require_http_methods(['POST'])
def create_shortcut(request):
    """إنشاء اختصار صوتي"""
    try:
        data = json.loads(request.body)
        
        shortcut = VoiceShortcut.objects.create(
            user=request.user,
            trigger_phrase=data.get('trigger_phrase'),
            action_url=data.get('action_url'),
            description=data.get('description', '')
        )
        
        return JsonResponse({
            'success': True,
            'shortcut_id': shortcut.id
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(['DELETE'])
def delete_shortcut(request, shortcut_id):
    """حذف اختصار صوتي"""
    try:
        shortcut = VoiceShortcut.objects.get(id=shortcut_id, user=request.user)
        shortcut.delete()
        
        return JsonResponse({'success': True})
    
    except VoiceShortcut.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'الاختصار غير موجود'
        })


@login_required
def command_history(request):
    """سجل الأوامر الصوتية"""
    commands = VoiceCommand.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    return render(request, 'voice_assistant/history.html', {
        'commands': commands,
    })


@login_required
def get_suggestions(request):
    """الحصول على اقتراحات الأوامر"""
    query = request.GET.get('q', '')
    
    suggestions = [
        {'text': 'افتح المبيعات', 'icon': 'fa-shopping-cart'},
        {'text': 'أنشئ فاتورة جديدة', 'icon': 'fa-file-invoice'},
        {'text': 'ابحث عن عميل', 'icon': 'fa-search'},
        {'text': 'تقرير المبيعات اليوم', 'icon': 'fa-chart-bar'},
        {'text': 'كم المبيعات اليوم', 'icon': 'fa-coins'},
        {'text': 'افتح المخزون', 'icon': 'fa-boxes'},
        {'text': 'أنشئ منتج جديد', 'icon': 'fa-plus-circle'},
        {'text': 'افتح الإعدادات', 'icon': 'fa-cog'},
    ]
    
    if query:
        suggestions = [s for s in suggestions if query in s['text']]
    
    return JsonResponse({'suggestions': suggestions})
