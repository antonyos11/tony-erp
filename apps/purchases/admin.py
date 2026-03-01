from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderLine


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'date', 'supplier', 'branch', 'status', 'total']
    list_filter = ['status', 'is_taxable', 'branch']
    search_fields = ['order_number', 'supplier__name']
    inlines = [PurchaseOrderLineInline]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
