"""
White Label Admin
لوحة تحكم نظام العلامة البيضاء

إدارة المستأجرين والعلامات التجارية
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Tenant, TenantBranding, TenantSettings, TenantDomain


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """إدارة المستأجرين"""
    
    list_display = [
        'name', 'company_name', 'slug', 'domain',
        'subscription_plan', 'is_active_badge', 'subscription_status',
        'created_at'
    ]
    
    list_filter = [
        'is_active', 'subscription_plan', 'country', 'created_at'
    ]
    
    search_fields = [
        'name', 'company_name', 'company_name_ar', 'slug',
        'email', 'tax_id', 'commercial_registration'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'usage_stats_display']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': (
                'name', 'slug', 'domain', 'is_active'
            )
        }),
        ('بيانات الشركة', {
            'fields': (
                'company_name', 'company_name_ar',
                'tax_id', 'commercial_registration'
            )
        }),
        ('بيانات الاتصال', {
            'fields': (
                'email', 'phone', 'address', 'city', 'country'
            )
        }),
        ('الاشتراك', {
            'fields': (
                'subscription_plan', 'subscription_start',
                'subscription_end', 'trial_end'
            )
        }),
        ('الحدود', {
            'fields': (
                'max_users', 'max_branches', 'max_products', 'max_storage_mb'
            )
        }),
        ('الميزات', {
            'fields': (
                'enabled_modules', 'custom_features'
            )
        }),
        ('الإعدادات', {
            'fields': (
                'timezone', 'language', 'currency'
            )
        }),
        ('إحصائيات', {
            'fields': ('usage_stats_display',),
            'classes': ('collapse',)
        }),
        ('تواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_active_badge(self, obj):
        """شارة الحالة"""
        if obj.is_active:
            return format_html(
                '<span style="color: green;">✓ نشط</span>'
            )
        return format_html(
            '<span style="color: red;">✗ غير نشط</span>'
        )
    is_active_badge.short_description = 'الحالة'
    
    def subscription_status(self, obj):
        """حالة الاشتراك"""
        if obj.is_subscription_active():
            return format_html(
                '<span style="color: green;">صالح</span>'
            )
        elif obj.is_trial_expired():
            return format_html(
                '<span style="color: red;">انتهت التجربة</span>'
            )
        return format_html(
            '<span style="color: orange;">منتهي</span>'
        )
    subscription_status.short_description = 'حالة الاشتراك'
    
    def usage_stats_display(self, obj):
        """عرض إحصائيات الاستخدام"""
        stats = obj.get_usage_stats()
        
        return format_html(
            '<table>'
            '<tr><td><b>المستخدمون:</b></td><td>{} / {}</td></tr>'
            '<tr><td><b>الفروع:</b></td><td>{} / {}</td></tr>'
            '<tr><td><b>المنتجات:</b></td><td>{} / {}</td></tr>'
            '</table>',
            stats['users'], obj.max_users,
            stats['branches'], obj.max_branches,
            stats['products'], obj.max_products
        )
    usage_stats_display.short_description = 'الاستخدام'


@admin.register(TenantBranding)
class TenantBrandingAdmin(admin.ModelAdmin):
    """إدارة العلامات التجارية"""
    
    list_display = [
        'tenant', 'logo_preview', 'app_title', 'primary_color',
        'updated_at'
    ]
    
    search_fields = ['tenant__name', 'app_title', 'app_title_ar']
    
    readonly_fields = ['created_at', 'updated_at', 'logo_preview', 'colors_preview']
    
    fieldsets = (
        ('المستأجر', {
            'fields': ('tenant',)
        }),
        ('الشعارات', {
            'fields': (
                'logo', 'logo_dark', 'favicon', 'logo_preview'
            )
        }),
        ('الألوان', {
            'fields': (
                'primary_color', 'secondary_color', 'accent_color',
                'background_color', 'text_color', 'colors_preview'
            )
        }),
        ('الخطوط', {
            'fields': ('font_family', 'font_url')
        }),
        ('النصوص', {
            'fields': (
                'app_title', 'app_title_ar', 'tagline', 'tagline_ar'
            )
        }),
        ('صفحة الدخول', {
            'fields': (
                'login_background', 'login_title', 'login_message'
            ),
            'classes': ('collapse',)
        }),
        ('التذييل', {
            'fields': ('footer_text', 'copyright_text'),
            'classes': ('collapse',)
        }),
        ('التواصل الاجتماعي', {
            'fields': (
                'website_url', 'facebook_url', 'twitter_url',
                'linkedin_url', 'instagram_url'
            ),
            'classes': ('collapse',)
        }),
        ('تخصيص متقدم', {
            'fields': ('custom_css', 'custom_js'),
            'classes': ('collapse',)
        }),
        ('تواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def logo_preview(self, obj):
        """معاينة الشعار"""
        if obj.logo:
            return format_html(
                '<img src="{}" width="100" height="auto" />',
                obj.logo.url
            )
        return '-'
    logo_preview.short_description = 'معاينة'
    
    def colors_preview(self, obj):
        """معاينة الألوان"""
        return format_html(
            '<div style="display: flex; gap: 10px;">'
            '<div style="width: 50px; height: 50px; background: {}; border: 1px solid #ccc;" title="أساسي"></div>'
            '<div style="width: 50px; height: 50px; background: {}; border: 1px solid #ccc;" title="ثانوي"></div>'
            '<div style="width: 50px; height: 50px; background: {}; border: 1px solid #ccc;" title="تمييز"></div>'
            '</div>',
            obj.primary_color,
            obj.secondary_color,
            obj.accent_color
        )
    colors_preview.short_description = 'الألوان'


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات المستأجرين"""
    
    list_display = [
        'tenant', 'invoice_prefix', 'tax_enabled', 'tax_rate',
        'api_enabled', 'updated_at'
    ]
    
    search_fields = ['tenant__name']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('المستأجر', {
            'fields': ('tenant',)
        }),
        ('الفواتير', {
            'fields': (
                'invoice_prefix', 'invoice_number_start',
                'invoice_terms', 'invoice_footer'
            )
        }),
        ('الضرائب', {
            'fields': ('tax_enabled', 'tax_rate', 'tax_number')
        }),
        ('المخزون', {
            'fields': (
                'allow_negative_stock', 'auto_reorder', 'low_stock_threshold'
            )
        }),
        ('التسعير', {
            'fields': ('default_markup', 'dynamic_pricing', 'price_rounding')
        }),
        ('الإنتاج', {
            'fields': ('production_auto_start', 'production_quality_check')
        }),
        ('الموافقات', {
            'fields': (
                'require_po_approval', 'po_approval_limit',
                'require_invoice_approval'
            )
        }),
        ('الإشعارات', {
            'fields': (
                'email_notifications', 'sms_notifications', 'push_notifications'
            )
        }),
        ('النسخ الاحتياطي', {
            'fields': (
                'auto_backup', 'backup_frequency', 'backup_retention_days'
            ),
            'classes': ('collapse',)
        }),
        ('الأمان', {
            'fields': (
                'password_expiry_days', 'max_login_attempts',
                'session_timeout_minutes', 'require_2fa'
            ),
            'classes': ('collapse',)
        }),
        ('API', {
            'fields': ('api_enabled', 'api_rate_limit', 'webhook_url'),
            'classes': ('collapse',)
        }),
        ('إعدادات مخصصة', {
            'fields': ('custom_settings',),
            'classes': ('collapse',)
        }),
        ('تواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(TenantDomain)
class TenantDomainAdmin(admin.ModelAdmin):
    """إدارة نطاقات المستأجرين"""
    
    list_display = [
        'domain', 'tenant', 'is_primary', 'is_active',
        'ssl_enabled', 'ssl_expiry', 'created_at'
    ]
    
    list_filter = ['is_primary', 'is_active', 'ssl_enabled']
    
    search_fields = ['domain', 'tenant__name']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('tenant', 'domain', 'is_primary', 'is_active')
        }),
        ('SSL', {
            'fields': ('ssl_enabled', 'ssl_certificate', 'ssl_expiry'),
            'classes': ('collapse',)
        }),
        ('تواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
