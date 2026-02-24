"""
خدمات بناء التقارير المتقدمة
"""

from django.db.models import Q, Sum, Avg, Count, Min, Max, F
from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import json
# import pandas as pd  # سيتم إضافته لاحقاً
from io import BytesIO
# from reportlab.lib.pagesizes import A4, letter  # سيتم إضافته لاحقاً
# from reportlab.lib import colors
# from reportlab.lib.units import inch
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# from openpyxl import Workbook  # سيتم إضافته لاحقاً
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
import csv


class ReportDataService:
    """خدمة جلب البيانات من مصادر متعددة"""
    
    @staticmethod
    def get_model_class(model_name):
        """الحصول على كلاس الموديل من اسمه"""
        try:
            # محاولة الحصول من app.Model
            if '.' in model_name:
                app_label, model = model_name.split('.')
                return apps.get_model(app_label, model)
            else:
                # البحث في جميع التطبيقات
                for model in apps.get_models():
                    if model.__name__.lower() == model_name.lower():
                        return model
                raise ValueError(f"Model {model_name} not found")
        except Exception as e:
            raise ValueError(f"Error loading model {model_name}: {str(e)}")
    
    @staticmethod
    def apply_filters(queryset, filters_config):
        """تطبيق الفلاتر على QuerySet"""
        q_objects = Q()
        current_group = 0
        group_q = Q()
        
        for filter_item in filters_config:
            field_name = filter_item.get('field_name')
            operator = filter_item.get('operator')
            value = filter_item.get('value')
            group_id = filter_item.get('group_id', 0)
            logical_op = filter_item.get('logical_operator', 'AND')
            
            # بناء الشرط
            filter_q = ReportDataService._build_filter_condition(
                field_name, operator, value
            )
            
            # التعامل مع المجموعات
            if group_id != current_group:
                if group_q:
                    q_objects &= group_q
                group_q = filter_q
                current_group = group_id
            else:
                if logical_op == 'AND':
                    group_q &= filter_q
                else:
                    group_q |= filter_q
        
        # إضافة المجموعة الأخيرة
        if group_q:
            q_objects &= group_q
        
        return queryset.filter(q_objects) if q_objects else queryset
    
    @staticmethod
    def _build_filter_condition(field_name, operator, value):
        """بناء شرط الفلتر"""
        lookup_map = {
            'equals': '__exact',
            'not_equals': '__exact',
            'greater_than': '__gt',
            'greater_than_equal': '__gte',
            'less_than': '__lt',
            'less_than_equal': '__lte',
            'contains': '__icontains',
            'not_contains': '__icontains',
            'starts_with': '__istartswith',
            'ends_with': '__iendswith',
            'in': '__in',
            'not_in': '__in',
            'is_null': '__isnull',
            'is_not_null': '__isnull',
        }
        
        lookup = lookup_map.get(operator, '__exact')
        filter_kwargs = {f"{field_name}{lookup}": value}
        
        q = Q(**filter_kwargs)
        
        # عكس الشرط للعمليات السلبية
        if operator in ['not_equals', 'not_contains', 'not_in']:
            q = ~q
        
        # القيم الخاصة
        if operator == 'is_null':
            q = Q(**{f"{field_name}__isnull": True})
        elif operator == 'is_not_null':
            q = Q(**{f"{field_name}__isnull": False})
        
        return q
    
    @staticmethod
    def apply_aggregations(queryset, fields_config):
        """تطبيق التجميعات"""
        aggregations = {}
        
        for field in fields_config:
            agg_type = field.get('aggregation', 'none')
            if agg_type == 'none':
                continue
            
            field_name = field.get('source_field')
            alias = field.get('name', field_name)
            
            agg_map = {
                'sum': Sum(field_name),
                'avg': Avg(field_name),
                'count': Count(field_name),
                'min': Min(field_name),
                'max': Max(field_name),
            }
            
            if agg_type in agg_map:
                aggregations[alias] = agg_map[agg_type]
        
        if aggregations:
            return queryset.aggregate(**aggregations)
        return None
    
    @staticmethod
    def fetch_data(template):
        """جلب البيانات حسب التكوين"""
        # الحصول على الموديل
        model_class = ReportDataService.get_model_class(template.data_source)
        queryset = model_class.objects.all()
        
        # تطبيق الفلاتر
        filters = template.get_filters_config()
        if filters:
            queryset = ReportDataService.apply_filters(queryset, filters)
        
        # تطبيق الترتيب
        sorting = json.loads(template.sorting_config) if template.sorting_config else []
        if sorting:
            order_fields = []
            for sort_item in sorting:
                field_name = sort_item.get('field')
                direction = sort_item.get('direction', 'asc')
                order_fields.append(f"{'-' if direction == 'desc' else ''}{field_name}")
            queryset = queryset.order_by(*order_fields)
        
        # استخراج الحقول
        fields = template.get_fields_config()
        field_names = [f.get('source_field') for f in fields if not f.get('is_calculated')]
        
        # تطبيق التجميع
        grouping = json.loads(template.grouping_config) if template.grouping_config else []
        if grouping:
            group_fields = [g.get('field') for g in grouping]
            queryset = queryset.values(*group_fields)
            
            # تطبيق Aggregations
            agg_result = ReportDataService.apply_aggregations(queryset, fields)
            if agg_result:
                return list(queryset.annotate(**agg_result))
        
        # جلب البيانات العادية
        return list(queryset.values(*field_names))


class ReportExecutionService:
    """خدمة تنفيذ التقارير - مبسطة"""
    
    @staticmethod
    def execute_report(template, parameters, output_format, user=None):
        """تنفيذ التقرير وتوليد الملف"""
        from reports.models_builder import ReportExecution
        
        # إنشاء سجل التنفيذ
        execution = ReportExecution.objects.create(
            template=template,
            executed_by=user,
            parameters=json.dumps(parameters),
            output_format=output_format,
            status='running',
            started_at=timezone.now()
        )
        
        try:
            # جلب البيانات
            data = ReportDataService.fetch_data(template)
            execution.rows_processed = len(data)
            
            # تحديث الحالة
            execution.status = 'completed'
            execution.completed_at = timezone.now()
            if execution.completed_at and execution.started_at:
                execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()
            else:
                execution.execution_time = 0
            
            # تحديث إحصائيات القالب
            template.run_count += 1
            template.last_run_at = timezone.now()
            template.save()
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            import traceback
            execution.error_traceback = traceback.format_exc()
            execution.completed_at = timezone.now()
        
        execution.save()
        return execution
