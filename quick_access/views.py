"""
Quick Access Views - Unified Dashboard and Quick Actions
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from datetime import datetime, timedelta
import json

from .models import UserPreference, QuickAction, FrequentlyUsedReport, ScheduledReport, BulkActionHistory
from sales.models import Invoice
from purchases.models import PurchaseBill
from inventory.models import Product, Stock
from accounting.models import JournalEntry


@login_required
def quick_dashboard(request):
    """لوحة التحكم الموحدة للوصول السريع"""
    
    # الحصول على تفضيلات المستخدم أو إنشاؤها
    prefs, created = UserPreference.objects.get_or_create(user=request.user)
    
    # الإجراءات السريعة المتاحة
    quick_actions = QuickAction.objects.filter(is_active=True)
    
    # تصفية حسب الصلاحيات
    if not request.user.is_superuser:
        accessible_actions = []
        for action in quick_actions:
            if not action.permission_required or request.user.has_perm(action.permission_required):
                accessible_actions.append(action)
        quick_actions = accessible_actions
    
    # تجميع الإجراءات حسب الفئة
    actions_by_category = {}
    for action in quick_actions:
        if action.category not in actions_by_category:
            actions_by_category[action.category] = []
        actions_by_category[action.category].append(action)
    
    # الإحصائيات السريعة
    today = timezone.now().date()
    stats = {
        'sales_today': Invoice.objects.filter(date=today).count(),
        'purchases_today': PurchaseBill.objects.filter(date=today).count(),
        'low_stock': Stock.objects.filter(quantity__lte=F('product__reorder_point')).count(),
        'pending_approvals': 0,  # يمكن إضافة منطق الموافقات
    }
    
    # التقارير المتكررة
    frequent_reports = FrequentlyUsedReport.objects.filter(user=request.user)[:5]
    
    # التقارير المجدولة القادمة
    scheduled_reports = ScheduledReport.objects.filter(
        user=request.user, 
        is_active=True,
        next_run__gte=timezone.now()
    )[:5]
    
    context = {
        'prefs': prefs,
        'actions_by_category': actions_by_category,
        'stats': stats,
        'frequent_reports': frequent_reports,
        'scheduled_reports': scheduled_reports,
        'page_title': 'لوحة الوصول السريع',
    }
    
    return render(request, 'quick_access/dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def track_action_usage(request, action_id):
    """تتبع استخدام الإجراءات السريعة"""
    action = get_object_or_404(QuickAction, id=action_id)
    action.increment_usage()
    return JsonResponse({'success': True, 'usage_count': action.usage_count})


@login_required
@require_http_methods(["POST"])
def track_report_access(request):
    """تتبع الوصول للتقارير"""
    data = json.loads(request.body)
    report_name = data.get('report_name')
    report_url = data.get('report_url')
    report_type = data.get('report_type', 'general')
    parameters = data.get('parameters', {})
    
    report, created = FrequentlyUsedReport.objects.get_or_create(
        user=request.user,
        report_name=report_name,
        defaults={
            'report_url': report_url,
            'report_type': report_type,
            'parameters': parameters
        }
    )
    
    if not created:
        report.access_count += 1
        report.parameters = parameters
        report.save()
    
    return JsonResponse({'success': True, 'access_count': report.access_count})


@login_required
def update_preferences(request):
    """تحديث تفضيلات المستخدم"""
    if request.method == 'POST':
        prefs, created = UserPreference.objects.get_or_create(user=request.user)
        
        data = json.loads(request.body)
        
        if 'default_view' in data:
            prefs.default_view = data['default_view']
        if 'theme' in data:
            prefs.theme = data['theme']
        if 'sidebar_collapsed' in data:
            prefs.sidebar_collapsed = data['sidebar_collapsed']
        if 'notifications_enabled' in data:
            prefs.notifications_enabled = data['notifications_enabled']
        if 'favorite_shortcuts' in data:
            prefs.favorite_shortcuts = data['favorite_shortcuts']
        if 'dashboard_widgets' in data:
            prefs.dashboard_widgets = data['dashboard_widgets']
        
        prefs.save()
        
        return JsonResponse({'success': True, 'message': 'تم حفظ التفضيلات بنجاح'})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def global_search(request):
    """بحث شامل عبر النظام"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'message': 'الرجاء إدخال حرفين على الأقل'})
    
    results = []
    
    # البحث في المنتجات
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(sku__icontains=query) |
        Q(barcode__icontains=query)
    )[:10]
    
    for product in products:
        results.append({
            'type': 'product',
            'title': product.name,
            'subtitle': f'كود: {product.sku}',
            'url': f'/inventory/products/{product.id}/',
            'icon': 'bi-box',
            'color': '#3b82f6'
        })
    
    # البحث في الفواتير
    invoices = Invoice.objects.filter(
        Q(number__icontains=query) |
        Q(customer__name__icontains=query)
    )[:5]
    
    for invoice in invoices:
        results.append({
            'type': 'invoice',
            'title': f'فاتورة {invoice.number}',
            'subtitle': f'العميل: {invoice.customer.name if invoice.customer else "غير محدد"}',
            'url': f'/sales/invoices/{invoice.id}/',
            'icon': 'bi-receipt',
            'color': '#10b981'
        })
    
    # البحث في العملاء (CRM)
    try:
        from crm.models import Customer
        customers = Customer.objects.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )[:5]
        
        for customer in customers:
            results.append({
                'type': 'customer',
                'title': customer.name,
                'subtitle': f'{customer.email or ""} {customer.phone or ""}',
                'url': f'/crm/customers/{customer.id}/',
                'icon': 'bi-person',
                'color': '#8b5cf6'
            })
    except:
        pass
    
    # البحث في الموظفين
    try:
        from hr.models import Employee
        employees = Employee.objects.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(employee_id__icontains=query)
        )[:5]
        
        for emp in employees:
            results.append({
                'type': 'employee',
                'title': emp.user.get_full_name() or emp.user.username,
                'subtitle': f'رقم الموظف: {emp.employee_id}',
                'url': f'/hr/employees/{emp.id}/',
                'icon': 'bi-person-badge',
                'color': '#f59e0b'
            })
    except:
        pass
    
    return JsonResponse({
        'results': results,
        'total': len(results),
        'query': query
    })


