import json
import re
import requests
from decimal import Decimal
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from .models import (
    WhatsAppConfig, WhatsAppConversation, WhatsAppMessage,
    WhatsAppTemplate, ProductCatalog, AutoReplyRule
)
from .serializers import (
    WhatsAppConversationSerializer, WhatsAppConversationListSerializer,
    WhatsAppMessageSerializer, WhatsAppTemplateSerializer,
    AutoReplyRuleSerializer, ProductCatalogSerializer,
    N8nWebhookSerializer, N8nProductSearchSerializer, N8nProductResponseSerializer,
    N8nCustomerCreateSerializer, N8nCustomerResponseSerializer,
    N8nSendMessageSerializer
)
from inventory.models import Product, Category
from crm.models import Customer, CustomerSource


# ============ Dashboard Views ============

def dashboard(request):
    """لوحة تحكم واتساب"""
    conversations = WhatsAppConversation.objects.all()[:20]
    templates = WhatsAppTemplate.objects.filter(is_active=True)
    rules = AutoReplyRule.objects.filter(is_active=True)
    
    stats = {
        'total_conversations': WhatsAppConversation.objects.count(),
        'open_conversations': WhatsAppConversation.objects.filter(status='open').count(),
        'total_messages': WhatsAppMessage.objects.count(),
        'today_messages': WhatsAppMessage.objects.filter(
            sent_at__date=timezone.now().date()
        ).count(),
        'auto_registered': WhatsAppConversation.objects.filter(auto_registered=True).count(),
    }
    
    context = {
        'conversations': conversations,
        'templates': templates,
        'rules': rules,
        'stats': stats,
    }
    return render(request, 'whatsapp_integration/dashboard.html', context)


def conversation_detail(request, pk):
    """تفاصيل المحادثة"""
    conversation = WhatsAppConversation.objects.get(pk=pk)
    messages = conversation.messages.all()
    templates = WhatsAppTemplate.objects.filter(is_active=True)
    
    context = {
        'conversation': conversation,
        'messages': messages,
        'templates': templates,
    }
    return render(request, 'whatsapp_integration/conversation.html', context)


