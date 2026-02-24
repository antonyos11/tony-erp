"""
واجهات نظام تكاليف المنتجات (Product Costing System)
محاسب التكاليف - إدارة بطاقات التكلفة والتحليلات
"""

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json

from inventory.models import Product
from .models import (
    ProductCosting, CostComponent, CostingHistory,
    CostCenter, Account
)


@login_required
def costing_dashboard(request):
    """لوحة تحكم محاسب التكاليف"""
    
    # إحصائيات عامة
    total_products = Product.objects.count()
    products_with_costing = Product.objects.filter(
        costings__status='active'
    ).distinct().count()
    
    # بطاقات التكلفة النشطة
    active_costings = ProductCosting.objects.filter(
        status='active'
    ).select_related('product').order_by('-updated_at')[:10]
    
    # منتجات بدون تكلفة أو تكلفة صفرية
    products_no_cost = Product.objects.filter(
        Q(cost=0) | Q(costings__isnull=True)
    ).distinct()[:10]
    
    # تغييرات التكلفة الأخيرة
    recent_changes = CostingHistory.objects.select_related(
        'product', 'changed_by'
    ).order_by('-changed_at')[:15]
    
    # تحليل هوامش الربح
    low_margin_products = []
    for costing in ProductCosting.objects.filter(status='active').select_related('product')[:20]:
        margin = costing.actual_profit_margin
        if margin < 10:  # هامش ربح أقل من 10%
            low_margin_products.append({
                'costing': costing,
                'margin': margin
            })
    
    context = {
        'total_products': total_products,
        'products_with_costing': products_with_costing,
        'coverage_percentage': (products_with_costing / total_products * 100) if total_products > 0 else 0,
        'active_costings': active_costings,
        'products_no_cost': products_no_cost,
        'recent_changes': recent_changes,
        'low_margin_products': low_margin_products,
    }
    
    return render(request, 'accounting/costing/dashboard.html', context)


@login_required
def costing_list(request):
    """قائمة بطاقات التكلفة"""
    
    # فلاتر
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    costings = ProductCosting.objects.select_related('product', 'created_by').all()
    
    if status:
        costings = costings.filter(status=status)
    
    if search:
        costings = costings.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # ترتيب
    sort = request.GET.get('sort', '-updated_at')
    costings = costings.order_by(sort)
    
    # ترقيم الصفحات
    paginator = Paginator(costings, 25)
    page = request.GET.get('page', 1)
    costings_page = paginator.get_page(page)
    
    context = {
        'costings': costings_page,
        'status': status,
        'search': search,
        'sort': sort,
    }
    
    return render(request, 'accounting/costing/list.html', context)


@login_required
def costing_detail(request, pk):
    """تفاصيل بطاقة تكلفة"""
    
    costing = get_object_or_404(
        ProductCosting.objects.select_related('product', 'created_by'),
        pk=pk
    )
    
    # مكونات التكلفة
    components = costing.components.select_related(
        'item', 'account', 'cost_center'
    ).order_by('sequence', 'component_type')
    
    # تجميع المكونات حسب النوع
    components_by_type = {}
    for comp in components:
        comp_type = comp.get_component_type_display()
        if comp_type not in components_by_type:
            components_by_type[comp_type] = []
        components_by_type[comp_type].append(comp)
    
    # سجل التكلفة
    history = CostingHistory.objects.filter(
        product=costing.product
    ).select_related('changed_by', 'costing').order_by('-changed_at')[:10]
    
    context = {
        'costing': costing,
        'components': components,
        'components_by_type': components_by_type,
        'history': history,
    }
    
    return render(request, 'accounting/costing/detail.html', context)


