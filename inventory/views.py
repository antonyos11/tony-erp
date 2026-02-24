# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportOperatorIssue=false, reportArgumentType=false, reportIndexIssue=false
from django.shortcuts import render, redirect, get_object_or_404
from inventory.forms import ProductForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, F, Count, DecimalField, Value
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import Coalesce, Cast
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.template import TemplateSyntaxError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext as _t
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator

import json
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, cast
from django.db.models.query import QuerySet

from django.apps import apps

from inventory.models import (
    Product,
    Location,
    Stock,
    StockTransfer,
    StockTransferItem,
    Receiving,
    ReceivingItem,
    Issue,
    IssueItem,
    StockCount,
    StockCountItem,
    StockBatch,
    Requisition,
    RequisitionItem,
    Category,
)

from inventory.barcode_utils import (
    barcode_generator,
    get_product_qr_code,
    validate_barcode,
    search_products_by_barcode,
    resolve_label_dimensions,
)

from core.models import AuditLog
from partners.models import Supplier
from inventory.models import SupplierProductPrice


# ========== API: بيانات المورد ==========
@login_required
def api_supplier_products(request, supplier_id):
    """API: جلب المنتجات المتاحة من مورد معين مع أسعارها"""
    try:
        supplier = Supplier.objects.get(pk=supplier_id)
        
        # جلب أسعار المنتجات من هذا المورد
        supplier_prices = SupplierProductPrice.objects.filter(
            supplier=supplier,
            is_active=True,
            product__isnull=False
        ).select_related('product').order_by('product__name')
        
        products = []
        for sp in supplier_prices:
            products.append({
                'id': sp.product.id,
                'sku': sp.product.sku,
                'name': sp.product.name,
                'price': float(sp.cost),
                'unit': sp.purchase_unit,
                'conversion_factor': float(sp.conversion_to_base),
                'min_order_qty': float(sp.min_order_qty) if sp.min_order_qty else None,
                'lead_time_days': sp.lead_time_days,
            })
        
        return JsonResponse({
            'success': True,
            'supplier': {
                'id': supplier.id,
                'name': supplier.name,
                'supply_type': supplier.supply_type,
            },
            'products': products
        })
    except Supplier.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'المورد غير موجود'}, status=404)


@login_required
def api_supplier_materials(request, supplier_id):
    """API: جلب المواد الخام التي يوردها المورد مع أسعارها ووحداتها - للاختيار الذكي"""
    try:
        supplier = Supplier.objects.get(pk=supplier_id)
        
        # جلب جميع المواد الخام من هذا المورد مع أسعارها
        supplier_prices = SupplierProductPrice.objects.filter(
            supplier=supplier,
            is_active=True,
            product__product_type='raw_material'
        ).select_related('product', 'product__category').order_by('-created_at')
        
        materials = []
        for sp in supplier_prices:
            product = sp.product
            materials.append({
                'id': sp.id,
                'product_id': product.id,
                'sku': product.sku,
                'name': product.name,
                'category': product.category.name if product.category else '',
                'raw_material_type': product.raw_material_type or '',
                'price': float(sp.cost),
                'purchase_unit': sp.purchase_unit,
                'usage_unit': product.usage_uom or 'unit',
                'conversion_factor': float(sp.conversion_to_base),
                'min_order_qty': float(sp.min_order_qty) if sp.min_order_qty else None,
                'lead_time_days': sp.lead_time_days,
                'notes': sp.notes or '',
            })
        
        # معلومات المورد
        supplier_info = {
            'id': supplier.id,
            'name': supplier.name,
            'supply_type': supplier.supply_type,
            'raw_material': getattr(supplier, 'raw_material', ''),
            'phone': supplier.phone or '',
            'default_unit': get_default_unit_for_supply_type(supplier.supply_type),
        }
        
        return JsonResponse({
            'success': True,
            'supplier': supplier_info,
            'materials': materials,
            'count': len(materials)
        })
    except Supplier.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'المورد غير موجود'}, status=404)


@login_required
@login_required
def api_supplier_price_info(request, supplier_id):
    """API: جلب معلومات السعر والوحدة من المورد"""
    try:
        supplier = Supplier.objects.get(pk=supplier_id)
        
        # معلومات المورد الأساسية
        data = {
            'success': True,
            'supplier': {
                'id': supplier.id,
                'name': supplier.name,
                'supply_type': supplier.supply_type,
                'raw_material': getattr(supplier, 'raw_material', ''),
                'phone': supplier.phone,
                'email': supplier.email,
            },
            # السعر الافتراضي بناءً على نوع التوريد
            'default_unit': get_default_unit_for_supply_type(supplier.supply_type),
            'suggested_price': None,
        }
        
        # جلب جميع المواد من هذا المورد
        supplier_prices = SupplierProductPrice.objects.filter(
            supplier=supplier,
            is_active=True
        ).select_related('product').order_by('-created_at')
        
        materials = []
        for sp in supplier_prices:
            materials.append({
                'id': sp.id,
                'product_id': sp.product.id if sp.product else None,
                'name': sp.product.name if sp.product else sp.material_name,
                'price': float(sp.cost),
                'unit': sp.purchase_unit,
                'conversion_factor': float(sp.conversion_to_base),
            })
        
        data['materials'] = materials
        
        # لو في منتجات سابقة من هذا المورد، نجيب آخر سعر
        last_price = supplier_prices.first()
        
        if last_price:
            data['last_product'] = {
                'name': last_price.product.name if last_price.product else last_price.material_name,
                'price': float(last_price.cost),
                'unit': last_price.purchase_unit,
                'conversion_factor': float(last_price.conversion_to_base),
            }
        
        return JsonResponse(data)
    except Supplier.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'المورد غير موجود'}, status=404)


def get_default_unit_for_supply_type(supply_type):
    """إرجاع الوحدة الافتراضية حسب نوع التوريد"""
    defaults = {
        'raw_materials': 'kg',
        'packaging': 'unit',
        'services': 'unit',
        'spare_parts': 'unit',
        'other': 'unit',
    }
    return defaults.get(supply_type, 'unit')


