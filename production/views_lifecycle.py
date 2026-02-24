"""
واجهات متقدمة لإدارة دورة حياة الإنتاج
تتضمن التكامل الكامل بين المخزون والمحاسبة
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import json

from production.models import ProductionOrder
from production.services import (
    ProductionLifecycleService,
    ProductionInventoryService,
    ProductionAccountingService
)


@login_required
def start_production_order_view(request, order_id):
    """
    بدء أمر الإنتاج - إنشاء صرف المواد والقيود المحاسبية تلقائياً
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    
    if request.method == 'POST':
        try:
            success, msg, details = ProductionLifecycleService.start_production_order(
                order,
                request.user
            )
            
            if success:
                messages.success(request, msg)
                # إضافة تفاصيل إضافية
                if details.get('issue_id'):
                    messages.info(request, f"تم إنشاء سند صرف رقم {details['issue_id']}")
                if details.get('journal_entry_id'):
                    messages.info(request, f"تم إنشاء قيد محاسبي رقم {details['journal_entry_id']}")
                
                return redirect('production:order_detail', order_id=order.id)
            else:
                messages.error(request, msg)
                
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
    
    # عرض معاينة قبل البدء
    all_available, materials_status = ProductionInventoryService.check_material_availability(order)
    
    context = {
        'order': order,
        'materials_available': all_available,
        'materials_status': materials_status,
        'can_start': order.status in ['draft', 'confirmed'] and all_available,
    }
    
    return render(request, 'production/start_order_confirm.html', context)


@login_required
def record_production_output_view(request, order_id):
    """
    تسجيل إنتاج منتجات تامة مع القيود المحاسبية
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    
    if request.method == 'POST':
        try:
            quantity = Decimal(request.POST.get('quantity', 0))
            generate_barcodes = request.POST.get('generate_barcodes') == 'on'
            size_text = request.POST.get('size_text', '')
            
            success, msg, details = ProductionLifecycleService.record_production_output(
                order,
                quantity,
                request.user,
                generate_barcodes=generate_barcodes,
                size_text=size_text
            )
            
            if success:
                messages.success(request, msg)
                
                # عرض معلومات الباركودات إن وجدت
                if details.get('barcodes'):
                    barcodes_count = len(details['barcodes'])
                    messages.info(request, f"تم توليد {barcodes_count} باركود")
                
                return redirect('production:order_detail', order_id=order.id)
            else:
                messages.error(request, msg)
                
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
    
    context = {
        'order': order,
        'can_record': order.status in ['in_progress', 'quality_check'],
        'remaining_quantity': order.remaining_quantity,
    }
    
    return render(request, 'production/record_output.html', context)


@login_required
def complete_production_order_view(request, order_id):
    """
    إكمال أمر الإنتاج - إنشاء جميع القيود النهائية
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    
    if request.method == 'POST':
        try:
            success, msg, analysis = ProductionLifecycleService.complete_production_order(order)
            
            if success:
                messages.success(request, msg)
                
                # عرض ملخص التحليل
                if analysis.get('variance_analysis'):
                    total_variance = analysis['variance_analysis'].get('total', {})
                    variance_pct = total_variance.get('variance_pct', 0)
                    
                    if variance_pct > 5:
                        messages.warning(request, f"تجاوز في التكلفة: {variance_pct:.2f}%")
                    elif variance_pct < -5:
                        messages.success(request, f"توفير في التكلفة: {abs(variance_pct):.2f}%")
                
                return redirect('production:order_detail', order_id=order.id)
            else:
                messages.error(request, msg)
                
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
    
    # عرض معاينة قبل الإكمال
    summary = ProductionLifecycleService.get_order_status_summary(order)
    
    context = {
        'order': order,
        'summary': summary,
        'can_complete': order.status in ['in_progress', 'quality_check'],
    }
    
    return render(request, 'production/complete_order_confirm.html', context)


@login_required
def production_order_status_api(request, order_id):
    """
    API للحصول على حالة أمر الإنتاج بالتفصيل
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    summary = ProductionLifecycleService.get_order_status_summary(order)
    
    return JsonResponse(summary, safe=False)


@login_required
def check_materials_availability_api(request, order_id):
    """
    API للتحقق من توفر المواد
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    all_available, materials_status = ProductionInventoryService.check_material_availability(order)
    
    return JsonResponse({
        'all_available': all_available,
        'materials': materials_status
    })


@login_required
def production_cost_variance_api(request, order_id):
    """
    API لتحليل انحرافات التكلفة
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    variance = ProductionAccountingService.calculate_cost_variance(order)
    
    return JsonResponse(variance)


@login_required
def generate_barcodes_view(request, order_id):
    """
    توليد باركودات للمنتجات التامة
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 0))
            size_text = request.POST.get('size_text', '')
            
            success, msg, units = ProductionInventoryService.generate_barcodes_for_finished_goods(
                order,
                quantity,
                size_text
            )
            
            if success:
                messages.success(request, msg)
                # حفظ الباركودات في الجلسة للطباعة
                request.session['barcode_units'] = [
                    {
                        'serial': u.unit_serial,
                        'barcode': u.barcode,
                        'size': u.size_text,
                        'product': u.product.name,
                        'manufacture_date': str(u.manufacture_date),
                        'expiry_date': str(u.expiry_date) if u.expiry_date else None,
                    }
                    for u in units
                ]
                return redirect('production:print_barcodes', order_id=order.id)
            else:
                messages.error(request, msg)
                
        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")
    
    context = {
        'order': order,
        'produced_quantity': int(order.produced_quantity),
    }
    
    return render(request, 'production/generate_barcodes.html', context)


