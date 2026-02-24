# -*- coding: utf-8 -*-
"""
Views لنظام استيراد البيانات
"""
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST, require_GET
from django.core.files.storage import default_storage
from django.conf import settings
import json

from .models import ImportSession, ImportError, SystemInitialization
from .services import ExcelImportService, ExcelTemplateGenerator


@login_required
@staff_member_required
def import_dashboard(request):
    """لوحة تحكم الاستيراد"""
    init_status = SystemInitialization.get_instance()
    recent_sessions = ImportSession.objects.all()[:10]
    
    # إحصائيات
    from inventory.models import Product, Category
    from partners.models import Customer, Supplier
    from hr.models import Employee, Department
    
    stats = {
        'products': Product.objects.count(),
        'categories': Category.objects.count(),
        'customers': Customer.objects.count(),
        'suppliers': Supplier.objects.count(),
        'employees': Employee.objects.count(),
        'departments': Department.objects.count(),
    }
    
    context = {
        'init_status': init_status,
        'recent_sessions': recent_sessions,
        'stats': stats,
        'title': _('استيراد البيانات'),
        'is_new_system': not init_status.is_initialized and sum(stats.values()) == 0,
    }
    return render(request, 'data_import/dashboard.html', context)


@login_required
@staff_member_required
def initial_setup(request):
    """صفحة الإعداد الأولي للنظام الجديد"""
    init_status = SystemInitialization.get_instance()
    
    if init_status.is_initialized:
        messages.info(request, _('تم تهيئة النظام مسبقاً'))
        return redirect('data_import:dashboard')
    
    context = {
        'init_status': init_status,
        'title': _('الإعداد الأولي للنظام'),
        'modules': [
            {'key': 'categories', 'name': 'الفئات', 'icon': 'fa-tags', 'order': 1},
            {'key': 'products', 'name': 'المنتجات', 'icon': 'fa-box', 'order': 2},
            {'key': 'locations', 'name': 'المخازن', 'icon': 'fa-warehouse', 'order': 3},
            {'key': 'opening_balances', 'name': 'الأرصدة الافتتاحية', 'icon': 'fa-balance-scale', 'order': 4},
            {'key': 'customers', 'name': 'العملاء', 'icon': 'fa-users', 'order': 5},
            {'key': 'suppliers', 'name': 'الموردين', 'icon': 'fa-truck', 'order': 6},
            {'key': 'departments', 'name': 'الأقسام', 'icon': 'fa-building', 'order': 7},
            {'key': 'employees', 'name': 'الموظفين', 'icon': 'fa-user-tie', 'order': 8},
            {'key': 'accounts', 'name': 'الحسابات المحاسبية', 'icon': 'fa-calculator', 'order': 9},
        ],
    }
    return render(request, 'data_import/initial_setup.html', context)


@login_required
@staff_member_required
def import_module(request, module):
    """صفحة استيراد موديول معين"""
    module_names = {
        'categories': 'الفئات',
        'products': 'المنتجات',
        'customers': 'العملاء',
        'suppliers': 'الموردين',
        'employees': 'الموظفين',
        'departments': 'الأقسام',
        'accounts': 'الحسابات المحاسبية',
        'locations': 'المخازن',
        'opening_balances': 'الأرصدة الافتتاحية',
    }
    
    if module not in module_names:
        messages.error(request, _('موديول غير صالح'))
        return redirect('data_import:dashboard')
    
    context = {
        'module': module,
        'module_name': module_names[module],
        'title': f"استيراد {module_names[module]}",
    }
    return render(request, 'data_import/import_module.html', context)


