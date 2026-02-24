from django.contrib import admin
from .models import PurchaseBill, PurchaseItem, SupplierPayment
from .models import PurchaseOrder, PurchaseOrderItem
from .models_advanced import (
    PurchaseRequest, PurchaseRequestItem,
    RFQ, RFQItem, RFQSupplier,
    SupplierQuotation, QuotationItem,
    ProductPriceHistory, SupplierLeadTime,
    Shipment, GoodsReceipt, GoodsReceiptItem
)
from typing import Callable, TypeVar, Any

F = TypeVar('F', bound=Callable[..., Any])

def short_desc(text: str):
	def decorator(func: F) -> F:
		setattr(func, 'short_description', text)
		return func
	return decorator


class PurchaseItemInline(admin.TabularInline):
	model = PurchaseItem
	extra = 1


@admin.register(PurchaseBill)
class PurchaseBillAdmin(admin.ModelAdmin):
	list_display = ("number", "supplier", "date", "status", "total", "paid", "remaining", "posted_at")
	list_filter = ("status", "date", "supplier")
	search_fields = ("number", "supplier__name")
	inlines = [PurchaseItemInline]
	readonly_fields = ("posted_at",)

	@short_desc("المتبقي")
	def remaining(self, obj):
		return obj.remaining

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
	list_display = ("number", "supplier", "date", "status", "total")
	list_filter = ("status", "date", "supplier")
	search_fields = ("number", "supplier__name")


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
	list_display = ("order", "product", "location", "quantity", "cost")
	list_filter = ("location",)
# Register your models here.


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
	list_display = ("receipt_number", "supplier", "bill", "date", "amount", "locked")
	list_filter = ("date", "supplier", "locked")
	search_fields = ("receipt_number", "supplier__name", "bill__number")


# =============================
# طلبات الشراء (PR)
# =============================

class PurchaseRequestItemInline(admin.TabularInline):
	model = PurchaseRequestItem
	extra = 1
	fields = ('product', 'quantity', 'unit', 'estimated_price', 'specifications')


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
	list_display = ('number', 'department', 'requested_by', 'date', 'required_date', 'status', 'priority', 'total_estimated_amount')
	list_filter = ('status', 'priority', 'date', 'department')
	search_fields = ('number', 'department', 'requested_by__username')
	readonly_fields = ('number', 'approved_at', 'created_at', 'updated_at')
	inlines = [PurchaseRequestItemInline]
	fieldsets = (
		('المعلومات الأساسية', {
			'fields': ('number', 'department', 'requested_by', 'date', 'required_date', 'status', 'priority')
		}),
		('التفاصيل', {
			'fields': ('notes', 'justification')
		}),
		('الاعتماد', {
			'fields': ('approved_by', 'approved_at', 'approval_notes'),
			'classes': ('collapse',)
		}),
		('التحويل', {
			'fields': ('purchase_order',),
			'classes': ('collapse',)
		}),
	)
	
	@short_desc("المبلغ التقديري")
	def total_estimated_amount(self, obj):
		return f"{obj.total_estimated_amount:,.2f}"


@admin.register(PurchaseRequestItem)
class PurchaseRequestItemAdmin(admin.ModelAdmin):
	list_display = ('request', 'product', 'quantity', 'unit', 'estimated_price', 'total_estimated')
	list_filter = ('request__status', 'product')
	search_fields = ('request__number', 'product__name')


# =============================
# طلب عروض أسعار (RFQ)
# =============================

class RFQItemInline(admin.TabularInline):
	model = RFQItem
	extra = 1
	fields = ('product', 'quantity', 'unit', 'specifications', 'target_price')


class RFQSupplierInline(admin.TabularInline):
	model = RFQSupplier
	extra = 1
	fields = ('supplier', 'email_sent', 'quotation_received', 'notes')


@admin.register(RFQ)
class RFQAdmin(admin.ModelAdmin):
	list_display = ('number', 'title', 'date', 'deadline', 'status', 'created_by')
	list_filter = ('status', 'date', 'deadline')
	search_fields = ('number', 'title')
	readonly_fields = ('number', 'created_at', 'updated_at')
	inlines = [RFQItemInline, RFQSupplierInline]
	fieldsets = (
		('المعلومات الأساسية', {
			'fields': ('number', 'purchase_request', 'title', 'date', 'deadline', 'status')
		}),
		('الشروط والأحكام', {
			'fields': ('terms_conditions', 'payment_terms', 'delivery_terms'),
			'classes': ('collapse',)
		}),
		('ملاحظات', {
			'fields': ('notes', 'created_by')
		}),
	)


@admin.register(RFQItem)
class RFQItemAdmin(admin.ModelAdmin):
	list_display = ('rfq', 'product', 'quantity', 'unit', 'target_price')
	list_filter = ('rfq__status',)
	search_fields = ('rfq__number', 'product__name')


@admin.register(RFQSupplier)
class RFQSupplierAdmin(admin.ModelAdmin):
	list_display = ('rfq', 'supplier', 'invited_date', 'email_sent', 'quotation_received')
	list_filter = ('email_sent', 'quotation_received', 'invited_date')
	search_fields = ('rfq__number', 'supplier__name')


# =============================
# عروض الموردين
# =============================

class QuotationItemInline(admin.TabularInline):
	model = QuotationItem
	extra = 1
	fields = ('rfq_item', 'product', 'quantity', 'unit_price', 'unit', 'brand', 'model')


