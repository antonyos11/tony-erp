from django.contrib import admin
from .models import ApprovalRequest, ApprovalAction

@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ('id','content_type','object_id','requested_by','status','current_level','required_levels','created_at')
    list_filter = ('status','content_type','created_at')
    search_fields = ('id','requested_by__username','reason')

@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ('approval','user','action','created_at')
    list_filter = ('action','created_at')
    search_fields = ('approval__id','user__username')