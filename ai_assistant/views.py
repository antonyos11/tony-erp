"""
Views للمساعد الذكي
==================
"""
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.utils import timezone

from .models import AIAssistantSettings, ChatSession, ChatMessage, FAQ, QuickReply
from .services import AIService


def get_client_ip(request):
    """الحصول على IP العميل"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_or_create_session(request, assistant_type: str) -> ChatSession:
    """الحصول على جلسة موجودة أو إنشاء جديدة"""
    # الحصول على إعدادات المساعد
    settings_obj, created = AIAssistantSettings.objects.get_or_create(
        assistant_type=assistant_type,
        defaults={
            'name': 'مساعد المتجر' if assistant_type == 'store' else 'مساعد النظام',
            'welcome_message': 'أهلاً بك! كيف يمكنني مساعدتك؟',
            'is_active': True
        }
    )
    
    # البحث عن جلسة نشطة
    session = None
    
    if request.user.is_authenticated:
        session = ChatSession.objects.filter(
            user=request.user,
            assistant_settings=settings_obj,
            is_active=True
        ).first()
    else:
        session_key = request.session.session_key
        if session_key:
            session = ChatSession.objects.filter(
                session_key=session_key,
                assistant_settings=settings_obj,
                is_active=True
            ).first()
    
    # إنشاء جلسة جديدة إذا لم توجد
    if not session:
        if not request.session.session_key:
            request.session.create()
        
        session = ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key if not request.user.is_authenticated else '',
            assistant_settings=settings_obj,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=get_client_ip(request)
        )
    
    return session


@require_http_methods(["POST"])
def chat_message(request, assistant_type: str):
    """إرسال رسالة واستقبال الرد"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': _('الرسالة فارغة')
            }, status=400)
        
        # الحصول على الجلسة
        session = get_or_create_session(request, assistant_type)
        
        # حفظ رسالة المستخدم
        user_msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_message
        )
        
        # تجهيز السياق
        context = {
            'user_authenticated': request.user.is_authenticated,
            'timestamp': timezone.now().isoformat()
        }
        
        if request.user.is_authenticated:
            context['user_name'] = request.user.get_full_name() or request.user.username
        
        # الحصول على رسائل المحادثة السابقة
        previous_messages = list(
            session.messages.order_by('created_at').values('role', 'content')[:10]
        )
        
        # استدعاء خدمة AI
        ai_service = AIService(session.assistant_settings)
        response = ai_service.get_response(previous_messages, context)
        
        # حفظ رد المساعد
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=response['content'],
            tokens_used=response.get('tokens_used', 0),
            processing_time=response.get('processing_time', 0),
            related_products=response.get('related_products', [])
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': str(assistant_msg.id),
                'content': response['content'],
                'role': 'assistant',
                'timestamp': assistant_msg.created_at.isoformat(),
                'related_products': response.get('related_products', [])
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': _('بيانات غير صالحة')
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_chat_history(request, assistant_type: str):
    """الحصول على سجل المحادثة"""
    try:
        session = get_or_create_session(request, assistant_type)
        
        messages = session.messages.order_by('created_at').values(
            'id', 'role', 'content', 'created_at', 'related_products'
        )
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.id),
            'messages': list(messages),
            'welcome_message': session.assistant_settings.welcome_message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_quick_replies(request, assistant_type: str):
    """الحصول على الردود السريعة"""
    try:
        replies = QuickReply.objects.filter(
            assistant_type=assistant_type,
            is_active=True
        ).order_by('order').values('id', 'title', 'content', 'icon')
        
        return JsonResponse({
            'success': True,
            'quick_replies': list(replies)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_faqs(request, assistant_type: str):
    """الحصول على الأسئلة الشائعة"""
    try:
        category = request.GET.get('category')
        
        faqs = FAQ.objects.filter(
            assistant_type=assistant_type,
            is_active=True
        )
        
        if category:
            faqs = faqs.filter(category=category)
        
        faqs = faqs.order_by('category', 'order').values(
            'id', 'category', 'question', 'answer'
        )
        
        return JsonResponse({
            'success': True,
            'faqs': list(faqs)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def end_session(request, assistant_type: str):
    """إنهاء جلسة المحادثة"""
    try:
        session = get_or_create_session(request, assistant_type)
        session.end_session()
        
        return JsonResponse({
            'success': True,
            'message': _('تم إنهاء المحادثة')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def rate_message(request, message_id: str):
    """تقييم رسالة (مفيدة/غير مفيدة)"""
    try:
        data = json.loads(request.body)
        is_helpful = data.get('helpful', True)
        
        message = get_object_or_404(ChatMessage, id=message_id)
        
        # يمكن إضافة حقل للتقييم في النموذج لاحقاً
        
        return JsonResponse({
            'success': True,
            'message': _('شكراً على تقييمك')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ===== Admin Views =====

@login_required
def admin_dashboard(request):
    """لوحة تحكم المساعد الذكي"""
    from django.db.models import Count, Avg
    from django.db.models.functions import TruncDate
    
    # إحصائيات
    total_sessions = ChatSession.objects.count()
    total_messages = ChatMessage.objects.count()
    active_sessions = ChatSession.objects.filter(is_active=True).count()
    
    # أحدث الجلسات
    recent_sessions = ChatSession.objects.select_related(
        'user', 'assistant_settings'
    ).order_by('-started_at')[:10]
    
    # إعدادات المساعدين
    assistants = AIAssistantSettings.objects.all()
    
    # إحصائيات الأسئلة الشائعة
    top_faqs = FAQ.objects.order_by('-views_count')[:5]
    
    context = {
        'title': _('لوحة تحكم المساعد الذكي'),
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'active_sessions': active_sessions,
        'recent_sessions': recent_sessions,
        'assistants': assistants,
        'top_faqs': top_faqs,
    }
    
    return render(request, 'ai_assistant/admin/dashboard.html', context)


@login_required
def admin_settings(request, assistant_type: str):
    """إعدادات المساعد"""
    settings_obj, created = AIAssistantSettings.objects.get_or_create(
        assistant_type=assistant_type,
        defaults={
            'name': 'مساعد المتجر' if assistant_type == 'store' else 'مساعد النظام',
        }
    )
    
    if request.method == 'POST':
        # تحديث الإعدادات
        settings_obj.name = request.POST.get('name', settings_obj.name)
        settings_obj.welcome_message = request.POST.get('welcome_message', '')
        settings_obj.provider = request.POST.get('provider', 'openai')
        settings_obj.api_key = request.POST.get('api_key', '')
        settings_obj.model_name = request.POST.get('model_name', 'gpt-3.5-turbo')
        settings_obj.system_prompt = request.POST.get('system_prompt', '')
        settings_obj.max_tokens = int(request.POST.get('max_tokens', 1000))
        settings_obj.temperature = float(request.POST.get('temperature', 0.7))
        settings_obj.is_active = request.POST.get('is_active') == 'on'
        settings_obj.enable_product_search = request.POST.get('enable_product_search') == 'on'
        settings_obj.enable_order_tracking = request.POST.get('enable_order_tracking') == 'on'
        settings_obj.enable_faq = request.POST.get('enable_faq') == 'on'
        settings_obj.save()
        
        return JsonResponse({'success': True, 'message': _('تم حفظ الإعدادات')})
    
    context = {
        'title': _('إعدادات المساعد'),
        'settings': settings_obj,
        'assistant_type': assistant_type,
    }
    
    return render(request, 'ai_assistant/admin/settings.html', context)
