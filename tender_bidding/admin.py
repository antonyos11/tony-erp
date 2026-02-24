from django.contrib import admin
from .models import Tender, Bid, BidComparison, TenderEvaluation, TenderPerformance


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'title', 'direction', 'tender_type', 'status',
                    'submission_deadline', 'estimated_value', 'created_at']
    list_filter = ['status', 'direction', 'tender_type', 'published_date']
    search_fields = ['reference_number', 'title', 'issuing_organization']
    readonly_fields = ['winning_bid', 'award_amount']


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['tender', 'bidder_name', 'bid_amount', 'status', 'total_score', 'rank', 'submitted_at']
    list_filter = ['status', 'submitted_at']
    search_fields = ['bidder_name', 'bidder_company', 'tender__reference_number']
    readonly_fields = ['total_score', 'rank']


@admin.register(BidComparison)
class BidComparisonAdmin(admin.ModelAdmin):
    list_display = ['tender', 'name', 'recommended_bid', 'comparison_date', 'approved_by']
    list_filter = ['comparison_date', 'approved_at']
    search_fields = ['tender__reference_number', 'name']


@admin.register(TenderEvaluation)
class TenderEvaluationAdmin(admin.ModelAdmin):
    list_display = ['bid', 'evaluator', 'final_score', 'is_recommended', 'evaluation_date']
    list_filter = ['is_recommended', 'evaluation_date']
    search_fields = ['bid__bidder_name', 'tender__reference_number']
    readonly_fields = ['final_score']


@admin.register(TenderPerformance)
class TenderPerformanceAdmin(admin.ModelAdmin):
    list_display = ['tender', 'winning_bid', 'completion_percentage', 'overall_rating',
                    'would_work_again', 'created_at']
    list_filter = ['would_work_again', 'quality_rating']
    search_fields = ['tender__reference_number']
    readonly_fields = ['overall_rating']
