"""
Admin panel لنظام تتبع الشحنات
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ShippingCompany, Shipment, ShipmentStatusHistory, ShipmentDocument, ShipmentNotification


@admin.register(ShippingCompany)
class ShippingCompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'is_active_badge', 'shipments_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'name_en', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'name_en', 'logo', 'is_active')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone', 'email', 'website')
        }),
        ('إعدادات التتبع', {
            'fields': ('tracking_url_template', 'api_key')
        }),
        ('ملاحظات', {
            'fields': ('notes',)
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✅ مفعل</span>')
        return format_html('<span style="color: red;">❌ معطل</span>')
    is_active_badge.short_description = 'الحالة'
    
    def shipments_count(self, obj):
        count = obj.shipments.count()
        url = reverse('admin:shipment_tracking_shipment_changelist') + f'?shipping_company__id__exact={obj.id}'
        return format_html('<a href="{}">{} شحنة</a>', url, count)
    shipments_count.short_description = 'عدد الشحنات'


class ShipmentStatusHistoryInline(admin.TabularInline):
    model = ShipmentStatusHistory
    extra = 0
    readonly_fields = ['created_by', 'created_at']
    fields = ['status', 'location', 'description', 'created_by', 'created_at']


class ShipmentDocumentInline(admin.TabularInline):
    model = ShipmentDocument
    extra = 0
    readonly_fields = ['uploaded_by', 'uploaded_at']
    fields = ['document_type', 'title', 'file', 'uploaded_by', 'uploaded_at']


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        'tracking_number',
        'status_badge',
        'shipping_company',
        'receiver_name',
        'receiver_city',
        'payment_method_badge',
        'cod_amount',
        'created_at'
    ]
    list_filter = [
        'status',
        'payment_method',
        'shipping_company',
        'receiver_city',
        'sender_city',
        'created_at'
    ]
    search_fields = [
        'tracking_number',
        'reference_number',
        'receiver_name',
        'receiver_phone',
        'sender_name',
        'sender_phone'
    ]
    readonly_fields = [
        'created_by',
        'created_at',
        'updated_at',
        'get_tracking_link',
        'get_status_timeline'
    ]
    date_hierarchy = 'created_at'
    
    inlines = [ShipmentStatusHistoryInline, ShipmentDocumentInline]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': (
                'tracking_number',
                'reference_number',
                'shipping_company',
                'status',
                'get_tracking_link'
            )
        }),
        ('معلومات المرسل', {
            'fields': (
                'sender_name',
                'sender_phone',
                'sender_address',
                'sender_city'
            )
        }),
        ('معلومات المستلم', {
            'fields': (
                'receiver_name',
                'receiver_phone',
                'receiver_alternate_phone',
                'receiver_email',
                'receiver_address',
                'receiver_city',
                'receiver_district',
                'receiver_postal_code'
            )
        }),
        ('تفاصيل الشحنة', {
            'fields': (
                'description',
                'weight',
                'pieces_count',
                'declared_value',
                'special_instructions'
            )
        }),
        ('معلومات الدفع', {
            'fields': (
                'payment_method',
                'cod_amount',
                'shipping_cost'
            )
        }),
        ('الموقع والتتبع', {
            'fields': (
                'current_location',
                'current_latitude',
                'current_longitude',
                'estimated_delivery_date',
                'pickup_date',
                'delivery_date'
            )
        }),
        ('ملاحظات', {
            'fields': (
                'notes',
                'failure_reason'
            ),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': (
                'customer_notified',
                'last_notification_sent',
                'created_by',
                'created_at',
                'updated_at',
                'get_status_timeline'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'picked_up': '#0dcaf0',
            'in_transit': '#0d6efd',
            'out_for_delivery': '#fd7e14',
            'delivered': '#198754',
            'failed': '#dc3545',
            'returned': '#6f42c1',
            'cancelled': '#adb5bd',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display_ar()
        )
    status_badge.short_description = 'الحالة'
    
    def payment_method_badge(self, obj):
        if obj.payment_method == 'cod':
            return format_html('<span style="color: #fd7e14;">💵 COD</span>')
        return format_html('<span style="color: #198754;">💳 مدفوع</span>')
    payment_method_badge.short_description = 'الدفع'
    
    def get_tracking_link(self, obj):
        url = obj.get_tracking_url()
        if url:
            return format_html('<a href="{}" target="_blank">🔗 تتبع الشحنة</a>', url)
        return '-'
    get_tracking_link.short_description = 'رابط التتبع'
    
    def get_status_timeline(self, obj):
        history = obj.status_history.all()[:5]
        if not history:
            return 'لا يوجد سجل'
        
        html = '<div style="margin-top: 10px;">'
        for h in history:
            html += f'''
            <div style="padding: 8px; margin: 5px 0; background: #f8f9fa; border-left: 3px solid #0d6efd;">
                <strong>{h.get_status_display()}</strong> - {h.created_at.strftime("%Y-%m-%d %H:%M")}
                {f"<br><small>{h.location}</small>" if h.location else ""}
                {f"<br><small>{h.description}</small>" if h.description else ""}
            </div>
            '''
        html += '</div>'
        return mark_safe(html)
    get_status_timeline.short_description = 'Timeline الحالات'
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_as_picked_up', 'mark_as_in_transit', 'mark_as_delivered']
    
    def mark_as_picked_up(self, request, queryset):
        for shipment in queryset:
            shipment.status = 'picked_up'
            shipment.save()
            ShipmentStatusHistory.objects.create(
                shipment=shipment,
                status='picked_up',
                description='تم الاستلام من قبل شركة الشحن',
                created_by=request.user
            )
        self.message_user(request, f'تم تحديث {queryset.count()} شحنة')
    mark_as_picked_up.short_description = '📦 تحديث: تم الاستلام'
    
    def mark_as_in_transit(self, request, queryset):
        for shipment in queryset:
            shipment.status = 'in_transit'
            shipment.save()
            ShipmentStatusHistory.objects.create(
                shipment=shipment,
                status='in_transit',
                description='الشحنة في الطريق',
                created_by=request.user
            )
        self.message_user(request, f'تم تحديث {queryset.count()} شحنة')
    mark_as_in_transit.short_description = '🚚 تحديث: قيد النقل'
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        for shipment in queryset:
            shipment.status = 'delivered'
            shipment.delivery_date = timezone.now()
            shipment.save()
            ShipmentStatusHistory.objects.create(
                shipment=shipment,
                status='delivered',
                description='تم التسليم بنجاح',
                created_by=request.user
            )
        self.message_user(request, f'تم تسليم {queryset.count()} شحنة')
    mark_as_delivered.short_description = '✅ تحديث: تم التسليم'


@admin.register(ShipmentStatusHistory)
class ShipmentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['shipment', 'status', 'location', 'created_at', 'created_by']
    list_filter = ['status', 'created_at']
    search_fields = ['shipment__tracking_number', 'location', 'description']
    readonly_fields = ['created_by', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(ShipmentDocument)
class ShipmentDocumentAdmin(admin.ModelAdmin):
    list_display = ['shipment', 'document_type', 'title', 'uploaded_at', 'uploaded_by']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['shipment__tracking_number', 'title']
    readonly_fields = ['uploaded_by', 'uploaded_at']
    date_hierarchy = 'uploaded_at'


@admin.register(ShipmentNotification)
class ShipmentNotificationAdmin(admin.ModelAdmin):
    list_display = ['shipment', 'notification_type', 'recipient', 'status', 'sent_at', 'created_at']
    list_filter = ['notification_type', 'status', 'created_at']
    search_fields = ['shipment__tracking_number', 'recipient', 'message']
    readonly_fields = ['created_at', 'sent_at']
    date_hierarchy = 'created_at'
