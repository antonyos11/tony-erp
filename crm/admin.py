from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count

from .models import (
    CustomerType, CustomerSource, Customer, ContactPerson,
    OpportunityStage, Opportunity, ActivityType, Activity,
    Quotation, QuotationItem, TicketCategory, SupportTicket,
    TicketComment, Campaign, CampaignResponse, CommissionScheme, CommissionAccrual
)


# Customer Management
@admin.register(CustomerType)
class CustomerTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'customer_count')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def customer_count(self, obj):
        count = obj.customer_set.count()
        return format_html(
            '<a href="{}?customer_type__id__exact={}">{} عميل</a>',
            reverse('admin:crm_customer_changelist'),
            obj.id,
            count
        )
    customer_count.short_description = 'عدد العملاء'


@admin.register(CustomerSource)
class CustomerSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'customer_count')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def customer_count(self, obj):
        count = obj.customer_set.count()
        return format_html(
            '<a href="{}?source__id__exact={}">{} عميل</a>',
            reverse('admin:crm_customer_changelist'),
            obj.id,
            count
        )
    customer_count.short_description = 'عدد العملاء'


class ContactPersonInline(admin.TabularInline):
    model = ContactPerson
    extra = 1
    fields = ('name', 'position', 'phone', 'email', 'is_primary')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'customer_code', 'full_name', 'company_name', 'customer_type',
        'phone', 'email', 'status', 'assigned_to', 'created_at'
    )
    list_filter = (
        'status', 'customer_type', 'source', 'assigned_to',
        'created_at', 'updated_at'
    )
    search_fields = (
        'customer_code', 'first_name', 'last_name', 'company_name',
        'phone', 'mobile', 'email'
    )
    readonly_fields = ('customer_code', 'created_at', 'updated_at', 'last_contact_date')
    inlines = [ContactPersonInline]
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('customer_code', 'first_name', 'last_name', 'company_name')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone', 'mobile', 'email', 'website')
        }),
        ('العنوان', {
            'fields': (
                'address_line1', 'address_line2', 'city', 
                'state', 'postal_code', 'country'
            ),
            'classes': ('collapse',)
        }),
        ('المعلومات الشخصية', {
            'fields': ('date_of_birth', 'gender', 'national_id'),
            'classes': ('collapse',)
        }),
        ('المعلومات التجارية', {
            'fields': (
                'customer_type', 'source', 'tax_number', 
                'credit_limit', 'payment_terms'
            )
        }),
        ('الحالة والتتبع', {
            'fields': ('status', 'assigned_to', 'notes')
        }),
        ('التوقيتات', {
            'fields': ('created_at', 'updated_at', 'last_contact_date'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'تم تفعيل {updated} عميل')
    mark_as_active.short_description = 'تفعيل العملاء المحددين'
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f'تم إلغاء تفعيل {updated} عميل')
    mark_as_inactive.short_description = 'إلغاء تفعيل العملاء المحددين'


# Opportunity Management
@admin.register(OpportunityStage)
class OpportunityStageAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'probability', 'is_won', 'is_lost', 'opportunity_count')
    list_editable = ('order', 'probability')
    list_filter = ('is_won', 'is_lost')
    ordering = ('order',)
    
    def opportunity_count(self, obj):
        count = obj.opportunity_set.count()
        return format_html(
            '<a href="{}?stage__id__exact={}">{} فرصة</a>',
            reverse('admin:crm_opportunity_changelist'),
            obj.id,
            count
        )
    opportunity_count.short_description = 'عدد الفرص'


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
    'name', 'customer', 'estimated_value', 'stage', 'probability',
    'expected_close_date', 'priority', 'assigned_to', 'closed_by', 'created_at'
    )
    list_filter = (
        'stage', 'priority', 'assigned_to', 'created_at',
        'expected_close_date'
    )
    search_fields = ('name', 'customer__first_name', 'customer__last_name', 'customer__company_name')
    readonly_fields = ('created_at', 'updated_at', 'closed_at')
    date_hierarchy = 'expected_close_date'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'customer', 'contact_person')
        }),
        ('المعلومات المالية', {
            'fields': ('estimated_value', 'probability', 'expected_close_date')
        }),
        ('الحالة والتتبع', {
            'fields': ('stage', 'priority', 'assigned_to', 'closed_by')
        }),
        ('التفاصيل', {
            'fields': ('description', 'notes'),
            'classes': ('collapse',)
        }),
        ('التوقيتات', {
            'fields': ('created_at', 'updated_at', 'closed_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'stage', 'assigned_to', 'closed_by'
        )


# Commission models
@admin.register(CommissionScheme)
class CommissionSchemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee', 'percentage', 'is_active', 'is_default', 'start_date', 'end_date')
    list_filter = ('is_active', 'is_default', 'start_date', 'end_date')
    search_fields = ('name', 'employee__arabic_name')
    ordering = ('-is_default', 'name')


@admin.register(CommissionAccrual)
class CommissionAccrualAdmin(admin.ModelAdmin):
    list_display = ('employee', 'opportunity', 'quotation', 'percentage', 'base_amount', 'amount', 'status', 'accrued_at')
    list_filter = ('status', 'employee', 'accrued_at')
    search_fields = ('employee__arabic_name', 'opportunity__name', 'quotation__quotation_number')
    date_hierarchy = 'accrued_at'
    actions = ['mark_selected_as_paid']

    def mark_selected_as_paid(self, request, queryset):
        paid_count = 0
        errors = 0
        from django.contrib import messages
        for accrual in queryset:
            if accrual.status == 'paid':
                continue
            try:
                accrual.mark_paid(paid_by=request.user)
                paid_count += 1
            except Exception as e:
                errors += 1
        if paid_count:
            self.message_user(request, f'تم صرف {paid_count} عمولة بنجاح.', level=messages.SUCCESS)
        if errors:
            self.message_user(request, f'تعذر صرف {errors} عمولة. تحقق من إعدادات الحسابات.', level=messages.ERROR)
    mark_selected_as_paid.short_description = 'صرف العمولات المحددة'


# Activity Management
@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'color_display', 'activity_count')
    search_fields = ('name',)
    ordering = ('name',)
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 50%;"></div>',
            obj.color
        )
    color_display.short_description = 'اللون'
    
    def activity_count(self, obj):
        count = obj.activity_set.count()
        return format_html(
            '<a href="{}?activity_type__id__exact={}">{} نشاط</a>',
            reverse('admin:crm_activity_changelist'),
            obj.id,
            count
        )
    activity_count.short_description = 'عدد الأنشطة'


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'customer', 'activity_type', 'scheduled_date',
        'duration_minutes', 'status', 'priority', 'assigned_to'
    )
    list_filter = (
        'activity_type', 'status', 'priority', 'assigned_to',
        'scheduled_date'
    )
    search_fields = ('title', 'customer__first_name', 'customer__last_name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'scheduled_date'
    ordering = ('-scheduled_date',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('title', 'activity_type', 'description')
        }),
        ('العلاقات', {
            'fields': ('customer', 'opportunity', 'contact_person')
        }),
        ('الجدولة', {
            'fields': ('scheduled_date', 'duration_minutes')
        }),
        ('الحالة والتعيين', {
            'fields': ('status', 'priority', 'assigned_to')
        }),
        ('النتائج', {
            'fields': ('outcome', 'follow_up_required', 'follow_up_date'),
            'classes': ('collapse',)
        }),
        ('التوقيتات', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )


