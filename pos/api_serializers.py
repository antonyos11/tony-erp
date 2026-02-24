from rest_framework import serializers
from .models import POSOrder, POSOrderLine
from showrooms.mixins import get_active_showroom_id

class POSOrderLineInSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)

class POSOrderCreateSerializer(serializers.Serializer):
    location_id = serializers.IntegerField(required=False, allow_null=True)
    showroom_id = serializers.IntegerField(required=False, allow_null=True)
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    lines = POSOrderLineInSerializer(many=True)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    vat_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    is_return = serializers.BooleanField(required=False, default=False)
    original_order_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        request = self.context.get('request') if hasattr(self, 'context') else None
        if attrs.get('is_return') and not attrs.get('original_order_id'):
            raise serializers.ValidationError('original_order_id is required for returns')
        sid = get_active_showroom_id(request) if request else None
        if sid is None:
            raise serializers.ValidationError('showroom is required')
        return attrs

class POSOrderSerializer(serializers.ModelSerializer):
    lines = serializers.SerializerMethodField()
    class Meta:
        model = POSOrder
        fields = ['id','number','status','total','paid_amount','showroom','location','customer','created_at','lines']
    def get_lines(self, obj):
        return [{'product': l.product_id, 'quantity': l.quantity, 'price': str(l.price)} for l in obj.lines.all()]
