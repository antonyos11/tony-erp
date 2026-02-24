"""
API Serializers for Quality Control Module - Tony ERP
"""

from rest_framework import serializers
from .models import (
    QualityStandard, InspectionType, QualityInspection,
    InspectionResult, QualityIssue
)


class QualityStandardSerializer(serializers.ModelSerializer):
    """Serializer لمعايير الجودة"""
    
    class Meta:
        model = QualityStandard
        fields = [
            'id', 'name', 'code', 'description', 'category',
            'min_value', 'max_value', 'unit', 'is_active',
            'created_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'created_by']


class InspectionTypeSerializer(serializers.ModelSerializer):
    """Serializer لأنواع الفحص"""
    standards_count = serializers.IntegerField(source='standards.count', read_only=True)
    
    class Meta:
        model = InspectionType
        fields = [
            'id', 'name', 'code', 'description', 'standards',
            'standards_count', 'is_active'
        ]


class InspectionResultSerializer(serializers.ModelSerializer):
    """Serializer لنتائج الفحص"""
    standard_name = serializers.CharField(source='standard.name', read_only=True)
    standard_code = serializers.CharField(source='standard.code', read_only=True)
    
    class Meta:
        model = InspectionResult
        fields = [
            'id', 'standard', 'standard_name', 'standard_code',
            'measured_value', 'is_passed', 'notes'
        ]


class QualityInspectionSerializer(serializers.ModelSerializer):
    """Serializer الرئيسي لفحوصات الجودة"""
    inspection_type_name = serializers.CharField(source='inspection_type.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    results = InspectionResultSerializer(many=True, read_only=True)
    
    class Meta:
        model = QualityInspection
        fields = [
            'id', 'code', 'inspection_type', 'inspection_type_name',
            'product', 'product_name', 'batch_number',
            'inspection_date', 'inspector', 'inspector_name',
            'status', 'overall_score', 'notes', 'results',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class QualityInspectionCreateSerializer(serializers.ModelSerializer):
    """Serializer لإنشاء فحص جديد"""
    results = InspectionResultSerializer(many=True, required=False)
    
    class Meta:
        model = QualityInspection
        fields = [
            'inspection_type', 'product', 'batch_number',
            'inspection_date', 'inspector', 'notes', 'results'
        ]
    
    def create(self, validated_data):
        results_data = validated_data.pop('results', [])
        inspection = QualityInspection.objects.create(**validated_data)
        
        for result_data in results_data:
            InspectionResult.objects.create(inspection=inspection, **result_data)
        
        return inspection


class QualityIssueSerializer(serializers.ModelSerializer):
    """Serializer لمشاكل الجودة"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    reported_by_name = serializers.CharField(source='reported_by.get_full_name', read_only=True)
    
    class Meta:
        model = QualityIssue
        fields = [
            'id', 'code', 'title', 'description', 'inspection',
            'product', 'product_name', 'severity', 'status',
            'reported_by', 'reported_by_name', 'created_at',
            'resolved_at', 'root_cause', 'corrective_action'
        ]
        read_only_fields = ['created_at']
