from django.contrib import admin
from .models import TicketCategory, Ticket, TicketComment, TicketAttachment, KnowledgeBase

@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'sla_hours', 'is_active']
    list_filter = ['is_active']

class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 1

class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 1

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'subject', 'category', 'priority', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['ticket_number', 'subject', 'description']
    inlines = [TicketCommentInline, TicketAttachmentInline]

@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_published', 'view_count']
    list_filter = ['is_published', 'category']
    prepopulated_fields = {'slug': ('title',)}
