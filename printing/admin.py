from django.contrib import admin
from django.utils.html import format_html
from .models import PrinterConfiguration, UnifiedPrintJob, PrintStation, PrinterMapping, StationSession, PrintTemplate


@admin.register(PrinterConfiguration)
class PrinterConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'printer_type_badge', 'document_type', 'connection_display',
        'is_default', 'is_active', 'online_status', 'total_prints', 'last_print_at',
    ]
    list_filter = ['printer_type', 'document_type', 'connection_type', 'is_active', 'is_default']
    search_fields = ['name', 'cups_printer_name', 'shared_printer_name', 'ip_address']
    list_editable = ['is_active', 'is_default']
    ordering = ['printer_type', '-is_default', 'name']

    fieldsets = (
        ('معلومات الطابعة', {
            'fields': ('name', 'printer_type', 'document_type', 'is_active', 'is_default'),
        }),
        ('الاتصال', {
            'fields': ('connection_type', 'ip_address', 'port', 'cups_printer_name', 'shared_printer_name'),
        }),
        ('الإحصائيات', {
            'fields': ('total_prints', 'last_print_at', 'last_error'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['total_prints', 'last_print_at', 'last_error']

    @admin.display(description='النوع')
    def printer_type_badge(self, obj):
        colors = {
            'zebra': '#e67e22',
            'thermal': '#27ae60',
            'a4': '#3498db',
            'card': '#9b59b6',
        }
        color = colors.get(obj.printer_type, '#95a5a6')
        label = obj.get_printer_type_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-size:0.8em;">{}</span>',
            color, label
        )

    @admin.display(description='الاتصال')
    def connection_display(self, obj):
        if obj.connection_type == 'network' and obj.ip_address:
            return format_html('🌐 {}:{}', obj.ip_address, obj.port or 9100)
        elif obj.connection_type == 'usb':
            return '🔌 USB'
        elif obj.cups_printer_name:
            return format_html('🖨️ CUPS: {}', obj.cups_printer_name)
        elif obj.shared_printer_name:
            return format_html('🖨️ Share: {}', obj.shared_printer_name)
        return obj.get_connection_type_display()

    @admin.display(description='الحالة')
    def online_status(self, obj):
        from .manager import PrintManager
        is_online = PrintManager._check_printer_online(obj)
        if is_online:
            return format_html('<span style="color:#28a745;">● متصلة</span>')
        return format_html('<span style="color:#dc3545;">● غير متصلة</span>')

    actions = ['test_print_action', 'mark_active', 'mark_inactive']

    @admin.action(description="🖨️ إرسال طباعة تجريبية")
    def test_print_action(self, request, queryset):
        from .manager import PrintManager
        for printer in queryset:
            success, msg = PrintManager.send_test_print(
                printer_id=str(printer.pk),
                printer_type=printer.printer_type,
                user=request.user,
            )
            if success:
                self.message_user(request, f"✅ تم الإرسال إلى {printer.name}")
            else:
                self.message_user(request, f"❌ {printer.name}: {msg}", level='error')

    @admin.action(description="✅ تفعيل المحددة")
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="❌ تعطيل المحددة")
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(UnifiedPrintJob)
class UnifiedPrintJobAdmin(admin.ModelAdmin):
    list_display = [
        'short_id', 'document_type', 'title', 'status_badge',
        'printer', 'copies', 'requested_by', 'created_at',
    ]
    list_filter = ['status', 'document_type', 'source_app', 'printer__printer_type']
    search_fields = ['title', 'source_id']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'zpl_command', 'pdf_base64', 'html_content', 'escpos_data',
        'created_at', 'sent_at', 'completed_at',
    ]

    @admin.display(description='معرف المهمة')
    def short_id(self, obj):
        return str(obj.pk)[:8]

    @admin.display(description='الحالة')
    def status_badge(self, obj):
        colors = {
            'queued': '#ffc107',
            'sent': '#17a2b8',
            'printing': '#007bff',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.8em;">{}</span>',
            color, obj.get_status_display()
        )

    def has_add_permission(self, request):
        return False

    actions = ['reprint_selected', 'cancel_selected']

    @admin.action(description="🔄 إعادة طباعة المهام المحددة")
    def reprint_selected(self, request, queryset):
        from printing.dispatch import PrintDispatcher
        count = 0
        for job in queryset:
            success, _, _ = PrintDispatcher.reprint(str(job.pk), user=request.user)
            if success:
                count += 1
        self.message_user(request, f"تمت إعادة طباعة {count} مهمة.")

    @admin.action(description="🚫 إلغاء المهام المحددة")
    def cancel_selected(self, request, queryset):
        updated = queryset.filter(status__in=['queued', 'sent']).update(status='cancelled')
        self.message_user(request, f"تم إلغاء {updated} مهمة.")


# ══════════════════════════════════════════════════════════════
# Multi-Device Printing Architecture — Station Management
# ══════════════════════════════════════════════════════════════

class PrinterMappingInline(admin.TabularInline):
    model = PrinterMapping
    extra = 1
    fields = [
        'document_type', 'printer_config', 'local_printer_name',
        'copies', 'is_enabled', 'priority',
    ]


@admin.register(PrintStation)
class PrintStationAdmin(admin.ModelAdmin):
    list_display = [
        'status_icon', 'display_name_or_machine', 'machine_name',
        'machine_ip', 'os_platform', 'agent_version',
        'printer_count', 'mapping_count', 'last_seen',
    ]
    list_filter = ['is_online', 'is_active', 'os_platform']
    search_fields = ['machine_name', 'display_name', 'machine_ip', 'location']
    readonly_fields = [
        'id', 'machine_name', 'machine_ip', 'agent_version',
        'os_platform', 'discovered_printers_display',
        'first_seen', 'last_seen', 'is_online',
    ]
    fieldsets = [
        ('🖥️ هوية المحطة', {
            'fields': [
                'id', 'machine_name', 'machine_ip', 'display_name',
                'location', 'is_active',
            ]
        }),
        ('🔌 معلومات الوكيل (مكتشفة تلقائياً)', {
            'fields': [
                'os_platform', 'agent_version', 'agent_port',
                'is_online', 'first_seen', 'last_seen',
            ]
        }),
        ('🖨️ الطابعات المكتشفة (من الوكيل)', {
            'fields': ['discovered_printers_display'],
        }),
        ('👤 المستخدمون المعيّنون', {
            'fields': ['assigned_users'],
        }),
    ]
    filter_horizontal = ['assigned_users']
    inlines = [PrinterMappingInline]
    actions = ['mark_active', 'mark_inactive', 'test_all_printers']

    @admin.display(description='الحالة')
    def status_icon(self, obj):
        if not obj.is_active:
            return format_html('<span title="معطّل">⚫</span>')
        if obj.is_online:
            return format_html('<span title="متصل">🟢</span>')
        return format_html('<span title="غير متصل">🔴</span>')

    @admin.display(description='المحطة', ordering='display_name')
    def display_name_or_machine(self, obj):
        return obj.display_name or obj.machine_name

    @admin.display(description='الطابعات')
    def printer_count(self, obj):
        count = len(obj.discovered_printers) if obj.discovered_printers else 0
        return count

    @admin.display(description='التعيينات')
    def mapping_count(self, obj):
        return obj.printer_mappings.filter(is_enabled=True).count()

    @admin.display(description='الطابعات المكتشفة')
    def discovered_printers_display(self, obj):
        if not obj.discovered_printers:
            return format_html('<em>لم تُكتشف طابعات بعد. شغّل الوكيل على هذا الجهاز.</em>')

        rows = []
        for p in obj.discovered_printers:
            name = p.get('name', '?')
            ptype = p.get('type', 'unknown')
            badge_color = {
                'zebra': '#e67e22', 'thermal': '#27ae60', 'a4': '#3498db',
            }.get(ptype, '#7f8c8d')
            rows.append(
                f'<tr>'
                f'<td style="padding:4px 12px"><code>{name}</code></td>'
                f'<td style="padding:4px 12px"><span style="background:{badge_color};color:#fff;'
                f'padding:2px 8px;border-radius:4px;font-size:11px">{ptype}</span></td>'
                f'</tr>'
            )

        table = (
            '<table style="border-collapse:collapse">'
            '<tr><th style="text-align:left;padding:4px 12px">الاسم</th>'
            '<th style="padding:4px 12px">النوع</th></tr>'
            + ''.join(rows)
            + '</table>'
        )
        return format_html(table)

    @admin.action(description="✅ تفعيل المحطات المحددة")
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="❌ تعطيل المحطات المحددة")
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="🖨️ إرسال طباعة تجريبية لجميع الطابعات")
    def test_all_printers(self, request, queryset):
        from .print_service import PrintService
        for station in queryset:
            results = PrintService.test_station_printers(station, user=request.user)
            for doc_type, (success, msg) in results.items():
                level = None if success else 'error'
                icon = '✅' if success else '❌'
                self.message_user(
                    request,
                    f"{icon} {station}: {doc_type} → {msg}",
                    level=level,
                )