# Quotation Management
class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1
    fields = ('product', 'description', 'quantity', 'unit_price', 'total')
    readonly_fields = ('total',)


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        'quotation_number', 'customer', 'quotation_date', 'valid_until',
        'total_amount', 'status', 'prepared_by'
    )
    list_filter = ('status', 'prepared_by', 'quotation_date', 'valid_until')
    search_fields = (
        'quotation_number', 'customer__first_name', 
        'customer__last_name', 'customer__company_name'
    )
    readonly_fields = (
        'quotation_number', 'subtotal', 'discount_amount', 
        'tax_amount', 'total_amount', 'created_at', 'updated_at',
        'sent_at', 'responded_at'
    )
    inlines = [QuotationItemInline]
    date_hierarchy = 'quotation_date'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': (
                'quotation_number', 'customer', 'opportunity', 
                'contact_person'
            )
        }),
        ('التواريخ', {
            'fields': ('quotation_date', 'valid_until')
        }),
        ('المعلومات المالية', {
            'fields': (
                'subtotal', 'discount_percentage', 'discount_amount',
                'tax_percentage', 'tax_amount', 'total_amount'
            )
        }),
        ('الحالة والملاحظات', {
            'fields': ('status', 'notes', 'terms_and_conditions')
        }),
        ('التعيين', {
            'fields': ('prepared_by',)
        }),
        ('التوقيتات', {
            'fields': ('created_at', 'updated_at', 'sent_at', 'responded_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(QuotationItem)
class QuotationItemAdmin(admin.ModelAdmin):
    list_display = ('quotation', 'product', 'quantity', 'unit_price', 'total')
    list_filter = ('quotation__status', 'product')
    search_fields = ('quotation__quotation_number', 'product__name', 'description')
    readonly_fields = ('total',)


# Support System
@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color_display', 'ticket_count')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 50%;"></div>',
            obj.color
        )
    color_display.short_description = 'اللون'
    
    def ticket_count(self, obj):
        count = obj.supportticket_set.count()
        return format_html(
            '<a href="{}?category__id__exact={}">{} تذكرة</a>',
            reverse('admin:crm_supportticket_changelist'),
            obj.id,
            count
        )
    ticket_count.short_description = 'عدد التذاكر'


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 1
    fields = ('comment', 'is_internal', 'created_by', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_number', 'title', 'customer', 'category', 
        'status', 'priority', 'assigned_to', 'created_at'
    )
    list_filter = (
        'status', 'priority', 'category', 'assigned_to',
        'created_at', 'resolved_at'
    )
    search_fields = ('ticket_number', 'title', 'description', 'customer__first_name', 'customer__last_name')
    readonly_fields = ('ticket_number', 'created_at', 'updated_at', 'resolved_at', 'closed_at')
    inlines = [TicketCommentInline]
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('ticket_number', 'title', 'description')
        }),
        ('العلاقات', {
            'fields': ('customer', 'contact_person', 'category')
        }),
        ('الحالة والأولوية', {
            'fields': ('status', 'priority')
        }),
        ('التعيين', {
            'fields': ('assigned_to', 'created_by')
        }),
        ('التوقيتات', {
            'fields': ('created_at', 'updated_at', 'resolved_at', 'closed_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_resolved', 'mark_as_closed']
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f'تم تحديد {updated} تذكرة كمحلولة')
    mark_as_resolved.short_description = 'تحديد كمحلولة'
    
    def mark_as_closed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='closed', closed_at=timezone.now())
        self.message_user(request, f'تم إغلاق {updated} تذكرة')
    mark_as_closed.short_description = 'إغلاق التذاكر'


