from django.db import transaction
from django.contrib.auth.models import User
from rest_framework import serializers
from inventory.models import Product, Location, Stock
from partners.models import Customer, Supplier
from sales.models import Invoice, InvoiceItem
from purchases.models import PurchaseBill, PurchaseItem, PurchaseOrder, PurchaseOrderItem
from accounting.models import Revenue, Expense
from core.models import Company, AuditLog
from crm.models import Customer as CRMCustomer
from branches.models import Branch
from notifications.models import Notification
from users.models import UserRole, ModulePermission


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    # Explicit field definitions with validation
    sku = serializers.CharField(max_length=100, required=True)
    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'name', 'description', 'category', 'price', 'cost', 
            'product_type', 'is_active', 'barcode', 'current_stock'
        ]
        read_only_fields = ['current_stock']
    
    def validate_name(self, value):
        """Validate product name for length and special characters"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('اسم المنتج مطلوب')
        if len(value) > 255:
            raise serializers.ValidationError('اسم المنتج طويل جداً (الحد الأقصى 255 حرف)')
        return value.strip()
    
    def validate_sku(self, value):
        """Validate SKU format"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('كود المنتج (SKU) مطلوب')
        if len(value) > 100:
            raise serializers.ValidationError('كود المنتج طويل جداً (الحد الأقصى 100 حرف)')
        return value.strip()
    
    def validate_description(self, value):
        """Validate description length"""
        if value and len(value) > 5000:
            raise serializers.ValidationError('الوصف طويل جداً (الحد الأقصى 5000 حرف)')
        return value


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'
        ref_name = 'ApiLocation'


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = '__all__'
        ref_name = 'ApiStock'


class PartnerCustomerSerializer(serializers.ModelSerializer):
    """Serializer for partners.Customer - renamed to avoid conflict with crm.CustomerSerializer"""
    class Meta:
        model = Customer
        fields = '__all__'


# Alias for backward compatibility
CustomerSerializer = PartnerCustomerSerializer


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'
        ref_name = 'ApiSupplier'

    def create(self, validated_data):
        from partners.models import Partner
        name = validated_data.get('name')
        email = validated_data.get('email', '')
        phone = validated_data.get('phone', '')
        address = validated_data.get('address', '')
        
        # Create partner first
        partner = Partner.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address,
            partner_type='supplier'
        )
        
        # The signal create_supplier_record will create the Supplier instance
        supplier = partner.supplier_profile
        
        # Update supplier with remaining validated_data if any
        for attr, value in validated_data.items():
            if attr not in ['name', 'email', 'phone', 'address', 'partner']:
                setattr(supplier, attr, value)
        supplier.save()
        
        return supplier


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = '__all__'


class SalesInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for sales.Invoice - renamed to avoid conflict with sales.api_serializers.InvoiceSerializer"""
    items = InvoiceItemSerializer(many=True, read_only=True)
    number = serializers.CharField(max_length=50, required=True)

    class Meta:
        model = Invoice
        fields = ['id', 'number', 'customer', 'date', 'due_date', 'discount', 'paid', 'items', 'total']
    
    def validate_number(self, value):
        """Validate invoice number length"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('رقم الفاتورة مطلوب')
        if len(value) > 50:
            raise serializers.ValidationError('رقم الفاتورة طويل جداً (الحد الأقصى 50 حرف)')
        return value.strip()
    
    def validate(self, data):
        """Validate related data"""
        if data.get('due_date') and data.get('date'):
            if data['due_date'] < data['date']:
                raise serializers.ValidationError({
                    'due_date': 'تاريخ الاستحقاق يجب أن يكون بعد أو يساوي تاريخ الفاتورة'
                })
        return data


# Alias for backward compatibility
InvoiceSerializer = SalesInvoiceSerializer


class PurchaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = '__all__'


class PurchaseItemNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = ['product', 'location', 'quantity', 'cost']

