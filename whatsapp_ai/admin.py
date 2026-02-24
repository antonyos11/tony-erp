from django.contrib import admin
from .models import (
    WhatsAppConversation, WhatsAppMessage,
    ProductKnowledgeBase, WhatsAppConfiguration,
    SocialConversation, SocialMessage, SocialPlatformConfig
)


# ==============================================
#   إعدادات منصات السوشيال ميديا (الموحدة)
# ==============================================

@admin.register(SocialPlatformConfig)
class SocialPlatformConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform', 'ai_provider', 'auto_create_customer', 'is_active']
    list_filter = ['platform', 'is_active', 'ai_provider']
    search_fields = ['name']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'platform', 'is_active')
        }),
        ('إعدادات Meta/Facebook API', {
            'fields': ('page_id', 'page_access_token', 'app_secret', 'verify_token'),
            'description': 'إعدادات مشتركة لـ WhatsApp و Facebook و Instagram'
        }),
        ('إعدادات WhatsApp (فقط للواتساب)', {
            'fields': ('phone_number_id', 'whatsapp_business_account_id'),
            'classes': ('collapse',)
        }),
        ('إعدادات Instagram (فقط للانستجرام)', {
            'fields': ('instagram_account_id',),
            'classes': ('collapse',)
        }),
        ('إعدادات n8n', {
            'fields': ('n8n_webhook_url',)
        }),
        ('إعدادات الذكاء الصناعي', {
            'fields': ('ai_provider', 'ai_api_key', 'ai_model', 'system_prompt')
        }),
        ('إعدادات CRM التلقائية', {
            'fields': ('auto_create_customer', 'auto_create_opportunity')
        }),
        ('ساعات العمل', {
            'fields': ('business_hours_enabled', 'business_hours_start', 
                      'business_hours_end', 'outside_hours_message'),
            'classes': ('collapse',)
        }),
    )


class SocialMessageInline(admin.TabularInline):
    model = SocialMessage
    extra = 0
    readonly_fields = ['direction', 'message_type', 'content', 'created_at', 
                      'platform_message_id', 'ai_intent', 'delivered', 'read']
    can_delete = False
    max_num = 30
    ordering = ['-created_at']


@admin.register(SocialConversation)
class SocialConversationAdmin(admin.ModelAdmin):
    list_display = ['platform', 'customer_name', 'platform_user_id', 'status', 
                   'messages_count', 'conversion_probability', 'last_message_at']
    list_filter = ['platform', 'status', 'ai_sentiment', 'created_at']
    search_fields = ['platform_user_id', 'customer_name', 'phone_number', 'customer__name']
    readonly_fields = ['first_message_at', 'last_message_at', 'messages_count', 
                      'created_at', 'updated_at']
    inlines = [SocialMessageInline]
    
    fieldsets = (
        ('معلومات المنصة', {
            'fields': ('platform', 'platform_user_id', 'phone_number', 'customer_name', 'profile_picture', 'status')
        }),
        ('ربط CRM', {
            'fields': ('customer', 'opportunity')
        }),
        ('الاهتمامات', {
            'fields': ('interested_products', 'requested_categories', 'budget_range', 'notes')
        }),
        ('تحليل الذكاء الصناعي', {
            'fields': ('conversation_summary', 'ai_sentiment', 'conversion_probability')
        }),
        ('معلومات إحصائية', {
            'fields': ('messages_count', 'first_message_at', 'last_message_at', 
                      'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['convert_to_customers', 'mark_as_closed']
    
    def convert_to_customers(self, request, queryset):
        """تحويل المحادثات المحددة إلى عملاء"""
        from crm.models import Customer
        
        converted = 0
        for conv in queryset.filter(customer__isnull=True):
            customer = Customer.objects.create(
                name=conv.customer_name or f"عميل {conv.get_platform_display()}",
                phone=conv.phone_number or '',
                source=conv.get_platform_display(),
                notes=f"محادثة {conv.platform} - {conv.messages_count} رسالة"
            )
            conv.customer = customer
            conv.status = 'converted'
            conv.save()
            converted += 1
        
        self.message_user(request, f"تم تحويل {converted} محادثة إلى عملاء")
    convert_to_customers.short_description = "تحويل إلى عملاء CRM"
    
    def mark_as_closed(self, request, queryset):
        queryset.update(status='closed')
        self.message_user(request, f"تم إغلاق {queryset.count()} محادثة")
    mark_as_closed.short_description = "إغلاق المحادثات"


@admin.register(SocialMessage)
class SocialMessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'direction', 'message_type', 'content_preview', 
                   'delivered', 'read', 'created_at']
    list_filter = ['conversation__platform', 'direction', 'message_type', 'delivered', 'read']
    search_fields = ['content', 'conversation__customer_name', 'conversation__platform_user_id']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'المحتوى'


# ==============================================
#   الإعدادات القديمة (للتوافقية)
# ==============================================

@admin.register(WhatsAppConfiguration)
class WhatsAppConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'ai_provider', 'auto_create_customer', 'is_active']
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'is_active')
        }),
        ('إعدادات WhatsApp API', {
            'fields': ('whatsapp_api_url', 'whatsapp_api_token', 'phone_number_id')
        }),
        ('إعدادات n8n', {
            'fields': ('n8n_webhook_url',)
        }),
        ('إعدادات الذكاء الصناعي', {
            'fields': ('ai_provider', 'ai_api_key', 'ai_model', 'system_prompt')
        }),
        ('إعدادات CRM التلقائية', {
            'fields': ('auto_create_customer', 'auto_create_opportunity', 'default_opportunity_stage')
        }),
        ('ساعات العمل', {
            'fields': ('business_hours_enabled', 'business_hours_start', 
                      'business_hours_end', 'outside_hours_message')
        }),
    )