@login_required
def costing_create(request, product_id=None):
    """إنشاء بطاقة تكلفة جديدة"""
    
    product = None
    if product_id:
        product = get_object_or_404(Product, pk=product_id)
    
    if request.method == 'POST':
        try:
            # بيانات البطاقة الأساسية
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, pk=product_id)
            
            # التحقق من وجود بطاقة نشطة
            existing_active = ProductCosting.objects.filter(
                product=product,
                status='active'
            ).first()
            
            # إنشاء رقم الإصدار
            last_version = ProductCosting.objects.filter(
                product=product
            ).aggregate(max_ver=Count('version'))['max_ver'] or 0
            
            costing = ProductCosting.objects.create(
                product=product,
                version=last_version + 1,
                costing_method=request.POST.get('costing_method', 'standard'),
                status='draft',
                target_profit_margin=Decimal(request.POST.get('target_profit_margin', '0')),
                effective_from=request.POST.get('effective_from', timezone.now().date()),
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            
            messages.success(request, f'تم إنشاء بطاقة التكلفة بنجاح - إصدار {costing.version}')
            return redirect('accounting:costing_detail', pk=costing.pk)
            
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء بطاقة التكلفة: {str(e)}')
    
    # قائمة المنتجات للاختيار
    products = Product.objects.all().order_by('name')[:500]
    cost_centers = CostCenter.objects.filter(is_active=True).order_by('code')
    
    context = {
        'product': product,
        'products': products,
        'cost_centers': cost_centers,
        'today': timezone.now().date(),
    }
    
    return render(request, 'accounting/costing/create.html', context)


@login_required
def costing_edit(request, pk):
    """تعديل بطاقة تكلفة"""
    
    costing = get_object_or_404(ProductCosting, pk=pk)
    
    # منع تعديل بطاقة نشطة
    if costing.status == 'active' and request.method == 'POST':
        messages.warning(request, 'لا يمكن تعديل بطاقة تكلفة نشطة. قم بإنشاء إصدار جديد بدلاً من ذلك.')
        return redirect('accounting:costing_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            costing.costing_method = request.POST.get('costing_method', costing.costing_method)
            costing.target_profit_margin = Decimal(request.POST.get('target_profit_margin', costing.target_profit_margin))
            costing.effective_from = request.POST.get('effective_from', costing.effective_from)
            costing.notes = request.POST.get('notes', costing.notes)
            
            costing.save()
            
            messages.success(request, 'تم تحديث بطاقة التكلفة بنجاح')
            return redirect('accounting:costing_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'خطأ في تحديث بطاقة التكلفة: {str(e)}')
    
    context = {
        'costing': costing,
    }
    
    return render(request, 'accounting/costing/edit.html', context)


@login_required
def costing_activate(request, pk):
    """تفعيل بطاقة تكلفة"""
    
    costing = get_object_or_404(ProductCosting, pk=pk)
    
    if request.method == 'POST':
        try:
            # التحقق من وجود مكونات تكلفة
            if not costing.components.exists():
                messages.warning(request, 'يجب إضافة مكونات التكلفة أولاً قبل التفعيل')
                return redirect('accounting:costing_detail', pk=pk)
            
            # التحقق من أن إجمالي التكلفة ليس صفر
            if costing.total_cost == 0:
                messages.warning(request, 'لا يمكن تفعيل بطاقة تكلفة بقيمة صفر')
                return redirect('accounting:costing_detail', pk=pk)
            
            # تفعيل البطاقة (سيتم إلغاء تفعيل البطاقات الأخرى تلقائياً)
            costing.status = 'active'
            costing.save()
            
            messages.success(request, f'تم تفعيل بطاقة التكلفة وتحديث تكلفة المنتج إلى {costing.total_cost}')
            return redirect('accounting:costing_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'خطأ في تفعيل بطاقة التكلفة: {str(e)}')
    
    return redirect('accounting:costing_detail', pk=pk)


@login_required
def component_create(request, costing_id):
    """إضافة مكون تكلفة"""
    
    costing = get_object_or_404(ProductCosting, pk=costing_id)
    
    if request.method == 'POST':
        try:
            # بيانات المكون
            component_type = request.POST.get('component_type', '').strip()
            description = request.POST.get('description', '').strip()
            quantity = Decimal(request.POST.get('quantity', '1'))
            unit_cost = Decimal(request.POST.get('unit_cost', '0'))
            
            # التحقق من الحقول المطلوبة
            if not component_type:
                messages.error(request, 'يجب اختيار نوع المكون')
                raise ValueError('نوع المكون مطلوب')
            
            if not description:
                messages.error(request, 'يجب إدخال وصف المكون')
                raise ValueError('وصف المكون مطلوب')
            
            # اختياري
            item_id = request.POST.get('item_id')
            account_id = request.POST.get('account_id')
            cost_center_id = request.POST.get('cost_center_id')
            unit = request.POST.get('unit', '')
            allocation_percentage = Decimal(request.POST.get('allocation_percentage', '0'))
            notes = request.POST.get('notes', '')
            
            component = CostComponent.objects.create(
                costing=costing,
                component_type=component_type,
                description=description,
                quantity=quantity,
                unit=unit,
                unit_cost=unit_cost,
                allocation_percentage=allocation_percentage,
                notes=notes
            )
            
            if item_id:
                component.item_id = item_id
            if account_id:
                component.account_id = account_id
            if cost_center_id:
                component.cost_center_id = cost_center_id
            
            component.save()
            
            messages.success(request, 'تم إضافة مكون التكلفة بنجاح')
            
            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'component_id': component.pk,
                    'total_cost': float(component.total_cost)
                })
            
            return redirect('accounting:costing_detail', pk=costing_id)
            
        except ValueError as ve:
            # خطأ في التحقق من البيانات - إعادة عرض النموذج
            pass
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, f'خطأ في إضافة مكون التكلفة: {str(e)}')
    
    # قوائم الاختيار
    products = Product.objects.all().order_by('name')[:500]
    accounts = Account.objects.filter(is_active=True).order_by('code')[:500]
    cost_centers = CostCenter.objects.filter(is_active=True).order_by('code')
    
    context = {
        'costing': costing,
        'products': products,
        'accounts': accounts,
        'cost_centers': cost_centers,
    }
    
    return render(request, 'accounting/costing/component_form.html', context)


@login_required
def component_edit(request, pk):
    """تعديل مكون تكلفة"""
    
    component = get_object_or_404(CostComponent, pk=pk)
    
    if request.method == 'POST':
        try:
            component.description = request.POST.get('description', component.description)
            component.quantity = Decimal(request.POST.get('quantity', component.quantity))
            component.unit_cost = Decimal(request.POST.get('unit_cost', component.unit_cost))
            component.unit = request.POST.get('unit', component.unit)
            component.allocation_percentage = Decimal(request.POST.get('allocation_percentage', component.allocation_percentage))
            component.notes = request.POST.get('notes', component.notes)
            
            component.save()
            
            messages.success(request, 'تم تحديث مكون التكلفة بنجاح')
            return redirect('accounting:costing_detail', pk=component.costing.pk)
            
        except Exception as e:
            messages.error(request, f'خطأ في تحديث مكون التكلفة: {str(e)}')
    
    context = {
        'component': component,
    }
    
    return render(request, 'accounting/costing/component_edit.html', context)


@login_required
def component_delete(request, pk):
    """حذف مكون تكلفة"""
    
    component = get_object_or_404(CostComponent, pk=pk)
    costing_id = component.costing.pk
    
    if request.method == 'POST':
        try:
            component.delete()
            messages.success(request, 'تم حذف مكون التكلفة بنجاح')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
                
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, f'خطأ في حذف مكون التكلفة: {str(e)}')
    
    return redirect('accounting:costing_detail', pk=costing_id)


