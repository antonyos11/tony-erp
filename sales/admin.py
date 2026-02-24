from django.contrib import admin
from .models import Invoice, InvoiceItem, FieldVisit, CollectionTask, InvoicePayment

# استيراد Admin للميزات المحسنة
from .invoice_admin import (
    InvoiceTemplateAdmin,
    InvoiceAutosaveAdmin,
    InvoiceAttachmentAdmin,
    InvoiceHistoryAdmin,
    CustomerCreditLimitAdmin
)


class InvoiceItemInline(admin.TabularInline):
	model = InvoiceItem
	extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
	list_display = ("number", "customer", "date", "total", "paid")
	search_fields = ("number",)
	inlines = [InvoiceItemInline]


@admin.register(FieldVisit)
class FieldVisitAdmin(admin.ModelAdmin):
	list_display = ("visit_date", "employee", "customer", "outcome", "next_action_date")
	list_filter = ("outcome",)
	search_fields = ("subject", "notes", "customer__name", "employee__arabic_name")


@admin.register(CollectionTask)
class CollectionTaskAdmin(admin.ModelAdmin):
	list_display = ("customer", "invoice", "due_date", "amount_due", "status", "assigned_to")
	list_filter = ("status",)
	search_fields = ("customer__name", "invoice__number")


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
	list_display = ("receipt_number", "invoice", "customer", "amount", "date", "payment_method", "printed_count", "locked")
	list_filter = ("payment_method", "locked")
	search_fields = ("receipt_number", "invoice__number", "customer__name", "reference")
	readonly_fields = ("receipt_number", "created_at", "created_by", "first_printed_at", "printed_count")

	def has_change_permission(self, request, obj=None):
		if obj and obj.locked:
			# السماح بعرض التفاصيل فقط
			if request.method in ("POST", "PUT", "PATCH"):
				return False
		return super().has_change_permission(request, obj)

	def has_delete_permission(self, request, obj=None):
		if obj and obj.locked:
			return False
		return super().has_delete_permission(request, obj)

	def save_model(self, request, obj, form, change):
		if not change and not obj.created_by:
			obj.created_by = request.user
		super().save_model(request, obj, form, change)

# Register your models here.