@login_required
def inventory_dashboard(request):
    """Inventory overview dashboard"""
    products_qs = Product.objects.all()
    total_products = products_qs.count()
    total_locations = Location.objects.count()

    # Low stock products
    low_stock_products = Product.objects.annotate(
        total_qty=Coalesce(
            Sum(Cast(F('stocks__quantity'), output_field=DecimalField(max_digits=18, decimal_places=2)),
                output_field=DecimalField(max_digits=18, decimal_places=2)),
            Value(Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2)),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
    ).filter(total_qty__lt=F('min_stock'))

    # Stock value calculation
    stock_value = Product.objects.annotate(
        total_qty=Coalesce(
            Sum(Cast(F('stocks__quantity'), output_field=DecimalField(max_digits=18, decimal_places=2)),
                output_field=DecimalField(max_digits=18, decimal_places=2)),
            Value(Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2)),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
    ).aggregate(
        total_value=Sum(
            ExpressionWrapper(
                F('total_qty') * Cast(F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2)),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            ),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
    )['total_value'] or Decimal('0')

    # إحصائيات المخازن حسب النوع
    warehouse_stats = {
        'finished': Location.objects.filter(type='finished', is_active=True).count(),
        'wip': Location.objects.filter(type='wip', is_active=True).count(),
        'raw': Location.objects.filter(type='raw', is_active=True).count(),
        'spare': Location.objects.filter(type='spare', is_active=True).count(),
        'store': Location.objects.filter(type='store', is_active=True).count(),
        'other': Location.objects.filter(type='other', is_active=True).count(),
    }

    context = {
        'total_products': total_products,
        'total_locations': total_locations,
        'low_stock_count': low_stock_products.count(),
        'low_stock_products': low_stock_products[:10],  # Show top 10
        'stock_value': stock_value,
        'warehouse_stats': warehouse_stats,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def raw_material_list(request):
    """عرض قائمة المواد الخام فقط"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    # فلترة حسب نوع المنتج = مادة خام
    products = Product.objects.filter(product_type='raw_material').select_related('category', 'preferred_supplier')
    
    # البحث
    q = (request.GET.get('q') or '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q)
        )
    
    # فلتر الفئة
    category_id = request.GET.get('category', '')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # فلتر المورد
    supplier_id = request.GET.get('supplier', '')
    if supplier_id:
        products = products.filter(preferred_supplier_id=supplier_id)
    
    # الترتيب
    sort = request.GET.get('sort', 'name')
    if sort in ['name', '-name', 'sku', '-sku', 'cost', '-cost']:
        products = products.order_by(sort)
    else:
        products = products.order_by('name')
    
    # إحصائيات
    total_count = products.count()
    
    # Pagination
    try:
        page_size = int(request.GET.get('page_size') or 25)
    except:
        page_size = 25
    page_size = page_size if page_size in [10, 25, 50, 100] else 25
    
    paginator = Paginator(products, page_size)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # الفئات والموردين للفلاتر
    categories = Category.objects.filter(is_active=True).order_by('name')
    suppliers = Supplier.objects.all().order_by('name')
    
    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'title': _t('المواد الخام'),
        'total_count': total_count,
        'categories': categories,
        'suppliers': suppliers,
        'current_category': category_id,
        'current_supplier': supplier_id,
        'search_query': q,
        'sort': sort,
        'page_size': page_size,
    }
    return render(request, 'inventory/raw_material_list.html', context)


@login_required
def product_list(request):
    """List and search products with advanced filters."""
    from inventory.filters import ProductFilter
    from inventory.exports import InventoryExporter
    
    # إضافة annotation للمخزون لتحسين الأداء
    products: QuerySet[Product] = Product.objects.annotate(
        total_qty=Coalesce(
            Sum(Cast(F('stocks__quantity'), output_field=DecimalField(max_digits=18, decimal_places=2)),
                output_field=DecimalField(max_digits=18, decimal_places=2)),
            Value(Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2)),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
    ).select_related('category')

    # Quick search across name/sku/barcode (q)
    q = (request.GET.get('q') or '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q)
        )
    
    # فلتر نوع المنتج
    product_type = request.GET.get('product_type', '').strip()
    if product_type:
        products = products.filter(product_type=product_type)
    
    # فلتر الفئة
    category_id = request.GET.get('category', '').strip()
    if category_id:
        try:
            products = products.filter(category_id=int(category_id))
        except ValueError:
            pass
    
    product_filter = ProductFilter(request.GET, queryset=products)
    filtered_qs: QuerySet[Product] = cast(QuerySet[Product], product_filter.qs)
    sorted_list: Optional[List[Product]] = None
    filtered_count = filtered_qs.count()
    
    # حساب الإحصائيات باستخدام aggregate بدلاً من iteration
    stats_qs = filtered_qs.aggregate(
        total=Count('id'),
        out_of_stock=Count('id', filter=Q(total_qty__lte=0)),
        low_stock=Count('id', filter=Q(total_qty__gt=0, total_qty__lte=F('min_stock'))),
    )
    in_stock_count = filtered_count - (stats_qs.get('out_of_stock', 0) or 0) - (stats_qs.get('low_stock', 0) or 0)
    
    stats = {
        'total': filtered_count,
        'in_stock': in_stock_count,
        'low_stock': stats_qs.get('low_stock', 0) or 0,
        'out_of_stock': stats_qs.get('out_of_stock', 0) or 0,
    }
    
    # Handle export requests
    export_format = request.GET.get('export')
    if export_format in ['excel', 'pdf']:
        exporter = InventoryExporter()
        # Optionally limit to selected IDs
        ids_param = request.GET.get('ids', '')
        if ids_param:
            try:
                ids_list = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
                export_qs = filtered_qs.filter(id__in=ids_list)
            except Exception:
                export_qs = filtered_qs
        else:
            export_qs = filtered_qs
        if export_format == 'excel':
            return exporter.export_products_excel(export_qs)
        elif export_format == 'pdf':
            return exporter.export_products_pdf(export_qs)
    
    # Generate charts for dashboard
    chart_html = None
    if request.GET.get('chart') == '1':
        try:
            exporter = InventoryExporter()
            chart_html = exporter.generate_stock_chart(sorted_list if sorted_list is not None else filtered_qs)
        except Exception as e:
            messages.warning(request, _t('تعذر إنشاء الرسم البياني: %(error)s') % {'error': e})

    # Sorting
    sort = request.GET.get('sort', '')
    sortable_db_fields = {
        'name': 'name',
        '-name': '-name',
        'sku': 'sku',
        '-sku': '-sku',
        'price': 'price',
        '-price': '-price',
        'cost': 'cost',
        '-cost': '-cost',
        'min_stock': 'min_stock',
        '-min_stock': '-min_stock',
    }
    if sort in sortable_db_fields:
        filtered_qs = filtered_qs.order_by(sortable_db_fields[sort])
    elif sort in ['stock', '-stock', 'value', '-value']:
        # Python-side sorting for computed props
        key_fn = (lambda p: getattr(p, 'current_stock', 0)) if 'stock' in sort else (lambda p: float(getattr(p, 'total_value', 0)))
        reverse = sort.startswith('-')
        sorted_list = sorted(list(filtered_qs), key=key_fn, reverse=reverse)

    # Ensure deterministic ordering if no sort selected (avoids UnorderedObjectListWarning)
    if not sort:
        try:
            filtered_qs = filtered_qs.order_by('name', 'id')
        except Exception:
            pass

    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    try:
        page_size = int(request.GET.get('page_size') or 25)
    except Exception:
        page_size = 25
    page_size = page_size if page_size in [10, 25, 50, 100] else 25
    base_iter = sorted_list if sorted_list is not None else list(filtered_qs)
    paginator = Paginator(base_iter, page_size)
    page = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Totals calculated on the full filtered set (not paged)
    iterable = list(page_obj.object_list)
    total_stock_value = sum(float(getattr(p, 'total_qty', 0) or 0) * float(getattr(p, 'price', 0) or 0) for p in iterable)
    
    # الفئات للفلتر
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    # استخدام low_stock_count من stats
    low_stock_count = stats.get('low_stock', 0)

    context = {
        'products': page_obj,  # إرسال page_obj كاملاً بدلاً من object_list فقط
        'page_obj': page_obj,
        'filter': product_filter,
        'chart_html': chart_html,
        'title': _t('قائمة المنتجات'),
        'total_count': filtered_count,
        'low_stock_count': low_stock_count,
        'total_stock_value': total_stock_value,
        'page_size': page_size,
        'sort': sort,
        'categories': categories,
        'stats': stats,
    }
    return render(request, 'inventory/product_list.html', context)


@login_required
def product_add(request):
    """Add new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            
            # الموقع (المخزن) المبدئي للمنتج
            location_id = (request.POST.get('location') or '').strip()
            if location_id:
                try:
                    loc = Location.objects.get(pk=int(location_id))
                    Stock.objects.get_or_create(product=product, location=loc, defaults={'quantity': 0})
                except Exception:
                    pass
            
            messages.success(request, _t('تم إضافة المنتج "%(name)s" بنجاح') % {'name': product.name})
            return redirect('inventory:product_list')
        else:
            messages.error(request, _t('يرجى تصحيح الأخطاء أدناه'))
    else:
        form = ProductForm()
    
    return render(request, 'inventory/product_form.html', {
        'title': _t('إضافة منتج جديد'),
        'form': form,
        'locations': Location.objects.filter(is_active=True).order_by('code', 'name'),
        'location_types': Location.WAREHOUSE_TYPES,
        'selected_location_id': None,
        'categories': Category.objects.filter(is_active=True).select_related('parent').order_by('sort_order', 'name'),
    })


def _save_packaging_units(request, product):
    """حفظ وحدات التعبئة للمنتج من بيانات النموذج"""
    from inventory.models import PackagingUnit

    # البحث عن وحدات التعبئة في البيانات المرسلة
    index = 0
    while True:
        prefix = f'packaging_units[{index}]'
        pu_type = request.POST.get(f'{prefix}[type]', '').strip()
        pu_name = request.POST.get(f'{prefix}[name]', '').strip()
        pu_qty = request.POST.get(f'{prefix}[quantity]', '').strip()

        if not pu_type or not pu_name:
            break

        try:
            pu = PackagingUnit(
                product=product,
                packaging_type=pu_type,
                name=pu_name,
                quantity_per_unit=Decimal(pu_qty or '0'),
                is_default=request.POST.get(f'{prefix}[is_default]') == '1',
                sort_order=index,
            )

            # الأبعاد (للألواح)
            length = request.POST.get(f'{prefix}[length]', '').strip()
            width = request.POST.get(f'{prefix}[width]', '').strip()
            height = request.POST.get(f'{prefix}[height]', '').strip()
            weight = request.POST.get(f'{prefix}[weight]', '').strip()

            if length:
                pu.length_cm = Decimal(length)
            if width:
                pu.width_cm = Decimal(width)
            if height:
                pu.height_cm = Decimal(height)
            if weight:
                pu.weight_kg = Decimal(weight)

            pu.save()
        except Exception as e:
            # تجاهل الأخطاء في وحدات التعبئة الفردية
            pass

        index += 1


def _save_product_suppliers(request, product):
    """حفظ الموردين المتعددين للمنتج من بيانات النموذج - تحديث بدل حذف وإعادة إنشاء"""
    from partners.models import Supplier
    from inventory.models import SupplierProductPrice

    supplier_ids = request.POST.getlist('supplier_ids[]')
    supplier_costs = request.POST.getlist('supplier_costs[]')
    supplier_currencies = request.POST.getlist('supplier_currencies[]')
    supplier_units = request.POST.getlist('supplier_units[]')
    supplier_conversions = request.POST.getlist('supplier_conversions[]')
    supplier_min_qty = request.POST.getlist('supplier_min_qty[]')
    supplier_lead_time = request.POST.getlist('supplier_lead_time[]')

    # تتبع الموردين الجدد لحذف غير الموجودين
    new_supplier_ids = set()

    for i in range(len(supplier_ids)):
        sid = supplier_ids[i].strip() if i < len(supplier_ids) else ''
        if not sid:
            continue

        try:
            supplier = Supplier.objects.get(pk=int(sid))
        except (Supplier.DoesNotExist, ValueError):
            continue

        new_supplier_ids.add(supplier.pk)

        cost = supplier_costs[i].strip() if i < len(supplier_costs) else '0'
        currency = supplier_currencies[i].strip() if i < len(supplier_currencies) else 'EGP'
        unit = supplier_units[i].strip() if i < len(supplier_units) else 'unit'
        conversion = supplier_conversions[i].strip() if i < len(supplier_conversions) else '1'
        min_qty = supplier_min_qty[i].strip() if i < len(supplier_min_qty) else ''
        lead_time = supplier_lead_time[i].strip() if i < len(supplier_lead_time) else ''

        try:
            # تحديث أو إنشاء (بدون حذف التاريخ)
            sp, created = SupplierProductPrice.objects.update_or_create(
                product=product,
                supplier=supplier,
                defaults={
                    'cost': Decimal(cost or '0'),
                    'currency': currency or 'EGP',
                    'purchase_unit': unit or 'unit',
                    'conversion_to_base': Decimal(conversion or '1'),
                    'min_order_qty': Decimal(min_qty) if min_qty else None,
                    'lead_time_days': int(lead_time) if lead_time else None,
                    'is_active': True,
                }
            )
        except Exception:
            continue

    # حذف الموردين اللي اتشالوا من الفورم
    if new_supplier_ids:
        SupplierProductPrice.objects.filter(
            product=product
        ).exclude(supplier_id__in=new_supplier_ids).delete()
    elif not supplier_ids:
        # لو مفيش موردين خالص، ما نحذفش
        pass


@login_required
def raw_material_create(request):
    """إضافة مادة خام جديدة مع دعم الباركود اليدوي والتلقائي ووحدات التعبئة"""
    from partners.models import Supplier
    from inventory.models import PackagingUnit

    if request.method == 'POST':
        # إنشاء المنتج كمادة خام
        product = Product()
        sku_input = request.POST.get('sku', '').strip()
        product.name = request.POST.get('name', '').strip()
        
        # التحقق من الاسم
        if not product.name:
            messages.error(request, 'يجب إدخال اسم المادة الخام')
            return redirect('inventory:raw_material_create')
        
        # توليد SKU تلقائياً إذا كان فارغاً
        if sku_input:
            product.sku = sku_input
        else:
            import uuid
            clean_name = product.name[:10].replace(' ', '-')
            product.sku = f'RM-{clean_name}-{uuid.uuid4().hex[:6].upper()}'
            # التأكد من عدم التكرار
            while Product.objects.filter(sku=product.sku).exists():
                product.sku = f'RM-{clean_name}-{uuid.uuid4().hex[:6].upper()}'
        
        product.description = request.POST.get('description', '').strip()
        product.product_type = 'raw_material'

        # نوع المادة الخام
        product.raw_material_type = request.POST.get('raw_material_type', '').strip()

        # معالجة الفئة
        category_id = request.POST.get('category', '').strip()
        if category_id:
            try:
                product.category = Category.objects.get(pk=int(category_id))
            except Category.DoesNotExist:
                pass

        # التسعير والتكلفة
        product.purchase_price = Decimal(request.POST.get('purchase_price', '0') or '0')
        product.waste_percentage = Decimal(request.POST.get('waste_percentage', '0') or '0')
        # cost و price يتم حسابها تلقائياً في Product.save()
        product.min_stock = int(request.POST.get('min_stock', '0') or '0')
        product.is_active = request.POST.get('is_active') == 'on'

        # وحدات القياس
        product.purchase_uom = request.POST.get('purchase_uom', 'unit')
        product.usage_uom = request.POST.get('usage_uom', 'unit')
        product.conversion_factor = Decimal(request.POST.get('conversion_factor', '1') or '1')
        
        # الأبعاد والحساب التلقائي
        product.auto_calculate_conversion = request.POST.get('auto_calculate_conversion') == 'on'
        
        if product.auto_calculate_conversion:
            length_val = request.POST.get('length', '').strip()
            width_val = request.POST.get('width', '').strip()
            height_val = request.POST.get('height', '').strip()
            
            if length_val:
                product.length = Decimal(length_val)
            if width_val:
                product.width = Decimal(width_val)
            if height_val:
                product.height = Decimal(height_val)

        # الباركود (يدوي أو تلقائي)
        manual_barcode = request.POST.get('manual_barcode') == 'on'
        product.manual_barcode = manual_barcode

        if manual_barcode:
            barcode_input = request.POST.get('barcode', '').strip()
            if barcode_input:
                # التحقق من عدم التكرار
                if Product.objects.filter(barcode=barcode_input).exists():
                    messages.error(request, 'رقم الباركود مستخدم بالفعل')
                    return redirect('inventory:raw_material_create')
                product.barcode = barcode_input
            else:
                messages.error(request, 'يجب إدخال رقم الباركود في الوضع اليدوي')
                return redirect('inventory:raw_material_create')
        # else: سيتم التوليد التلقائي في save()

        # المورد المفضل
        preferred_supplier_id = request.POST.get('preferred_supplier', '').strip()
        if preferred_supplier_id:
            try:
                product.preferred_supplier = Supplier.objects.get(pk=int(preferred_supplier_id))
            except Supplier.DoesNotExist:
                pass

        # الصورة
        if 'image' in request.FILES:
            product.image = request.FILES['image']

        # حفظ المنتج
        try:
            product.save()

            # معالجة وحدات التعبئة
            _save_packaging_units(request, product)

            # معالجة الموردين المتعددين
            _save_product_suppliers(request, product)

            # ربط سعر المورد المختار بالمادة الخام الجديدة
            selected_supplier_price_id = request.POST.get('selected_supplier_price_id', '').strip()
            if selected_supplier_price_id:
                try:
                    from inventory.models import SupplierProductPrice
                    supplier_price = SupplierProductPrice.objects.get(pk=int(selected_supplier_price_id))
                    supplier_price.product = product
                    # تحديث معامل التحويل إذا تم تغييره
                    conversion_factor = request.POST.get('conversion_factor', '').strip()
                    if conversion_factor:
                        supplier_price.conversion_to_base = Decimal(conversion_factor)
                    supplier_price.save()
                except Exception:
                    pass

            # إضافة إلى المخزن إذا تم تحديده
            location_id = request.POST.get('location', '').strip()
            if location_id:
                try:
                    loc = Location.objects.get(pk=int(location_id))
                    Stock.objects.get_or_create(
                        product=product,
                        location=loc,
                        defaults={'quantity': 0}
                    )
                except Location.DoesNotExist:
                    pass

            messages.success(request, f'تم إضافة المادة الخام "{product.name}" بنجاح')

            # إذا طلب الطباعة
            if request.POST.get('action') == 'save_print':
                return redirect('inventory:product_label', product_id=product.pk)

            return redirect('inventory:raw_material_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في حفظ المادة: {str(e)}')
            return redirect('inventory:raw_material_create')
    
    # GET request - مع Caching للأداء ⚡
    from django.core.cache import cache
    
    # محاولة الحصول على البيانات من الـ cache
    cache_key = 'raw_material_create_dropdowns'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        context = cached_data
    else:
        # استعلامات قاعدة البيانات
        context = {
            'categories': list(Category.objects.filter(is_active=True).order_by('sort_order', 'name')),
            'suppliers': list(Supplier.objects.all().order_by('name')),
            'raw_locations': list(Location.objects.filter(type='raw', is_active=True).order_by('code')),
        }
        # حفظ في الـ cache لمدة 5 دقائق
        cache.set(cache_key, context, 60 * 5)
    
    # إضافة title
    context['title'] = 'إضافة مادة خام جديدة - نظام ذكي'
    
    # بناء JSON الفئات بشكل صحيح (بدون trailing comma)
    import json
    categories_tree = []
    for cat in context['categories']:
        if not cat.parent:
            categories_tree.append({
                'id': cat.pk,
                'name': cat.name,
                'children': [{'id': c.pk, 'name': c.name} for c in cat.children.filter(is_active=True)]
            })
    context['categories_json'] = json.dumps(categories_tree, ensure_ascii=False)
    
    # استخدام النموذج المحسن الجديد
    return render(request, 'inventory/raw_material_form_enhanced.html', context)


@login_required
def raw_material_edit(request, pk):
    """تعديل مادة خام موجودة"""
    from partners.models import Supplier
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        from inventory.models import PackagingUnit

        # تحديث بيانات المادة الخام
        sku_input = request.POST.get('sku', '').strip()
        product.sku = sku_input if sku_input else product.sku  # احتفظ بالـ SKU الحالي إذا كان الحقل فارغاً
        product.name = request.POST.get('name', '').strip()
        product.description = request.POST.get('description', '').strip()
        product.product_type = 'raw_material'

        # نوع المادة الخام
        product.raw_material_type = request.POST.get('raw_material_type', '').strip()

        # معالجة الفئة
        category_id = request.POST.get('category', '').strip()
        if category_id:
            try:
                product.category = Category.objects.get(pk=int(category_id))
            except Category.DoesNotExist:
                product.category = None
        else:
            product.category = None
        
        # التسعير والتكلفة
        old_cost = product.cost  # حفظ السعر القديم للمقارنة
        product.purchase_price = Decimal(request.POST.get('purchase_price', '0') or '0')
        product.waste_percentage = Decimal(request.POST.get('waste_percentage', '0') or '0')
        # cost و price يتم حسابها تلقائياً في Product.save()
        product.min_stock = int(request.POST.get('min_stock', '0') or '0')
        product.is_active = request.POST.get('is_active') == 'on'

        # وحدات القياس
        product.purchase_uom = request.POST.get('purchase_uom', 'unit')
        product.usage_uom = request.POST.get('usage_uom', 'unit')
        product.conversion_factor = Decimal(request.POST.get('conversion_factor', '1') or '1')
        
        # الأبعاد والحساب التلقائي
        product.auto_calculate_conversion = request.POST.get('auto_calculate_conversion') == 'on'
        
        if product.auto_calculate_conversion:
            length_val = request.POST.get('length', '').strip()
            width_val = request.POST.get('width', '').strip()
            height_val = request.POST.get('height', '').strip()
            
            product.length = Decimal(length_val) if length_val else None
            product.width = Decimal(width_val) if width_val else None
            product.height = Decimal(height_val) if height_val else None
        else:
            product.length = None
            product.width = None
            product.height = None

        # الباركود (يدوي أو تلقائي)
        manual_barcode = request.POST.get('manual_barcode') == 'on'
        product.manual_barcode = manual_barcode

        if manual_barcode:
            barcode_input = request.POST.get('barcode', '').strip()
            if barcode_input:
                # التحقق من عدم التكرار (باستثناء المنتج الحالي)
                if Product.objects.filter(barcode=barcode_input).exclude(pk=pk).exists():
                    messages.error(request, 'رقم الباركود مستخدم بالفعل')
                    return redirect('inventory:raw_material_edit', pk=pk)
                product.barcode = barcode_input
        else:
            barcode_input = request.POST.get('barcode', '').strip()
            if barcode_input:
                product.barcode = barcode_input

        # المورد المفضل
        preferred_supplier_id = request.POST.get('preferred_supplier', '').strip()
        if preferred_supplier_id:
            try:
                product.preferred_supplier = Supplier.objects.get(pk=int(preferred_supplier_id))
            except Supplier.DoesNotExist:
                product.preferred_supplier = None
        else:
            product.preferred_supplier = None

        # الصورة
        if 'image' in request.FILES:
            product.image = request.FILES['image']

        # حفظ المنتج
        try:
            product.save()

            # إضافة/تحديث المخزن إذا تم تحديده
            # حذف وحدات التعبئة القديمة وإضافة الجديدة
            PackagingUnit.objects.filter(product=product).delete()
            _save_packaging_units(request, product)

            # تحديث الموردين المتعددين
            _save_product_suppliers(request, product)

            # ربط سعر المورد المختار بالمادة الخام
            selected_supplier_price_id = request.POST.get('selected_supplier_price_id', '').strip()
            if selected_supplier_price_id:
                try:
                    from inventory.models import SupplierProductPrice
                    supplier_price = SupplierProductPrice.objects.get(pk=int(selected_supplier_price_id))
                    supplier_price.product = product
                    # تحديث معامل التحويل إذا تم تغييره
                    conversion_factor = request.POST.get('conversion_factor', '').strip()
                    if conversion_factor:
                        supplier_price.conversion_to_base = Decimal(conversion_factor)
                    supplier_price.save()
                except Exception:
                    pass

            # إذا تغير السعر، تحديث أسعار وحدات التعبئة
            if old_cost != product.cost:
                packaging_units = PackagingUnit.objects.filter(product=product)
                for pu in packaging_units:
                    pu.calculated_price = pu.calculate_price()
                    pu.save(update_fields=['calculated_price', 'updated_at'])

            # إضافة/تحديث المخزن إذا تم تحديده
            location_id = request.POST.get('location', '').strip()
            if location_id:
                try:
                    loc = Location.objects.get(pk=int(location_id))
                    Stock.objects.get_or_create(
                        product=product,
                        location=loc,
                        defaults={'quantity': 0}
                    )
                except Location.DoesNotExist:
                    pass

            messages.success(request, f'تم تحديث المادة الخام "{product.name}" بنجاح')
            
            # إذا طلب الطباعة
            if request.POST.get('action') == 'save_print':
                return redirect('inventory:print_product_barcode', product_id=product.pk)
            
            return redirect('inventory:raw_material_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في حفظ المادة: {str(e)}')
            return redirect('inventory:raw_material_edit', pk=pk)
    
    # GET request - تحميل البيانات الموجودة
    # الحصول على المخزن الحالي للمنتج
    current_stock = Stock.objects.filter(product=product).first()
    current_location_id = current_stock.location_id if current_stock else None
    
    # جلب أسعار الموردين الحالية
    existing_supplier_prices = SupplierProductPrice.objects.filter(
        product=product, is_active=True
    ).select_related('supplier').order_by('-created_at')

    categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    # بناء JSON الفئات بشكل صحيح
    import json
    categories_tree = []
    for cat in categories:
        if not cat.parent:
            categories_tree.append({
                'id': cat.pk,
                'name': cat.name,
                'children': [{'id': c.pk, 'name': c.name} for c in cat.children.filter(is_active=True)]
            })
    
    context = {
        'title': f'تعديل مادة خام: {product.name}',
        'product': product,
        'categories': categories,
        'categories_json': json.dumps(categories_tree, ensure_ascii=False),
        'suppliers': Supplier.objects.all().order_by('name'),
        'raw_locations': Location.objects.filter(type='raw', is_active=True).order_by('code'),
        'current_location_id': current_location_id,
        'existing_supplier_prices': existing_supplier_prices,
        'is_edit': True,
    }
    return render(request, 'inventory/raw_material_form_enhanced.html', context)


@login_required
def raw_material_quick_price(request, pk):
    """تعديل سريع لسعر المادة الخام مع تحديث أسعار وحدات التعبئة و BOM تلقائياً"""
    if request.method != 'POST':
        return redirect('inventory:raw_material_list')

    product = get_object_or_404(Product, pk=pk, product_type='raw_material')

    try:
        new_purchase_price = Decimal(request.POST.get('purchase_price', '') or '0')
        new_cost = Decimal(request.POST.get('cost', '0') or '0')

        if new_purchase_price < 0 or new_cost < 0:
            messages.error(request, 'السعر يجب أن يكون أكبر من أو يساوي صفر')
            return redirect('inventory:raw_material_list')

        old_cost = product.cost
        old_purchase_price = product.purchase_price
        
        # تحديث سعر الشراء
        if new_purchase_price > 0:
            product.purchase_price = new_purchase_price
        
        # save() سيحسب usage_unit_cost و cost تلقائياً
        product.save()

        # تحديث أسعار جميع وحدات التعبئة تلقائياً
        from inventory.models import PackagingUnit
        packaging_units = PackagingUnit.objects.filter(product=product)
        updated_pu_count = 0

        for pu in packaging_units:
            pu.calculated_price = pu.calculate_price()
            pu.save(update_fields=['calculated_price', 'updated_at'])
            updated_pu_count += 1

        # تحديث أسعار BOM تلقائياً
        from production.models import BOMItem, BillOfMaterials
        bom_items = BOMItem.objects.filter(material=product).select_related('bom')
        updated_bom_count = 0
        affected_boms = set()
        
        for item in bom_items:
            item.unit_cost = product.cost  # usage_unit_cost
            item.save(update_fields=['unit_cost'])
            affected_boms.add(item.bom_id)
            updated_bom_count += 1
        
        # إعادة حساب إجمالي تكلفة المواد لكل BOM متأثر
        for bom_id in affected_boms:
            try:
                bom = BillOfMaterials.objects.get(pk=bom_id)
                total_material = sum(
                    item.total_cost for item in bom.items.all()
                )
                bom.total_material_cost = total_material
                bom.save(update_fields=['total_material_cost', 'updated_at'])
            except Exception:
                pass

        # تسجيل تاريخ تغيير السعر
        try:
            from inventory.price_history import MaterialPriceHistory
            price_change = product.purchase_price - old_purchase_price
            change_pct = (price_change / old_purchase_price * 100) if old_purchase_price > 0 else Decimal('0')
            MaterialPriceHistory.objects.create(
                product=product,
                old_price=old_purchase_price,
                new_price=product.purchase_price,
                price_change=price_change,
                change_percentage=change_pct,
                change_type='manual',
                change_reason='market_change',
                notes=request.POST.get('reason', 'تحديث سريع'),
                changed_by=request.user,
            )
        except Exception:
            pass

        # رسالة نجاح مفصلة
        success_msg = f'✅ تم تحديث سعر "{product.name}"'
        if old_purchase_price != product.purchase_price:
            success_msg += f' - سعر الشراء: {old_purchase_price} ← {product.purchase_price} ج.م'
        success_msg += f' - تكلفة الاستخدام: {old_cost} ← {product.cost} ج.م'
        if updated_pu_count > 0:
            success_msg += f' | تم تحديث {updated_pu_count} وحدة تعبئة'
        if updated_bom_count > 0:
            success_msg += f' | تم تحديث {updated_bom_count} عنصر في {len(affected_boms)} قائمة مواد (BOM)'

        messages.success(request, success_msg)

    except Exception as e:
        messages.error(request, f'خطأ في تحديث السعر: {str(e)}')

    return redirect('inventory:raw_material_list')


@login_required
def raw_material_bulk_price_update(request):
    """
    تحديث أسعار مواد خام متعددة دفعة واحدة
    مع تحديث تلقائي لـ: وحدات التعبئة + BOM + سجل الأسعار
    """
    from production.models import BOMItem, BillOfMaterials
    from inventory.models import PackagingUnit
    
    if request.method == 'POST':
        import json
        
        is_ajax = request.headers.get('Content-Type', '') == 'application/json'
        
        if is_ajax:
            data = json.loads(request.body)
            updates = data.get('updates', [])
        else:
            # من form عادي
            updates = []
            for key, value in request.POST.items():
                if key.startswith('price_'):
                    pk = key.replace('price_', '')
                    try:
                        updates.append({
                            'id': int(pk),
                            'purchase_price': value,
                            'reason': request.POST.get(f'reason_{pk}', 'تحديث جماعي'),
                        })
                    except ValueError:
                        continue
        
        updated_materials = []
        updated_boms = set()
        errors = []
        
        for update in updates:
            try:
                product = Product.objects.get(pk=update['id'], product_type='raw_material')
                old_purchase_price = product.purchase_price
                old_cost = product.cost
                
                new_price = Decimal(str(update.get('purchase_price', '0')))
                if new_price <= 0:
                    continue
                if new_price == old_purchase_price:
                    continue
                
                product.purchase_price = new_price
                product.save()  # سيحسب usage_unit_cost و cost تلقائياً
                
                # تحديث وحدات التعبئة
                for pu in PackagingUnit.objects.filter(product=product):
                    pu.calculated_price = pu.calculate_price()
                    pu.save(update_fields=['calculated_price', 'updated_at'])
                
                # تحديث BOM items
                for item in BOMItem.objects.filter(material=product):
                    item.unit_cost = product.cost
                    item.save(update_fields=['unit_cost'])
                    updated_boms.add(item.bom_id)
                
                # تسجيل تاريخ السعر
                try:
                    from inventory.price_history import MaterialPriceHistory
                    price_change = product.purchase_price - old_purchase_price
                    change_pct = (price_change / old_purchase_price * 100) if old_purchase_price > 0 else Decimal('0')
                    MaterialPriceHistory.objects.create(
                        product=product,
                        old_price=old_purchase_price,
                        new_price=product.purchase_price,
                        price_change=price_change,
                        change_percentage=change_pct,
                        change_type='bulk_update',
                        change_reason='market_change',
                        notes=update.get('reason', 'تحديث جماعي'),
                        changed_by=request.user,
                    )
                except Exception:
                    pass
                
                updated_materials.append({
                    'id': product.id,
                    'name': product.name,
                    'old_price': float(old_purchase_price),
                    'new_price': float(product.purchase_price),
                    'old_cost': float(old_cost),
                    'new_cost': float(product.cost),
                })
                
            except Product.DoesNotExist:
                errors.append(f"مادة غير موجودة: {update.get('id')}")
            except Exception as e:
                errors.append(f"خطأ في المادة {update.get('id')}: {str(e)}")
        
        # إعادة حساب إجمالي تكلفة المواد لكل BOM متأثر
        for bom_id in updated_boms:
            try:
                bom = BillOfMaterials.objects.get(pk=bom_id)
                total_material = sum(item.total_cost for item in bom.items.all())
                bom.total_material_cost = total_material
                bom.save(update_fields=['total_material_cost', 'updated_at'])
            except Exception:
                pass
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'updated_count': len(updated_materials),
                'updated_materials': updated_materials,
                'updated_boms_count': len(updated_boms),
                'errors': errors,
            })
        else:
            if updated_materials:
                messages.success(request, 
                    f'✅ تم تحديث {len(updated_materials)} مادة خام'
                    f' وتأثر {len(updated_boms)} قائمة مواد (BOM)'
                )
            if errors:
                messages.warning(request, f'⚠️ أخطاء: {", ".join(errors)}')
            return redirect('inventory:raw_material_list')
    
    # GET - عرض صفحة التحديث الجماعي
    raw_materials = Product.objects.filter(
        product_type='raw_material', is_active=True
    ).select_related('preferred_supplier', 'category').order_by('name')
    
    context = {
        'raw_materials': raw_materials,
        'page_title': 'تحديث جماعي لأسعار المواد الخام',
    }
    return render(request, 'inventory/raw_material_bulk_price.html', context)


@login_required
def print_product_barcode(request, product_id):
    """صفحة طباعة باركود المنتج مع خيارات متعددة"""
    product = get_object_or_404(Product, pk=product_id)
    
    # خيارات الطباعة من الـ query parameters
    copies = int(request.GET.get('copies', 1))
    copies = max(1, min(copies, 100))  # بين 1 و 100
    
    size = request.GET.get('size', 'medium')
    show_name = request.GET.get('show_name', 'on') == 'on'
    show_price = request.GET.get('show_price', '') == 'on'
    barcode_type = request.GET.get('barcode_type', 'code128')
    
    context = {
        'product': product,
        'copies': copies,
        'copy_range': range(copies),
        'size': size,
        'show_name': show_name,
        'show_price': show_price,
        'barcode_type': barcode_type,
    }
    
    return render(request, 'inventory/print_barcode.html', context)


@login_required
def print_barcode_zebra_api(request, product_id):
    """API: إرجاع بيانات طباعة باركود لـ Zebra (يرسلها المتصفح للـ Print Agent)"""
    product = get_object_or_404(Product, pk=product_id)

    if not product.barcode:
        return JsonResponse({'success': False, 'error': 'المنتج لا يحتوي على باركود'})

    label_width = int(request.GET.get('label_width_mm', 50))
    label_height = int(request.GET.get('label_height_mm', 30))
    copies = int(request.GET.get('copies', 1))
    dpi = int(request.GET.get('dpi', 203))

    # إعدادات الطابعة من قاعدة البيانات
    from inventory.models import PrinterConfiguration
    zebra_config = PrinterConfiguration.objects.filter(
        printer_type='zebra',
        document_type='barcode',
        is_active=True,
        is_default=True
    ).first()

    printer_ip = ''
    printer_port = 9100
    printer_name = ''
    if zebra_config:
        printer_ip = str(zebra_config.ip_address) if zebra_config.ip_address else ''
        printer_port = zebra_config.port or 9100
        printer_name = zebra_config.shared_printer_name or zebra_config.name or ''
        if not label_width or label_width == 50:
            label_width = zebra_config.label_width_mm or 50
        if not label_height or label_height == 30:
            label_height = zebra_config.label_height_mm or 30
        dpi = zebra_config.dpi or dpi

    # السعر
    price_str = ''
    if hasattr(product, 'unit_price') and product.unit_price:
        price_str = str(product.unit_price)
    elif hasattr(product, 'price') and product.price:
        price_str = str(product.price)

    print_data = {
        'action': 'print_zebra_label',
        'barcode': product.barcode,
        'product_name': product.name,
        'price': price_str,
        'size_text': '',
        'label_width_mm': label_width,
        'label_height_mm': label_height,
        'dpi': dpi,
        'copies': copies,
        'printer_name': printer_name,
        'ip': printer_ip,
        'port': printer_port,
    }

    return JsonResponse({'success': True, 'print_data': print_data})


@login_required
def printer_config_api(request):
    """API: إرجاع إعدادات الطابعات المكوّنة في النظام"""
    from inventory.models import PrinterConfiguration
    configs = PrinterConfiguration.objects.filter(is_active=True).order_by('printer_type', '-is_default')

    printers = []
    for c in configs:
        printers.append({
            'id': c.id,
            'name': c.name,
            'printer_type': c.printer_type,
            'document_type': c.document_type,
            'connection_type': c.connection_type,
            'ip_address': str(c.ip_address) if c.ip_address else '',
            'port': c.port,
            'shared_printer_name': c.shared_printer_name or '',
            'paper_size': c.paper_size,
            'dpi': c.dpi,
            'label_width_mm': c.label_width_mm,
            'label_height_mm': c.label_height_mm,
            'is_default': c.is_default,
            'total_prints': c.total_prints,
        })

    return JsonResponse({'success': True, 'printers': printers})


