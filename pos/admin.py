from django.contrib import admin
from . import models


@admin.register(models.POSSession)
class POSSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'opened_at', 'closed_at', 'opening_balance', 'closing_balance', 'is_open', 'total_sales')
    list_filter = ('is_open', 'opened_at')
    search_fields = ('user__username',)


class POSOrderLineInline(admin.TabularInline):
    model = models.POSOrderLine
    extra = 0


@admin.register(models.POSOrder)
class POSOrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'session', 'customer', 'location', 'status', 'total', 'paid_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('number', 'customer__name')
    inlines = [POSOrderLineInline]


@admin.register(models.POSPayment)
class POSPaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'method', 'created_at')
    list_filter = ('method', 'created_at')
    search_fields = ('order__number',)
