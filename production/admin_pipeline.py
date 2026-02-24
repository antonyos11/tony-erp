from django.contrib import admin
from django.utils.html import format_html
from production.models_pipeline import PipelineBoard, PipelineStageEntry, PipelinePrintJob, ProductionIssue


class PipelineStageEntryInline(admin.TabularInline):
    model = PipelineStageEntry
    extra = 0
    readonly_fields = ['started_at', 'completed_at', 'started_by', 'completed_by']
    fields = [
        'work_center', 'sequence', 'status', 'started_at', 'completed_at',
        'started_by', 'completed_by', 'failure_reason', 'failure_category',
        'print_status', 'notes',
    ]


@admin.register(PipelineBoard)
class PipelineBoardAdmin(admin.ModelAdmin):
    list_display = ['production_order', 'overall_progress', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['production_order__number']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PipelineStageEntryInline]


@admin.register(PipelineStageEntry)
class PipelineStageEntryAdmin(admin.ModelAdmin):
    list_display = [
        'board', 'work_center', 'sequence', 'status',
        'print_status', 'started_at', 'completed_at'
    ]
    list_filter = ['status', 'print_status', 'failure_category']
    search_fields = ['board__production_order__number', 'work_center__name']


@admin.register(PipelinePrintJob)
class PipelinePrintJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'production_order', 'status', 'copies', 'created_at', 'completed_at']
    list_filter = ['status']
    search_fields = ['production_order__number']
    readonly_fields = ['id', 'created_at']


@admin.register(ProductionIssue)
class ProductionIssueAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'production_order', 'work_center', 'category_display',
        'severity_badge', 'status_badge', 'reported_by', 'reported_at',
    ]
    list_filter = ['severity', 'status', 'category', 'work_center']
    search_fields = ['title', 'description', 'production_order__number']
    readonly_fields = ['reported_at', 'resolved_at']
    raw_id_fields = ['production_order', 'stage_entry', 'reported_by', 'assigned_to']
    fieldsets = [
        ('📋 معلومات المشكلة', {
            'fields': [
                'production_order', 'stage_entry', 'work_center',
                'title', 'description', 'category', 'severity', 'status',
            ],
        }),
        ('📊 التأثير', {
            'fields': ['units_affected', 'downtime_minutes', 'estimated_cost'],
        }),
        ('👤 الأشخاص', {
            'fields': ['reported_by', 'assigned_to', 'reported_at', 'resolved_at'],
        }),
        ('📸 الأدلة والحل', {
            'fields': ['photo', 'resolution'],
            'classes': ['collapse'],
        }),
    ]
    actions = ['mark_resolved', 'mark_escalated']

    @admin.display(description='التصنيف')
    def category_display(self, obj):
        icons = {
            'material_defect': '🧱', 'machine_failure': '⚙️',
            'quality_issue': '🔍', 'missing_material': '📦',
            'worker_error': '👷', 'design_issue': '📐',
            'power_outage': '⚡', 'other': '❓',
        }
        return f"{icons.get(obj.category, '❓')} {obj.get_category_display()}"

    @admin.display(description='الخطورة')
    def severity_badge(self, obj):
        colors = {
            'low': '#28a745', 'medium': '#ffc107',
            'high': '#fd7e14', 'critical': '#dc3545',
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:0.8em;">{}</span>',
            color, obj.get_severity_display()
        )

    @admin.display(description='الحالة')
    def status_badge(self, obj):
        colors = {
            'open': '#dc3545', 'investigating': '#ffc107',
            'resolved': '#28a745', 'escalated': '#fd7e14', 'closed': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:0.8em;">{}</span>',
            color, obj.get_status_display()
        )

    @admin.action(description="✅ تحديد كـ 'تم الحل'")
    def mark_resolved(self, request, queryset):
        from django.utils import timezone as tz
        updated = queryset.filter(status__in=['open', 'investigating']).update(
            status='resolved', resolved_at=tz.now(),
        )
        self.message_user(request, f"تم تحديث {updated} مشكلة كمحلولة.")

    @admin.action(description="⬆️ تصعيد المشاكل المحددة")
    def mark_escalated(self, request, queryset):
        updated = queryset.filter(status__in=['open', 'investigating']).update(
            status='escalated',
        )
        self.message_user(request, f"تم تصعيد {updated} مشكلة.")