@login_required
def product_edit(request, pk):
    """Edit existing product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.sku = request.POST.get('sku')
        product.name = request.POST.get('name')
        product.description = request.POST.get('description', '')
        product.price = request.POST.get('price', 0)
        product.cost = request.POST.get('cost', 0)
        product.min_stock = request.POST.get('min_stock', 0)
        # موقع اختياري لإضافة ارتباط مخزني أولي إن لم يكن موجوداً
        location_id = (request.POST.get('location') or '').strip()
        
        # معالجة الفئة
        category_id = (request.POST.get('category') or '').strip()
        if category_id:
            try:
                product.category = Category.objects.get(pk=int(category_id))
            except Category.DoesNotExist:
                product.category = None
        else:
            product.category = None
        
        # حالة المنتج (نشط/غير نشط) - checkbox لا يُرسل قيمة عند unchecked
        product.is_active = request.POST.get('is_active') == 'on'
        
        # حقول المتجر الإلكتروني
        product.show_in_store = request.POST.get('show_in_store') == 'on'
        product.store_featured = request.POST.get('store_featured') == 'on'
        product.is_new = request.POST.get('is_new') == 'on'
        product.new_until = request.POST.get('new_until') or None
        product.store_description = request.POST.get('store_description', '')
        
        # صورة المنتج
        if 'image' in request.FILES:
            product.image = request.FILES.get('image')
        
        # التعامل مع الباركود
        new_barcode = request.POST.get('barcode', '').strip()
        if new_barcode and new_barcode != product.barcode:
            # التحقق من صحة الباركود الجديد
            is_valid, error_msg = validate_barcode(new_barcode)
            if not is_valid:
                messages.error(request, _t('خطأ في الباركود: %(msg)s') % {'msg': error_msg})
                context = {
                    'product': product,
                    'title': _t('تعديل المنتج: %(name)s') % {'name': product.name},
                    'form_data': request.POST,
                    'locations': Location.objects.filter(is_active=True).order_by('code', 'name'),
                    'location_types': Location.WAREHOUSE_TYPES,
                }
                return render(request, 'inventory/product_form.html', context)
            
            # التحقق من عدم تكرار الباركود الجديد
            if Product.objects.filter(barcode=new_barcode).exclude(pk=product.pk).exists():
                messages.error(request, _t('رقم الباركود مستخدم بالفعل'))
                context = {
                    'product': product,
                    'title': _t('تعديل المنتج: %(name)s') % {'name': product.name},
                    'form_data': request.POST,
                    'locations': Location.objects.filter(is_active=True).order_by('code', 'name'),
                    'location_types': Location.WAREHOUSE_TYPES,
                }
                return render(request, 'inventory/product_form.html', context)
            
            product.barcode = new_barcode
        elif not new_barcode:
            # إذا تم حذف الباركود
            product.barcode = None
        
        try:
            product.save()
            # إذا اختير موقع ولم يكن للمنتج أي أرصدة بعد؛ أنشئ رصيداً صفرياً للربط بالموقع
            if location_id and not product.stocks.exists():
                try:
                    loc = Location.objects.get(pk=int(location_id))
                    Stock.objects.get_or_create(product=product, location=loc, defaults={'quantity': 0})
                except Exception:
                    pass
            messages.success(request, _t('تم تحديث المنتج "%(name)s" بنجاح') % {'name': product.name})
            return redirect('inventory:product_list')
        except Exception as e:
            messages.error(request, _t('خطأ في تحديث المنتج: %(error)s') % {'error': e})
    
    # إنشاء form object للتوافق مع القالب
    class FormInstance:
        def __init__(self, product):
            self.instance = product
    
    form = FormInstance(product)
    
    # أرصدة المخزون حسب الموقع
    stock_by_location = list(
        Stock.objects.filter(product=product)
        .select_related('location')
        .order_by('location__name')
        .values('location__id', 'location__name', 'location__code', 'location__type', 'quantity')
    )
    
    context = {
        'product': product,
        'form': form,
        'title': _t('تعديل المنتج: %(name)s') % {'name': product.name},
        'locations': Location.objects.filter(is_active=True).order_by('code', 'name'),
        'location_types': Location.WAREHOUSE_TYPES,
        'selected_location_id': (product.stocks.first().location_id if product.stocks.exists() else None),
        'categories': Category.objects.filter(is_active=True).select_related('parent').order_by('sort_order', 'name'),
        'stock_by_location': stock_by_location,
    }
    return render(request, 'inventory/product_form.html', context)


@login_required
def location_add_inline(request):
    """إنشاء موقع جديد بسرعة من داخل نموذج المنتج (AJAX)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _t('طريقة غير مدعومة')}, status=405)
    name = (request.POST.get('name') or '').strip()
    code = (request.POST.get('code') or '').strip()
    w_type = (request.POST.get('type') or 'other').strip()
    is_default = (request.POST.get('is_default') == 'on') or (request.POST.get('is_default') == 'true')

    if not name or not code:
        return JsonResponse({'success': False, 'message': _t('الاسم والكود مطلوبان')}, status=400)
    try:
        obj = Location.objects.create(name=name, code=code, type=w_type, is_default=is_default)
        return JsonResponse({
            'success': True,
            'id': obj.id,
            'name': obj.name,
            'code': obj.code,
            'label': f"{obj.code} - {obj.name}",
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def category_add_inline(request):
    """إنشاء فئة جديدة بسرعة من داخل نموذج المنتج (AJAX)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _t('طريقة غير مدعومة')}, status=405)
    
    name = (request.POST.get('name') or '').strip()
    description = (request.POST.get('description') or '').strip()
    parent_id = (request.POST.get('parent') or '').strip()
    
    if not name:
        return JsonResponse({'success': False, 'message': _t('اسم الفئة مطلوب')}, status=400)
    
    try:
        parent = None
        if parent_id:
            parent = Category.objects.get(pk=int(parent_id))
        
        obj = Category.objects.create(
            name=name,
            description=description,
            parent=parent,
            is_active=True
        )
        
        label = f"{parent.name} » {obj.name}" if parent else obj.name
        
        return JsonResponse({
            'success': True,
            'id': obj.id,
            'name': obj.name,
            'label': label,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def api_category_create(request):
    """API لإنشاء فئة جديدة (JSON) - يُستخدم من نموذج المواد الخام"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'بيانات JSON غير صالحة'}, status=400)
    
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    parent_id = data.get('parent_id')
    
    if not name:
        return JsonResponse({'success': False, 'error': 'اسم الفئة مطلوب'}, status=400)
    
    # التحقق من عدم التكرار
    if Category.objects.filter(name=name).exists():
        return JsonResponse({'success': False, 'error': f'الفئة "{name}" موجودة بالفعل'}, status=400)
    
    try:
        parent = None
        if parent_id:
            parent = Category.objects.get(pk=int(parent_id))
        
        obj = Category.objects.create(
            name=name,
            description=description,
            parent=parent,
            is_active=True
        )
        
        # Clear cache
        from django.core.cache import cache
        cache.delete('raw_material_create_dropdowns')
        
        return JsonResponse({
            'success': True,
            'id': obj.id,
            'name': obj.name,
            'parent_name': parent.name if parent else None,
        })
    except Category.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'الفئة الأم غير موجودة'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def category_list(request):
    """عرض قائمة الفئات"""
    categories = Category.objects.select_related('parent').order_by('sort_order', 'name')
    return render(request, 'inventory/category_list.html', {
        'categories': categories,
        'title': _t('إدارة فئات المنتجات'),
    })


@login_required
def category_list_json(request):
    """جلب قائمة الفئات بصيغة JSON للتحديث الديناميكي"""
    categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    data = {
        'categories': [
            {'id': cat.id, 'name': cat.full_path if hasattr(cat, 'full_path') else cat.name}
            for cat in categories
        ]
    }
    return JsonResponse(data)


@login_required
def category_add(request):
    """إضافة فئة جديدة"""
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        description = (request.POST.get('description') or '').strip()
        parent_id = (request.POST.get('parent') or '').strip()
        is_active = request.POST.get('is_active') == 'on'
        sort_order = request.POST.get('sort_order', 0)
        
        if not name:
            messages.error(request, _t('اسم الفئة مطلوب'))
            return redirect('inventory:category_add')
        
        try:
            parent = None
            if parent_id:
                parent = Category.objects.get(pk=int(parent_id))
            
            # معالجة الصورة
            image = request.FILES.get('image')
            
            Category.objects.create(
                name=name,
                description=description,
                parent=parent,
                is_active=is_active,
                sort_order=int(sort_order) if sort_order else 0,
                image=image
            )
            messages.success(request, _t('تم إضافة الفئة "%(name)s" بنجاح') % {'name': name})
            return redirect('inventory:category_list')
        except Exception as e:
            messages.error(request, _t('خطأ في إضافة الفئة: %(error)s') % {'error': e})
    
    categories = Category.objects.filter(parent__isnull=True, is_active=True).order_by('sort_order', 'name')
    return render(request, 'inventory/category_form.html', {
        'title': _t('إضافة فئة جديدة'),
        'parent_categories': categories,
    })


@login_required
def category_edit(request, pk):
    """تعديل فئة"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category.name = (request.POST.get('name') or '').strip()
        category.description = (request.POST.get('description') or '').strip()
        parent_id = (request.POST.get('parent') or '').strip()
        category.is_active = request.POST.get('is_active') == 'on'
        category.sort_order = int(request.POST.get('sort_order', 0) or 0)
        
        if not category.name:
            messages.error(request, _t('اسم الفئة مطلوب'))
            return redirect('inventory:category_edit', pk=pk)
        
        try:
            if parent_id and int(parent_id) != category.pk:
                category.parent = Category.objects.get(pk=int(parent_id))
            elif not parent_id:
                category.parent = None
            
            # معالجة الصورة
            if 'image' in request.FILES:
                category.image = request.FILES.get('image')
            
            category.save()
            messages.success(request, _t('تم تحديث الفئة "%(name)s" بنجاح') % {'name': category.name})
            return redirect('inventory:category_list')
        except Exception as e:
            messages.error(request, _t('خطأ في تحديث الفئة: %(error)s') % {'error': e})
    
    # استثناء الفئة الحالية وفروعها من قائمة الآباء المحتملين
    parent_categories = Category.objects.filter(is_active=True).exclude(pk=pk).order_by('sort_order', 'name')
    return render(request, 'inventory/category_form.html', {
        'title': _t('تعديل الفئة: %(name)s') % {'name': category.name},
        'category': category,
        'parent_categories': parent_categories,
    })


@login_required
def category_delete(request, pk):
    """حذف فئة"""
    category = get_object_or_404(Category, pk=pk)
    
    # فحص الفئات الفرعية
    children_count = Category.objects.filter(parent=category).count()
    
    if children_count > 0:
        messages.error(request, _t('لا يمكن حذف الفئة لأنها تحتوي على %(count)d فئة فرعية، احذف الفئات الفرعية أولاً') % {'count': children_count})
        return redirect('inventory:category_list')
    
    # فصل المنتجات المرتبطة عن الفئة (تصبح بدون فئة)
    products_count = Product.objects.filter(category=category).count()
    if products_count > 0:
        Product.objects.filter(category=category).update(category=None)
    
    name = category.name
    category.delete()
    
    if products_count > 0:
        messages.success(request, _t('تم حذف الفئة "%(name)s" بنجاح وتم إزالة %(count)d منتج من الفئة') % {'name': name, 'count': products_count})
    else:
        messages.success(request, _t('تم حذف الفئة "%(name)s" بنجاح') % {'name': name})
    return redirect('inventory:category_list')


@login_required
def product_delete(request, pk):
    """حذف منتج مع فحص الاعتماديات وتسجبل عملية التدقيق.
    السياسات:
    - يتطلب صلاحية delete على وحدة المخازن عبر resource permission إن وُجد.
    - يمنع الحذف إن كان هناك سجلات مرتبطة حساسة (بنود فواتير بيع/شراء، batches، أرصدة مخزون).
    - في حال السماح، يتم الحذف فعلياً ثم تسجيل AuditLog.
    """
    product = get_object_or_404(Product, pk=pk)

    # تصريح على مستوى الوحدة إن كان نظام الأذونات المعيارية مفعل
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'delete'):
        messages.error(request, _t('ليست لديك صلاحية الحذف'))
        return redirect('inventory:product_list')

    if request.method == 'POST':
        # تأكيد اسم المنتج اختياري للأمان
        confirm = (request.POST.get('confirm_name') or '').strip()
        if confirm and confirm != product.name:
            messages.error(request, _t('قيمة التأكيد لا تطابق اسم المنتج'))
            return redirect('inventory:product_delete', pk=pk)

        # فحوصات علاقات تمنع الحذف
        blocking_reasons = []
        # أرصدة المخزون المجملة - نحذف سجلات المخزون الصفرية أولاً
        total_qty = product.stocks.aggregate(total=Sum('quantity'))['total'] or 0
        if total_qty != 0:
            blocking_reasons.append(_t('يوجد رصيد مخزون للمنتج (%(qty)s) ولا يمكن حذفه. قم بتصفير المخزون أولاً.') % {'qty': total_qty})
        else:
            # حذف سجلات المخزون الصفرية للسماح بحذف المنتج
            product.stocks.filter(quantity=0).delete()
        # دفعات المخزون
        if hasattr(product, 'batches') and product.batches.exists():
            blocking_reasons.append(_t('يوجد دُفعات مخزون مرتبطة بهذا المنتج'))
        # بنود الاستلام/الصرف/الجرد
        if ReceivingItem.objects.filter(product=product).exists():
            blocking_reasons.append(_t('يوجد مستندات استلام مرتبطة بهذا المنتج'))
        if IssueItem.objects.filter(product=product).exists():
            blocking_reasons.append(_t('يوجد مستندات صرف مرتبطة بهذا المنتج'))
        if StockCountItem.objects.filter(product=product).exists():
            blocking_reasons.append(_t('يوجد عناصر جرد مرتبطة بهذا المنتج'))
        # بنود المشتريات/المبيعات
        try:
            from purchases.models import PurchaseItem, PurchaseOrderItem
            if PurchaseItem.objects.filter(product=product).exists():
                blocking_reasons.append(_t('يوجد بنود فواتير شراء مرتبطة بهذا المنتج'))
            if PurchaseOrderItem.objects.filter(product=product).exists():
                blocking_reasons.append(_t('يوجد بنود أوامر شراء مرتبطة بهذا المنتج'))
        except Exception:
            pass
        try:
            from sales.models import InvoiceItem
            if InvoiceItem.objects.filter(product=product).exists():
                blocking_reasons.append(_t('يوجد بنود فواتير بيع مرتبطة بهذا المنتج'))
        except Exception:
            pass

        if blocking_reasons:
            for r in blocking_reasons:
                messages.error(request, r)
            messages.warning(request, _t('لا يمكن حذف المنتج لوجود اعتماديات مرتبطة.'))
            return redirect('inventory:product_delete', pk=pk)

        # تنفيذ الحذف
        obj_meta = AuditLog.build_object_meta(product)
        name_repr = str(product)
        try:
            product.delete()
            messages.success(request, _t('تم حذف المنتج %(name)s بنجاح') % {'name': name_repr})
            # سجل التدقيق
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ACTION_DELETE,
                content_type_id=obj_meta['content_type_id'],
                object_id=obj_meta['object_id'],
                model_name=obj_meta['model_name'],
                app_label=obj_meta['app_label'],
                object_repr=name_repr[:255],
                changes={'reason': 'inventory.product.delete'},
                ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            )
            return redirect('inventory:product_list')
        except Exception as e:
            messages.error(request, _t('تعذر حذف المنتج: %(err)s') % {'err': e})
            return redirect('inventory:product_delete', pk=pk)

    # GET: صفحة تأكيد
    # إظهار تحذيرات إن كان هناك رصيد أو اعتماديات قد تمنع الحذف
    warnings = []
    total_qty = product.stocks.aggregate(total=Sum('quantity'))['total'] or 0
    if total_qty != 0:
        warnings.append(_t('يوجد رصيد مخزون إجمالي: %(qty)s') % {'qty': total_qty})
    if product.batches.exists():
        warnings.append(_t('يوجد دُفعات مخزون مرتبطة'))
    context = {
        'product': product,
        'warnings': warnings,
        'title': _t('تأكيد حذف المنتج')
    }
    return render(request, 'inventory/product_confirm_delete.html', context)


@login_required
def stock_management(request):
    """Stock levels management"""
    stocks = Stock.objects.select_related('product', 'location').all()
    
    # Filter by location
    location_filter = request.GET.get('location', '')
    if location_filter:
        stocks = stocks.filter(location_id=location_filter)
    
    # Filter by product type
    product_type_filter = request.GET.get('product_type', '')
    if product_type_filter:
        stocks = stocks.filter(product__product_type=product_type_filter)
    
    # Filter by low stock
    low_stock_filter = request.GET.get('low_stock', '')
    if low_stock_filter:
        stocks = stocks.filter(quantity__lt=F('product__min_stock'))
    
    locations = Location.objects.all()
    
    context = {
        'stocks': stocks,
        'locations': locations,
        'location_filter': location_filter,
        'product_type_filter': product_type_filter,
        'low_stock_filter': low_stock_filter,
        'product_types': Product.PRODUCT_TYPE_CHOICES,
    }
    return render(request, 'inventory/stock_management.html', context)


@login_required
def warehouse_summary(request):
    """لوحة ملخص المخزون لكل مخزن"""
    from django.db.models import Prefetch

    # Prefetch stocks with products; compute everything in Python to avoid DB mixed-type issues
    locations = (
        Location.objects.filter(is_active=True)
        .prefetch_related(Prefetch('stocks', queryset=Stock.objects.select_related('product')))
        .order_by('code')
    )

    for loc in locations:
        stocks = list(getattr(loc, 'stocks').all())
        # Distinct products count
        loc.product_count = len({s.product_id for s in stocks})
        # Total quantity as Decimal
        loc.total_qty = sum(Decimal(s.quantity) for s in stocks)
        # Total value as Decimal
        loc.total_value = sum(Decimal(s.quantity) * (s.product.cost or Decimal('0')) for s in stocks)

    overall = {
        'warehouses': locations.count(),
        'products': sum(int(getattr(loc, 'product_count', 0) or 0) for loc in locations),
        'quantity': sum(Decimal(getattr(loc, 'total_qty', 0) or 0) for loc in locations),
        'value': sum(Decimal(getattr(loc, 'total_value', 0) or 0) for loc in locations),
    }

    return render(request, 'inventory/warehouse_summary.html', {
        'locations': locations,
        'overall': overall,
        'title': _t('ملخص المخزون حسب المخزن'),
    })


@login_required
def stock_adjust(request):
    """Adjust stock quantities"""
    if request.method == 'POST':
        stock_id = request.POST.get('stock_id')
        adjustment = int(request.POST.get('adjustment', 0))
        reason = request.POST.get('reason', _t('تعديل يدوي'))
        
        try:
            stock = get_object_or_404(Stock, pk=stock_id)
            old_qty = stock.quantity
            stock.quantity += adjustment
            stock.save()
            
            messages.success(
                request,
                _t('تم تعديل مخزون "%(product)s" من %(old)s إلى %(new)s') % {
                    'product': stock.product.name,
                    'old': old_qty,
                    'new': stock.quantity,
                }
            )
            
            # Log the adjustment (can be added to a separate model later)
            
        except Exception as e:
            messages.error(request, _t('خطأ في تعديل المخزون: %(error)s') % {'error': e})
            
        return redirect('inventory:stock_management')
    
    return redirect('inventory:stock_management')


@login_required
def stock_add(request):
    """إضافة كمية مخزون جديدة لمنتج"""
    # الفلترة حسب نوع المنتج
    product_type_filter = request.GET.get('product_type', '')
    location_type_filter = request.GET.get('location_type', '')
    
    if request.method == 'POST':
        product_id = request.POST.get('product')
        location_id = request.POST.get('location')
        quantity = request.POST.get('quantity', 0)
        unit_cost = request.POST.get('unit_cost', 0)
        notes = request.POST.get('notes', '')
        lot_number = request.POST.get('lot_number', '')
        
        try:
            product = get_object_or_404(Product, pk=product_id)
            location = get_object_or_404(Location, pk=location_id)
            quantity = int(quantity)
            
            if quantity <= 0:
                messages.error(request, _t('الكمية يجب أن تكون أكبر من صفر'))
                return redirect('inventory:stock_add')
            
            # إنشاء أو تحديث سجل المخزون
            stock, created = Stock.objects.get_or_create(
                product=product,
                location=location,
                defaults={'quantity': 0}
            )
            
            old_qty = stock.quantity
            stock.quantity += quantity
            stock.save()
            
            # إنشاء سجل دفعة إذا تم تحديد رقم دفعة
            if lot_number:
                StockBatch.objects.create(
                    product=product,
                    location=location,
                    lot_number=lot_number,
                    unit_cost=Decimal(str(unit_cost)) if unit_cost else product.cost,
                    quantity=quantity
                )
            
            # تحديث تكلفة المنتج إذا تم إدخال تكلفة جديدة
            if unit_cost and Decimal(str(unit_cost)) > 0:
                # متوسط التكلفة المرجحة
                if old_qty > 0:
                    current_value = old_qty * product.cost
                    new_value = quantity * Decimal(str(unit_cost))
                    product.cost = (current_value + new_value) / (old_qty + quantity)
                else:
                    product.cost = Decimal(str(unit_cost))
                product.save(update_fields=['cost'])
            
            messages.success(
                request,
                _t('تم إضافة %(qty)s وحدة من "%(product)s" إلى "%(location)s" بنجاح') % {
                    'qty': quantity,
                    'product': product.name,
                    'location': location.name,
                }
            )
            
            # العودة للصفحة مع الفلترات المحفوظة
            redirect_url = 'inventory:stock_add'
            if product_type_filter or location_type_filter:
                params = []
                if product_type_filter:
                    params.append(f'product_type={product_type_filter}')
                if location_type_filter:
                    params.append(f'location_type={location_type_filter}')
                from django.urls import reverse
                redirect_url = reverse('inventory:stock_add') + '?' + '&'.join(params)
                return redirect(redirect_url)
            
            return redirect('inventory:stock_add')
            
        except Exception as e:
            messages.error(request, _t('خطأ في إضافة المخزون: %(error)s') % {'error': e})
            return redirect('inventory:stock_add')
    
    # فلترة المنتجات
    products = Product.objects.filter(is_active=True)
    if product_type_filter:
        products = products.filter(product_type=product_type_filter)
    
    # فلترة المواقع
    locations = Location.objects.filter(is_active=True)
    if location_type_filter:
        locations = locations.filter(type=location_type_filter)
    
    # توصية المواقع بناءً على نوع المنتج
    recommended_locations = []
    if product_type_filter:
        type_mapping = {
            'finished': 'finished',
            'semi_finished': 'wip',
            'raw_material': 'raw',
            'spare_part': 'spare',
        }
        loc_type = type_mapping.get(product_type_filter, 'other')
        recommended_locations = Location.objects.filter(type=loc_type, is_active=True)
    
    context = {
        'products': products.order_by('name'),
        'locations': locations.order_by('name'),
        'recommended_locations': recommended_locations,
        'product_types': Product.PRODUCT_TYPE_CHOICES,
        'location_types': Location.WAREHOUSE_TYPES,
        'product_type_filter': product_type_filter,
        'location_type_filter': location_type_filter,
        'title': _t('إضافة كمية للمخزون'),
    }
    return render(request, 'inventory/stock_add.html', context)


@login_required
def location_list(request):
    """List all locations"""
    locations = Location.objects.annotate(
        product_count=Count('stocks__product', distinct=True),
        total_items=Coalesce(
            Sum(Cast('stocks__quantity', output_field=DecimalField(max_digits=18, decimal_places=2)), 
                output_field=DecimalField(max_digits=18, decimal_places=2)),
            Value(Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2)),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
    )
    
    context = {
        'locations': locations,
    }
    return render(request, 'inventory/location_list.html', context)


@login_required
def location_add(request):
    """Add new location"""
    # الحصول على النوع المحدد مسبقاً من URL
    default_type = request.GET.get('type', 'other')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        address = request.POST.get('address', '')
        w_type = request.POST.get('type') or 'other'
        is_default = request.POST.get('is_default') == 'on'
        
        try:
            Location.objects.create(
                name=name,
                code=code,
                address=address,
                type=w_type,
                is_default=is_default
            )
            messages.success(request, _t('تم إضافة الموقع "%(name)s" بنجاح') % {'name': name})
            return redirect('inventory:warehouse_types')
        except Exception as e:
            messages.error(request, _t('خطأ في إضافة الموقع: %(error)s') % {'error': e})
    
    return render(request, 'inventory/location_form.html', {
        'title': _t('إضافة موقع جديد'), 
        'types': Location.WAREHOUSE_TYPES,
        'default_type': default_type
    })


@login_required
def location_edit(request, pk):
    """Edit an existing location/warehouse"""
    location = get_object_or_404(Location, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        address = request.POST.get('address', '')
        w_type = request.POST.get('type') or 'other'
        is_default = request.POST.get('is_default') == 'on'
        
        try:
            location.name = name
            location.code = code
            location.address = address
            location.type = w_type
            location.is_default = is_default
            location.save()
            
            messages.success(request, _t('تم تحديث المخزن "%(name)s" بنجاح') % {'name': name})
            return redirect('inventory:warehouse_types')
        except Exception as e:
            messages.error(request, _t('خطأ في تحديث المخزن: %(error)s') % {'error': e})
    
    return render(request, 'inventory/location_form.html', {
        'title': _t('تعديل المخزن'), 
        'types': Location.WAREHOUSE_TYPES,
        'location': location,
        'edit_mode': True
    })


@login_required
def location_delete(request, pk):
    """Delete a location/warehouse"""
    location = get_object_or_404(Location, pk=pk)
    
    if request.method == 'POST':
        # التحقق من وجود أرصدة مخزون
        from .models import Stock
        stock_count = Stock.objects.filter(location=location).exclude(quantity=0).count()
        
        if stock_count > 0:
            messages.error(request, f'لا يمكن حذف المخزن "{location.name}" لأنه يحتوي على {stock_count} أصناف بها أرصدة')
            return redirect('inventory:warehouse_types')
        
        try:
            # حذف أي أرصدة صفرية
            Stock.objects.filter(location=location, quantity=0).delete()
            
            location_name = location.name
            location.delete()
            messages.success(request, f'تم حذف المخزن "{location_name}" بنجاح')
        except Exception as e:
            messages.error(request, f'خطأ في حذف المخزن: {e}')
        
        return redirect('inventory:warehouse_types')
    
    return render(request, 'inventory/location_confirm_delete.html', {'location': location})


# =====================
# Stock Transfers
# =====================

@login_required
def transfer_list(request):
    transfers = StockTransfer.objects.select_related('source', 'destination').all()
    return render(request, 'inventory/transfer_list.html', {'transfers': transfers})


@login_required
def transfer_create(request):
    if request.method == 'POST':
        source_id = request.POST.get('source')
        dest_id = request.POST.get('destination')
        notes = request.POST.get('notes', '')
        try:
            source = get_object_or_404(Location, pk=source_id)
            dest = get_object_or_404(Location, pk=dest_id)
            if source_id == dest_id:
                messages.error(request, _t('لا يمكن اختيار نفس الموقع كمصدر ووجهة'))
            else:
                transfer = StockTransfer.objects.create(source=source, destination=dest, notes=notes)
                messages.success(request, _t('تم إنشاء تحويل %(num)s') % {'num': transfer.number})
                return redirect('inventory:transfer_detail', pk=transfer.pk)
        except Exception as e:
            messages.error(request, _t('حدث خطأ: %(error)s') % {'error': e})
    return render(request, 'inventory/transfer_form.html', {
        'locations': Location.objects.filter(is_active=True),
        'title': _t('إنشاء تحويل مخزني')
    })


@login_required
def transfer_detail(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk)

    if request.method == 'POST' and transfer.is_editable:
        product_id = request.POST.get('product')
        qty = int(request.POST.get('quantity', 0))
        try:
            product = get_object_or_404(Product, pk=product_id)
            # check availability
            src = Stock.objects.filter(product=product, location=transfer.source).first()
            if not src or src.quantity < qty:
                messages.error(request, _t('لا يوجد رصيد كافٍ للمنتج %(product)s في %(location)s') % {
                    'product': product.name,
                    'location': transfer.source.name,
                })
            else:
                StockTransferItem.objects.create(transfer=transfer, product=product, quantity=qty)
                messages.success(request, _t('تم إضافة البند'))
        except Exception as e:
            messages.error(request, _t('خطأ: %(error)s') % {'error': e})
        return redirect('inventory:transfer_detail', pk=pk)

    # إظهار المنتجات المتاحة فقط في المخزن المصدر مع الكمية المتاحة
    src_stocks = (
        Stock.objects.filter(location=transfer.source, quantity__gt=0)
        .select_related('product')
        .order_by('product__name', 'product__id')
    )
    available_products = []
    for s in src_stocks:
        p = s.product
        # إرفاق خاصية كمية متاحة لعرضها في القالب
        setattr(p, 'available_qty', int(s.quantity or 0))
        available_products.append(p)

    return render(request, 'inventory/transfer_detail.html', {
        'transfer': transfer,
        'products': available_products,
        'title': _t('تحويل %(num)s') % {'num': transfer.number}
    })


@login_required
def transfer_submit(request, pk):
    """تقديم التحويل للمراجعة (draft -> pending)"""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    if transfer.status != 'draft':
        messages.warning(request, _t('التحويل ليس في حالة مسودة'))
        return redirect('inventory:transfer_detail', pk=pk)
    if not transfer.items.exists():
        messages.error(request, _t('لا يمكن تقديم تحويل بدون بنود'))
        return redirect('inventory:transfer_detail', pk=pk)
    transfer.status = 'pending'
    transfer.save(update_fields=['status'])
    messages.success(request, _t('تم تقديم التحويل للمراجعة'))
    return redirect('inventory:transfer_detail', pk=pk)


@login_required
def transfer_confirm(request, pk):
    transfer = get_object_or_404(StockTransfer, pk=pk)
    if transfer.status not in ('draft', 'pending'):
        messages.warning(request, _t('التحويل مؤكد بالفعل'))
        return redirect('inventory:transfer_detail', pk=pk)
    try:
        transfer.confirm()
        messages.success(request, _t('تم تأكيد التحويل وتحديث الأرصدة'))
    except Exception as e:
        messages.error(request, _t('تعذر التأكيد: %(error)s') % {'error': e})
    return redirect('inventory:transfer_detail', pk=pk)


# =====================
# الاستلام Receiving
# =====================

@login_required
def receiving_list(request):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'view'):
        messages.error(request, _t('ليست لديك صلاحية العرض'))
        return redirect('inventory:dashboard')
    items = Receiving.objects.select_related('location').all()
    return render(request, 'inventory/receiving_list.html', {
        'items': items,
        'title': _t('مستندات الاستلام')
    })


@login_required
def receiving_create(request):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'add'):
        messages.error(request, _t('ليست لديك صلاحية الإضافة'))
        return redirect('inventory:receiving_list')
    if request.method == 'POST':
        location_id = request.POST.get('location')
        # دعم اختيار المورد من قائمة جاهزة مع إمكانية الإدخال اليدوي كخيار احتياطي
        supplier_id = (request.POST.get('supplier_id') or '').strip()
        supplier_name = request.POST.get('supplier_name', '')
        po_reference = request.POST.get('po_reference', '')
        purchase_order_id = request.POST.get('purchase_order') or None
        notes = request.POST.get('notes', '')
        quality_checked = request.POST.get('quality_checked') == 'on'
        try:
            # في حال اختيار مورد من القائمة؛ استخدم اسمه
            if supplier_id:
                try:
                    supplier_obj = Supplier.objects.filter(pk=int(supplier_id)).only('name').first()
                    if supplier_obj:
                        supplier_name = supplier_obj.name
                except Exception:
                    # تجاهل أي خطأ في التحويل واستخدم الإدخال اليدوي إن وُجد
                    pass
            loc = get_object_or_404(Location, pk=location_id)
            obj = Receiving.objects.create(
                location=loc,
                supplier_name=supplier_name,
                po_reference=po_reference,
                purchase_order_id=purchase_order_id,
                notes=notes,
                quality_checked=quality_checked,
            )
            # في حال اختيار أمر شراء؛ يمكن تهيئة المورد من الأمر
            if obj.purchase_order_id and not obj.supplier_name:
                try:
                    PurchaseOrder = apps.get_model('purchases', 'PurchaseOrder')
                    if PurchaseOrder:
                        po = PurchaseOrder.objects.get(pk=obj.purchase_order_id)
                        obj.supplier_name = str(getattr(po, 'supplier', ''))
                        obj.save(update_fields=['supplier_name'])
                except Exception:
                    pass
            messages.success(request, _t('تم إنشاء مستند الاستلام %(num)s') % {'num': obj.number})
            return redirect('inventory:receiving_detail', pk=obj.pk)
        except Exception as e:
            messages.error(request, _t('خطأ: %(error)s') % {'error': e})
    try:
        PurchaseOrder = apps.get_model('purchases', 'PurchaseOrder')
        po_list = PurchaseOrder.objects.filter(status='confirmed') if PurchaseOrder else []
    except Exception:
        po_list = []
    return render(request, 'inventory/receiving_form.html', {
    'locations': Location.objects.filter(is_active=True),
        'suppliers': Supplier.objects.all().order_by('name'),
        'purchase_orders': po_list,
        'title': _t('إنشاء استلام جديد')
    })


@login_required
def receiving_detail(request, pk):
    obj = get_object_or_404(Receiving, pk=pk)
    if request.method == 'POST' and obj.is_editable:
        # زر استيراد بنود أمر الشراء
        if request.POST.get('import_po') and obj.purchase_order_id:
            from purchases.models import PurchaseOrderItem
            try:
                # استيراد بنود الأمر إلى نفس الموقع الخاص بالاستلام فقط
                po_items = PurchaseOrderItem.objects.filter(order_id=obj.purchase_order_id, location=obj.location)
                created = 0
                for it in po_items:
                    ReceivingItem.objects.create(
                        receiving=obj,
                        product=it.product,
                        quantity=it.quantity,
                        unit_cost=it.cost,
                    )
                    created += 1
                messages.success(request, _t('تم استيراد %(count)s بند من أمر الشراء') % {'count': created})
            except Exception as e:
                messages.error(request, _t('تعذر الاستيراد: %(error)s') % {'error': e})
            return redirect('inventory:receiving_detail', pk=pk)
        # إضافة بند يدوي
        else:
            product_id = request.POST.get('product')
            try:
                qty = int(request.POST.get('quantity', 0))
            except Exception:
                qty = 0
            unit_cost = request.POST.get('unit_cost', 0) or 0
            lot_number = request.POST.get('lot_number', '')
            expiry_date = request.POST.get('expiry_date') or None
            try:
                product = get_object_or_404(Product, pk=product_id)
                ReceivingItem.objects.create(
                    receiving=obj,
                    product=product,
                    quantity=qty,
                    unit_cost=unit_cost,
                    lot_number=lot_number,
                    expiry_date=expiry_date,
                )
                messages.success(request, _t('تم إضافة بند'))
            except Exception as e:
                messages.error(request, _t('خطأ: %(error)s') % {'error': e})
            return redirect('inventory:receiving_detail', pk=pk)
    # عرض التفاصيل مع كائن أمر الشراء إن وجد
    po = None
    if obj.purchase_order_id:
        try:
            PurchaseOrder = apps.get_model('purchases', 'PurchaseOrder')
            if PurchaseOrder:
                po = PurchaseOrder.objects.get(pk=obj.purchase_order_id)
        except Exception:
            po = None
    return render(request, 'inventory/receiving_detail.html', {
        'receiving': obj,
        'po': po,
        'products': Product.objects.all(),
        'title': _t('استلام %(num)s') % {'num': obj.number}
    })


@login_required
def receiving_confirm(request, pk):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'change'):
        messages.error(request, _t('ليست لديك صلاحية التأكيد'))
        return redirect('inventory:receiving_detail', pk=pk)
    obj = get_object_or_404(Receiving, pk=pk)
    try:
        obj.confirm()
        messages.success(request, _t('تم تأكيد الاستلام وتحديث المخزون'))
    except Exception as e:
        messages.error(request, _t('تعذر التأكيد: %(error)s') % {'error': e})
    return redirect('inventory:receiving_detail', pk=pk)


# =====================
# الصرف Issue
# =====================

@login_required
def issue_list(request):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'view'):
        messages.error(request, _t('ليست لديك صلاحية العرض'))
        return redirect('inventory:dashboard')
    items = Issue.objects.select_related('location').all()
    return render(request, 'inventory/issue_list.html', {
        'items': items,
        'title': _t('مستندات الصرف')
    })


@login_required
def issue_create(request):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'add'):
        messages.error(request, _t('ليست لديك صلاحية الإضافة'))
        return redirect('inventory:issue_list')
    if request.method == 'POST':
        location_id = request.POST.get('location')
        to_department = request.POST.get('to_department', 'production')
        reference = request.POST.get('reference', '')
        allocation_method = request.POST.get('allocation_method', 'fifo')
        notes = request.POST.get('notes', '')
        received_by_name = (request.POST.get('received_by_name') or '').strip()
        try:
            loc = get_object_or_404(Location, pk=location_id)
            obj = Issue.objects.create(
                location=loc,
                to_department=to_department,
                reference=reference,
                allocation_method=allocation_method,
                notes=notes,
                issued_by=getattr(request, 'user', None),
                received_by_name=received_by_name,
            )
            messages.success(request, _t('تم إنشاء مستند الصرف %(num)s') % {'num': obj.number})
            return redirect('inventory:issue_detail', pk=obj.pk)
        except Exception as e:
            messages.error(request, _t('خطأ: %(error)s') % {'error': e})
    return render(request, 'inventory/issue_form.html', {
    'locations': Location.objects.filter(is_active=True),
        'title': _t('إنشاء صرف جديد')
    })


@login_required
def issue_detail(request, pk):
    obj = get_object_or_404(Issue, pk=pk)
    if request.method == 'POST' and obj.is_editable:
        # Allow updating receiver name before confirmation
        if 'received_by_name' in request.POST and (request.POST.get('update_receiver') == '1'):
            obj.received_by_name = (request.POST.get('received_by_name') or '').strip()
            obj.save(update_fields=['received_by_name'])
            messages.success(request, _t('تم تحديث اسم المستلم'))
            return redirect('inventory:issue_detail', pk=pk)
        product_id = request.POST.get('product')
        qty = int(request.POST.get('quantity', 0))
        try:
            product = get_object_or_404(Product, pk=product_id)
            IssueItem.objects.create(issue=obj, product=product, quantity=qty)
            messages.success(request, _t('تم إضافة بند'))
        except Exception as e:
            messages.error(request, _t('خطأ: %(error)s') % {'error': e})
        return redirect('inventory:issue_detail', pk=pk)
    # عند إضافة بنود الصرف؛ اعرض المنتجات المتوفرة فقط في موقع الصرف
    loc_stocks = (
        Stock.objects.filter(location=obj.location, quantity__gt=0)
        .select_related('product')
        .order_by('product__name', 'product__id')
    )
    available_products = []
    for s in loc_stocks:
        p = s.product
        setattr(p, 'available_qty', int(s.quantity or 0))
        available_products.append(p)

    return render(request, 'inventory/issue_detail.html', {
        'issue': obj,
        'products': available_products,
        'title': _t('صرف %(num)s') % {'num': obj.number}
    })


@login_required
def issue_print(request, pk):
    """عرض طباعة ودي للمستند مع خانة توقيع المستلم."""
    obj = get_object_or_404(Issue, pk=pk)
    context = {
        'issue': obj,
        'title': _t('طباعة إذن صرف %(num)s') % {'num': obj.number},
        'printed_at': timezone.now(),
    }
    return render(request, 'inventory/issue_print.html', context)


@login_required
def issue_confirm(request, pk):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'change'):
        messages.error(request, _t('ليست لديك صلاحية التأكيد'))
        return redirect('inventory:issue_detail', pk=pk)
    obj = get_object_or_404(Issue, pk=pk)
    try:
        # Ensure issuer is captured if missing
        if not obj.issued_by and getattr(request, 'user', None) and request.user.is_authenticated:
            obj.issued_by = request.user
            obj.save(update_fields=['issued_by'])
        obj.confirm()
        messages.success(request, _t('تم تأكيد الصرف وتحديث المخزون'))
    except Exception as e:
        messages.error(request, _t('تعذر التأكيد: %(error)s') % {'error': e})
    return redirect('inventory:issue_detail', pk=pk)


@login_required
def issue_item_delete(request, pk, item_id):
    """حذف بند من إذن الصرف أثناء المسودة فقط."""
    obj = get_object_or_404(Issue, pk=pk)
    if request.method != 'POST':
        return redirect('inventory:issue_detail', pk=pk)
    if not obj.is_editable:
        messages.error(request, _t('لا يمكن حذف البنود بعد التأكيد'))
        return redirect('inventory:issue_detail', pk=pk)
    try:
        item = get_object_or_404(IssueItem, pk=item_id, issue=obj)
        item.delete()
        messages.success(request, _t('تم حذف البند'))
    except Exception as e:
        messages.error(request, _t('تعذر الحذف: %(error)s') % {'error': e})
    return redirect('inventory:issue_detail', pk=pk)


# =====================
# Material Requisitions
# =====================

@login_required
def requisition_list(request):
    items = Requisition.objects.all()
    # تصدير القائمة
    export = (request.GET.get('export') or '').lower()
    if export in {'excel', 'pdf', 'csv'}:
        from inventory.exports import InventoryExporter
        exporter = InventoryExporter()
        # تجهيز بيانات مشتقة: عدد البنود وإجمالي الكمية
        items = items.select_related().prefetch_related('items',)
        if export == 'excel':
            return exporter.export_requisitions_excel(items, filename=_t('طلبات_الخامات'))
        elif export == 'pdf':
            return exporter.export_requisitions_pdf(items, filename=_t('طلبات_الخامات'))
        else:
            return exporter.export_requisitions_csv(items, filename=_t('طلبات_الخامات'))
    return render(request, 'inventory/requisition_list.html', {
        'items': items,
        'title': _t('طلبات خامات الإنتاج')
    })


@login_required
def requisition_create(request):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'add'):
        messages.error(request, _t('ليست لديك صلاحية الإضافة'))
        return redirect('inventory:requisition_list')
    if request.method == 'POST':
        reference = request.POST.get('reference', '')
        notes = request.POST.get('notes', '')
        try:
            obj = Requisition.objects.create(
                from_department='production',
                reference=reference,
                notes=notes,
                requested_by=getattr(request, 'user', None),
            )
            messages.success(request, _t('تم إنشاء طلب الخامات %(num)s') % {'num': obj.number})
            return redirect('inventory:requisition_detail', pk=obj.pk)
        except Exception as e:
            messages.error(request, _t('خطأ: %(error)s') % {'error': e})
    initial = {
        'reference': (request.GET.get('reference') or ''),
        'notes': (request.GET.get('notes') or ''),
    }
    return render(request, 'inventory/requisition_form.html', {
        'title': _t('إنشاء طلب خامات'),
        'initial': initial,
    })


@login_required
def requisition_detail(request, pk):
    obj = get_object_or_404(Requisition, pk=pk)
    # عرض فقط داخل المخزون: لا يسمح بإضافة/تعديل البنود هنا إطلاقاً
    can_edit_items = False
    if request.method == 'POST':
        messages.error(request, _t('العرض فقط: لا يمكن إضافة أو تعديل البنود من شاشة المخزون'))
        return redirect('inventory:requisition_detail', pk=pk)

    # صلاحيات التحكم بالأزرار: تقديم/موافقة من الإنتاج فقط، والتحويل إلى إذن صرف لمن لديه صلاحية إضافة في المخزون
    # التقديم/الموافقة: فقط مستخدمو الإنتاج ذوو صلاحية change أو superuser
    can_submit_approve = bool(getattr(request.user, 'is_superuser', False))
    can_convert_issue = False
    can_convert_po = False
    if hasattr(request.user, 'has_module_permission'):
        try:
            can_submit_approve = can_submit_approve or request.user.has_module_permission('production', 'change')
            can_convert_issue = request.user.has_module_permission('inventory', 'add')
            can_convert_po = request.user.has_module_permission('purchases', 'add')
        except Exception:
            pass
    # Django perms fallback for purchases
    try:
        if not can_convert_po and request.user.has_perm('purchases.add_purchaseorder'):
            can_convert_po = True
    except Exception:
        pass
    return render(request, 'inventory/requisition_detail.html', {
        'requisition': obj,
        'products': Product.objects.all().order_by('name', 'id'),
    'can_edit_items': False,
    'can_submit_approve': can_submit_approve,
    'can_convert_issue': can_convert_issue,
    'can_convert_po': can_convert_po,
    'is_production_request': (str(getattr(obj, 'from_department', '')).lower() == 'production'),
        'title': _t('طلب %(num)s') % {'num': obj.number}
    })


@login_required
def requisition_submit(request, pk):
    obj = get_object_or_404(Requisition, pk=pk)
    # السماح بالتقديم لمستخدمي الإنتاج فقط
    allowed = bool(getattr(request.user, 'is_superuser', False))
    if hasattr(request.user, 'has_module_permission'):
        try:
            allowed = allowed or request.user.has_module_permission('production', 'change')
        except Exception:
            pass
    if not allowed:
        messages.error(request, _t('غير مسموح بالتقديم من شاشة المخزون'))
        return redirect('inventory:requisition_detail', pk=pk)

    if not obj.is_editable:
        return redirect('inventory:requisition_detail', pk=pk)
    obj.status = 'submitted'
    obj.save(update_fields=['status'])
    messages.success(request, _t('تم تقديم الطلب'))
    return redirect('inventory:requisition_detail', pk=pk)


@login_required
def requisition_approve(request, pk):
    # الموافقة من الإنتاج فقط
    allowed = bool(getattr(request.user, 'is_superuser', False))
    if hasattr(request.user, 'has_module_permission'):
        try:
            allowed = allowed or request.user.has_module_permission('production', 'change')
        except Exception:
            pass
    if not allowed:
        messages.error(request, _t('الموافقة متاحة لمستخدمي الإنتاج فقط'))
        return redirect('inventory:requisition_detail', pk=pk)
    obj = get_object_or_404(Requisition, pk=pk)
    if obj.status not in ('submitted', 'draft'):
        messages.error(request, _t('لا يمكن الموافقة في هذه الحالة'))
        return redirect('inventory:requisition_detail', pk=pk)
    obj.status = 'approved'
    obj.approved_by = getattr(request, 'user', None)
    obj.approved_at = timezone.now()
    obj.save(update_fields=['status', 'approved_by', 'approved_at'])
    messages.success(request, _t('تمت الموافقة على الطلب'))
    return redirect('inventory:requisition_detail', pk=pk)


@login_required
def requisition_convert_to_issue(request, pk):
    """تحويل طلب خامات معتمد إلى إذن صرف مسودة مع اختيار المخزن.

    - GET: عرض نموذج لاختيار المخزن وطريقة التخصيص واسم المستلم.
    - POST: إنشاء Issue مسودة وإضافة البنود ثم ربطه بالطلب.
    - الحماية: يتطلب صلاحية على وحدة المخزون (add) ليقوم المستخدم بالتحويل.
    """
    obj = get_object_or_404(Requisition, pk=pk)
    if obj.status not in ('approved',):
        messages.error(request, _t('يجب الموافقة على الطلب قبل التحويل'))
        return redirect('inventory:requisition_detail', pk=pk)

    # فحص صلاحية المستخدم (مخزن)
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'add'):
        messages.error(request, _t('ليست لديك صلاحية التحويل إلى إذن صرف'))
        return redirect('inventory:requisition_detail', pk=pk)

    if request.method == 'POST':
        location_id = request.POST.get('location')
        allocation_method = (request.POST.get('allocation_method') or 'fifo').lower()
        received_by_name = (request.POST.get('received_by_name') or '').strip()
        try:
            loc = get_object_or_404(Location, pk=location_id)
        except Exception:
            loc = None
        if not loc:
            messages.error(request, _t('الرجاء اختيار مخزن صحيح'))
            return redirect('inventory:requisition_convert_to_issue', pk=pk)

        issue = Issue.objects.create(
            location=loc,
            to_department='production',
            reference=obj.reference or obj.number,
            allocation_method=('lifo' if allocation_method == 'lifo' else 'fifo'),
            notes=f'ناتج عن طلب خامات {obj.number}',
            issued_by=getattr(request, 'user', None),
            received_by_name=received_by_name or None,
        )
        count = 0
        for line in obj.items.all():
            try:
                IssueItem.objects.create(issue=issue, product=line.product, quantity=line.quantity)
                count += 1
            except Exception:
                continue
        obj.status = 'converted'
        obj.linked_issue_id = issue.id
        obj.save(update_fields=['status', 'linked_issue_id'])
        messages.success(request, _t('تم إنشاء إذن الصرف %(num)s من الطلب (%(count)s بند)') % {'num': issue.number, 'count': count})
        return redirect('inventory:issue_detail', pk=issue.pk)

    # GET: عرض نموذج الاختيار
    locations = Location.objects.filter(is_active=True).order_by('-is_default', 'code', 'name')
    context = {
        'requisition': obj,
        'locations': locations,
        'title': _t('تحويل طلب %(num)s إلى إذن صرف') % {'num': obj.number},
    }
    return render(request, 'inventory/requisition_convert.html', context)


@login_required
def requisition_print(request, pk):
    """عرض طباعة منسق لطلب الخامات مع مناطق توقيع الموافقة والاستلام.

    يُستخدم في الإنتاج لطلب خامات، ويمكن للمخزن الاعتماد عليه لتجهيز إذن الصرف.
    """
    obj = get_object_or_404(Requisition, pk=pk)
    context = {
        'requisition': obj,
        'title': _t('طباعة طلب خامات %(num)s') % {'num': obj.number},
        'printed_at': timezone.now(),
    }
    return render(request, 'inventory/requisition_print.html', context)


@login_required
def requisition_convert_to_po(request, pk):
    """إنشاء أمر شراء مسودة للنواقص بناءً على طلب خامات معتمد.

    - يتطلب صلاحية purchases.add_purchaseorder.
    - يسمح بإضافة خامة إضافية غير موجودة في الطلب (اختيارية).
    """
    obj = get_object_or_404(Requisition, pk=pk)
    if obj.status not in ('approved',):
        messages.error(request, _t('يجب الموافقة على الطلب قبل التحويل إلى مشتريات'))
        return redirect('inventory:requisition_detail', pk=pk)

    # صلاحيات إنشاء أمر شراء
    has_perm = False
    try:
        has_perm = request.user.is_superuser or request.user.has_perm('purchases.add_purchaseorder')
    except Exception:
        has_perm = False
    if not has_perm and hasattr(request.user, 'has_module_permission'):
        try:
            has_perm = request.user.has_module_permission('purchases', 'add')
        except Exception:
            pass
    if not has_perm:
        messages.error(request, _t('ليست لديك صلاحية إنشاء أوامر شراء'))
        return redirect('inventory:requisition_detail', pk=pk)

    # احسب النواقص بشكل مبسط: المتوفر الإجمالي عبر المخازن
    shortages = []
    for line in obj.items.select_related('product'):
        p = line.product
        required = int(line.quantity or 0)
        available = int(p.current_stock or 0)
        to_buy = max(required - available, 0)
        if to_buy > 0:
            shortages.append({'product': p, 'required': required, 'available': available, 'qty': to_buy})

    if request.method == 'POST':
        # إذا لم توجد نواقص ويضيف المستخدم خامة إضافية فقط، سننشئ أمر شراء بهذه الخامة.
        from purchases.models import PurchaseOrder, PurchaseOrderItem
        supplier_id = request.POST.get('supplier')
        expected_date = request.POST.get('expected_date') or None
        extra_product_id = request.POST.get('extra_product') or None
        extra_qty_raw = request.POST.get('extra_qty') or ''
        try:
            supplier = get_object_or_404(Supplier, pk=supplier_id)
            # جهّز قائمة البنود
            po_items = []
            rows = list(shortages)
            # خامة إضافية اختيارية
            if extra_product_id and extra_qty_raw:
                try:
                    extra_qty = int(extra_qty_raw)
                except Exception:
                    extra_qty = 0
                if extra_qty > 0:
                    ep = get_object_or_404(Product, pk=extra_product_id)
                    rows.append({'product': ep, 'required': extra_qty, 'available': 0, 'qty': extra_qty})

            if not rows:
                messages.info(request, _t('لا توجد نواقص أو خامات مضافة لإنشاء أمر شراء'))
                return redirect('inventory:requisition_detail', pk=pk)

            # رقم أمر شراء
            last = PurchaseOrder.objects.order_by('-id').first()
            if last and last.number:
                try:
                    last_seq = int(str(last.number).split('-')[-1])
                except Exception:
                    last_seq = last.id or 0
                new_no = f"PO-{str(last_seq + 1).zfill(6)}"
            else:
                new_no = 'PO-000001'
            # ضع علامة مصدر واضحة في الملاحظات لربط أمر الشراء بالطلب لاحقاً: REQ#<id>
            src_note = f"REQ#{obj.id} - " + (obj.reference or f"طلب خامات {obj.number}")
            po = PurchaseOrder.objects.create(
                number=new_no,
                supplier=supplier,
                expected_date=expected_date,
                notes=src_note,
                created_by=(request.user if request.user.is_authenticated else None),
                requested_by=(request.user if request.user.is_authenticated else None),
            )
            # موقع استلام افتراضي: أول موقع خامات فعال إن وُجد، وإلا أول موقع فعال
            recv_loc = Location.objects.filter(is_active=True, type='raw').order_by('-is_default', 'code', 'name').first() or \
                       Location.objects.filter(is_active=True).order_by('-is_default', 'code', 'name').first()
            for r in rows:
                po_items.append(PurchaseOrderItem(
                    order=po,
                    product=r['product'],
                    location=recv_loc,
                    quantity=int(r['qty']),
                    cost=r['product'].cost or 0,
                ))
            if po_items:
                PurchaseOrderItem.objects.bulk_create(po_items)
            messages.success(request, _t('تم إنشاء أمر الشراء %(num)s وسيُتابعه قسم المشتريات') % {'num': po.number})
            # إنهاء دور موظف المخزن بتحويله لواجهة المشتريات مباشرةً
            return redirect('purchases:po_detail', pk=po.pk)
        except Exception as e:
            messages.error(request, _t('تعذر إنشاء أمر الشراء: %(error)s') % {'error': e})
            return redirect('inventory:requisition_convert_to_po', pk=pk)

    # GET: عرض صفحة توضح النواقص واختيار المورد
    # جلب الموردين للعرض
    try:
        suppliers_qs = Supplier.objects.all()
    except Exception:
        suppliers_qs = []
    context = {
        'requisition': obj,
        'shortages': shortages,
        'suppliers': suppliers_qs,
        'products': Product.objects.all().order_by('name'),
        'title': _t('تحويل الطلب %(num)s إلى أمر شراء') % {'num': obj.number},
    }
    return render(request, 'inventory/requisition_convert_po.html', context)

@login_required
def requisition_delete(request, pk):
    """حذف طلب خامات بأمان.

    السياسات:
    - مسموح الحذف فقط في حالتي draft/submitted ولم يتم تحويله أو ربطه بإذن صرف.
    - يتطلب صلاحية delete على وحدة المخازن أو superuser.
    - يعرض صفحة تأكيد قبل التنفيذ.
    """
    obj = get_object_or_404(Requisition, pk=pk)

    # صلاحية عامة
    allowed = bool(getattr(request.user, 'is_superuser', False))
    if hasattr(request.user, 'has_module_permission'):
        try:
            allowed = allowed or request.user.has_module_permission('inventory', 'delete')
        except Exception:
            pass
    if not allowed:
        messages.error(request, _t('ليست لديك صلاحية الحذف'))
        return redirect('inventory:requisition_detail', pk=pk)

    # لا يسمح بحذف الحالات غير القابلة
    if obj.status not in ('draft', 'submitted'):
        messages.error(request, _t('لا يمكن حذف الطلب في حالته الحالية'))
        return redirect('inventory:requisition_detail', pk=pk)
    if obj.linked_issue_id:
        messages.error(request, _t('تم ربط الطلب بإذن صرف ولا يمكن حذفه'))
        return redirect('inventory:requisition_detail', pk=pk)

    if request.method == 'POST':
        try:
            meta = AuditLog.build_object_meta(obj)
        except Exception:
            meta = None
        obj_repr = str(obj)
        try:
            obj.delete()
            messages.success(request, _t('تم حذف طلب الخامات بنجاح'))
            # سجل تدقيق اختياري
            try:
                if meta:
                    AuditLog.objects.create(
                        user=request.user,
                        action=AuditLog.ACTION_DELETE,
                        content_type_id=meta['content_type_id'],
                        object_id=meta['object_id'],
                        model_name=meta['model_name'],
                        app_label=meta['app_label'],
                        object_repr=obj_repr[:255],
                        changes={'reason': 'inventory.requisition.delete'},
                        ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    )
            except Exception:
                pass
            return redirect('inventory:requisition_list')
        except Exception as e:
            messages.error(request, _t('تعذر حذف الطلب: %(error)s') % {'error': e})
            return redirect('inventory:requisition_detail', pk=pk)

    # GET: صفحة تأكيد
    return render(request, 'inventory/requisition_confirm_delete.html', {
        'requisition': obj,
        'title': _t('تأكيد حذف الطلب %(num)s') % {'num': obj.number}
    })


# =====================
# الجرد StockCount
# =====================

@login_required
def count_list(request):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'view'):
        messages.error(request, _t('ليست لديك صلاحية العرض'))
        return redirect('inventory:dashboard')
    items = StockCount.objects.select_related('location').all()
    return render(request, 'inventory/count_list.html', {
        'items': items,
        'title': _t('جلسات الجرد')
    })


@login_required
def count_create(request):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'add'):
        messages.error(request, _t('ليست لديك صلاحية الإضافة'))
        return redirect('inventory:count_list')
    if request.method == 'POST':
        location_id = request.POST.get('location')
        notes = request.POST.get('notes', '')
        try:
            loc = get_object_or_404(Location, pk=location_id)
            obj = StockCount.objects.create(location=loc, notes=notes)
            # تعبئة بنود مبدئية من النظام
            stocks = Stock.objects.filter(location=loc).select_related('product')
            items = [
                StockCountItem(
                    stock_count=obj,
                    product=s.product,
                    system_qty=s.quantity,
                    counted_qty=s.quantity,
                ) for s in stocks
            ]
            StockCountItem.objects.bulk_create(items)
            messages.success(request, _t('تم إنشاء جلسة الجرد %(num)s') % {'num': obj.number})
            return redirect('inventory:count_detail', pk=obj.pk)
        except Exception as e:
            messages.error(request, _t('خطأ: %(error)s') % {'error': e})
    return render(request, 'inventory/count_form.html', {
    'locations': Location.objects.filter(is_active=True),
        'title': _t('إنشاء جلسة جرد')
    })


@login_required
def count_detail(request, pk):
    obj = get_object_or_404(StockCount, pk=pk)
    if request.method == 'POST' and obj.is_editable:
        # تحديث الكميات المعدودة من نموذج بسيط
        for item in obj.items.all():
            new_qty = request.POST.get(f'item_{item.id}', None)
            if new_qty is not None:
                try:
                    item.counted_qty = int(new_qty)
                    item.save(update_fields=['counted_qty'])
                except Exception:
                    pass
        obj.status = 'counted'
        obj.save(update_fields=['status'])
        messages.success(request, _t('تم حفظ كميات الجرد'))
        return redirect('inventory:count_detail', pk=pk)
    return render(request, 'inventory/count_detail.html', {
        'count': obj,
        'title': _t('جرد %(num)s') % {'num': obj.number}
    })


@login_required
def count_apply(request, pk):
    if hasattr(request.user, 'has_module_permission') and not request.user.has_module_permission('inventory', 'change'):
        messages.error(request, _t('ليست لديك صلاحية الترحيل'))
        return redirect('inventory:count_detail', pk=pk)
    obj = get_object_or_404(StockCount, pk=pk)
    try:
        obj.apply()
        messages.success(request, _t('تم ترحيل فروقات الجرد'))
    except Exception as e:
        messages.error(request, _t('تعذر الترحيل: %(error)s') % {'error': e})
    return redirect('inventory:count_detail', pk=pk)


@login_required
def count_scan_barcode(request, pk):
    """تحديث جلسة الجرد بالاعتماد على مسح الباركود.

    - يبحث عن المنتج بالباركود
    - إذا كان موجوداً في الجلسة: يزيد الكمية المعدودة
    - إذا لم يكن موجوداً: يضيف بنداً جديداً للجلسة
    """
    count = get_object_or_404(StockCount, pk=pk)

    if not count.is_editable:
        messages.error(request, _t('لا يمكن التعديل على جلسة جرد مُرحلة'))
        return redirect('inventory:count_detail', pk=pk)

    if request.method == 'POST':
        barcode_value = (request.POST.get('barcode') or '').strip()
        qty_raw = (request.POST.get('qty') or '1').strip()

        # التحقق من الكمية
        try:
            qty = int(qty_raw)
            if qty <= 0:
                raise ValueError()
        except Exception:
            qty = 1

        if not barcode_value:
            messages.error(request, _t('رقم الباركود مطلوب'))
            return redirect('inventory:count_detail', pk=pk)

        products = search_products_by_barcode(barcode_value)
        product = products.first()

        if product is None:
            messages.error(request, _t('لم يتم العثور على منتج بهذا الباركود'))
            return redirect('inventory:count_detail', pk=pk)

        # الحصول على بند الجرد أو إنشاؤه
        item, created = StockCountItem.objects.get_or_create(
            stock_count=count,
            product=product,
            defaults={
                'system_qty': 0,
                'counted_qty': 0,
            },
        )

        # في أول مرة نحاول جلب رصيد النظام من جدول Stock
        if created and item.system_qty == 0:
            try:
                stock_row = Stock.objects.get(product=product, location=count.location)
                item.system_qty = int(stock_row.quantity)
            except Stock.DoesNotExist:
                item.system_qty = 0

        # زيادة الكمية المعدودة وحفظها فوراً
        item.counted_qty = int(item.counted_qty) + qty
        item.save(update_fields=['system_qty', 'counted_qty'])

        # تحديث حالة الجلسة إلى "تم العد" حتى بدون الضغط على زر "حفظ العد"
        if count.status == 'draft':
            count.status = 'counted'
            count.save(update_fields=['status'])

        messages.success(
            request,
            _t('تم تسجيل %(qty)s قطعة من %(product)s بالباركود')
            % {'qty': qty, 'product': product.name},
        )

    return redirect('inventory:count_detail', pk=pk)


# ============= نظام الباركود المتكامل =============

@login_required
def barcode_scanner(request):
    """صفحة مسح الباركود"""
    context = {
        'title': _t('مسح الباركود')
    }
    return render(request, 'inventory/barcode_scanner.html', context)


@csrf_exempt
@login_required
def search_by_barcode(request):
    """البحث عن المنتجات بالباركود عبر AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        barcode_value = data.get('barcode', '').strip()

        if not barcode_value:
            return JsonResponse({'success': False, 'message': _t('رقم الباركود مطلوب')})

        # البحث عن المنتج
        products = search_products_by_barcode(barcode_value)
        product = products.first()
        if product is not None:
            product_data = {
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'description': product.description,
                'price': float(product.price),
                'cost': float(product.cost),
                'current_stock': product.current_stock,
                'min_stock': product.min_stock,
                'barcode': product.barcode,
                'is_low_stock': product.is_low_stock,
                'total_value': float(product.total_value)
            }

            return JsonResponse({'success': True, 'product': product_data})
        else:
            return JsonResponse({'success': False, 'message': _t('لم يتم العثور على منتج بهذا الباركود')})

    return JsonResponse({'success': False, 'message': _t('طريقة غير مدعومة')})


@login_required
def generate_barcode_image(request, product_id):
    """توليد صورة الباركود للمنتج"""
    product = get_object_or_404(Product, id=product_id)
    
    if not product.barcode:
        return HttpResponse(_t("المنتج لا يحتوي على باركود"), status=404)

    is_valid, error_msg = validate_barcode(product.barcode)
    if not is_valid:
        return HttpResponse(_t(error_msg), status=400)
    
    # توليد صورة الباركود
    buffer, base64_image = barcode_generator.generate_barcode_image(
        product.barcode, 
        barcode_type='code128',
        width=2.0,
        height=15.0
    )
    
    if buffer:
        # إعادة الصورة كاستجابة HTTP
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="barcode_{product.barcode}.png"'
        return response
    else:
        return HttpResponse(_t("خطأ في توليد الباركود"), status=500)


@login_required
def generate_qr_code(request, product_id):
    """توليد QR Code للمنتج"""
    product = get_object_or_404(Product, id=product_id)
    
    qr_code = get_product_qr_code(product)
    
    if qr_code:
        # استخراج بيانات الصورة من base64
        import base64
        image_data = qr_code.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        response = HttpResponse(image_bytes, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="qr_{product.sku}.png"'
        return response
    else:
        return HttpResponse(_t("خطأ في توليد QR Code"), status=500)


@login_required
def product_label(request, product_id):
    """توليد ملصق المنتج مع الباركود"""
    product = get_object_or_404(Product, id=product_id)
    
    if not product.barcode:
        messages.error(request, _t('المنتج لا يحتوي على باركود'))
        return redirect('inventory:product_list')

    is_valid, error_msg = validate_barcode(product.barcode)
    if not is_valid:
        messages.error(request, _t(error_msg))
        return redirect('inventory:product_list')
    
    # إعدادات الملصق
    include_price = request.GET.get('price', 'true').lower() == 'true'
    include_stock = request.GET.get('stock', 'true').lower() == 'true'
    label_preset = request.GET.get('label_size', 'medium')
    width_mm_param = request.GET.get('width_mm')
    height_mm_param = request.GET.get('height_mm')
    barcode_type = request.GET.get('barcode_type', 'code128').lower()
    barcode_only = request.GET.get('barcode_only', '0') == '1'

    try:
        dpi = int(request.GET.get('dpi') or 203)
    except Exception:
        dpi = 203
    dpi = max(150, min(dpi, 600))

    # تحويل المقاس المطلوب إلى بكسل مع حفظ المقاس بالملليمتر للعرض
    label_px, label_mm = resolve_label_dimensions(label_preset, width_mm_param, height_mm_param, px_per_mm=8)
    
    # توليد الملصق
    label_image = barcode_generator.create_product_label(
        product,
        include_price=include_price,
        include_stock=include_stock,
        label_size=label_px,
        barcode_type=barcode_type,
        dpi=dpi,
        barcode_only=barcode_only,
    )
    
    if label_image:
        # وضع طباعة مباشر عبر HTML عند طلب print=1
        if request.GET.get('print') == '1':
            context = {
                'label_image': label_image,
                'label_width_mm': label_mm[0],
                'label_height_mm': label_mm[1],
                'product': product,
                'dpi': dpi,
                'barcode_only': barcode_only,
            }
            return render(request, 'inventory/product_label_print.html', context)

        # الوضع الافتراضي: إعادة الصورة كـ PNG
        import base64
        image_data = label_image.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        response = HttpResponse(image_bytes, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="label_{product.sku}.png"'
        return response
    else:
        messages.error(request, _t('خطأ في توليد ملصق المنتج'))
        return redirect('inventory:product_list')


@login_required
def batch_labels(request):
    """توليد ملصقات متعددة للمنتجات (محسّنة)"""
    if request.method == 'POST':
        product_ids = request.POST.getlist('product_ids')
        if not product_ids:
            messages.error(request, _t('يجب اختيار منتج واحد على الأقل'))
            return redirect('inventory:product_list')
        products = Product.objects.filter(id__in=product_ids, barcode__isnull=False).exclude(barcode__exact='')
        if not products.exists():
            messages.error(request, _t('لا توجد منتجات مع باركود صحيح'))
            return redirect('inventory:product_list')
        include_price = request.POST.get('include_price', 'on') == 'on'
        include_stock = request.POST.get('include_stock', 'on') == 'on'
        barcode_type = request.POST.get('barcode_type', 'code128').lower()
        label_preset = request.POST.get('label_size', 'default')
        width_mm_param = request.POST.get('width_mm')
        height_mm_param = request.POST.get('height_mm')
        barcode_only = request.POST.get('barcode_only') == 'on'
        try:
            copies = int(request.POST.get('copies', '1') or '1')
        except Exception:
            copies = 1
        copies = max(1, min(copies, 50))  # حمايات
        try:
            dpi = int(request.POST.get('dpi') or 203)
        except Exception:
            dpi = 203
        dpi = max(150, min(dpi, 600))

        label_px, label_mm = resolve_label_dimensions(label_preset, width_mm_param, height_mm_param, px_per_mm=8)

        invalid_products = []
        labels = []
        for product in products:
            if product.barcode:
                is_valid, error_msg = validate_barcode(product.barcode)
                if not is_valid:
                    invalid_products.append(f"{product.sku} - {error_msg}")
                    continue
                for _ in range(copies):
                    label_img = barcode_generator.create_product_label(
                        product,
                        include_price=include_price,
                        include_stock=include_stock,
                        label_size=label_px,
                        barcode_type=barcode_type,
                        dpi=dpi,
                        barcode_only=barcode_only,
                    )
                    if label_img:
                        labels.append({'product': product, 'label_image': label_img})
        if invalid_products:
            messages.warning(request, _t('تم تجاوز %(count)s منتج بسبب باركود غير صالح') % {'count': len(invalid_products)})
        # خيار تنزيل جميع الملصقات كملف ZIP للصور الخام
        if request.POST.get('download_zip') == '1' and labels:
            import zipfile, base64, io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for idx, item in enumerate(labels, start=1):
                    # استخراج base64
                    b64 = item['label_image'].split(',')[1]
                    data = base64.b64decode(b64)
                    filename = f"label_{item['product'].sku}_{idx}.png"
                    zf.writestr(filename, data)
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="product_labels.zip"'
            return response
        context = {
            'labels': labels,
            'title': _t('ملصقات المنتجات'),
            'barcode_type': barcode_type,
            'label_size': label_preset,
            'label_width_mm': label_mm[0],
            'label_height_mm': label_mm[1],
            'copies': copies,
            'dpi': dpi,
            'barcode_only': barcode_only,
        }
        return render(request, 'inventory/batch_labels.html', context)
    products = Product.objects.filter(barcode__isnull=False).exclude(barcode__exact='')
    context = {
        'products': products,
        'default_label_width_mm': 40,
        'default_label_height_mm': 20,
        'default_dpi': 203,
        'default_barcode_only': False,
        'title': _t('طباعة ملصقات متعددة')
    }
    return render(request, 'inventory/select_products_for_labels.html', context)


@login_required
def regenerate_barcode(request, product_id):
    """إعادة توليد باركود للمنتج"""
    product = get_object_or_404(Product, id=product_id)
    
    confirmed = False
    new_barcode = None
    
    if request.method == 'POST':
        # إعادة توليد الباركود
        from inventory.models import generate_unique_barcode
        old_barcode = product.barcode
        new_barcode = generate_unique_barcode()
        product.barcode = new_barcode
        product.save()
        
        confirmed = True
        
        messages.success(request, 
            _t('تم توليد باركود جديد للمنتج "%(name)s": %(barcode)s') % {
                'name': product.name,
                'barcode': product.barcode,
            })
        
        # عرض صفحة التأكيد بدلاً من إعادة التوجيه المباشر
        context = {
            'product': product,
            'title': _t('إعادة توليد باركود: %(name)s') % {'name': product.name},
            'confirmed': confirmed,
            'new_barcode': new_barcode,
            'old_barcode': old_barcode
        }
        return render(request, 'inventory/regenerate_barcode.html', context)
    
    context = {
        'product': product,
        'title': _t('إعادة توليد باركود: %(name)s') % {'name': product.name},
        'confirmed': confirmed,
        'new_barcode': new_barcode
    }
    return render(request, 'inventory/regenerate_barcode.html', context)


@csrf_exempt
@login_required
def barcode_lookup_api(request):
    """API للبحث السريع بالباركود - للاستخدام مع أجهزة المسح الخارجية"""
    if request.method == 'GET':
        barcode_value = request.GET.get('barcode', '').strip()

        if not barcode_value:
            return JsonResponse({'error': 'Barcode parameter is required', 'success': False}, status=400)

        # البحث عن المنتج
        products = search_products_by_barcode(barcode_value)
        product = products.first()
        if product is not None:
            # إنشاء استجابة API مع بيانات كاملة
            response_data = {
                'success': True,
                'found': True,
                'product': {
                    'id': product.id,
                    'sku': product.sku,
                    'name': product.name,
                    'description': product.description,
                    'price': float(product.price),
                    'cost': float(product.cost),
                    'current_stock': product.current_stock,
                    'min_stock': product.min_stock,
                    'barcode': product.barcode,
                    'is_low_stock': product.is_low_stock,
                    'total_value': float(product.total_value)
                },
                'barcode_image_url': f'/inventory/barcode/{product.id}/image/',
                'qr_code_url': f'/inventory/product/{product.id}/qr-code/',
                'label_url': f'/inventory/product/{product.id}/label/'
            }
            return JsonResponse(response_data)
        else:
            return JsonResponse({'success': True, 'found': False, 'message': 'Product not found'})

    return JsonResponse({'error': 'Method not allowed', 'success': False}, status=405)


@login_required
def barcode_management(request):
    """صفحة إدارة الباركود"""
    # إحصائيات الباركود
    total_products = Product.objects.count()
    products_with_barcode = Product.objects.filter(barcode__isnull=False).count()
    products_without_barcode = total_products - products_with_barcode
    
    # المنتجات بدون باركود
    no_barcode_products = Product.objects.filter(barcode__isnull=True)[:10]
    
    # المنتجات المضافة حديثاً مع باركود
    recent_products = Product.objects.filter(
        barcode__isnull=False
    ).order_by('-id')[:10]
    
    context = {
        'title': _t('إدارة الباركود'),
        'total_products': total_products,
        'products_with_barcode': products_with_barcode,
        'products_without_barcode': products_without_barcode,
        'barcode_coverage_percentage': (products_with_barcode / total_products * 100) if total_products > 0 else 0,
        'no_barcode_products': no_barcode_products,
        'recent_products': recent_products,
    }
    return render(request, 'inventory/barcode_management.html', context)


@login_required
def generate_missing_barcodes(request):
    """توليد باركود للمنتجات التي لا تحتوي على باركود"""
    if request.method == 'POST':
        products_without_barcode = Product.objects.filter(
            Q(barcode__isnull=True) | Q(barcode__exact='')
        )
        
        generated_count = 0
        for product in products_without_barcode:
            from inventory.models import generate_unique_barcode
            product.barcode = generate_unique_barcode()
            product.save()
            generated_count += 1
        
        messages.success(request, 
            _t('تم توليد باركود لـ %(count)s منتج بنجاح') % {'count': generated_count})
        
        return redirect('inventory:barcode_management')
    
    # عرض صفحة التأكيد
    products_count = Product.objects.filter(
        Q(barcode__isnull=True) | Q(barcode__exact='')
    ).count()
    
    context = {
        'products_count': products_count,
        'title': _t('توليد الباركود للمنتجات')
    }
    return render(request, 'inventory/generate_missing_barcodes.html', context)


# =====================
# تقارير المخزون: التقييم والتهالك (الأقدمية)
# =====================

@login_required
def valuation_report(request):
    """تقرير تقييم المخزون بالقيمة الحالية لكل منتج/موقع.
    يعتمد على الرصيد المجمل (Stock.quantity) وتكلفة المنتج القياسية Product.cost.
    فلاتر: موقع، كلمة بحث للمنتج. يدعم تصدير CSV.
    """
    # السماح بالوصول القرائي لتقارير المخزون للمستخدمين المسجلين بدون شرط صلاحيات مخصصة
    # يتم التحكم العام عبر Middleware الذي يسمح GET على مسارات التقارير.

    location_id = request.GET.get('location', '')
    search = request.GET.get('search', '').strip()
    export = request.GET.get('export') == 'csv'

    qs = Stock.objects.select_related('product', 'location')
    if location_id:
        qs = qs.filter(location_id=location_id)
    if search:
        qs = qs.filter(Q(product__sku__icontains=search) | Q(product__name__icontains=search))

    rows = []
    total_qty = 0
    total_value = 0
    for s in qs.order_by('location__code', 'product__sku'):
        value = (s.quantity or 0) * (s.product.cost or 0)
        rows.append({
            'location': s.location,
            'product': s.product,
            'sku': s.product.sku,
            'name': s.product.name,
            'qty': s.quantity or 0,
            'cost': s.product.cost or 0,
            'value': value,
        })
        total_qty += s.quantity or 0
        total_value += value

    if export:
        # CSV مع BOM للتوافق مع Excel
        import csv
        from io import StringIO
        buffer = StringIO()
        buffer.write('\ufeff')
        writer = csv.writer(buffer)
        writer.writerow([_t('الموقع'), 'SKU', _t('المنتج'), _t('الكمية'), _t('التكلفة'), _t('القيمة')])
        for r in rows:
            writer.writerow([str(r['location']), r['sku'], r['name'], r['qty'], f"{r['cost']}", f"{r['value']}"])
        writer.writerow([_t('الإجمالي'), '', '', total_qty, '', f"{total_value}"])
        resp = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="inventory_valuation.csv"'
        return resp

    context = {
        'rows': rows,
        'locations': Location.objects.filter(is_active=True),
        'location_filter': location_id,
        'search': search,
        'total_qty': total_qty,
        'total_value': total_value,
        'title': _t('تقرير تقييم المخزون'),
    }
    return render(request, 'inventory/valuation_report.html', context)


@login_required
def aging_report(request):
    """تقرير أقدمية المخزون حسب الدُفعات، يبني سلال عمرية بناءً على تاريخ الاستلام.
    سلال افتراضية بالأيام: 0-30، 31-60، 61-90، 91-180، 180+.
    فلاتر: موقع، منتج، تاريخ مرجعي (الافتراضي اليوم). تصدير CSV.
    """
    # السماح بالوصول القرائي لتقارير المخزون للمستخدمين المسجلين بدون شرط صلاحيات مخصصة
    # يتم التحكم العام عبر Middleware الذي يسمح GET على مسارات التقارير.

    location_id = request.GET.get('location', '')
    product_id = request.GET.get('product', '')
    as_of_str = request.GET.get('as_of', '')
    export = request.GET.get('export') == 'csv'

    if as_of_str:
        try:
            as_of = datetime.strptime(as_of_str, '%Y-%m-%d').date()
        except Exception:
            as_of = datetime.today().date()
    else:
        as_of = datetime.today().date()

    batches = StockBatch.objects.select_related('product', 'location').filter(quantity__gt=0)
    if location_id:
        batches = batches.filter(location_id=location_id)
    if product_id:
        batches = batches.filter(product_id=product_id)

    # سلال العمر
    buckets = [
        (0, 30, '0-30'),
        (31, 60, '31-60'),
        (61, 90, '61-90'),
        (91, 180, '91-180'),
        (181, 99999, '180+'),
    ]

    # تجميع حسب المنتج والموقع
    from collections import defaultdict
    summary = defaultdict(lambda: {'qty': 0, 'value': 0, 'buckets': {b[2]: {'qty': 0, 'value': 0} for b in buckets}})

    for b in batches.order_by('location__code', 'product__sku', 'received_at'):
        days = (as_of - b.received_at.date()).days if b.received_at else 0
        label = buckets[-1][2]
        for lo, hi, name in buckets:
            if lo <= days <= hi:
                label = name
                break
        key = (b.location_id, b.product_id)
        line = summary[key]
        unit_cost = float(b.unit_cost or b.product.cost or 0)
        value = (b.quantity or 0) * unit_cost
        line['qty'] += b.quantity or 0
        line['value'] += value
        line['location'] = b.location
        line['product'] = b.product
        line['sku'] = b.product.sku
        line['name'] = b.product.name
        line['buckets'][label]['qty'] += b.quantity or 0
        line['buckets'][label]['value'] += value

    rows = []
    totals = {'qty': 0, 'value': 0, **{f'qty_{n}': 0 for _, _, n in buckets}, **{f'value_{n}': 0 for _, _, n in buckets}}
    for (_, _), data in summary.items():
        row = {
            'location': data['location'],
            'sku': data['sku'],
            'name': data['name'],
            'qty': data['qty'],
            'value': data['value'],
        }
        for _, _, n in buckets:
            row[f'qty_{n}'] = data['buckets'][n]['qty']
            row[f'value_{n}'] = data['buckets'][n]['value']
            totals[f'qty_{n}'] += data['buckets'][n]['qty']
            totals[f'value_{n}'] += data['buckets'][n]['value']
        totals['qty'] += data['qty']
        totals['value'] += data['value']
        rows.append(row)

    if export:
        # CSV مع BOM
        import csv
        from io import StringIO
        buffer = StringIO()
        buffer.write('\ufeff')
        writer = csv.writer(buffer)
        header = [_t('التاريخ'), _t('الموقع'), 'SKU', _t('المنتج'), _t('الإجمالي (كمية)'), _t('الإجمالي (قيمة)')] + \
                 [f'{n} ({_t("كمية")})' for _, _, n in buckets] + [f'{n} ({_t("قيمة")})' for _, _, n in buckets]
        writer.writerow(header)
        for r in rows:
            writer.writerow([
                as_of.isoformat(), str(r['location']), r['sku'], r['name'], r['qty'], f"{r['value']}"
            ] + [r[f'qty_{n}'] for _, _, n in buckets] + [f"{r[f'value_{n}']}" for _, _, n in buckets])
        writer.writerow([
            as_of.isoformat(), _t('الإجمالي'), '', '', totals['qty'], f"{totals['value']}"
        ] + [totals[f'qty_{n}'] for _, _, n in buckets] + [f"{totals[f'value_{n}']}" for _, _, n in buckets])
        resp = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="inventory_aging.csv"'
        return resp

    bucket_labels = [n for _, _, n in buckets]
    colspan = 5 + (len(bucket_labels) * 2)
    context = {
        'rows': rows,
        'totals': totals,
        'buckets': bucket_labels,
        'locations': Location.objects.filter(is_active=True),
        'products': Product.objects.all(),
        'location_filter': location_id,
        'product_filter': product_id,
        'as_of': as_of,
        'title': _t('تقرير أقدمية المخزون'),
        'colspan': colspan,
    }
    # Try rendering the full template; if a TemplateSyntaxError occurs, fall back to a minimal HTML response
    try:
        return render(request, 'inventory/aging_report.html', context)
    except TemplateSyntaxError:
        # Minimal safe HTML (headers only + totals) to keep page available in case of template parse issues
        html = [
            '<div class="container-fluid">',
            f"<h3 class=\"mb-3\">{context['title']}</h3>",
            '<div class="alert alert-warning">' + _t('حدثت مشكلة في تحميل القالب الكامل. يتم عرض نسخة مبسطة مؤقتاً.') + '</div>',
            '<table class="table table-striped table-sm align-middle">',
            '<thead><tr><th>' + _t('الموقع') + '</th><th>SKU</th><th>' + _t('المنتج') + '</th><th class="text-end">' + _t('الإجمالي (كمية)') + '</th><th class="text-end">' + _t('الإجمالي (قيمة)') + '</th></tr></thead>',
            '<tbody>'
        ]
        for r in rows:
            html.append(
                f"<tr><td>{r['location']}</td><td>{r['sku']}</td><td>{r['name']}</td><td class='text-end'>{r['qty']}</td><td class='text-end'>{r['value']}</td></tr>"
            )
        html.append('</tbody>')
        html.append(
            f"<tfoot><tr class='fw-bold'><td>{_t('الإجمالي')}</td><td></td><td></td><td class='text-end'>{totals['qty']}</td><td class='text-end'>{totals['value']}</td></tr></tfoot>"
        )
        html.append('</table></div>')
        return HttpResponse('\n'.join(html))


# =============================================================================
# الدورة المستندية الكاملة
# =============================================================================

@login_required
def document_cycle_view(request):
    """صفحة الدورة المستندية الكاملة لمصنع المراتب"""
    return render(request, 'inventory/document_cycle.html')


# =============================================================================
# Advanced Inventory Views - Low Stock Monitoring & Real-time Updates
# =============================================================================

@login_required
def low_stock_dashboard(request):
    """Dashboard for monitoring low stock items with real-time updates"""
    from django.conf import settings
    from inventory.filters import ProductFilter
    
    threshold = getattr(settings, 'LOW_STOCK_THRESHOLD_DEFAULT', 10)
    
    # Get all products and filter low stock ones
    all_products = Product.objects.all()
    low_stock_products = [p for p in all_products if p.is_low_stock]
    
    # Apply additional filters
    product_filter = ProductFilter(request.GET, queryset=Product.objects.filter(
        id__in=[p.id for p in low_stock_products]
    ))
    
    filtered_products = product_filter.qs
    
    # Export functionality
    export_format = request.GET.get('export')
    if export_format in ['excel', 'pdf']:
        from inventory.exports import InventoryExporter
        exporter = InventoryExporter()
        if export_format == 'excel':
            return exporter.export_products_excel(
                filtered_products, 
                filename=_t("منتجات_مخزون_منخفض")
            )
        elif export_format == 'pdf':
            return exporter.export_products_pdf(
                filtered_products,
                filename=_t("منتجات_مخزون_منخفض")
            )
    
    # Statistics
    stats = {
        'total_low_stock': len(low_stock_products),
        'critical_stock': len([p for p in low_stock_products if p.current_stock == 0]),
        'warning_stock': len([p for p in low_stock_products if p.current_stock > 0]),
        'total_value_at_risk': sum(p.current_stock * p.cost for p in low_stock_products),
    }
    
    context = {
        'products': filtered_products,
        'filter': product_filter,
        'stats': stats,
        'threshold': threshold,
        'title': _t('مراقبة المخزون المنخفض'),
    }
    
    return render(request, 'inventory/low_stock_dashboard.html', context)


@csrf_exempt
@login_required
def inventory_notifications_api(request):
    """API endpoint for real-time inventory notifications"""
    if request.method == 'GET':
        # Get recent low stock notifications from logs or database
        # For now, return mock data until full notification system is implemented
        
        # Get low stock products as notifications
        low_stock_products = [p for p in Product.objects.all() if p.is_low_stock][:20]
        
        notifications_data = []
        for product in low_stock_products:
            notifications_data.append({
                'id': product.id,
                'message': _t('تحذير: المنتج %(name)s وصل إلى حد المخزون المنخفض (%(stock)s متبقي)') % {
                    'name': product.name,
                    'stock': product.current_stock,
                },
                'timestamp': timezone.now().isoformat(),
                'product_id': product.id,
                'current_stock': product.current_stock,
            })
        
        return JsonResponse({
            'notifications': notifications_data,
            'count': len(notifications_data)
        })
    
    elif request.method == 'POST':
        # Mock mark as read functionality
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        # For now, just return success
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})


@login_required
def advanced_stock_analytics(request):
    """Advanced analytics dashboard for stock management"""
    from inventory.filters import ProductFilter
    from inventory.exports import InventoryExporter
    
    products = Product.objects.all()
    product_filter = ProductFilter(request.GET, queryset=products)
    filtered_products = product_filter.qs
    
    # Generate analytics charts
    exporter = InventoryExporter()
    chart_html = None
    
    try:
        chart_html = exporter.generate_stock_chart(filtered_products)
    except Exception as e:
        messages.warning(request, _t('تعذر إنشاء التحليلات: %(error)s') % {'error': e})
    
    # Calculate analytics data
    analytics_data = {
        'total_products': filtered_products.count(),
        'total_stock_value': sum(p.current_stock * p.cost for p in filtered_products),
        'avg_stock_per_product': sum(p.current_stock for p in filtered_products) / max(filtered_products.count(), 1),
        'low_stock_percentage': (sum(1 for p in filtered_products if p.is_low_stock) / max(filtered_products.count(), 1)) * 100,
    }
    
    # Top products by various metrics
    top_by_value = sorted(
        [(p, p.current_stock * p.cost) for p in filtered_products],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    top_by_quantity = sorted(
        [(p, p.current_stock) for p in filtered_products],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    context = {
        'filter': product_filter,
        'chart_html': chart_html,
        'analytics_data': analytics_data,
        'top_by_value': top_by_value,
        'top_by_quantity': top_by_quantity,
        'title': _t('تحليلات المخزون المتقدمة'),
    }
    
    return render(request, 'inventory/advanced_analytics.html', context)


@login_required
def location_analytics(request):
    """Analytics for warehouse locations"""
    from inventory.filters import LocationFilter
    from inventory.exports import InventoryExporter
    
    locations = Location.objects.filter(is_active=True)
    location_filter = LocationFilter(request.GET, queryset=locations)
    filtered_locations = location_filter.qs
    
    # Export functionality
    export_format = request.GET.get('export')
    if export_format == 'excel':
        exporter = InventoryExporter()
        return exporter.export_locations_excel(filtered_locations)
    
    # Calculate location statistics
    location_stats = []
    for location in filtered_locations:
        total_products = location.stocks.count()
        total_quantity = sum(stock.quantity for stock in location.stocks.all())
        total_value = sum(stock.total_value for stock in location.stocks.all())
        low_stock_count = sum(1 for stock in location.stocks.all() if stock.product.is_low_stock)
        
        location_stats.append({
            'location': location,
            'total_products': total_products,
            'total_quantity': total_quantity,
            'total_value': float(total_value),
            'low_stock_count': low_stock_count,
            'utilization': (total_products / max(100, total_products)) * 100,  # Assuming 100 as max capacity
        })
    
    context = {
        'location_stats': location_stats,
        'filter': location_filter,
        'title': _t('تحليلات المواقع والمستودعات'),
    }
    
    return render(request, 'inventory/location_analytics.html', context)


@csrf_exempt
@login_required
def real_time_stock_update(request, product_id):
    """API endpoint for real-time stock updates"""
    if request.method == 'GET':
        try:
            product = Product.objects.get(id=product_id)
            return JsonResponse({
                'success': True,
                'product_id': product.id,
                'current_stock': product.current_stock,
                'is_low_stock': product.is_low_stock,
                'total_value': float(product.current_stock * product.cost),
                'locations': [
                    {
                        'name': stock.location.name,
                        'quantity': stock.quantity
                    }
                    for stock in product.stocks.all()
                ]
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})


# ============================================================================
# نظام كتالوج المنتجات - Product Catalog System
# ============================================================================

@login_required
def catalog_list(request):
    """
    عرض كتالوج المنتجات بتصميم جميل قابل للطباعة
    يشمل الصور والأسعار والوصف
    """
    # الفلاتر
    category_id = request.GET.get('category')
    search_query = request.GET.get('q', '')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    sort_by = request.GET.get('sort', 'name')
    view_mode = request.GET.get('view', 'grid')  # grid or list
    
    # قاعدة الاستعلام
    products = Product.objects.all()
    
    # تطبيق الفلاتر
    if category_id:
        from inventory.models import Category
        products = products.filter(category_id=category_id)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(barcode__icontains=search_query)
        )
    
    if price_min:
        try:
            products = products.filter(price__gte=Decimal(price_min))
        except:
            pass
    
    if price_max:
        try:
            products = products.filter(price__lte=Decimal(price_max))
        except:
            pass
    
    # الترتيب
    if sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == '-name':
        products = products.order_by('-name')
    elif sort_by == 'price':
        products = products.order_by('price')
    elif sort_by == '-price':
        products = products.order_by('-price')
    elif sort_by == 'category':
        products = products.order_by('category__name', 'name')
    elif sort_by == 'sku':
        products = products.order_by('sku')
    else:
        products = products.order_by('name')
    
    # الفئات للفلتر
    from inventory.models import Category
    categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    # إحصائيات
    total_products = products.count()
    products_with_images = products.exclude(image='').exclude(image__isnull=True).count()
    
    context = {
        'title': _t('كتالوج المنتجات'),
        'products': products,
        'categories': categories,
        'selected_category': category_id,
        'search_query': search_query,
        'price_min': price_min,
        'price_max': price_max,
        'sort_by': sort_by,
        'view_mode': view_mode,
        'total_products': total_products,
        'products_with_images': products_with_images,
    }
    
    return render(request, 'inventory/catalog/catalog_list.html', context)


@login_required
def catalog_print(request):
    """
    صفحة طباعة الكتالوج بتنسيق PDF-ready
    """
    # الفلاتر المختارة
    category_id = request.GET.get('category')
    product_ids = request.GET.getlist('products')
    layout = request.GET.get('layout', 'grid')  # grid, list, detailed
    columns = int(request.GET.get('columns', 3))
    show_price = request.GET.get('show_price', 'true') == 'true'
    show_barcode = request.GET.get('show_barcode', 'true') == 'true'
    show_sku = request.GET.get('show_sku', 'true') == 'true'
    show_description = request.GET.get('show_description', 'true') == 'true'
    show_stock = request.GET.get('show_stock', 'false') == 'true'
    
    # جلب المنتجات
    if product_ids:
        products = Product.objects.filter(id__in=product_ids)
    elif category_id:
        products = Product.objects.filter(category_id=category_id)
    else:
        products = Product.objects.all()
    
    products = products.order_by('category__name', 'name')
    
    # تجميع المنتجات حسب الفئة
    from collections import defaultdict
    products_by_category = defaultdict(list)
    for product in products:
        category_name = product.category.name if product.category else _t('بدون فئة')
        products_by_category[category_name].append(product)
    
    context = {
        'title': _t('طباعة الكتالوج'),
        'products': products,
        'products_by_category': dict(products_by_category),
        'layout': layout,
        'columns': columns,
        'show_price': show_price,
        'show_barcode': show_barcode,
        'show_sku': show_sku,
        'show_description': show_description,
        'show_stock': show_stock,
        'total_products': products.count(),
        'print_date': timezone.now(),
    }
    
    return render(request, 'inventory/catalog/catalog_print.html', context)


@login_required
def catalog_settings(request):
    """
    إعدادات الكتالوج واختيار المنتجات للطباعة
    """
    from inventory.models import Category
    
    if request.method == 'POST':
        # حفظ الإعدادات في الجلسة
        request.session['catalog_settings'] = {
            'layout': request.POST.get('layout', 'grid'),
            'columns': request.POST.get('columns', 3),
            'show_price': request.POST.get('show_price') == 'on',
            'show_barcode': request.POST.get('show_barcode') == 'on',
            'show_sku': request.POST.get('show_sku') == 'on',
            'show_description': request.POST.get('show_description') == 'on',
            'show_stock': request.POST.get('show_stock') == 'on',
        }
        
        # بناء رابط الطباعة
        selected_products = request.POST.getlist('products')
        selected_category = request.POST.get('category')
        
        params = []
        if selected_products:
            for pid in selected_products:
                params.append(f'products={pid}')
        elif selected_category:
            params.append(f'category={selected_category}')
        
        settings = request.session['catalog_settings']
        params.extend([
            f'layout={settings["layout"]}',
            f'columns={settings["columns"]}',
            f'show_price={"true" if settings["show_price"] else "false"}',
            f'show_barcode={"true" if settings["show_barcode"] else "false"}',
            f'show_sku={"true" if settings["show_sku"] else "false"}',
            f'show_description={"true" if settings["show_description"] else "false"}',
            f'show_stock={"true" if settings["show_stock"] else "false"}',
        ])
        
        from django.urls import reverse
        print_url = reverse('inventory:catalog_print') + '?' + '&'.join(params)
        return redirect(print_url)
    
    # جلب البيانات للعرض
    categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    products = Product.objects.all().order_by('category__name', 'name')
    
    # الإعدادات المحفوظة
    saved_settings = request.session.get('catalog_settings', {
        'layout': 'grid',
        'columns': 3,
        'show_price': True,
        'show_barcode': True,
        'show_sku': True,
        'show_description': True,
        'show_stock': False,
    })
    
    context = {
        'title': _t('إعدادات طباعة الكتالوج'),
        'categories': categories,
        'products': products,
        'settings': saved_settings,
    }
    
    return render(request, 'inventory/catalog/catalog_settings.html', context)


@login_required
def catalog_product_detail(request, pk):
    """
    عرض تفاصيل منتج واحد في الكتالوج
    """
    product = get_object_or_404(Product, pk=pk)
    
    # المنتجات المشابهة (نفس الفئة)
    related_products = []
    if product.category:
        related_products = Product.objects.filter(
            category=product.category
        ).exclude(pk=pk)[:6]
    
    context = {
        'title': product.name,
        'product': product,
        'related_products': related_products,
    }
    
    return render(request, 'inventory/catalog/catalog_product_detail.html', context)


@login_required
def catalog_by_category(request, category_id):
    """
    عرض كتالوج منتجات فئة معينة
    """
    from inventory.models import Category
    category = get_object_or_404(Category, pk=category_id)
    
    products = Product.objects.filter(category=category).order_by('name')
    
    # الفئات الفرعية
    subcategories = Category.objects.filter(parent=category, is_active=True)
    
    context = {
        'title': f'كتالوج {category.name}',
        'category': category,
        'products': products,
        'subcategories': subcategories,
    }
    
    return render(request, 'inventory/catalog/catalog_by_category.html', context)


# =============================
# قوائم المواد (BOM)
# =============================

@login_required
def bom_list(request):
    """قائمة قوائم المواد (Bill of Materials)"""
    from production.models import BillOfMaterials
    
    boms = BillOfMaterials.objects.select_related('product').all()
    
    # فلترة حسب البحث
    search = request.GET.get('search', '')
    if search:
        boms = boms.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search)
        )
    
    # ترقيم الصفحات
    paginator = Paginator(boms, 20)
    page = request.GET.get('page', 1)
    boms = paginator.get_page(page)
    
    context = {
        'boms': boms,
        'search': search,
        'page_title': 'قوائم المواد (BOM)',
    }
    return render(request, 'inventory/bom_list.html', context)


@login_required
def bom_create(request):
    """إنشاء قائمة مواد جديدة"""
    from production.models import BillOfMaterials, BOMItem
    
    if request.method == 'POST':
        product_id = request.POST.get('product')
        product = get_object_or_404(Product, pk=product_id)
        
        # التحقق من عدم وجود BOM لهذا المنتج
        existing = BillOfMaterials.objects.filter(product=product, is_active=True).first()
        if existing:
            messages.warning(request, f'يوجد بالفعل قائمة مواد للمنتج {product.name}')
            return redirect('inventory:bom_detail', pk=existing.pk)
        
        bom = BillOfMaterials.objects.create(
            product=product,
            name=f'وصفة {product.name}',
            description=request.POST.get('notes', ''),
            is_active=True,
            is_default=True,
        )
        
        messages.success(request, f'تم إنشاء قائمة مواد للمنتج {product.name}')
        return redirect('inventory:bom_detail', pk=bom.pk)
    
    # فقط المنتجات التامة والنصف مصنع
    products = Product.objects.filter(
        product_type__in=['finished', 'semi_finished']
    ).order_by('name')
    
    context = {
        'products': products,
        'page_title': 'إنشاء قائمة مواد جديدة',
    }
    return render(request, 'inventory/bom_create.html', context)


@login_required
def bom_detail(request, pk):
    """تفاصيل قائمة مواد"""
    from production.models import BillOfMaterials, BOMItem
    
    bom = get_object_or_404(BillOfMaterials, pk=pk)
    # الـ related_name في BOMItem هو 'items'
    items = bom.items.select_related('material').all().order_by('sequence')
    
    context = {
        'bom': bom,
        'items': items,
        'components': items,  # للتوافق مع القالب القديم
        'page_title': f'قائمة مواد: {bom.product.name}',
    }
    return render(request, 'inventory/bom_detail.html', context)


@login_required
def bom_edit(request, pk):
    """تعديل قائمة مواد"""
    from production.models import BillOfMaterials
    
    bom = get_object_or_404(BillOfMaterials, pk=pk)
    
    if request.method == 'POST':
        bom.description = request.POST.get('notes', '')
        bom.is_active = request.POST.get('is_active') == 'on'
        bom.save()
        
        messages.success(request, 'تم تحديث قائمة المواد')
        return redirect('inventory:bom_detail', pk=pk)
    
    context = {
        'bom': bom,
        'page_title': f'تعديل قائمة مواد: {bom.product.name}',
    }
    return render(request, 'inventory/bom_edit.html', context)


@login_required
def bom_add_item(request, pk):
    """إضافة مكون لقائمة المواد"""
    from production.models import BillOfMaterials, BOMItem
    from decimal import Decimal
    
    bom = get_object_or_404(BillOfMaterials, pk=pk)
    
    if request.method == 'POST':
        material_id = request.POST.get('material')
        quantity = request.POST.get('quantity', '1')
        unit_cost = request.POST.get('unit_cost', '0')
        wastage = request.POST.get('wastage_percentage', '0')
        notes = request.POST.get('notes', '')
        
        try:
            material = Product.objects.get(pk=material_id)
            
            # التحقق من عدم وجود المكون مسبقاً
            if BOMItem.objects.filter(bom=bom, material=material).exists():
                messages.warning(request, f'المادة {material.name} موجودة بالفعل في القائمة')
            else:
                # الحصول على آخر ترتيب
                last_seq = BOMItem.objects.filter(bom=bom).order_by('-sequence').first()
                next_seq = (last_seq.sequence + 1) if last_seq else 1
                
                BOMItem.objects.create(
                    bom=bom,
                    material=material,
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(unit_cost) if unit_cost else material.cost or Decimal('0'),
                    wastage_percentage=Decimal(wastage) if wastage else Decimal('0'),
                    notes=notes,
                    sequence=next_seq,
                )
                messages.success(request, f'تم إضافة {material.name} للقائمة')
        except Product.DoesNotExist:
            messages.error(request, 'المادة غير موجودة')
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
        
        return redirect('inventory:bom_detail', pk=pk)
    
    # GET - عرض نموذج الإضافة
    # جلب المواد الخام والمكونات
    raw_materials = Product.objects.filter(
        product_type__in=['raw_material', 'semi_finished']
    ).order_by('name')
    
    context = {
        'bom': bom,
        'raw_materials': raw_materials,
        'page_title': f'إضافة مكون لـ: {bom.product.name}',
    }
    return render(request, 'inventory/bom_add_item.html', context)


@login_required
def bom_delete_item(request, pk, item_pk):
    """حذف مكون من قائمة المواد"""
    from production.models import BillOfMaterials, BOMItem
    
    bom = get_object_or_404(BillOfMaterials, pk=pk)
    item = get_object_or_404(BOMItem, pk=item_pk, bom=bom)
    
    if request.method == 'POST':
        material_name = item.material.name
        item.delete()
        messages.success(request, f'تم حذف {material_name} من القائمة')
    
    return redirect('inventory:bom_detail', pk=pk)


@login_required
def warehouse_types_view(request):
    """عرض المخازن حسب النوع مع الإحصائيات"""
    from django.db.models import Sum, Count
    
    # تجميع المخازن حسب النوع
    finished_locations = Location.objects.filter(type='finished', is_active=True)
    wip_locations = Location.objects.filter(type='wip', is_active=True)
    raw_locations = Location.objects.filter(type='raw', is_active=True)
    spare_locations = Location.objects.filter(type='spare', is_active=True)
    store_locations = Location.objects.filter(type='store', is_active=True)
    other_locations = Location.objects.filter(type='other', is_active=True)
    
    # حساب الإحصائيات لكل نوع
    def get_stats(locations):
        stats = locations.aggregate(
            count=Count('id'),
            products=Count('stocks__product', distinct=True),
            quantity=Sum('stocks__quantity')
        )
        return {
            'count': stats['count'] or 0,
            'products': stats['products'] or 0,
            'quantity': stats['quantity'] or 0
        }
    
    finished_stats = get_stats(finished_locations)
    wip_stats = get_stats(wip_locations)
    raw_stats = get_stats(raw_locations)
    spare_stats = get_stats(spare_locations)
    store_stats = get_stats(store_locations)
    other_stats = get_stats(other_locations)
    
    context = {
        # Finished products
        'finished_locations': finished_locations,
        'finished_count': finished_stats['count'],
        'finished_products': finished_stats['products'],
        'finished_quantity': finished_stats['quantity'],
        
        # Work in progress
        'wip_locations': wip_locations,
        'wip_count': wip_stats['count'],
        'wip_products': wip_stats['products'],
        'wip_quantity': wip_stats['quantity'],
        
        # Raw materials
        'raw_locations': raw_locations,
        'raw_count': raw_stats['count'],
        'raw_products': raw_stats['products'],
        'raw_quantity': raw_stats['quantity'],
        
        # Spare parts
        'spare_locations': spare_locations,
        'spare_count': spare_stats['count'],
        'spare_products': spare_stats['products'],
        'spare_quantity': spare_stats['quantity'],
        
        # Store
        'store_locations': store_locations,
        'store_count': store_stats['count'],
        'store_products': store_stats['products'],
        'store_quantity': store_stats['quantity'],
        
        # Other
        'other_locations': other_locations,
        'other_count': other_stats['count'],
        'other_products': other_stats['products'],
        'other_quantity': other_stats['quantity'],
    }
    
    return render(request, 'inventory/warehouse_types.html', context)


@login_required
def stock_by_supplier_report(request):
    """
    تقرير المخزون حسب المورد
    يعرض المخزون الحالي مع معلومات المورد والأسعار
    """
    from partners.models import Supplier, SupplierProduct
    from django.db.models import Sum, F, Value, DecimalField
    from django.db.models.functions import Coalesce

    # الفلاتر
    supplier_id = request.GET.get('supplier', '')
    category_id = request.GET.get('category', '')
    raw_material_type = request.GET.get('raw_material_type', '')
    location_id = request.GET.get('location', '')

    # جلب المنتجات مع المخزون
    products_qs = Product.objects.filter(
        is_active=True
    ).select_related('category', 'preferred_supplier').prefetch_related(
        'stocks', 'stocks__location', 'suppliers', 'suppliers__supplier'
    )

    # فلترة
    if category_id:
        products_qs = products_qs.filter(category_id=category_id)
    if raw_material_type:
        products_qs = products_qs.filter(raw_material_type=raw_material_type)
    if supplier_id:
        products_qs = products_qs.filter(
            Q(preferred_supplier_id=supplier_id) |
            Q(suppliers__supplier_id=supplier_id)
        ).distinct()

    # تجميع البيانات
    report_data = []
    total_value = Decimal('0')
    total_quantity = Decimal('0')

    for product in products_qs:
        # حساب المخزون
        stocks = product.stocks.all()
        if location_id:
            stocks = [s for s in stocks if str(s.location_id) == location_id]

        product_qty = sum(s.quantity for s in stocks)
        if product_qty <= 0:
            continue

        product_value = product_qty * product.cost

        # جلب معلومات الموردين
        supplier_info = []
        for sp in product.suppliers.all():
            supplier_info.append({
                'supplier': sp.supplier,
                'price': sp.price,
                'currency': sp.currency,
                'is_preferred': sp.is_preferred,
            })

        report_data.append({
            'product': product,
            'quantity': product_qty,
            'value': product_value,
            'preferred_supplier': product.preferred_supplier,
            'supplier_products': supplier_info,
            'stocks': stocks,
        })

        total_value += product_value
        total_quantity += product_qty

    # ترتيب حسب القيمة
    report_data.sort(key=lambda x: x['value'], reverse=True)

    # إحصائيات حسب المورد
    supplier_stats = {}
    for item in report_data:
        if item['preferred_supplier']:
            sid = item['preferred_supplier'].id
            if sid not in supplier_stats:
                supplier_stats[sid] = {
                    'supplier': item['preferred_supplier'],
                    'products_count': 0,
                    'total_quantity': Decimal('0'),
                    'total_value': Decimal('0'),
                }
            supplier_stats[sid]['products_count'] += 1
            supplier_stats[sid]['total_quantity'] += item['quantity']
            supplier_stats[sid]['total_value'] += item['value']

    context = {
        'title': 'تقرير المخزون حسب المورد',
        'report_data': report_data,
        'total_value': total_value,
        'total_quantity': total_quantity,
        'supplier_stats': list(supplier_stats.values()),
        'suppliers': Supplier.objects.all().order_by('name'),
        'categories': Category.objects.filter(is_active=True).order_by('name'),
        'locations': Location.objects.filter(is_active=True).order_by('code'),
        'raw_material_types': Product.RAW_MATERIAL_TYPE_CHOICES,
        'current_supplier': supplier_id,
        'current_category': category_id,
        'current_location': location_id,
        'current_raw_material_type': raw_material_type,
    }
    return render(request, 'inventory/stock_by_supplier_report.html', context)


@login_required
def supplier_prices_view(request, product_id):
    """عرض وإدارة أسعار الموردين لمنتج معين"""
    from partners.models import Supplier
    from inventory.models import SupplierProductPrice, StockBatch

    product = get_object_or_404(Product, pk=product_id, product_type='raw_material')

    # جلب جميع الأسعار
    prices = SupplierProductPrice.objects.filter(product=product).select_related('supplier').order_by('-is_active', 'supplier__name')

    # جلب جميع الموردين
    suppliers = Supplier.objects.all().order_by('name')

    # جلب دفعات المخزون حسب المورد
    batches = StockBatch.objects.filter(
        product=product,
        quantity__gt=0
    ).select_related('supplier', 'location').order_by('-received_at')

    # إضافة حقل total_value لكل batch
    for batch in batches:
        batch.total_value = batch.quantity * batch.unit_cost

    context = {
        'product': product,
        'prices': prices,
        'suppliers': suppliers,
        'batches': batches,
    }

    return render(request, 'inventory/supplier_prices.html', context)


@login_required
def supplier_price_add(request, product_id):
    """إضافة سعر مورد جديد"""
    if request.method != 'POST':
        return redirect('inventory:supplier_prices', product_id=product_id)

    from partners.models import Supplier
    from inventory.models import SupplierProductPrice

    product = get_object_or_404(Product, pk=product_id, product_type='raw_material')

    try:
        supplier_id = request.POST.get('supplier')
        supplier = get_object_or_404(Supplier, pk=supplier_id)

        cost = Decimal(request.POST.get('cost', '0'))
        min_order_qty = request.POST.get('min_order_qty', '').strip()
        lead_time_days = request.POST.get('lead_time_days', '').strip()
        notes = request.POST.get('notes', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        # إنشاء السعر
        price = SupplierProductPrice.objects.create(
            product=product,
            supplier=supplier,
            cost=cost,
            min_order_qty=Decimal(min_order_qty) if min_order_qty else None,
            lead_time_days=int(lead_time_days) if lead_time_days else None,
            notes=notes,
            is_active=is_active
        )

        messages.success(request, f'✅ تم إضافة سعر المورد "{supplier.name}" بنجاح')

    except Exception as e:
        messages.error(request, f'خطأ في إضافة السعر: {str(e)}')

    return redirect('inventory:supplier_prices', product_id=product_id)


@login_required
@require_http_methods(["POST"])
def supplier_price_set_preferred(request, price_id):
    """تعيين مورد كمورد مفضل"""
    from inventory.models import SupplierProductPrice, PackagingUnit
    import json

    try:
        price = get_object_or_404(SupplierProductPrice, pk=price_id)

        # تحديث المورد المفضل
        product = price.product
        product.preferred_supplier = price.supplier
        product.cost = price.cost
        product.price = price.cost
        product.save()

        # تحديث أسعار وحدات التعبئة
        updated_count = 0
        for pu in PackagingUnit.objects.filter(product=product):
            pu.calculated_price = pu.calculate_price()
            pu.save(update_fields=['calculated_price', 'updated_at'])
            updated_count += 1

        return JsonResponse({
            'success': True,
            'message': f'تم تعيين "{price.supplier.name}" كمورد مفضل وتحديث {updated_count} وحدة تعبئة'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ========== نسخ منتج موجود (Duplicate Product) ==========
@login_required
def product_duplicate(request, pk):
    """نسخ منتج موجود لإنشاء منتج جديد بنفس المواصفات"""
    original = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            
            # نسخ أسعار الموردين
            for supplier_price in SupplierProductPrice.objects.filter(product=original):
                SupplierProductPrice.objects.create(
                    product=product,
                    supplier=supplier_price.supplier,
                    cost=supplier_price.cost,
                    purchase_unit=supplier_price.purchase_unit,
                    conversion_to_base=supplier_price.conversion_to_base,
                    min_order_qty=supplier_price.min_order_qty,
                    lead_time_days=supplier_price.lead_time_days,
                    notes=supplier_price.notes,
                    is_active=supplier_price.is_active
                )
            
            # نسخ وحدات التعبئة
            from inventory.models import PackagingUnit
            for pkg in PackagingUnit.objects.filter(product=original):
                PackagingUnit.objects.create(
                    product=product,
                    packaging_type=pkg.packaging_type,
                    name=pkg.name,
                    quantity_per_unit=pkg.quantity_per_unit,
                    is_default=pkg.is_default,
                    length_cm=pkg.length_cm,
                    width_cm=pkg.width_cm,
                    height_cm=pkg.height_cm,
                    weight_kg=pkg.weight_kg,
                    sort_order=pkg.sort_order
                )
            
            messages.success(request, f'✅ تم نسخ المنتج "{original.name}" بنجاح كـ "{product.name}"')
            return redirect('inventory:product_detail', pk=product.id)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء أدناه')
    else:
        # إعداد البيانات الأولية من المنتج الأصلي
        initial_data = {
            'name': f"{original.name} (نسخة)",
            'description': original.description,
            'product_type': original.product_type,
            'raw_material_type': original.raw_material_type,
            'category': original.category,
            'purchase_price': original.purchase_price,
            'cost': original.cost,
            'price': original.price,
            'min_stock': original.min_stock,
            'max_stock': original.max_stock,
            'purchase_uom': original.purchase_uom,
            'usage_uom': original.usage_uom,
            'conversion_factor': original.conversion_factor,
            'auto_calculate_conversion': original.auto_calculate_conversion,
            'length': original.length,
            'width': original.width,
            'height': original.height,
            'is_active': original.is_active,
            'notes': original.notes,
        }
        form = ProductForm(initial=initial_data)
    
    return render(request, 'inventory/product_form.html', {
        'title': f'نسخ منتج: {original.name}',
        'form': form,
        'is_duplicate': True,
        'original_product': original,
        'locations': Location.objects.filter(is_active=True).order_by('code', 'name'),
        'categories': Category.objects.filter(is_active=True).select_related('parent').order_by('sort_order', 'name'),
    })


# ========== استيراد منتجات من Excel/CSV ==========
@login_required
def bulk_import_products(request):
    """صفحة استيراد منتجات من ملف Excel أو CSV"""
    if request.method == 'POST' and request.FILES.get('import_file'):
        try:
            import openpyxl
            import pandas as pd
            from io import BytesIO
            
            file = request.FILES['import_file']
            file_ext = file.name.split('.')[-1].lower()
            
            # قراءة الملف
            if file_ext == 'xlsx':
                df = pd.read_excel(file, engine='openpyxl')
            elif file_ext == 'csv':
                df = pd.read_csv(file)
            else:
                messages.error(request, 'نوع الملف غير مدعوم. يرجى رفع ملف Excel (.xlsx) أو CSV (.csv)')
                return redirect('inventory:bulk_import_products')
            
            # معالجة البيانات
            results = process_excel_import(df, request.user)
            
            # عرض النتائج
            success_count = len(results['success'])
            error_count = len(results['errors'])
            
            if success_count > 0:
                messages.success(request, f'✅ تم استيراد {success_count} منتج بنجاح')
            if error_count > 0:
                messages.warning(request, f'⚠️ فشل استيراد {error_count} منتج')
            
            return render(request, 'inventory/bulk_import_results.html', {
                'results': results,
                'success_count': success_count,
                'error_count': error_count,
            })
            
        except Exception as e:
            messages.error(request, f'خطأ في معالجة الملف: {str(e)}')
            return redirect('inventory:bulk_import_products')
    
    return render(request, 'inventory/bulk_import.html', {
        'title': 'استيراد منتجات من Excel/CSV'
    })


def process_excel_import(df, user):
    """معالجة بيانات Excel وإنشاء المنتجات"""
    results = {
        'success': [],
        'errors': []
    }
    
    for index, row in df.iterrows():
        try:
            # التحقق من البيانات المطلوبة
            if pd.isna(row.get('اسم المنتج')) or not str(row.get('اسم المنتج')).strip():
                results['errors'].append({
                    'row': index + 2,
                    'error': 'اسم المنتج مطلوب'
                })
                continue
            
            # إنشاء المنتج
            product = Product()
            product.name = str(row.get('اسم المنتج')).strip()
            
            # SKU (إذا لم يكن موجوداً، سيتم توليده تلقائياً)
            if not pd.isna(row.get('SKU')):
                sku = str(row.get('SKU')).strip()
                if Product.objects.filter(sku=sku).exists():
                    results['errors'].append({
                        'row': index + 2,
                        'error': f'SKU "{sku}" مستخدم بالفعل'
                    })
                    continue
                product.sku = sku
            
            # نوع المنتج
            product_type = str(row.get('نوع المنتج', 'raw_material')).strip()
            if product_type in dict(Product.PRODUCT_TYPE_CHOICES).keys():
                product.product_type = product_type
            else:
                product.product_type = 'raw_material'
            
            # نوع المادة الخام
            if not pd.isna(row.get('نوع المادة الخام')):
                raw_type = str(row.get('نوع المادة الخام')).strip()
                if raw_type in dict(Product.RAW_MATERIAL_TYPE_CHOICES).keys():
                    product.raw_material_type = raw_type
            
            # الفئة
            if not pd.isna(row.get('الفئة')):
                category_name = str(row.get('الفئة')).strip()
                category = Category.objects.filter(name__icontains=category_name).first()
                if category:
                    product.category = category
            
            # وحدات القياس
            product.purchase_uom = str(row.get('وحدة الشراء', 'unit')).strip()
            product.usage_uom = str(row.get('وحدة الاستخدام', 'unit')).strip()
            product.conversion_factor = Decimal(str(row.get('معامل التحويل', '1')))
            
            # الأسعار
            product.purchase_price = Decimal(str(row.get('سعر الشراء', '0')))
            product.cost = product.purchase_price
            product.price = product.cost
            
            # الحد الأدنى للمخزون
            if not pd.isna(row.get('الحد الأدنى للمخزون')):
                product.min_stock = int(row.get('الحد الأدنى للمخزون'))
            
            # الباركود (اختياري)
            if not pd.isna(row.get('الباركود')):
                barcode = str(row.get('الباركود')).strip()
                if Product.objects.filter(barcode=barcode).exists():
                    results['errors'].append({
                        'row': index + 2,
                        'error': f'الباركود "{barcode}" مستخدم بالفعل'
                    })
                    continue
                product.barcode = barcode
                product.manual_barcode = True
            
            # الوصف
            if not pd.isna(row.get('الوصف')):
                product.description = str(row.get('الوصف')).strip()
            
            # حفظ المنتج
            product.save()
            
            # إضافة سعر المورد إذا كان موجوداً
            if not pd.isna(row.get('المورد')):
                supplier_name = str(row.get('المورد')).strip()
                supplier = Supplier.objects.filter(name__icontains=supplier_name).first()
                if supplier:
                    SupplierProductPrice.objects.create(
                        product=product,
                        supplier=supplier,
                        cost=product.purchase_price,
                        purchase_unit=product.purchase_uom,
                        conversion_to_base=product.conversion_factor,
                        is_active=True
                    )
            
            results['success'].append({
                'row': index + 2,
                'product': product,
                'name': product.name,
                'sku': product.sku
            })
            
        except Exception as e:
            results['errors'].append({
                'row': index + 2,
                'error': str(e)
            })
    
    return results


@login_required
def download_import_template(request):
    """تحميل قالب Excel للاستيراد"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from django.http import HttpResponse
        
        # إنشاء ملف Excel جديد
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "قالب المنتجات"
        
        # العناوين
        headers = [
            'اسم المنتج',
            'SKU',
            'نوع المنتج',
            'نوع المادة الخام',
            'الفئة',
            'وحدة الشراء',
            'وحدة الاستخدام',
            'معامل التحويل',
            'سعر الشراء',
            'الحد الأدنى للمخزون',
            'المورد',
            'الباركود',
            'الوصف'
        ]
        
        # تنسيق العناوين
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # إضافة صف مثال
        example_data = [
            'إسفنج مضغوط 20 كثافة',
            '',  # سيتم توليده تلقائياً
            'raw_material',
            'foam',
            'إسفنج',
            'roll',
            'm2',
            '60',
            '150.50',
            '10',
            'صفا فوم',
            '',  # اختياري
            'إسفنج مضغوط عالي الجودة'
        ]
        
        for col_num, value in enumerate(example_data, 1):
            ws.cell(row=2, column=col_num, value=value)
        
        # ضبط عرض الأعمدة
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
        
        # إنشاء ورقة التعليمات
        ws_instructions = wb.create_sheet("التعليمات")
        instructions = [
            ['قالب استيراد المنتجات - تعليمات الاستخدام'],
            [''],
            ['الحقول المطلوبة:'],
            ['• اسم المنتج: (مطلوب) اسم المنتج أو المادة الخام'],
            [''],
            ['الحقول الاختيارية:'],
            ['• SKU: رمز المنتج (سيتم توليده تلقائياً إذا ترك فارغاً)'],
            ['• نوع المنتج: raw_material, finished, semi_finished, accessory'],
            ['• نوع المادة الخام: foam, fabric, spring, wood, metal, chemical, packaging, other'],
            ['• الفئة: اسم الفئة (يجب أن تكون موجودة في النظام)'],
            ['• وحدة الشراء: unit, kg, m, m2, m3, roll, sheet, box, etc.'],
            ['• وحدة الاستخدام: unit, kg, m, m2, m3, piece, etc.'],
            ['• معامل التحويل: عدد وحدات الاستخدام في وحدة الشراء'],
            ['• سعر الشراء: سعر شراء وحدة الشراء'],
            ['• الحد الأدنى للمخزون: عدد صحيح'],
            ['• المورد: اسم المورد (يجب أن يكون موجوداً في النظام)'],
            ['• الباركود: رقم الباركود (اختياري)'],
            ['• الوصف: وصف المنتج'],
            [''],
            ['ملاحظات:'],
            ['• احذف صف المثال قبل رفع الملف'],
            ['• تأكد من أن الفئات والموردين موجودة في النظام'],
            ['• سيتم تجاهل الصفوف التي تحتوي على أخطاء'],
            ['• يمكنك استيراد آلاف المنتجات دفعة واحدة'],
        ]
        
        for row_num, instruction in enumerate(instructions, 1):
            ws_instructions.cell(row=row_num, column=1, value=instruction[0])
            if row_num == 1:
                ws_instructions.cell(row=row_num, column=1).font = Font(bold=True, size=14)
        
        ws_instructions.column_dimensions['A'].width = 80
        
        # حفظ الملف وإرساله
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=product_import_template.xlsx'
        wb.save(response)
        
        return response
        
    except Exception as e:
        messages.error(request, f'خطأ في إنشاء القالب: {str(e)}')
        return redirect('inventory:bulk_import_products')


# ========== قوالب المنتجات (Product Templates) ==========
@login_required
def product_template_list(request):
    """قائمة قوالب المنتجات"""
    from inventory.models import ProductTemplate
    
    templates = ProductTemplate.objects.all().select_related('category', 'created_by').order_by('-created_at')
    
    return render(request, 'inventory/product_template_list.html', {
        'title': 'قوالب المنتجات',
        'templates': templates
    })


@login_required
def product_template_create(request):
    """إنشاء قالب منتج جديد"""
    from inventory.models import ProductTemplate
    
    if request.method == 'POST':
        try:
            template = ProductTemplate()
            template.name = request.POST.get('name', '').strip()
            template.product_type = request.POST.get('product_type', 'raw_material')
            template.raw_material_type = request.POST.get('raw_material_type', '')
            
            category_id = request.POST.get('category')
            if category_id:
                template.category = Category.objects.get(pk=int(category_id))
            
            template.purchase_uom = request.POST.get('purchase_uom', 'unit')
            template.usage_uom = request.POST.get('usage_uom', 'unit')
            template.conversion_factor = Decimal(request.POST.get('conversion_factor', '1'))
            template.purchase_price = Decimal(request.POST.get('purchase_price', '0'))
            template.min_stock = int(request.POST.get('min_stock', '0'))
            template.auto_calculate_conversion = request.POST.get('auto_calculate_conversion') == 'on'
            
            if template.auto_calculate_conversion:
                length_val = request.POST.get('length', '').strip()
                width_val = request.POST.get('width', '').strip()
                height_val = request.POST.get('height', '').strip()
                
                if length_val:
                    template.length = Decimal(length_val)
                if width_val:
                    template.width = Decimal(width_val)
                if height_val:
                    template.height = Decimal(height_val)
            
            template.notes = request.POST.get('notes', '')
            template.created_by = request.user
            template.save()
            
            messages.success(request, f'✅ تم إنشاء القالب "{template.name}" بنجاح')
            return redirect('inventory:product_template_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء القالب: {str(e)}')
    
    return render(request, 'inventory/product_template_form.html', {
        'title': 'إنشاء قالب منتج جديد',
        'categories': Category.objects.filter(is_active=True).order_by('sort_order', 'name'),
    })


@login_required
def product_template_edit(request, pk):
    """تعديل قالب منتج"""
    from inventory.models import ProductTemplate
    
    template = get_object_or_404(ProductTemplate, pk=pk)
    
    if request.method == 'POST':
        try:
            template.name = request.POST.get('name', '').strip()
            template.product_type = request.POST.get('product_type', 'raw_material')
            template.raw_material_type = request.POST.get('raw_material_type', '')
            
            category_id = request.POST.get('category')
            if category_id:
                template.category = Category.objects.get(pk=int(category_id))
            else:
                template.category = None
            
            template.purchase_uom = request.POST.get('purchase_uom', 'unit')
            template.usage_uom = request.POST.get('usage_uom', 'unit')
            template.conversion_factor = Decimal(request.POST.get('conversion_factor', '1'))
            template.purchase_price = Decimal(request.POST.get('purchase_price', '0'))
            template.min_stock = int(request.POST.get('min_stock', '0'))
            template.auto_calculate_conversion = request.POST.get('auto_calculate_conversion') == 'on'
            
            if template.auto_calculate_conversion:
                length_val = request.POST.get('length', '').strip()
                width_val = request.POST.get('width', '').strip()
                height_val = request.POST.get('height', '').strip()
                
                template.length = Decimal(length_val) if length_val else None
                template.width = Decimal(width_val) if width_val else None
                template.height = Decimal(height_val) if height_val else None
            else:
                template.length = None
                template.width = None
                template.height = None
            
            template.notes = request.POST.get('notes', '')
            template.save()
            
            messages.success(request, f'✅ تم تحديث القالب "{template.name}" بنجاح')
            return redirect('inventory:product_template_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في تحديث القالب: {str(e)}')
    
    return render(request, 'inventory/product_template_form.html', {
        'title': f'تعديل القالب: {template.name}',
        'template': template,
        'categories': Category.objects.filter(is_active=True).order_by('sort_order', 'name'),
    })


@login_required
def product_template_delete(request, pk):
    """حذف قالب منتج"""
    from inventory.models import ProductTemplate
    
    template = get_object_or_404(ProductTemplate, pk=pk)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f'✅ تم حذف القالب "{template_name}" بنجاح')
        return redirect('inventory:product_template_list')
    
    return render(request, 'inventory/product_template_confirm_delete.html', {
        'title': 'تأكيد حذف القالب',
        'template': template
    })


@login_required
def product_add_from_template(request, template_id):
    """إضافة منتج جديد من قالب"""
    from inventory.models import ProductTemplate
    
    template = get_object_or_404(ProductTemplate, pk=template_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'✅ تم إضافة المنتج "{product.name}" من القالب "{template.name}" بنجاح')
            return redirect('inventory:product_detail', pk=product.id)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء أدناه')
    else:
        # ملء البيانات من القالب
        initial_data = {
            'product_type': template.product_type,
            'raw_material_type': template.raw_material_type,
            'category': template.category,
            'purchase_uom': template.purchase_uom,
            'usage_uom': template.usage_uom,
            'conversion_factor': template.conversion_factor,
            'purchase_price': template.purchase_price,
            'cost': template.purchase_price,
            'price': template.purchase_price,
            'min_stock': template.min_stock,
            'auto_calculate_conversion': template.auto_calculate_conversion,
            'length': template.length,
            'width': template.width,
            'height': template.height,
        }
        form = ProductForm(initial=initial_data)
    
    return render(request, 'inventory/product_form.html', {
        'title': f'إضافة منتج من القالب: {template.name}',
        'form': form,
        'template': template,
        'locations': Location.objects.filter(is_active=True).order_by('code', 'name'),
        'categories': Category.objects.filter(is_active=True).select_related('parent').order_by('sort_order', 'name'),
    })


@login_required
def save_product_as_template(request, pk):
    """حفظ منتج موجود كقالب"""
    from inventory.models import ProductTemplate
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        template_name = request.POST.get('template_name', '').strip()
        if not template_name:
            messages.error(request, 'يجب إدخال اسم للقالب')
            return redirect('inventory:product_detail', pk=pk)
        
        try:
            template = ProductTemplate.objects.create(
                name=template_name,
                product_type=product.product_type,
                raw_material_type=product.raw_material_type,
                category=product.category,
                purchase_uom=product.purchase_uom,
                usage_uom=product.usage_uom,
                conversion_factor=product.conversion_factor,
                purchase_price=product.purchase_price,
                min_stock=product.min_stock,
                auto_calculate_conversion=product.auto_calculate_conversion,
                length=product.length,
                width=product.width,
                height=product.height,
                notes=product.notes,
                created_by=request.user
            )
            
            messages.success(request, f'✅ تم حفظ المنتج "{product.name}" كقالب "{template.name}" بنجاح')
            return redirect('inventory:product_template_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في حفظ القالب: {str(e)}')
            return redirect('inventory:product_detail', pk=pk)
    
    return render(request, 'inventory/save_as_template.html', {
        'title': 'حفظ كقالب',
        'product': product
    })
