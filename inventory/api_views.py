"""
Inventory REST API Views
واجهة برمجية RESTful للمخزون
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum

from .models import Product, Category, Stock, Location
from .api_serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    CategorySerializer,
    LocationSerializer,
    StockSerializer,
)


def _apply_showroom_scope(request, qs, location_field='id'):
    """Filter queryset by active showroom for showroom employees.

    - Non-showroom users: unfiltered (returns full queryset)
    - Showroom employee without active showroom: empty queryset
    - Showroom employee with active showroom they belong to: filtered by
      that showroom's location
    - Showroom employee with active showroom they don't belong to: empty
    """
    from showrooms.models import ShowroomEmployee, Showroom

    user = request.user
    if not user.is_authenticated:
        return qs

    is_showroom_employee = ShowroomEmployee.objects.filter(
        user=user, active=True
    ).exists()
    if not is_showroom_employee:
        return qs  # non-showroom users see everything

    sess = getattr(request, 'session', None)
    active_showroom_id = sess.get('ACTIVE_SHOWROOM_ID') if sess else None
    if not active_showroom_id:
        return qs.none()

    try:
        showroom = Showroom.objects.get(id=active_showroom_id)
    except Showroom.DoesNotExist:
        return qs.none()

    # Check user is assigned to this showroom
    has_access = ShowroomEmployee.objects.filter(
        showroom=showroom, user=user, active=True
    ).exists()
    if not has_access:
        return qs.none()

    return qs.filter(**{location_field: showroom.location_id})


class ProductViewSet(viewsets.ModelViewSet):
    """
    CRUD كامل للمنتجات
    GET    /inventory/api/v1/products/          → قائمة المنتجات
    POST   /inventory/api/v1/products/          → إضافة منتج
    GET    /inventory/api/v1/products/{id}/     → تفاصيل منتج
    PUT    /inventory/api/v1/products/{id}/     → تعديل منتج
    DELETE /inventory/api/v1/products/{id}/     → حذف منتج
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'product_type', 'is_active']
    search_fields = ['name', 'sku', 'barcode', 'internal_code']
    ordering_fields = ['name', 'price', 'cost', 'sku']
    ordering = ['name']

    def get_queryset(self):
        return Product.objects.select_related('category', 'preferred_supplier').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def create(self, request, *args, **kwargs):
        """Override create to handle code→sku mapping and auto-generate defaults"""
        import uuid
        from django.http import QueryDict
        
        # Make a mutable copy of request data
        if isinstance(request.data, QueryDict):
            data = request.data.copy()
        else:
            data = dict(request.data)
        
        # Auto-generate code if not provided
        if not data.get('sku') and not data.get('code'):
            data['code'] = f'PRD-{uuid.uuid4().hex[:8].upper()}'
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Override update to allow partial updates"""
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        """المنتجات ذات المخزون المنخفض"""
        from django.db.models import Subquery, OuterRef, IntegerField
        from django.db.models.functions import Coalesce

        stock_subq = Stock.objects.filter(
            product_id=OuterRef('pk')
        ).values('product_id').annotate(
            total_qty=Sum('quantity')
        ).values('total_qty')[:1]

        products = Product.objects.filter(is_active=True).annotate(
            total_stock=Coalesce(Subquery(stock_subq, output_field=IntegerField()), 0)
        ).filter(
            total_stock__lte=models_F('min_stock')
        ).select_related('category')

        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='stock')
    def stock_detail(self, request, pk=None):
        """مخزون منتج معين في جميع المواقع"""
        product = self.get_object()
        stocks = Stock.objects.filter(product=product).select_related('location')
        serializer = StockSerializer(stocks, many=True)
        return Response(serializer.data)


# Fix import for F expression
from django.db.models import F as models_F


class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD كامل لفئات المنتجات
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering = ['sort_order', 'name']


class LocationViewSet(viewsets.ModelViewSet):
    """
    CRUD للمواقع / المستودعات
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']
    ordering = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_showroom_scope(self.request, qs, location_field='id')


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    عرض المخزون (قراءة فقط - التعديل عبر عمليات الاستلام والإصدار)
    """
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['product', 'location']
    search_fields = ['product__name', 'product__sku', 'location__name']

    def get_queryset(self):
        qs = Stock.objects.select_related('product', 'location').all()
        return _apply_showroom_scope(self.request, qs, location_field='location_id')

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """ملخص المخزون حسب المنتج"""
        data = Stock.objects.values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            total_quantity=Sum('quantity')
        ).order_by('product__name')
        return Response(list(data))
