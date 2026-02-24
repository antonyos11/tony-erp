"""
API Serializers for Shipping Module - Tony ERP
"""

from rest_framework import serializers
from .models import (
    ShippingCompany, ShippingZone, ShippingRate,
    Shipment, ShipmentTracking
)


class ShippingCompanySerializer(serializers.ModelSerializer):
    """Serializer لشركات الشحن"""
    
    class Meta:
        model = ShippingCompany
        fields = [
            'id', 'name', 'code', 'contact_person', 'phone',
            'email', 'address', 'website', 'is_active',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ShippingZoneSerializer(serializers.ModelSerializer):
    """Serializer لمناطق الشحن"""
    
    class Meta:
        model = ShippingZone
        fields = '__all__'


class ShippingRateSerializer(serializers.ModelSerializer):
    """Serializer لتعريفات الشحن"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    
    class Meta:
        model = ShippingRate
        fields = [
            'id', 'company', 'company_name', 'zone', 'zone_name',
            'weight_from', 'weight_to', 'base_rate', 'extra_kg_rate',
            'delivery_days', 'is_active'
        ]


class ShipmentTrackingSerializer(serializers.ModelSerializer):
    """Serializer لتتبع الشحنة"""
    
    class Meta:
        model = ShipmentTracking
        fields = ['id', 'status', 'location', 'description', 'timestamp', 'updated_by']
        read_only_fields = ['timestamp']


class ShipmentSerializer(serializers.ModelSerializer):
    """Serializer الرئيسي للشحنات"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    tracking_history = ShipmentTrackingSerializer(many=True, read_only=True)
    
    class Meta:
        model = Shipment
        fields = [
            'id', 'tracking_number', 'company', 'company_name', 'status',
            'sender_name', 'sender_phone', 'sender_address', 'sender_city',
            'receiver_name', 'receiver_phone', 'receiver_address', 'receiver_city',
            'weight', 'shipping_cost', 'payment_type',
            'cod_amount', 'insurance_amount',
            'pickup_date', 'expected_delivery', 'actual_delivery',
            'notes', 'tracking_history',
            'created_at', 'created_by', 'updated_at'
        ]
        read_only_fields = ['created_at', 'created_by', 'updated_at', 'tracking_number']


class ShipmentCreateSerializer(serializers.ModelSerializer):
    """Serializer لإنشاء شحنة جديدة"""
    
    class Meta:
        model = Shipment
        fields = [
            'company', 'sender_name', 'sender_phone', 'sender_address', 'sender_city',
            'receiver_name', 'receiver_phone', 'receiver_address', 'receiver_city',
            'weight', 'payment_type', 'cod_amount', 'insurance_amount',
            'pickup_date', 'expected_delivery', 'notes'
        ]
