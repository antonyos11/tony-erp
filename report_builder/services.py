"""
خدمات منشئ التقارير
Report Builder Services
"""

from django.db.models import Sum, Count, Avg, Min, Max, F, Q
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
import json


class DataSourceService:
    """خدمة مصادر البيانات"""
    
    @staticmethod
    def get_available_models():
        """الحصول على النماذج المتاحة"""
        models = []
        excluded_apps = ['admin', 'auth', 'contenttypes', 'sessions', 'messages']
        
        for app_config in apps.get_app_configs():
            if app_config.name.split('.')[-1] in excluded_apps:
                continue
            
            for model in app_config.get_models():
                ct = ContentType.objects.get_for_model(model)
                models.append({
                    'id': ct.id,
                    'app': app_config.verbose_name,
                    'model': model._meta.verbose_name.title(),
                    'model_name': model.__name__,
                    'fields': DataSourceService.get_model_fields(model)
                })
        
        return models
    
    @staticmethod
    def get_model_fields(model):
        """الحصول على حقول النموذج"""
        fields = []
        
        for field in model._meta.get_fields():
            if hasattr(field, 'verbose_name'):
                fields.append({
                    'name': field.name,
                    'verbose_name': str(field.verbose_name),
                    'type': field.get_internal_type() if hasattr(field, 'get_internal_type') else 'relation',
                    'is_relation': field.is_relation,
                })
        
        return fields


class ReportExecutionService:
    """خدمة تنفيذ التقارير"""
    
    def __init__(self, report):
        self.report = report
        self.data_source = report.data_source
    
    def execute(self, parameters=None):
        """تنفيذ التقرير"""
        from .models import ReportExecution
        import time
        from django.utils import timezone
        
        execution = ReportExecution.objects.create(
            report=self.report,
            parameters=parameters or {},
            status='running'
        )
        
        start_time = time.time()
        
        try:
            # الحصول على البيانات
            data = self.get_data(parameters)
            
            # تطبيق الفلاتر
            data = self.apply_filters(data)
            
            # تطبيق التجميع
            if self.report.grouping:
                data = self.apply_grouping(data)
            
            # تطبيق الترتيب
            data = self.apply_sorting(data)
            
            # تحديث التنفيذ
            execution.status = 'completed'
            execution.rows_count = len(data) if isinstance(data, list) else data.count()
            execution.execution_time = time.time() - start_time
            execution.completed_at = timezone.now()
            execution.save()
            
            return data
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.execution_time = time.time() - start_time
            execution.completed_at = timezone.now()
            execution.save()
            raise
    
    def get_data(self, parameters=None):
        """الحصول على البيانات"""
        if self.data_source.source_type == 'model':
            return self.get_model_data()
        elif self.data_source.source_type == 'sql':
            return self.get_sql_data()
        return []
    
    def get_model_data(self):
        """الحصول على بيانات النموذج"""
        if not self.data_source.content_type:
            return []
        
        model = self.data_source.content_type.model_class()
        queryset = model.objects.all()
        
        # تحديد الأعمدة
        if self.report.selected_columns:
            queryset = queryset.values(*self.report.selected_columns)
        
        return queryset
    
    def get_sql_data(self):
        """الحصول على بيانات SQL"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute(self.data_source.sql_query)
            columns = [col[0] for col in cursor.description]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
    
    def apply_filters(self, data):
        """تطبيق الفلاتر"""
        if not self.report.filters:
            return data
        
        if hasattr(data, 'filter'):
            q = Q()
            for f in self.report.filters:
                field = f.get('field')
                operator = f.get('operator')
                value = f.get('value')
                
                if operator == 'equals':
                    q &= Q(**{field: value})
                elif operator == 'contains':
                    q &= Q(**{f'{field}__icontains': value})
                elif operator == 'gt':
                    q &= Q(**{f'{field}__gt': value})
                elif operator == 'lt':
                    q &= Q(**{f'{field}__lt': value})
                elif operator == 'gte':
                    q &= Q(**{f'{field}__gte': value})
                elif operator == 'lte':
                    q &= Q(**{f'{field}__lte': value})
            
            return data.filter(q)
        
        return data
    
    def apply_grouping(self, data):
        """تطبيق التجميع"""
        if not self.report.grouping or not hasattr(data, 'values'):
            return data
        
        group_fields = [g['field'] for g in self.report.grouping]
        aggregations = {}
        
        for calc in self.report.calculations:
            field = calc.get('field')
            func = calc.get('function')
            alias = calc.get('alias', f'{func}_{field}')
            
            if func == 'sum':
                aggregations[alias] = Sum(field)
            elif func == 'count':
                aggregations[alias] = Count(field)
            elif func == 'avg':
                aggregations[alias] = Avg(field)
            elif func == 'min':
                aggregations[alias] = Min(field)
            elif func == 'max':
                aggregations[alias] = Max(field)
        
        return data.values(*group_fields).annotate(**aggregations)
    
    def apply_sorting(self, data):
        """تطبيق الترتيب"""
        if not self.report.sorting or not hasattr(data, 'order_by'):
            return data
        
        order_fields = []
        for s in self.report.sorting:
            field = s.get('field')
            direction = s.get('direction', 'asc')
            if direction == 'desc':
                field = f'-{field}'
            order_fields.append(field)
        
        return data.order_by(*order_fields)


class ChartDataService:
    """خدمة بيانات الرسوم البيانية"""
    
    @staticmethod
    def prepare_chart_data(widget, data):
        """تحضير بيانات الرسم البياني"""
        config = widget.data_config
        chart_type = widget.widget_type
        
        label_field = config.get('label_field')
        value_field = config.get('value_field')
        
        labels = []
        values = []
        
        for item in data:
            if isinstance(item, dict):
                labels.append(item.get(label_field, ''))
                values.append(item.get(value_field, 0))
        
        return {
            'labels': labels,
            'datasets': [{
                'data': values,
                'backgroundColor': ChartDataService.get_colors(len(values)),
            }]
        }
    
    @staticmethod
    def get_colors(count):
        """الحصول على ألوان"""
        colors = [
            '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
            '#5a5c69', '#858796', '#6610f2', '#e83e8c', '#fd7e14'
        ]
        return (colors * ((count // len(colors)) + 1))[:count]
