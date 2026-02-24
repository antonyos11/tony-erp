from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponse
import hashlib
import hmac
from .models import (
    WhatsAppConversation, WhatsAppMessage, 
    ProductKnowledgeBase, WhatsAppConfiguration,
    SocialConversation, SocialMessage, SocialPlatformConfig
)
from .serializers import (
    WhatsAppConversationSerializer, WhatsAppMessageSerializer,
    ProductKnowledgeSerializer, WhatsAppIncomingMessageSerializer,
    AIResponseSerializer, CRMAutoCreateSerializer,
    SocialConversationSerializer
)
from crm.models import Customer, Opportunity
import json
import logging
import requests

logger = logging.getLogger(__name__)


class ProductKnowledgeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API للحصول على معلومات المنتجات للـ AI
    """
    queryset = ProductKnowledgeBase.objects.filter(is_active=True)
    serializer_class = ProductKnowledgeSerializer
    permission_classes = [AllowAny]  # يمكن الوصول من n8n
    
    @action(detail=False, methods=['get'])
    def for_ai(self, request):
        """
        إرجاع المنتجات بصيغة مناسبة للـ AI
        """
        products = self.get_queryset()
        
        # بناء context للـ AI
        products_context = []
        for p in products:
            product_info = {
                'name': p.product_name,
                'code': p.product_code,
                'description': p.description,
                'price': f"{p.price} {p.currency}" if p.price else "اتصل للسعر",
                'available': p.in_stock,
                'category': p.category,
                'features': p.features,
            }
            products_context.append(product_info)
        
        return Response({
            'products_count': len(products_context),
            'products': products_context,
            'last_updated': timezone.now()
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        البحث في المنتجات بالكلمات المفتاحية
        """
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'error': 'يرجى إدخال كلمة بحث'}, status=400)
        
        # البحث في الاسم، الوصف، والكلمات المفتاحية
        products = self.get_queryset().filter(
            models.Q(product_name__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(keywords__contains=[query]) |
            models.Q(category__icontains=query)
        )
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class WhatsAppConversationViewSet(viewsets.ModelViewSet):
    """
    إدارة محادثات الواتساب
    """
    queryset = WhatsAppConversation.objects.all()
    serializer_class = WhatsAppConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # فلترة حسب الحالة
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        # فلترة حسب العميل
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        
        return qs
    
    @action(detail=True, methods=['post'])
    def convert_to_customer(self, request, pk=None):
        """
        تحويل المحادثة إلى عميل في CRM
        """
        conversation = self.get_object()
        
        if conversation.customer:
            return Response({
                'message': 'المحادثة مرتبطة بعميل بالفعل',
                'customer_id': conversation.customer.id
            })
        
        # إنشاء عميل
        customer = Customer.objects.create(
            name=conversation.customer_name or f"عميل واتساب {conversation.phone_number}",
            phone=conversation.phone_number,
            source='واتساب',
            notes=conversation.conversation_summary or f"محادثة واتساب - {conversation.messages_count} رسالة"
        )
        
        # ربط المحادثة بالعميل
        conversation.customer = customer
        conversation.status = 'converted'
        conversation.save()
        
        # إنشاء فرصة بيع إذا كان هناك منتجات مهتم بها
        opportunity = None
        if conversation.interested_products:
            opportunity = Opportunity.objects.create(
                customer=customer,
                title=f"فرصة من واتساب - {customer.name}",
                description=f"منتجات مهتم بها: {', '.join(conversation.interested_products)}\n\n"
                           f"{conversation.conversation_summary or ''}",
                stage='مبدئي',
                probability=min(conversation.conversion_probability * 100, 100),
                source='واتساب'
            )
            conversation.opportunity = opportunity
            conversation.save()
        
        return Response({
            'message': 'تم التحويل بنجاح',
            'customer_id': customer.id,
            'opportunity_id': opportunity.id if opportunity else None
        })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def whatsapp_webhook(request):
    """
    Webhook لاستقبال رسائل WhatsApp
    يستقبل الرسائل من WhatsApp Business API
    """
    try:
        data = request.data
        logger.info(f"Received WhatsApp webhook: {data}")
        
        # التحقق من صحة البيانات
        serializer = WhatsAppIncomingMessageSerializer(data=data)
        if not serializer.is_valid():
            return Response({'error': 'بيانات غير صحيحة', 'details': serializer.errors}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        validated = serializer.validated_data
        
        # البحث عن المحادثة أو إنشائها
        conversation, created = WhatsAppConversation.objects.get_or_create(
            phone_number=validated['from_number'],
            defaults={
                'customer_name': validated.get('customer_name', ''),
                'status': 'active'
            }
        )
        
        # إنشاء الرسالة
        message = WhatsAppMessage.objects.create(
            conversation=conversation,
            direction='inbound',
            message_type=validated.get('message_type', 'text'),
            content=validated.get('text_body', ''),
            media_url=validated.get('media_url', ''),
            whatsapp_message_id=validated['message_id']
        )
        
        # تحديث عداد الرسائل
        conversation.messages_count += 1
        conversation.last_message_at = timezone.now()
        conversation.save()
        
        return Response({
            'success': True,
            'conversation_id': conversation.id,
            'message_id': message.id,
            'message': 'تم استقبال الرسالة بنجاح'
        })
        
    except Exception as e:
        logger.error(f"Error in WhatsApp webhook: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def n8n_callback(request):
    """
    Callback من n8n بعد معالجة الرسالة بالـ AI
    """
    try:
        data = request.data
        logger.info(f"Received n8n callback: {data}")
        
        conversation_id = data.get('conversation_id')
        ai_response = data.get('ai_response', '')
        detected_intent = data.get('intent', '')
        extracted_products = data.get('products', [])
        sentiment = data.get('sentiment', '')
        conversion_score = float(data.get('conversion_score', 0.0))
        
        # تحديث المحادثة
        try:
            conversation = WhatsAppConversation.objects.get(id=conversation_id)
            
            # تحديث المعلومات
            if extracted_products:
                existing = conversation.interested_products or []
                conversation.interested_products = list(set(existing + extracted_products))
            
            if sentiment:
                conversation.ai_sentiment = sentiment
            
            if conversion_score > conversation.conversion_probability:
                conversation.conversion_probability = conversion_score
            
            conversation.save()
            
            # حفظ رد الـ AI كرسالة صادرة
            outbound_message = WhatsAppMessage.objects.create(
                conversation=conversation,
                direction='outbound',
                message_type='text',
                content=ai_response,
                whatsapp_message_id=f"ai_{timezone.now().timestamp()}",
                ai_intent=detected_intent
            )
            
            # إنشاء عميل تلقائياً إذا كان التحويل محتمل
            config = WhatsAppConfiguration.objects.filter(is_active=True).first()
            if config and config.auto_create_customer and conversion_score >= 0.5:
                if not conversation.customer:
                    auto_create_data = {
                        'phone_number': conversation.phone_number,
                        'customer_name': conversation.customer_name,
                        'interested_products': conversation.interested_products,
                        'conversation_summary': conversation.conversation_summary,
                        'conversion_probability': conversion_score
                    }
                    crm_serializer = CRMAutoCreateSerializer(data=auto_create_data)
                    if crm_serializer.is_valid():
                        result = crm_serializer.save()
                        conversation.customer = result['customer']
                        if result.get('opportunity'):
                            conversation.opportunity = result['opportunity']
                        conversation.save()
            
            return Response({
                'success': True,
                'message': 'تم تحديث المحادثة بنجاح',
                'conversation_id': conversation.id
            })
            
        except WhatsAppConversation.DoesNotExist:
            return Response({'error': 'المحادثة غير موجودة'}, status=404)
        
    except Exception as e:
        logger.error(f"Error in n8n callback: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def ai_context(request):
    """
    الحصول على السياق الكامل للـ AI
    يستخدمه n8n لتغذية الذكاء الصناعي
    """
    try:
        # معلومات المنتجات
        products = ProductKnowledgeBase.objects.filter(is_active=True)
        products_data = ProductKnowledgeSerializer(products, many=True).data
        
        # إعدادات النظام
        config = WhatsAppConfiguration.objects.filter(is_active=True).first()
        system_prompt = config.system_prompt if config else "أنت مساعد مبيعات ذكي"
        
        # معلومات الشركة (يمكن إضافتها لاحقاً)
        company_info = {
            'name': 'شركتنا',
            'description': 'نحن شركة متخصصة في بيع منتجات عالية الجودة',
            'working_hours': '9 صباحاً - 6 مساءً',
            'contact': 'للاستفسار اتصل بنا'
        }
        
        context = {
            'system_prompt': system_prompt,
            'products': products_data,
            'products_count': len(products_data),
            'company_info': company_info,
            'timestamp': timezone.now().isoformat()
        }
        
        return Response(context)
        
    except Exception as e:
        logger.error(f"Error getting AI context: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_products(request):
    """
    مزامنة المنتجات من النظام إلى قاعدة معرفة الـ AI
    """
    try:
        from inventory.models import Product
        
        synced_count = 0
        updated_count = 0
        
        products = Product.objects.filter(is_active=True)
        for product in products:
            # الحصول على السعر
            price = None
            if hasattr(product, 'price') and product.price:
                price = product.price
            elif hasattr(product, 'price') and product.price:
                price = product.price
            
            # الحصول على الفئة
            category = ''
            if hasattr(product, 'category') and product.category:
                category = str(product.category)
            
            # إنشاء أو تحديث في قاعدة المعرفة
            obj, created = ProductKnowledgeBase.objects.update_or_create(
                product_code=product.code if hasattr(product, 'code') else str(product.id),
                defaults={
                    'product_name': product.name,
                    'description': getattr(product, 'description', '') or f"منتج: {product.name}",
                    'price': price,
                    'category': category,
                    'in_stock': getattr(product, 'is_active', True),
                    'is_active': True
                }
            )
            if created:
                synced_count += 1
            else:
                updated_count += 1
        
        return Response({
            'success': True,
            'synced_count': synced_count + updated_count,
            'new_products': synced_count,
            'updated_products': updated_count,
            'message': f'تمت مزامنة {synced_count + updated_count} منتج ({synced_count} جديد، {updated_count} محدّث)'
        })
        
    except Exception as e:
        logger.error(f"Error syncing products: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)


# ============================================
#   Social Media Unified Webhook (FB, IG, WA)
# ============================================

def verify_facebook_signature(request, app_secret):
    """التحقق من توقيع Facebook/Meta"""
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not signature:
        return True  # لبعض الطلبات قد لا يوجد توقيع
    
    expected = 'sha256=' + hmac.new(
        app_secret.encode('utf-8'),
        request.body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def unified_webhook(request, platform):
    """
    Webhook موحد لجميع المنصات (whatsapp, facebook, instagram)
    
    GET: للتحقق من الـ webhook (verification challenge)
    POST: لاستقبال الرسائل
    """
    platform = platform.lower()
    
    if platform not in ['whatsapp', 'facebook', 'instagram']:
        return Response({'error': 'منصة غير مدعومة'}, status=400)
    
    # الحصول على إعدادات المنصة
    config = SocialPlatformConfig.objects.filter(platform=platform, is_active=True).first()
    
    # GET = Webhook Verification
    if request.method == 'GET':
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')
        
        expected_token = config.verify_token if config else 'default_verify_token'
        
        if mode == 'subscribe' and token == expected_token:
            logger.info(f"Webhook verified for {platform}")
            return HttpResponse(challenge, content_type='text/plain')
        else:
            return Response({'error': 'Verification failed'}, status=403)
    
    # POST = Incoming Message
    try:
        data = request.data
        logger.info(f"Received {platform} webhook: {json.dumps(data, ensure_ascii=False)[:500]}")
        
        # تحقق من التوقيع
        if config and config.app_secret:
            if not verify_facebook_signature(request, config.app_secret):
                logger.warning(f"Invalid signature for {platform} webhook")
                return Response({'error': 'Invalid signature'}, status=403)
        
        # معالجة الرسالة حسب المنصة
        if platform == 'whatsapp':
            result = process_whatsapp_message(data, config)
        elif platform == 'facebook':
            result = process_facebook_message(data, config)
        elif platform == 'instagram':
            result = process_instagram_message(data, config)
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Error in {platform} webhook: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)


def process_whatsapp_message(data, config):
    """معالجة رسائل WhatsApp"""
    messages = []
    
    # استخراج الرسائل من WhatsApp webhook format
    entry = data.get('entry', [])
    for e in entry:
        changes = e.get('changes', [])
        for change in changes:
            value = change.get('value', {})
            wa_messages = value.get('messages', [])
            contacts = value.get('contacts', [])
            
            for msg in wa_messages:
                sender_name = ''
                sender_id = msg.get('from', '')
                
                # الحصول على اسم المرسل
                for contact in contacts:
                    if contact.get('wa_id') == sender_id:
                        sender_name = contact.get('profile', {}).get('name', '')
                        break
                
                # استخراج محتوى الرسالة
                msg_type = msg.get('type', 'text')
                content = ''
                media_url = ''
                
                if msg_type == 'text':
                    content = msg.get('text', {}).get('body', '')
                elif msg_type == 'image':
                    content = msg.get('image', {}).get('caption', '[صورة]')
                    media_url = msg.get('image', {}).get('id', '')
                elif msg_type == 'document':
                    content = msg.get('document', {}).get('filename', '[مستند]')
                    media_url = msg.get('document', {}).get('id', '')
                elif msg_type == 'voice':
                    content = '[رسالة صوتية]'
                    media_url = msg.get('audio', {}).get('id', '')
                elif msg_type == 'video':
                    content = msg.get('video', {}).get('caption', '[فيديو]')
                    media_url = msg.get('video', {}).get('id', '')
                
                messages.append({
                    'platform_user_id': sender_id,
                    'phone_number': sender_id,
                    'customer_name': sender_name,
                    'message_id': msg.get('id', ''),
                    'message_type': msg_type,
                    'content': content,
                    'media_url': media_url
                })
    
    # حفظ الرسائل
    saved_messages = save_social_messages('whatsapp', messages, config)
    
    return {
        'success': True,
        'platform': 'whatsapp',
        'messages_count': len(saved_messages),
        'messages': saved_messages
    }


def process_facebook_message(data, config):
    """معالجة رسائل Facebook Messenger"""
    messages = []
    
    entry = data.get('entry', [])
    for e in entry:
        messaging = e.get('messaging', [])
        for msg_event in messaging:
            sender = msg_event.get('sender', {})
            sender_id = sender.get('id', '')
            
            message = msg_event.get('message', {})
            if not message:
                continue  # قد يكون delivery notification
            
            msg_type = 'text'
            content = message.get('text', '')
            media_url = ''
            
            # التحقق من المرفقات
            attachments = message.get('attachments', [])
            if attachments:
                attachment = attachments[0]
                att_type = attachment.get('type', '')
                if att_type == 'image':
                    msg_type = 'image'
                    content = '[صورة]'
                    media_url = attachment.get('payload', {}).get('url', '')
                elif att_type == 'video':
                    msg_type = 'video'
                    content = '[فيديو]'
                    media_url = attachment.get('payload', {}).get('url', '')
                elif att_type == 'audio':
                    msg_type = 'voice'
                    content = '[رسالة صوتية]'
                    media_url = attachment.get('payload', {}).get('url', '')
                elif att_type == 'file':
                    msg_type = 'document'
                    content = '[ملف]'
                    media_url = attachment.get('payload', {}).get('url', '')
            
            messages.append({
                'platform_user_id': sender_id,
                'phone_number': '',
                'customer_name': '',  # سيتم جلبه لاحقاً من Facebook API
                'message_id': message.get('mid', ''),
                'message_type': msg_type,
                'content': content,
                'media_url': media_url
            })
    
    # جلب أسماء المستخدمين من Facebook (اختياري)
    if config and messages:
        for msg in messages:
            user_info = get_facebook_user_info(msg['platform_user_id'], config.page_access_token)
            if user_info:
                msg['customer_name'] = user_info.get('name', '')
    
    # حفظ الرسائل
    saved_messages = save_social_messages('facebook', messages, config)
    
    return {
        'success': True,
        'platform': 'facebook',
        'messages_count': len(saved_messages),
        'messages': saved_messages
    }


def process_instagram_message(data, config):
    """معالجة رسائل Instagram DM"""
    messages = []
    
    entry = data.get('entry', [])
    for e in entry:
        messaging = e.get('messaging', [])
        for msg_event in messaging:
            sender = msg_event.get('sender', {})
            sender_id = sender.get('id', '')
            
            message = msg_event.get('message', {})
            if not message:
                continue
            
            msg_type = 'text'
            content = message.get('text', '')
            media_url = ''
            
            # التحقق من المرفقات
            attachments = message.get('attachments', [])
            if attachments:
                attachment = attachments[0]
                att_type = attachment.get('type', '')
                if att_type == 'image':
                    msg_type = 'image'
                    content = '[صورة]'
                    media_url = attachment.get('payload', {}).get('url', '')
                elif att_type == 'video':
                    msg_type = 'video'
                    content = '[فيديو]'
                    media_url = attachment.get('payload', {}).get('url', '')
                elif att_type == 'share':
                    msg_type = 'sticker'
                    content = '[مشاركة]'
                elif att_type == 'story_mention':
                    msg_type = 'story_mention'
                    content = '[إشارة في ستوري]'
            
            # إذا كان رد على ستوري
            if message.get('is_story_reply'):
                msg_type = 'story_reply'
                content = f"[رد على ستوري] {content}"
            
            messages.append({
                'platform_user_id': sender_id,
                'phone_number': '',
                'customer_name': '',
                'message_id': message.get('mid', ''),
                'message_type': msg_type,
                'content': content,
                'media_url': media_url
            })
    
    # جلب أسماء المستخدمين من Instagram
    if config and messages:
        for msg in messages:
            user_info = get_instagram_user_info(msg['platform_user_id'], config.page_access_token)
            if user_info:
                msg['customer_name'] = user_info.get('username', user_info.get('name', ''))
    
    # حفظ الرسائل
    saved_messages = save_social_messages('instagram', messages, config)
    
    return {
        'success': True,
        'platform': 'instagram',
        'messages_count': len(saved_messages),
        'messages': saved_messages
    }


def save_social_messages(platform, messages, config):
    """حفظ الرسائل في قاعدة البيانات"""
    saved = []
    
    for msg_data in messages:
        try:
            # البحث عن المحادثة أو إنشائها
            conversation, created = SocialConversation.objects.get_or_create(
                platform=platform,
                platform_user_id=msg_data['platform_user_id'],
                defaults={
                    'customer_name': msg_data.get('customer_name', ''),
                    'phone_number': msg_data.get('phone_number', ''),
                    'status': 'active'
                }
            )
            
            # تحديث الاسم إذا تم الحصول عليه
            if msg_data.get('customer_name') and not conversation.customer_name:
                conversation.customer_name = msg_data['customer_name']
                conversation.save()
            
            # حفظ الرسالة
            message = SocialMessage.objects.create(
                conversation=conversation,
                direction='inbound',
                message_type=msg_data.get('message_type', 'text'),
                content=msg_data.get('content', ''),
                media_url=msg_data.get('media_url', ''),
                platform_message_id=msg_data.get('message_id', f"{platform}_{timezone.now().timestamp()}")
            )
            
            # تحديث المحادثة
            conversation.messages_count += 1
            conversation.last_message_at = timezone.now()
            conversation.save()
            
            # معالجة AI مباشرة (بدون n8n)
            if config and config.is_active and msg_data.get('content'):
                try:
                    from .ai_handler import process_message_with_ai
                    ai_result = process_message_with_ai(conversation, msg_data.get('content', ''))
                    
                    if ai_result and ai_result.get('response'):
                        # حفظ رد الـ AI
                        ai_message = SocialMessage.objects.create(
                            conversation=conversation,
                            direction='outbound',
                            message_type='text',
                            content=ai_result['response'],
                            platform_message_id=f"ai_{platform}_{timezone.now().timestamp()}",
                            ai_intent=ai_result.get('intent', '')
                        )
                        
                        # إرسال الرد للمستخدم
                        send_success = send_social_reply(conversation, ai_result['response'])
                        ai_message.delivered = send_success
                        ai_message.save()
                        
                        logger.info(f"AI response sent for {platform}: {send_success}")
                except Exception as e:
                    logger.error(f"AI processing error: {str(e)}")
            
            # إرسال للـ n8n إذا كان مُعداً (اختياري - كـ backup)
            elif config and config.n8n_webhook_url:
                try:
                    send_to_n8n(config.n8n_webhook_url, {
                        'platform': platform,
                        'conversation_id': conversation.id,
                        'message_id': message.id,
                        'sender_id': msg_data['platform_user_id'],
                        'sender_name': conversation.customer_name,
                        'message_type': message.message_type,
                        'content': message.content,
                        'media_url': message.media_url,
                        'timestamp': timezone.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Failed to send to n8n: {str(e)}")
            
            saved.append({
                'conversation_id': conversation.id,
                'message_id': message.id
            })
            
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}", exc_info=True)
    
    return saved


def get_facebook_user_info(user_id, access_token):
    """جلب معلومات المستخدم من Facebook Graph API"""
    try:
        url = f"https://graph.facebook.com/{user_id}"
        params = {
            'fields': 'name,first_name,last_name,profile_pic',
            'access_token': access_token
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error getting Facebook user info: {str(e)}")
    return None


def get_instagram_user_info(user_id, access_token):
    """جلب معلومات المستخدم من Instagram Graph API"""
    try:
        url = f"https://graph.facebook.com/{user_id}"
        params = {
            'fields': 'name,username',
            'access_token': access_token
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error getting Instagram user info: {str(e)}")
    return None


def send_to_n8n(webhook_url, data):
    """إرسال البيانات لـ n8n"""
    try:
        response = requests.post(
            webhook_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        logger.info(f"Sent to n8n: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending to n8n: {str(e)}")
        return False


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def social_callback(request):
    """
    Callback موحد من n8n بعد معالجة الرسالة بالـ AI
    """
    try:
        data = request.data
        logger.info(f"Received social callback: {data}")
        
        conversation_id = data.get('conversation_id')
        platform = data.get('platform', 'whatsapp')
        ai_response = data.get('ai_response', '')
        detected_intent = data.get('intent', '')
        extracted_products = data.get('products', [])
        sentiment = data.get('sentiment', '')
        conversion_score = float(data.get('conversion_score', 0.0))
        should_send = data.get('send_reply', True)
        
        # الحصول على المحادثة
        try:
            conversation = SocialConversation.objects.get(id=conversation_id)
        except SocialConversation.DoesNotExist:
            return Response({'error': 'المحادثة غير موجودة'}, status=404)
        
        # تحديث المحادثة
        if extracted_products:
            existing = conversation.interested_products or []
            conversation.interested_products = list(set(existing + extracted_products))
        
        if sentiment:
            conversation.ai_sentiment = sentiment
        
        if conversion_score > conversation.conversion_probability:
            conversation.conversion_probability = conversion_score
        
        conversation.save()
        
        # حفظ رد الـ AI كرسالة صادرة
        outbound_message = SocialMessage.objects.create(
            conversation=conversation,
            direction='outbound',
            message_type='text',
            content=ai_response,
            platform_message_id=f"ai_{platform}_{timezone.now().timestamp()}",
            ai_intent=detected_intent
        )
        
        # إرسال الرد للمستخدم
        if should_send and ai_response:
            send_success = send_social_reply(conversation, ai_response)
            outbound_message.delivered = send_success
            outbound_message.save()
        
        # إنشاء عميل تلقائياً إذا كان التحويل محتمل
        config = SocialPlatformConfig.objects.filter(platform=platform, is_active=True).first()
        if config and config.auto_create_customer and conversion_score >= 0.5:
            if not conversation.customer:
                customer = Customer.objects.create(
                    name=conversation.customer_name or f"عميل {platform} {conversation.platform_user_id}",
                    phone=conversation.phone_number or '',
                    source=platform.title(),
                    notes=f"محادثة {platform} - {conversation.messages_count} رسالة"
                )
                conversation.customer = customer
                
                # إنشاء فرصة بيع
                if config.auto_create_opportunity and conversation.interested_products:
                    opportunity = Opportunity.objects.create(
                        customer=customer,
                        title=f"فرصة من {platform.title()} - {customer.name}",
                        description=f"منتجات مهتم بها: {', '.join(conversation.interested_products)}",
                        stage='مبدئي',
                        probability=min(conversion_score * 100, 100),
                        source=platform.title()
                    )
                    conversation.opportunity = opportunity
                
                conversation.status = 'converted'
                conversation.save()
        
        return Response({
            'success': True,
            'message': 'تم معالجة الرد بنجاح',
            'conversation_id': conversation.id,
            'reply_sent': should_send
        })
        
    except Exception as e:
        logger.error(f"Error in social callback: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)


def send_social_reply(conversation, message_text):
    """إرسال رد للمستخدم على المنصة المناسبة"""
    try:
        config = SocialPlatformConfig.objects.filter(
            platform=conversation.platform, 
            is_active=True
        ).first()
        
        if not config:
            logger.error(f"No config found for platform: {conversation.platform}")
            return False
        
        if conversation.platform == 'whatsapp':
            return send_whatsapp_reply(conversation, message_text, config)
        elif conversation.platform == 'facebook':
            return send_facebook_reply(conversation, message_text, config)
        elif conversation.platform == 'instagram':
            return send_instagram_reply(conversation, message_text, config)
        
        return False
        
    except Exception as e:
        logger.error(f"Error sending reply: {str(e)}", exc_info=True)
        return False


def send_whatsapp_reply(conversation, message_text, config):
    """إرسال رسالة عبر WhatsApp Business API"""
    try:
        url = f"https://graph.facebook.com/v18.0/{config.phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {config.page_access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': conversation.phone_number or conversation.platform_user_id,
            'type': 'text',
            'text': {'body': message_text}
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        logger.info(f"WhatsApp send response: {response.status_code} - {response.text[:200]}")
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error sending WhatsApp: {str(e)}")
        return False


def send_facebook_reply(conversation, message_text, config):
    """إرسال رسالة عبر Facebook Messenger API"""
    try:
        url = f"https://graph.facebook.com/v18.0/me/messages"
        
        params = {'access_token': config.page_access_token}
        
        payload = {
            'recipient': {'id': conversation.platform_user_id},
            'message': {'text': message_text}
        }
        
        response = requests.post(url, params=params, json=payload, timeout=30)
        logger.info(f"Facebook send response: {response.status_code} - {response.text[:200]}")
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error sending Facebook: {str(e)}")
        return False


def send_instagram_reply(conversation, message_text, config):
    """إرسال رسالة عبر Instagram DM API"""
    try:
        url = f"https://graph.facebook.com/v18.0/me/messages"
        
        params = {'access_token': config.page_access_token}
        
        payload = {
            'recipient': {'id': conversation.platform_user_id},
            'message': {'text': message_text}
        }
        
        response = requests.post(url, params=params, json=payload, timeout=30)
        logger.info(f"Instagram send response: {response.status_code} - {response.text[:200]}")
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error sending Instagram: {str(e)}")
        return False


@api_view(['GET'])
@permission_classes([AllowAny])
def social_ai_context(request, platform=None):
    """
    الحصول على السياق الكامل للـ AI لمنصة معينة
    """
    try:
        # معلومات المنتجات
        products = ProductKnowledgeBase.objects.filter(is_active=True)
        products_data = ProductKnowledgeSerializer(products, many=True).data
        
        # إعدادات المنصة
        config = None
        if platform:
            config = SocialPlatformConfig.objects.filter(platform=platform, is_active=True).first()
        
        if not config:
            config = SocialPlatformConfig.objects.filter(is_active=True).first()
        
        system_prompt = config.system_prompt if config else "أنت مساعد مبيعات ذكي"
        
        context = {
            'platform': platform or 'all',
            'system_prompt': system_prompt,
            'products': products_data,
            'products_count': len(products_data),
            'timestamp': timezone.now().isoformat()
        }
        
        return Response(context)
        
    except Exception as e:
        logger.error(f"Error getting social AI context: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)


class SocialConversationViewSet(viewsets.ModelViewSet):
    """
    إدارة محادثات السوشيال ميديا
    """
    queryset = SocialConversation.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = SocialConversationSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # فلترة حسب المنصة
        platform = self.request.query_params.get('platform')
        if platform:
            qs = qs.filter(platform=platform)
        
        # فلترة حسب الحالة
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs
    
    @action(detail=True, methods=['post'])
    def convert_to_customer(self, request, pk=None):
        """تحويل المحادثة إلى عميل في CRM"""
        conversation = self.get_object()
        
        if conversation.customer:
            return Response({
                'message': 'المحادثة مرتبطة بعميل بالفعل',
                'customer_id': conversation.customer.id
            })
        
        customer = Customer.objects.create(
            name=conversation.customer_name or f"عميل {conversation.platform}",
            phone=conversation.phone_number,
            source=conversation.get_platform_display(),
            notes=f"محادثة {conversation.platform} - {conversation.messages_count} رسالة"
        )
        
        conversation.customer = customer
        conversation.status = 'converted'
        conversation.save()
        
        return Response({
            'message': 'تم التحويل بنجاح',
            'customer_id': customer.id
        })
