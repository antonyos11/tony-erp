"""
Serializers لنظام بناء المراتب المخصصة
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from decimal import Decimal
from .models import (
    MattressFeelingType,
    AIRecommendationConfig,
    MattressSize,
    MattressComponentCategory,
    MattressComponent,
    MattressRecommendationRule,
    CustomMattressDesign,
    DesignComponent,
    MattressTemplate,
    BuilderSettings,
    MattressOrder,
    DesignerCommission,
)


class MattressFeelingTypeSerializer(serializers.ModelSerializer):
    """Serializer لأنواع إحساس المرتبة"""
    firmness_level_display = serializers.CharField(source='get_firmness_level_display', read_only=True)
    
    class Meta:
        model = MattressFeelingType
        fields = [
            'id', 'name', 'name_en', 'firmness_level', 'firmness_level_display',
            'firmness_score', 'description', 'icon', 'color',
            'ideal_for', 'benefits', 'extra_price',
            'is_active', 'sort_order'
        ]


class AIRecommendationSerializer(serializers.ModelSerializer):
    """Serializer لاقتراحات الذكاء الاصطناعي"""
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)
    suggestion_type_display = serializers.CharField(source='get_suggestion_type_display', read_only=True)
    suggested_component_name = serializers.CharField(source='suggested_component.name', read_only=True, default=None)
    suggested_feeling_name = serializers.CharField(source='suggested_feeling.name', read_only=True, default=None)
    
    class Meta:
        model = AIRecommendationConfig
        fields = [
            'id', 'name', 'trigger_type', 'trigger_type_display',
            'suggestion_type', 'suggestion_type_display',
            'suggestion_data', 'message_ar', 'message_en',
            'icon', 'message_style', 'priority',
            'suggested_component', 'suggested_component_name',
            'suggested_feeling', 'suggested_feeling_name',
        ]


class MattressSizeSerializer(serializers.ModelSerializer):
    """Serializer لأحجام المراتب"""
    display_dimensions = serializers.CharField(read_only=True)
    area = serializers.FloatField(read_only=True)
    
    class Meta:
        model = MattressSize
        fields = [
            'id', 'name', 'name_en', 'width', 'length', 'height_default',
            'price_multiplier', 'base_price', 'is_active', 'sort_order',
            'image', 'icon', 'display_dimensions', 'area'
        ]


class MattressComponentCategorySerializer(serializers.ModelSerializer):
    """Serializer لفئات المكونات"""
    components_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MattressComponentCategory
        fields = [
            'id', 'name', 'name_en', 'category_type', 'description',
            'icon', 'color', 'layer_order', 'is_required', 'max_selections',
            'is_active', 'sort_order', 'components_count'
        ]
    
    @extend_schema_field(serializers.IntegerField())
    def get_components_count(self, obj):
        return obj.components.filter(is_active=True).count()


class MattressComponentSerializer(serializers.ModelSerializer):
    """Serializer للمكونات"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    quality_display = serializers.CharField(source='get_quality_level_display', read_only=True)
    pricing_display = serializers.SerializerMethodField()
    
    class Meta:
        model = MattressComponent
        fields = [
            'id', 'category', 'category_name', 'category_color',
            'name', 'name_en', 'description', 'short_description',
            'base_price', 'price_per_sqm', 'pricing_type', 'pricing_display',
            'quality_level', 'quality_display', 'thickness', 'density',
            'specifications', 'image', 'icon', 'texture_pattern',
            'is_active', 'is_featured', 'is_popular', 'popularity_score',
            'benefits', 'sort_order'
        ]
    
    @extend_schema_field(serializers.CharField())
    def get_pricing_display(self, obj):
        if obj.pricing_type == 'fixed':
            return f"{obj.base_price} جنيه"
        elif obj.pricing_type == 'per_sqm':
            return f"{obj.price_per_sqm} جنيه/م²"
        else:
            return f"{obj.base_price} + {obj.price_per_sqm}/م²"


class DesignComponentSerializer(serializers.ModelSerializer):
    """Serializer لمكونات التصميم"""
    component_details = MattressComponentSerializer(source='component', read_only=True)
    
    class Meta:
        model = DesignComponent
        fields = [
            'id', 'component', 'component_details', 'quantity',
            'layer_position', 'custom_specifications', 'price_at_selection'
        ]


class CustomMattressDesignSerializer(serializers.ModelSerializer):
    """Serializer لتصميمات المراتب"""
    mattress_size_details = MattressSizeSerializer(source='mattress_size', read_only=True)
    design_components = DesignComponentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_username = serializers.CharField(source='customer.username', read_only=True)
    feeling_details = MattressFeelingTypeSerializer(source='feeling_type', read_only=True)
    
    class Meta:
        model = CustomMattressDesign
        fields = [
            'id', 'customer', 'customer_username', 'customer_name',
            'customer_phone', 'customer_email', 'design_name',
            'published_name', 'is_public', 'sales_count', 'designer_commission_rate',
            'mattress_size', 'mattress_size_details', 'design_components',
            'feeling_type', 'feeling_details', 'feeling_auto_detected', 'feeling_score',
            'design_data', 'notes', 'admin_notes', 'base_price',
            'components_price', 'discount_amount', 'final_price',
            'status', 'status_display', 'approved_by', 'approved_at',
            'rejection_reason', 'estimated_production_days',
            'preview_image', 'view_count', 'is_template',
            'created_at', 'updated_at', 'submitted_at'
        ]
        read_only_fields = [
            'customer', 'base_price', 'components_price', 'final_price',
            'approved_by', 'approved_at', 'view_count', 'sales_count',
            'created_at', 'updated_at', 'submitted_at',
            'feeling_auto_detected', 'feeling_score'
        ]


