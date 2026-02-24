from django.contrib import admin
from .models import (
	Product, Location, Stock,
	StockTransfer, StockTransferItem,
	StockBatch, Receiving, ReceivingItem,
	Issue, IssueItem, StockCount, StockCountItem,
	PrinterConfiguration, Category, SupplierProductPrice,
	ProductTemplate
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ("name", "parent", "product_count", "is_active", "sort_order")
	list_filter = ("is_active", "parent")
	search_fields = ("name", "description")
	list_editable = ("sort_order", "is_active")
	ordering = ("sort_order", "name")
	fieldsets = (
		(None, {"fields": ("name", "description", "parent")}),
		("الإعدادات", {"fields": ("image", "is_active", "sort_order")}),
	)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ("sku", "name", "category", "price", "effective_price", "promo_percent", "promo_price", "is_promo_active")
	search_fields = ("sku", "name")
	list_filter = ("is_promo_active", "category")
	fieldsets = (
		(None, {"fields": ("sku", "name", "description", "category", "price", "cost", "min_stock")}),
		("العرض والتسعير", {"fields": ("is_promo_active", "promo_percent", "promo_price", "promo_start", "promo_end")}),
	)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
	list_display = ("code", "name")
	search_fields = ("code", "name")


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
	list_display = ("product", "location", "quantity")

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
	list_display = ("number", "source", "destination", "status", "date")
	readonly_fields = ("number",)


class StockTransferItemInline(admin.TabularInline):
	model = StockTransferItem
	extra = 0


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
	list_display = ("product", "location", "lot_number", "quantity", "unit_cost", "received_at")
	list_filter = ("location", "product")


class ReceivingItemInline(admin.TabularInline):
	model = ReceivingItem
	extra = 0


@admin.register(Receiving)
class ReceivingAdmin(admin.ModelAdmin):
	list_display = ("number", "supplier_name", "location", "status", "receive_date", "quality_checked")
	inlines = [ReceivingItemInline]
	readonly_fields = ("number",)


class IssueItemInline(admin.TabularInline):
	model = IssueItem
	extra = 0


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
	list_display = ("number", "location", "to_department", "status", "issue_date", "allocation_method")
	inlines = [IssueItemInline]
	readonly_fields = ("number",)


class StockCountItemInline(admin.TabularInline):
	model = StockCountItem
	extra = 0


@admin.register(StockCount)
class StockCountAdmin(admin.ModelAdmin):
	list_display = ("number", "location", "status", "count_date")
	inlines = [StockCountItemInline]
	readonly_fields = ("number",)


@admin.register(PrinterConfiguration)
class PrinterConfigurationAdmin(admin.ModelAdmin):
	list_display = ("name", "printer_type", "document_type", "connection_type", "is_default", "is_active", "total_prints")
	list_filter = ("printer_type", "document_type", "is_active", "is_default")
	search_fields = ("name", "ip_address")
	fieldsets = (
		("معلومات أساسية", {
			"fields": ("name", "printer_type", "document_type", "is_default", "is_active")
		}),
		("إعدادات الاتصال", {
			"fields": ("connection_type", "ip_address", "port", "usb_device_path", "shared_printer_name")
		}),
		("إعدادات الطباعة", {
			"fields": ("paper_size", "dpi", "label_width_mm", "label_height_mm")
		}),
		("إحصائيات", {
			"fields": ("total_prints", "last_print_at"),
			"classes": ("collapse",)
		}),
	)
	readonly_fields = ("total_prints", "last_print_at")


@admin.register(SupplierProductPrice)
class SupplierProductPriceAdmin(admin.ModelAdmin):
	"""إدارة أسعار المنتجات حسب المورد"""
	list_display = ('product', 'supplier', 'cost', 'currency', 'is_active', 'is_preferred_badge', 'effective_date')
	list_filter = ('is_active', 'currency', 'supplier', 'product__category')
	search_fields = ('product__name', 'product__sku', 'supplier__name')
	list_editable = ('is_active',)
	date_hierarchy = 'effective_date'

	fieldsets = (
		(None, {
			'fields': ('product', 'supplier', 'cost', 'currency')
		}),
		('شروط الشراء', {
			'fields': ('min_order_qty', 'lead_time_days')
		}),
		('الحالة', {
			'fields': ('is_active', 'effective_date', 'notes')
		}),
	)

	readonly_fields = ('effective_date',)

	def is_preferred_badge(self, obj):
		"""عرض شارة إذا كان المورد المفضل"""
		if obj.is_preferred:
			return '⭐ مفضل'
		return '-'
	is_preferred_badge.short_description = 'المورد المفضل'

	def save_model(self, request, obj, form, change):
		"""حفظ مع تحديث سعر المنتج إذا كان المورد المفضل"""
		super().save_model(request, obj, form, change)

		# تحديث أسعار وحدات التعبئة إذا كان المورد المفضل
		if obj.is_preferred:
			from inventory.models import PackagingUnit
			for pu in PackagingUnit.objects.filter(product=obj.product):
				pu.calculated_price = pu.calculate_price()
				pu.save(update_fields=['calculated_price', 'updated_at'])


@admin.register(ProductTemplate)
class ProductTemplateAdmin(admin.ModelAdmin):
	"""إدارة قوالب المنتجات"""
	list_display = ('name', 'product_type', 'raw_material_type', 'category', 'usage_count', 'is_active', 'created_at')
	list_filter = ('product_type', 'raw_material_type', 'is_active', 'category')
	search_fields = ('name', 'description')
	list_editable = ('is_active',)
	readonly_fields = ('usage_count', 'created_at', 'updated_at')
	
	fieldsets = (
		('معلومات أساسية', {
			'fields': ('name', 'description', 'product_type', 'raw_material_type', 'category')
		}),
		('وحدات القياس', {
			'fields': ('purchase_uom', 'usage_uom', 'conversion_factor', 'auto_calculate_conversion')
		}),
		('الأبعاد', {
			'fields': ('length', 'width', 'height'),
			'classes': ('collapse',)
		}),
		('الموردين والمخزون', {
			'fields': ('preferred_supplier', 'min_stock')
		}),
		('الحالة والإحصائيات', {
			'fields': ('is_active', 'usage_count', 'created_at', 'updated_at', 'created_by'),
			'classes': ('collapse',)
		}),
	)


# Import advanced admin registrations
try:
    from . import admin_advanced  # noqa: F401
except ImportError:
    pass

