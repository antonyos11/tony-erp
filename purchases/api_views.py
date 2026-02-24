"""
Purchases REST API Views
واجهة برمجية RESTful للمشتريات
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import PurchaseOrder, PurchaseBill
from partners.models import Partner
from .api_serializers import (
    SupplierSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderDetailSerializer,
    PurchaseBillListSerializer,
    PurchaseBillDetailSerializer,
)


class SupplierViewSet(viewsets.ModelViewSet):
    """
    CRUD كامل للموردين
    """
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'email', 'phone']
    ordering = ['name']

    def get_queryset(self):
        return Partner.objects.filter(partner_type='supplier')


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    CRUD كامل لأوامر الشراء
    GET    /purchases/api/v1/orders/             → قائمة الأوامر
    POST   /purchases/api/v1/orders/             → إنشاء أمر شراء
    GET    /purchases/api/v1/orders/{id}/        → تفاصيل أمر
    POST   /purchases/api/v1/orders/{id}/confirm/  → تأكيد الأمر
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'supplier']
    search_fields = ['number', 'supplier__name', 'notes']
    ordering_fields = ['date', 'number', 'created_at']
    ordering = ['-date', '-id']

    def get_queryset(self):
        return PurchaseOrder.objects.select_related('supplier', 'created_by').prefetch_related('items__product')

    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseOrderListSerializer
        return PurchaseOrderDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm_order(self, request, pk=None):
        """تأكيد أمر الشراء"""
        order = self.get_object()
        if order.status != 'draft':
            return Response(
                {'error': f'لا يمكن تأكيد أمر بحالة: {order.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = 'confirmed'
        order.save(update_fields=['status'])
        serializer = PurchaseOrderDetailSerializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_order(self, request, pk=None):
        """إلغاء أمر الشراء"""
        order = self.get_object()
        if order.status in ('completed', 'cancelled'):
            return Response(
                {'error': f'لا يمكن إلغاء أمر بحالة: {order.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        serializer = PurchaseOrderDetailSerializer(order)
        return Response(serializer.data)


class PurchaseBillViewSet(viewsets.ModelViewSet):
    """
    CRUD لفواتير المشتريات
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'supplier', 'is_deleted']
    search_fields = ['number', 'supplier__name', 'supplier_invoice_number']
    ordering_fields = ['date', 'number']
    ordering = ['-date', '-id']

    def get_queryset(self):
        return PurchaseBill.objects.select_related('supplier', 'showroom').prefetch_related('items__product').filter(is_deleted=False)

    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseBillListSerializer
        return PurchaseBillDetailSerializer
