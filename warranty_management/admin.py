from django.contrib import admin
from .models import WarrantyPolicy, Warranty, WarrantyClaim

@admin.register(WarrantyPolicy)
class WarrantyPolicyAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'duration_months', 'coverage_type', 'cost', 'is_active']
    list_filter = ['coverage_type', 'is_active']
    search_fields = ['name', 'product__name']

@admin.register(Warranty)
class WarrantyAdmin(admin.ModelAdmin):
    list_display = ['warranty_number', 'customer', 'product', 'start_date', 'end_date', 'status']
    list_filter = ['status', 'start_date']
    search_fields = ['warranty_number', 'customer__name', 'serial_number']

@admin.register(WarrantyClaim)
class WarrantyClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_number', 'warranty', 'claim_date', 'status', 'repair_cost', 'handled_by']
    list_filter = ['status', 'claim_date']
    search_fields = ['claim_number', 'warranty__warranty_number']
