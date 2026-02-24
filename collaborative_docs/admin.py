"""
Admin للمستندات التعاونية
"""

from django.contrib import admin
from .models import (
    Document, DocumentFolder, DocumentCollaborator,
    DocumentVersion, DocumentComment, DocumentActivity
)


class DocumentCollaboratorInline(admin.TabularInline):
    model = DocumentCollaborator
    extra = 0
    raw_id_fields = ['user', 'added_by']


@admin.register(DocumentFolder)
class DocumentFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'is_shared', 'created_at']
    list_filter = ['is_shared', 'created_at']
    search_fields = ['name']
    raw_id_fields = ['owner', 'parent']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'doc_type', 'owner', 'is_public', 'view_count', 'updated_at']
    list_filter = ['doc_type', 'is_public', 'is_archived', 'created_at']
    search_fields = ['title']
    raw_id_fields = ['owner', 'folder', 'last_edited_by']
    inlines = [DocumentCollaboratorInline]
    readonly_fields = ['uuid', 'view_count']


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version_number', 'created_by', 'created_at']
    list_filter = ['created_at']
    raw_id_fields = ['document', 'created_by']


@admin.register(DocumentComment)
class DocumentCommentAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'is_resolved', 'created_at']
    list_filter = ['is_resolved', 'created_at']
    raw_id_fields = ['document', 'user', 'parent']


@admin.register(DocumentActivity)
class DocumentActivityAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'activity_type', 'created_at']
    list_filter = ['activity_type', 'created_at']
    raw_id_fields = ['document', 'user']