class WhatsAppMessageInline(admin.TabularInline):
    model = WhatsAppMessage
    extra = 0
    readonly_fields = ['direction', 'message_type', 'content', 'created_at', 
                      'whatsapp_message_id', 'ai_intent']
    can_delete = False
    max_num = 20
    ordering = ['-created_at']


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'customer_name', 'status', 'messages_count', 
                   'conversion_probability', 'last_message_at']
    list_filter = ['status', 'ai_sentiment', 'created_at']
    search_fields = ['phone_number', 'customer_name', 'customer__name']
    readonly_fields = ['first_message_at', 'last_message_at', 'messages_count', 
                      'created_at', 'updated_at']
    inlines = [WhatsAppMessageInline]
    
    fieldsets = (
        ('معلومات الاتصال', {
            'fields': ('phone_number', 'customer_name', 'status')
        }),
        ('ربط CRM', {
            'fields': ('customer', 'opportunity')
        }),
        ('الاهتمامات', {
            'fields': ('interested_products', 'requested_categories', 'budget_range', 'notes')
        }),
        ('تحليل الذكاء الصناعي', {
            'fields': ('conversation_summary', 'ai_sentiment', 'conversion_probability')
        }),
        ('معلومات إحصائية', {
            'fields': ('messages_count', 'first_message_at', 'last_message_at', 
                      'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['convert_to_customers', 'mark_as_closed']
    
    def convert_to_customers(self, request, queryset):
        """تحويل المحادثات المحددة إلى عملاء"""
        from crm.models import Customer
        
        converted = 0
        for conversation in queryset:
            if not conversation.customer:
                customer = Customer.objects.create(
                    name=conversation.customer_name or f"عميل واتساب {conversation.phone_number}",
                    phone=conversation.phone_number,
                    source='واتساب',
                    notes=conversation.conversation_summary or ''
                )
                conversation.customer = customer
                conversation.status = 'converted'
                conversation.save()
                converted += 1
        
        self.message_user(request, f'تم تحويل {converted} محادثة إلى عملاء')
    
    convert_to_customers.short_description = 'تحويل إلى عملاء في CRM'
    
    def mark_as_closed(self, request, queryset):
        """إغلاق المحادثات"""
        count = queryset.update(status='closed')
        self.message_user(request, f'تم إغلاق {count} محادثة')
    
    mark_as_closed.short_description = 'إغلاق المحادثات'


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'direction', 'message_type', 'content_preview', 
                   'ai_intent', 'created_at']
    list_filter = ['direction', 'message_type', 'ai_intent', 'created_at']
    search_fields = ['content', 'conversation__phone_number', 'whatsapp_message_id']
    readonly_fields = ['created_at', 'whatsapp_message_id']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'المحتوى'


@admin.register(ProductKnowledgeBase)
class ProductKnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'product_code', 'category', 'price', 
                   'in_stock', 'popularity_score', 'is_active']
    list_filter = ['category', 'in_stock', 'is_active']
    search_fields = ['product_name', 'product_code', 'description', 'keywords']
    
    fieldsets = (
        ('معلومات المنتج', {
            'fields': ('product_name', 'product_code', 'category', 'is_active')
        }),
        ('الوصف والمعلومات', {
            'fields': ('description', 'features', 'specifications')
        }),
        ('السعر والتوفر', {
            'fields': ('price', 'currency', 'in_stock', 'stock_quantity')
        }),
        ('معلومات للذكاء الصناعي', {
            'fields': ('keywords', 'common_questions', 'tags')
        }),
        ('إحصائيات', {
            'fields': ('popularity_score', 'times_mentioned', 'times_purchased'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['sync_from_inventory']
    
    def sync_from_inventory(self, request, queryset):
        """مزامنة من المخزون"""
        try:
            from inventory.models import Product
            synced = 0
            
            for product in Product.objects.all():
                obj, created = ProductKnowledgeBase.objects.update_or_create(
                    product_code=product.code,
                    defaults={
                        'product_name': product.name,
                        'description': product.description or f"منتج: {product.name}",
                        'is_active': True
                    }
                )
                synced += 1
            
            self.message_user(request, f'تمت مزامنة {synced} منتج من المخزون')
        except Exception as e:
            self.message_user(request, f'خطأ في المزامنة: {str(e)}', level='error')
    
    sync_from_inventory.short_description = 'مزامنة من المخزون'
