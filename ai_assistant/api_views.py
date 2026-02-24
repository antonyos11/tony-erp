"""
API Views للمساعد الذكي
========================
Endpoints محسنة للتكامل مع واجهة الشات
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

from .models import AIAssistantSettings, ChatSession, ChatMessage
from .services import AIService


def get_client_ip(request):
    """الحصول على IP العميل"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


@csrf_exempt
@require_http_methods(["POST"])
def api_start_session(request):
    """بدء جلسة جديدة"""
    try:
        data = json.loads(request.body) if request.body else {}
        assistant_type = data.get('type', 'system')
        
        # إنشاء أو الحصول على الإعدادات
        settings_obj, _ = AIAssistantSettings.objects.get_or_create(
            assistant_type=assistant_type,
            defaults={
                'name': 'المساعد الذكي',
                'welcome_message': 'أهلاً بك! كيف يمكنني مساعدتك؟',
                'is_active': True,
                'provider': 'local',
                'system_prompt': get_default_system_prompt(assistant_type)
            }
        )
        
        if not request.session.session_key:
            request.session.create()
        
        # إنشاء جلسة جديدة
        session = ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            assistant_settings=settings_obj,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.id),
            'welcome_message': settings_obj.welcome_message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_chat(request):
    """معالجة رسالة الشات"""
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'الرسالة فارغة'
            }, status=400)
        
        # الحصول على الجلسة أو إنشاء واحدة جديدة
        session = None
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, is_active=True)
            except ChatSession.DoesNotExist:
                pass
        
        if not session:
            # إنشاء جلسة جديدة
            settings_obj, _ = AIAssistantSettings.objects.get_or_create(
                assistant_type='system',
                defaults={
                    'name': 'المساعد الذكي',
                    'is_active': True,
                    'provider': 'local'
                }
            )
            
            if not request.session.session_key:
                request.session.create()
            
            session = ChatSession.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                assistant_settings=settings_obj,
                ip_address=get_client_ip(request)
            )
        
        # حفظ رسالة المستخدم
        ChatMessage.objects.create(
            session=session,
            role='user',
            content=message
        )
        
        # الحصول على تاريخ المحادثة
        history = list(session.messages.order_by('-created_at').values('role', 'content')[:10])
        messages = [{'role': m['role'], 'content': m['content']} for m in history]
        
        # تجهيز السياق
        context = {
            'user_authenticated': request.user.is_authenticated,
            'username': request.user.username if request.user.is_authenticated else None,
            'timestamp': timezone.now().isoformat()
        }
        
        # الحصول على الرد من AI
        ai_service = AIService(session.assistant_settings)
        response = ai_service.get_response(messages, context)
        
        # حفظ رد المساعد
        assistant_message = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=response.get('content', ''),
            tokens_used=response.get('tokens_used', 0)
        )
        
        return JsonResponse({
            'success': True,
            'response': response.get('content', ''),
            'session_id': str(session.id),
            'message_id': str(assistant_message.id),
            'tokens_used': response.get('tokens_used', 0),
            'processing_time': response.get('processing_time', 0),
            'quick_replies': get_quick_replies_for_response(response.get('content', ''))
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_quick_replies_for_response(response_text):
    """اقتراح ردود سريعة بناءً على الرد"""
    quick_replies = []
    
    response_lower = response_text.lower()
    
    if 'فاتورة' in response_lower:
        quick_replies = ['عرض الفواتير', 'تقرير المبيعات', 'إضافة عميل']
    elif 'مخزون' in response_lower or 'منتج' in response_lower:
        quick_replies = ['جرد المخزون', 'المنتجات منخفضة', 'إضافة منتج']
    elif 'عميل' in response_lower:
        quick_replies = ['قائمة العملاء', 'كشف حساب', 'فاتورة جديدة']
    elif 'تقرير' in response_lower:
        quick_replies = ['تقرير يومي', 'تقرير شهري', 'تصدير Excel']
    else:
        quick_replies = ['المبيعات', 'المخزون', 'التقارير', 'المساعدة']
    
    return quick_replies


def get_default_system_prompt(assistant_type):
    """الحصول على System Prompt الافتراضي"""
    if assistant_type == 'store':
        return """أنت مساعد ذكي ودود لمتجر إلكتروني عربي.
        
مهامك الرئيسية:
- مساعدة العملاء في البحث عن المنتجات
- الإجابة عن أسئلة الشحن والدفع
- تتبع الطلبات
- تقديم توصيات ذكية

تحدث بالعربية بشكل ودود ومهني. أجب بإيجاز."""
    else:
        return """أنت مساعد ذكي لنظام Tony ERP المحاسبي والإداري.

مهامك:
- شرح وظائف النظام (المبيعات، المشتريات، المخزون، المحاسبة)
- إرشاد المستخدمين للقوائم والصفحات
- المساعدة في إنشاء الفواتير والتقارير
- حل المشكلات الشائعة

قواعد:
- تحدث بالعربية
- أجب بخطوات واضحة ومحددة
- استخدم الإيموجي للتوضيح
- إذا لم تعرف الإجابة، اقترح التواصل مع الدعم"""
