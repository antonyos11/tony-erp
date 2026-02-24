from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Vehicle, Driver, Trip, VehicleExpense, VehicleDocument
from .models import DriverViolation, DriverAdvance, DriverLocationPing
from showrooms.mixins import scope_queryset_to_active_showroom
from .api_serializers import (
    VehicleSerializer,
    DriverSerializer,
    TripSerializer,
    VehicleExpenseSerializer,
    VehicleDocumentSerializer,
    DriverViolationSerializer,
    DriverAdvanceSerializer,
    DriverLocationPingSerializer,
)

class BasePermission(permissions.IsAuthenticated):
    pass

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all().order_by('plate_number')
    serializer_class = VehicleSerializer
    permission_classes = [BasePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['plate_number','name','type']
    ordering_fields = ['plate_number','model_year','current_odometer']

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_to_active_showroom(self.request, qs)

class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all().order_by('name')
    serializer_class = DriverSerializer
    permission_classes = [BasePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name','phone','license_number']
    ordering_fields = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_to_active_showroom(self.request, qs)

    @action(detail=True, methods=['post'])
    def location(self, request, pk=None):
        """استقبال نقطة تتبع لسائق محدد.

        body: latitude, longitude, accuracy_m?, speed_mps?, heading_deg?, recorded_at?, vehicle?, trip?, source?
        """
        driver = self.get_object()
        payload = dict(request.data)
        payload['driver'] = driver.pk
        serializer = DriverLocationPingSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        ping = serializer.save(created_by=request.user if request.user.is_authenticated else None)
        return Response(DriverLocationPingSerializer(ping).data)

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.select_related('vehicle','driver').all().order_by('-start_time')
    serializer_class = TripSerializer
    permission_classes = [BasePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['vehicle','driver']
    search_fields = ['origin','destination','vehicle__plate_number','driver__name']
    ordering_fields = ['start_time','distance_km']

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_to_active_showroom(self.request, qs)

class VehicleExpenseViewSet(viewsets.ModelViewSet):
    queryset = VehicleExpense.objects.select_related('vehicle').all().order_by('-date','-id')
    serializer_class = VehicleExpenseSerializer
    permission_classes = [BasePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['vehicle','category','date']
    search_fields = ['description','vehicle__plate_number']
    ordering_fields = ['date','amount']

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_to_active_showroom(self.request, qs)

class VehicleDocumentViewSet(viewsets.ModelViewSet):
    queryset = VehicleDocument.objects.select_related('vehicle').all().order_by('-uploaded_at')
    serializer_class = VehicleDocumentSerializer
    permission_classes = [BasePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['vehicle','doc_type','expiry_date']
    search_fields = ['doc_type','vehicle__plate_number']
    ordering_fields = ['expiry_date','uploaded_at']

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_to_active_showroom(self.request, qs)

class DriverViolationViewSet(viewsets.ModelViewSet):
    queryset = DriverViolation.objects.all().select_related('driver','vehicle')
    serializer_class = DriverViolationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['driver','vehicle','violation_type','is_paid','date']
    search_fields = ['violation_type','driver__name','vehicle__plate_number']

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_to_active_showroom(self.request, qs)

class DriverAdvanceViewSet(viewsets.ModelViewSet):
    queryset = DriverAdvance.objects.all().select_related('driver')
    serializer_class = DriverAdvanceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['driver','status','date']
    search_fields = ['description','driver__name']

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_to_active_showroom(self.request, qs)

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        advance = self.get_object()
        if not advance.can_settle():
            return Response({'detail':'لا يمكن التصفية: المتبقي أكبر من الهامش المسموح'}, status=400)
        advance.settle()
        return Response(self.get_serializer(advance).data)


class DriverLocationPingViewSet(viewsets.ModelViewSet):
    queryset = DriverLocationPing.objects.select_related('driver', 'vehicle', 'trip').all().order_by('-recorded_at', '-id')
    serializer_class = DriverLocationPingSerializer
    permission_classes = [BasePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['driver', 'vehicle', 'trip']
    search_fields = ['driver__name', 'vehicle__plate_number', 'source']
    ordering_fields = ['recorded_at', 'id']

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_to_active_showroom(self.request, qs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
