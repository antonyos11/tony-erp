"""
Admin interface for Enhanced Invoice Features
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .invoice_templates import (
    InvoiceTemplate,
    InvoiceAutosave,
    InvoiceAttachment,
    InvoiceHistory,
    CustomerCreditLimit
)


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    """إدارة نماذج الفواتير"""
    list_display = ['name', 'customer', 'usage_count_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'payment_method']
    search_fields = ['name', 'description', 'customer__name']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'description', 'is_active')
        }),
        (_('بيانات الفاتورة'), {
            'fields': ('customer', 'payment_method', 'discount', 'is_tax_inclusive')
        }),
        (_('الأصناف'), {
            'fields': ('items_data', 'notes')
        }),
        (_('الاستخدام والتتبع'), {
            'fields': ('usage_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def usage_count_display(self, obj):
        """عرض عداد الاستخدام مع أيقونة"""
        if obj.usage_count > 10:
            color = 'green'
        elif obj.usage_count > 5:
            color = 'orange'
        else:
            color = 'gray'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">🔥 {} مرة</span>',
            color,
            obj.usage_count
        )
    usage_count_display.short_description = _('عدد الاستخدام')


@admin.register(InvoiceAutosave)
class InvoiceAutosaveAdmin(admin.ModelAdmin):
    """إدارة الحفظ التلقائي"""
    list_display = ['user', 'session_key', 'updated_at', 'expires_at', 'is_expired_display']
    list_filter = ['updated_at', 'expires_at']
    search_fields = ['user__username', 'session_key']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['cleanup_expired']
    
    def is_expired_display(self, obj):
        """عرض حالة الانتهاء"""
        if obj.is_expired():
            return format_html('<span style="color: red;">⏰ منتهي</span>')
        return format_html('<span style="color: green;">✓ نشط</span>')
    is_expired_display.short_description = _('الحالة')
    
    def cleanup_expired(self, request, queryset):
        """حذف السجلات المنتهية"""
        InvoiceAutosave.cleanup_expired()
        self.message_user(request, _('تم حذف السجلات المنتهية'))
    cleanup_expired.short_description = _('حذف المنتهية')


@admin.register(InvoiceAttachment)
class InvoiceAttachmentAdmin(admin.ModelAdmin):
    """إدارة مرفقات الفواتير"""
    list_display = ['original_filename', 'invoice', 'file_type_display', 'file_size_display', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['original_filename', 'description', 'invoice__number']
    readonly_fields = ['uploaded_at', 'file_size', 'file_type']
    
    def file_type_display(self, obj):
        """عرض نوع الملف مع أيقونة"""
        icons = {
            'image': '🖼️',
            'pdf': '📄',
            'word': '📝',
            'excel': '📊',
        }
        
        icon = '📎'
        for key, value in icons.items():
            if key in obj.file_type.lower():
                icon = value
                break
        
        return format_html('{} {}', icon, obj.file_type)
    file_type_display.short_description = _('نوع الملف')
    
    def file_size_display(self, obj):
        """عرض حجم الملف بطريقة مقروءة"""
        size = obj.file_size
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        else:
            return f'{size / (1024 * 1024):.1f} MB'
    file_size_display.short_description = _('الحجم')


@admin.register(InvoiceHistory)
class InvoiceHistoryAdmin(admin.ModelAdmin):
    """إدارة سجل تغييرات الفواتير"""
    list_display = ['invoice', 'action_display', 'user', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['invoice__number', 'user__username', 'ip_address']
    readonly_fields = ['invoice', 'action', 'user', 'timestamp', 'changes', 'previous_data', 'ip_address', 'user_agent']
    
    fieldsets = (
        (_('معلومات التغيير'), {
            'fields': ('invoice', 'action', 'user', 'timestamp')
        }),
        (_('التفاصيل'), {
            'fields': ('changes', 'previous_data')
        }),
        (_('معلومات الاتصال'), {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def action_display(self, obj):
        """عرض نوع الإجراء مع لون"""
        colors = {
            'created': 'green',
            'updated': 'blue',
            'deleted': 'red',
            'restored': 'orange',
            'item_added': 'teal',
            'item_removed': 'purple',
            'payment_added': 'darkgreen',
        }
        
        color = colors.get(obj.action, 'black')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_display.short_description = _('الإجراء')
    
    def has_add_permission(self, request):
        """منع الإضافة اليدوية"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """منع الحذف"""
        return False


@admin.register(CustomerCreditLimit)
class CustomerCreditLimitAdmin(admin.ModelAdmin):
    """إدارة حدود الائتمان للعملاء"""
    list_display = ['customer', 'credit_limit_display', 'current_balance_display', 'available_credit_display', 'is_over_limit_display', 'is_blocked']
    list_filter = ['is_blocked', 'payment_days']
    search_fields = ['customer__name']
    readonly_fields = ['current_balance', 'last_transaction_date', 'last_payment_date', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات العميل'), {
            'fields': ('customer',)
        }),
        (_('حدود الائتمان'), {
            'fields': ('credit_limit', 'current_balance', 'payment_days')
        }),
        (_('الحظر'), {
            'fields': ('is_blocked', 'block_reason')
        }),
        (_('آخر المعاملات'), {
            'fields': ('last_transaction_date', 'last_payment_date'),
            'classes': ('collapse',)
        }),
        (_('التتبع'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['update_balances', 'block_customers', 'unblock_customers']
    
    def credit_limit_display(self, obj):
        """عرض حد الائتمان"""
        return format_html('<strong>{:,.2f} ج.م</strong>', obj.credit_limit)
    credit_limit_display.short_description = _('حد الائتمان')
    
    def current_balance_display(self, obj):
        """عرض الرصيد الحالي"""
        color = 'red' if obj.is_over_limit() else 'green'
        return format_html(
            '<span style="color: {};">{:,.2f} ج.م</span>',
            color,
            obj.current_balance
        )
    current_balance_display.short_description = _('الرصيد الحالي')
    
    def available_credit_display(self, obj):
        """عرض الائتمان المتاح"""
        available = obj.available_credit()
        color = 'green' if available > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:,.2f} ج.م</span>',
            color,
            available
        )
    available_credit_display.short_description = _('المتاح')
    
    def is_over_limit_display(self, obj):
        """عرض حالة التجاوز"""
        if obj.is_over_limit():
            return format_html('<span style="color: red; font-weight: bold;">⚠️ متجاوز</span>')
        return format_html('<span style="color: green;">✓ طبيعي</span>')
    is_over_limit_display.short_description = _('الحالة')
    
    def update_balances(self, request, queryset):
        """تحديث أرصدة العملاء"""
        for credit_limit in queryset:
            credit_limit.update_balance()
        self.message_user(request, _('تم تحديث الأرصدة'))
    update_balances.short_description = _('تحديث الأرصدة')
    
    def block_customers(self, request, queryset):
        """حظر العملاء"""
        queryset.update(is_blocked=True)
        self.message_user(request, _('تم حظر العملاء المحددين'))
    block_customers.short_description = _('حظر العملاء')
    
    def unblock_customers(self, request, queryset):
        """إلغاء حظر العملاء"""
        queryset.update(is_blocked=False, block_reason='')
        self.message_user(request, _('تم إلغاء الحظر'))
    unblock_customers.short_description = _('إلغاء الحظر')
