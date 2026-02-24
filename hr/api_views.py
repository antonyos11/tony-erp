"""
HR REST API Views
واجهة برمجية RESTful للموارد البشرية
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Employee, Department, JobPosition
from .api_serializers import (
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    DepartmentSerializer,
    JobPositionSerializer,
)


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    CRUD كامل للموظفين
    GET    /hr/api/v1/employees/          → قائمة الموظفين
    POST   /hr/api/v1/employees/          → إضافة موظف
    GET    /hr/api/v1/employees/{id}/     → تفاصيل موظف
    PUT    /hr/api/v1/employees/{id}/     → تعديل موظف
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'position', 'status', 'gender']
    search_fields = ['first_name', 'last_name', 'arabic_name', 'employee_id', 'national_id', 'phone', 'email']
    ordering_fields = ['first_name', 'hire_date', 'employee_id']
    ordering = ['first_name']

    def get_queryset(self):
        return Employee.objects.select_related('department', 'position', 'user').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeListSerializer
        return EmployeeDetailSerializer

    @action(detail=False, methods=['get'], url_path='active')
    def active_employees(self, request):
        """الموظفين النشطين فقط"""
        employees = self.get_queryset().filter(status='active')
        serializer = EmployeeListSerializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """إحصائيات الموظفين"""
        from django.db.models import Count, Avg
        qs = Employee.objects.all()
        return Response({
            'total': qs.count(),
            'active': qs.filter(status='active').count(),
            'inactive': qs.filter(status='inactive').count(),
            'terminated': qs.filter(status='terminated').count(),
            'by_department': list(
                qs.filter(status='active').values('department__name').annotate(
                    count=Count('id')
                ).order_by('-count')
            ),
            'avg_salary': float(
                qs.filter(status='active').aggregate(avg=Avg('basic_salary'))['avg'] or 0
            ),
        })


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    CRUD للأقسام
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']
    ordering = ['name']


class JobPositionViewSet(viewsets.ModelViewSet):
    """
    CRUD للوظائف
    """
    queryset = JobPosition.objects.select_related('department').all()
    serializer_class = JobPositionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'is_active']
    search_fields = ['title', 'code']
    ordering = ['title']
