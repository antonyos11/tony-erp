"""
API Views for Quality Control Module - Tony ERP
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Avg, Q

from .models import (
    QualityStandard, InspectionType, QualityInspection,
    InspectionResult, QualityIssue
)
from .serializers import (
    QualityStandardSerializer, InspectionTypeSerializer,
    QualityInspectionSerializer, QualityInspectionCreateSerializer,
    InspectionResultSerializer, QualityIssueSerializer
)


class QualityStandardViewSet(viewsets.ModelViewSet):
    """API ViewSet لمعايير الجودة"""
    queryset = QualityStandard.objects.all()
    serializer_class = QualityStandardSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    filterset_fields = ['category', 'is_active']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InspectionTypeViewSet(viewsets.ModelViewSet):
    """API ViewSet لأنواع الفحص"""
    queryset = InspectionType.objects.prefetch_related('standards').all()
    serializer_class = InspectionTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['is_active']


class QualityInspectionViewSet(viewsets.ModelViewSet):
    """API ViewSet لفحوصات الجودة"""
    queryset = QualityInspection.objects.select_related(
        'inspection_type', 'product', 'inspector'
    ).prefetch_related('results').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'batch_number']
    filterset_fields = ['status', 'inspection_type', 'product', 'inspector']
    ordering_fields = ['inspection_date', 'created_at', 'overall_score']
    ordering = ['-inspection_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return QualityInspectionCreateSerializer
        return QualityInspectionSerializer
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """تحديث حالة الفحص"""
        inspection = self.get_object()
        new_status = request.data.get('status')
        overall_score = request.data.get('overall_score')
        
        if new_status not in dict(QualityInspection.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inspection.status = new_status
        if overall_score:
            inspection.overall_score = overall_score
        inspection.save()
        
        serializer = self.get_serializer(inspection)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_result(self, request, pk=None):
        """إضافة نتيجة فحص"""
        inspection = self.get_object()
        serializer = InspectionResultSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(inspection=inspection)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """إحصائيات الفحوصات"""
        stats = QualityInspection.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            passed=Count('id', filter=Q(status='passed')),
            failed=Count('id', filter=Q(status='failed')),
            conditional=Count('id', filter=Q(status='conditional')),
            avg_score=Avg('overall_score')
        )
        
        # معدل النجاح
        if stats['total'] > 0:
            completed = stats['passed'] + stats['failed'] + stats['conditional']
            success_rate = (stats['passed'] / completed * 100) if completed > 0 else 0
            stats['success_rate'] = round(success_rate, 2)
        else:
            stats['success_rate'] = 0
        
        return Response(stats)


class QualityIssueViewSet(viewsets.ModelViewSet):
    """API ViewSet لمشاكل الجودة"""
    queryset = QualityIssue.objects.select_related(
        'product', 'reported_by', 'inspection'
    ).prefetch_related('actions').all()
    serializer_class = QualityIssueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'title', 'description']
    filterset_fields = ['status', 'severity', 'product']
    ordering_fields = ['reported_date', 'severity']
    ordering = ['-reported_date']
    
    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """حل المشكلة"""
        issue = self.get_object()
        root_cause = request.data.get('root_cause', '')
        
        issue.status = 'resolved'
        issue.resolved_date = timezone.now()
        issue.root_cause = root_cause
        issue.save()
        
        serializer = self.get_serializer(issue)
        return Response(serializer.data)