@login_required
def costing_history(request, product_id):
    """سجل تاريخ تكاليف منتج"""
    
    product = get_object_or_404(Product, pk=product_id)
    
    history = CostingHistory.objects.filter(
        product=product
    ).select_related('changed_by', 'costing').order_by('-changed_at')
    
    # رسم بياني للتغييرات
    chart_data = {
        'labels': [],
        'costs': [],
    }
    
    for h in history[:20]:
        chart_data['labels'].insert(0, h.changed_at.strftime('%Y-%m-%d'))
        chart_data['costs'].insert(0, float(h.new_cost))
    
    context = {
        'product': product,
        'history': history,
        'chart_data': json.dumps(chart_data),
    }
    
    return render(request, 'accounting/costing/history.html', context)


@login_required
def costing_analysis(request):
    """تحليلات التكاليف"""
    
    # المنتجات حسب نسبة المواد
    high_material_cost = ProductCosting.objects.filter(
        status='active'
    ).annotate(
        material_ratio=F('direct_material_cost') * 100 / F('total_cost')
    ).filter(
        material_ratio__gt=70
    ).select_related('product').order_by('-material_ratio')[:20]
    
    # المنتجات حسب نسبة العمالة
    high_labor_cost = ProductCosting.objects.filter(
        status='active'
    ).annotate(
        labor_ratio=F('direct_labor_cost') * 100 / F('total_cost')
    ).filter(
        labor_ratio__gt=30
    ).select_related('product').order_by('-labor_ratio')[:20]
    
    # مقارنة التكلفة بسعر البيع
    price_analysis = []
    for costing in ProductCosting.objects.filter(status='active').select_related('product')[:50]:
        price_analysis.append({
            'product': costing.product,
            'cost': costing.total_cost,
            'price': costing.product.price,
            'margin': costing.actual_profit_margin,
            'suggested_price': costing.suggested_price,
        })
    
    # ترتيب حسب الهامش
    price_analysis.sort(key=lambda x: x['margin'])
    
    # إحصائيات عامة
    stats = ProductCosting.objects.filter(status='active').aggregate(
        avg_material=Avg('direct_material_cost'),
        avg_labor=Avg('direct_labor_cost'),
        avg_overhead=Avg('overhead_cost'),
        avg_total=Avg('total_cost'),
    )
    
    context = {
        'high_material_cost': high_material_cost,
        'high_labor_cost': high_labor_cost,
        'price_analysis': price_analysis[:30],
        'stats': stats,
    }
    
    return render(request, 'accounting/costing/analysis.html', context)


