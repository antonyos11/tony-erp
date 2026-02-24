"""
تسجيل النماذج المحاسبية المتقدمة في لوحة التحكم
"""

from django.contrib import admin

from accounting.models_advanced import AccountingPeriod


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'fiscal_year', 'period_type',
        'start_date', 'end_date', 'is_open'
    ]
    list_filter = ['fiscal_year', 'is_open', 'period_type']
    readonly_fields = ['closed_by', 'closed_at']
    actions = ['close_periods']

    @admin.action(description='إقفال الفترات المحددة')
    def close_periods(self, request, queryset):
        closed_count = 0
        for period in queryset.filter(is_open=True):
            try:
                period.close_period(request.user)
                closed_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"خطأ في إقفال {period.name}: {e}",
                    level='error'
                )
        if closed_count:
            self.message_user(request, f"تم إقفال {closed_count} فترة بنجاح")
