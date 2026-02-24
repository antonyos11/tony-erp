from django.contrib import admin
from .models import (
    PricingRule, SmartQuote, ProductionLineRecommendation,
    AutoMaterialRelease, MaterialReleaseItem
)
from .models_extended import (
    Competitor, CompetitorPrice, PricingStrategy, SeasonalPricing,
    PriceHistory, PricingGoal, PriceAlert, PricingSimulation,
    ProductPricingProfile, BundlePricing, BundlePricingItem
)

# تسجيل admin قوائم الأسعار
from .admin_price_list import *  # noqa

# تسجيل admin إصدارات الأسعار
from .admin_versioning import *  # noqa


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'method', 'target_profit_margin', 'use_ai_pricing', 'is_active']
    list_filter = ['method', 'use_ai_pricing', 'is_active']
    search_fields = ['name', 'product_category']
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'product_category', 'method', 'is_active')
        }),
        ('معاملات التسعير', {
            'fields': ('base_cost_multiplier', 'quantity_discount_threshold', 'quantity_discount_rate')
        }),
        ('هامش الربح', {
            'fields': ('min_profit_margin', 'target_profit_margin', 'max_profit_margin')
        }),
        ('معاملات الحجم', {
            'fields': ('size_multiplier_small', 'size_multiplier_medium', 'size_multiplier_large', 'size_multiplier_xlarge')
        }),
        ('معاملات التعقيد', {
            'fields': ('complexity_simple', 'complexity_medium', 'complexity_complex')
        }),
        ('الذكاء الاصطناعي', {
            'fields': ('use_ai_pricing', 'ai_model_version')
        }),
    )


class MaterialReleaseItemInline(admin.TabularInline):
    model = MaterialReleaseItem
    extra = 1
    fields = ['material', 'required_quantity', 'released_quantity', 'unit_cost', 'total_cost']


