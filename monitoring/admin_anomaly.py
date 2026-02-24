"""
Anomaly Detection Admin
لوحة تحكم نظام الكشف عن الشذوذات

إدارة التنبيهات والتحذيرات
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponseRedirect
from .anomaly_detection import AnomalyAlert, ProactiveWarning, anomaly_detector, proactive_warner


@admin.register(AnomalyAlert)
class AnomalyAlertAdmin(admin.ModelAdmin):
    """إدارة تنبيهات الشذوذ"""
    
    list_display = [
        'title', 'category_badge', 'severity_badge', 'status_badge',
        'deviation_display', 'assigned_to', 'detected_at'
    ]
    
    list_filter = [
        'category', 'severity', 'status', 'anomaly_type', 'detected_at'
    ]
    
    search_fields = [
        'title', 'description', 'anomaly_type'
    ]
    
    readonly_fields = [
        'detected_at', 'resolved_at', 'deviation_display_detail',
        'recommended_actions_display'
    ]
    
    fieldsets = (
        ('التصنيف', {
            'fields': ('category', 'severity', 'status', 'anomaly_type')
        }),
        ('التفاصيل', {
            'fields': ('title', 'description')
        }),
        ('البيانات', {
            'fields': (
                'detected_value', 'expected_value', 'deviation_percentage',
                'deviation_display_detail'
            )
        }),
        ('الإجراءات', {
            'fields': ('recommended_actions', 'recommended_actions_display')
        }),
        ('المراجع', {
            'fields': ('related_model', 'related_id'),
            'classes': ('collapse',)
        }),
        ('المسؤول', {
            'fields': ('assigned_to', 'notes')
        }),
        ('التواريخ', {
            'fields': ('detected_at', 'resolved_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_as_investigating',
        'mark_as_acknowledged',
        'mark_as_resolved',
        'mark_as_false_positive'
    ]
    
    def category_badge(self, obj):
        """شارة الفئة"""
        colors = {
            'sales': '#2196F3',
            'inventory': '#FF9800',
            'production': '#4CAF50',
            'financial': '#F44336',
            'quality': '#9C27B0',
            'performance': '#00BCD4',
            'security': '#E91E63',
        }
        color = colors.get(obj.category, '#9E9E9E')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_category_display()
        )
    category_badge.short_description = 'الفئة'
    
    def severity_badge(self, obj):
        """شارة الخطورة"""
        colors = {
            'low': '#4CAF50',
            'medium': '#FF9800',
            'high': '#FF5722',
            'critical': '#F44336',
        }
        color = colors.get(obj.severity, '#9E9E9E')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_severity_display()
        )
    severity_badge.short_description = 'الخطورة'
    
    def status_badge(self, obj):
        """شارة الحالة"""
        colors = {
            'new': '#F44336',
            'investigating': '#FF9800',
            'acknowledged': '#2196F3',
            'resolved': '#4CAF50',
            'false_positive': '#9E9E9E',
        }
        color = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'الحالة'
    
    def deviation_display(self, obj):
        """عرض الانحراف"""
        if obj.deviation_percentage:
            return f'{obj.deviation_percentage}%'
        return '-'
    deviation_display.short_description = 'الانحراف'
    
    def deviation_display_detail(self, obj):
        """عرض تفصيلي للانحراف"""
        if obj.detected_value and obj.expected_value:
            return format_html(
                '<table>'
                '<tr><td><b>القيمة المكتشفة:</b></td><td>{}</td></tr>'
                '<tr><td><b>القيمة المتوقعة:</b></td><td>{}</td></tr>'
                '<tr><td><b>الانحراف:</b></td><td style="color: red; font-weight: bold;">{}%</td></tr>'
                '</table>',
                obj.detected_value,
                obj.expected_value,
                obj.deviation_percentage or 0
            )
        return '-'
    deviation_display_detail.short_description = 'تفاصيل الانحراف'
    
    def recommended_actions_display(self, obj):
        """عرض الإجراءات الموصى بها"""
        if obj.recommended_actions:
            actions_html = '<ul>'
            for action in obj.recommended_actions:
                actions_html += f'<li>{action}</li>'
            actions_html += '</ul>'
            return format_html(actions_html)
        return '-'
    recommended_actions_display.short_description = 'الإجراءات الموصى بها'
    
    # Actions
    def mark_as_investigating(self, request, queryset):
        """تعيين كقيد التحقيق"""
        queryset.update(status='investigating')
        self.message_user(request, f'تم تعيين {queryset.count()} تنبيه كقيد التحقيق')
    mark_as_investigating.short_description = 'تعيين كقيد التحقيق'
    
    def mark_as_acknowledged(self, request, queryset):
        """تعيين كمطلع عليه"""
        queryset.update(status='acknowledged')
        self.message_user(request, f'تم تعيين {queryset.count()} تنبيه كمطلع عليه')
    mark_as_acknowledged.short_description = 'تعيين كمطلع عليه'
    
    def mark_as_resolved(self, request, queryset):
        """تعيين كمحلول"""
        from django.utils import timezone
        queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f'تم تعيين {queryset.count()} تنبيه كمحلول')
    mark_as_resolved.short_description = 'تعيين كمحلول'
    
    def mark_as_false_positive(self, request, queryset):
        """تعيين كإنذار خاطئ"""
        queryset.update(status='false_positive')
        self.message_user(request, f'تم تعيين {queryset.count()} تنبيه كإنذار خاطئ')
    mark_as_false_positive.short_description = 'تعيين كإنذار خاطئ'
    
    # Custom views
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-detection/', self.admin_site.admin_view(self.run_detection_view), name='anomaly-run-detection'),
        ]
        return custom_urls + urls
    
    def run_detection_view(self, request):
        """صفحة تشغيل الكشف"""
        if request.method == 'POST':
            results = anomaly_detector.run_all_detections()
            
            total = sum(len(alerts) for alerts in results.values())
            
            self.message_user(request, f'تم اكتشاف {total} شذوذ جديد')
            return HttpResponseRedirect('../')
        
        return render(request, 'admin/anomaly_detection/run_detection.html')


@admin.register(ProactiveWarning)
class ProactiveWarningAdmin(admin.ModelAdmin):
    """إدارة التحذيرات الاستباقية"""
    
    list_display = [
        'title', 'warning_type_badge', 'predicted_date',
        'confidence_display', 'is_active', 'created_at'
    ]
    
    list_filter = [
        'warning_type', 'is_active', 'is_dismissed', 'predicted_date', 'created_at'
    ]
    
    search_fields = ['title', 'description']
    
    readonly_fields = [
        'created_at', 'updated_at', 'confidence_display_detail',
        'preventive_actions_display', 'prediction_chart'
    ]
    
    fieldsets = (
        ('التحذير', {
            'fields': ('warning_type', 'title', 'description')
        }),
        ('التوقعات', {
            'fields': (
                'predicted_date', 'confidence_level',
                'confidence_display_detail', 'prediction_chart'
            )
        }),
        ('البيانات', {
            'fields': (
                'current_value', 'threshold_value', 'predicted_value'
            )
        }),
        ('الإجراءات الوقائية', {
            'fields': ('preventive_actions', 'preventive_actions_display')
        }),
        ('الحالة', {
            'fields': ('is_active', 'is_dismissed')
        }),
        ('تواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['dismiss_warnings', 'activate_warnings']
    
    def warning_type_badge(self, obj):
        """شارة نوع التحذير"""
        colors = {
            'stock_out': '#FF5722',
            'capacity_overload': '#FF9800',
            'cash_flow': '#F44336',
            'deadline_risk': '#E91E63',
            'quality_trend': '#9C27B0',
            'cost_overrun': '#FF5722',
        }
        color = colors.get(obj.warning_type, '#9E9E9E')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_warning_type_display()
        )
    warning_type_badge.short_description = 'نوع التحذير'
    
    def confidence_display(self, obj):
        """عرض مستوى الثقة"""
        color = '#4CAF50' if obj.confidence_level >= 80 else '#FF9800' if obj.confidence_level >= 60 else '#F44336'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, obj.confidence_level
        )
    confidence_display.short_description = 'الثقة'
    
    def confidence_display_detail(self, obj):
        """عرض تفصيلي لمستوى الثقة"""
        width = int(obj.confidence_level)
        color = '#4CAF50' if width >= 80 else '#FF9800' if width >= 60 else '#F44336'
        
        return format_html(
            '<div style="width: 200px; background: #e0e0e0; border-radius: 5px; overflow: hidden;">'
            '<div style="width: {}%; background: {}; color: white; text-align: center; padding: 5px; font-weight: bold;">'
            '{}%'
            '</div>'
            '</div>',
            width, color, obj.confidence_level
        )
    confidence_display_detail.short_description = 'مستوى الثقة'
    
    def preventive_actions_display(self, obj):
        """عرض الإجراءات الوقائية"""
        if obj.preventive_actions:
            actions_html = '<ol style="margin: 0; padding-right: 20px;">'
            for action in obj.preventive_actions:
                actions_html += f'<li style="margin-bottom: 5px;">{action}</li>'
            actions_html += '</ol>'
            return format_html(actions_html)
        return '-'
    preventive_actions_display.short_description = 'الإجراءات الوقائية'
    
    def prediction_chart(self, obj):
        """رسم بياني للتوقع"""
        if obj.current_value and obj.predicted_value:
            current = float(obj.current_value)
            predicted = float(obj.predicted_value)
            threshold = float(obj.threshold_value) if obj.threshold_value else 0
            
            max_value = max(current, predicted, threshold) * 1.2
            
            current_width = (current / max_value * 100) if max_value > 0 else 0
            predicted_width = (predicted / max_value * 100) if max_value > 0 else 0
            threshold_width = (threshold / max_value * 100) if max_value > 0 else 0
            
            return format_html(
                '<div style="width: 300px;">'
                '<div style="margin-bottom: 10px;">'
                '<b>القيمة الحالية:</b> {}<br>'
                '<div style="width: {}%; background: #2196F3; height: 20px; margin: 5px 0;"></div>'
                '</div>'
                '<div style="margin-bottom: 10px;">'
                '<b>القيمة المتوقعة:</b> {}<br>'
                '<div style="width: {}%; background: #FF5722; height: 20px; margin: 5px 0;"></div>'
                '</div>'
                '<div style="margin-bottom: 10px;">'
                '<b>الحد:</b> {}<br>'
                '<div style="width: {}%; background: #FFC107; height: 20px; margin: 5px 0;"></div>'
                '</div>'
                '</div>',
                current, current_width,
                predicted, predicted_width,
                threshold, threshold_width
            )
        return '-'
    prediction_chart.short_description = 'رسم بياني'
    
    # Actions
    def dismiss_warnings(self, request, queryset):
        """تجاهل التحذيرات"""
        queryset.update(is_dismissed=True, is_active=False)
        self.message_user(request, f'تم تجاهل {queryset.count()} تحذير')
    dismiss_warnings.short_description = 'تجاهل التحذيرات'
    
    def activate_warnings(self, request, queryset):
        """تفعيل التحذيرات"""
        queryset.update(is_dismissed=False, is_active=True)
        self.message_user(request, f'تم تفعيل {queryset.count()} تحذير')
    activate_warnings.short_description = 'تفعيل التحذيرات'
    
    # Custom views
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-predictions/', self.admin_site.admin_view(self.run_predictions_view), name='warning-run-predictions'),
        ]
        return custom_urls + urls
    
    def run_predictions_view(self, request):
        """صفحة تشغيل التنبؤات"""
        if request.method == 'POST':
            results = proactive_warner.run_all_predictions()
            
            total = sum(len(warnings) for warnings in results.values())
            
            self.message_user(request, f'تم إنشاء {total} تحذير جديد')
            return HttpResponseRedirect('../')
        
        return render(request, 'admin/anomaly_detection/run_predictions.html')