@login_required
def keyboard_shortcuts_guide(request):
    """دليل اختصارات لوحة المفاتيح"""
    shortcuts = QuickAction.objects.filter(
        is_active=True,
        keyboard_shortcut__isnull=False
    ).exclude(keyboard_shortcut='').order_by('category')
    
    # تجميع حسب الفئة
    shortcuts_by_category = {}
    for shortcut in shortcuts:
        if shortcut.category not in shortcuts_by_category:
            shortcuts_by_category[shortcut.category] = []
        shortcuts_by_category[shortcut.category].append(shortcut)
    
    # اختصارات عامة إضافية
    general_shortcuts = [
        {'keys': 'Ctrl + K', 'description': 'البحث السريع', 'icon': 'bi-search'},
        {'keys': 'Ctrl + /', 'description': 'عرض الاختصارات', 'icon': 'bi-question-circle'},
        {'keys': 'Ctrl + B', 'description': 'إظهار/إخفاء القائمة الجانبية', 'icon': 'bi-layout-sidebar'},
        {'keys': 'Esc', 'description': 'إغلاق النافذة المنبثقة', 'icon': 'bi-x-circle'},
        {'keys': 'Alt + H', 'description': 'الصفحة الرئيسية', 'icon': 'bi-house'},
    ]
    
    context = {
        'shortcuts_by_category': shortcuts_by_category,
        'general_shortcuts': general_shortcuts,
        'page_title': 'دليل اختصارات لوحة المفاتيح'
    }
    
    return render(request, 'quick_access/shortcuts_guide.html', context)


