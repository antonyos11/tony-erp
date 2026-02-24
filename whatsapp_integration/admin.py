from django.contrib import admin
from .models import (
    WhatsAppConfig, WhatsAppConversation, WhatsAppMessage,
    WhatsAppTemplate, ProductCatalog, AutoReplyRule
)


@admin.register(WhatsAppConfig)
class WhatsAppConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'use_ai_responses', 'updated_at']
    fieldsets = (
        ('عام', {
            'fields': ('name', 'is_active')
        }),
        ('إعدادات n8n', {
            'fields': ('n8n_webhook_url', 'n8n_api_key'),
            'classes': ('collapse',)
        }),
        ('WhatsApp Business API', {
            'fields': ('whatsapp_phone_id', 'whatsapp_token', 'whatsapp_verify_token'),
            'classes': ('collapse',)
        }),
        ('الرسائل التلقائية', {
            'fields': ('welcome_message', 'product_inquiry_response', 'order_confirmation')
        }),
        ('الذكاء الاصطناعي', {
            'fields': ('use_ai_responses', 'ai_model', 'ai_api_key'),
            'classes': ('collapse',)
        }),
    )


class WhatsAppMessageInline(admin.TabularInline):
    model = WhatsAppMessage
    extra = 0
    readonly_fields = ['direction', 'content', 'detected_intent', 'sent_at']
    can_delete = False


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'customer_name', 'customer', 'status', 'assigned_to', 'last_message_at']
    list_filter = ['status', 'auto_registered', 'assigned_to']
    search_fields = ['phone_number', 'customer_name']
    readonly_fields = ['auto_registered', 'created_at', 'last_message_at']
    inlines = [WhatsAppMessageInline]
    
    actions = ['mark_as_resolved', 'mark_as_closed']
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
    mark_as_resolved.short_description = 'تحديد كمحلولة'
    
    def mark_as_closed(self, request, queryset):
        queryset.update(status='closed')
    mark_as_closed.short_description = 'إغلاق المحادثات'


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'direction', 'content_preview', 'detected_intent', 'sent_at']
    list_filter = ['direction', 'message_type', 'detected_intent']
    search_fields = ['content']
    readonly_fields = ['whatsapp_message_id', 'sent_at', 'delivered_at', 'read_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'المحتوى'


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'body']


@admin.register(ProductCatalog)
class ProductCatalogAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_available_on_whatsapp', 'keywords']
    list_filter = ['is_available_on_whatsapp']
    search_fields = ['product__name', 'keywords']
    autocomplete_fields = ['product']


@admin.register(AutoReplyRule)
class AutoReplyRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'trigger_text', 'match_type', 'action', 'priority', 'is_active']
    list_filter = ['match_type', 'action', 'is_active']
    search_fields = ['name', 'trigger_text']
    ordering = ['-priority']
