from rest_framework import viewsets, mixins, status, serializers
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from django.conf import settings
from django.http import FileResponse, Http404
from pathlib import Path
from exports.models import DataExport
from exports.tasks import run_data_export


# DataExportSerializer defined locally to avoid serializers package conflict
class DataExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExport
        fields = [
            'id','export_name','export_type','export_format','parameters','status','progress',
            'file_path','file_size','created_at','completed_at','download_count','expires_at','error_message'
        ]
        read_only_fields = ['status','progress','file_path','file_size','created_at','completed_at','download_count','expires_at','error_message']

class ExportsBurstThrottle(UserRateThrottle):
    scope = 'exports_burst'

class ExportsDayThrottle(UserRateThrottle):
    scope = 'exports_day'


class DataExportViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    queryset = DataExport.objects.all()
    serializer_class = DataExportSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['export_type','status']
    ordering = ['-created_at']

    throttle_classes = [ExportsBurstThrottle, ExportsDayThrottle]

    def perform_create(self, serializer):
        from django.conf import settings
        obj = serializer.save(requested_by=self.request.user, status='pending', progress=0)
        # set default expiry (hours)
        expiry_hours = getattr(settings, 'EXPORT_EXPIRY_HOURS', 24)
        obj.set_default_expiry(expiry_hours)
        run_data_export.delay(obj.id)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        export = self.get_object()
        if export.status != 'completed' or not export.file_path:
            return Response({'detail': 'Not ready'}, status=400)
        if export.expires_at and export.expires_at < timezone.now():
            return Response({'detail': 'Expired'}, status=410)
        file_abspath = Path(settings.MEDIA_ROOT) / export.file_path
        if not file_abspath.exists():
            raise Http404
        export.download_count += 1
        export.save(update_fields=['download_count'])
        return FileResponse(open(file_abspath, 'rb'), as_attachment=True, filename=file_abspath.name)