@login_required
def bulk_actions_interface(request):
    """واجهة العمليات الجماعية"""
    
    # العمليات الجماعية المتاحة
    available_operations = [
        {
            'id': 'bulk_update_prices',
            'name': 'تحديث الأسعار',
            'model': 'product',
            'icon': 'bi-tag',
            'color': '#3b82f6',
            'description': 'تحديث أسعار مجموعة من المنتجات'
        },
        {
            'id': 'bulk_update_stock',
            'name': 'تحديث المخزون',
            'model': 'stock',
            'icon': 'bi-boxes',
            'color': '#10b981',
            'description': 'تحديث كميات المخزون لمنتجات متعددة'
        },
        {
            'id': 'bulk_send_emails',
            'name': 'إرسال بريد إلكتروني',
            'model': 'customer',
            'icon': 'bi-envelope',
            'color': '#8b5cf6',
            'description': 'إرسال رسائل بريد إلكتروني لعملاء متعددين'
        },
        {
            'id': 'bulk_export_data',
            'name': 'تصدير البيانات',
            'model': 'any',
            'icon': 'bi-download',
            'color': '#f59e0b',
            'description': 'تصدير بيانات متعددة إلى Excel أو CSV'
        },
        {
            'id': 'bulk_delete',
            'name': 'حذف جماعي',
            'model': 'any',
            'icon': 'bi-trash',
            'color': '#ef4444',
            'description': 'حذف سجلات متعددة (بحذر!)'
        },
    ]
    
    # سجل العمليات السابقة
    recent_operations = BulkActionHistory.objects.filter(
        user=request.user
    ).order_by('-timestamp')[:10]
    
    context = {
        'available_operations': available_operations,
        'recent_operations': recent_operations,
        'page_title': 'العمليات الجماعية'
    }
    
    return render(request, 'quick_access/bulk_actions.html', context)


