from rest_framework import serializers
from exports.models import DataExport

class DataExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExport
        fields = [
            'id','export_name','export_type','export_format','parameters','status','progress',
            'file_path','file_size','created_at','completed_at','download_count','expires_at','error_message'
        ]
        read_only_fields = ['status','progress','file_path','file_size','created_at','completed_at','download_count','expires_at','error_message']
