"""
Admin لمكالمات الفيديو
"""

from django.contrib import admin
from .models import VideoRoom, VideoParticipant, VideoRecording, VideoMessage


class VideoParticipantInline(admin.TabularInline):
    model = VideoParticipant
    extra = 0


@admin.register(VideoRoom)
class VideoRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'room_type', 'is_active', 'scheduled_at', 'created_at']
    list_filter = ['room_type', 'is_active', 'created_at']
    search_fields = ['name']
    raw_id_fields = ['host']
    inlines = [VideoParticipantInline]
    readonly_fields = ['uuid']


@admin.register(VideoRecording)
class VideoRecordingAdmin(admin.ModelAdmin):
    list_display = ['room', 'duration_seconds', 'file_size', 'recorded_at']
    list_filter = ['recorded_at']