@login_required
@staff_member_required
@require_POST
def process_import(request, module):
    """معالجة استيراد ملف Excel"""
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'لم يتم رفع ملف'})
    
    uploaded_file = request.FILES['file']
    
    # التحقق من نوع الملف
    if not uploaded_file.name.endswith(('.xlsx', '.xls')):
        return JsonResponse({'success': False, 'error': 'يجب أن يكون الملف بصيغة Excel (.xlsx أو .xls)'})
    
    # حفظ الملف
    file_path = default_storage.save(f'imports/{uploaded_file.name}', uploaded_file)
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    # إنشاء جلسة استيراد
    session = ImportSession.objects.create(
        user=request.user,
        module=module,
        file=file_path,
        original_filename=uploaded_file.name,
        status='processing',
    )
    
    try:
        service = ExcelImportService(session)
        
        # تحديد دالة الاستيراد المناسبة
        import_functions = {
            'categories': service.import_categories,
            'products': service.import_products,
            'customers': service.import_customers,
            'suppliers': service.import_suppliers,
            'employees': service.import_employees,
            'departments': service.import_departments,
            'accounts': service.import_accounts,
            'locations': service.import_locations,
            'opening_balances': service.import_opening_balances,
        }
        
        import_func = import_functions.get(module)
        if not import_func:
            session.status = 'failed'
            session.error_log = 'موديول غير مدعوم'
            session.save()
            return JsonResponse({'success': False, 'error': 'موديول غير مدعوم'})
        
        success_count, error_count = import_func(full_path)
        
        session.success_count = success_count
        session.error_count = error_count
        session.processed_rows = success_count + error_count
        session.total_rows = success_count + error_count
        session.status = 'completed' if error_count == 0 else 'partial'
        session.completed_at = timezone.now()
        session.save()
        
        # تحديث حالة التهيئة
        init_status = SystemInitialization.get_instance()
        field_map = {
            'categories': 'categories_imported',
            'products': 'products_imported',
            'customers': 'customers_imported',
            'suppliers': 'suppliers_imported',
            'employees': 'employees_imported',
            'departments': 'departments_imported',
            'accounts': 'accounts_imported',
            'locations': 'locations_imported',
            'opening_balances': 'opening_balances_imported',
        }
        if module in field_map:
            setattr(init_status, field_map[module], True)
            init_status.save()
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'success_count': success_count,
            'error_count': error_count,
            'errors': [{'row': e['row_number'], 'message': e['error_message']} for e in service.errors[:10]],
        })
        
    except Exception as e:
        session.status = 'failed'
        session.error_log = str(e)
        session.save()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_member_required
def download_template(request, module):
    """تحميل قالب Excel لموديول معين"""
    try:
        wb = ExcelTemplateGenerator.generate_template(module)
        
        # إنشاء response
        from django.http import HttpResponse
        import io
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        template_name = ExcelTemplateGenerator.TEMPLATES[module]['name']
        
        response = HttpResponse(
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{template_name}"'
        
        wb.close()
        return response
        
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('data_import:dashboard')


@login_required
@staff_member_required
def download_all_templates(request):
    """تحميل جميع القوالب في ملف zip"""
    zip_buffer = ExcelTemplateGenerator.get_all_templates_zip()
    
    response = HttpResponse(
        zip_buffer.read(),
        content_type='application/zip'
    )
    response['Content-Disposition'] = 'attachment; filename="قوالب_الاستيراد.zip"'
    
    return response


@login_required
@staff_member_required
def session_detail(request, session_id):
    """تفاصيل جلسة استيراد"""
    session = get_object_or_404(ImportSession, pk=session_id)
    errors = session.errors.all()[:50]
    
    context = {
        'session': session,
        'errors': errors,
        'title': f"جلسة استيراد #{session.id}",
    }
    return render(request, 'data_import/session_detail.html', context)


@login_required
@staff_member_required
@require_POST
def mark_initialized(request):
    """تأكيد اكتمال التهيئة"""
    init_status = SystemInitialization.get_instance()
    init_status.is_initialized = True
    init_status.initialized_at = timezone.now()
    init_status.initialized_by = request.user
    init_status.save()
    
    messages.success(request, _('تم تأكيد اكتمال تهيئة النظام بنجاح'))
    return redirect('data_import:dashboard')


@login_required
@staff_member_required
def check_system_status(request):
    """التحقق من حالة النظام (API)"""
    init_status = SystemInitialization.get_instance()
    
    from inventory.models import Product, Category
    from partners.models import Customer, Supplier
    from hr.models import Employee, Department
    
    data = {
        'is_initialized': init_status.is_initialized,
        'is_new_system': not init_status.is_initialized,
        'stats': {
            'products': Product.objects.count(),
            'categories': Category.objects.count(),
            'customers': Customer.objects.count(),
            'suppliers': Supplier.objects.count(),
            'employees': Employee.objects.count(),
            'departments': Department.objects.count(),
        },
        'import_status': {
            'categories': init_status.categories_imported,
            'products': init_status.products_imported,
            'customers': init_status.customers_imported,
            'suppliers': init_status.suppliers_imported,
            'employees': init_status.employees_imported,
            'departments': init_status.departments_imported,
            'accounts': init_status.accounts_imported,
            'locations': init_status.locations_imported,
            'opening_balances': init_status.opening_balances_imported,
        },
    }
    
    return JsonResponse(data)
