from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import WhatsAppConversation, WhatsAppMessage, ProductKnowledgeBase, WhatsAppConfiguration, SocialConversation
from crm.models import Customer, Opportunity


class ProductKnowledgeSerializer(serializers.ModelSerializer):
    """معلومات المنتج للـ AI"""
    
    class Meta:
        model = ProductKnowledgeBase
        fields = [
            'id', 'product_name', 'product_code', 'description',
            'features', 'specifications', 'price', 'currency',
            'keywords', 'common_questions', 'in_stock', 'stock_quantity',
            'category', 'tags', 'popularity_score'
        ]


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    """رسالة واتساب"""
    
    class Meta:
        model = WhatsAppMessage
        fields = [
            'id', 'direction', 'message_type', 'content', 'media_url',
            'whatsapp_message_id', 'ai_intent', 'ai_entities',
            'delivered', 'read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
        ref_name = 'WAAIMessage'


class WhatsAppConversationSerializer(serializers.ModelSerializer):
    """محادثة واتساب"""
    
    messages = WhatsAppMessageSerializer(many=True, read_only=True)
    customer_name_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WhatsAppConversation
        fields = [
            'id', 'phone_number', 'customer_name', 'customer_name_display',
            'customer', 'opportunity', 'status', 'interested_products',
            'requested_categories', 'budget_range', 'notes',
            'first_message_at', 'last_message_at', 'messages_count',
            'conversation_summary', 'ai_sentiment', 'conversion_probability',
            'messages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'first_message_at', 'last_message_at', 
                           'messages_count', 'created_at', 'updated_at']
        ref_name = 'WAAIConversation'
    
    @extend_schema_field(serializers.CharField())
    def get_customer_name_display(self, obj):
        if obj.customer:
            return obj.customer.name
        return obj.customer_name or obj.phone_number


class WhatsAppIncomingMessageSerializer(serializers.Serializer):
    """استقبال رسالة من WhatsApp API"""
    
    from_number = serializers.CharField(max_length=20)
    message_id = serializers.CharField(max_length=200)
    message_type = serializers.CharField(max_length=20, default='text')
    text_body = serializers.CharField(required=False, allow_blank=True)
    media_url = serializers.URLField(required=False, allow_blank=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)


class AIResponseSerializer(serializers.Serializer):
    """استجابة الذكاء الصناعي"""
    
    response_text = serializers.CharField()
    detected_intent = serializers.CharField(required=False, allow_blank=True)
    extracted_products = serializers.ListField(child=serializers.CharField(), required=False)
    sentiment = serializers.CharField(required=False, allow_blank=True)
    suggested_action = serializers.CharField(required=False, allow_blank=True)
    conversion_score = serializers.FloatField(required=False, default=0.0)


class CRMAutoCreateSerializer(serializers.Serializer):
    """بيانات إنشاء عميل وفرصة تلقائياً"""
    
    phone_number = serializers.CharField(max_length=20)
    customer_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    interested_products = serializers.ListField(child=serializers.CharField(), required=False)
    conversation_summary = serializers.CharField(required=False, allow_blank=True)
    conversion_probability = serializers.FloatField(required=False, default=0.0)
    
    def create(self, validated_data):
        """إنشاء عميل وفرصة في CRM"""
        phone = validated_data['phone_number']
        name = validated_data.get('customer_name') or f"عميل واتساب {phone}"
        
        # البحث أو الإنشاء
        customer, created = Customer.objects.get_or_create(
            phone=phone,
            defaults={
                'name': name,
                'source': 'واتساب',
                'notes': validated_data.get('conversation_summary', ''),
            }
        )
        
        # إنشاء فرصة بيع
        opportunity = None
        if validated_data.get('interested_products'):
            opportunity = Opportunity.objects.create(
                customer=customer,
                title=f"فرصة من واتساب - {name}",
                description=f"منتجات مهتم بها: {', '.join(validated_data['interested_products'])}\n\n"
                           f"{validated_data.get('conversation_summary', '')}",
                stage='مبدئي',
                probability=min(validated_data.get('conversion_probability', 0.0) * 100, 100),
                source='واتساب'
            )
        
        return {
            'customer': customer,
            'customer_created': created,
            'opportunity': opportunity
        }


class SocialConversationSerializer(serializers.ModelSerializer):
    """سيريالايزر محادثات السوشيال ميديا"""

    class Meta:
        model = SocialConversation
        fields = [
            'id', 'platform', 'platform_user_id', 'phone_number',
            'customer_name', 'profile_picture',
            'customer', 'opportunity', 'status',
            'interested_products', 'requested_categories',
            'budget_range', 'notes',
            'first_message_at', 'last_message_at', 'messages_count',
        ]
        read_only_fields = ['first_message_at', 'last_message_at', 'messages_count']
        ref_name = 'SocialConversation'
