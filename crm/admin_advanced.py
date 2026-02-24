"""
تسجيل نماذج CRM المتقدمة في لوحة التحكم
"""

from django.contrib import admin

from crm.models_advanced import (
    FollowUpRule,
    FollowUpLog,
    LeadScore,
    SupportSLA,
)


@admin.register(FollowUpRule)
class FollowUpRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'trigger', 'days_after', 'action',
        'is_active', 'execution_count', 'last_executed'
    ]
    list_filter = ['trigger', 'action', 'is_active']
    search_fields = ['name']
    list_editable = ['is_active']


@admin.register(FollowUpLog)
class FollowUpLogAdmin(admin.ModelAdmin):
    list_display = ['rule', 'customer', 'result', 'executed_at']
    list_filter = ['result', 'rule']
    readonly_fields = ['rule', 'customer', 'executed_at', 'result', 'details']


@admin.register(LeadScore)
class LeadScoreAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'grade', 'total_score',
        'demographic_score', 'behavior_score',
        'financial_score', 'engagement_score',
        'manual_adjustment', 'last_calculated'
    ]
    list_filter = ['grade']
    search_fields = ['customer__first_name', 'customer__last_name', 'customer__company_name']
    readonly_fields = ['last_calculated']
    list_editable = ['manual_adjustment']


@admin.register(SupportSLA)
class SupportSLAAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'priority', 'first_response_hours',
        'resolution_hours', 'escalation_after_hours', 'is_active'
    ]
    list_filter = ['is_active', 'priority']
    list_editable = ['is_active']
