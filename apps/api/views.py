from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from apps.api.serializers import (
    ProductSerializer, CustomerSerializer, CustomerQuickCreateSerializer,
    SalesInvoiceSerializer, StockLevelSerializer, ProductionOrderSerializer,
    QuotationSerializer, EmployeeSerializer, AttendanceSerializer,
)
from apps.inventory.models import Product, StockLevel
from apps.sales.models import Customer, SalesInvoice
from apps.production.models import ProductionOrder
from apps.quotations.models import Quotation
from apps.hr.models import Employee, Attendance


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    filterset_fields = ['product_type', 'category', 'is_active']
    search_fields = ['code', 'name', 'barcode']
    ordering_fields = ['code', 'name', 'cost_price', 'retail_price']


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.filter(is_active=True)
    serializer_class = CustomerSerializer
    filterset_fields = ['customer_type', 'branch', 'is_active']
    search_fields = ['code', 'name', 'phone']

    @action(detail=False, methods=['post'])
    def quick_create(self, request):
        serializer = CustomerQuickCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Auto-generate code
            last = Customer.objects.order_by('-code').first()
            new_num = int(last.code[1:]) + 1 if last and last.code.startswith('C') else 1
            customer = serializer.save(
                code=f'C{new_num:04d}',
                branch=request.current_branch,
                created_by=request.user,
                updated_by=request.user,
            )
            return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SalesInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SalesInvoice.objects.all()
    serializer_class = SalesInvoiceSerializer
    filterset_fields = ['status', 'branch', 'customer', 'payment_method']
    search_fields = ['invoice_number', 'customer__name']
    ordering_fields = ['date', 'total']


class StockLevelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockLevel.objects.filter(quantity__gt=0)
    serializer_class = StockLevelSerializer
    filterset_fields = ['product', 'warehouse']


class ProductionOrderViewSet(viewsets.ModelViewSet):
    queryset = ProductionOrder.objects.all()
    serializer_class = ProductionOrderSerializer
    filterset_fields = ['status', 'production_line']


class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.all()
    serializer_class = QuotationSerializer
    filterset_fields = ['status', 'branch', 'salesperson']
    search_fields = ['quotation_number', 'prospect_name']


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.filter(is_active=True)
    serializer_class = EmployeeSerializer
    filterset_fields = ['branch', 'department', 'employment_type']
    search_fields = ['employee_number', 'full_name_ar']


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    filterset_fields = ['employee', 'date', 'status']


@api_view(['GET'])
def dashboard_api(request):
    """API الداشبورد"""
    from django.utils import timezone
    from django.db.models import Sum

    today = timezone.now().date()
    branch = getattr(request, 'current_branch', None)

    invoice_filter = {}
    if branch:
        invoice_filter['branch'] = branch

    sales_today = SalesInvoice.objects.filter(
        date__date=today,
        status__in=['confirmed', 'paid', 'partial_paid'],
        **invoice_filter,
    ).aggregate(total=Sum('total'))['total'] or 0

    from apps.inventory.services.valuation import InventoryValuation
    inventory_value = InventoryValuation.get_total_inventory_value()

    from apps.inventory.services.stock_engine import StockEngine
    low_stock = len(StockEngine.get_low_stock_products())

    return Response({
        'sales_today': float(sales_today),
        'inventory_value': float(inventory_value),
        'low_stock_count': low_stock,
        'active_production': ProductionOrder.objects.filter(status='in_progress').count(),
        'active_customers': Customer.objects.filter(is_active=True).count(),
    })
