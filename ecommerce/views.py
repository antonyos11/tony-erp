"""
Views للمتجر الإلكتروني - متكامل مع النظام
واجهة متجر احترافية للعملاء مع دعم كامل لـ SEO
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.db import OperationalError, transaction
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.contrib.sitemaps import Sitemap
from decimal import Decimal
import datetime
import time

from .models import (
    EcommerceSettings, ProductCategory, OnlineProduct, ProductImage,
    Cart, CartItem, Order, OrderItem, Wishlist, ProductReview, Coupon,
    SocialAuthProvider, Brand, FlashSale, FlashSaleProduct, NewsletterSubscriber
)
from .decorators import store_login_required


# ============ Context Processor للمتجر ============
def store_context(request):
    """سياق عام لجميع صفحات المتجر"""
    try:
        settings = EcommerceSettings.get_settings()
        nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
        all_categories = ProductCategory.objects.filter(is_active=True)
        cart = get_or_create_cart(request)
        
        # مزودي تسجيل الدخول الاجتماعي النشطين
        social_providers = SocialAuthProvider.objects.filter(is_active=True).order_by('sort_order')
        
        # قائمة الأمنيات للمستخدم
        wishlist_ids = []
        if request.user.is_authenticated:
            wishlist_ids = list(Wishlist.objects.filter(
                user=request.user
            ).values_list('product_id', flat=True))
        
        return {
            'store_settings': settings,
            'nav_categories': nav_categories,
            'all_categories': all_categories,
            'store_cart': cart,
            'wishlist_ids': wishlist_ids,
            'social_providers': social_providers,
            'current_year': datetime.datetime.now().year,
        }
    except Exception:
        return {}


def get_or_create_cart(request):
    """الحصول على سلة التسوق أو إنشاء واحدة جديدة"""
    import logging
    logger = logging.getLogger(__name__)
    
    def _ensure_session(req):
        """التأكد من وجود session key"""
        if req.session.session_key:
            return req.session.session_key
        try:
            req.session.create()
            return req.session.session_key
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}", exc_info=True)
            # إعادة المحاولة مرة واحدة
            req.session.save()
            return req.session.session_key

    for attempt in range(3):
        try:
            with transaction.atomic():
                # التحقق من وجود user attribute
                if hasattr(request, 'user') and request.user.is_authenticated:
                    cart, created = Cart.objects.select_for_update().get_or_create(user=request.user)
                    if created:
                        logger.info(f"Created new cart for user {request.user.id}")
                else:
                    session_key = _ensure_session(request)
                    if not session_key:
                        logger.error("Failed to get session_key after multiple attempts")
                        raise ValueError("Could not create session")
                    cart, created = Cart.objects.select_for_update().get_or_create(
                        session_key=session_key, 
                        user=None
                    )
                    if created:
                        logger.info(f"Created new cart for session {session_key}")
            return cart
        except OperationalError as exc:
            if 'locked' in str(exc).lower() and attempt < 2:
                logger.warning(f"Database locked, attempt {attempt + 1}/3")
                time.sleep(0.2 * (attempt + 1))
                continue
            logger.error(f"OperationalError in get_or_create_cart: {str(exc)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_or_create_cart: {str(e)}", exc_info=True)
            raise


def store_home(request):
    """الصفحة الرئيسية للمتجر - واجهة عامة للزوار"""
    settings = EcommerceSettings.get_settings()
    
    # المنتجات المميزة
    featured_products = OnlineProduct.objects.filter(
        is_active=True, is_featured=True
    ).select_related('inventory_item', 'category')[:8]
    
    # المنتجات الجديدة
    new_products = OnlineProduct.objects.filter(
        is_active=True, is_new=True
    ).select_related('inventory_item', 'category')[:8]
    
    # الأكثر مبيعاً
    best_sellers = OnlineProduct.objects.filter(
        is_active=True
    ).order_by('-sales_count').select_related('inventory_item', 'category')[:8]
    
    # الفئات الرئيسية
    categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    nav_categories = categories
    all_categories = ProductCategory.objects.filter(is_active=True)
    
    # سلة التسوق
    cart = get_or_create_cart(request)
    
    # قائمة الأمنيات
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    # الخدمات المنزلية
    home_services_data = {}
    try:
        from home_services.models import MaintenanceCategory, CleaningPackage, HomeServicesSettings
        home_services_settings = HomeServicesSettings.get_settings()
        if home_services_settings.is_active:
            home_services_data = {
                'enabled': True,
                'settings': home_services_settings,
                'maintenance_categories': MaintenanceCategory.objects.filter(is_active=True)[:6],
                'cleaning_packages': CleaningPackage.objects.filter(is_active=True, is_featured=True)[:3],
            }
    except Exception:
        pass
    
    # العلامات التجارية المميزة
    featured_brands = Brand.get_featured()
    
    # العروض السريعة النشطة
    now = timezone.now()
    flash_sales = FlashSale.objects.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).prefetch_related('products__product')[:3]
    
    # أول عرض سريع للعرض الرئيسي
    flash_sale = flash_sales.first() if flash_sales.exists() else None
    
    context = {
        'settings': settings,
        'featured_products': featured_products,
        'new_products': new_products,
        'best_sellers': best_sellers,
        'categories': categories,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'wishlist_ids': wishlist_ids,
        'current_year': datetime.datetime.now().year,
        'home_services': home_services_data,
        'featured_brands': featured_brands,
        'flash_sales': flash_sales,
        'flash_sale': flash_sale,
        # الميزات الجديدة
        'show_new_features': True,
        'new_features': [
            {
                'icon': 'bi-box-seam',
                'title': 'صمم مرتبتك الخاصة',
                'description': 'اختر المقاس والمكونات واحصل على مرتبة أحلامك',
                'url': '/store/mattress-builder/',
                'color': 'purple'
            },
            {
                'icon': 'bi-truck',
                'title': 'تتبع شحنتك',
                'description': 'تابع طلبك بالوقت الفعلي مع GPS',
                'url': '/store/track-shipment/',
                'color': 'info'
            },
            {
                'icon': 'bi-star-fill',
                'title': 'المراجعات والتقييمات',
                'description': 'شارك تجربتك واقرأ آراء العملاء',
                'url': '/ecommerce/reviews/',
                'color': 'warning'
            }
        ]

    }
    return render(request, 'ecommerce/store_home_new2.html', context)


def categories_list(request):
    """صفحة عرض جميع الفئات"""
    settings = EcommerceSettings.get_settings()
    
    # الفئات الرئيسية مع الفئات الفرعية وعدد المنتجات
    main_categories = ProductCategory.objects.filter(
        is_active=True, parent=None
    ).prefetch_related('children').annotate(
        products_count=Count('online_products', filter=Q(online_products__is_active=True))
    ).order_by('sort_order', 'name')
    
    # جميع الفئات للسايدبار
    all_categories = ProductCategory.objects.filter(is_active=True)
    nav_categories = main_categories[:6]
    
    cart = get_or_create_cart(request)
    
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    context = {
        'settings': settings,
        'main_categories': main_categories,
        'categories': all_categories,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'wishlist_ids': wishlist_ids,
        'current_year': datetime.datetime.now().year,
    }
    return render(request, 'ecommerce/store_categories_new.html', context)


def brands_list(request):
    """صفحة عرض جميع العلامات التجارية"""
    settings = EcommerceSettings.get_settings()
    
    brands = Brand.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    cart = get_or_create_cart(request)
    
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    context = {
        'settings': settings,
        'brands': brands,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'wishlist_ids': wishlist_ids,
        'current_year': datetime.datetime.now().year,
    }
    return render(request, 'ecommerce/brands_list.html', context)


def search_products(request):
    """صفحة بحث متقدمة"""
    settings = EcommerceSettings.get_settings()
    
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '')
    
    products = OnlineProduct.objects.filter(is_active=True).select_related('inventory_item', 'category')
    
    if query:
        products = products.filter(
            Q(display_name__icontains=query) |
            Q(inventory_item__name__icontains=query) |
            Q(short_description__icontains=query) |
            Q(full_description__icontains=query) |
            Q(inventory_item__sku__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # تصفية بالفئة
    current_category = None
    if category_slug:
        current_category = ProductCategory.objects.filter(slug=category_slug, is_active=True).first()
        if current_category:
            products = products.filter(category=current_category)
    
    # تصفية السعر
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(inventory_item__price__gte=Decimal(min_price))
    if max_price:
        products = products.filter(inventory_item__price__lte=Decimal(max_price))
    
    # التوفر
    in_stock_only = request.GET.get('in_stock')
    if in_stock_only:
        products = products.filter(inventory_item__current_stock__gt=0)
    
    # الترتيب
    sort_by = request.GET.get('sort', 'relevance')
    if sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'price_low':
        products = products.order_by('inventory_item__price')
    elif sort_by == 'price_high':
        products = products.order_by('-inventory_item__price')
    elif sort_by == 'popular':
        products = products.order_by('-sales_count')
    
    # الصفحات
    paginator = Paginator(products, settings.products_per_page)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)
    
    all_categories = ProductCategory.objects.filter(is_active=True)
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    
    cart = get_or_create_cart(request)
    
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    context = {
        'settings': settings,
        'products': products_page,
        'search_query': query,
        'current_category': current_category,
        'categories': all_categories,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'sort_by': sort_by,
        'cart': cart,
        'wishlist_ids': wishlist_ids,
        'results_count': paginator.count,
        'current_year': datetime.datetime.now().year,
    }
    return render(request, 'ecommerce/store_product_list_new.html', context)


def product_list(request):
    """قائمة المنتجات مع التصفية والبحث"""
    settings = EcommerceSettings.get_settings()
    
    products = OnlineProduct.objects.filter(is_active=True).select_related('inventory_item', 'category')
    
    # البحث
    search_query = request.GET.get('q', '')
    if search_query:
        products = products.filter(
            Q(display_name__icontains=search_query) |
            Q(inventory_item__name__icontains=search_query) |
            Q(short_description__icontains=search_query)
        )
    
    # تصفية الفئة
    category_slug = request.GET.get('category')
    category = None
    if category_slug:
        category = get_object_or_404(ProductCategory, slug=category_slug, is_active=True)
        products = products.filter(category=category)
    
    # تصفية السعر
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(inventory_item__price__gte=Decimal(min_price))
    if max_price:
        products = products.filter(inventory_item__price__lte=Decimal(max_price))
    
    # التوفر
    in_stock_only = request.GET.get('in_stock')
    if in_stock_only:
        products = products.filter(inventory_item__current_stock__gt=0)
    
    # الترتيب
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'price_low':
        products = products.order_by('inventory_item__price')
    elif sort_by == 'price_high':
        products = products.order_by('-inventory_item__price')
    elif sort_by == 'popular':
        products = products.order_by('-sales_count')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    
    # الصفحات
    paginator = Paginator(products, settings.products_per_page)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)
    
    # الفئات للفلتر
    categories = ProductCategory.objects.filter(is_active=True)
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    
    cart = get_or_create_cart(request)
    
    # قائمة الأمنيات
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    context = {
        'settings': settings,
        'products': products_page,
        'categories': categories,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'current_category': category,
        'search_query': search_query,
        'sort_by': sort_by,
        'cart': cart,
        'wishlist_ids': wishlist_ids,
        'current_year': datetime.datetime.now().year,
    }
    return render(request, 'ecommerce/store_product_list_new.html', context)


def product_detail(request, pk):
    """تفاصيل المنتج"""
    settings = EcommerceSettings.get_settings()
    
    product = get_object_or_404(OnlineProduct, pk=pk, is_active=True)
    
    # زيادة عدد المشاهدات
    product.views_count += 1
    product.save(update_fields=['views_count'])
    
    # الصور الإضافية
    images = product.images.all()
    
    # التقييمات
    reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # منتجات مشابهة
    related_products = OnlineProduct.objects.filter(
        is_active=True, category=product.category
    ).exclude(pk=pk).select_related('inventory_item')[:4]
    
    cart = get_or_create_cart(request)
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    
    # هل المنتج في قائمة الأمنيات
    in_wishlist = False
    wishlist_ids = []
    if hasattr(request, 'user') and request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    context = {
        'settings': settings,
        'product': product,
        'images': images,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'reviews_count': reviews.count(),
        'related_products': related_products,
        'cart': cart,
        'in_wishlist': in_wishlist,
        'wishlist_ids': wishlist_ids,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'current_year': datetime.datetime.now().year,
    }
    return render(request, 'ecommerce/store_product_detail_new.html', context)


def category_products(request, slug):
    """صفحة مستقلة لمنتجات فئة معينة"""
    settings = EcommerceSettings.get_settings()
    category = get_object_or_404(ProductCategory, slug=slug, is_active=True)
    
    # المنتجات في هذه الفئة
    products = OnlineProduct.objects.filter(
        is_active=True, category=category
    ).select_related('inventory_item', 'category')
    
    # الفئات الفرعية
    subcategories = ProductCategory.objects.filter(parent=category, is_active=True)
    
    # تصفية السعر
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(inventory_item__price__gte=Decimal(min_price))
    if max_price:
        products = products.filter(inventory_item__price__lte=Decimal(max_price))
    
    # التوفر
    in_stock_only = request.GET.get('in_stock')
    if in_stock_only:
        products = products.filter(inventory_item__current_stock__gt=0)
    
    # البحث داخل الفئة
    search_query = request.GET.get('q', '')
    if search_query:
        products = products.filter(
            Q(display_name__icontains=search_query) |
            Q(inventory_item__name__icontains=search_query) |
            Q(short_description__icontains=search_query)
        )
    
    # الترتيب
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'price_low':
        products = products.order_by('inventory_item__price')
    elif sort_by == 'price_high':
        products = products.order_by('-inventory_item__price')
    elif sort_by == 'popular':
        products = products.order_by('-sales_count')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    
    # الصفحات
    paginator = Paginator(products, settings.products_per_page)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)
    
    # الفئات للسايدبار
    all_categories = ProductCategory.objects.filter(is_active=True)
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    
    cart = get_or_create_cart(request)
    
    # قائمة الأمنيات
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    # مسار الفئة (breadcrumb)
    breadcrumb = []
    current = category
    while current:
        breadcrumb.insert(0, current)
        current = current.parent
    
    context = {
        'settings': settings,
        'category': category,
        'subcategories': subcategories,
        'products': products_page,
        'categories': all_categories,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'current_category': category,
        'search_query': search_query,
        'sort_by': sort_by,
        'cart': cart,
        'wishlist_ids': wishlist_ids,
        'breadcrumb': breadcrumb,
        'current_year': datetime.datetime.now().year,
    }
    return render(request, 'ecommerce/store_product_list_new.html', context)


# ============ سلة التسوق ============

def cart_view(request):
    """عرض سلة التسوق"""
    settings = EcommerceSettings.get_settings()
    cart = get_or_create_cart(request)
    
    # Fetch cart items explicitly
    cart_items = cart.items.select_related('product__inventory_item').all()
    
    context = {
        'settings': settings,
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'ecommerce/store_cart_new.html', context)


@require_POST
def cart_add(request):
    """إضافة منتج للسلة"""
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    
    product = get_object_or_404(OnlineProduct, pk=product_id, is_active=True)
    cart = get_or_create_cart(request)
    
    # التحقق من التوفر
    if quantity > product.stock:
        return JsonResponse({
            'success': False,
            'message': _('الكمية المطلوبة غير متوفرة')
        })
    
    # إضافة أو تحديث العنصر
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        if cart_item.quantity > product.stock:
            cart_item.quantity = product.stock
        cart_item.save()
    
    return JsonResponse({
        'success': True,
        'message': _('تمت الإضافة للسلة'),
        'cart_count': cart.items_count,
        'cart_total': float(cart.total),
    })


@require_POST
def cart_update(request):
    """تحديث كمية منتج في السلة"""
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))
    
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    
    if quantity <= 0:
        item.delete()
    else:
        if quantity > item.product.stock:
            quantity = item.product.stock
        item.quantity = quantity
        item.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.items_count,
            'cart_total': float(cart.total),
        })
    
    return redirect('ecommerce:cart')


@require_POST
def cart_remove(request):
    """حذف منتج من السلة"""
    item_id = request.POST.get('item_id')
    
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': _('تم الحذف من السلة'),
            'cart_count': cart.items_count,
            'cart_total': float(cart.total),
        })
    
    messages.success(request, _('تم حذف المنتج من السلة'))
    return redirect('ecommerce:cart')


# ============ الطلبات ============

@store_login_required
def checkout(request):
    """صفحة إتمام الطلب"""
    settings = EcommerceSettings.get_settings()
    cart = get_or_create_cart(request)
    
    if cart.items_count == 0:
        messages.warning(request, _('السلة فارغة'))
        return redirect('ecommerce:cart')
    
    # حساب الشحن
    shipping_cost = settings.default_shipping_cost
    if settings.free_shipping_threshold > 0 and cart.total >= settings.free_shipping_threshold:
        shipping_cost = Decimal('0')
    
    context = {
        'settings': settings,
        'cart': cart,
        'cart_items': cart.items.all(),
        'subtotal': cart.total,
        'shipping_cost': shipping_cost,
        'total': cart.total + shipping_cost,
        'currency_symbol': settings.currency,
    }
    return render(request, 'ecommerce/store_checkout_new.html', context)


@store_login_required
@require_POST
def place_order(request):
    """إنشاء الطلب"""
    settings = EcommerceSettings.get_settings()
    cart = get_or_create_cart(request)
    
    if cart.items_count == 0:
        return JsonResponse({'success': False, 'message': _('السلة فارغة')})
    
    # بيانات العميل
    customer_name = request.POST.get('customer_name')
    customer_email = request.POST.get('customer_email')
    customer_phone = request.POST.get('customer_phone')
    shipping_address = request.POST.get('shipping_address')
    shipping_city = request.POST.get('shipping_city')
    customer_notes = request.POST.get('customer_notes', '')
    
    # حساب المبالغ
    subtotal = cart.total
    shipping_cost = settings.default_shipping_cost
    if settings.free_shipping_threshold > 0 and subtotal >= settings.free_shipping_threshold:
        shipping_cost = Decimal('0')
    
    # الخصم (كوبون)
    discount = Decimal('0')
    coupon_code = request.POST.get('coupon_code')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code.strip())
            
            # التحقق من صلاحية الكوبون
            if not coupon.is_valid():
                return JsonResponse({
                    'success': False, 
                    'message': _('الكوبون غير صالح أو منتهي الصلاحية')
                })
            
            # التحقق من الحد الأدنى للطلب
            if subtotal < coupon.min_order_amount:
                return JsonResponse({
                    'success': False,
                    'message': _(f'الحد الأدنى للطلب {coupon.min_order_amount} {settings.currency}')
                })
            
            # حساب الخصم
            if coupon.discount_type == 'percentage':
                discount = subtotal * (coupon.discount_value / 100)
                if coupon.max_discount:
                    discount = min(discount, coupon.max_discount)
            else:
                discount = coupon.discount_value
            
            # زيادة عداد الاستخدام
            coupon.used_count += 1
            coupon.save()
            
        except Coupon.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': _('كود الكوبون غير صحيح')
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error applying coupon: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': _('حدث خطأ أثناء تطبيق الكوبون')
            })
    
    # الضريبة (14% لمصر - تم التحديث January 2026)
    settings = EcommerceSettings.get_settings()
    vat_rate = settings.vat_rate / 100 if hasattr(settings, 'vat_rate') else Decimal('0.14')
    tax = (subtotal - discount) * vat_rate
    total = subtotal + shipping_cost + tax - discount
    
    # إنشاء الطلب
    order = Order.objects.create(
        user=request.user,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        shipping_address=shipping_address,
        shipping_city=shipping_city,
        customer_notes=customer_notes,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        discount=discount,
        tax=tax,
        total=total,
        status='pending',
        payment_status='pending',
    )
    
    # إنشاء عناصر الطلب مع خصم المخزون
    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            quantity=cart_item.quantity,
            unit_price=cart_item.product.price,
            subtotal=cart_item.subtotal,
        )
        # تحديث إحصائيات المنتج
        cart_item.product.sales_count += cart_item.quantity
        cart_item.product.save(update_fields=['sales_count'])
        
        # ✅ خصم المخزون من نظام ERP
        try:
            if cart_item.product.inventory_item:
                inv_item = cart_item.product.inventory_item
                inv_item.current_stock = max(0, inv_item.current_stock - cart_item.quantity)
                inv_item.save(update_fields=['current_stock'])
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error updating stock for product {cart_item.product.id}: {e}")
    
    # ✅ إنشاء فاتورة في نظام ERP
    try:
        from sales.models import Invoice
        from partners.models import Customer as ERPCustomer
        
        # ربط أو إنشاء عميل ERP
        erp_customer = None
        try:
            from ecommerce.models import Customer as EcomCustomer
            ecom_customer = EcomCustomer.objects.filter(user=request.user).first()
            if ecom_customer and ecom_customer.partner_customer:
                erp_customer = ecom_customer.partner_customer
            else:
                erp_customer, _created = ERPCustomer.objects.get_or_create(
                    name=customer_name,
                    defaults={
                        'phone': customer_phone,
                        'email': customer_email,
                        'address': shipping_address,
                    }
                )
                if ecom_customer:
                    ecom_customer.partner_customer = erp_customer
                    ecom_customer.save(update_fields=['partner_customer'])
        except Exception:
            pass
        
        # إنشاء الفاتورة
        if erp_customer:
            invoice = Invoice.objects.create(
                customer=erp_customer,
                cached_total=total,
                discount=discount,
            )
            order.invoice = invoice
            if erp_customer:
                order.customer = erp_customer
            order.save(update_fields=['invoice', 'customer'])
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not create ERP invoice for order {order.order_number}: {e}")
    
    # تفريغ السلة
    cart.items.all().delete()
    
    # ✅ إنشاء بطاقات ضمان تلقائية
    try:
        from ecommerce.views_warranty import create_warranty_for_order
        warranty_cards = create_warranty_for_order(order, invoice=getattr(order, 'invoice', None))
        if warranty_cards:
            import logging
            logging.getLogger(__name__).info(
                f"Created {len(warranty_cards)} warranty cards for order {order.order_number}"
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not create warranty cards for order {order.order_number}: {e}")
    
    messages.success(request, _('تم إنشاء طلبك بنجاح!'))
    
    # redirect to order detail or return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'order_number': order.order_number,
            'redirect_url': f'/store/order/{order.id}/',
        })
    
    return redirect('ecommerce:order_detail', pk=order.id)


@store_login_required
def order_detail(request, pk):
    """تفاصيل الطلب"""
    settings = EcommerceSettings.get_settings()
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    context = {
        'settings': settings,
        'order': order,
        'currency_symbol': settings.currency,
    }
    return render(request, 'ecommerce/order_detail.html', context)


@store_login_required
def my_orders(request):
    """طلباتي"""
    settings = EcommerceSettings.get_settings()
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    paginator = Paginator(orders, 10)
    page = request.GET.get('page', 1)
    orders_page = paginator.get_page(page)
    
    context = {
        'settings': settings,
        'orders': orders_page,
        'currency_symbol': settings.currency,
    }
    return render(request, 'ecommerce/my_orders.html', context)


# ============ قائمة الأمنيات ============

@store_login_required
def wishlist_view(request):
    """عرض قائمة الأمنيات"""
    settings = EcommerceSettings.get_settings()
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product', 'product__inventory_item')
    
    context = {
        'settings': settings,
        'wishlist_items': wishlist_items,
        'currency_symbol': settings.currency,
    }
    return render(request, 'ecommerce/wishlist.html', context)


@store_login_required
@require_POST
def wishlist_toggle(request):
    """إضافة/إزالة من قائمة الأمنيات"""
    product_id = request.POST.get('product_id')
    product = get_object_or_404(OnlineProduct, pk=product_id)
    
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user, product=product
    )
    
    if not created:
        wishlist_item.delete()
        return JsonResponse({
            'success': True,
            'added': False,
            'message': _('تمت الإزالة من قائمة الأمنيات')
        })
    
    return JsonResponse({
        'success': True,
        'added': True,
        'message': _('تمت الإضافة لقائمة الأمنيات')
    })


# ============ التقييمات ============

@store_login_required
@require_POST
def add_review(request, product_id):
    """إضافة تقييم للمنتج"""
    product = get_object_or_404(OnlineProduct, pk=product_id)
    
    rating = int(request.POST.get('rating', 5))
    comment = request.POST.get('comment', '')
    
    review, created = ProductReview.objects.update_or_create(
        product=product, user=request.user,
        defaults={'rating': rating, 'comment': comment, 'is_approved': False}
    )
    
    if created:
        messages.success(request, _('شكراً لتقييمك! سيتم مراجعته قريباً.'))
    else:
        messages.info(request, _('تم تحديث تقييمك.'))
    
    return redirect('ecommerce:product_detail', pk=product_id)


# ============ API للسلة ============

def cart_count_api(request):
    """API لعدد عناصر السلة"""
    cart = get_or_create_cart(request)
    return JsonResponse({
        'count': cart.items_count,
        'total': float(cart.total),
    })


# ============ لوحة تحكم المتجر (للإدارة) ============

@store_login_required
def admin_dashboard(request):
    """لوحة تحكم المتجر للإدارة"""
    if not request.user.is_staff:
        messages.error(request, _('غير مصرح لك'))
        return redirect('ecommerce:store_home')
    
    settings = EcommerceSettings.get_settings()
    
    # إحصائيات
    from django.db.models.functions import TruncDate
    from datetime import timedelta
    
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    stats = {
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'today_orders': Order.objects.filter(created_at__date=today).count(),
        'total_revenue': Order.objects.filter(payment_status='paid').aggregate(
            total=Sum('total'))['total'] or 0,
        'total_products': OnlineProduct.objects.filter(is_active=True).count(),
        'out_of_stock': OnlineProduct.objects.filter(
            is_active=True, inventory_item__current_stock=0).count(),
    }
    
    # آخر الطلبات
    recent_orders = Order.objects.order_by('-created_at')[:10]
    
    # الأكثر مبيعاً
    top_products = OnlineProduct.objects.filter(is_active=True).order_by('-sales_count')[:5]
    
    context = {
        'settings': settings,
        'stats': stats,
        'recent_orders': recent_orders,
        'top_products': top_products,
    }
    return render(request, 'ecommerce/admin/dashboard.html', context)


# ============ الصفحات الثابتة (للزوار) ============

def store_about(request):
    """صفحة من نحن"""
    settings = EcommerceSettings.get_settings()
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    cart = get_or_create_cart(request)
    
    context = {
        'settings': settings,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'current_year': datetime.datetime.now().year,
        'page_title': 'من نحن',
    }
    return render(request, 'ecommerce/pages/about.html', context)


def store_contact(request):
    """صفحة اتصل بنا"""
    settings = EcommerceSettings.get_settings()
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    cart = get_or_create_cart(request)
    
    if request.method == 'POST':
        # معالجة نموذج الاتصال
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # يمكنك إضافة منطق حفظ الرسالة أو إرسالها بالبريد هنا
        messages.success(request, _('تم إرسال رسالتك بنجاح! سنتواصل معك قريباً.'))
        return redirect('ecommerce:store_contact')
    
    context = {
        'settings': settings,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'current_year': datetime.datetime.now().year,
        'page_title': 'اتصل بنا',
    }
    return render(request, 'ecommerce/pages/contact.html', context)


def store_faq(request):
    """صفحة الأسئلة الشائعة"""
    settings = EcommerceSettings.get_settings()
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    cart = get_or_create_cart(request)
    
    context = {
        'settings': settings,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'current_year': datetime.datetime.now().year,
        'page_title': 'الأسئلة الشائعة',
    }
    return render(request, 'ecommerce/pages/faq.html', context)


def store_privacy(request):
    """صفحة سياسة الخصوصية"""
    settings = EcommerceSettings.get_settings()
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    cart = get_or_create_cart(request)
    
    context = {
        'settings': settings,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'current_year': datetime.datetime.now().year,
        'page_title': 'سياسة الخصوصية',
    }
    return render(request, 'ecommerce/pages/privacy.html', context)


def store_terms(request):
    """صفحة الشروط والأحكام"""
    settings = EcommerceSettings.get_settings()
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    cart = get_or_create_cart(request)
    
    context = {
        'settings': settings,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'current_year': datetime.datetime.now().year,
        'page_title': 'الشروط والأحكام',
    }
    return render(request, 'ecommerce/pages/terms.html', context)


def store_shipping(request):
    """صفحة سياسة الشحن"""
    settings = EcommerceSettings.get_settings()
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    cart = get_or_create_cart(request)
    
    context = {
        'settings': settings,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'current_year': datetime.datetime.now().year,
        'page_title': 'سياسة الشحن والتوصيل',
    }
    return render(request, 'ecommerce/pages/shipping.html', context)


def store_page(request, page_type):
    """صفحة عامة حسب النوع (terms, privacy, etc)"""
    from .models import StorePageContent
    
    settings = EcommerceSettings.get_settings()
    nav_categories = ProductCategory.objects.filter(is_active=True, parent=None)[:6]
    all_categories = ProductCategory.objects.filter(is_active=True)
    cart = get_or_create_cart(request)
    
    try:
        page_content = StorePageContent.objects.get(page=page_type, is_active=True)
    except StorePageContent.DoesNotExist:
        page_content = None
    
    context = {
        'settings': settings,
        'nav_categories': nav_categories,
        'all_categories': all_categories,
        'cart': cart,
        'current_year': datetime.datetime.now().year,
        'page_content': page_content,
        'page_title': page_content.title if page_content else page_type,
    }
    return render(request, 'ecommerce/pages/generic_page.html', context)


# ============ SEO: Sitemap & Robots.txt ============

def robots_txt(request):
    """ملف robots.txt للسيرش إنجن"""
    lines = [
        "User-Agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


class ProductSitemap(Sitemap):
    """Sitemap للمنتجات"""
    changefreq = "daily"
    priority = 0.8
    
    def items(self):
        return OnlineProduct.objects.filter(is_active=True)
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return f'/ecommerce/product/{obj.pk}/'


class CategorySitemap(Sitemap):
    """Sitemap للفئات"""
    changefreq = "weekly"
    priority = 0.7
    
    def items(self):
        return ProductCategory.objects.filter(is_active=True)
    
    def location(self, obj):
        return f'/ecommerce/category/{obj.slug}/'


class StaticPagesSitemap(Sitemap):
    """Sitemap للصفحات الثابتة"""
    changefreq = "monthly"
    priority = 0.5
    
    def items(self):
        return ['store_home', 'store_about', 'store_contact', 'store_faq', 'store_privacy', 'store_terms']
    
    def location(self, item):
        from django.urls import reverse
        if item == 'store_home':
            return '/ecommerce/'
        return f'/ecommerce/{item.replace("store_", "")}/'


# ============ الميزات الإضافية ============

def flash_sales_list(request):
    """صفحة العروض السريعة"""
    settings = EcommerceSettings.get_settings()
    now = timezone.now()
    
    # العروض النشطة
    active_sales = FlashSale.objects.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).prefetch_related('products__product')
    
    # العروض القادمة
    upcoming_sales = FlashSale.objects.filter(
        is_active=True,
        start_date__gt=now
    ).order_by('start_date')[:5]
    
    context = {
        'settings': settings,
        'active_sales': active_sales,
        'upcoming_sales': upcoming_sales,
        'page_title': 'العروض السريعة',
    }
    return render(request, 'ecommerce/flash_sales.html', context)


@require_POST
def newsletter_subscribe(request):
    """الاشتراك في النشرة البريدية"""
    email = request.POST.get('email', '').strip().lower()
    
    if not email:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'يرجى إدخال البريد الإلكتروني'})
        messages.error(request, 'يرجى إدخال البريد الإلكتروني')
        return redirect(request.META.get('HTTP_REFERER', 'ecommerce:store_home'))
    
    # التحقق من وجود الاشتراك
    subscriber, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={'is_active': True}
    )
    
    if not created:
        if subscriber.is_active:
            msg = 'أنت مشترك بالفعل في النشرة البريدية'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': msg})
            messages.info(request, msg)
        else:
            subscriber.is_active = True
            subscriber.save()
            msg = 'تم إعادة تفعيل اشتراكك بنجاح!'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
    else:
        msg = 'تم الاشتراك في النشرة البريدية بنجاح!'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
    
    return redirect(request.META.get('HTTP_REFERER', 'ecommerce:store_home'))


@require_POST
def apply_coupon(request):
    """تطبيق كوبون الخصم على السلة"""
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    cart = get_or_create_cart(request)
    
    if not coupon_code:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'يرجى إدخال كود الكوبون'})
        messages.error(request, 'يرجى إدخال كود الكوبون')
        return redirect('ecommerce:cart')
    
    try:
        coupon = Coupon.objects.get(code=coupon_code)
        
        # التحقق من صلاحية الكوبون
        now = timezone.now()
        
        if not coupon.is_active:
            raise ValueError('هذا الكوبون غير مفعل')
        
        if coupon.valid_from and coupon.valid_from > now:
            raise ValueError('هذا الكوبون لم يبدأ بعد')
        
        if coupon.valid_to and coupon.valid_to < now:
            raise ValueError('انتهت صلاحية هذا الكوبون')
        
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            raise ValueError('تم استخدام هذا الكوبون الحد الأقصى من المرات')
        
        if coupon.min_order_amount and cart.total < coupon.min_order_amount:
            raise ValueError(f'الحد الأدنى للطلب هو {coupon.min_order_amount} ج.م')
        
        # حساب الخصم
        if coupon.discount_type == 'percentage':
            discount = (cart.total * coupon.discount_value) / 100
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:
            discount = coupon.discount_value
        
        # حفظ الكوبون في السلة
        cart.coupon = coupon
        cart.discount_amount = discount
        cart.save()
        
        msg = f'تم تطبيق الكوبون بنجاح! خصم: {discount} ر.س'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': msg,
                'discount': float(discount),
                'new_total': float(cart.total - discount)
            })
        messages.success(request, msg)
        
    except Coupon.DoesNotExist:
        msg = 'كود الكوبون غير صحيح'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
    except ValueError as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': str(e)})
        messages.error(request, str(e))
    
    return redirect('ecommerce:cart')


@require_POST
def remove_coupon(request):
    """إزالة الكوبون من السلة"""
    cart = get_or_create_cart(request)
    cart.coupon = None
    cart.discount_amount = Decimal('0')
    cart.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'تم إزالة الكوبون'})
    
    messages.success(request, 'تم إزالة الكوبون')
    return redirect('ecommerce:cart')


def add_to_recently_viewed(request, product_id):
    """إضافة منتج للمشاهدة مؤخراً (Session-based)"""
    recently_viewed = request.session.get('recently_viewed', [])
    
    # إزالة المنتج إذا كان موجوداً مسبقاً
    if product_id in recently_viewed:
        recently_viewed.remove(product_id)
    
    # إضافته في البداية
    recently_viewed.insert(0, product_id)
    
    # الاحتفاظ بآخر 10 منتجات فقط
    request.session['recently_viewed'] = recently_viewed[:10]


def get_recently_viewed_products(request):
    """جلب المنتجات المشاهدة مؤخراً"""
    recently_viewed = request.session.get('recently_viewed', [])
    if not recently_viewed:
        return []
    
    # جلب المنتجات مع الحفاظ على الترتيب
    products = OnlineProduct.objects.filter(id__in=recently_viewed, is_active=True)
    products_dict = {p.id: p for p in products}
    return [products_dict[pid] for pid in recently_viewed if pid in products_dict]


def compare_products(request):
    """صفحة مقارنة المنتجات"""
    settings = EcommerceSettings.get_settings()
    compare_ids = request.session.get('compare_products', [])
    
    products = []
    if compare_ids:
        products = OnlineProduct.objects.filter(id__in=compare_ids, is_active=True)
    
    context = {
        'settings': settings,
        'products': products,
        'page_title': 'مقارنة المنتجات',
    }
    return render(request, 'ecommerce/compare.html', context)


@require_POST
def add_to_compare(request):
    """إضافة منتج للمقارنة"""
    product_id = request.POST.get('product_id')
    if not product_id:
        return JsonResponse({'success': False, 'message': 'منتج غير صحيح'})
    
    try:
        product_id = int(product_id)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'منتج غير صحيح'})
    
    compare_list = request.session.get('compare_products', [])
    
    if product_id in compare_list:
        return JsonResponse({'success': False, 'message': 'المنتج موجود في قائمة المقارنة'})
    
    if len(compare_list) >= 4:
        return JsonResponse({'success': False, 'message': 'يمكنك مقارنة 4 منتجات كحد أقصى'})
    
    compare_list.append(product_id)
    request.session['compare_products'] = compare_list
    
    return JsonResponse({
        'success': True,
        'message': 'تم إضافة المنتج للمقارنة',
        'count': len(compare_list)
    })


@require_POST
def remove_from_compare(request):
    """إزالة منتج من المقارنة"""
    product_id = request.POST.get('product_id')
    if not product_id:
        return JsonResponse({'success': False, 'message': 'منتج غير صحيح'})
    
    try:
        product_id = int(product_id)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'منتج غير صحيح'})
    
    compare_list = request.session.get('compare_products', [])
    
    if product_id in compare_list:
        compare_list.remove(product_id)
        request.session['compare_products'] = compare_list
    
    return JsonResponse({
        'success': True,
        'message': 'تم إزالة المنتج من المقارنة',
        'count': len(compare_list)
    })


def clear_compare(request):
    """مسح قائمة المقارنة"""
    request.session['compare_products'] = []
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'تم مسح قائمة المقارنة'})
    
    return redirect('ecommerce:compare_products')


@require_POST
def submit_review(request, product_id):
    """إضافة تقييم للمنتج"""
    if not request.user.is_authenticated:
        messages.error(request, 'يجب تسجيل الدخول أولاً لإضافة تقييم')
        return redirect('ecommerce:product_detail', pk=product_id)
    
    product = get_object_or_404(OnlineProduct, pk=product_id, is_active=True)
    
    rating = request.POST.get('rating')
    title = request.POST.get('title', '').strip()
    comment = request.POST.get('comment', '').strip()
    
    if not rating:
        messages.error(request, 'يرجى اختيار التقييم')
        return redirect('ecommerce:product_detail', pk=product_id)
    
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError()
    except ValueError:
        messages.error(request, 'تقييم غير صحيح')
        return redirect('ecommerce:product_detail', pk=product_id)
    
    # التحقق من عدم وجود تقييم سابق
    existing = ProductReview.objects.filter(product=product, user=request.user).first()
    if existing:
        messages.warning(request, 'لقد قمت بتقييم هذا المنتج من قبل')
        return redirect('ecommerce:product_detail', pk=product_id)
    
    review = ProductReview.objects.create(
        product=product,
        user=request.user,
        rating=rating,
        comment=comment,
        is_approved=False  # يحتاج موافقة
    )
    
    messages.success(request, 'شكراً لك! سيتم مراجعة تقييمك ونشره قريباً')
    return redirect('ecommerce:product_detail', pk=product_id)


# ==========================================
# الميزات الجديدة - January 2026
# ==========================================

def track_shipment(request):
    """صفحة تتبع الشحنات"""
    from shipment_tracking.models import Shipment
    
    tracking_number = request.GET.get('tracking_number', '')
    shipment = None
    
    if tracking_number:
        try:
            shipment = Shipment.objects.get(tracking_number=tracking_number)
        except Shipment.DoesNotExist:
            messages.error(request, 'رقم التتبع غير صحيح')
    
    return render(request, 'ecommerce/track_shipment.html', {
        'tracking_number': tracking_number,
        'shipment': shipment
    })


def shipment_details(request, tracking_number):
    """تفاصيل الشحنة"""
    from shipment_tracking.models import Shipment
    
    shipment = get_object_or_404(Shipment, tracking_number=tracking_number)
    
    return render(request, 'ecommerce/shipment_details.html', {
        'shipment': shipment,
        'tracking_number': tracking_number
    })


def all_reviews(request):
    """جميع المراجعات"""
    from product_reviews.models import ProductReview
    
    reviews = ProductReview.objects.filter(status='approved').select_related('product', 'user').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page', 1)
    reviews_page = paginator.get_page(page)
    
    return render(request, 'ecommerce/all_reviews.html', {
        'reviews': reviews_page
    })


@store_login_required
def my_reviews(request):
    """مراجعاتي"""
    from product_reviews.models import ProductReview
    
    user_reviews = ProductReview.objects.filter(user=request.user).select_related('product').order_by('-created_at')
    
    return render(request, 'ecommerce/my_reviews.html', {
        'user_reviews': user_reviews
    })