@admin.register(PrinterMapping)
class PrinterMappingAdmin(admin.ModelAdmin):
    list_display = [
        'station', 'document_type', 'printer_display',
        'copies', 'is_enabled', 'priority',
    ]
    list_filter = ['document_type', 'is_enabled', 'station']
    list_editable = ['copies', 'is_enabled', 'priority']

    @admin.display(description='الطابعة')
    def printer_display(self, obj):
        if obj.printer_config:
            return f"🌐 {obj.printer_config.name}"
        if obj.local_printer_name:
            return f"🖥️ {obj.local_printer_name}"
        return "—"


@admin.register(StationSession)
class StationSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'station', 'client_ip', 'connected_at']
    list_filter = ['station']
    readonly_fields = ['connected_at']


@admin.register(PrintTemplate)
class PrintTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'template_type', 'dimensions_display', 'dpi',
        'is_default', 'is_active',
    ]
    list_filter = ['template_type', 'is_default', 'is_active', 'unit']
    search_fields = ['name']
    list_editable = ['is_default', 'is_active']
    fieldsets = [
        ('📋 معلومات أساسية', {
            'fields': ['name', 'template_type', 'is_default', 'is_active'],
        }),
        ('📐 الأبعاد', {
            'fields': ['width', 'height', 'unit', 'dpi', 'margin_top', 'margin_left'],
        }),
        ('🔤 الخطوط والباركود', {
            'fields': ['font_size', 'barcode_height', 'barcode_width'],
        }),
        ('📝 القوالب', {
            'classes': ['collapse'],
            'fields': ['zpl_template', 'escpos_template', 'html_template'],
        }),
    ]

    @admin.display(description='الأبعاد')
    def dimensions_display(self, obj):
        return f"{obj.width}×{obj.height} {obj.unit}"
