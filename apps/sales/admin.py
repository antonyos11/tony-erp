"""
تسجيل نماذج المبيعات في لوحة الإدارة
"""
from django.contrib import admin
from .models import PriceList, PriceListItem, Customer, SalesInvoice, SalesInvoiceLine, SalesReturn


class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 1


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_type', 'discount_percentage', 'is_active']
    list_filter = ['price_type', 'is_active']
    search_fields = ['name']
    ordering = ['name']
    inlines = [PriceListItemInline]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'customer_type', 'phone', 'governorate', 'credit_limit', 'is_active']
    list_filter = ['customer_type', 'governorate', 'is_active']
    search_fields = ['code', 'name', 'phone', 'tax_number']
    ordering = ['code']


class SalesInvoiceLineInline(admin.TabularInline):
    model = SalesInvoiceLine
    extra = 1


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'date', 'customer', 'branch', 'status', 'payment_method', 'total', 'paid_amount', 'remaining_amount']
    list_filter = ['status', 'payment_method', 'sale_channel', 'branch', 'is_taxable']
    search_fields = ['invoice_number', 'customer__name', 'customer__code']
    ordering = ['-date', '-invoice_number']
    inlines = [SalesInvoiceLineInline]


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    list_display = ['return_number', 'date', 'customer', 'original_invoice', 'status', 'total']
    list_filter = ['status', 'branch']
    search_fields = ['return_number', 'customer__name', 'original_invoice__invoice_number']
    ordering = ['-date']

