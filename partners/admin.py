from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Customer, Supplier, SupplierDocument, SupplierProduct, Partner, PartnerContact


class PartnerContactInline(admin.TabularInline):
    """عرض جهات الاتصال داخل صفحة الشريك"""
    model = PartnerContact
    extra = 1
    fields = ('contact_name', 'phone', 'notes', 'is_primary')


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'partner_type', 'phone', 'email', 'is_active', 'contacts_count')
    search_fields = ('name', 'phone', 'email')
    list_filter = ('partner_type', 'is_active')
    inlines = [PartnerContactInline]

    def contacts_count(self, obj):
        count = obj.contacts.count()
        if count > 0:
            return format_html('<span style="color: blue;">📞 {}</span>', count)
        return format_html('<span style="color: gray;">-</span>')
    contacts_count.short_description = _('جهات الاتصال')


class SupplierProductInline(admin.TabularInline):
    """عرض منتجات المورد داخل صفحة المورد"""
    model = SupplierProduct
    extra = 1
    fields = ('product', 'supplier_sku', 'price', 'currency', 'minimum_order_quantity', 'lead_time_days', 'is_preferred', 'is_active')
    autocomplete_fields = ['product']


class SupplierDocumentInline(admin.TabularInline):
    """عرض المستندات داخل صفحة المورد"""
    model = SupplierDocument
    extra = 1
    fields = ('document_type', 'title', 'document_number', 'file', 'issue_date', 'expiry_date', 'is_verified')
    readonly_fields = ('uploaded_by', 'uploaded_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
	list_display = ("name", "email", "phone")
	search_fields = ("name", "email", "phone")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
	list_display = ("code", "name", "email", "phone", "supply_type", "raw_material", "products_count", "documents_count")
	search_fields = ("code", "name", "email", "phone", "raw_material")
	list_filter = ("supply_type", "raw_material")
	inlines = [SupplierProductInline, SupplierDocumentInline]

	def products_count(self, obj):
		count = obj.products.count()
		if count > 0:
			return format_html('<span style="color: blue;">📦 {}</span>', count)
		return format_html('<span style="color: gray;">-</span>')
	products_count.short_description = _('عدد المنتجات')

	def documents_count(self, obj):
		count = obj.documents.count()
		if count > 0:
			return format_html('<span style="color: green;">📄 {}</span>', count)
		return format_html('<span style="color: gray;">-</span>')
	documents_count.short_description = _('عدد المستندات')


@admin.register(SupplierDocument)
class SupplierDocumentAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'document_type', 'title', 'document_number', 'expiry_status', 'is_verified', 'uploaded_at')
    list_filter = ('document_type', 'is_verified', 'expiry_date')
    search_fields = ('supplier__name', 'title', 'document_number')
    readonly_fields = ('uploaded_by', 'uploaded_at', 'expiry_status_detail')
    fieldsets = (
        (_('معلومات المستند'), {
            'fields': ('supplier', 'document_type', 'title', 'document_number', 'file')
        }),
        (_('التواريخ'), {
            'fields': ('issue_date', 'expiry_date', 'expiry_status_detail')
        }),
        (_('معلومات إضافية'), {
            'fields': ('notes', 'is_verified', 'uploaded_by', 'uploaded_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    def expiry_status(self, obj):
        """حالة انتهاء الصلاحية"""
        if not obj.expiry_date:
            return format_html('<span style="color: gray;">-</span>')
        
        if obj.is_expired:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ منتهي</span>')
        
        days = obj.days_until_expiry
        if days and days <= 30:
            return format_html('<span style="color: orange;">⏰ {} يوم</span>', days)
        
        return format_html('<span style="color: green;">✓ ساري</span>')
    expiry_status.short_description = _('الصلاحية')
    
    def expiry_status_detail(self, obj):
        """تفاصيل حالة انتهاء الصلاحية"""
        if not obj.expiry_date:
            return _('لا يوجد تاريخ انتهاء')
        
        if obj.is_expired:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ منتهي الصلاحية</span>')
        
        days = obj.days_until_expiry
        if days:
            if days <= 30:
                return format_html('<span style="color: orange;">⏰ باقي {} يوم على الانتهاء</span>', days)
            else:
                return format_html('<span style="color: green;">✓ ساري - باقي {} يوم</span>', days)
        
        return _('ساري')
    expiry_status_detail.short_description = _('حالة الصلاحية')


@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'price', 'currency', 'is_preferred', 'is_active', 'last_purchase_info')
    list_filter = ('is_preferred', 'is_active', 'currency', 'supplier')
    search_fields = ('product__name', 'product__sku', 'supplier__name', 'supplier_sku')
    autocomplete_fields = ['product', 'supplier']

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('supplier', 'product', 'supplier_sku')
        }),
        (_('التسعير'), {
            'fields': ('price', 'currency', 'last_purchase_price', 'last_purchase_date')
        }),
        (_('شروط التوريد'), {
            'fields': ('minimum_order_quantity', 'lead_time_days', 'is_preferred', 'is_active')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def last_purchase_info(self, obj):
        """معلومات آخر شراء"""
        if obj.last_purchase_date and obj.last_purchase_price:
            return format_html(
                '<span style="color: green;">{} ج في {}</span>',
                obj.last_purchase_price,
                obj.last_purchase_date.strftime('%Y-%m-%d')
            )
        return format_html('<span style="color: gray;">-</span>')
    last_purchase_info.short_description = _('آخر شراء')


# Register your models here.
