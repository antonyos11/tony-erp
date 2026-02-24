# -*- coding: utf-8 -*-
"""
API views للميزات الإضافية في نقطة البيع
- الطلبات المعلقة
- المنتجات المفضلة
- الأكثر مبيعاً
- اختصارات لوحة المفاتيح
"""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import json

from .models_hold import HeldOrder, FavoriteProduct, get_top_selling_products, get_recent_products
from inventory.models import Product


@login_required
@require_POST
def hold_order(request):
    """
    حفظ طلب معلق
    """
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        customer_name = data.get('customer_name', '')
        customer_phone = data.get('customer_phone', '')
        note = data.get('note', '')
        total = Decimal(str(data.get('total', 0)))
        location_id = data.get('location_id')
        
        if not items:
            return JsonResponse({
                'success': False, 
                'error': _('لا توجد منتجات للحفظ')
            }, status=400)
        
        held = HeldOrder.objects.create(
            user=request.user,
            customer_name=customer_name,
            customer_phone=customer_phone,
            note=note,
            items_json=items,
            total=total,
            location_id=location_id
        )
        
        return JsonResponse({
            'success': True,
            'hold_id': held.id,
            'message': _('تم حفظ الطلب المعلق بنجاح')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_GET
def list_held_orders(request):
    """
    عرض قائمة الطلبات المعلقة
    """
    held_orders = HeldOrder.objects.filter(user=request.user).order_by('-created_at')[:20]
    
    data = [{
        'id': h.id,
        'customer_name': h.customer_name or _('عميل نقدي'),
        'customer_phone': h.customer_phone,
        'note': h.note,
        'items_count': h.items_count,
        'total': float(h.total),
        'created_at': h.created_at.strftime('%Y-%m-%d %H:%M'),
    } for h in held_orders]
    
    return JsonResponse({'success': True, 'orders': data})


@login_required
@require_GET
def get_held_order(request, hold_id):
    """
    جلب تفاصيل طلب معلق
    """
    held = get_object_or_404(HeldOrder, pk=hold_id, user=request.user)
    
    return JsonResponse({
        'success': True,
        'order': {
            'id': held.id,
            'customer_name': held.customer_name,
            'customer_phone': held.customer_phone,
            'note': held.note,
            'items': held.items_json,
            'total': float(held.total),
            'created_at': held.created_at.strftime('%Y-%m-%d %H:%M'),
        }
    })


@login_required
@require_POST
def restore_held_order(request, hold_id):
    """
    استعادة طلب معلق وحذفه من المعلقات
    """
    held = get_object_or_404(HeldOrder, pk=hold_id, user=request.user)
    
    data = {
        'success': True,
        'items': held.items_json,
        'customer_name': held.customer_name,
        'customer_phone': held.customer_phone,
        'note': held.note,
    }
    
    # حذف الطلب المعلق بعد استعادته
    held.delete()
    
    return JsonResponse(data)


@login_required
@require_POST
def delete_held_order(request, hold_id):
    """
    حذف طلب معلق
    """
    held = get_object_or_404(HeldOrder, pk=hold_id, user=request.user)
    held.delete()
    
    return JsonResponse({
        'success': True,
        'message': _('تم حذف الطلب المعلق')
    })


# =========== المنتجات المفضلة ===========

@login_required
@require_POST
def toggle_favorite(request):
    """
    إضافة/إزالة منتج من المفضلة
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        if not product_id:
            return JsonResponse({'success': False, 'error': _('منتج غير صالح')}, status=400)
        
        product = get_object_or_404(Product, pk=product_id)
        
        fav, created = FavoriteProduct.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            # كان موجوداً، نحذفه
            fav.delete()
            return JsonResponse({
                'success': True,
                'is_favorite': False,
                'message': _('تمت الإزالة من المفضلة')
            })
        
        return JsonResponse({
            'success': True,
            'is_favorite': True,
            'message': _('تمت الإضافة للمفضلة')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_GET
def list_favorites(request):
    """
    عرض قائمة المنتجات المفضلة
    """
    favorites = FavoriteProduct.objects.filter(
        user=request.user
    ).select_related('product')[:50]
    
    data = [{
        'id': f.product.id,
        'name': f.product.name,
        'price': float(f.product.sale_price or f.product.price or 0),
        'sku': f.product.sku,
        'barcode': f.product.barcode,
        'image': f.product.image.url if f.product.image else None,
        'stock': f.product.current_stock or 0,
    } for f in favorites]
    
    return JsonResponse({'success': True, 'products': data})


# =========== الأكثر مبيعاً ===========

@login_required
@require_GET
def top_selling(request):
    """
    المنتجات الأكثر مبيعاً
    """
    days = int(request.GET.get('days', 7))
    limit = int(request.GET.get('limit', 10))
    
    top_products = get_top_selling_products(
        user=request.user if request.GET.get('my_sales') else None,
        days=days,
        limit=limit
    )
    
    # جلب تفاصيل المنتجات
    product_ids = [p['product_id'] for p in top_products]
    products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
    
    data = []
    for item in top_products:
        prod = products.get(item['product_id'])
        if prod:
            data.append({
                'id': prod.id,
                'name': prod.name,
                'price': float(prod.sale_price or prod.price or 0),
                'image': prod.image.url if prod.image else None,
                'total_sold': item['total_qty'],
                'times_sold': item['times_sold'],
            })
    
    return JsonResponse({'success': True, 'products': data})


@login_required
@require_GET
def recent_products(request):
    """
    آخر المنتجات المباعة
    """
    limit = int(request.GET.get('limit', 10))
    product_ids = list(get_recent_products(request.user, limit))
    
    products = Product.objects.filter(id__in=product_ids)
    
    # ترتيب حسب الترتيب الأصلي
    products_dict = {p.id: p for p in products}
    data = []
    for pid in product_ids:
        prod = products_dict.get(pid)
        if prod:
            data.append({
                'id': prod.id,
                'name': prod.name,
                'price': float(prod.sale_price or prod.price or 0),
                'image': prod.image.url if prod.image else None,
                'stock': prod.current_stock or 0,
            })
    
    return JsonResponse({'success': True, 'products': data})


# =========== تغيير السعر والخصم السريع ===========

@login_required
@require_POST
def quick_price_change(request, order_id, line_id):
    """
    تغيير سعر منتج في السلة
    """
    from .models import POSOrder, POSOrderLine
    
    try:
        data = json.loads(request.body)
        new_price = Decimal(str(data.get('price', 0)))
        
        if new_price < 0:
            return JsonResponse({'success': False, 'error': _('سعر غير صالح')}, status=400)
        
        order = get_object_or_404(POSOrder, pk=order_id)
        line = get_object_or_404(POSOrderLine, pk=line_id, order=order)
        
        if order.status != 'draft':
            return JsonResponse({
                'success': False, 
                'error': _('لا يمكن تعديل طلب مدفوع')
            }, status=400)
        
        line.price = new_price
        line.save(update_fields=['price'])
        order.recalc_total()
        
        return JsonResponse({
            'success': True,
            'line_total': float(line.total),
            'order_total': float(order.total),
            'message': _('تم تحديث السعر')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def quick_line_discount(request, order_id, line_id):
    """
    خصم على منتج محدد في السلة
    """
    from .models import POSOrder, POSOrderLine
    
    try:
        data = json.loads(request.body)
        discount_percent = Decimal(str(data.get('discount_percent', 0)))
        discount_amount = Decimal(str(data.get('discount_amount', 0)))
        
        order = get_object_or_404(POSOrder, pk=order_id)
        line = get_object_or_404(POSOrderLine, pk=line_id, order=order)
        
        if order.status != 'draft':
            return JsonResponse({
                'success': False,
                'error': _('لا يمكن تعديل طلب مدفوع')
            }, status=400)
        
        if discount_percent > 0:
            # خصم بالنسبة المئوية
            discount = line.price * (discount_percent / 100)
            line.price = line.price - discount
        elif discount_amount > 0:
            # خصم بالقيمة
            line.price = max(Decimal('0'), line.price - discount_amount)
        
        line.save(update_fields=['price'])
        order.recalc_total()
        
        return JsonResponse({
            'success': True,
            'new_price': float(line.price),
            'line_total': float(line.total),
            'order_total': float(order.total),
            'message': _('تم تطبيق الخصم')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =========== تحديث الكمية ===========

@login_required
@require_POST
def update_line_quantity(request, order_id, line_id):
    """
    تحديث كمية منتج في السلة
    """
    from .models import POSOrder, POSOrderLine
    
    try:
        data = json.loads(request.body)
        new_qty = int(data.get('quantity', 1))
        
        if new_qty < 1:
            return JsonResponse({
                'success': False, 
                'error': _('الكمية يجب أن تكون 1 على الأقل')
            }, status=400)
        
        order = get_object_or_404(POSOrder, pk=order_id)
        line = get_object_or_404(POSOrderLine, pk=line_id, order=order)
        
        if order.status != 'draft':
            return JsonResponse({
                'success': False,
                'error': _('لا يمكن تعديل طلب مدفوع')
            }, status=400)
        
        line.quantity = new_qty
        line.save(update_fields=['quantity'])
        order.recalc_total()
        
        return JsonResponse({
            'success': True,
            'quantity': line.quantity,
            'line_total': float(line.total),
            'order_total': float(order.total),
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =========== أزرار المبالغ السريعة ===========

@login_required
@require_GET
def quick_amounts(request):
    """
    جلب أزرار المبالغ السريعة للدفع
    """
    from .models_hold import QuickPriceButton
    
    buttons = QuickPriceButton.objects.filter(is_active=True).order_by('order', 'amount')
    
    if not buttons.exists():
        # إنشاء الأزرار الافتراضية
        defaults = [10, 20, 50, 100, 200, 500]
        for i, amt in enumerate(defaults):
            QuickPriceButton.objects.create(amount=amt, order=i)
        buttons = QuickPriceButton.objects.filter(is_active=True).order_by('order', 'amount')
    
    return JsonResponse({
        'success': True,
        'buttons': [{
            'id': b.id,
            'amount': float(b.amount),
            'label': b.label or f'{b.amount:,.0f}'
        } for b in buttons]
    })


# =========== اختصارات لوحة المفاتيح ===========

@login_required
@require_GET
def keyboard_shortcuts(request):
    """
    جلب إعدادات اختصارات لوحة المفاتيح
    """
    shortcuts = {
        'search_focus': {'key': 'F2', 'description': _('التركيز على البحث')},
        'new_order': {'key': 'F3', 'description': _('طلب جديد')},
        'pay': {'key': 'F8', 'description': _('الدفع')},
        'hold': {'key': 'F9', 'description': _('تعليق الطلب')},
        'recall': {'key': 'F10', 'description': _('استعادة طلب معلق')},
        'clear': {'key': 'Escape', 'description': _('إفراغ السلة')},
        'increase_qty': {'key': '+', 'description': _('زيادة الكمية')},
        'decrease_qty': {'key': '-', 'description': _('نقص الكمية')},
        'delete_item': {'key': 'Delete', 'description': _('حذف المنتج')},
        'category_1': {'key': 'F1', 'description': _('الفئة الأولى')},
        'category_2': {'key': 'F4', 'description': _('الفئة الثانية')},
        'category_3': {'key': 'F5', 'description': _('الفئة الثالثة')},
        'category_4': {'key': 'F6', 'description': _('الفئة الرابعة')},
        'category_5': {'key': 'F7', 'description': _('الفئة الخامسة')},
        'print_receipt': {'key': 'Ctrl+P', 'description': _('طباعة الإيصال')},
        'discount': {'key': 'Ctrl+D', 'description': _('تطبيق خصم')},
    }
    
    return JsonResponse({'success': True, 'shortcuts': shortcuts})


@login_required
@require_POST
def complete_order(request):
    """
    إتمام طلب جديد والدفع
    """
    try:
        data = json.loads(request.body)
        cart = data.get('cart', [])
        total = Decimal(str(data.get('total', 0)))
        paid_amount = Decimal(str(data.get('paid_amount', 0)))
        payment_method = data.get('payment_method', 'cash')
        notes = data.get('notes', '')
        order_id = data.get('order_id')
        
        if not cart or len(cart) == 0:
            return JsonResponse({
                'success': False,
                'error': _('السلة فارغة')
            }, status=400)
        
        from .models import POSOrder, POSOrderLine, POSSession, POSPayment
        from inventory.models import Product, Location
        from payments.models import PaymentMethod as PMModel
        from showrooms.mixins import get_active_showroom_id
        
        # الحصول على الجلسة النشطة
        sid = get_active_showroom_id(request)
        active_session = POSSession.objects.filter(user=request.user, is_open=True).first()
        
        if not active_session:
            return JsonResponse({
                'success': False,
                'error': _('لا توجد جلسة نشطة. يرجى فتح جلسة أولاً')
            }, status=400)
        
        # إنشاء أو تحديث الطلب
        with transaction.atomic():
            if order_id and order_id != 'null':
                order = POSOrder.objects.get(id=order_id)
                order.lines.all().delete()  # مسح البنود القديمة
            else:
                order = POSOrder.objects.create(
                    session=active_session,
                    location=active_session.location,
                    status='draft'
                )
            
            # إضافة المنتجات
            for item in cart:
                product = Product.objects.get(id=item['id'])
                POSOrderLine.objects.create(
                    order=order,
                    product=product,
                    quantity=item['qty'],
                    price=Decimal(str(item['price']))
                )
            
            # إعادة حساب الإجمالي
            order.recalc_total()
            
            # الحصول على طريقة الدفع
            payment_method_obj = None
            if payment_method:
                payment_method_obj = PMModel.objects.filter(
                    name__icontains=payment_method
                ).first()
                if not payment_method_obj:
                    # إنشاء طريقة دفع إذا لم تكن موجودة
                    if payment_method == 'cash':
                        payment_method_obj = PMModel.objects.get_or_create(
                            name='نقدي',
                            defaults={'is_active': True}
                        )[0]
                    elif payment_method == 'card':
                        payment_method_obj = PMModel.objects.get_or_create(
                            name='بطاقة',
                            defaults={'is_active': True}
                        )[0]
            
            # إتمام الدفع
            order.finalize_payment(paid_amount, payment_method_obj)
            
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_number': order.number,
            'message': _('تم إتمام الطلب بنجاح')
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': _('منتج غير موجود')
        }, status=404)
    except POSOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': _('الطلب غير موجود')
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =========== الطباعة الحرارية المباشرة ===========

@login_required
@require_POST
def print_thermal_receipt(request, order_id):
    """
    طباعة الإيصال على الطابعة الحرارية مباشرة
    """
    from .models import POSOrder
    
    try:
        order = get_object_or_404(POSOrder, pk=order_id)
        lines = order.lines.select_related('product').all()
        
        # محاولة الطباعة عبر thermal_printer
        try:
            from .thermal_printer import print_receipt_direct
            result = print_receipt_direct(order, lines)
            if result.get('success'):
                return JsonResponse({
                    'success': True,
                    'message': _('تم إرسال الإيصال للطابعة الحرارية'),
                    'printer': result.get('printer_name', 'default')
                })
        except ImportError:
            pass
        except Exception as e:
            print(f"Thermal print error: {e}")
        
        # إذا فشلت الطباعة المباشرة، نرجع رابط الطباعة
        return JsonResponse({
            'success': True,
            'print_url': f'/pos/order/{order_id}/receipt/?thermal=1&auto=1',
            'message': _('يرجى استخدام رابط الطباعة')
        })
        
    except POSOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': _('الطلب غير موجود')
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def create_installment_order(request):
    """
    إنشاء طلب جديد بالتقسيط
    """
    try:
        data = json.loads(request.body)
        cart = data.get('cart', [])
        total = Decimal(str(data.get('total', 0)))
        customer_id = data.get('customer_id')
        customer_name = data.get('customer_name')
        customer_phone = data.get('customer_phone')
        customer_national_id = data.get('customer_national_id', '')
        
        # بيانات التقسيط
        down_payment = Decimal(str(data.get('down_payment', 0)))
        number_of_installments = int(data.get('number_of_installments', 6))
        interest_rate = Decimal(str(data.get('interest_rate', 0)))
        start_date_str = data.get('start_date')
        
        if not cart or len(cart) == 0:
            return JsonResponse({
                'success': False,
                'error': _('السلة فارغة')
            }, status=400)
        
        if not customer_id and not customer_name:
            return JsonResponse({
                'success': False,
                'error': _('يجب اختيار عميل أو إدخال بيانات العميل')
            }, status=400)
        
        from .models import POSOrder, POSOrderLine, POSSession
        from inventory.models import Product
        from partners.models import Customer
        from installments.models import InstallmentContract, Installment
        from showrooms.mixins import get_active_showroom_id
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        # الحصول على الجلسة النشطة
        active_session = POSSession.objects.filter(user=request.user, is_open=True).first()
        
        if not active_session:
            return JsonResponse({
                'success': False,
                'error': _('لا توجد جلسة نشطة. يرجى فتح جلسة أولاً')
            }, status=400)
        
        with transaction.atomic():
            # الحصول أو إنشاء العميل
            if customer_id:
                customer = Customer.objects.get(id=customer_id)
            else:
                customer, created = Customer.objects.get_or_create(
                    name=customer_name,
                    defaults={
                        'phone': customer_phone,
                        'national_id': customer_national_id,
                        'customer_type': 'individual'
                    }
                )
            
            # إنشاء الطلب
            order = POSOrder.objects.create(
                session=active_session,
                location=active_session.location,
                customer=customer,
                status='draft'
            )
            
            # إضافة المنتجات
            for item in cart:
                product = Product.objects.get(id=item['id'])
                POSOrderLine.objects.create(
                    order=order,
                    product=product,
                    quantity=item['qty'],
                    price=Decimal(str(item['price']))
                )
            
            # إعادة حساب الإجمالي
            order.recalc_total()
            total_amount = order.total
            
            # حساب مبلغ التمويل
            financed_amount = total_amount - down_payment
            
            # حساب القسط الشهري
            if interest_rate > 0:
                monthly_rate = interest_rate / Decimal('100') / Decimal('12')
                if monthly_rate > 0:
                    monthly_payment = (financed_amount * monthly_rate * 
                                     (Decimal('1') + monthly_rate) ** number_of_installments) / \
                                    ((Decimal('1') + monthly_rate) ** number_of_installments - Decimal('1'))
                else:
                    monthly_payment = financed_amount / Decimal(str(number_of_installments))
            else:
                monthly_payment = financed_amount / Decimal(str(number_of_installments))
            
            monthly_payment = monthly_payment.quantize(Decimal('0.01'))
            
            # إنشاء عقد التقسيط
            contract = InstallmentContract.objects.create(
                customer=customer,
                order=order,
                total_amount=total_amount,
                down_payment=down_payment,
                financed_amount=financed_amount,
                number_of_installments=number_of_installments,
                installment_amount=monthly_payment,
                interest_rate=interest_rate,
                status='active',
                created_by=request.user
            )
            
            # إنشاء الأقساط
            if start_date_str:
                current_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                current_date = datetime.now().date()
            
            for i in range(1, number_of_installments + 1):
                Installment.objects.create(
                    contract=contract,
                    installment_number=i,
                    due_date=current_date,
                    amount=monthly_payment,
                    status='pending'
                )
                current_date = current_date + relativedelta(months=1)
            
            # تسجيل الدفعة المقدمة إذا كانت موجودة
            if down_payment > 0:
                from payments.models import PaymentMethod
                cash_method = PaymentMethod.objects.filter(name__icontains='نقد').first()
                order.add_payment(down_payment, cash_method)
            
            # إتمام الطلب إذا تم دفع الدفعة المقدمة بالكامل
            if down_payment >= total_amount:
                order.status = 'paid'
                order.save()
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'contract_id': contract.id,
            'contract_number': contract.contract_number,
            'message': _('تم إنشاء عقد التقسيط بنجاح')
        })
        
    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': _('العميل غير موجود')
        }, status=404)
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': _('منتج غير موجود')
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

