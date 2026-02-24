from django.contrib import admin
from . import models


@admin.register(models.Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate_number", "name", "status", "current_odometer")
    search_fields = ("plate_number", "name")
    list_filter = ("status",)


@admin.register(models.Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "license_number", "active")
    search_fields = ("name", "phone", "license_number")
    list_filter = ("active",)


@admin.register(models.VehicleExpense)
class VehicleExpenseAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "category", "amount", "date", "journal_entry_status")
    list_filter = ("category", "date")
    search_fields = ("vehicle__plate_number", "description")

    def journal_entry_status(self, obj):
        return 'تم' if obj.journal_entry_id else 'لا'
    journal_entry_status.short_description = 'قيد'


@admin.register(models.Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "driver", "origin", "destination", "start_time", "distance_km")
    list_filter = ("vehicle", "driver")
    search_fields = ("origin", "destination", "vehicle__plate_number", "driver__name")


@admin.register(models.VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "doc_type", "expiry_date", "uploaded_at")
    list_filter = ("doc_type",)
    search_fields = ("vehicle__plate_number", "doc_type")


@admin.register(models.FleetAccountingSettings)
class FleetAccountingSettingsAdmin(admin.ModelAdmin):
    list_display = ("maintenance_account", "fuel_account", "default_credit_account", "auto_create_journals", "updated_at")
    fieldsets = (
        (None, {"fields": ("auto_create_journals",)}),
        ("حسابات المصروفات", {"fields": ("maintenance_account", "license_account", "fuel_account", "fine_account", "other_expense_account")}),
        ("الحساب الدائن", {"fields": ("default_credit_account",)}),
    )

    def has_add_permission(self, request):
        # السماح بسجل واحد فقط
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)


@admin.register(models.DriverViolation)
class DriverViolationAdmin(admin.ModelAdmin):
    list_display = ("driver", "vehicle", "violation_type", "date", "amount", "is_paid")
    list_filter = ("is_paid", "date")
    search_fields = ("driver__name", "violation_type", "vehicle__plate_number")


@admin.register(models.DriverAdvance)
class DriverAdvanceAdmin(admin.ModelAdmin):
    list_display = ("driver", "date", "amount", "status", "remaining")
    list_filter = ("status", "date")
    search_fields = ("driver__name",)

    def remaining(self, obj):
        return obj.remaining_amount
    remaining.short_description = 'المتبقي'


@admin.register(models.DriverLocationPing)
class DriverLocationPingAdmin(admin.ModelAdmin):
    list_display = ("driver", "vehicle", "trip", "recorded_at", "latitude", "longitude", "source")
    list_filter = ("driver", "vehicle", "source")
    search_fields = ("driver__name", "vehicle__plate_number", "source")
