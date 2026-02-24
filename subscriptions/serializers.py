"""
REST API للباقات والاشتراكات
"""

from rest_framework import serializers
from .models import SubscriptionPlan, CustomerSubscription, SubscriptionPayment


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """باقات الاشتراك"""
    
    quarterly_discount = serializers.SerializerMethodField()
    annual_discount = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'
    
    def get_quarterly_discount(self, obj):
        """حساب نسبة الخصم الربع سنوي"""
        if obj.quarterly_price:
            monthly_total = obj.monthly_price * 3
            discount = ((monthly_total - obj.quarterly_price) / monthly_total) * 100
            return round(discount, 1)
        return 0
    
    def get_annual_discount(self, obj):
        """حساب نسبة الخصم السنوي"""
        if obj.annual_price:
            monthly_total = obj.monthly_price * 12
            discount = ((monthly_total - obj.annual_price) / monthly_total) * 100
            return round(discount, 1)
        return 0


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    """دفعات الاشتراك"""
    
    class Meta:
        model = SubscriptionPayment
        fields = '__all__'
        read_only_fields = ['payment_number', 'transaction_id']


class CustomerSubscriptionSerializer(serializers.ModelSerializer):
    """اشتراكات العملاء"""
    
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    customer_username = serializers.CharField(source='customer.username', read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    is_active_status = serializers.BooleanField(source='is_active', read_only=True)
    usage_limits = serializers.SerializerMethodField()
    payments = SubscriptionPaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = CustomerSubscription
        fields = '__all__'
        read_only_fields = ['subscription_number']
    
    def get_usage_limits(self, obj):
        """حدود الاستخدام"""
        return {
            'users': {
                'current': obj.current_users,
                'max': obj.plan.max_users,
                'exceeded': obj.current_users > obj.plan.max_users
            },
            'products': {
                'current': obj.current_products,
                'max': obj.plan.max_products,
                'exceeded': obj.current_products > obj.plan.max_products
            },
            'invoices_this_month': {
                'current': obj.current_invoices_this_month,
                'max': obj.plan.max_invoices_per_month,
                'exceeded': obj.current_invoices_this_month > obj.plan.max_invoices_per_month
            },
            'storage': {
                'current': float(obj.current_storage_gb),
                'max': obj.plan.max_storage_gb,
                'exceeded': obj.current_storage_gb > obj.plan.max_storage_gb
            }
        }


class SubscriptionPlanListSerializer(serializers.ModelSerializer):
    """قائمة الباقات المبسطة"""
    
    features_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'code', 'plan_type', 'description',
            'monthly_price', 'annual_price', 'max_users',
            'is_active', 'is_featured', 'features_count'
        ]
    
    def get_features_count(self, obj):
        """عدد المميزات المفعلة"""
        return sum([
            obj.has_api_access,
            obj.has_mobile_app,
            obj.has_advanced_reports,
            obj.has_ai_features,
            obj.has_whatsapp_integration,
            obj.has_ecommerce,
            obj.has_multi_branch,
            obj.has_priority_support
        ])
