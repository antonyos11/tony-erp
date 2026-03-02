"""
Admin عروض الأسعار — RITA ERP
"""
from django.contrib import admin
from apps.quotations.models import Quotation, QuotationLine, QuotationFollowUp


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 0
    readonly_fields = ('subtotal', 'estimated_cost', 'estimated_profit')
    fields = (
        'product', 'description', 'quantity', 'unit_price',
        'discount_percentage', 'subtotal', 'estimated_cost', 'estimated_profit',
        'notes', 'sort_order',
    )


class QuotationFollowUpInline(admin.TabularInline):
    model = QuotationFollowUp
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('date', 'follow_up_type', 'result', 'notes', 'next_follow_up_date')


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        'quotation_number', 'customer_display_name', 'branch',
        'status', 'total', 'date', 'valid_until',
    )
    list_filter = ('status', 'branch', 'is_taxable', 'delivery_required')
    search_fields = (
        'quotation_number', 'customer__name',
        'prospect_name', 'prospect_phone',
    )
    readonly_fields = (
        'quotation_number', 'subtotal', 'discount_amount',
        'taxable_amount', 'tax_amount', 'total', 'created_at', 'updated_at',
    )
    inlines = [QuotationLineInline, QuotationFollowUpInline]
    ordering = ['-date']

    fieldsets = (
        ('بيانات العرض', {
            'fields': (
                'quotation_number', 'date', 'valid_until',
                'branch', 'salesperson', 'status', 'revision_number',
            ),
        }),
        ('العميل', {
            'fields': (
                'customer',
                ('prospect_name', 'prospect_phone', 'prospect_email'),
                ('prospect_company', 'prospect_address'),
            ),
        }),
        ('الأسعار', {
            'fields': (
                'price_list', 'discount_percentage', 'is_taxable',
                ('subtotal', 'discount_amount'),
                ('taxable_amount', 'tax_amount'),
                'total',
            ),
        }),
        ('التوصيل', {
            'fields': (
                'delivery_required', 'delivery_address',
                'delivery_fee', 'estimated_delivery_days',
            ),
            'classes': ('collapse',),
        }),
        ('الشروط والملاحظات', {
            'fields': (
                'payment_terms', 'terms_and_conditions',
                'customer_notes', 'internal_notes',
            ),
            'classes': ('collapse',),
        }),
        ('المتابعة', {
            'fields': (
                'follow_up_date', 'converted_invoice',
                'rejection_reason', 'lost_to_competitor',
            ),
            'classes': ('collapse',),
        }),
    )


@admin.register(QuotationLine)
class QuotationLineAdmin(admin.ModelAdmin):
    list_display = ('quotation', 'product', 'quantity', 'unit_price', 'subtotal')
    list_filter = ('product',)
    search_fields = ('quotation__quotation_number', 'product__name')


@admin.register(QuotationFollowUp)
class QuotationFollowUpAdmin(admin.ModelAdmin):
    list_display = ('quotation', 'date', 'follow_up_type', 'result', 'next_follow_up_date')
    list_filter = ('follow_up_type', 'result')
    search_fields = ('quotation__quotation_number', 'notes')