class PurchaseBillSerializer(serializers.ModelSerializer):
    items = PurchaseItemNestedSerializer(many=True, required=False)
    number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = PurchaseBill
        fields = ['id', 'number', 'supplier', 'date', 'discount', 'paid', 'items', 'total']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        bill = PurchaseBill.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseItem.objects.create(bill=bill, **item_data)
        return bill


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'location', 'quantity', 'cost']
        ref_name = 'ApiPurchaseOrderItem'

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, required=False)
    number = serializers.CharField(read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ['id', 'number', 'supplier', 'date', 'expected_date', 'status', 'discount', 'items', 'total', 'notes']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        # 'total' and 'number' are read_only, so they won't be in validated_data
        order = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(order=order, **item_data)
        return order

class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = '__all__'


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'created_at', 'action', 'app_label', 'model_name', 'object_id', 'object_repr',
            'user', 'user_username', 'ip_address', 'user_agent', 'changes'
        ]


# ================================
# CRM Customer Serializer (crm.Customer)
# ================================
class CRMCustomerSerializer(serializers.ModelSerializer):
    """Serializer for crm.Customer with auto customer_code generation"""
    customer_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    class Meta:
        model = CRMCustomer
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        # customer_code will be auto-generated in model's save() if not provided
        return super().create(validated_data)
    
    def validate(self, data):
        # Ensure required fields for basic customer creation
        if not data.get('first_name'):
            raise serializers.ValidationError({'first_name': 'الاسم الأول مطلوب'})
        if not data.get('last_name'):
            raise serializers.ValidationError({'last_name': 'اسم العائلة مطلوب'})
        if not data.get('phone'):
            raise serializers.ValidationError({'phone': 'رقم الهاتف مطلوب'})
        return data


# ================================
# Enhanced Invoice Serializers with Nested Items
# ================================
class InvoiceItemNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for creating invoice items within invoice"""
    class Meta:
        model = InvoiceItem
        fields = ['product', 'location', 'quantity', 'price']
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('الكمية يجب أن تكون أكبر من صفر')
        return value
    
    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('السعر يجب أن يكون صفر أو أكثر')
        return value


class EnhancedInvoiceSerializer(serializers.ModelSerializer):
    """Enhanced invoice serializer with nested items support"""
    items = InvoiceItemNestedSerializer(many=True, required=False)
    number = serializers.CharField(required=False, allow_blank=True)  # Auto-generated if not provided
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'customer', 'date', 'due_date', 'discount', 'paid', 
            'items', 'is_approved', 'approved_by', 'approved_at', 'showroom'
        ]
        read_only_fields = ['is_approved', 'approved_by', 'approved_at']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        invoice = Invoice.objects.create(**validated_data)
        
        # Create invoice items
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        
        return invoice
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        instance = super().update(instance, validated_data)
        if items_data is not None:
            with transaction.atomic():
                instance.items.all().delete()
                for item_data in items_data:
                    InvoiceItem.objects.create(invoice=instance, **item_data)
        return instance

    def validate(self, data):
        if data.get('due_date') and data.get('date'):
            if data['due_date'] < data['date']:
                raise serializers.ValidationError({
                    'due_date': 'تاريخ الاستحقاق يجب أن يكون بعد أو يساوي تاريخ الفاتورة'
                })
        return data


# ================================
# Branch and Notification Serializers
# ================================
class BranchSerializer(serializers.ModelSerializer):
    """Serializer for branches.Branch"""
    class Meta:
        model = Branch
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications.Notification"""
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['created_at']


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'roles', 'is_superuser']
        
    def get_roles(self, obj):
        if hasattr(obj, 'profile') and obj.profile.role:
            return [{'id': obj.profile.role.id, 'name': obj.profile.role.name, 'display_name': obj.profile.role.display_name}]
        return []


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = '__all__'


class ModulePermissionSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='get_module_display', read_only=True)
    
    class Meta:
        model = ModulePermission
        fields = ['id', 'role', 'module', 'module_name', 'action', 'is_allowed']
