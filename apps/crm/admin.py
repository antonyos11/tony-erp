"""
Admin — CRM
"""
from django.contrib import admin
from apps.crm.models import (
    CustomerGroup, Lead, Interaction, Complaint,
    Task, CustomerRating, SMSLog,
)


@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_percentage', 'credit_limit', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'status', 'priority', 'source', 'assigned_to', 'branch', 'created_at')
    list_filter = ('status', 'source', 'priority', 'branch')
    search_fields = ('name', 'phone', 'company', 'email')
    autocomplete_fields = ['assigned_to', 'branch']
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    date_hierarchy = 'created_at'


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('date', 'interaction_type', 'customer', 'lead', 'handled_by', 'result', 'follow_up_date')
    list_filter = ('interaction_type', 'result', 'is_follow_up_done')
    search_fields = ('subject', 'details', 'customer__name', 'lead__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('complaint_number', 'customer', 'complaint_type', 'severity', 'status', 'date', 'assigned_to')
    list_filter = ('status', 'severity', 'complaint_type', 'branch')
    search_fields = ('complaint_number', 'subject', 'customer__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    date_hierarchy = 'date'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'due_date', 'status', 'priority')
    list_filter = ('status', 'priority')
    search_fields = ('title', 'assigned_to__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'due_date'


@admin.register(CustomerRating)
class CustomerRatingAdmin(admin.ModelAdmin):
    list_display = ('customer', 'grade', 'score', 'total_purchases', 'total_invoices', 'days_since_last_purchase', 'last_updated')
    list_filter = ('grade',)
    search_fields = ('customer__name', 'customer__code')
    readonly_fields = ('last_updated',)


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('phone', 'message_type', 'status', 'sent_at', 'sent_by')
    list_filter = ('message_type', 'status')
    search_fields = ('phone', 'message')
    readonly_fields = ('sent_at',)
