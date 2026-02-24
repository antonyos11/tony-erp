from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import AIAssistantSettings, ChatSession, ChatMessage, FAQ, QuickReply


@admin.register(AIAssistantSettings)
class AIAssistantSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'assistant_type', 'provider', 'is_active', 'updated_at']
    list_filter = ['assistant_type', 'provider', 'is_active']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('id', 'assistant_type', 'name', 'welcome_message', 'is_active')
        }),
        (_('إعدادات AI'), {
            'fields': ('provider', 'api_key', 'model_name', 'system_prompt', 'max_tokens', 'temperature')
        }),
        (_('الميزات'), {
            'fields': ('enable_product_search', 'enable_order_tracking', 'enable_faq')
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['id', 'role', 'content', 'tokens_used', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'assistant_settings', 'is_active', 'started_at', 'get_messages_count']
    list_filter = ['assistant_settings', 'is_active', 'started_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'started_at', 'ended_at', 'user_agent', 'ip_address']
    inlines = [ChatMessageInline]
    
    def get_messages_count(self, obj):
        return obj.messages.count()
    get_messages_count.short_description = _('عدد الرسائل')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'short_content', 'tokens_used', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content']
    readonly_fields = ['id', 'session', 'created_at']
    
    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = _('المحتوى')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'assistant_type', 'category', 'views_count', 'is_active', 'order']
    list_filter = ['assistant_type', 'category', 'is_active']
    search_fields = ['question', 'answer', 'keywords']
    list_editable = ['order', 'is_active']
    readonly_fields = ['id', 'views_count', 'helpful_count', 'created_at', 'updated_at']
    
    def question_short(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_short.short_description = _('السؤال')


@admin.register(QuickReply)
class QuickReplyAdmin(admin.ModelAdmin):
    list_display = ['title', 'assistant_type', 'is_active', 'order']
    list_filter = ['assistant_type', 'is_active']
    search_fields = ['title', 'content']
    list_editable = ['order', 'is_active']
    readonly_fields = ['id']
