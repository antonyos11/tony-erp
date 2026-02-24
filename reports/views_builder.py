"""
Views لنظام بناء التقارير المتقدم
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
import json

from reports.models_builder import (
    ReportTemplate, ReportExecution, ReportField,
    ReportFilter, SavedReport
)
from reports.report_builder_service import (
    ReportDataService, ReportExecutionService
)


@login_required
def report_builder_dashboard(request):
    """لوحة تحكم بناء التقارير"""
    # فلترة القوالب
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    templates = ReportTemplate.objects.filter(is_active=True)
    
    # الأذونات
    if not request.user.is_superuser:
        templates = templates.filter(
            Q(is_public=True) |
            Q(created_by=request.user) |
            Q(allowed_users=request.user) |
            Q(allowed_groups__in=request.user.groups.all())
        ).distinct()
    
    if search:
        templates = templates.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    
    if category:
        templates = templates.filter(category=category)
    
    templates = templates.order_by('-created_at')
    
    # الصفحات
    paginator = Paginator(templates, 12)
    page = request.GET.get('page', 1)
    templates_page = paginator.get_page(page)
    
    # الإحصائيات
    stats = {
        'total_templates': ReportTemplate.objects.filter(is_active=True).count(),
        'my_templates': ReportTemplate.objects.filter(created_by=request.user, is_active=True).count(),
        'executions_today': ReportExecution.objects.filter(
            executed_by=request.user,
            created_at__date=timezone.now().date()
        ).count(),
        'scheduled_reports': ReportTemplate.objects.filter(
            is_scheduled=True,
            is_active=True
        ).count(),
    }
    
    context = {
        'templates': templates_page,
        'categories': ReportTemplate.CATEGORY_CHOICES,
        'stats': stats,
        'search': search,
        'selected_category': category,
    }
    
    return render(request, 'reports/builder/dashboard.html', context)


@login_required
def create_report_template(request):
    """إنشاء قالب تقرير جديد"""
    if request.method == 'POST':
        try:
            # البيانات الأساسية
            template = ReportTemplate.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                category=request.POST.get('category'),
                data_source=request.POST.get('data_source'),
                created_by=request.user,
                
                # التكوين
                fields_config=request.POST.get('fields_config', '[]'),
                filters_config=request.POST.get('filters_config', '[]'),
                grouping_config=request.POST.get('grouping_config', '[]'),
                sorting_config=request.POST.get('sorting_config', '[]'),
                
                # العرض
                layout=request.POST.get('layout', 'table'),
                chart_type=request.POST.get('chart_type', ''),
                theme=request.POST.get('theme', 'default'),
                
                # الأذونات
                is_public=request.POST.get('is_public') == 'on',
                
                # الصيغ
                supported_formats=request.POST.get('supported_formats', 'pdf,excel,csv'),
            )
            
            messages.success(request, 'تم إنشاء القالب بنجاح!')
            return redirect('reports:edit_template', template_id=template.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء القالب: {str(e)}')
    
    # GET request
    from django.apps import apps
    available_models = []
    for model in apps.get_models():
        app_label = model._meta.app_label
        model_name = model.__name__
        available_models.append({
            'value': f'{app_label}.{model_name}',
            'label': f'{model._meta.verbose_name} ({app_label})'
        })
    
    context = {
        'available_models': available_models,
        'categories': ReportTemplate.CATEGORY_CHOICES,
    }
    
    return render(request, 'reports/builder/create.html', context)


@login_required
def edit_report_template(request, template_id):
    """تحرير قالب تقرير"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    # التحقق من الأذونات
    if not request.user.is_superuser and template.created_by != request.user:
        messages.error(request, 'ليس لديك صلاحية لتحرير هذا القالب')
        return redirect('reports:dashboard')
    
    if request.method == 'POST':
        try:
            # تحديث البيانات
            template.name = request.POST.get('name')
            template.description = request.POST.get('description', '')
            template.category = request.POST.get('category')
            template.data_source = request.POST.get('data_source')
            
            template.fields_config = request.POST.get('fields_config', '[]')
            template.filters_config = request.POST.get('filters_config', '[]')
            template.grouping_config = request.POST.get('grouping_config', '[]')
            template.sorting_config = request.POST.get('sorting_config', '[]')
            
            template.layout = request.POST.get('layout', 'table')
            template.chart_type = request.POST.get('chart_type', '')
            template.theme = request.POST.get('theme', 'default')
            
            template.is_public = request.POST.get('is_public') == 'on'
            template.supported_formats = request.POST.get('supported_formats', 'pdf,excel,csv')
            
            template.save()
            
            messages.success(request, 'تم تحديث القالب بنجاح!')
            return redirect('reports:edit_template', template_id=template.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في التحديث: {str(e)}')
    
    context = {
        'template': template,
        'fields': template.get_fields_config(),
        'filters': template.get_filters_config(),
        'categories': ReportTemplate.CATEGORY_CHOICES,
    }
    
    return render(request, 'reports/builder/edit.html', context)


@login_required
def preview_report(request, template_id):
    """معاينة التقرير"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    try:
        # جلب البيانات (أول 100 صف)
        data = ReportDataService.fetch_data(template)[:100]
        
        context = {
            'template': template,
            'data': data,
            'fields': template.get_fields_config(),
            'preview_mode': True,
        }
        
        return render(request, 'reports/builder/preview.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في معاينة التقرير: {str(e)}')
        return redirect('reports:dashboard')


@login_required
def execute_report(request, template_id):
    """تنفيذ التقرير وتوليد الملف"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    if request.method == 'POST':
        try:
            output_format = request.POST.get('output_format', 'pdf')
            parameters = json.loads(request.POST.get('parameters', '{}'))
            
            # التنفيذ
            execution = ReportExecutionService.execute_report(
                template=template,
                parameters=parameters,
                output_format=output_format,
                user=request.user
            )
            
            if execution.status == 'completed':
                messages.success(request, 'تم توليد التقرير بنجاح!')
                return redirect('reports:download_report', execution_id=execution.id)
            else:
                messages.error(request, f'فشل التنفيذ: {execution.error_message}')
                return redirect('reports:dashboard')
                
        except Exception as e:
            messages.error(request, f'خطأ في التنفيذ: {str(e)}')
            return redirect('reports:dashboard')
    
    # GET - نموذج التنفيذ
    context = {
        'template': template,
        'supported_formats': template.get_supported_formats_list(),
    }
    
    return render(request, 'reports/builder/execute.html', context)


@login_required
def download_report(request, execution_id):
    """تحميل ملف التقرير"""
    execution = get_object_or_404(ReportExecution, id=execution_id)
    
    # التحقق من الأذونات
    if not request.user.is_superuser and execution.executed_by != request.user:
        messages.error(request, 'ليس لديك صلاحية لتحميل هذا التقرير')
        return redirect('reports:dashboard')
    
    if execution.output_file:
        response = FileResponse(
            execution.output_file.open('rb'),
            as_attachment=True,
            filename=execution.output_file.name.split('/')[-1]
        )
        return response
    else:
        messages.error(request, 'الملف غير متوفر')
        return redirect('reports:dashboard')


@login_required
def execution_history(request):
    """سجل تنفيذات التقارير"""
    executions = ReportExecution.objects.all()
    
    if not request.user.is_superuser:
        executions = executions.filter(executed_by=request.user)
    
    # الفلترة
    status = request.GET.get('status', '')
    if status:
        executions = executions.filter(status=status)
    
    template_id = request.GET.get('template', '')
    if template_id:
        executions = executions.filter(template_id=template_id)
    
    executions = executions.order_by('-created_at')
    
    # الصفحات
    paginator = Paginator(executions, 20)
    page = request.GET.get('page', 1)
    executions_page = paginator.get_page(page)
    
    context = {
        'executions': executions_page,
        'statuses': ReportExecution.STATUS_CHOICES,
        'templates': ReportTemplate.objects.filter(is_active=True),
    }
    
    return render(request, 'reports/builder/history.html', context)


@login_required
def delete_template(request, template_id):
    """حذف قالب تقرير"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    # التحقق من الأذونات
    if not request.user.is_superuser and template.created_by != request.user:
        messages.error(request, 'ليس لديك صلاحية لحذف هذا القالب')
        return redirect('reports:dashboard')
    
    if request.method == 'POST':
        template.is_active = False
        template.save()
        messages.success(request, 'تم حذف القالب بنجاح!')
        return redirect('reports:dashboard')
    
    context = {'template': template}
    return render(request, 'reports/builder/delete_confirm.html', context)


# AJAX APIs

@login_required
@require_http_methods(['GET'])
def get_model_fields(request):
    """الحصول على حقول الموديل (AJAX)"""
    model_name = request.GET.get('model')
    
    try:
        model_class = ReportDataService.get_model_class(model_name)
        fields = []
        
        for field in model_class._meta.get_fields():
            if not field.many_to_many and not field.one_to_many:
                fields.append({
                    'name': field.name,
                    'label': getattr(field, 'verbose_name', field.name),
                    'type': field.get_internal_type(),
                })
        
        return JsonResponse({'success': True, 'fields': fields})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def validate_report_config(request):
    """التحقق من صحة تكوين التقرير (AJAX)"""
    try:
        data = json.loads(request.body)
        
        # التحقق من المصدر
        model_class = ReportDataService.get_model_class(data.get('data_source'))
        
        # التحقق من الحقول
        fields_config = data.get('fields_config', [])
        if not fields_config:
            return JsonResponse({'valid': False, 'error': 'يجب تحديد حقل واحد على الأقل'})
        
        # التحقق من الفلاتر
        filters_config = data.get('filters_config', [])
        # يمكن إضافة تحققات إضافية
        
        return JsonResponse({'valid': True})
        
    except Exception as e:
        return JsonResponse({'valid': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def duplicate_template(request, template_id):
    """نسخ قالب تقرير"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    try:
        # إنشاء نسخة
        new_template = ReportTemplate.objects.create(
            name=f"{template.name} (نسخة)",
            description=template.description,
            category=template.category,
            data_source=template.data_source,
            fields_config=template.fields_config,
            filters_config=template.filters_config,
            grouping_config=template.grouping_config,
            sorting_config=template.sorting_config,
            layout=template.layout,
            chart_type=template.chart_type,
            theme=template.theme,
            supported_formats=template.supported_formats,
            created_by=request.user,
            is_public=False,
        )
        
        return JsonResponse({
            'success': True,
            'template_id': new_template.id,
            'message': 'تم نسخ القالب بنجاح'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def schedule_report(request, template_id):
    """جدولة تقرير"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    # التحقق من الأذونات
    if not request.user.is_superuser and template.created_by != request.user:
        messages.error(request, 'ليس لديك صلاحية لجدولة هذا التقرير')
        return redirect('reports:dashboard')
    
    if request.method == 'POST':
        try:
            template.is_scheduled = request.POST.get('is_scheduled') == 'on'
            template.schedule_frequency = request.POST.get('frequency', '')
            template.schedule_time = request.POST.get('time', None)
            template.schedule_recipients = request.POST.get('recipients', '')
            template.save()
            
            messages.success(request, 'تم حفظ إعدادات الجدولة!')
            return redirect('reports:dashboard')
            
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'template': template,
        'frequencies': [
            ('daily', 'يومي'),
            ('weekly', 'أسبوعي'),
            ('monthly', 'شهري'),
            ('quarterly', 'ربع سنوي'),
            ('yearly', 'سنوي'),
        ]
    }
    
    return render(request, 'reports/builder/schedule.html', context)
