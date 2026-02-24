"""
إدارة الشؤون المالية
Treasury Management Admin
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import CashPosition, CashFlow, Investment, TreasuryTarget


@admin.register(CashPosition)
class CashPositionAdmin(admin.ModelAdmin):
    list_display = ['position_date', 'bank_balance', 'total_liquidity', 'net_position', 'liquidity_ratio']
    list_filter = ['position_date']
    readonly_fields = ['id', 'total_liquidity', 'net_position', 'liquidity_ratio', 'created_at']


@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):
    list_display = ['forecast_date', 'period_type', 'opening_balance', 'closing_balance', 'accuracy_score']
    list_filter = ['period_type', 'forecast_date']
    readonly_fields = ['id', 'created_at']


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['investment_id', 'investment_type', 'principal_amount', 'status', 'maturity_date']
    list_filter = ['investment_type', 'status', 'maturity_date']
    search_fields = ['investment_id', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معرف الاستثمار'), {
            'fields': ('investment_id', 'investment_type')
        }),
        (_('البيانات'), {
            'fields': ('description', 'principal_amount', 'investment_date', 'maturity_date')
        }),
        (_('العائد'), {
            'fields': ('expected_return_rate', 'expected_return_amount', 'actual_return_amount')
        }),
        (_('الحالة'), {
            'fields': ('status', 'current_value')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
    )


@admin.register(TreasuryTarget)
class TreasuryTargetAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'target_liquidity', 'end_date']
    list_filter = ['status']
    readonly_fields = ['id', 'created_at']
