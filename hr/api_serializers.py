"""
HR REST API Serializers
سيرياليزرز واجهة الموارد البشرية
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Employee, Department, JobPosition


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.CharField(source='head.get_full_name', read_only=True, default=None)
    employees_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'description',
            'head', 'head_name', 'budget', 'cost_center',
            'is_active', 'employees_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_employees_count(self, obj):
        return obj.employees.filter(status='active').count()


class JobPositionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = JobPosition
        fields = [
            'id', 'title', 'code', 'department', 'department_name',
            'description', 'requirements',
            'min_salary', 'max_salary',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class EmployeeListSerializer(serializers.ModelSerializer):
    """Serializer مُبسّط للقوائم"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'full_name', 'arabic_name',
            'department', 'department_name',
            'position', 'position_title',
            'status', 'phone', 'email',
            'hire_date',
        ]

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """Serializer مُفصّل"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    full_name = serializers.SerializerMethodField()
    total_salary = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'user',
            'first_name', 'last_name', 'arabic_name', 'full_name',
            'national_id', 'passport_number',
            'gender', 'birth_date', 'marital_status',
            'phone', 'email', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
            'department', 'department_name',
            'position', 'position_title',
            'hire_date', 'termination_date', 'status',
            'basic_salary', 'housing_allowance',
            'transportation_allowance', 'other_allowances',
            'total_salary',
            'bank_name', 'bank_account_number', 'iban',
            'fingerprint_id', 'rfid_card_number', 'attendance_exempt',
            'photo', 'created_at', 'updated_at',
        ]
        read_only_fields = ['employee_id', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    @extend_schema_field(serializers.FloatField())
    def get_total_salary(self, obj):
        return float(
            (obj.basic_salary or 0)
            + (obj.housing_allowance or 0)
            + (obj.transportation_allowance or 0)
            + (obj.other_allowances or 0)
        )
