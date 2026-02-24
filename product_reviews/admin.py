"""
Admin panel لنظام المراجعات والتقييمات
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import ProductReview, ReviewImage, ReviewVideo, ReviewHelpfulness, MerchantReply, ReviewReport


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    fields = ['image', 'caption']


class ReviewVideoInline(admin.TabularInline):
    model = ReviewVideo
    extra = 0
    fields = ['video', 'thumbnail', 'duration']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = [
        'get_stars',
        'product',
        'user',
        'status_badge',
        'verified_badge',
        'helpful_count',
        'created_at'
    ]
    list_filter = ['status', 'rating', 'verified_purchase', 'created_at']
    search_fields = ['product__name', 'user__username', 'title', 'review_text']
    readonly_fields = ['created_at', 'updated_at', 'approved_at', 'approved_by', 'helpful_count', 'not_helpful_count']
    date_hierarchy = 'created_at'
    
    inlines = [ReviewImageInline, ReviewVideoInline]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('product', 'user', 'verified_purchase', 'purchase_date')
        }),
        ('التقييم', {
            'fields': ('rating', 'title', 'review_text')
        }),
        ('تقييمات تفصيلية', {
            'fields': ('quality_rating', 'value_rating', 'delivery_rating'),
            'classes': ('collapse',)
        }),
        ('الحالة', {
            'fields': ('status', 'admin_notes', 'rejection_reason', 'approved_at', 'approved_by')
        }),
        ('التفاعل', {
            'fields': ('helpful_count', 'not_helpful_count'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_stars(self, obj):
        stars = '⭐' * obj.rating
        return format_html('<span style="font-size: 16px;">{}</span>', stars)
    get_stars.short_description = 'التقييم'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'الحالة'
    
    def verified_badge(self, obj):
        if obj.verified_purchase:
            return format_html('<span style="color: #28a745;">✅ شراء موثق</span>')
        return format_html('<span style="color: #6c757d;">❌</span>')
    verified_badge.short_description = 'موثق'
    
    actions = ['approve_reviews', 'reject_reviews']
    
    def approve_reviews(self, request, queryset):
        from django.utils import timezone
        for review in queryset:
            review.approve(request.user)
        self.message_user(request, f'تم الموافقة على {queryset.count()} مراجعة')
    approve_reviews.short_description = '✅ الموافقة على المراجعات المحددة'
    
    def reject_reviews(self, request, queryset):
        for review in queryset:
            review.reject('تم الرفض بواسطة الإدارة', request.user)
        self.message_user(request, f'تم رفض {queryset.count()} مراجعة')
    reject_reviews.short_description = '❌ رفض المراجعات المحددة'


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ['review', 'caption', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['review__product__name', 'caption']


@admin.register(ReviewVideo)
class ReviewVideoAdmin(admin.ModelAdmin):
    list_display = ['review', 'duration', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['review__product__name']


@admin.register(MerchantReply)
class MerchantReplyAdmin(admin.ModelAdmin):
    list_display = ['review', 'replied_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['review__product__name', 'reply_text']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ['review', 'reason', 'reported_by', 'is_resolved', 'created_at']
    list_filter = ['reason', 'is_resolved', 'created_at']
    search_fields = ['review__product__name', 'description']
    readonly_fields = ['created_at', 'resolved_at']
    
    actions = ['mark_as_resolved']
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_resolved=True, resolved_at=timezone.now(), resolved_by=request.user)
        self.message_user(request, f'تم تحديد {queryset.count()} بلاغ كمعالج')
    mark_as_resolved.short_description = '✅ تحديد كمعالج'