@login_required
@require_http_methods(["POST"])
def execute_bulk_action(request):
    """تنفيذ عملية جماعية"""
    import time
    from django.core.mail import send_mail
    from django.conf import settings
    from decimal import Decimal

    start_time = time.time()

    # Handle both JSON and form data
    if request.content_type == 'application/json':
        data = json.loads(request.body)
    else:
        data = {
            'action_type': request.POST.get('action_type'),
            'target_ids': request.POST.get('target_ids', '').split(',') if request.POST.get('target_ids') else [],
            'parameters': json.loads(request.POST.get('parameters', '{}'))
        }

    action_type = data.get('action_type')
    target_ids = data.get('target_ids', [])
    # Clean target_ids - remove empty strings and convert to integers
    target_ids = [int(id.strip()) for id in target_ids if id and str(id).strip().isdigit()]
    parameters = data.get('parameters', {})

    success_count = 0
    error_count = 0
    errors_log = []

    try:
        if action_type == 'bulk_update_prices':
            # تحديث الأسعار
            price_change = Decimal(str(parameters.get('price_change', 0)))
            change_type = parameters.get('change_type', 'fixed')  # fixed, percentage

            # إذا لم يتم تحديد IDs، حدث كل المنتجات
            if target_ids:
                products = Product.objects.filter(id__in=target_ids)
            else:
                products = Product.objects.all()

            for product in products:
                try:
                    if change_type == 'percentage':
                        product.price = product.price * (1 + price_change / 100)
                    else:
                        product.price = product.price + price_change
                    product.save()
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors_log.append(f"المنتج {product.sku}: {str(e)}")

        elif action_type == 'bulk_update_stock':
            # تحديث المخزون
            quantity_change = int(parameters.get('quantity_change', 0))
            location_id = parameters.get('location_id')
            stock_change_type = parameters.get('stock_change_type', 'add')

            if not location_id:
                return JsonResponse({'success': False, 'error': 'يجب اختيار المستودع'})

            # Get or create stock records for products
            for product_id in target_ids:
                try:
                    stock, created = Stock.objects.get_or_create(
                        product_id=product_id,
                        location_id=location_id,
                        defaults={'quantity': 0}
                    )

                    if stock_change_type == 'add':
                        stock.quantity += quantity_change
                    elif stock_change_type == 'subtract':
                        stock.quantity = max(0, stock.quantity - quantity_change)
                    else:  # set
                        stock.quantity = quantity_change

                    stock.save()
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors_log.append(f"المنتج {product_id}: {str(e)}")

        elif action_type == 'bulk_send_emails':
            # إرسال بريد إلكتروني جماعي
            from crm.models import Customer

            subject = parameters.get('subject', '')
            body = parameters.get('body', '')

            if not subject or not body:
                return JsonResponse({'success': False, 'error': 'يجب إدخال الموضوع والمحتوى'})

            # Get customers
            if target_ids:
                customers = Customer.objects.filter(id__in=target_ids, email__isnull=False).exclude(email='')
            else:
                customers = Customer.objects.filter(email__isnull=False).exclude(email='')

            for customer in customers:
                try:
                    send_mail(
                        subject=subject,
                        message=body,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                        recipient_list=[customer.email],
                        fail_silently=False
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors_log.append(f"{customer.email}: {str(e)}")

        elif action_type == 'bulk_export_data':
            # تصدير البيانات
            return handle_bulk_export(request, parameters, target_ids)

        elif action_type == 'bulk_delete':
            # حذف جماعي
            delete_model = parameters.get('delete_model', '')
            confirm = parameters.get('confirm', '')

            if confirm != 'حذف':
                return JsonResponse({'success': False, 'error': 'يجب تأكيد الحذف بكتابة "حذف"'})

            if not target_ids:
                return JsonResponse({'success': False, 'error': 'يجب تحديد العناصر المراد حذفها'})

            if delete_model == 'products':
                for product_id in target_ids:
                    try:
                        product = Product.objects.get(id=product_id)
                        product.delete()
                        success_count += 1
                    except Product.DoesNotExist:
                        error_count += 1
                        errors_log.append(f"المنتج {product_id}: غير موجود")
                    except Exception as e:
                        error_count += 1
                        errors_log.append(f"المنتج {product_id}: {str(e)}")

            elif delete_model == 'customers':
                from crm.models import Customer
                for customer_id in target_ids:
                    try:
                        customer = Customer.objects.get(id=customer_id)
                        customer.delete()
                        success_count += 1
                    except Customer.DoesNotExist:
                        error_count += 1
                        errors_log.append(f"العميل {customer_id}: غير موجود")
                    except Exception as e:
                        error_count += 1
                        errors_log.append(f"العميل {customer_id}: {str(e)}")
            else:
                return JsonResponse({'success': False, 'error': 'نوع البيانات غير مدعوم'})

        else:
            return JsonResponse({'success': False, 'error': f'نوع العملية غير معروف: {action_type}'})

        # سجل العملية
        duration = time.time() - start_time
        BulkActionHistory.objects.create(
            user=request.user,
            action_type=action_type,
            model_name=parameters.get('model_name', 'unknown'),
            affected_count=len(target_ids) if target_ids else success_count,
            success_count=success_count,
            error_count=error_count,
            parameters=parameters,
            errors_log=errors_log,
            duration_seconds=duration
        )

        return JsonResponse({
            'success': True,
            'message': f'تم معالجة {success_count} عنصر بنجاح',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors_log[:10],  # أول 10 أخطاء فقط
            'duration': round(duration, 2)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def handle_bulk_export(request, parameters, target_ids):
    """معالجة تصدير البيانات"""
    import csv
    from io import BytesIO

    export_model = parameters.get('export_model', 'products')
    export_format = parameters.get('export_format', 'excel')

    # Prepare data based on model
    if export_model == 'products':
        if target_ids:
            queryset = Product.objects.filter(id__in=target_ids)
        else:
            queryset = Product.objects.all()

        headers = ['ID', 'الكود', 'الاسم', 'سعر البيع', 'سعر الشراء', 'الحالة']
        rows = []
        for item in queryset:
            rows.append([
                item.id,
                item.sku,
                item.name,
                str(item.price),
                str(item.cost_price) if hasattr(item, 'cost_price') else '',
                'نشط' if item.is_active else 'غير نشط'
            ])

    elif export_model == 'customers':
        from crm.models import Customer
        if target_ids:
            queryset = Customer.objects.filter(id__in=target_ids)
        else:
            queryset = Customer.objects.all()

        headers = ['ID', 'الكود', 'الاسم', 'الهاتف', 'البريد', 'المدينة', 'الحالة']
        rows = []
        for item in queryset:
            rows.append([
                item.id,
                item.customer_code,
                f"{item.first_name} {item.last_name}",
                item.phone,
                item.email,
                item.city,
                item.status
            ])

    elif export_model == 'invoices':
        if target_ids:
            queryset = Invoice.objects.filter(id__in=target_ids)
        else:
            queryset = Invoice.objects.all()[:1000]  # Limit to 1000

        headers = ['ID', 'رقم الفاتورة', 'التاريخ', 'العميل', 'الإجمالي', 'الحالة']
        rows = []
        for item in queryset:
            rows.append([
                item.id,
                item.number,
                str(item.date),
                item.customer.name if item.customer else '',
                str(item.total) if hasattr(item, 'total') else '',
                item.status if hasattr(item, 'status') else ''
            ])

    elif export_model == 'stocks':
        if target_ids:
            queryset = Stock.objects.filter(product_id__in=target_ids)
        else:
            queryset = Stock.objects.all()

        headers = ['ID', 'المنتج', 'المستودع', 'الكمية']
        rows = []
        for item in queryset:
            rows.append([
                item.id,
                item.product.name if item.product else '',
                item.location.name if item.location else '',
                str(item.quantity)
            ])
    else:
        return JsonResponse({'success': False, 'error': 'نوع البيانات غير مدعوم'})

    # Generate file
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{export_model}_export.csv"'

        # Add BOM for Excel UTF-8 compatibility
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)

        return response

    else:  # Excel
        try:
            import openpyxl
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = export_model

            # Headers
            for col, header in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=header)
                ws.cell(row=1, column=col).font = openpyxl.styles.Font(bold=True)

            # Data
            for row_idx, row_data in enumerate(rows, 2):
                for col_idx, value in enumerate(row_data, 1):
                    ws.cell(row=row_idx, column=col_idx, value=value)

            # Auto-adjust column widths
            for col in range(1, len(headers) + 1):
                ws.column_dimensions[get_column_letter(col)].width = 15

            # Save to response
            output = BytesIO()
            wb.save(output)
            output.seek(0)

            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{export_model}_export.xlsx"'
            return response

        except ImportError:
            # Fallback to CSV if openpyxl not installed
            return JsonResponse({'success': False, 'error': 'مكتبة Excel غير مثبتة، استخدم CSV بدلاً منها'})


@login_required
def get_locations_json(request):
    """جلب قائمة المستودعات بصيغة JSON"""
    from inventory.models import Location

    locations = Location.objects.filter(is_active=True).order_by('name')
    data = {
        'success': True,
        'locations': [
            {'id': loc.id, 'name': f"{loc.code} - {loc.name}", 'type': loc.type}
            for loc in locations
        ]
    }
    return JsonResponse(data)


@login_required
def scheduled_reports_manager(request):
    """إدارة التقارير المجدولة"""
    user_reports = ScheduledReport.objects.filter(user=request.user)

    context = {
        'scheduled_reports': user_reports,
        'page_title': 'التقارير المجدولة'
    }

    return render(request, 'quick_access/scheduled_reports.html', context)
