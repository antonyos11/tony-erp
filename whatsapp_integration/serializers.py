from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import (
    WhatsAppConfig, WhatsAppConversation, WhatsAppMessage,
    WhatsAppTemplate, ProductCatalog, AutoReplyRule
)
from inventory.models import Product
from crm.models import Customer


class ProductCatalogSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(
        source='product.sale_price', max_digits=15, decimal_places=2, read_only=True
    )
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    stock_quantity = serializers.IntegerField(source='product.stock_quantity', read_only=True)
    
    class Meta:
        model = ProductCatalog
        fields = [
            'id', 'product', 'product_name', 'product_price', 'product_sku',
            'stock_quantity', 'whatsapp_description', 'whatsapp_image_url',
            'keywords', 'is_available_on_whatsapp', 'quick_replies'
        ]


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppMessage
        fields = [
            'id', 'whatsapp_message_id', 'direction', 'message_type',
            'content', 'media_url', 'detected_intent', 'confidence',
            'is_read', 'sent_at', 'delivered_at', 'read_at'
        ]
        ref_name = 'WAIntegrationMessage'


class WhatsAppConversationSerializer(serializers.ModelSerializer):
    messages = WhatsAppMessageSerializer(many=True, read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    
    class Meta:
        model = WhatsAppConversation
        fields = [
            'id', 'phone_number', 'customer_name', 'customer',
            'customer_email', 'status', 'assigned_to',
            'last_message_at', 'created_at', 'auto_registered', 'messages'
        ]
        ref_name = 'WAIntegrationConversation'


class WhatsAppConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = WhatsAppConversation
        fields = [
            'id', 'phone_number', 'customer_name', 'customer',
            'status', 'last_message_at', 'last_message', 'unread_count'
        ]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_last_message(self, obj):
        last = obj.messages.last()
        if last:
            return {
                'content': last.content[:100],
                'direction': last.direction,
                'sent_at': last.sent_at
            }
        return None
    
    @extend_schema_field(serializers.IntegerField())
    def get_unread_count(self, obj):
        return obj.messages.filter(is_read=False, direction='incoming').count()


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppTemplate
        fields = [
            'id', 'name', 'category', 'header', 'body', 'footer',
            'buttons', 'variables', 'is_active'
        ]


class AutoReplyRuleSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='response_template.name', read_only=True)
    
    class Meta:
        model = AutoReplyRule
        fields = [
            'id', 'name', 'priority', 'trigger_text', 'match_type',
            'action', 'response_template', 'template_name',
            'response_text', 'webhook_url', 'is_active'
        ]


# ============ n8n Integration Serializers ============

class N8nWebhookSerializer(serializers.Serializer):
    """Serializer للرسائل الواردة من n8n"""
    phone = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    message = serializers.CharField()
    message_id = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateTimeField(required=False)


class N8nProductSearchSerializer(serializers.Serializer):
    """Serializer للبحث عن المنتجات"""
    query = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    max_results = serializers.IntegerField(default=5, min_value=1, max_value=20)


class N8nProductResponseSerializer(serializers.Serializer):
    """Serializer لاستجابة المنتجات"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    sku = serializers.CharField()
    description = serializers.CharField()
    price = serializers.DecimalField(max_digits=15, decimal_places=2)
    stock = serializers.IntegerField()
    category = serializers.CharField()
    image_url = serializers.URLField(allow_blank=True)
    whatsapp_text = serializers.CharField()  # نص جاهز للإرسال على واتساب


class N8nCustomerCreateSerializer(serializers.Serializer):
    """Serializer لإنشاء عميل جديد من واتساب"""
    phone = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    source = serializers.CharField(default='whatsapp')
    notes = serializers.CharField(required=False, allow_blank=True)
    
    # Optional fields
    company = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)


class N8nCustomerResponseSerializer(serializers.ModelSerializer):
    """Serializer لاستجابة العميل"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_code', 'full_name', 'phone', 'mobile',
            'email', 'company_name', 'city', 'status', 'created_at'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class N8nSendMessageSerializer(serializers.Serializer):
    """Serializer لإرسال رسالة"""
    phone = serializers.CharField(max_length=20)
    message = serializers.CharField()
    template_id = serializers.IntegerField(required=False)
    variables = serializers.DictField(required=False, default=dict)
