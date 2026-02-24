from django.contrib import admin
from .models import License, LicenseRenewal, GovernmentPermit

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ['license_number', 'name', 'license_type', 'issue_date', 'expiry_date',
                    'status', 'responsible_person']
    list_filter = ['status', 'license_type', 'expiry_date']
    search_fields = ['license_number', 'name', 'issuing_authority']

@admin.register(LicenseRenewal)
class LicenseRenewalAdmin(admin.ModelAdmin):
    list_display = ['license', 'renewal_date', 'new_expiry_date', 'renewal_fee', 
                    'payment_status', 'processed_by']
    list_filter = ['payment_status', 'renewal_date']
    search_fields = ['license__license_number']

@admin.register(GovernmentPermit)
class GovernmentPermitAdmin(admin.ModelAdmin):
    list_display = ['permit_number', 'title', 'permit_type', 'government_entity',
                    'status', 'application_date', 'approval_date']
    list_filter = ['status', 'permit_type', 'application_date']
    search_fields = ['permit_number', 'title', 'government_entity']