# ============ n8n Webhook Endpoints ============

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def n8n_incoming_message(request):
    """
    Webhook لاستقبال الرسائل من n8n
    
    يستخدم في n8n كـ Webhook node للرسائل الواردة من WhatsApp
    
    Request Body:
    {
        "phone": "201234567890",
        "name": "اسم العميل",
        "message": "نص الرسالة",
        "message_id": "wamid.xxx",
        "timestamp": "2026-01-15T10:30:00Z"
    }
    """
    serializer = N8nWebhookSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    phone = data['phone']
    name = data.get('name', '')
    message = data['message']
    
    # البحث عن أو إنشاء المحادثة
    conversation, created = WhatsAppConversation.objects.get_or_create(
        phone_number=phone,
        defaults={'customer_name': name}
    )
    
    # تحديث اسم العميل إذا لم يكن موجوداً
    if name and not conversation.customer_name:
        conversation.customer_name = name
        conversation.save()
    
    # إنشاء الرسالة
    msg = WhatsAppMessage.objects.create(
        conversation=conversation,
        whatsapp_message_id=data.get('message_id', ''),
        direction='incoming',
        content=message,
    )
    
    # تحليل النية
    intent, confidence = detect_intent(message)
    msg.detected_intent = intent
    msg.confidence = confidence
    msg.save()
    
    # البحث عن المنتجات المذكورة
    products = search_products_in_message(message)
    if products:
        msg.mentioned_products.set(products)
    
    # التحقق من قواعد الرد التلقائي
    auto_response = check_auto_reply_rules(message)
    
    # التسجيل التلقائي في CRM
    customer = None
    if not conversation.customer:
        customer = auto_register_customer(phone, name, 'whatsapp')
        if customer:
            conversation.customer = customer
            conversation.auto_registered = True
            conversation.save()
    
    response_data = {
        'success': True,
        'conversation_id': conversation.id,
        'message_id': msg.id,
        'detected_intent': intent,
        'confidence': confidence,
        'mentioned_products': [p.name for p in products],
        'customer_registered': customer is not None,
        'customer_id': customer.id if customer else (
            conversation.customer.id if conversation.customer else None
        ),
        'auto_response': auto_response,
    }
    
    return Response(response_data)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def n8n_search_products(request):
    """
    البحث عن المنتجات - يستخدم في n8n للرد على استفسارات المنتجات
    
    GET /api/whatsapp/n8n/products/search/?query=مراتب&max_results=5
    
    POST:
    {
        "query": "مراتب سوست",
        "category": "مراتب",
        "max_results": 5
    }
    
    Response:
    {
        "count": 3,
        "products": [...],
        "whatsapp_message": "المنتجات المتاحة:\n1. ..."
    }
    """
    if request.method == 'GET':
        query = request.GET.get('query', '')
        category = request.GET.get('category', '')
        max_results = int(request.GET.get('max_results', 5))
    else:
        serializer = N8nProductSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        query = data['query']
        category = data.get('category', '')
        max_results = data.get('max_results', 5)
    
    # البحث عن المنتجات
    products = Product.objects.filter(is_active=True).select_related('category')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(description__icontains=query) |
            Q(barcode__icontains=query)
        )
    
    if category:
        products = products.filter(
            Q(category__name__icontains=category) |
            Q(category__parent__name__icontains=category)
        )
    
    products = products[:max_results]
    
    # تحضير الاستجابة
    product_list = []
    whatsapp_lines = ["🛍️ *المنتجات المتاحة:*\\n"]
    
    for i, p in enumerate(products, 1):
        # محاولة الحصول على الصورة
        image_url = ''
        if hasattr(p, 'image') and p.image:
            try:
                image_url = request.build_absolute_uri(p.image.url)
            except:
                pass
        
        # الحصول على السعر والمخزون الصحيح
        try:
            price = p.price if hasattr(p, 'price') else p.cost
            stock = p.current_stock if hasattr(p, 'current_stock') else 0
        except:
            price = 0
            stock = 0
        
        # تحضير النص للواتساب
        whatsapp_text = f"""
📦 *{p.name}*
💰 السعر: {price} جنيه
📊 المتوفر: {stock} قطعة
🔖 الكود: {p.sku or 'غير محدد'}
"""
        
        product_list.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku or '',
            'description': p.description or '',
            'price': str(price),
            'stock': stock,
            'category': p.category.name if p.category else '',
            'image_url': image_url,
            'whatsapp_text': whatsapp_text.strip(),
        })
        
        whatsapp_lines.append(f"{i}. *{p.name}* - {price} جنيه")
    
    if not product_list:
        whatsapp_message = "⚠️ عذراً، لم نجد منتجات مطابقة لبحثك."
    else:
        whatsapp_lines.append("\\n📞 للطلب أو الاستفسار، أرسل رقم المنتج")
        whatsapp_message = "\\n".join(whatsapp_lines)
    
    return Response({
        'success': True,
        'count': len(product_list),
        'products': product_list,
        'whatsapp_message': whatsapp_message,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def n8n_register_customer(request):
    """
    تسجيل عميل جديد من واتساب - يستخدم في n8n
    
    POST:
    {
        "phone": "201234567890",
        "name": "أحمد محمد",
        "email": "ahmed@example.com",
        "company": "شركة ABC",
        "city": "القاهرة",
        "source": "whatsapp",
        "notes": "عميل من حملة يناير"
    }
    """
    serializer = N8nCustomerCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    phone = data['phone']
    
    # التحقق من وجود العميل
    existing = Customer.objects.filter(
        Q(phone=phone) | Q(mobile=phone)
    ).first()
    
    if existing:
        return Response({
            'success': True,
            'created': False,
            'message': 'العميل موجود مسبقاً',
            'customer': N8nCustomerResponseSerializer(existing).data
        })
    
    # إنشاء عميل جديد
    customer = auto_register_customer(
        phone=phone,
        name=data.get('name', ''),
        source=data.get('source', 'whatsapp'),
        email=data.get('email', ''),
        company=data.get('company', ''),
        city=data.get('city', ''),
        notes=data.get('notes', '')
    )
    
    if customer:
        return Response({
            'success': True,
            'created': True,
            'message': 'تم تسجيل العميل بنجاح',
            'customer': N8nCustomerResponseSerializer(customer).data
        })
    
    return Response({
        'success': False,
        'message': 'فشل في تسجيل العميل'
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def n8n_get_customer(request, phone):
    """
    الحصول على بيانات عميل بالهاتف
    
    GET /api/whatsapp/n8n/customer/201234567890/
    """
    customer = Customer.objects.filter(
        Q(phone=phone) | Q(mobile=phone)
    ).first()
    
    if not customer:
        return Response({
            'success': False,
            'found': False,
            'message': 'العميل غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': True,
        'found': True,
        'customer': N8nCustomerResponseSerializer(customer).data
    })


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def n8n_get_products_catalog(request):
    """
    الحصول على كتالوج المنتجات الكامل للواتساب
    
    GET /api/whatsapp/n8n/catalog/
    GET /api/whatsapp/n8n/catalog/?category=مراتب
    """
    category = request.GET.get('category', '')
    
    products = Product.objects.filter(is_active=True).select_related('category')
    
    if category:
        products = products.filter(
            Q(category__name__icontains=category) |
            Q(category__parent__name__icontains=category)
        )
    
    catalog = []
    for p in products[:50]:
        # الحصول على السعر والمخزون الصحيح
        try:
            price = p.price if hasattr(p, 'price') else p.cost
            stock = p.current_stock if hasattr(p, 'current_stock') else 0
        except:
            price = 0
            stock = 0
        
        catalog.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku or '',
            'price': str(price),
            'stock': stock,
            'category': p.category.name if p.category else '',
            'available': stock > 0,
        })
    
    return Response({
        'success': True,
        'count': len(catalog),
        'catalog': catalog,
    })



@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def n8n_log_conversation(request):
    """
    تسجيل محادثة كاملة من n8n
    
    POST:
    {
        "phone": "201234567890",
        "messages": [
            {"direction": "incoming", "content": "السلام عليكم"},
            {"direction": "outgoing", "content": "وعليكم السلام"}
        ]
    }
    """
    phone = request.data.get('phone')
    messages = request.data.get('messages', [])
    
    if not phone:
        return Response({'error': 'phone is required'}, status=400)
    
    conversation, _ = WhatsAppConversation.objects.get_or_create(
        phone_number=phone
    )
    
    for msg in messages:
        WhatsAppMessage.objects.create(
            conversation=conversation,
            direction=msg.get('direction', 'incoming'),
            content=msg.get('content', ''),
        )
    
    return Response({
        'success': True,
        'conversation_id': conversation.id,
        'messages_count': len(messages)
    })


# ============ WhatsApp Webhook Verification ============

@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    Webhook للتحقق من واتساب و استقبال الرسائل
    
    هذا يستخدم مباشرة مع WhatsApp Business API
    """
    if request.method == 'GET':
        # Verification
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        config = WhatsAppConfig.objects.first()
        verify_token = config.whatsapp_verify_token if config else 'VERIFY_TOKEN'
        
        if mode == 'subscribe' and token == verify_token:
            return HttpResponse(challenge)
        return HttpResponse('Forbidden', status=403)
    
    # POST - incoming message
    try:
        data = json.loads(request.body)
        # Process the message
        process_whatsapp_message(data)
    except Exception as e:
        print(f"Error processing webhook: {e}")
    
    return HttpResponse('OK')


# ============ Helper Functions ============

def detect_intent(message):
    """تحليل نية الرسالة"""
    message_lower = message.lower()
    
    intents = {
        'greeting': ['مرحبا', 'السلام', 'صباح', 'مساء', 'اهلا', 'هاي', 'hello', 'hi'],
        'product_inquiry': ['سعر', 'منتج', 'متوفر', 'موجود', 'عندكم', 'ايه', 'شو'],
        'order': ['طلب', 'اطلب', 'اشتري', 'خد', 'order', 'buy'],
        'complaint': ['شكوى', 'مشكلة', 'مش', 'خربان', 'سيء'],
        'support': ['مساعدة', 'ازاي', 'كيف', 'help'],
        'price_list': ['قايمة', 'قائمة', 'اسعار', 'كتالوج', 'catalog'],
        'location': ['عنوان', 'فين', 'وين', 'موقع', 'location'],
        'contact': ['رقم', 'تليفون', 'تواصل', 'contact'],
    }
    
    for intent, keywords in intents.items():
        for keyword in keywords:
            if keyword in message_lower:
                confidence = 0.8 if len(keyword) > 3 else 0.6
                return intent, confidence
    
    return 'unknown', 0.3


def search_products_in_message(message):
    """البحث عن المنتجات المذكورة في الرسالة"""
    products = Product.objects.filter(is_active=True)
    found = []
    
    message_lower = message.lower()
    
    for product in products[:100]:  # Limit for performance
        if product.name.lower() in message_lower:
            found.append(product)
        elif product.sku and product.sku.lower() in message_lower:
            found.append(product)
    
    return found[:5]  # Max 5 products


def check_auto_reply_rules(message):
    """التحقق من قواعد الرد التلقائي"""
    rules = AutoReplyRule.objects.filter(is_active=True).order_by('-priority')
    
    for rule in rules:
        matched = False
        
        if rule.match_type == 'exact':
            matched = message.strip() == rule.trigger_text.strip()
        elif rule.match_type == 'contains':
            matched = rule.trigger_text.lower() in message.lower()
        elif rule.match_type == 'starts_with':
            matched = message.lower().startswith(rule.trigger_text.lower())
        elif rule.match_type == 'regex':
            try:
                matched = bool(re.search(rule.trigger_text, message, re.IGNORECASE))
            except:
                pass
        
        if matched:
            if rule.response_template:
                return {
                    'rule_id': rule.id,
                    'action': rule.action,
                    'template_id': rule.response_template.id,
                    'response': rule.response_template.body
                }
            elif rule.response_text:
                return {
                    'rule_id': rule.id,
                    'action': rule.action,
                    'response': rule.response_text
                }
    
    return None


def auto_register_customer(phone, name='', source='whatsapp', email='', company='', city='', notes=''):
    """تسجيل عميل تلقائي من واتساب"""
    try:
        # التحقق من وجود العميل
        existing = Customer.objects.filter(
            Q(phone=phone) | Q(mobile=phone)
        ).first()
        
        if existing:
            return existing
        
        # إنشاء كود العميل
        last_customer = Customer.objects.order_by('-id').first()
        if last_customer:
            try:
                last_code = int(last_customer.customer_code.replace('C', ''))
                customer_code = f'C{last_code + 1:06d}'
            except:
                customer_code = f'CW{timezone.now().strftime("%Y%m%d%H%M%S")}'
        else:
            customer_code = 'C000001'
        
        # تحليل الاسم
        name_parts = name.split() if name else ['عميل', 'واتساب']
        first_name = name_parts[0] if name_parts else 'عميل'
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'واتساب'
        
        # الحصول على مصدر العميل
        customer_source, _ = CustomerSource.objects.get_or_create(
            name='واتساب',
            defaults={'description': 'عملاء من واتساب', 'is_active': True}
        )
        
        # إنشاء العميل
        customer = Customer.objects.create(
            customer_code=customer_code,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            mobile=phone,
            email=email,
            company_name=company,
            city=city,
            source=customer_source,
            status='active',
            notes=f"تم التسجيل تلقائياً من واتساب\n{notes}".strip(),
        )
        
        return customer
    except Exception as e:
        print(f"Error auto-registering customer: {e}")
        return None


def process_whatsapp_message(data):
    """معالجة رسالة واتساب"""
    try:
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])
        
        for msg in messages:
            phone = msg.get('from')
            text = msg.get('text', {}).get('body', '')
            msg_id = msg.get('id')
            
            # تنفيذ نفس منطق n8n_incoming_message
            # ...
    except Exception as e:
        print(f"Error: {e}")


# ============ ViewSets ============

class WhatsAppConversationViewSet(viewsets.ModelViewSet):
    queryset = WhatsAppConversation.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return WhatsAppConversationListSerializer
        return WhatsAppConversationSerializer
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """إرسال رسالة"""
        conversation = self.get_object()
        message = request.data.get('message')
        
        if not message:
            return Response({'error': 'message required'}, status=400)
        
        msg = WhatsAppMessage.objects.create(
            conversation=conversation,
            direction='outgoing',
            content=message,
        )
        
        return Response(WhatsAppMessageSerializer(msg).data)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """تعيين موظف للمحادثة"""
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        conversation.assigned_to_id = user_id
        conversation.save()
        
        return Response({'success': True})


class WhatsAppTemplateViewSet(viewsets.ModelViewSet):
    queryset = WhatsAppTemplate.objects.all()
    serializer_class = WhatsAppTemplateSerializer
    permission_classes = [IsAuthenticated]


class AutoReplyRuleViewSet(viewsets.ModelViewSet):
    queryset = AutoReplyRule.objects.all()
    serializer_class = AutoReplyRuleSerializer
    permission_classes = [IsAuthenticated]