@admin.register(SupplierQuotation)
class SupplierQuotationAdmin(admin.ModelAdmin):
	list_display = ('number', 'rfq', 'supplier', 'quotation_date', 'valid_until', 'status', 'subtotal', 'total', 'evaluation_score')
	list_filter = ('status', 'quotation_date', 'supplier')
	search_fields = ('number', 'rfq__number', 'supplier__name')
	readonly_fields = ('number', 'subtotal', 'total', 'created_at', 'updated_at')
	inlines = [QuotationItemInline]
	fieldsets = (
		('المعلومات الأساسية', {
			'fields': ('number', 'rfq', 'supplier', 'quotation_date', 'valid_until', 'status')
		}),
		('شروط العرض', {
			'fields': ('payment_terms', 'delivery_time', 'warranty_period')
		}),
		('التكاليف', {
			'fields': ('subtotal', 'shipping_cost', 'tax_amount', 'discount', 'total')
		}),
		('التقييم', {
			'fields': ('evaluation_score', 'evaluation_notes', 'evaluated_by', 'evaluated_at'),
			'classes': ('collapse',)
		}),
		('مرفقات وملاحظات', {
			'fields': ('notes', 'attachments')
		}),
	)


@admin.register(QuotationItem)
class QuotationItemAdmin(admin.ModelAdmin):
	list_display = ('quotation', 'product', 'quantity', 'unit_price', 'total', 'brand', 'model')
	list_filter = ('quotation__status',)
	search_fields = ('quotation__number', 'product__name', 'brand', 'model')


# =============================
# السجل التاريخي للأسعار
# =============================

@admin.register(ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
	list_display = ('product', 'supplier', 'price', 'quantity', 'currency', 'date', 'source')
	list_filter = ('source', 'date', 'supplier', 'currency')
	search_fields = ('product__name', 'supplier__name')
	readonly_fields = ('created_at',)
	date_hierarchy = 'date'


# =============================
# جدول التسليم والشحنات
# =============================

@admin.register(SupplierLeadTime)
class SupplierLeadTimeAdmin(admin.ModelAdmin):
	list_display = ('supplier', 'product', 'product_category', 'lead_time_days', 'min_order_quantity', 'max_order_quantity', 'is_active')
	list_filter = ('is_active', 'supplier')
	search_fields = ('supplier__name', 'product__name', 'product_category')
	list_editable = ('is_active',)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
	list_display = ('number', 'purchase_order', 'supplier', 'status', 'shipped_date', 'estimated_arrival', 'actual_arrival', 'is_delayed', 'total_cost')
	list_filter = ('status', 'shipped_date', 'estimated_arrival')
	search_fields = ('number', 'purchase_order__number', 'tracking_number', 'awb_bl_number')
	readonly_fields = ('number', 'is_delayed', 'total_cost', 'created_at', 'updated_at')
	fieldsets = (
		('المعلومات الأساسية', {
			'fields': ('number', 'purchase_order', 'supplier', 'status')
		}),
		('معلومات الشحن', {
			'fields': ('shipping_method', 'carrier', 'tracking_number', 'awb_bl_number')
		}),
		('التواريخ', {
			'fields': ('shipped_date', 'estimated_arrival', 'actual_arrival', 'is_delayed')
		}),
		('التكاليف', {
			'fields': ('shipping_cost', 'customs_cost', 'insurance_cost', 'total_cost')
		}),
		('مرفقات وملاحظات', {
			'fields': ('notes', 'attachments')
		}),
	)


# =============================
# استلام الواردات
# =============================

class GoodsReceiptItemInline(admin.TabularInline):
	model = GoodsReceiptItem
	extra = 1
	fields = ('purchase_order_item', 'product', 'ordered_quantity', 'received_quantity', 'accepted_quantity', 'rejected_quantity', 'quality_grade')


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
	list_display = ('number', 'purchase_order', 'location', 'receipt_date', 'status', 'quality_status', 'has_variance', 'has_quality_issues')
	list_filter = ('status', 'quality_status', 'receipt_date')
	search_fields = ('number', 'purchase_order__number')
	readonly_fields = ('number', 'has_variance', 'has_quality_issues', 'created_at', 'updated_at')
	inlines = [GoodsReceiptItemInline]
	fieldsets = (
		('المعلومات الأساسية', {
			'fields': ('number', 'purchase_order', 'shipment', 'location', 'receipt_date', 'status', 'quality_status')
		}),
		('الفحص والجودة', {
			'fields': ('inspected_by', 'inspection_date', 'inspection_notes', 'has_quality_issues')
		}),
		('الاستلام', {
			'fields': ('received_by', 'has_variance')
		}),
		('مرفقات وملاحظات', {
			'fields': ('notes', 'attachments')
		}),
	)


@admin.register(GoodsReceiptItem)
class GoodsReceiptItemAdmin(admin.ModelAdmin):
	list_display = ('receipt', 'product', 'ordered_quantity', 'received_quantity', 'accepted_quantity', 'rejected_quantity', 'variance_quantity', 'quality_grade')
	list_filter = ('quality_grade', 'receipt__status')
	search_fields = ('receipt__number', 'product__name')
	readonly_fields = ('variance_quantity', 'variance_percentage')

	def has_change_permission(self, request, obj=None):
		if obj and hasattr(obj, 'receipt') and hasattr(obj.receipt, 'locked') and obj.receipt.locked:
			return False
		return super().has_change_permission(request, obj)

	def has_delete_permission(self, request, obj=None):
		if obj and hasattr(obj, 'receipt') and hasattr(obj.receipt, 'locked') and obj.receipt.locked:
			return False
		return super().has_delete_permission(request, obj)
