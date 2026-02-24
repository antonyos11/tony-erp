"""
Admin للتوقيعات الرقمية
"""

from django.contrib import admin
from .models import (
    SignatureProfile, SignatureRequest, Signer, SignatureField,
    Signature, SignatureAuditLog, SignatureTemplate
)


@admin.register(SignatureProfile)
class SignatureProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']


class SignerInline(admin.TabularInline):
    model = Signer
    extra = 0


class SignatureFieldInline(admin.TabularInline):
    model = SignatureField
    extra = 0


@admin.register(SignatureRequest)
class SignatureRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'requester', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['title', 'requester__username']
    raw_id_fields = ['requester']
    inlines = [SignerInline, SignatureFieldInline]
    readonly_fields = ['uuid', 'document_hash']


@admin.register(Signer)
class SignerAdmin(admin.ModelAdmin):
    list_display = ['request', 'user', 'email', 'role', 'is_signed', 'signed_at']
    list_filter = ['role', 'is_signed']
    search_fields = ['email', 'user__username']
    raw_id_fields = ['request', 'user']


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ['signer', 'field', 'ip_address', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['signature_hash', 'created_at']


@admin.register(SignatureAuditLog)
class SignatureAuditLogAdmin(admin.ModelAdmin):
    list_display = ['request', 'user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['request__title']
    readonly_fields = ['request', 'user', 'action', 'details', 'ip_address', 'created_at']


@admin.register(SignatureTemplate)
class SignatureTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'usage_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    raw_id_fields = ['created_by']
