from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_username', 'title', 'message',
            'level', 'level_display', 'is_read', 'created_at'
        ]
        read_only_fields = ['created_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications"""
    
    class Meta:
        model = Notification
        fields = ['user', 'title', 'message', 'level']


class NotificationMarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='List of notification IDs to mark as read. If empty, marks all as read.'
    )
    
    def validate_notification_ids(self, value):
        """Validate that all IDs exist"""
        if value:
            existing_ids = set(Notification.objects.filter(id__in=value).values_list('id', flat=True))
            invalid_ids = set(value) - existing_ids
            if invalid_ids:
                raise serializers.ValidationError(
                    f'Invalid notification IDs: {invalid_ids}'
                )
        return value


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing notifications"""
    
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'title', 'level', 'level_display', 'is_read', 'created_at']
