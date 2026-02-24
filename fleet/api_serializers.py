from rest_framework import serializers
from .models import Vehicle, Driver, Trip, VehicleExpense, VehicleDocument, DriverViolation, DriverAdvance, DriverLocationPing

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['id','name','phone','license_number','license_expiry','active','notes']

class VehicleSerializer(serializers.ModelSerializer):
    total_expenses = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ['id','name','plate_number','type','model_year','status','current_odometer','notes','total_expenses']

    def get_total_expenses(self, obj):
        return obj.total_expenses

class VehicleExpenseSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(source='vehicle.plate_number', read_only=True)
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    advance_remaining = serializers.SerializerMethodField()
    class Meta:
        model = VehicleExpense
        fields = ['id','vehicle','vehicle_plate','driver','driver_name','category','description','amount','date','advance','advance_remaining','journal_entry']
        read_only_fields = ['journal_entry','advance_remaining']

    def get_advance_remaining(self, obj):
        if obj.advance_id:
            try:
                return obj.advance.remaining_amount
            except Exception:
                return None
        return None

class TripSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(source='vehicle.plate_number', read_only=True)
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    class Meta:
        model = Trip
        fields = ['id','vehicle','vehicle_plate','driver','driver_name','start_time','end_time','origin','destination','distance_km','purpose','notes','duration_hours']
        read_only_fields = ['duration_hours']

class VehicleDocumentSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(source='vehicle.plate_number', read_only=True)
    class Meta:
        model = VehicleDocument
        fields = ['id','vehicle','vehicle_plate','doc_type','file','expiry_date','notes','uploaded_at']
        read_only_fields = ['uploaded_at']


class DriverViolationSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    vehicle_plate = serializers.CharField(source='vehicle.plate_number', read_only=True)
    class Meta:
        model = DriverViolation
        fields = ['id','driver','driver_name','vehicle','vehicle_plate','violation_type','date','amount','is_paid','receipt','notes']


class DriverAdvanceSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    utilized_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    class Meta:
        model = DriverAdvance
        fields = ['id','driver','driver_name','date','amount','description','status','settlement_date','notes','utilized_amount','remaining_amount']
        read_only_fields = ['status','settlement_date','utilized_amount','remaining_amount']

    def get_utilized_amount(self, obj):
        return obj.utilized_amount

    def get_remaining_amount(self, obj):
        return obj.remaining_amount


class DriverLocationPingSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    vehicle_plate = serializers.CharField(source='vehicle.plate_number', read_only=True)

    class Meta:
        model = DriverLocationPing
        fields = [
            'id',
            'driver', 'driver_name',
            'vehicle', 'vehicle_plate',
            'trip',
            'latitude', 'longitude',
            'accuracy_m', 'speed_mps', 'heading_deg',
            'recorded_at', 'source',
        ]