# Campaign Management
@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'campaign_type', 'status', 'budget',
        'start_date', 'end_date', 'created_by'
    )
    list_filter = ('campaign_type', 'status', 'start_date', 'created_by')
    search_fields = ('name', 'description', 'message_content')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('target_customers',)
    date_hierarchy = 'start_date'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'campaign_type', 'description')
        }),
        ('الاستهداف', {
            'fields': ('target_customers', 'customer_type')
        }),
        ('تفاصيل الحملة', {
            'fields': ('message_content', 'budget')
        }),
        ('الحالة والتواريخ', {
            'fields': ('status', 'start_date', 'end_date')
        }),
        ('التعيين', {
            'fields': ('created_by',)
        }),
        ('التوقيتات', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(CampaignResponse)
class CampaignResponseAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'customer', 'response_type', 'response_date')
    list_filter = ('response_type', 'campaign', 'response_date')
    search_fields = ('campaign__name', 'customer__first_name', 'customer__last_name', 'notes')
    readonly_fields = ('response_date',)
    ordering = ('-response_date',)


# Contact Person (if not inline only)
@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer', 'position', 'phone', 'email', 'is_primary')
    list_filter = ('is_primary', 'customer__customer_type')
    search_fields = ('name', 'position', 'phone', 'email', 'customer__first_name', 'customer__last_name')
    ordering = ('customer', 'name')


# Ticket Comments (if not inline only)
@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'created_by', 'is_internal', 'created_at')
    list_filter = ('is_internal', 'created_by', 'created_at')
    search_fields = ('ticket__ticket_number', 'ticket__title', 'comment')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


# Admin site customization
admin.site.site_header = "إدارة نظام CRM الشامل"
admin.site.site_title = "CRM Admin"
admin.site.index_title = "مرحباً بك في لوحة إدارة نظام CRM"

# Import advanced admin registrations
try:
    from . import admin_advanced  # noqa: F401
except ImportError:
    pass