@admin.register(SmartQuote)
class SmartQuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_number', 'customer', 'product_name', 'quantity', 'final_price', 'status', 'ai_calculated']
    list_filter = ['status', 'size', 'complexity', 'ai_calculated']
    search_fields = ['quote_number', 'customer__name', 'product_name']
    readonly_fields = ['quote_number', 'total_cost', 'unit_price', 'total_price', 'final_price', 'ai_confidence_score']
    
    fieldsets = (
        ('معلومات العرض', {
            'fields': ('quote_number', 'customer', 'status', 'valid_until')
        }),
        ('مواصفات المنتج', {
            'fields': ('product_name', 'description', 'quantity', 'size', 'complexity')
        }),
        ('الأبعاد', {
            'fields': ('width', 'height', 'depth', 'weight'),
            'classes': ('collapse',)
        }),
        ('التسعير', {
            'fields': ('pricing_rule', 'raw_material_cost', 'labor_cost', 'overhead_cost', 
                      'total_cost', 'profit_margin', 'unit_price', 'total_price', 
                      'quantity_discount', 'final_price')
        }),
        ('الذكاء الاصطناعي', {
            'fields': ('ai_calculated', 'ai_confidence_score')
        }),
        ('ملاحظات', {
            'fields': ('notes', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['calculate_prices', 'recommend_production_lines']
    
    def calculate_prices(self, request, queryset):
        """حساب الأسعار تلقائياً"""
        count = 0
        for quote in queryset:
            if quote.calculate_price():
                count += 1
        self.message_user(request, f'تم حساب أسعار {count} عرض')
    calculate_prices.short_description = 'حساب الأسعار تلقائياً'
    
    def recommend_production_lines(self, request, queryset):
        """ترشيح خطوط الإنتاج"""
        from .ai_engine import auto_recommend_production_line
        count = 0
        for quote in queryset:
            auto_recommend_production_line(quote)
            count += 1
        self.message_user(request, f'تم ترشيح خطوط الإنتاج لـ {count} عرض')
    recommend_production_lines.short_description = 'ترشيح خطوط الإنتاج بالذكاء الاصطناعي'


@admin.register(ProductionLineRecommendation)
class ProductionLineRecommendationAdmin(admin.ModelAdmin):
    list_display = ['smart_quote', 'work_center', 'recommendation_score', 'is_recommended', 'estimated_cost', 'estimated_time']
    list_filter = ['is_recommended', 'work_center']
    search_fields = ['smart_quote__quote_number', 'work_center__name']
    readonly_fields = ['created_at']


@admin.register(AutoMaterialRelease)
class AutoMaterialReleaseAdmin(admin.ModelAdmin):
    list_display = ['release_number', 'production_order', 'warehouse', 'status', 'auto_generated', 'released_at']
    list_filter = ['status', 'auto_generated', 'warehouse']
    search_fields = ['release_number', 'production_order__order_number']
    readonly_fields = ['release_number', 'auto_generated', 'released_at']
    inlines = [MaterialReleaseItemInline]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('release_number', 'production_order', 'warehouse', 'status')
        }),
        ('معلومات الصرف', {
            'fields': ('auto_generated', 'released_at', 'released_by')
        }),
        ('ملاحظات', {
            'fields': ('notes', 'created_at'),
            'classes': ('collapse',)
        }),
    )


# ============ Extended Models Admin ============

@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'competitor_type', 'market_share', 'price_level', 'quality_rating', 'is_active']
    list_filter = ['competitor_type', 'price_level', 'is_active']
    search_fields = ['name', 'website']
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'website', 'logo', 'competitor_type', 'is_active')
        }),
        ('التقييم', {
            'fields': ('market_share', 'quality_rating', 'price_level')
        }),
        ('التحليل', {
            'fields': ('strengths', 'weaknesses', 'notes'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CompetitorPrice)
class CompetitorPriceAdmin(admin.ModelAdmin):
    list_display = ['competitor', 'product_name', 'price', 'source', 'recorded_at']
    list_filter = ['competitor', 'source', 'recorded_at']
    search_fields = ['product_name', 'competitor__name']
    raw_id_fields = ['product']
    date_hierarchy = 'recorded_at'


@admin.register(PricingStrategy)
class PricingStrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy_type', 'base_margin', 'is_active', 'priority']
    list_filter = ['strategy_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['-priority']
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'strategy_type', 'description', 'is_active', 'priority')
        }),
        ('الهوامش', {
            'fields': ('base_margin', 'min_margin', 'max_margin')
        }),
        ('التعديلات', {
            'fields': ('competitor_adjustment', 'demand_sensitivity')
        }),
        ('النطاق', {
            'fields': ('applies_to_category', 'applies_to_customer_segment', 'start_date', 'end_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SeasonalPricing)
class SeasonalPricingAdmin(admin.ModelAdmin):
    list_display = ['name', 'season_type', 'start_date', 'end_date', 'adjustment_type', 'adjustment_value', 'is_active']
    list_filter = ['season_type', 'adjustment_type', 'is_active', 'applies_to_all']
    search_fields = ['name']
    date_hierarchy = 'start_date'
    fieldsets = (
        ('معلومات الموسم', {
            'fields': ('name', 'season_type', 'start_date', 'end_date')
        }),
        ('التعديل', {
            'fields': ('adjustment_type', 'adjustment_value')
        }),
        ('النطاق والتفعيل', {
            'fields': ('applies_to_all', 'product_categories', 'is_active', 'auto_activate')
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'old_price', 'new_price', 'price_change_percentage', 'reason', 'changed_at', 'approved']
    list_filter = ['reason', 'approved', 'requires_approval', 'changed_at']
    search_fields = ['product__name', 'reason_details']
    raw_id_fields = ['product']
    readonly_fields = ['price_change_percentage', 'changed_at']
    date_hierarchy = 'changed_at'


@admin.register(PricingGoal)
class PricingGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'goal_type', 'target_value', 'current_value', 'status', 'period_start', 'period_end']
    list_filter = ['goal_type', 'status']
    search_fields = ['name', 'description']
    date_hierarchy = 'period_start'


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'alert_type', 'priority', 'product', 'is_read', 'is_actioned', 'created_at']
    list_filter = ['alert_type', 'priority', 'is_read', 'is_actioned']
    search_fields = ['title', 'message']
    raw_id_fields = ['product', 'competitor']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_read', 'mark_as_actioned']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "تحديد كمقروء"
    
    def mark_as_actioned(self, request, queryset):
        queryset.update(is_actioned=True, actioned_by=request.user)
    mark_as_actioned.short_description = "تحديد كمعالج"


@admin.register(PricingSimulation)
class PricingSimulationAdmin(admin.ModelAdmin):
    list_display = ['name', 'scenario_type', 'price_change_percentage', 'expected_profit_change', 'created_at']
    list_filter = ['scenario_type']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']


@admin.register(ProductPricingProfile)
class ProductPricingProfileAdmin(admin.ModelAdmin):
    list_display = ['product', 'target_margin', 'enable_dynamic_pricing', 'enable_competitor_tracking', 'average_margin']
    list_filter = ['enable_dynamic_pricing', 'enable_competitor_tracking', 'enable_demand_based_pricing']
    search_fields = ['product__name']
    raw_id_fields = ['product', 'pricing_strategy', 'pricing_rule']
    fieldsets = (
        ('المنتج', {
            'fields': ('product', 'pricing_strategy', 'pricing_rule')
        }),
        ('التسعير الأساسي', {
            'fields': ('base_cost', 'target_margin', 'min_price', 'max_price')
        }),
        ('التسعير الذكي', {
            'fields': ('enable_dynamic_pricing', 'enable_competitor_tracking', 'enable_demand_based_pricing')
        }),
        ('معاملات AI', {
            'fields': ('ai_price_adjustment_limit', 'last_ai_recommendation', 'last_ai_recommendation_date'),
            'classes': ('collapse',)
        }),
        ('الإحصائيات', {
            'fields': ('average_margin', 'price_changes_count'),
            'classes': ('collapse',)
        }),
    )


class BundlePricingItemInline(admin.TabularInline):
    model = BundlePricingItem
    extra = 1
    raw_id_fields = ['product']


@admin.register(BundlePricing)
class BundlePricingAdmin(admin.ModelAdmin):
    list_display = ['name', 'discount_type', 'discount_value', 'bundle_price', 'savings', 'is_active']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['name', 'description']
    inlines = [BundlePricingItemInline]
    readonly_fields = ['total_original_price', 'bundle_price', 'savings']
    
    fieldsets = (
        ('معلومات الحزمة', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('التسعير', {
            'fields': ('discount_type', 'discount_value', 'total_original_price', 'bundle_price', 'savings')
        }),
        ('الفترة', {
            'fields': ('start_date', 'end_date'),
            'classes': ('collapse',)
        }),
    )


# استيراد admin من نظام قوائم الأسعار
from .admin_price_list import *
