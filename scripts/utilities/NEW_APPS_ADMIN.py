"""
إدارة الإشعارات المتقدمة والمراسلات والذكاء الاصطناعي والملكية الفكرية
Advanced Admin Interfaces
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

# ============ Advanced Notifications Admin ============
from advanced_notifications.models import (
    MessageTemplate, NotificationSchedule, SentNotification, 
    NotificationPreference, SMSProvider, WhatsAppProvider
)

@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel', 'trigger_event', 'is_active']
    list_filter = ['channel', 'trigger_event', 'is_active']
    search_fields = ['name', 'body']

@admin.register(NotificationSchedule)
class NotificationScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'schedule_type', 'is_active']
    list_filter = ['schedule_type', 'is_active']

@admin.register(SentNotification)
class SentNotificationAdmin(admin.ModelAdmin):
    list_display = ['template', 'recipient_email', 'status', 'sent_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['id', 'created_at']

@admin.register(SMSProvider)
class SMSProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'priority']
    list_filter = ['is_active']

@admin.register(WhatsAppProvider)
class WhatsAppProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']

# ============ Treasury Management Admin ============
from treasury_management.models import CashPosition, CashFlow, Investment, TreasuryTarget

@admin.register(CashPosition)
class CashPositionAdmin(admin.ModelAdmin):
    list_display = ['position_date', 'total_liquidity', 'net_position', 'liquidity_ratio']
    readonly_fields = ['id', 'created_at']

@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):
    list_display = ['forecast_date', 'period_type', 'opening_balance', 'closing_balance']
    list_filter = ['period_type', 'forecast_date']

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['investment_id', 'investment_type', 'principal_amount', 'status']
    list_filter = ['investment_type', 'status']
    search_fields = ['investment_id', 'description']

@admin.register(TreasuryTarget)
class TreasuryTargetAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'target_liquidity', 'end_date']
    list_filter = ['status']

# ============ Advanced CRM Admin ============
from advanced_crm.models import Opportunity, SalesStage, ActivityLog, ForecastRecord

@admin.register(SalesStage)
class SalesStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'sequence', 'conversion_probability']
    ordering = ['sequence']

@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ['opportunity_id', 'title', 'stage', 'status', 'expected_value']
    list_filter = ['status', 'stage', 'expected_close_date']
    search_fields = ['opportunity_id', 'title']
    readonly_fields = ['id', 'weighted_value', 'success_probability', 'created_at']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['opportunity', 'activity_type', 'activity_date', 'follow_up_required']
    list_filter = ['activity_type', 'activity_date', 'follow_up_required']
    search_fields = ['opportunity__title', 'subject']

@admin.register(ForecastRecord)
class ForecastRecordAdmin(admin.ModelAdmin):
    list_display = ['forecast_date', 'period', 'expected_revenue', 'accuracy_percentage']
    list_filter = ['forecast_date']

# ============ Business Intelligence Admin ============
from business_intelligence.models import Dashboard, Widget, Forecast, PredictiveAnalysis, Report

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_public', 'is_default']
    list_filter = ['is_public', 'is_default']
    filter_horizontal = ['allowed_users']

@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ['dashboard', 'title', 'widget_type']
    list_filter = ['widget_type']

@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ['forecast_type', 'period_end', 'predicted_value', 'confidence_level']
    list_filter = ['forecast_type', 'period_end']

@admin.register(PredictiveAnalysis)
class PredictiveAnalysisAdmin(admin.ModelAdmin):
    list_display = ['analysis_type', 'entity_type', 'score', 'analysis_date']
    list_filter = ['analysis_type']

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'frequency', 'is_active']
    list_filter = ['report_type', 'frequency', 'is_active']
    filter_horizontal = ['recipients']

# ============ Correspondence Management Admin ============
from correspondence_management.models import (
    Correspondence, CorrespondenceThread, CorrespondenceArchive, CorrespondenceTemplate
)

@admin.register(Correspondence)
class CorrespondenceAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'correspondence_type', 'subject', 'status', 'received_date']
    list_filter = ['status', 'correspondence_type', 'received_date', 'priority']
    search_fields = ['reference_number', 'subject', 'sender', 'recipient']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(CorrespondenceThread)
class CorrespondenceThreadAdmin(admin.ModelAdmin):
    list_display = ['original_correspondence', 'is_resolved', 'resolution_date']
    list_filter = ['is_resolved']

@admin.register(CorrespondenceArchive)
class CorrespondenceArchiveAdmin(admin.ModelAdmin):
    list_display = ['correspondence', 'archive_date', 'access_restricted']
    filter_horizontal = ['allowed_users']

@admin.register(CorrespondenceTemplate)
class CorrespondenceTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    list_filter = ['category']

# ============ Intellectual Property Admin ============
from intellectual_property.models import Patent, Trademark, CopyrightWork, IPLicense

@admin.register(Patent)
class PatentAdmin(admin.ModelAdmin):
    list_display = ['patent_number', 'title', 'patent_type', 'status', 'expiry_date']
    list_filter = ['status', 'patent_type', 'expiry_date']
    search_fields = ['patent_number', 'title', 'inventor']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(Trademark)
class TrademarkAdmin(admin.ModelAdmin):
    list_display = ['trademark_number', 'name', 'status', 'expiry_date']
    list_filter = ['status']
    search_fields = ['trademark_number', 'name']

@admin.register(CopyrightWork)
class CopyrightWorkAdmin(admin.ModelAdmin):
    list_display = ['title', 'work_type', 'author', 'expiry_date']
    list_filter = ['work_type']
    search_fields = ['title', 'author']

@admin.register(IPLicense)
class IPLicenseAdmin(admin.ModelAdmin):
    list_display = ['license_number', 'license_type', 'licensor', 'licensee', 'end_date']
    list_filter = ['license_type']
    search_fields = ['license_number', 'licensor', 'licensee']
