from rest_framework import serializers
from .models import ProductionOrder, ProductionOrderStage, ProductionStage, BillOfMaterials
import datetime


class FlexibleDateField(serializers.DateField):
    """DateField يقبل قيم datetime ويحولها تلقائياً إلى date."""
    def to_representation(self, value):
        if isinstance(value, datetime.datetime):
            value = value.date()
        return super().to_representation(value)

    def to_internal_value(self, value):
        if isinstance(value, datetime.datetime):
            return value.date()
        return super().to_internal_value(value)


class ProductionOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    bom_name = serializers.CharField(source='bom.name', read_only=True)
    order_date = FlexibleDateField()
    planned_start_date = FlexibleDateField()
    planned_end_date = FlexibleDateField()
    actual_start_date = FlexibleDateField(required=False, allow_null=True)
    actual_end_date = FlexibleDateField(required=False, allow_null=True)

    class Meta:
        model = ProductionOrder
        fields = '__all__'
        read_only_fields = ['number', 'created_at', 'updated_at',
                            'estimated_material_cost', 'estimated_labor_cost', 'estimated_overhead_cost',
                            'actual_material_cost', 'actual_labor_cost', 'actual_overhead_cost']


class ProductionStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionStage
        fields = '__all__'


class ProductionOrderStageSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source='stage.name', read_only=True)

    class Meta:
        model = ProductionOrderStage
        fields = '__all__'


class BillOfMaterialsSerializer(serializers.ModelSerializer):
    effective_date = FlexibleDateField()
    expiry_date = FlexibleDateField(required=False, allow_null=True)

    class Meta:
        model = BillOfMaterials
        fields = '__all__'
