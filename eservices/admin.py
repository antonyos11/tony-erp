"""
تسجيل نماذج الخدمات الإلكترونية في لوحة الإدارة - Tony ERP
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    ServiceCategory, ServiceProvider, EService, MobileOperator,
    RechargePackage, BillType, ServiceTransaction, MobileRecharge,
    BillPayment, MoneyTransfer, ServiceReport
)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'name']


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'commission_rate', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(EService)
class EServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'provider', 'service_type', 'base_fee', 'is_active']
    list_filter = ['category', 'provider', 'service_type', 'is_active', 'is_featured']
    search_fields = ['name', 'code']
    ordering = ['category', 'name']


@admin.register(MobileOperator)
class MobileOperatorAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'prefixes', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


@admin.register(RechargePackage)
class RechargePackageAdmin(admin.ModelAdmin):
    list_display = ['operator', 'name', 'amount', 'validity_days', 'is_active']
    list_filter = ['operator', 'is_active']
    ordering = ['operator', 'order', 'amount']


@admin.register(BillType)
class BillTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'service_fee', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


class MobileRechargeInline(admin.StackedInline):
    model = MobileRecharge
    extra = 0


class BillPaymentInline(admin.StackedInline):
    model = BillPayment
    extra = 0


class MoneyTransferInline(admin.StackedInline):
    model = MoneyTransfer
    extra = 0


@admin.register(ServiceTransaction)
class ServiceTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'service', 'user', 'amount', 'fee', 'total', 'status', 'created_at']
    list_filter = ['status', 'service__service_type', 'created_at']
    search_fields = ['transaction_id', 'service_number', 'user__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['transaction_id', 'created_at', 'processed_at', 'completed_at']
    inlines = [MobileRechargeInline, BillPaymentInline, MoneyTransferInline]


@admin.register(ServiceReport)
class ServiceReportAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_transactions', 'total_amount', 'total_fees', 'successful_count', 'failed_count']
    date_hierarchy = 'date'
    ordering = ['-date']
