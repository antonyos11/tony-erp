from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Customer, CustomerType, CustomerSource, ContactPerson,
    Opportunity, OpportunityStage, Activity, ActivityType,
    Quotation, QuotationItem, SupportTicket, TicketCategory,
    Campaign, CampaignResponse
)
from inventory.models import Product

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class CustomerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerType
        fields = '__all__'

class CustomerSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerSource
        fields = '__all__'

class ContactPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPerson
        fields = '__all__'

class CRMCustomerSerializer(serializers.ModelSerializer):
    """CRM Customer serializer with full details - renamed to avoid conflict"""
    full_name = serializers.SerializerMethodField()
    full_address = serializers.SerializerMethodField()
    customer_type_name = serializers.CharField(source='customer_type.name', read_only=True)
    source_name = serializers.CharField(source='source.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    contacts = ContactPersonSerializer(many=True, read_only=True)
    
    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['customer_code', 'created_at', 'updated_at']

    def get_full_name(self, obj) -> str:
        return getattr(obj, 'full_name', f"{obj.first_name} {obj.last_name}")

    def get_full_address(self, obj) -> str:
        return getattr(obj, 'full_address', '')


# Alias for backward compatibility
CustomerSerializer = CRMCustomerSerializer

class CustomerListSerializer(serializers.ModelSerializer):
    """مُسلسل مبسط لقائمة العملاء"""
    full_name = serializers.ReadOnlyField()
    customer_type_name = serializers.CharField(source='customer_type.name', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_code', 'full_name', 'company_name', 
            'phone', 'email', 'customer_type_name', 'status', 'created_at'
        ]

class OpportunityStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityStage
        fields = '__all__'

class OpportunitySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Opportunity
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'closed_at']

class OpportunityListSerializer(serializers.ModelSerializer):
    """مُسلسل مبسط لقائمة الفرص"""
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    
    class Meta:
        model = Opportunity
        fields = [
            'id', 'name', 'customer_name', 'stage_name', 
            'estimated_value', 'probability', 'expected_close_date', 'created_at'
        ]

class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = '__all__'

class ActivitySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    activity_type_name = serializers.CharField(source='activity_type.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Activity
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'completed_at']

class ActivityListSerializer(serializers.ModelSerializer):
    """مُسلسل مبسط لقائمة الأنشطة"""
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    activity_type_name = serializers.CharField(source='activity_type.name', read_only=True)
    
    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'customer_name', 'activity_type_name',
            'scheduled_date', 'status', 'priority', 'created_at'
        ]

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'price']

class QuotationItemNestedSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = QuotationItem
        fields = '__all__'
        read_only_fields = ['total', 'quotation']
        extra_kwargs = {
            'quotation': {'required': False, 'allow_null': True}
        }

class QuotationItemSerializer(serializers.ModelSerializer):
    """Standard serializer for QuotationItem"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    quotation_number = serializers.CharField(source='quotation.quotation_number', read_only=True)
    
    class Meta:
        model = QuotationItem
        fields = '__all__'


class QuotationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    prepared_by_name = serializers.CharField(source='prepared_by.get_full_name', read_only=True)
    items = QuotationItemNestedSerializer(many=True)
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = Quotation
        fields = '__all__'
        read_only_fields = [
            'quotation_number', 'subtotal', 'discount_amount', 
            'tax_amount', 'total_amount', 'created_at', 'updated_at', 'prepared_by'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        quotation = Quotation.objects.create(**validated_data)
        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)
        # Recalculate totals after adding items
        quotation.calculate_totals()
        return quotation

class QuotationListSerializer(serializers.ModelSerializer):
    """مُسلسل مبسط لقائمة عروض الأسعار"""
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_number', 'customer_name', 'quotation_date',
            'valid_until', 'total_amount', 'status', 'created_at'
        ]

class TicketCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketCategory
        fields = '__all__'

class SupportTicketSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = '__all__'
        read_only_fields = ['ticket_number', 'created_at', 'updated_at']

class SupportTicketListSerializer(serializers.ModelSerializer):
    """مُسلسل مبسط لقائمة التذاكر"""
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number', 'title', 'customer_name', 
            'category_name', 'status', 'priority', 'created_at'
        ]

class CampaignResponseSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    
    class Meta:
        model = CampaignResponse
        fields = '__all__'
        read_only_fields = ['response_date']

class CampaignSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    customer_type_name = serializers.CharField(source='customer_type.name', read_only=True)
    responses = CampaignResponseSerializer(many=True, read_only=True)
    target_customers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_target_customers_count(self, obj):
        return obj.target_customers.count()

class CampaignListSerializer(serializers.ModelSerializer):
    """مُسلسل مبسط لقائمة الحملات"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'campaign_type', 'status', 
            'start_date', 'end_date', 'budget', 'created_by_name', 'created_at'
        ]

# Serializers لإحصائيات وتقارير
class CustomerStatsSerializer(serializers.Serializer):
    total_customers = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    new_customers_this_month = serializers.IntegerField()
    customers_by_type = serializers.JSONField()
    customers_by_source = serializers.JSONField()

class OpportunityStatsSerializer(serializers.Serializer):
    total_opportunities = serializers.IntegerField()
    open_opportunities = serializers.IntegerField()
    won_opportunities = serializers.IntegerField()
    lost_opportunities = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    won_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    conversion_rate = serializers.FloatField()
    opportunities_by_stage = serializers.JSONField()

class ActivityStatsSerializer(serializers.Serializer):
    total_activities = serializers.IntegerField()
    completed_activities = serializers.IntegerField()
    overdue_activities = serializers.IntegerField()
    activities_this_week = serializers.IntegerField()
    activities_by_type = serializers.JSONField()

class SalesStatsSerializer(serializers.Serializer):
    total_quotations = serializers.IntegerField()
    accepted_quotations = serializers.IntegerField()
    quotations_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    conversion_rate = serializers.FloatField()

class CRMDashboardSerializer(serializers.Serializer):
    customer_stats = CustomerStatsSerializer()
    opportunity_stats = OpportunityStatsSerializer()
    activity_stats = ActivityStatsSerializer()
    sales_stats = SalesStatsSerializer()
    recent_activities = ActivityListSerializer(many=True)
    overdue_opportunities = OpportunityListSerializer(many=True)