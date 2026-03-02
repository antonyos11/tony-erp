from rest_framework import serializers
from apps.core.models import User, Branch, Warehouse, Company
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine
from apps.inventory.models import Product, Category, StockLevel
from apps.production.models import ProductionOrder
from apps.purchases.models import PurchaseOrder
from apps.quotations.models import Quotation
from apps.accounts.models import Account, JournalEntry
from apps.hr.models import Employee, Attendance


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_name = serializers.CharField(source='unit.symbol', read_only=True)
    current_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_current_stock(self, obj):
        from apps.inventory.services.stock_engine import StockEngine
        return float(StockEngine.get_stock_level(obj))


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class CustomerQuickCreateSerializer(serializers.ModelSerializer):
    """إضافة عميل سريع من الموبايل"""
    class Meta:
        model = Customer
        fields = ['name', 'customer_type', 'phone', 'phone2', 'address', 'governorate']


class SalesInvoiceLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SalesInvoiceLine
        fields = '__all__'


class SalesInvoiceSerializer(serializers.ModelSerializer):
    lines = SalesInvoiceLineSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = SalesInvoice
        fields = '__all__'


class StockLevelSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = StockLevel
        fields = '__all__'


class ProductionOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductionOrder
        fields = '__all__'


class QuotationSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = '__all__'

    def get_customer_name(self, obj):
        return obj.customer_display_name


class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Employee
        fields = '__all__'


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name_ar', read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'


class DashboardSerializer(serializers.Serializer):
    """بيانات الداشبورد"""
    sales_today = serializers.DecimalField(max_digits=15, decimal_places=2)
    sales_month = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    invoice_count_today = serializers.IntegerField()
    inventory_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_production = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    overdue_invoices = serializers.IntegerField()
