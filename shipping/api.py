"""
API Views for Shipping Module - Tony ERP
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import (
    ShippingCompany, ShippingZone, ShippingRate,
    Shipment, ShipmentTracking
)
from .serializers import (
    ShippingCompanySerializer, ShippingZoneSerializer,
    ShippingRateSerializer, ShipmentSerializer,
    ShipmentCreateSerializer, ShipmentTrackingSerializer
)


class ShippingCompanyViewSet(viewsets.ModelViewSet):
    """API ViewSet لشركات الشحن"""
    queryset = ShippingCompany.objects.all()
    serializer_class = ShippingCompanySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'contact_person']
    filterset_fields = ['is_active']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ShippingZoneViewSet(viewsets.ModelViewSet):
    """API ViewSet لمناطق الشحن"""
    queryset = ShippingZone.objects.all()
    serializer_class = ShippingZoneSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'code', 'country', 'cities']
    filterset_fields = ['is_active', 'country']


class ShippingRateViewSet(viewsets.ModelViewSet):
    """API ViewSet لتعريفات الشحن"""
    queryset = ShippingRate.objects.select_related('company', 'zone').all()
    serializer_class = ShippingRateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['company', 'zone', 'is_active']
    ordering_fields = ['base_rate', 'delivery_days']
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """حساب تكلفة الشحن بناءً على الوزن والمنطقة"""
        weight = request.data.get('weight')
        zone_id = request.data.get('zone')
        company_id = request.data.get('company')
        
        if not all([weight, zone_id]):
            return Response(
                {'error': 'Weight and zone are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rates = ShippingRate.objects.filter(
            zone_id=zone_id,
            is_active=True,
            weight_from__lte=weight,
            weight_to__gte=weight
        )
        
        if company_id:
            rates = rates.filter(company_id=company_id)
        
        results = []
        for rate in rates:
            extra_weight = max(0, float(weight) - float(rate.weight_from))
            total_cost = float(rate.base_rate) + (extra_weight * float(rate.extra_kg_rate))
            
            results.append({
                'company': rate.company.name,
                'rate_id': rate.id,
                'base_rate': float(rate.base_rate),
                'extra_kg_rate': float(rate.extra_kg_rate),
                'total_cost': round(total_cost, 2),
                'delivery_days': rate.delivery_days
            })
        
        return Response(results)


class ShipmentViewSet(viewsets.ModelViewSet):
    """API ViewSet للشحنات"""
    queryset = Shipment.objects.select_related('company', 'created_by').prefetch_related('items', 'tracking').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['tracking_number', 'receiver_name', 'receiver_phone']
    filterset_fields = ['status', 'company', 'payment_type']
    ordering_fields = ['created_at', 'expected_delivery']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ShipmentCreateSerializer
        return ShipmentSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """تحديث حالة الشحنة"""
        shipment = self.get_object()
        new_status = request.data.get('status')
        location = request.data.get('location', '')
        notes = request.data.get('notes', '')
        
        if new_status not in dict(Shipment.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        shipment.status = new_status
        if new_status == 'delivered':
            shipment.actual_delivery = timezone.now()
        shipment.save()
        
        # إضافة سجل تتبع
        ShipmentTracking.objects.create(
            shipment=shipment,
            status=new_status,
            location=location,
            notes=notes,
            updated_by=request.user
        )
        
        serializer = self.get_serializer(shipment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """تتبع الشحنة"""
        shipment = self.get_object()
        tracking_history = shipment.tracking.all().order_by('-timestamp')
        serializer = ShipmentTrackingSerializer(tracking_history, many=True)
        
        return Response({
            'tracking_number': shipment.tracking_number,
            'current_status': shipment.status,
            'company': shipment.company.name,
            'expected_delivery': shipment.expected_delivery,
            'actual_delivery': shipment.actual_delivery,
            'history': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """إحصائيات الشحنات"""
        from django.db.models import Count, Sum, Avg
        
        stats = Shipment.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=models.Q(status='pending')),
            in_transit=Count('id', filter=models.Q(status='in_transit')),
            delivered=Count('id', filter=models.Q(status='delivered')),
            total_value=Sum('declared_value'),
            total_cost=Sum('shipping_cost'),
            avg_cost=Avg('shipping_cost')
        )
        
        return Response(stats)
