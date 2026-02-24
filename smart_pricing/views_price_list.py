"""
Views for Price List System
واجهات نظام قوائم الأسعار
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from decimal import Decimal
import json

from .models_price_list import (
    ProductSize, ProductFamily, ProductVariant,
    CostCategory, VariantCostBreakdown, OverheadCostSetting,
    PriceList, ProductVariantPrice, PriceListExport, PriceListSettings
)
from .services_price_list import CostCalculationService, PriceListService, TaxCalculationService
from .export_service import PriceListExporter, export_all_price_lists


# ============ لوحة التحكم ============

@login_required
def price_list_dashboard(request):
    """لوحة تحكم قوائم الأسعار"""
    
    # إحصائيات
    stats = {
        'families_count': ProductFamily.objects.filter(is_active=True).count(),
        'sizes_count': ProductSize.objects.filter(is_active=True).count(),
        'price_lists_count': PriceList.objects.filter(is_active=True).count(),
        'variants_count': ProductVariant.objects.filter(is_active=True).count(),
    }
    
    # أحدث قوائم الأسعار
    recent_price_lists = PriceList.objects.filter(is_active=True).order_by('-updated_at')[:5]
    
    # أحدث التصديرات
    recent_exports = PriceListExport.objects.order_by('-generated_at')[:5]
    
    # عائلات تحتاج تحديث (بدون أسعار)
    families_without_prices = ProductFamily.objects.filter(
        is_active=True,
        base_price=0
    ).count()
    
    context = {
        'title': 'لوحة تحكم قوائم الأسعار',
        'stats': stats,
        'recent_price_lists': recent_price_lists,
        'recent_exports': recent_exports,
        'families_without_prices': families_without_prices,
    }
    
    return render(request, 'smart_pricing/price_list/dashboard.html', context)


# ============ إدارة المقاسات ============

@login_required
def sizes_list(request):
    """قائمة المقاسات"""
    sizes = ProductSize.objects.all().order_by('sort_order', 'width', 'length')
    
    context = {
        'title': 'المقاسات',
        'sizes': sizes,
    }
    
    return render(request, 'smart_pricing/price_list/sizes_list.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def size_create(request):
    """إنشاء مقاس جديد"""
    if request.method == 'POST':
        try:
            size = ProductSize.objects.create(
                width=int(request.POST.get('width')),
                length=int(request.POST.get('length')),
                height=int(request.POST.get('height')) if request.POST.get('height') else None,
                price_multiplier=Decimal(request.POST.get('price_multiplier', '1')),
                cost_multiplier=Decimal(request.POST.get('cost_multiplier', '1')),
                sort_order=int(request.POST.get('sort_order', 0)),
            )
            messages.success(request, f'تم إنشاء المقاس {size} بنجاح')
            return redirect('smart_pricing:sizes_list')
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'title': 'إضافة مقاس جديد',
    }
    
    return render(request, 'smart_pricing/price_list/size_form.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def size_edit(request, size_id):
    """تعديل مقاس"""
    size = get_object_or_404(ProductSize, id=size_id)
    size_display = f"{size.width}×{size.length}"
    
    if request.method == 'POST':
        try:
            size.width = int(request.POST.get('width'))
            size.length = int(request.POST.get('length'))
            size.height = int(request.POST.get('height')) if request.POST.get('height') else None
            size.price_multiplier = Decimal(request.POST.get('price_multiplier') or '1')
            size.cost_multiplier = Decimal(request.POST.get('cost_multiplier') or '1')
            size.sort_order = int(request.POST.get('sort_order') or 0)
            size.is_active = request.POST.get('is_active') == 'on'
            size.save()
            
            messages.success(request, f'تم تحديث المقاس {size.width}×{size.length} بنجاح')
            return redirect('smart_pricing:sizes_list')
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'title': f'تعديل المقاس {size_display}',
        'size': size,
    }
    
    return render(request, 'smart_pricing/price_list/size_form.html', context)


@login_required
@require_POST
def size_delete(request, size_id):
    """حذف مقاس"""
    size = get_object_or_404(ProductSize, id=size_id)
    size_name = str(size)
    
    try:
        size.delete()
        messages.success(request, f'تم حذف المقاس {size_name} بنجاح')
    except Exception as e:
        messages.error(request, f'لا يمكن حذف المقاس: {str(e)}')
    
    return redirect('smart_pricing:sizes_list')


@login_required
@require_POST
def bulk_create_sizes(request):
    """إنشاء مقاسات متعددة"""
    # مقاسات المراتب الشائعة
    common_sizes = [
        (90, 190), (90, 195), (90, 200),
        (100, 190), (100, 195), (100, 200),
        (120, 190), (120, 195), (120, 200),
        (140, 190), (140, 195), (140, 200),
        (150, 190), (150, 195), (150, 200),
        (160, 190), (160, 195), (160, 200),
        (175, 190), (175, 195), (175, 200),
        (180, 190), (180, 195), (180, 200),
        (190, 190), (190, 195), (190, 200),
        (200, 200), (200, 210),
    ]
    
    created = 0
    # حساب معامل السعر بناءً على المساحة (90×190 كمرجع)
    base_area = 90 * 190
    
    for width, length in common_sizes:
        size, was_created = ProductSize.objects.get_or_create(
            width=width,
            length=length,
            defaults={
                'price_multiplier': Decimal(str(round((width * length) / base_area, 3))),
                'cost_multiplier': Decimal(str(round((width * length) / base_area, 3))),
            }
        )
        if was_created:
            created += 1
    
    messages.success(request, f'تم إنشاء {created} مقاس جديد')
    return redirect('smart_pricing:sizes_list')


# ============ إدارة عائلات المنتجات ============

@login_required
def families_list(request):
    """قائمة عائلات المنتجات"""
    from inventory.models import Category
    
    families = ProductFamily.objects.filter(is_active=True).annotate(
        sizes_count=Count('available_sizes')
    ).order_by('sort_order', 'name')
    
    # الفلترة
    category = request.GET.get('category')
    if category:
        families = families.filter(category_id=category)
    
    search = request.GET.get('q')
    if search:
        families = families.filter(Q(name__icontains=search) | Q(code__icontains=search))
    
    # الترقيم
    paginator = Paginator(families, 20)
    page = request.GET.get('page', 1)
    families = paginator.get_page(page)
    
    # جلب الفئات للفلترة
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    context = {
        'title': 'عائلات المنتجات',
        'families': families,
        'categories': categories,
    }
    
    return render(request, 'smart_pricing/price_list/families_list.html', context)


@login_required
@require_http_methods(['GET'])
def generate_family_code(request):
    """توليد كود فريد لعائلة المنتجات"""
    code = ProductFamily.generate_unique_code()
    return JsonResponse({'code': code})


@login_required
@require_http_methods(['GET', 'POST'])
def family_create(request):
    """إنشاء عائلة منتجات جديدة"""
    from inventory.models import Product, Category
    
    if request.method == 'POST':
        try:
            # الكود - إذا كان فارغاً سيتم توليده تلقائياً
            code = request.POST.get('code', '').strip() or None
            
            family = ProductFamily.objects.create(
                code=code,
                name=request.POST.get('name'),
                name_en=request.POST.get('name_en', ''),
                description=request.POST.get('description', ''),
                base_price=Decimal(request.POST.get('base_price', '0')),
                base_cost=Decimal(request.POST.get('base_cost', '0')),
                default_height=int(request.POST.get('default_height', '30')),
                created_by=request.user,
            )
            
            # ربط بمنتج من المخزون
            base_product_id = request.POST.get('base_product')
            if base_product_id:
                family.base_product_id = base_product_id
                family.save()
            
            # إضافة المقاسات
            size_ids = request.POST.getlist('sizes')
            if size_ids:
                family.available_sizes.set(size_ids)
            
            # إنشاء منتجات تامة في المخزون لكل مقاس
            create_products = request.POST.get('create_finished_products') == 'on'
            products_created = 0
            
            if create_products and size_ids:
                # الحصول على المقاسات المحددة
                selected_sizes = ProductSize.objects.filter(id__in=size_ids)
                
                # الحصول على المخزن المحدد
                from inventory.models import Stock, Location
                location_id = request.POST.get('product_location')
                selected_location = None
                if location_id:
                    selected_location = Location.objects.filter(id=location_id).first()
                
                # إذا لم يتم اختيار مخزن، نحاول إيجاد المخزن الافتراضي
                if not selected_location:
                    selected_location = Location.objects.filter(is_default=True).first()
                    if not selected_location:
                        selected_location = Location.objects.filter(is_active=True).first()
                
                # البحث عن أو إنشاء فئة "منتجات تامة"
                finished_category = None
                category_id = request.POST.get('product_category')
                if category_id:
                    finished_category = Category.objects.filter(id=category_id).first()
                
                if not finished_category:
                    finished_category, _ = Category.objects.get_or_create(
                        name='منتجات تامة',
                        defaults={'description': 'منتجات تامة الصنع'}
                    )
                
                # الحصول على قائمة الأسعار الافتراضية (إن وجدت)
                default_price_list = PriceList.objects.filter(is_default=True).first()
                if not default_price_list:
                    default_price_list = PriceList.objects.filter(is_active=True).first()
                
                for size in selected_sizes:
                    # حساب السعر والتكلفة لهذا المقاس
                    price = family.base_price * size.price_multiplier
                    cost = family.base_cost * size.cost_multiplier
                    
                    # إنشاء SKU فريد للمنتج
                    product_sku = f"{family.code}-{size.width}x{size.length}"
                    if size.height:
                        product_sku += f"x{size.height}"
                    
                    # إنشاء اسم المنتج
                    product_name = f"{family.name} {size}"
                    product_name_en = f"{family.name_en} {size}" if family.name_en else product_name
                    
                    # التحقق من عدم وجود منتج بنفس الـ SKU
                    existing_product = Product.objects.filter(sku=product_sku).first()
                    
                    if existing_product:
                        # تحديث المنتج الموجود
                        existing_product.name = product_name
                        existing_product.price = price
                        existing_product.cost = cost
                        existing_product.width = size.width
                        existing_product.length = size.length
                        existing_product.height = size.height or family.default_height
                        existing_product.category = finished_category
                        existing_product.product_type = 'finished'
                        existing_product.description = family.description
                        existing_product.save()
                        product = existing_product
                    else:
                        # إنشاء internal_code فريد
                        internal_code = f"INT{product_sku}"
                        counter = 1
                        base_internal_code = internal_code
                        while Product.objects.filter(internal_code=internal_code).exists():
                            internal_code = f"{base_internal_code}-{counter}"
                            counter += 1
                        
                        # إنشاء منتج جديد
                        product = Product.objects.create(
                            sku=product_sku,
                            name=product_name,
                            description=family.description,
                            price=price,
                            cost=cost,
                            category=finished_category,
                            product_type='finished',
                            width=size.width,
                            length=size.length,
                            height=size.height or family.default_height,
                            internal_code=internal_code,
                        )
                        products_created += 1
                    
                    # إنشاء سجل المخزون في المخزن المحدد
                    if selected_location:
                        Stock.objects.get_or_create(
                            product=product,
                            location=selected_location,
                            defaults={'quantity': 0}
                        )
                    
                    # إنشاء أو تحديث نسخة المنتج (ProductVariant)
                    variant, variant_created = ProductVariant.objects.get_or_create(
                        family=family,
                        size=size,
                        defaults={
                            'product': product,
                            'sku': product_sku,
                            'is_active': True,
                        }
                    )
                    
                    if not variant_created and not variant.product:
                        variant.product = product
                        variant.save(update_fields=['product'])
                    
                    # إنشاء أسعار للمنتج في قوائم الأسعار النشطة
                    for price_list in PriceList.objects.filter(is_active=True):
                        calculated_price = price_list.apply_discount(price)
                        ProductVariantPrice.objects.get_or_create(
                            family=family,
                            size=size,
                            price_list=price_list,
                            defaults={
                                'custom_price': None,  # استخدام السعر المحسوب
                                'is_active': True,
                            }
                        )
                
                if products_created > 0:
                    messages.success(request, f'تم إنشاء {products_created} منتج تام في المخزون')
            
            messages.success(request, f'تم إنشاء العائلة {family.name} بنجاح')
            return redirect('smart_pricing:family_detail', family_id=family.id)
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    sizes = ProductSize.objects.filter(is_active=True).order_by('sort_order')
    products = Product.objects.all().order_by('name')[:200]
    
    # جلب الفئات للاختيار
    from inventory.models import Category, Location
    categories = Category.objects.filter(is_active=True).order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('name')
    
    context = {
        'title': 'إضافة عائلة منتجات',
        'sizes': sizes,
        'products': products,
        'categories': categories,
        'locations': locations,
    }
    
    return render(request, 'smart_pricing/price_list/family_form.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def family_edit(request, family_id):
    """تعديل عائلة منتجات"""
    from inventory.models import Product, Category, Location
    
    family = get_object_or_404(ProductFamily, id=family_id)
    
    if request.method == 'POST':
        try:
            # تحديث البيانات الأساسية
            family.name = request.POST.get('name', family.name)
            family.name_en = request.POST.get('name_en', '')
            family.description = request.POST.get('description', '')
            family.base_price = Decimal(request.POST.get('base_price', '0'))
            family.base_cost = Decimal(request.POST.get('base_cost', '0'))
            family.default_height = int(request.POST.get('default_height', '30'))
            
            # تحديث الفئة
            category_id = request.POST.get('product_category')
            if category_id:
                family.category_id = category_id
            
            # ربط بمنتج من المخزون
            base_product_id = request.POST.get('base_product')
            if base_product_id:
                family.base_product_id = base_product_id
            else:
                family.base_product = None
            
            family.save()
            
            # تحديث المقاسات
            size_ids = request.POST.getlist('sizes')
            if size_ids:
                family.available_sizes.set(size_ids)
            
            messages.success(request, f'تم تحديث العائلة {family.name} بنجاح')
            return redirect('smart_pricing:family_detail', family_id=family.id)
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    sizes = ProductSize.objects.filter(is_active=True).order_by('sort_order')
    products = Product.objects.all().order_by('name')[:200]
    categories = Category.objects.filter(is_active=True).order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('name')
    
    # المقاسات المحددة حالياً
    selected_size_ids = list(family.available_sizes.values_list('id', flat=True))
    
    context = {
        'title': f'تعديل العائلة: {family.name}',
        'family': family,
        'sizes': sizes,
        'products': products,
        'categories': categories,
        'locations': locations,
        'selected_size_ids': selected_size_ids,
        'is_edit': True,
    }
    
    return render(request, 'smart_pricing/price_list/family_form.html', context)


@login_required
def family_detail(request, family_id):
    """تفاصيل عائلة المنتجات"""
    family = get_object_or_404(ProductFamily, id=family_id)
    
    # النسخ والأسعار
    variants = ProductVariant.objects.filter(family=family).select_related('size')
    
    # قوائم الأسعار
    price_lists = PriceList.objects.filter(is_active=True)
    
    # مصفوفة الأسعار
    price_matrix = []
    for size in family.available_sizes.all().order_by('sort_order'):
        row = {
            'size': size,
            'cost': family.get_cost_for_size(size),
            'prices': {}
        }
        
        for pl in price_lists:
            row['prices'][pl.code] = family.get_price_for_size(size, pl)
        
        price_matrix.append(row)
    
    # حساب هامش الربح الصحيح
    profit_margin = 0
    if family.base_cost > 0:
        profit_margin = ((family.base_price - family.base_cost) / family.base_cost) * 100
    
    context = {
        'title': f'عائلة: {family.name}',
        'family': family,
        'variants': variants,
        'price_lists': price_lists,
        'price_matrix': price_matrix,
        'profit_margin': profit_margin,
    }
    
    return render(request, 'smart_pricing/price_list/family_detail.html', context)


@login_required
@require_POST
def family_delete(request, family_id):
    """حذف عائلة منتجات"""
    family = get_object_or_404(ProductFamily, id=family_id)
    family_name = family.name
    
    try:
        # حذف العائلة (سيتم حذف المتغيرات والأسعار المرتبطة تلقائياً بسبب CASCADE)
        family.delete()
        messages.success(request, f'تم حذف العائلة "{family_name}" بنجاح')
    except Exception as e:
        messages.error(request, f'خطأ في حذف العائلة: {str(e)}')
    
    return redirect('smart_pricing:families_list')


@login_required
def family_update_prices(request, family_id):
    """تحديث أسعار عائلة"""
    family = get_object_or_404(ProductFamily, id=family_id)
    
    # إذا كان الطلب GET، توجيه إلى صفحة تفاصيل العائلة
    if request.method == 'GET':
        return redirect('smart_pricing:family_detail', family_id=family_id)
    
    # تحديث السعر الأساسي
    base_price = request.POST.get('base_price')
    if base_price:
        family.base_price = Decimal(base_price)
    
    # تحديث الارتفاع
    default_height = request.POST.get('default_height')
    if default_height:
        family.default_height = int(default_height)
    
    family.save()
    
    # تحديث الأسعار المخصصة
    for key, value in request.POST.items():
        if key.startswith('price_'):
            parts = key.split('_')
            if len(parts) == 3:
                size_id = parts[1]
                price_list_code = parts[2]
                
                try:
                    size = ProductSize.objects.get(id=size_id)
                    price_list = PriceList.objects.get(code=price_list_code)
                    
                    vp, _ = ProductVariantPrice.objects.get_or_create(
                        family=family,
                        size=size,
                        price_list=price_list
                    )
                    
                    if value:
                        vp.custom_price = Decimal(value)
                    else:
                        vp.custom_price = None
                    vp.save()
                except:
                    pass
    
    messages.success(request, 'تم تحديث الأسعار بنجاح')
    return redirect('smart_pricing:family_detail', family_id=family_id)


@login_required
@require_POST
def sync_family_to_inventory(request, family_id):
    """
    مزامنة عائلة منتجات مع المخزون
    إنشاء منتجات تامة لكل مقاس في العائلة
    """
    from inventory.models import Product, Category, Stock, Location
    
    family = get_object_or_404(ProductFamily, id=family_id)
    
    try:
        # الحصول على المقاسات المتاحة
        available_sizes = family.available_sizes.all()
        
        if not available_sizes.exists():
            messages.warning(request, 'لا توجد مقاسات محددة لهذه العائلة')
            return redirect('smart_pricing:family_detail', family_id=family_id)
        
        # البحث عن أو إنشاء فئة "منتجات تامة"
        finished_category, _ = Category.objects.get_or_create(
            name='منتجات تامة',
            defaults={'description': 'منتجات تامة الصنع'}
        )
        
        # إذا كانت العائلة مرتبطة بمنتج له فئة، استخدم نفس الفئة
        if family.base_product and family.base_product.category:
            finished_category = family.base_product.category
        elif family.category:
            finished_category = family.category
        
        products_created = 0
        products_updated = 0
        
        for size in available_sizes:
            # حساب السعر والتكلفة لهذا المقاس
            price = family.base_price * size.price_multiplier
            cost = family.base_cost * size.cost_multiplier
            
            # إنشاء SKU فريد للمنتج
            product_sku = f"{family.code}-{size.width}x{size.length}"
            if size.height:
                product_sku += f"x{size.height}"
            
            # إنشاء اسم المنتج
            product_name = f"{family.name} {size}"
            
            # التحقق من عدم وجود منتج بنفس الـ SKU
            existing_product = Product.objects.filter(sku=product_sku).first()
            
            if existing_product:
                # تحديث المنتج الموجود
                existing_product.name = product_name
                existing_product.price = price
                existing_product.cost = cost
                existing_product.width = size.width
                existing_product.length = size.length
                existing_product.height = size.height or family.default_height
                existing_product.category = finished_category
                existing_product.product_type = 'finished'
                existing_product.description = family.description
                existing_product.save()
                product = existing_product
                products_updated += 1
            else:
                # إنشاء internal_code فريد
                internal_code = f"INT{product_sku}"
                # التأكد من أن internal_code فريد
                counter = 1
                base_internal_code = internal_code
                while Product.objects.filter(internal_code=internal_code).exists():
                    internal_code = f"{base_internal_code}-{counter}"
                    counter += 1
                
                # إنشاء منتج جديد
                product = Product.objects.create(
                    sku=product_sku,
                    name=product_name,
                    description=family.description,
                    price=price,
                    cost=cost,
                    category=finished_category,
                    product_type='finished',
                    width=size.width,
                    length=size.length,
                    height=size.height or family.default_height,
                    internal_code=internal_code,
                )
                products_created += 1
                
                # إنشاء سجل مخزون في مخزن المنتجات التامة
                finished_location = Location.objects.filter(
                    type='finished', is_active=True
                ).first()
                if finished_location:
                    Stock.objects.get_or_create(
                        product=product,
                        location=finished_location,
                        defaults={'quantity': 0}
                    )
            
            # إنشاء أو تحديث نسخة المنتج (ProductVariant)
            variant, variant_created = ProductVariant.objects.get_or_create(
                family=family,
                size=size,
                defaults={
                    'product': product,
                    'sku': product_sku,
                    'is_active': True,
                }
            )
            
            if not variant_created:
                variant.product = product
                variant.sku = product_sku
                variant.save(update_fields=['product', 'sku'])
            
            # إنشاء أسعار للمنتج في قوائم الأسعار النشطة
            for price_list in PriceList.objects.filter(is_active=True):
                ProductVariantPrice.objects.get_or_create(
                    family=family,
                    size=size,
                    price_list=price_list,
                    defaults={
                        'custom_price': None,
                        'is_active': True,
                    }
                )
        
        if products_created > 0 or products_updated > 0:
            msg = f'تم مزامنة العائلة "{family.name}" مع المخزون: '
            if products_created > 0:
                msg += f'{products_created} منتج جديد'
            if products_updated > 0:
                if products_created > 0:
                    msg += f'، '
                msg += f'{products_updated} منتج محدث'
            messages.success(request, msg)
        else:
            messages.info(request, 'جميع المنتجات موجودة بالفعل')
            
    except Exception as e:
        messages.error(request, f'خطأ في المزامنة: {str(e)}')
    
    return redirect('smart_pricing:family_detail', family_id=family_id)


@login_required
@require_POST
def sync_all_families_to_inventory(request):
    """
    مزامنة جميع العائلات مع المخزون
    """
    from inventory.models import Product, Category, Stock, Location
    
    try:
        families = ProductFamily.objects.filter(is_active=True)
        total_created = 0
        total_updated = 0
        
        # البحث عن مخزن المنتجات التامة
        finished_location = Location.objects.filter(
            type='finished', is_active=True
        ).first()
        
        # البحث عن أو إنشاء فئة "منتجات تامة"
        finished_category, _ = Category.objects.get_or_create(
            name='منتجات تامة',
            defaults={'description': 'منتجات تامة الصنع'}
        )
        
        for family in families:
            available_sizes = family.available_sizes.all()
            
            # استخدام فئة العائلة إن وجدت
            category = family.category or finished_category
            
            for size in available_sizes:
                price = family.base_price * size.price_multiplier
                cost = family.base_cost * size.cost_multiplier
                
                product_sku = f"{family.code}-{size.width}x{size.length}"
                if size.height:
                    product_sku += f"x{size.height}"
                
                product_name = f"{family.name} {size}"
                
                existing_product = Product.objects.filter(sku=product_sku).first()
                
                if existing_product:
                    existing_product.name = product_name
                    existing_product.price = price
                    existing_product.cost = cost
                    existing_product.width = size.width
                    existing_product.length = size.length
                    existing_product.height = size.height or family.default_height
                    existing_product.category = category
                    existing_product.product_type = 'finished'
                    existing_product.save()
                    product = existing_product
                    total_updated += 1
                else:
                    # إنشاء internal_code فريد
                    internal_code = f"INT{product_sku}"
                    counter = 1
                    base_internal_code = internal_code
                    while Product.objects.filter(internal_code=internal_code).exists():
                        internal_code = f"{base_internal_code}-{counter}"
                        counter += 1
                    
                    product = Product.objects.create(
                        sku=product_sku,
                        name=product_name,
                        description=family.description,
                        price=price,
                        cost=cost,
                        category=category,
                        product_type='finished',
                        width=size.width,
                        length=size.length,
                        height=size.height or family.default_height,
                        internal_code=internal_code,
                    )
                    total_created += 1
                    
                    # إنشاء سجل مخزون في مخزن المنتجات التامة
                    if finished_location:
                        Stock.objects.get_or_create(
                            product=product,
                            location=finished_location,
                            defaults={'quantity': 0}
                        )
                
                # نسخة المنتج
                variant, _ = ProductVariant.objects.get_or_create(
                    family=family,
                    size=size,
                    defaults={'product': product, 'sku': product_sku, 'is_active': True}
                )
                if variant.product != product:
                    variant.product = product
                    variant.save(update_fields=['product'])
                
                # أسعار
                for price_list in PriceList.objects.filter(is_active=True):
                    ProductVariantPrice.objects.get_or_create(
                        family=family,
                        size=size,
                        price_list=price_list,
                        defaults={'is_active': True}
                    )
        
        messages.success(request, f'تم مزامنة جميع العائلات: {total_created} منتج جديد، {total_updated} منتج محدث')
        
    except Exception as e:
        messages.error(request, f'خطأ في المزامنة: {str(e)}')
    
    return redirect('smart_pricing:families_list')


# ============ إدارة قوائم الأسعار ============

@login_required
def price_lists_list(request):
    """قائمة قوائم الأسعار"""
    price_lists = PriceList.objects.all().order_by('name')
    
    context = {
        'title': 'قوائم الأسعار',
        'price_lists': price_lists,
    }
    
    return render(request, 'smart_pricing/price_list/price_lists.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def price_list_create(request):
    """إنشاء قائمة أسعار جديدة"""
    if request.method == 'POST':
        try:
            price_list = PriceList.objects.create(
                code=request.POST.get('code'),
                name=request.POST.get('name'),
                name_en=request.POST.get('name_en', ''),
                list_type=request.POST.get('list_type', 'retail'),
                description=request.POST.get('description', ''),
                discount_percentage=Decimal(request.POST.get('discount_percentage', '0')),
                includes_tax=request.POST.get('includes_tax') == 'on',
                tax_rate=Decimal(request.POST.get('tax_rate', '15')),
                created_by=request.user,
            )
            
            messages.success(request, f'تم إنشاء قائمة الأسعار {price_list.name} بنجاح')
            return redirect('smart_pricing:price_list_view', price_list_id=price_list.id)
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'title': 'إضافة قائمة أسعار',
        'list_types': PriceList.PRICE_LIST_TYPE_CHOICES,
    }
    
    return render(request, 'smart_pricing/price_list/price_list_form.html', context)


@login_required
def price_list_view(request, price_list_id):
    """عرض قائمة أسعار"""
    price_list = get_object_or_404(PriceList, id=price_list_id)
    
    # توليد المصفوفة
    price_matrix = PriceListService.generate_price_matrix(price_list)
    
    # المقاسات المستخدمة
    sizes = ProductSize.objects.filter(
        is_active=True,
        product_families__show_in_price_list=True
    ).distinct().order_by('sort_order', 'width', 'length')
    
    context = {
        'title': f'قائمة الأسعار: {price_list.name}',
        'price_list': price_list,
        'price_matrix': price_matrix,
        'sizes': sizes,
    }
    
    return render(request, 'smart_pricing/price_list/price_list_view.html', context)


@login_required
def price_list_print(request, price_list_id):
    """عرض قائمة أسعار للطباعة - صفحة مستقلة بتصميم RITA"""
    price_list = get_object_or_404(PriceList, id=price_list_id)
    
    # توليد المصفوفة
    price_matrix = PriceListService.generate_price_matrix(price_list)
    
    # المقاسات المستخدمة
    sizes = ProductSize.objects.filter(
        is_active=True,
        product_families__show_in_price_list=True
    ).distinct().order_by('sort_order', 'width', 'length')
    
    context = {
        'title': f'قائمة الأسعار: {price_list.name}',
        'price_list': price_list,
        'price_matrix': price_matrix,
        'sizes': sizes,
    }
    
    return render(request, 'smart_pricing/price_list/price_list_standalone.html', context)


@login_required
def price_list_smart(request, price_list_id):
    """
    عرض قائمة أسعار ذكية - مُنظّمة حسب الارتفاع
    التصميم مثل صورة RITA الأصلية
    """
    price_list = get_object_or_404(PriceList, id=price_list_id)
    
    # جلب العائلات والمقاسات
    families = ProductFamily.objects.filter(
        is_active=True,
        show_in_price_list=True
    ).order_by('sort_order', 'name')
    
    # تجميع العرض والطول
    widths = sorted(set(ProductSize.objects.filter(is_active=True).values_list('width', flat=True)))
    lengths = sorted(set(ProductSize.objects.filter(is_active=True).values_list('length', flat=True)))
    
    # تجميع العائلات حسب الارتفاع
    height_groups = {}
    
    for family in families:
        height = family.default_height
        if height not in height_groups:
            height_groups[height] = []
        
        # جمع أسعار هذه العائلة
        prices = {}
        variant_prices = ProductVariantPrice.objects.filter(
            family=family,
            price_list=price_list,
            is_active=True
        ).select_related('size')
        
        for vp in variant_prices:
            key = f"{vp.size.width}x{vp.size.length}"
            if price_list.includes_tax:
                prices[key] = vp.final_price
            else:
                prices[key] = vp.calculated_price
        
        # إذا لم توجد أسعار محفوظة، نحسبها
        if not prices:
            for size in ProductSize.objects.filter(is_active=True):
                base_price = family.base_price * size.price_multiplier
                calculated = price_list.apply_discount(base_price)
                if price_list.includes_tax:
                    calculated = price_list.apply_tax(calculated)
                key = f"{size.width}x{size.length}"
                prices[key] = calculated
        
        height_groups[height].append({
            'code': family.code,
            'name': family.name,
            'name_en': family.name_en,
            'prices': prices,
        })
    
    # تحويل إلى قائمة مرتبة
    grouped_data = []
    for height in sorted(height_groups.keys()):
        grouped_data.append({
            'height': height,
            'products': height_groups[height],
        })
    
    context = {
        'title': f'قائمة الأسعار: {price_list.name}',
        'price_list': price_list,
        'grouped_data': grouped_data,
        'widths': widths,
        'lengths': lengths,
    }
    
    return render(request, 'smart_pricing/price_list/price_list_smart.html', context)


@login_required
def price_list_a4(request, price_list_id):
    """
    عرض قائمة أسعار بحجم A4 للطباعة
    تصميم مشابه لصورة RITA الأصلية
    """
    from datetime import date
    
    price_list = get_object_or_404(PriceList, id=price_list_id)
    
    # جلب العائلات
    families = ProductFamily.objects.filter(
        is_active=True,
        show_in_price_list=True
    ).order_by('sort_order', 'name')
    
    # العروض المتاحة
    widths = [90, 100, 120, 140, 150, 160, 180, 200]
    lengths = [190, 195, 200]
    
    # بناء بيانات المنتجات
    products = []
    
    for family in families:
        # جمع أسعار هذه العائلة - مُنظّمة حسب العرض ثم الطول
        prices_by_width = {}
        
        variant_prices = ProductVariantPrice.objects.filter(
            family=family,
            price_list=price_list,
            is_active=True
        ).select_related('size')
        
        for vp in variant_prices:
            w = str(vp.size.width)
            l = str(vp.size.length)
            
            if w not in prices_by_width:
                prices_by_width[w] = {}
            
            if price_list.includes_tax:
                prices_by_width[w][l] = vp.final_price
            else:
                prices_by_width[w][l] = vp.calculated_price
        
        # إذا لم توجد أسعار محفوظة، نحسبها
        if not prices_by_width:
            for size in ProductSize.objects.filter(is_active=True):
                w = str(size.width)
                l = str(size.length)
                
                if w not in prices_by_width:
                    prices_by_width[w] = {}
                
                base_price = family.base_price * size.price_multiplier
                calculated = price_list.apply_discount(base_price)
                if price_list.includes_tax:
                    calculated = price_list.apply_tax(calculated)
                
                prices_by_width[w][l] = calculated
        
        products.append({
            'code': family.code,
            'name': family.name,
            'name_en': family.name_en,
            'prices': prices_by_width,
        })
    
    context = {
        'title': f'قائمة الأسعار: {price_list.name}',
        'price_list': price_list,
        'products': products,
        'widths': widths,
        'lengths': lengths,
        'today': date.today().strftime('%Y/%m/%d'),
    }
    
    return render(request, 'smart_pricing/price_list/price_list_a4.html', context)


@login_required
def export_price_list(request, price_list_id):
    """تصدير قائمة أسعار"""
    price_list = get_object_or_404(PriceList, id=price_list_id)
    format_type = request.GET.get('format', 'pdf')
    
    exporter = PriceListExporter(
        price_list,
        include_tax_column=request.GET.get('tax_column', 'true') == 'true',
        show_cost=request.GET.get('show_cost', 'false') == 'true',
    )
    
    if format_type == 'excel':
        return exporter.export_to_excel()
    elif format_type == 'csv':
        return exporter.export_to_csv()
    else:
        return exporter.export_to_pdf()


@login_required
def export_all_lists(request):
    """تصدير جميع قوائم الأسعار"""
    format_type = request.GET.get('format', 'excel')
    return export_all_price_lists(format_type)


# ============ إدارة التكاليف ============

@login_required
def cost_categories_list(request):
    """قائمة فئات التكاليف"""
    categories = CostCategory.objects.all().order_by('sort_order')
    
    context = {
        'title': 'فئات التكاليف',
        'categories': categories,
    }
    
    return render(request, 'smart_pricing/price_list/cost_categories.html', context)


@login_required
def variant_cost_detail(request, variant_id):
    """تفاصيل تكلفة نسخة منتج"""
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    # حساب التكلفة
    cost_data = CostCalculationService.calculate_variant_cost(variant)
    
    # حساب الهامش لكل قائمة أسعار
    margins = []
    price_lists = PriceList.objects.filter(is_active=True)
    
    for pl in price_lists:
        price = variant.family.get_price_for_size(variant.size, pl)
        margin = CostCalculationService.calculate_margin(price, cost_data['total_cost'])
        margins.append({
            'price_list': pl,
            'price': price,
            **margin
        })
    
    context = {
        'title': f'تكلفة: {variant}',
        'variant': variant,
        'cost_data': cost_data,
        'margins': margins,
    }
    
    return render(request, 'smart_pricing/price_list/variant_cost.html', context)


@login_required
@require_POST
def update_variant_cost(request, variant_id):
    """تحديث تكلفة نسخة"""
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    # تحديث التكلفة المخصصة
    custom_cost = request.POST.get('custom_cost')
    if custom_cost:
        variant.custom_cost = Decimal(custom_cost)
    else:
        variant.custom_cost = None
    variant.save()
    
    # تحديث تفاصيل التكلفة
    # حذف التفاصيل القديمة وإنشاء جديدة
    VariantCostBreakdown.objects.filter(variant=variant).delete()
    
    for key, value in request.POST.items():
        if key.startswith('cost_item_'):
            parts = key.split('_')
            if len(parts) >= 3:
                category_id = parts[2]
                amount = Decimal(value) if value else Decimal('0')
                
                if amount > 0:
                    try:
                        category = CostCategory.objects.get(id=category_id)
                        VariantCostBreakdown.objects.create(
                            variant=variant,
                            cost_category=category,
                            amount=amount
                        )
                    except:
                        pass
    
    messages.success(request, 'تم تحديث التكلفة بنجاح')
    return redirect('smart_pricing:variant_cost_detail', variant_id=variant_id)


# ============ API Endpoints ============

@login_required
def api_get_family_prices(request, family_id):
    """API: الحصول على أسعار عائلة"""
    family = get_object_or_404(ProductFamily, id=family_id)
    
    prices = []
    for size in family.available_sizes.all():
        size_data = {
            'size_id': size.id,
            'size_name': str(size),
            'width': size.width,
            'length': size.length,
            'cost': str(family.get_cost_for_size(size)),
            'prices': {}
        }
        
        for pl in PriceList.objects.filter(is_active=True):
            price = family.get_price_for_size(size, pl)
            size_data['prices'][pl.code] = {
                'price': str(price),
                'price_with_tax': str(pl.apply_tax(price)),
            }
        
        prices.append(size_data)
    
    return JsonResponse({
        'family_id': family.id,
        'family_name': family.name,
        'base_price': str(family.base_price),
        'base_cost': str(family.base_cost),
        'prices': prices
    })


@login_required
def api_calculate_price(request):
    """API: حساب السعر"""
    family_id = request.GET.get('family_id')
    size_id = request.GET.get('size_id')
    price_list_code = request.GET.get('price_list', 'retail')
    include_tax = request.GET.get('include_tax', 'true') == 'true'
    
    try:
        family = ProductFamily.objects.get(id=family_id)
        size = ProductSize.objects.get(id=size_id)
        price_list = PriceList.objects.get(code=price_list_code)
        
        price = family.get_price_for_size(size, price_list)
        cost = family.get_cost_for_size(size)
        
        tax_breakdown = TaxCalculationService.get_tax_breakdown(
            price, 
            price_list.tax_rate,
            price_list.includes_tax
        )
        
        margin = CostCalculationService.calculate_margin(price, cost)
        
        return JsonResponse({
            'success': True,
            'family': family.name,
            'size': str(size),
            'price_list': price_list.name,
            'cost': str(cost),
            'price': str(price),
            'tax': tax_breakdown,
            'margin': margin,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def api_bulk_update_prices(request):
    """API: تحديث أسعار متعددة"""
    try:
        data = json.loads(request.body)
        
        family_id = data.get('family_id')
        prices = data.get('prices', [])
        
        family = ProductFamily.objects.get(id=family_id)
        
        updated = 0
        for price_data in prices:
            size_id = price_data.get('size_id')
            price_list_code = price_data.get('price_list')
            custom_price = price_data.get('price')
            
            try:
                size = ProductSize.objects.get(id=size_id)
                price_list = PriceList.objects.get(code=price_list_code)
                
                vp, _ = ProductVariantPrice.objects.get_or_create(
                    family=family,
                    size=size,
                    price_list=price_list
                )
                
                if custom_price:
                    vp.custom_price = Decimal(str(custom_price))
                else:
                    vp.custom_price = None
                vp.save()
                updated += 1
            except:
                pass
        
        return JsonResponse({
            'success': True,
            'updated': updated
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============ الإعدادات ============

@login_required
def settings_view(request):
    """عرض وتعديل الإعدادات"""
    settings_obj = PriceListSettings.get_settings()
    
    if request.method == 'POST':
        settings_obj.company_name = request.POST.get('company_name', '')
        settings_obj.company_name_en = request.POST.get('company_name_en', '')
        settings_obj.phone = request.POST.get('phone', '')
        settings_obj.email = request.POST.get('email', '')
        settings_obj.website = request.POST.get('website', '')
        settings_obj.address = request.POST.get('address', '')
        settings_obj.default_tax_rate = Decimal(request.POST.get('default_tax_rate', '15'))
        settings_obj.tax_registration_number = request.POST.get('tax_registration_number', '')
        settings_obj.price_validity_text = request.POST.get('price_validity_text', '')
        settings_obj.price_list_header = request.POST.get('price_list_header', '')
        settings_obj.price_list_footer = request.POST.get('price_list_footer', '')
        
        if 'logo' in request.FILES:
            settings_obj.logo = request.FILES['logo']
        
        settings_obj.save()
        messages.success(request, 'تم حفظ الإعدادات بنجاح')
        return redirect('smart_pricing:price_list_settings')
    
    context = {
        'title': 'إعدادات قوائم الأسعار',
        'settings': settings_obj,
    }
    
    return render(request, 'smart_pricing/price_list/settings.html', context)


@login_required
def api_calculate_product_cost(request, product_id):
    """
    API لحساب تكلفة منتج من BOM
    يستخدم في صفحة إنشاء عائلة منتجات
    """
    from inventory.models import Product
    from production.services.costing_service import ProductCostingService
    
    try:
        product = Product.objects.get(id=product_id)
        
        # حساب التكلفة الكاملة
        cost_data = ProductCostingService.calculate_full_product_cost(product, Decimal('1'))
        
        return JsonResponse({
            'success': True,
            'product_id': product_id,
            'product_name': product.name,
            'material_cost': float(cost_data.get('material_cost', 0)),
            'labor_cost': float(cost_data.get('labor_cost', 0)),
            'overhead_cost': float(cost_data.get('overhead_cost', 0)),
            'total_cost': float(cost_data.get('total_cost', 0)),
            'cost_per_unit': float(cost_data.get('cost_per_unit', 0)),
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'المنتج غير موجود'
        })
    except Exception as e:
        # في حالة عدم وجود BOM، نرجع تكلفة المنتج المباشرة
        try:
            product = Product.objects.get(id=product_id)
            return JsonResponse({
                'success': True,
                'product_id': product_id,
                'product_name': product.name,
                'material_cost': float(product.cost or 0),
                'labor_cost': 0,
                'overhead_cost': 0,
                'total_cost': float(product.cost or 0),
                'cost_per_unit': float(product.cost or 0),
                'note': 'لا يوجد BOM - تم استخدام تكلفة المنتج المباشرة'
            })
        except:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


@login_required
@require_POST
def api_create_category(request):
    """
    API لإنشاء فئة جديدة بسرعة
    يستخدم في صفحة إنشاء عائلة منتجات
    """
    from inventory.models import Category
    import json
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"api_create_category called - Body: {request.body}")
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        logger.info(f"Creating category: name={name}, description={description}")
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'يرجى إدخال اسم الفئة'
            })
        
        # التحقق من عدم وجود فئة بنفس الاسم
        if Category.objects.filter(name=name).exists():
            return JsonResponse({
                'success': False,
                'error': f'الفئة "{name}" موجودة مسبقاً'
            })
        
        # إنشاء الفئة
        category = Category.objects.create(
            name=name,
            description=description,
            is_active=True
        )
        
        logger.info(f"Category created successfully: id={category.id}, name={category.name}")
        
        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات غير صحيحة'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
