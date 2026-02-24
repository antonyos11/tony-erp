from django.contrib import admin
from .models import SubscriptionPlan, CustomerSubscription, SubscriptionPayment


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'monthly_price', 'annual_price', 'max_users', 'is_active', 'is_featured']
    list_filter = ['plan_type', 'is_active', 'is_featured']
    search_fields = ['name', 'code']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'code', 'plan_type', 'description')
        }),
        ('التسعير', {
            'fields': ('monthly_price', 'quarterly_price', 'semi_annual_price', 'annual_price')
        }),
        ('الحدود', {
            'fields': ('max_users', 'max_products', 'max_invoices_per_month', 'max_storage_gb')
        }),
        ('المميزات', {
            'fields': ('has_api_access', 'has_mobile_app', 'has_advanced_reports', 
                      'has_ai_features', 'has_whatsapp_integration', 'has_ecommerce',
                      'has_multi_branch', 'has_priority_support')
        }),
        ('العرض', {
            'fields': ('display_order', 'is_active', 'is_featured', 'features')
        }),
    )


class SubscriptionPaymentInline(admin.TabularInline):
    model = SubscriptionPayment
    extra = 0
    readonly_fields = ['payment_number', 'payment_date', 'transaction_id']
    fields = ['payment_number', 'amount', 'payment_method', 'status', 'payment_date']


@admin.register(CustomerSubscription)
class CustomerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['subscription_number', 'customer', 'plan', 'status', 'start_date', 'end_date', 'auto_renew']
    list_filter = ['status', 'plan', 'billing_period', 'auto_renew']
    search_fields = ['subscription_number', 'customer__username', 'customer__email']
    readonly_fields = ['subscription_number', 'created_at', 'updated_at']
    inlines = [SubscriptionPaymentInline]
    
    fieldsets = (
        ('معلومات الاشتراك', {
            'fields': ('subscription_number', 'customer', 'plan', 'billing_period', 'status')
        }),
        ('التواريخ', {
            'fields': ('start_date', 'end_date', 'trial_ends_at', 'auto_renew')
        }),
        ('التسعير', {
            'fields': ('price', 'discount', 'final_price')
        }),
        ('الاستخدام', {
            'fields': ('current_users', 'current_products', 'current_invoices_this_month', 'current_storage_gb')
        }),
        ('ملاحظات', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_subscriptions', 'suspend_subscriptions', 'renew_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        count = queryset.update(status='active')
        self.message_user(request, f'تم تفعيل {count} اشتراك')
    activate_subscriptions.short_description = 'تفعيل الاشتراكات'
    
    def suspend_subscriptions(self, request, queryset):
        count = queryset.update(status='suspended')
        self.message_user(request, f'تم إيقاف {count} اشتراك')
    suspend_subscriptions.short_description = 'إيقاف الاشتراكات'
    
    def renew_subscriptions(self, request, queryset):
        count = 0
        for subscription in queryset:
            subscription.renew()
            count += 1
        self.message_user(request, f'تم تجديد {count} اشتراك')
    renew_subscriptions.short_description = 'تجديد الاشتراكات'


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'subscription', 'amount', 'payment_method', 'status', 'payment_date']
    list_filter = ['status', 'payment_method']
    search_fields = ['payment_number', 'transaction_id', 'subscription__subscription_number']
    readonly_fields = ['payment_number', 'transaction_id', 'created_at']
    
    fieldsets = (
        ('معلومات الدفعة', {
            'fields': ('payment_number', 'subscription', 'amount', 'payment_method', 'status')
        }),
        ('تفاصيل الدفع', {
            'fields': ('transaction_id', 'payment_date', 'invoice_number')
        }),
        ('ملاحظات', {
            'fields': ('notes', 'created_at')
        }),
    )
