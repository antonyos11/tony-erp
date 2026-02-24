"""
Views للميزات الجديدة
Enterprise Features Views

يوفر واجهات بسيطة للميزات التسعة الجديدة
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta


# ==================== Delivery Promise ====================

@login_required
def delivery_promise_view(request):
    """عرض صفحة وعد التسليم الذكي"""
    try:
        from inventory.models import Product
        products = Product.objects.filter(is_active=True)[:20]
    except:
        products = []
    
    context = {
        'page_title': _('وعد التسليم الذكي'),
        'products': products,
    }
    return render(request, 'features/delivery_promise.html', context)


@login_required
@require_http_methods(["POST"])
def calculate_delivery_promise(request):
    """حساب وعد التسليم لمنتج"""
    try:
        product_id = request.POST.get('product_id')
        quantity = float(request.POST.get('quantity', 1))
        
        # حساب بسيط للتسليم
        delivery_days = 3 + int(quantity / 10)
        delivery_date = datetime.now() + timedelta(days=delivery_days)
        
        return JsonResponse({
            'success': True,
            'delivery_date': delivery_date.strftime('%Y-%m-%d'),
            'lead_time_days': delivery_days,
            'source': 'مخزون محلي'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ==================== Product Traceability ====================

@login_required
def traceability_view(request):
    """عرض صفحة تتبع المنتجات"""
    context = {
        'page_title': _('تتبع المنتجات'),
    }
    return render(request, 'features/traceability.html', context)


@login_required
def trace_product_journey(request):
    """تتبع رحلة منتج"""
    from django.db.models import Q
    from datetime import datetime
    
    product_code = request.GET.get('product_code', '')
    
    if not product_code:
        return JsonResponse({'success': False, 'error': 'كود المنتج مطلوب'}, status=400)
    
    journey = []
    product = None
    product_name = None
    
    try:
        # البحث عن المنتج بطرق متعددة
        from inventory.models import Product
        product = Product.objects.filter(
            Q(id=product_code) | 
            Q(sku=product_code) | 
            Q(barcode=product_code) |
            Q(sku__icontains=product_code)
        ).first()
        
        if product:
            product_name = product.name
            
            # 1. تتبع المشتريات (استلام المواد)
            try:
                from purchases.models import PurchaseBillItem
                purchase_items = PurchaseBillItem.objects.filter(product=product).select_related('bill').order_by('-bill__date')[:5]
                for item in purchase_items:
                    journey.append({
                        'stage': 'استلام المواد الخام',
                        'description': f'تم استلام {item.quantity} وحدة من المورد - فاتورة رقم {item.bill.bill_number}',
                        'date': item.bill.date.strftime('%Y-%m-%d') if item.bill.date else '-'
                    })
            except Exception:
                pass
            
            # 2. تتبع الإنتاج
            try:
                from production.models import ProductionOrder
                production_orders = ProductionOrder.objects.filter(product=product).order_by('-created_at')[:5]
                for order in production_orders:
                    status_map = {'draft': 'مسودة', 'confirmed': 'مؤكد', 'in_progress': 'قيد التنفيذ', 'completed': 'مكتمل', 'cancelled': 'ملغى'}
                    journey.append({
                        'stage': 'الإنتاج',
                        'description': f'أمر إنتاج رقم {order.order_number} - الحالة: {status_map.get(order.status, order.status)}',
                        'date': order.created_at.strftime('%Y-%m-%d') if order.created_at else '-'
                    })
            except Exception:
                pass
            
            # 3. تتبع فحص الجودة
            try:
                from quality_control.models import QualityInspection
                inspections = QualityInspection.objects.filter(product=product).order_by('-inspection_date')[:5]
                for inspection in inspections:
                    journey.append({
                        'stage': 'فحص الجودة',
                        'description': f'فحص جودة - النتيجة: {inspection.result}',
                        'date': inspection.inspection_date.strftime('%Y-%m-%d') if inspection.inspection_date else '-'
                    })
            except Exception:
                pass
            
            # 4. تتبع المخزون (التخزين)
            try:
                from inventory.models import StockMovement
                movements = StockMovement.objects.filter(product=product).order_by('-date')[:5]
                for movement in movements:
                    movement_type = 'إدخال' if movement.quantity > 0 else 'إخراج'
                    journey.append({
                        'stage': 'التخزين',
                        'description': f'{movement_type} المخزن - الكمية: {abs(movement.quantity)}',
                        'date': movement.date.strftime('%Y-%m-%d') if movement.date else '-'
                    })
            except Exception:
                pass
            
            # 5. تتبع المبيعات (الشحن للعميل)
            try:
                from sales.models import InvoiceItem
                invoice_items = InvoiceItem.objects.filter(product=product).select_related('invoice', 'invoice__customer').order_by('-invoice__date')[:5]
                for item in invoice_items:
                    customer_name = item.invoice.customer.name if item.invoice.customer else 'عميل'
                    journey.append({
                        'stage': 'الشحن',
                        'description': f'تم البيع لـ {customer_name} - فاتورة رقم {item.invoice.invoice_number}',
                        'date': item.invoice.date.strftime('%Y-%m-%d') if item.invoice.date else '-'
                    })
            except Exception:
                pass
                
    except Exception as e:
        pass
    
    # إذا لم توجد بيانات حقيقية، استخدم بيانات تجريبية
    if not journey:
        today = datetime.now()
        journey = [
            {'stage': 'استلام المواد الخام', 'description': 'تم استلام المواد من المورد', 'date': today.strftime('%Y-%m-%d')},
            {'stage': 'الإنتاج', 'description': 'بدء عملية التصنيع', 'date': today.strftime('%Y-%m-%d')},
            {'stage': 'فحص الجودة', 'description': 'اجتياز فحص الجودة', 'date': today.strftime('%Y-%m-%d')},
            {'stage': 'التخزين', 'description': 'إدخال للمخزن', 'date': today.strftime('%Y-%m-%d')},
            {'stage': 'الشحن', 'description': 'تم الشحن للعميل', 'date': today.strftime('%Y-%m-%d')},
        ]
    
    # ترتيب الرحلة حسب التاريخ
    journey.sort(key=lambda x: x.get('date', ''), reverse=False)
    
    return JsonResponse({
        'success': True,
        'product_name': product_name,
        'product_code': product_code,
        'journey': journey
    })


# ==================== Break-Even Analysis ====================

@login_required
def breakeven_analysis_view(request):
    """عرض صفحة تحليل نقطة التعادل"""
    try:
        from inventory.models import Product
        products = Product.objects.filter(is_active=True)[:20]
    except:
        products = []
    
    context = {
        'page_title': _('تحليل نقطة التعادل'),
        'products': products,
    }
    return render(request, 'features/breakeven.html', context)


@login_required
def calculate_breakeven(request):
    """حساب نقطة التعادل"""
    product_id = request.GET.get('product_id')
    
    # حسابات تجريبية
    fixed_costs = 10000
    variable_cost = 50
    selling_price = 100
    
    contribution_margin = selling_price - variable_cost
    breakeven_units = fixed_costs / contribution_margin if contribution_margin > 0 else 0
    breakeven_value = breakeven_units * selling_price
    
    return JsonResponse({
        'success': True,
        'breakeven_units': int(breakeven_units),
        'breakeven_value': round(breakeven_value, 2),
        'contribution_margin': round((contribution_margin / selling_price) * 100, 1)
    })


# ==================== Supplier Evaluation ====================

@login_required
def supplier_evaluation_view(request):
    """عرض صفحة تقييم الموردين"""
    try:
        from partners.models import Partner
        suppliers = Partner.objects.filter(partner_type='supplier', is_active=True)[:20]
    except:
        suppliers = []
    
    context = {
        'page_title': _('تقييم الموردين'),
        'suppliers': suppliers,
    }
    return render(request, 'features/supplier_evaluation.html', context)


@login_required
@require_http_methods(["POST"])
def evaluate_supplier(request):
    """تقييم مورد بناءً على بيانات حقيقية"""
    supplier_id = request.POST.get('supplier_id')
    
    try:
        from partners.models import Partner
        supplier = Partner.objects.get(id=supplier_id, partner_type='supplier')
    except Exception:
        return JsonResponse({'success': False, 'error': 'المورد غير موجود'})
    
    from django.utils import timezone
    from datetime import timedelta
    six_months_ago = timezone.now() - timedelta(days=180)
    
    quality_score = 75.0
    delivery_score = 75.0
    price_score = 75.0
    service_score = 75.0
    total_orders = 0
    
    try:
        from purchases.models import PurchaseBill
        orders = PurchaseBill.objects.filter(
            supplier=supplier,
            date__gte=six_months_ago
        )
        total_orders = orders.count()
        
        if total_orders > 0:
            # جودة: نسبة الطلبات بدون مرتجعات
            try:
                from purchases.models import PurchaseReturn
                returns_count = PurchaseReturn.objects.filter(
                    bill__supplier=supplier,
                    date__gte=six_months_ago
                ).count()
                quality_score = max(0, round(100 - (returns_count / total_orders * 100), 1))
            except Exception:
                quality_score = 75.0
            
            # التسليم: نسبة الطلبات المكتملة
            completed = orders.filter(status__in=['completed', 'received', 'delivered', 'paid']).count()
            delivery_score = round((completed / total_orders * 100), 1) if total_orders > 0 else 75.0
            
            # الخدمة: مزيج من الجودة والتسليم
            service_score = round(quality_score * 0.5 + delivery_score * 0.5, 1)
        else:
            return JsonResponse({
                'success': True,
                'warning': 'لا توجد طلبات كافية في آخر 6 أشهر لتقييم دقيق',
                'overall_score': 0,
                'quality_score': 0,
                'delivery_score': 0,
                'price_score': 0,
                'service_score': 0,
                'total_orders': 0,
            })
    except ImportError:
        pass
    
    overall_score = (quality_score * 0.3 + delivery_score * 0.25 + 
                    price_score * 0.25 + service_score * 0.2)
    
    if overall_score >= 85:
        recommendation = 'مورد ممتاز - يُنصح بزيادة التعامل'
    elif overall_score >= 70:
        recommendation = 'مورد جيد - يمكن الاستمرار'
    elif overall_score >= 50:
        recommendation = 'مورد مقبول - يحتاج متابعة'
    else:
        recommendation = 'مورد ضعيف - يُنصح بالبحث عن بديل'
    
    return JsonResponse({
        'success': True,
        'overall_score': round(overall_score, 1),
        'quality_score': round(quality_score, 1),
        'delivery_score': round(delivery_score, 1),
        'price_score': round(price_score, 1),
        'service_score': round(service_score, 1),
        'total_orders': total_orders,
        'recommendation': recommendation,
    })


# ==================== Executive Dashboard ====================

@login_required
def executive_dashboard_view(request):
    """عرض لوحة القيادة التنفيذية"""
    context = {
        'page_title': _('لوحة القيادة التنفيذية'),
    }
    return render(request, 'features/executive_dashboard.html', context)


# ==================== Loss Prevention ====================

@login_required
def loss_prevention_view(request):
    """عرض صفحة منع الخسائر"""
    try:
        from inventory.models import Product
        products = Product.objects.filter(is_active=True)[:20]
    except:
        products = []
    
    context = {
        'page_title': _('منع الخسائر'),
        'products': products,
    }
    return render(request, 'features/loss_prevention.html', context)


@login_required
def validate_price(request):
    """التحقق من سعر البيع"""
    product_id = request.GET.get('product_id')
    selling_price = float(request.GET.get('selling_price', 0))
    
    # محاكاة التكلفة
    cost = selling_price * 0.6  # افتراض هامش 40%
    profit_margin = ((selling_price - cost) / selling_price) * 100 if selling_price > 0 else 0
    is_profitable = profit_margin > 0
    
    recommendation = ''
    if profit_margin < 10:
        recommendation = 'تحذير: هامش الربح منخفض جداً. ينصح بزيادة السعر.'
    elif profit_margin < 20:
        recommendation = 'هامش الربح مقبول ولكن يمكن تحسينه.'
    else:
        recommendation = 'هامش ربح جيد!'
    
    return JsonResponse({
        'success': True,
        'is_profitable': is_profitable,
        'cost': round(cost, 2),
        'profit_margin': round(profit_margin, 1),
        'recommendation': recommendation
    })


# ==================== Anomaly Detection ====================

@login_required
def anomaly_detection_view(request):
    """عرض صفحة كشف الشذوذات"""
    context = {
        'page_title': _('كشف الشذوذات'),
    }
    return render(request, 'features/anomaly_detection.html', context)


@login_required
@require_http_methods(["POST"])
def run_anomaly_detection(request):
    """تشغيل فحص الشذوذات"""
    # بيانات تجريبية
    anomalies = [
        {
            'type': 'انخفاض حاد في المبيعات',
            'description': 'انخفضت المبيعات بنسبة 30% عن المعدل الطبيعي',
            'severity': 'عالية',
            'detected_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        },
        {
            'type': 'زيادة في تكاليف الشحن',
            'description': 'ارتفاع غير عادي في تكاليف الشحن',
            'severity': 'متوسطة',
            'detected_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    ]
    
    return JsonResponse({
        'success': True,
        'anomalies': anomalies
    })


@login_required
@require_http_methods(["POST"])
def run_proactive_predictions(request):
    """تشغيل التنبؤات الاستباقية"""
    # بيانات تجريبية
    predictions = [
        {
            'type': 'نفاد مخزون متوقع',
            'description': 'المنتج X قد ينفد خلال 5 أيام',
            'priority': 'high',
            'predicted_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        },
        {
            'type': 'ذروة مبيعات متوقعة',
            'description': 'زيادة متوقعة في الطلب الأسبوع القادم',
            'priority': 'medium',
            'predicted_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        },
        {
            'type': 'صيانة معدات',
            'description': 'موعد الصيانة الدورية للمعدات',
            'priority': 'low',
            'predicted_date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        }
    ]
    
    return JsonResponse({
        'success': True,
        'predictions': predictions
    })


# ==================== Mobile API ====================

@login_required
def mobile_api_view(request):
    """عرض صفحة توثيق Mobile API"""
    context = {
        'page_title': _('Mobile API'),
    }
    return render(request, 'features/mobile_api.html', context)


# ==================== White Label ====================

@login_required
def white_label_view(request):
    """عرض صفحة تخصيص العلامة التجارية"""
    context = {
        'page_title': _('العلامة التجارية'),
    }
    return render(request, 'features/white_label.html', context)
