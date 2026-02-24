"""
Smart Pricing API Serializers
المسلسلات للـ API
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import PricingRule, SmartQuote, ProductionLineRecommendation
from .models_extended import (
    Competitor, CompetitorPrice, PricingStrategy, SeasonalPricing,
    PriceHistory, PricingGoal, PriceAlert, ProductPricingProfile,
    BundlePricing
)


class PricingRuleSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    
    class Meta:
        model = PricingRule
        fields = [
            'id', 'name', 'product_category', 'method', 'method_display',
            'base_cost_multiplier', 'quantity_discount_threshold', 'quantity_discount_rate',
            'min_profit_margin', 'target_profit_margin', 'max_profit_margin',
            'use_ai_pricing', 'is_active', 'created_at', 'updated_at'
        ]


class SmartQuoteSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    size_display = serializers.CharField(source='get_size_display', read_only=True)
    complexity_display = serializers.CharField(source='get_complexity_display', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = SmartQuote
        fields = [
            'id', 'quote_number', 'customer', 'customer_name',
            'product_name', 'description', 'quantity',
            'size', 'size_display', 'complexity', 'complexity_display',
            'width', 'height', 'depth', 'weight',
            'pricing_rule', 'raw_material_cost', 'labor_cost', 'overhead_cost',
            'total_cost', 'profit_margin', 'unit_price', 'total_price',
            'quantity_discount', 'final_price',
            'ai_calculated', 'ai_confidence_score',
            'status', 'status_display', 'valid_until',
            'created_at', 'updated_at'
        ]


class SmartQuoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartQuote
        fields = [
            'customer', 'product_name', 'description', 'quantity',
            'size', 'complexity', 'width', 'height', 'depth', 'weight',
            'pricing_rule', 'raw_material_cost', 'labor_cost', 'overhead_cost'
        ]


class CompetitorSerializer(serializers.ModelSerializer):
    competitor_type_display = serializers.CharField(source='get_competitor_type_display', read_only=True)
    price_level_display = serializers.CharField(source='get_price_level_display', read_only=True)
    
    class Meta:
        model = Competitor
        fields = [
            'id', 'name', 'website', 'logo',
            'competitor_type', 'competitor_type_display',
            'market_share', 'quality_rating',
            'price_level', 'price_level_display',
            'strengths', 'weaknesses', 'notes',
            'is_active', 'created_at'
        ]


class CompetitorPriceSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = CompetitorPrice
        fields = [
            'id', 'competitor', 'competitor_name',
            'product', 'product_name', 'product_category',
            'price', 'currency',
            'source', 'source_display', 'source_url',
            'recorded_at', 'valid_until', 'notes'
        ]


class CompetitorPriceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitorPrice
        fields = [
            'competitor', 'product', 'product_name',
            'product_category', 'price', 'source',
            'source_url', 'valid_until', 'notes'
        ]


class PricingStrategySerializer(serializers.ModelSerializer):
    strategy_type_display = serializers.CharField(source='get_strategy_type_display', read_only=True)
    
    class Meta:
        model = PricingStrategy
        fields = [
            'id', 'name', 'strategy_type', 'strategy_type_display',
            'description', 'base_margin', 'min_margin', 'max_margin',
            'competitor_adjustment', 'demand_sensitivity',
            'applies_to_category', 'applies_to_customer_segment',
            'start_date', 'end_date', 'is_active', 'priority'
        ]


class SeasonalPricingSerializer(serializers.ModelSerializer):
    season_type_display = serializers.CharField(source='get_season_type_display', read_only=True)
    adjustment_type_display = serializers.CharField(source='get_adjustment_type_display', read_only=True)
    is_currently_active = serializers.SerializerMethodField()
    
    class Meta:
        model = SeasonalPricing
        fields = [
            'id', 'name', 'season_type', 'season_type_display',
            'start_date', 'end_date',
            'adjustment_type', 'adjustment_type_display', 'adjustment_value',
            'applies_to_all', 'product_categories',
            'is_active', 'auto_activate', 'is_currently_active',
            'notes', 'created_at'
        ]
    
    @extend_schema_field(serializers.BooleanField())
    def get_is_currently_active(self, obj):
        return obj.is_currently_active()


class PriceHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = PriceHistory
        fields = [
            'id', 'product', 'product_name',
            'old_price', 'new_price', 'old_cost', 'new_cost',
            'reason', 'reason_display', 'reason_details',
            'price_change_percentage',
            'changed_by', 'changed_by_name', 'changed_at',
            'requires_approval', 'approved', 'approved_by', 'approved_at'
        ]


class PricingGoalSerializer(serializers.ModelSerializer):
    goal_type_display = serializers.CharField(source='get_goal_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = PricingGoal
        fields = [
            'id', 'name', 'goal_type', 'goal_type_display',
            'description', 'period_start', 'period_end',
            'target_value', 'current_value', 'progress',
            'product_category', 'status', 'status_display',
            'created_by', 'created_at'
        ]
    
    @extend_schema_field(serializers.FloatField())
    def get_progress(self, obj):
        return obj.progress_percentage()


class PriceAlertSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = PriceAlert
        fields = [
            'id', 'alert_type', 'alert_type_display',
            'title', 'message',
            'product', 'product_name',
            'competitor', 'competitor_name',
            'data', 'recommended_action', 'recommended_price',
            'priority', 'priority_display',
            'is_read', 'is_actioned', 'actioned_by', 'actioned_at',
            'created_at', 'expires_at'
        ]


class ProductPricingProfileSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ProductPricingProfile
        fields = [
            'id', 'product', 'product_name',
            'pricing_strategy', 'pricing_rule',
            'base_cost', 'target_margin', 'min_price', 'max_price',
            'enable_dynamic_pricing', 'enable_competitor_tracking',
            'enable_demand_based_pricing',
            'ai_price_adjustment_limit', 'last_ai_recommendation',
            'last_ai_recommendation_date',
            'average_margin', 'price_changes_count', 'updated_at'
        ]


class BundlePricingSerializer(serializers.ModelSerializer):
    discount_type_display = serializers.CharField(source='get_discount_type_display', read_only=True)
    items = serializers.SerializerMethodField()
    
    class Meta:
        model = BundlePricing
        fields = [
            'id', 'name', 'description',
            'discount_type', 'discount_type_display', 'discount_value',
            'total_original_price', 'bundle_price', 'savings',
            'start_date', 'end_date', 'is_active',
            'items', 'created_at'
        ]
    
    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_items(self, obj):
        return [
            {
                'product_id': item.product_id,
                'product_name': item.product.name,
                'quantity': item.quantity
            }
            for item in obj.items.all()
        ]


# ============ API Response Serializers ============

class PriceCalculationRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    strategy = serializers.ChoiceField(
        choices=['aggressive', 'conservative', 'balanced', 'premium', 'penetration'],
        default='balanced'
    )
    include_competitor_analysis = serializers.BooleanField(default=True)
    include_demand_analysis = serializers.BooleanField(default=True)
    include_seasonality = serializers.BooleanField(default=True)


class PriceCalculationResponseSerializer(serializers.Serializer):
    recommended_price = serializers.FloatField()
    calculated_price = serializers.FloatField()
    confidence_score = serializers.FloatField()
    price_range = serializers.DictField()
    current_price = serializers.FloatField()
    price_change = serializers.FloatField()
    factors = serializers.ListField()
    adjustments = serializers.ListField()
    strategy = serializers.CharField()
    strategy_adjustment = serializers.FloatField()
    analysis = serializers.DictField()


class BulkPriceCalculationRequestSerializer(serializers.Serializer):
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        max_length=50
    )
    strategy = serializers.ChoiceField(
        choices=['aggressive', 'conservative', 'balanced', 'premium', 'penetration'],
        default='balanced'
    )


class AutoPricingRequestSerializer(serializers.Serializer):
    strategy = serializers.ChoiceField(
        choices=['aggressive', 'conservative', 'balanced', 'premium', 'penetration'],
        default='balanced'
    )
    category_id = serializers.IntegerField(required=False, allow_null=True)
    apply_immediately = serializers.BooleanField(default=False)
    requires_approval = serializers.BooleanField(default=True)


class PriceSimulationRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    price_changes = serializers.ListField(
        child=serializers.FloatField(),
        default=[-20, -15, -10, -5, 0, 5, 10, 15, 20]
    )
    demand_elasticity = serializers.FloatField(default=-1.5)
