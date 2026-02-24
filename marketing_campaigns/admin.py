from django.contrib import admin
from .models import CustomerSegment, Campaign, CampaignMessage, ABTest, CampaignROI


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'segment_type', 'customer_count', 'total_revenue', 'is_active', 'created_at']
    list_filter = ['segment_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['customer_count', 'total_revenue', 'average_order_value']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign_type', 'status', 'start_date', 'end_date', 
                    'budget', 'actual_cost', 'roi', 'conversion_rate', 'created_at']
    list_filter = ['campaign_type', 'status', 'start_date', 'created_at']
    search_fields = ['name', 'goal_description']
    readonly_fields = ['total_sent', 'total_delivered', 'total_opened', 'total_clicked',
                      'total_conversions', 'total_revenue', 'roi', 'conversion_rate', 'cost_per_conversion']
    filter_horizontal = ['target_segments']


@admin.register(CampaignMessage)
class CampaignMessageAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'customer', 'message_type', 'status', 'sent_at', 
                    'conversion_value', 'created_at']
    list_filter = ['message_type', 'status', 'sent_at', 'created_at']
    search_fields = ['campaign__name', 'customer__name', 'content']
    readonly_fields = ['sent_at', 'delivered_at', 'opened_at', 'clicked_at', 'converted_at']


@admin.register(ABTest)
class ABTestAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign', 'variant_a_conversion_rate', 'variant_b_conversion_rate',
                    'winner', 'confidence_level', 'is_completed', 'created_at']
    list_filter = ['is_active', 'is_completed', 'winner', 'created_at']
    search_fields = ['name', 'campaign__name']
    readonly_fields = ['variant_a_conversion_rate', 'variant_b_conversion_rate', 
                      'winner', 'confidence_level']


@admin.register(CampaignROI)
class CampaignROIAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'total_cost', 'total_revenue', 'net_profit', 
                    'roi_percentage', 'customer_acquisition_cost', 'created_at']
    list_filter = ['created_at']
    search_fields = ['campaign__name']
    readonly_fields = ['total_cost', 'total_revenue', 'net_profit', 'roi_percentage']
