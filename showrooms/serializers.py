from rest_framework import serializers
from .models import (
    Showroom,
    ShowroomEmployee,
    ShowroomExpense,
    ShowroomPurchase,
    ShowroomPurchaseItem,
    ShowroomStockMovement,
    ShowroomPayrollEntry,
    ShowroomShift,
    ShowroomShiftAssignment,
    TemporaryWorker,
    ShowroomRentPayment,
)

class ShowroomSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    showroom_type_display = serializers.CharField(source='get_showroom_type_display', read_only=True)
    is_temporary = serializers.BooleanField(read_only=True)
    is_rented = serializers.BooleanField(read_only=True)
    is_owned = serializers.BooleanField(read_only=True)
    contract_days_remaining = serializers.IntegerField(read_only=True)
    is_contract_expiring_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = Showroom
        fields = [
            'id','code','name','name_ar','showroom_type','showroom_type_display',
            'property_type','property_type_display','property_value','monthly_rent',
            'contract_start_date','contract_end_date','contract_document','contract_notes',
            'asset_account','rent_expense_account',
            'location','location_name','manager','opening_date',
            'address','city','contact_phone','contact_person','is_active',
            'is_temporary','is_rented','is_owned',
            'contract_days_remaining','is_contract_expiring_soon'
        ]

class ShowroomEmployeeSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    showroom_code = serializers.CharField(source='showroom.code', read_only=True)

    class Meta:
        model = ShowroomEmployee
        fields = ['id','showroom','showroom_code','user','user_username','role','can_cross_access','active','assigned_at']


class ShowroomExpenseSerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source='showroom.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = ShowroomExpense
        fields = [
            'id','showroom','showroom_name','amount','category','description','status','requires_approval','attachment',
            'created_by','created_by_username','approved_by','approved_by_username','approved_at','rejection_note','created_at'
        ]
        read_only_fields = ('status','requires_approval','approved_by','approved_at','rejection_note','created_at')


class ShowroomPurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ShowroomPurchaseItem
        fields = ['id','product','product_name','quantity','cost','total']
        read_only_fields = ('total',)


class ShowroomPurchaseSerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source='showroom.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = ShowroomPurchaseItemSerializer(many=True)

    class Meta:
        model = ShowroomPurchase
        fields = [
            'id','number','showroom','showroom_name','supplier','supplier_name','location','status','notes','invoice_file','total',
            'created_by','confirmed_by','confirmed_at','created_at','items'
        ]
        read_only_fields = ('number','status','total','confirmed_by','confirmed_at','created_at')

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        purchase = ShowroomPurchase.objects.create(**validated_data)
        for item in items_data:
            ShowroomPurchaseItem.objects.create(purchase=purchase, **item)
        purchase.recalc_total()
        return purchase

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item in items_data:
                ShowroomPurchaseItem.objects.create(purchase=instance, **item)
            instance.recalc_total()
        return instance


class ShowroomStockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    showroom_name = serializers.CharField(source='showroom.name', read_only=True)

    class Meta:
        model = ShowroomStockMovement
        fields = ['id','showroom','showroom_name','location','product','product_name','quantity','movement_type','reference','note','created_by','created_at']
        read_only_fields = ('created_by','created_at')


class ShowroomPayrollEntrySerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source='showroom.name', read_only=True)
    employee_role = serializers.CharField(source='employee.role', read_only=True)

    class Meta:
        model = ShowroomPayrollEntry
        fields = [
            'id','showroom','showroom_name','employee','employee_role','user','period','amount','entry_type',
            'status','note','approved_by','approved_at','created_at'
        ]
        read_only_fields = ('status','approved_by','approved_at','created_at')


class ShowroomTransferSerializer(serializers.Serializer):
    to_showroom = serializers.IntegerField()
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, default='')


class ShowroomShiftSerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source='showroom.name', read_only=True)

    class Meta:
        model = ShowroomShift
        fields = ['id','showroom','showroom_name','name','start_time','end_time','break_minutes','is_active','created_at']
        read_only_fields = ('created_at',)


class ShowroomShiftAssignmentSerializer(serializers.ModelSerializer):
    shift_name = serializers.CharField(source='shift.name', read_only=True)
    showroom = serializers.IntegerField(source='shift.showroom_id', read_only=True)
    employee_user = serializers.CharField(source='employee.user.username', read_only=True)

    class Meta:
        model = ShowroomShiftAssignment
        fields = ['id','shift','shift_name','showroom','employee','employee_user','day_of_week','note','active','created_at']
        read_only_fields = ('created_at','showroom','shift_name','employee_user')


class TemporaryWorkerSerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source='showroom.name', read_only=True)
    worker_type_display = serializers.CharField(source='get_worker_type_display', read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    is_finished = serializers.BooleanField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = TemporaryWorker
        fields = [
            'id','showroom','showroom_name','worker_name','worker_phone','national_id',
            'worker_type','worker_type_display','job_title',
            'start_date','end_date','daily_wage','hourly_wage',
            'days_worked','hours_worked','total_amount',
            'is_paid','payment_date','payment_reference',
            'expense_account','journal_entry','notes','is_active',
            'duration_days','is_finished','created_by','created_by_username',
            'created_at','updated_at'
        ]
        read_only_fields = ('total_amount','created_at','updated_at')


class ShowroomRentPaymentSerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source='showroom.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = ShowroomRentPayment
        fields = [
            'id','showroom','showroom_name','payment_date','amount',
            'status','status_display','actual_payment_date','payment_reference',
            'journal_entry','notes','days_overdue',
            'created_by','created_by_username','created_at','updated_at'
        ]
        read_only_fields = ('created_at','updated_at')
