"""
تسجيل نماذج الفروع المتقدمة في لوحة التحكم
"""

from django.contrib import admin
from django.utils.html import format_html

from branches.models_advanced import (
    BranchTarget,
    InterBranchTransfer,
    InterBranchTransferItem,
    BranchProfitability,
)


@admin.register(BranchTarget)
class BranchTargetAdmin(admin.ModelAdmin):
    list_display = [
        'branch', 'period', 'sales_target', 'actual_sales',
        'sales_achievement_display', 'new_customers_target',
        'overall_achievement'
    ]
    list_filter = ['branch', 'period']
    search_fields = ['branch__name']

    @admin.display(description='تحقيق المبيعات %')
    def sales_achievement_display(self, obj):
        pct = obj.sales_achievement
        color = 'green' if pct >= 100 else ('orange' if pct >= 75 else 'red')
        return format_html(
            '<span style="color:{};font-weight:bold">{}%</span>',
            color, pct
        )


class InterBranchTransferItemInline(admin.TabularInline):
    model = InterBranchTransferItem
    extra = 1


@admin.register(InterBranchTransfer)
class InterBranchTransferAdmin(admin.ModelAdmin):
    list_display = [
        'transfer_number', 'from_branch', 'to_branch',
        'status', 'total_items', 'request_date'
    ]
    list_filter = ['status', 'from_branch', 'to_branch']
    search_fields = ['transfer_number']
    inlines = [InterBranchTransferItemInline]
    readonly_fields = [
        'transfer_number', 'request_date', 'approval_date',
        'ship_date', 'receive_date'
    ]
    raw_id_fields = ['requested_by', 'approved_by', 'received_by']


@admin.register(BranchProfitability)
class BranchProfitabilityAdmin(admin.ModelAdmin):
    list_display = [
        'branch', 'period', 'net_revenue', 'gross_profit',
        'gross_profit_margin', 'net_profit', 'net_profit_margin',
        'is_profitable_display'
    ]
    list_filter = ['branch', 'period']

    @admin.display(description='مربح', boolean=True)
    def is_profitable_display(self, obj):
        return obj.is_profitable

    fieldsets = (
        ('معلومات عامة', {
            'fields': ('branch', 'period', 'calculated_by', 'notes')
        }),
        ('الإيرادات', {
            'fields': ('total_revenue', 'returns_amount')
        }),
        ('التكاليف', {
            'fields': ('cost_of_goods',)
        }),
        ('المصاريف التشغيلية', {
            'fields': (
                'salary_expense', 'rent_expense', 'utilities_expense',
                'marketing_expense', 'other_expenses'
            )
        }),
    )
