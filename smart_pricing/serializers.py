"""
REST API للتسعير الذكي
"""

from rest_framework import serializers
from .models import (
    PricingRule, SmartQuote, ProductionLineRecommendation,
    AutoMaterialRelease, MaterialReleaseItem
)


class PricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingRule
        fields = '__all__'


class SmartQuoteSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    pricing_rule_name = serializers.CharField(source='pricing_rule.name', read_only=True)
    
    class Meta:
        model = SmartQuote
        fields = '__all__'
        read_only_fields = [
            'quote_number', 'total_cost', 'unit_price', 'total_price',
            'final_price', 'ai_confidence_score'
        ]


class ProductionLineRecommendationSerializer(serializers.ModelSerializer):
    work_center_name = serializers.CharField(source='work_center.name', read_only=True)
    
    class Meta:
        model = ProductionLineRecommendation
        fields = '__all__'


class MaterialReleaseItemSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    
    class Meta:
        model = MaterialReleaseItem
        fields = '__all__'


class AutoMaterialReleaseSerializer(serializers.ModelSerializer):
    items = MaterialReleaseItemSerializer(many=True, read_only=True)
    production_order_number = serializers.CharField(source='production_order.order_number', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    
    class Meta:
        model = AutoMaterialRelease
        fields = '__all__'
        read_only_fields = ['release_number', 'auto_generated', 'released_at']
