"""
Admin Configuration for Price List Versioning System
إعدادات لوحة الإدارة لنظام إصدارات قوائم الأسعار
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone

from .models_versioning import (
    PriceListVersion, VersionedPrice, LockedPrice, PriceChangeLog
)


class VersionedPriceInline(admin.TabularInline):
    model = VersionedPrice
    extra = 0
    fields = ['family', 'size', 'base_price', 'discounted_price', 'final_price', 'cost', 'margin_percentage']
    readonly_fields = ['base_price', 'discounted_price', 'final_price', 'cost', 'margin_percentage']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PriceListVersion)
class PriceListVersionAdmin(admin.ModelAdmin):
    list_display = [
        'version_display', 'price_list', 'status_badge', 'effective_from', 
        'grace_period_display', 'prices_count', 'created_by', 'action_buttons'
    ]
    list_filter = ['status', 'price_list', 'created_at']
    search_fields = ['version_name', 'price_list__name', 'change_reason']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('معلومات الإصدار', {
            'fields': (('price_list', 'version_number'), 'version_name')
        }),
        ('التواريخ', {
            'fields': (('effective_from', 'effective_until'), 'grace_period_days')
        }),
        ('الحالة والاعتماد', {
            'fields': ('status', ('approved_by', 'approved_at'))
        }),
        ('التفاصيل', {
            'fields': ('change_reason', 'notes')
        }),
    )
    
    readonly_fields = ['version_number', 'approved_by', 'approved_at', 'effective_until']
    inlines = [VersionedPriceInline]
    
    def version_display(self, obj):
        return f"v{obj.version_number}"
    version_display.short_description = 'الإصدار'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'active': '#28a745',
            'expired': '#dc3545',
            'archived': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'الحالة'
    
    def grace_period_display(self, obj):
        if obj.grace_period_days:
            if obj.is_in_grace_period():
                return format_html(
                    '<span style="color: orange;">⏰ {} يوم (جاري)</span>',
                    obj.grace_period_days
                )
            return f"{obj.grace_period_days} يوم"
        return '-'
    grace_period_display.short_description = 'فترة السماح'
    
    def prices_count(self, obj):
        return obj.prices.count()
    prices_count.short_description = 'عدد الأسعار'
    
    def action_buttons(self, obj):
        buttons = []
        
        if obj.status == 'draft':
            buttons.append(
                f'<a class="button" style="background: #28a745; color: white; padding: 3px 10px; text-decoration: none; border-radius: 3px;" '
                f'href="{reverse("admin:smart_pricing_pricelistversion_activate", args=[obj.pk])}">تفعيل</a>'
            )
        
        if obj.status in ['active', 'expired']:
            buttons.append(
                f'<a class="button" style="background: #17a2b8; color: white; padding: 3px 10px; text-decoration: none; border-radius: 3px;" '
                f'href="{reverse("admin:smart_pricing_pricelistversion_view_changes", args=[obj.pk])}">التغييرات</a>'
            )
        
        return format_html(' '.join(buttons)) if buttons else '-'
    action_buttons.short_description = 'إجراءات'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/activate/',
                self.admin_site.admin_view(self.activate_version),
                name='smart_pricing_pricelistversion_activate'
            ),
            path(
                '<int:pk>/view-changes/',
                self.admin_site.admin_view(self.view_changes),
                name='smart_pricing_pricelistversion_view_changes'
            ),
        ]
        return custom_urls + urls
    
    def activate_version(self, request, pk):
        version = PriceListVersion.objects.get(pk=pk)
        
        if version.status != 'draft':
            messages.error(request, 'يمكن تفعيل المسودات فقط')
        else:
            from .services_versioning import PriceVersioningService
            PriceVersioningService.activate_version(version, request.user)
            messages.success(request, f'تم تفعيل الإصدار {version.version_name}')
        
        return HttpResponseRedirect(
            reverse('admin:smart_pricing_pricelistversion_changelist')
        )
    
    def view_changes(self, request, pk):
        return HttpResponseRedirect(
            reverse('admin:smart_pricing_pricechangelog_changelist') + 
            f'?version__id__exact={pk}'
        )
    
    actions = ['create_new_version', 'activate_selected']
    
    def create_new_version(self, request, queryset):
        if queryset.count() != 1:
            messages.error(request, 'يرجى اختيار قائمة أسعار واحدة فقط')
            return
        
        version = queryset.first()
        from .services_versioning import PriceVersioningService
        
        new_version = PriceVersioningService.create_new_version(
            version.price_list,
            user=request.user,
            change_reason='نسخة من الإصدار السابق'
        )
        
        messages.success(request, f'تم إنشاء الإصدار {new_version.version_name}')
    create_new_version.short_description = "إنشاء إصدار جديد من المحدد"
    
    def activate_selected(self, request, queryset):
        for version in queryset.filter(status='draft'):
            from .services_versioning import PriceVersioningService
            PriceVersioningService.activate_version(version, request.user)
        
        messages.success(request, f'تم تفعيل {queryset.filter(status="draft").count()} إصدار')
    activate_selected.short_description = "تفعيل الإصدارات المحددة"


@admin.register(LockedPrice)
class LockedPriceAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'product_display', 'locked_price_display', 
        'lock_type', 'validity_display', 'status_display', 'created_at'
    ]
    list_filter = ['lock_type', 'is_active', 'is_used', 'price_list', 'created_at']
    search_fields = ['customer__name', 'family__name', 'reference_number']
    date_hierarchy = 'created_at'
    autocomplete_fields = ['customer', 'family', 'size', 'price_list']
    
    fieldsets = (
        ('العميل والمنتج', {
            'fields': (('customer', 'family', 'size'),)
        }),
        ('السعر', {
            'fields': (('locked_price', 'locked_price_with_tax'), 'locked_quantity')
        }),
        ('المصدر', {
            'fields': (('lock_type', 'price_list', 'price_version'),)
        }),
        ('المرجع', {
            'fields': (('reference_type', 'reference_id', 'reference_number'),)
        }),
        ('الصلاحية', {
            'fields': (('valid_from', 'valid_until'), ('is_active', 'is_used', 'used_at'))
        }),
        ('ملاحظات', {
            'fields': ('notes',)
        }),
    )
    
    readonly_fields = ['is_used', 'used_at']
    
    def product_display(self, obj):
        return f"{obj.family.name} - {obj.size}"
    product_display.short_description = 'المنتج'
    
    def locked_price_display(self, obj):
        return format_html(
            '<strong>{:,.2f}</strong> <small style="color:gray;">({:,.2f} شامل الضريبة)</small>',
            obj.locked_price, obj.locked_price_with_tax
        )
    locked_price_display.short_description = 'السعر المثبت'
    
    def validity_display(self, obj):
        if obj.valid_until:
            if obj.valid_until < timezone.now():
                return format_html('<span style="color: red;">منتهي</span>')
            days_left = (obj.valid_until - timezone.now()).days
            return f'{days_left} يوم متبقي'
        return format_html('<span style="color: green;">دائم</span>')
    validity_display.short_description = 'الصلاحية'
    
    def status_display(self, obj):
        if not obj.is_active:
            return format_html('<span style="color: gray;">⚫ غير نشط</span>')
        if obj.is_used:
            return format_html('<span style="color: blue;">✓ مستخدم</span>')
        if obj.is_valid:
            return format_html('<span style="color: green;">● نشط</span>')
        return format_html('<span style="color: red;">⚠ منتهي</span>')
    status_display.short_description = 'الحالة'
    
    actions = ['deactivate_locks', 'extend_validity']
    
    def deactivate_locks(self, request, queryset):
        count = queryset.update(is_active=False)
        messages.success(request, f'تم إلغاء {count} سعر مثبت')
    deactivate_locks.short_description = "إلغاء الأسعار المثبتة"
    
    def extend_validity(self, request, queryset):
        from datetime import timedelta
        count = 0
        for lock in queryset.filter(is_active=True):
            if lock.valid_until:
                lock.valid_until += timedelta(days=30)
            else:
                lock.valid_until = timezone.now() + timedelta(days=30)
            lock.save()
            count += 1
        messages.success(request, f'تم تمديد {count} سعر مثبت لمدة 30 يوم')
    extend_validity.short_description = "تمديد الصلاحية 30 يوم"


@admin.register(PriceChangeLog)
class PriceChangeLogAdmin(admin.ModelAdmin):
    list_display = [
        'changed_at', 'price_list', 'product_display', 
        'price_change_display', 'change_type_badge', 'changed_by'
    ]
    list_filter = ['change_type', 'price_list', 'changed_at', 'version']
    search_fields = ['family__name', 'reason']
    date_hierarchy = 'changed_at'
    ordering = ['-changed_at']
    
    readonly_fields = [
        'price_list', 'version', 'family', 'size',
        'old_price', 'new_price', 'price_change', 'change_percentage',
        'change_type', 'changed_by', 'changed_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def product_display(self, obj):
        return f"{obj.family.name} - {obj.size}"
    product_display.short_description = 'المنتج'
    
    def price_change_display(self, obj):
        arrow = '↑' if obj.price_change > 0 else '↓' if obj.price_change < 0 else '='
        color = 'red' if obj.price_change > 0 else 'green' if obj.price_change < 0 else 'gray'
        return format_html(
            '{:,.2f} → {:,.2f} <span style="color: {};">{} {:+.1f}%</span>',
            obj.old_price, obj.new_price, color, arrow, obj.change_percentage
        )
    price_change_display.short_description = 'التغيير'
    
    def change_type_badge(self, obj):
        colors = {
            'increase': '#dc3545',
            'decrease': '#28a745',
            'new': '#17a2b8',
        }
        color = colors.get(obj.change_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_change_type_display()
        )
    change_type_badge.short_description = 'النوع'