class MattressTemplateSerializer(serializers.ModelSerializer):
    """Serializer لقوالب المراتب"""
    target_audience_display = serializers.CharField(source='get_target_audience_display', read_only=True)
    
    class Meta:
        model = MattressTemplate
        fields = [
            'id', 'name', 'name_en', 'description', 'short_description',
            'template_data', 'target_audience', 'target_audience_display',
            'starting_price', 'discount_percent', 'image', 'icon',
            'features', 'is_active', 'is_featured', 'is_popular',
            'usage_count', 'sort_order'
        ]


class BuilderSettingsSerializer(serializers.ModelSerializer):
    """Serializer لإعدادات النظام"""
    
    class Meta:
        model = BuilderSettings
        fields = [
            'profit_margin_percent', 'auto_approval_threshold',
            'enable_auto_approval', 'estimated_production_days',
            'max_designs_per_customer', 'enable_recommendations',
            'enable_gamification', 'welcome_message'
        ]


class CalculatePriceSerializer(serializers.Serializer):
    """Serializer لحساب السعر"""
    mattress_size_id = serializers.IntegerField()
    component_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )
    
    def validate(self, data):
        # التحقق من وجود الحجم
        try:
            size = MattressSize.objects.get(id=data['mattress_size_id'], is_active=True)
        except MattressSize.DoesNotExist:
            raise serializers.ValidationError("حجم المرتبة غير موجود")
        
        # التحقق من وجود المكونات
        components = MattressComponent.objects.filter(
            id__in=data['component_ids'],
            is_active=True
        )
        
        if len(components) != len(data['component_ids']):
            raise serializers.ValidationError("بعض المكونات غير موجودة أو غير مفعلة")
        
        data['size'] = size
        data['components'] = components
        
        return data


class GetRecommendationsSerializer(serializers.Serializer):
    """Serializer للحصول على الاقتراحات"""
    design_data = serializers.JSONField()
    mattress_size_id = serializers.IntegerField()
    selected_component_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )


class MattressOrderSerializer(serializers.ModelSerializer):
    """Serializer لطلبات المراتب"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    design_name = serializers.CharField(source='design.design_name', read_only=True)
    design_published_name = serializers.CharField(source='design.published_name', read_only=True)
    designer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MattressOrder
        fields = [
            'id', 'order_number', 'customer', 'design', 'design_name',
            'design_published_name', 'is_community_purchase', 'original_designer',
            'designer_name', 'customer_name', 'customer_phone', 'customer_email',
            'shipping_address', 'shipping_city', 'subtotal', 'shipping_cost',
            'discount', 'tax', 'total', 'status', 'status_display',
            'payment_method', 'payment_reference', 'paid_at',
            'estimated_delivery_date', 'actual_delivery_date',
            'customer_notes', 'admin_notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'order_number', 'customer', 'paid_at', 'status',
            'production_order', 'journal_entry',
            'created_at', 'updated_at',
        ]
    
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_designer_name(self, obj):
        if obj.original_designer:
            return obj.original_designer.get_full_name() or obj.original_designer.username
        return None


class DesignerCommissionSerializer(serializers.ModelSerializer):
    """Serializer لعمولات المصممين"""
    designer_name = serializers.SerializerMethodField()
    design_name = serializers.CharField(source='design.published_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DesignerCommission
        fields = [
            'id', 'designer', 'designer_name', 'order', 'order_number',
            'design', 'design_name', 'commission_rate', 'commission_amount',
            'status', 'status_display', 'paid_at', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['designer', 'order', 'design', 'commission_rate', 
                          'commission_amount', 'created_at', 'updated_at']
    
    @extend_schema_field(serializers.CharField())
    def get_designer_name(self, obj):
        return obj.designer.get_full_name() or obj.designer.username


class CommunityDesignSerializer(serializers.ModelSerializer):
    """Serializer مختصر للتصميمات المنشورة للمجتمع"""
    designer_name = serializers.SerializerMethodField()
    size_name = serializers.CharField(source='mattress_size.name', read_only=True)
    size_dims = serializers.SerializerMethodField()
    feeling_name = serializers.CharField(source='feeling_type.name', read_only=True, default=None)
    feeling_color = serializers.CharField(source='feeling_type.color', read_only=True, default=None)
    feeling_score = serializers.IntegerField(read_only=True)
    components_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomMattressDesign
        fields = [
            'id', 'published_name', 'designer_name', 'mattress_size',
            'size_name', 'size_dims', 'feeling_name', 'feeling_color',
            'feeling_score', 'final_price', 'components_count',
            'sales_count', 'view_count', 'preview_image', 'created_at',
        ]
    
    @extend_schema_field(serializers.CharField())
    def get_designer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username
    
    @extend_schema_field(serializers.CharField())
    def get_size_dims(self, obj):
        return f"{obj.mattress_size.width} × {obj.mattress_size.length} سم"
    
    @extend_schema_field(serializers.IntegerField())
    def get_components_count(self, obj):
        return obj.design_components.count()