@login_required
def bulk_update_costs(request):
    """تحديث جماعي للتكاليف"""
    
    if request.method == 'POST':
        try:
            # نسبة الزيادة/النقصان
            adjustment_type = request.POST.get('adjustment_type')  # 'percentage' or 'fixed'
            adjustment_value = Decimal(request.POST.get('adjustment_value', '0'))
            component_type = request.POST.get('component_type', 'all')  # 'material', 'labor', 'overhead', 'all'
            
            # المنتجات المحددة (أو الكل)
            product_ids = request.POST.getlist('product_ids')
            
            if not product_ids:
                messages.warning(request, 'يجب اختيار منتج واحد على الأقل')
                return redirect('accounting:costing_list')
            
            updated_count = 0
            
            for product_id in product_ids:
                # الحصول على البطاقة النشطة
                costing = ProductCosting.objects.filter(
                    product_id=product_id,
                    status='active'
                ).first()
                
                if not costing:
                    continue
                
                # تطبيق التعديل
                if adjustment_type == 'percentage':
                    multiplier = (Decimal('100') + adjustment_value) / Decimal('100')
                    
                    if component_type == 'material' or component_type == 'all':
                        costing.direct_material_cost *= multiplier
                    if component_type == 'labor' or component_type == 'all':
                        costing.direct_labor_cost *= multiplier
                    if component_type == 'overhead' or component_type == 'all':
                        costing.overhead_cost *= multiplier
                    if component_type == 'other' or component_type == 'all':
                        costing.other_cost *= multiplier
                        
                else:  # fixed
                    if component_type == 'material':
                        costing.direct_material_cost += adjustment_value
                    elif component_type == 'labor':
                        costing.direct_labor_cost += adjustment_value
                    elif component_type == 'overhead':
                        costing.overhead_cost += adjustment_value
                    elif component_type == 'other':
                        costing.other_cost += adjustment_value
                
                costing.save()
                updated_count += 1
            
            messages.success(request, f'تم تحديث {updated_count} بطاقة تكلفة بنجاح')
            return redirect('accounting:costing_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في التحديث الجماعي: {str(e)}')
    
    # قائمة المنتجات مع بطاقات التكلفة النشطة
    costings = ProductCosting.objects.filter(
        status='active'
    ).select_related('product').order_by('product__name')
    
    context = {
        'costings': costings,
    }
    
    return render(request, 'accounting/costing/bulk_update.html', context)


@login_required
def costing_export(request):
    """تصدير بطاقات التكلفة إلى Excel"""
    
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "بطاقات التكلفة"
    
    # العناوين
    headers = [
        'كود المنتج', 'اسم المنتج', 'الإصدار', 'الحالة',
        'تكلفة المواد', 'تكلفة العمالة', 'التكاليف الصناعية', 'أخرى',
        'إجمالي التكلفة', 'السعر الحالي', 'هامش الربح %',
        'السعر المقترح', 'تاريخ الإنشاء'
    ]
    
    ws.append(headers)
    
    # تنسيق العناوين
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    
    # البيانات
    costings = ProductCosting.objects.select_related('product').order_by('-created_at')
    
    for costing in costings:
        ws.append([
            costing.product.sku,
            costing.product.name,
            costing.version,
            costing.get_status_display(),
            float(costing.direct_material_cost),
            float(costing.direct_labor_cost),
            float(costing.overhead_cost),
            float(costing.other_cost),
            float(costing.total_cost),
            float(costing.product.price),
            float(costing.actual_profit_margin),
            float(costing.suggested_price),
            costing.created_at.strftime('%Y-%m-%d'),
        ])
    
    # تعديل عرض الأعمدة
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # الاستجابة
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="product_costings_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    
    return response