@login_required
def print_barcodes_view(request, order_id):
    """
    طباعة الباركودات
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    
    # الحصول على الباركودات من الجلسة أو قاعدة البيانات
    barcode_units = request.session.get('barcode_units', [])
    
    if not barcode_units:
        # جلب آخر باركودات من قاعدة البيانات
        from production.models import FinishedGoodUnit
        units = FinishedGoodUnit.objects.filter(
            production_order=order
        ).order_by('-created_at')[:50]
        
        barcode_units = [
            {
                'serial': u.unit_serial,
                'barcode': u.barcode,
                'size': u.size_text,
                'product': u.product.name,
                'manufacture_date': str(u.manufacture_date),
                'expiry_date': str(u.expiry_date) if u.expiry_date else None,
            }
            for u in units
        ]
    
    context = {
        'order': order,
        'barcode_units': barcode_units,
    }
    
    return render(request, 'production/print_barcodes.html', context)


@login_required
def production_integrated_dashboard(request):
    """
    لوحة تحكم متكاملة للإنتاج تعرض:
    - أوامر الإنتاج النشطة مع حالة المواد
    - التكاليف والانحرافات
    - الإنتاجية والجودة
    """
    from django.db.models import Q, Count, Sum
    
    # أوامر الإنتاج النشطة - QuerySet للإحصائيات
    active_orders_qs = ProductionOrder.objects.filter(
        status__in=['confirmed', 'in_progress', 'quality_check']
    ).select_related('product', 'supervisor').order_by('planned_end_date')
    
    # أول 20 أمر للعرض
    active_orders = list(active_orders_qs[:20])
    
    # تحضير بيانات إضافية لكل أمر
    orders_with_status = []
    for order in active_orders:
        all_available, materials = ProductionInventoryService.check_material_availability(order)
        variance = ProductionAccountingService.calculate_cost_variance(order)
        
        orders_with_status.append({
            'order': order,
            'materials_available': all_available,
            'materials_shortage_count': sum(1 for m in materials if not m.get('is_available', True)),
            'cost_variance_pct': variance.get('total', {}).get('variance_pct', 0),
        })
    
    # إحصائيات عامة - استخدام QuerySet الأصلي بدون slice
    today = timezone.now().date()
    stats = {
        'total_active': active_orders_qs.count(),
        'behind_schedule': active_orders_qs.filter(
            planned_end_date__lt=today
        ).count(),
        'on_track': active_orders_qs.filter(
            planned_end_date__gte=today,
            status='in_progress'
        ).count(),
        'awaiting_materials': sum(
            1 for o in orders_with_status if not o['materials_available']
        ),
    }
    
    context = {
        'orders_with_status': orders_with_status,
        'stats': stats,
    }
    
    return render(request, 'production/integrated_dashboard.html', context)


@login_required
@transaction.atomic
def bulk_start_orders_view(request):
    """
    بدء عدة أوامر إنتاج دفعة واحدة
    """
    if request.method == 'POST':
        order_ids = request.POST.getlist('order_ids')
        
        results = {
            'success': [],
            'failed': [],
        }
        
        for order_id in order_ids:
            try:
                order = ProductionOrder.objects.get(id=order_id)
                success, msg, details = ProductionLifecycleService.start_production_order(
                    order,
                    request.user
                )
                
                if success:
                    results['success'].append({
                        'order_number': order.number,
                        'message': msg
                    })
                else:
                    results['failed'].append({
                        'order_number': order.number,
                        'message': msg
                    })
            except Exception as e:
                results['failed'].append({
                    'order_number': f"Order {order_id}",
                    'message': str(e)
                })
        
        messages.success(request, f"تم بدء {len(results['success'])} أمر بنجاح")
        if results['failed']:
            messages.warning(request, f"فشل بدء {len(results['failed'])} أمر")
        
        return JsonResponse(results)
    
    # عرض الأوامر القابلة للبدء
    pending_orders = ProductionOrder.objects.filter(
        status__in=['draft', 'confirmed']
    ).select_related('product')[:50]
    
    # فحص توفر المواد لكل أمر
    orders_status = []
    for order in pending_orders:
        all_available, _ = ProductionInventoryService.check_material_availability(order)
        orders_status.append({
            'order': order,
            'materials_available': all_available,
        })
    
    context = {
        'orders_status': orders_status,
    }
    
    return render(request, 'production/bulk_start_orders.html', context)
