from rest_framework import serializers
from .models import ApprovalRequest, ApprovalAction
from django.contrib.auth.models import User


class ApprovalActionSerializer(serializers.ModelSerializer):
    """Serializer for Approval Action"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = ApprovalAction
        fields = [
            'id', 'approval', 'user', 'user_username', 'user_full_name',
            'action', 'action_display', 'note', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ApprovalRequestSerializer(serializers.ModelSerializer):
    """Serializer for Approval Request"""
    
    requested_by_username = serializers.CharField(source='requested_by.username', read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    actions = ApprovalActionSerializer(many=True, read_only=True)
    content_type_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ApprovalRequest
        fields = [
            'id', 'created_at', 'updated_at', 'requested_by',
            'requested_by_username', 'requested_by_name', 'content_type',
            'object_id', 'content_type_name', 'amount', 'reason', 'status',
            'status_display', 'current_level', 'required_levels', 'actions'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.username
    
    def get_content_type_name(self, obj):
        return obj.content_type.model if obj.content_type else None


class ApprovalRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating approval requests"""
    
    class Meta:
        model = ApprovalRequest
        fields = [
            'requested_by', 'content_type', 'object_id', 'amount',
            'reason', 'required_levels'
        ]
    
    def validate(self, data):
        """Validate that the content object exists"""
        content_type = data.get('content_type')
        object_id = data.get('object_id')
        
        if content_type and object_id:
            model_class = content_type.model_class()
            if not model_class.objects.filter(pk=object_id).exists():
                raise serializers.ValidationError(
                    f'{content_type.model} with ID {object_id} does not exist'
                )
        
        return data


class ApprovalActionCreateSerializer(serializers.Serializer):
    """Serializer for creating approval actions"""
    
    action = serializers.ChoiceField(choices=['approve', 'reject', 'comment'])
    note = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate that rejection has a note"""
        if data['action'] == 'reject' and not data.get('note'):
            raise serializers.ValidationError(
                {'note': 'يجب إدخال سبب الرفض'}
            )
        return data


class ApprovalRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing approval requests"""
    
    requested_by_username = serializers.CharField(source='requested_by.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ApprovalRequest
        fields = [
            'id', 'requested_by_username', 'status', 'status_display',
            'amount', 'current_level', 'required_levels', 'created_at'
        ]


class ApprovalStatisticsSerializer(serializers.Serializer):
    """Serializer for approval statistics"""
    
    total_pending = serializers.IntegerField()
    total_approved = serializers.IntegerField()
    total_rejected = serializers.IntegerField()
    total_cancelled = serializers.IntegerField()
    my_pending = serializers.IntegerField()
    my_approved = serializers.IntegerField()
    my_rejected = serializers.IntegerField()
