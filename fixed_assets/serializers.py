from rest_framework import serializers
from .models import AssetCategory, Asset, DepreciationSchedule, AssetMaintenance, AssetTransfer
from decimal import Decimal


class AssetCategorySerializer(serializers.ModelSerializer):
    """Serializer for Asset Category"""
    
    depreciation_method_display = serializers.CharField(
        source='get_default_depreciation_method_display',
        read_only=True
    )
    
    class Meta:
        model = AssetCategory
        fields = [
            'id', 'name', 'code', 'description', 'default_depreciation_method',
            'depreciation_method_display', 'default_useful_life_years',
            'default_salvage_value_percent', 'asset_account',
            'accumulated_depreciation_account', 'depreciation_expense_account',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DepreciationScheduleSerializer(serializers.ModelSerializer):
    """Serializer for Depreciation Schedule"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DepreciationSchedule
        fields = [
            'id', 'asset', 'period_date', 'depreciation_amount',
            'accumulated_depreciation', 'book_value', 'status',
            'status_display', 'posted_at', 'journal_entry'
        ]
        read_only_fields = ['accumulated_depreciation', 'book_value', 'posted_at']


class AssetMaintenanceSerializer(serializers.ModelSerializer):
    """Serializer for Asset Maintenance"""
    
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_number = serializers.CharField(source='asset.number', read_only=True)
    performed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AssetMaintenance
        fields = [
            'id', 'asset', 'asset_name', 'asset_number', 'maintenance_date',
            'description', 'cost', 'performed_by', 'performed_by_name',
            'vendor', 'notes', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.get_full_name() or obj.performed_by.username
        return None


class AssetTransferSerializer(serializers.ModelSerializer):
    """Serializer for Asset Transfer"""
    
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_number = serializers.CharField(source='asset.number', read_only=True)
    transferred_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AssetTransfer
        fields = [
            'id', 'asset', 'asset_name', 'asset_number', 'transfer_date',
            'from_location', 'to_location', 'from_department', 'to_department',
            'from_employee', 'to_employee', 'reason', 'transferred_by',
            'transferred_by_name', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_transferred_by_name(self, obj):
        if obj.transferred_by:
            return obj.transferred_by.get_full_name() or obj.transferred_by.username
        return None


class AssetSerializer(serializers.ModelSerializer):
    """Serializer for Asset"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    depreciation_method_display = serializers.CharField(
        source='get_depreciation_method_display',
        read_only=True
    )
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    # Nested serializers for detail view
    depreciation_schedules = DepreciationScheduleSerializer(
        many=True,
        read_only=True,
        source='depreciationschedule_set'
    )
    maintenance_records = AssetMaintenanceSerializer(
        many=True,
        read_only=True,
        source='assetmaintenance_set'
    )
    
    class Meta:
        model = Asset
        fields = [
            'id', 'number', 'name', 'category', 'category_name', 'description',
            'serial_number', 'manufacturer', 'model', 'location', 'location_name',
            'department', 'assigned_to', 'acquisition_date', 'acquisition_cost',
            'purchase_invoice', 'depreciation_method', 'depreciation_method_display',
            'useful_life_years', 'useful_life_months', 'salvage_value',
            'depreciation_start_date', 'current_book_value',
            'accumulated_depreciation', 'status', 'status_display',
            'disposal_date', 'disposal_value', 'disposal_reason', 'notes',
            'depreciation_schedules', 'maintenance_records',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'number', 'current_book_value', 'accumulated_depreciation',
            'created_at', 'updated_at'
        ]


class AssetListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing assets"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = Asset
        fields = [
            'id', 'number', 'name', 'category_name', 'acquisition_date',
            'acquisition_cost', 'current_book_value', 'status', 'status_display',
            'location_name'
        ]


class AssetDepreciationSerializer(serializers.Serializer):
    """Serializer for asset depreciation calculations"""
    
    asset_id = serializers.IntegerField()
    asset_name = serializers.CharField()
    acquisition_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    salvage_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    useful_life_months = serializers.IntegerField()
    depreciation_per_month = serializers.DecimalField(max_digits=15, decimal_places=2)
    accumulated_depreciation = serializers.DecimalField(max_digits=15, decimal_places=2)
    current_book_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    remaining_months = serializers.IntegerField()


class AssetStatisticsSerializer(serializers.Serializer):
    """Serializer for asset statistics"""
    
    total_assets = serializers.IntegerField()
    active_assets = serializers.IntegerField()
    under_maintenance = serializers.IntegerField()
    disposed_assets = serializers.IntegerField()
    total_acquisition_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_current_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_accumulated_depreciation = serializers.DecimalField(max_digits=15, decimal_places=2)
    depreciation_this_month = serializers.DecimalField(max_digits=15, decimal_places=2)
    depreciation_this_year = serializers.DecimalField(max_digits=15, decimal_places=2)
