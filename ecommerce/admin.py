from django.contrib import admin
from django.utils.html import format_html
from .models import (
    EcommerceSettings, ProductCategory, OnlineProduct, ProductImage,
    Cart, CartItem, Order, OrderItem, ProductReview, Wishlist,
    PaymentGateway, ShippingCompany, SocialMediaIntegration,
    StorePageContent, Coupon, SocialAuthProvider,
    ProductWarranty, WarrantyCard, WarrantyRegistration, WarrantyClaim, WarrantyClaimImage
)


# =====================================================
# إدارة الضمان
# =====================================================

@admin.register(ProductWarranty)
class ProductWarrantyAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration', 'duration_unit', 'requires_registration', 'is_active', 'created_at']
    list_filter = ['is_active', 'requires_registration', 'duration_unit']
    search_fields = ['name', 'description']
    list_editable = ['is_active']


@admin.register(WarrantyCard)
class WarrantyCardAdmin(admin.ModelAdmin):
    list_display = ['warranty_code', 'get_product_name', 'purchase_date', 'warranty_end_date', 'status', 'created_at']
    list_filter = ['status', 'warranty_policy', 'created_at']
    search_fields = ['warranty_code', 'serial_number']
    readonly_fields = ['warranty_code', 'qr_code', 'created_at', 'updated_at']
    raw_id_fields = ['product', 'inventory_product', 'order', 'sales_invoice']
    
    def get_product_name(self, obj):
        if obj.product:
            return obj.product.name
        elif obj.inventory_product:
            return obj.inventory_product.name
        return "-"
    get_product_name.short_description = "المنتج"


@admin.register(WarrantyRegistration)
class WarrantyRegistrationAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'warranty_code_entered', 'purchase_date', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer_name', 'customer_email', 'warranty_code_entered']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['warranty_card', 'user', 'reviewed_by']
    
    actions = ['approve_registrations', 'reject_registrations']
    
    def approve_registrations(self, request, queryset):
        for reg in queryset.filter(status='pending'):
            reg.approve(request.user)
        self.message_user(request, f"تم تفعيل {queryset.count()} ضمان")
    approve_registrations.short_description = "الموافقة على الطلبات المحددة"
    
    def reject_registrations(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"تم رفض {queryset.count()} طلب")
    reject_registrations.short_description = "رفض الطلبات المحددة"


class WarrantyClaimImageInline(admin.TabularInline):
    model = WarrantyClaimImage
    extra = 0


@admin.register(WarrantyClaim)
class WarrantyClaimAdmin(admin.ModelAdmin):
    list_display = ['id', 'warranty_card', 'claim_type', 'contact_name', 'status', 'submitted_at']
    list_filter = ['status', 'claim_type', 'submitted_at']
    search_fields = ['warranty_card__warranty_code', 'contact_name', 'contact_phone']
    raw_id_fields = ['warranty_card', 'assigned_to']
    inlines = [WarrantyClaimImageInline]

