"""
E-commerce API Optimization Views
==================================
Performance optimized API endpoints for Egypt market
Week 2 Phase 1 - January 2026
"""

from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET
from django.core.cache import cache
from django.db import models
from django.db.models import Avg, Count, Q, Prefetch, F
from django.utils import timezone
from datetime import timedelta
import json
from typing import TypeAlias

from .models import (
    OnlineProduct, ProductCategory, Brand, ProductReview, 
    Cart, CartItem, Wishlist, Order
)

# Type aliases for compatibility (Pylance-friendly)
Product: TypeAlias = OnlineProduct
Category: TypeAlias = ProductCategory


# =============================================
# CACHED API ENDPOINTS
# =============================================

@require_GET
@cache_page(60 * 5)  # Cache for 5 minutes
def api_products_list(request):
    """
    Optimized products list with caching and filtering
    """
    # Get query parameters
    category = request.GET.get('category')
    brand = request.GET.get('brand')
    brands = request.GET.get('brands', '').split(',') if request.GET.get('brands') else []
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    rating = request.GET.get('rating')
    in_stock = request.GET.get('in_stock')
    search = request.GET.get('q') or request.GET.get('search')
    sort_by = request.GET.get('sort', 'relevance')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    
    # Build cache key
    cache_key = f"products_list_{category}_{brand}_{price_min}_{price_max}_{rating}_{sort_by}_{page}"
    cached_result = cache.get(cache_key)
    
    if cached_result and not search:
        return JsonResponse(cached_result)
    
    # Base queryset with optimized select
    queryset = OnlineProduct.objects.select_related(
        'category', 'brand'
    ).prefetch_related(
        Prefetch(
            'reviews',
            queryset=ProductReview.objects.only('rating'),
            to_attr='_reviews_for_rating'
        )
    ).filter(
        is_active=True
    ).only(
        'id', 'display_name', 'slug', 'custom_price', 'discount_price', 'compare_price', 
        'main_image', 'category_id', 'brand_id',
        'created_at', 'inventory_item_id'
    )
    
    # Apply filters
    if category:
        queryset = queryset.filter(
            Q(category__slug=category) | Q(category__parent__slug=category)
        )
    
    if brand:
        queryset = queryset.filter(brand__slug=brand)
    
    if brands:
        queryset = queryset.filter(brand__slug__in=brands)
    
    if price_min:
        queryset = queryset.filter(custom_price__gte=float(price_min))
    
    if price_max:
        queryset = queryset.filter(custom_price__lte=float(price_max))
    
    if rating:
        queryset = queryset.annotate(
            avg_rating=Avg('reviews__rating')
        ).filter(avg_rating__gte=int(rating))
    
    if in_stock == 'true':
        queryset = queryset.filter(inventory_item__stocks__quantity__gt=0).distinct()
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(category__name__icontains=search) |
            Q(brand__name__icontains=search)
        )
    
    # Apply sorting
    sort_mapping = {
        'relevance': '-id',
        'price_low': 'custom_price',
        'price_high': '-custom_price',
        'newest': '-created_at',
        'rating': '-avg_rating',
        'popular': '-views_count',
        'bestseller': '-sales_count'
    }
    
    if sort_by in sort_mapping:
        if sort_by == 'rating':
            queryset = queryset.annotate(avg_rating=Avg('reviews__rating'))
        queryset = queryset.order_by(sort_mapping[sort_by])
    
    # Pagination
    total_count = queryset.count()
    start = (page - 1) * limit
    end = start + limit
    products = queryset[start:end]
    
    # Serialize
    results = []
    for product in products:
        # Calculate average rating
        reviews = getattr(product, '_reviews_for_rating', [])
        avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
        
        # Calculate discount
        product_price = product.discount_price if product.discount_price else product.custom_price
        # Handle None values
        if product_price is None:
            product_price = 0
        if product.compare_price is None:
            product.compare_price = 0
            
        discount = None
        if product.compare_price and product.compare_price > product_price and product_price > 0:
            discount = int(((product.compare_price - product_price) / product.compare_price) * 100)
        
        # Get stock from inventory_item if available
        try:
            stock = product.inventory_item.current_stock if product.inventory_item else 0
        except Exception:
            stock = 0
        
        results.append({
            'id': product.id,
            'name': product.display_name,
            'slug': product.slug,
            'price': float(product_price) if product_price else 0.0,
            'original_price': float(product.compare_price) if product.compare_price else None,
            'discount': discount,
            'image': product.main_image.url if product.main_image else None,
            'in_stock': stock > 0,
            'stock': stock,
            'category_id': product.category_id,
            'category_name': product.category.name if product.category else None,
            'brand_id': product.brand_id,
            'brand_name': product.brand.name if product.brand else None,
            'rating': round(avg_rating, 1),
            'reviews_count': len(reviews),
            'is_new': product.created_at > timezone.now() - timedelta(days=30)
        })
    
    response_data = {
        'count': total_count,
        'page': page,
        'pages': (total_count + limit - 1) // limit,
        'next': page < (total_count + limit - 1) // limit,
        'previous': page > 1,
        'results': results
    }
    
    # Cache the result
    if not search:
        cache.set(cache_key, response_data, 60 * 5)
    
    return JsonResponse(response_data)


@require_GET
@cache_page(60 * 10)  # Cache for 10 minutes
def api_categories_list(request):
    """
    Optimized categories list with product counts
    """
    cache_key = 'categories_list_v2'
    cached = cache.get(cache_key)
    
    if cached:
        return JsonResponse({'categories': cached})
    
    categories = Category.objects.filter(
        is_active=True
    ).annotate(
        product_count=Count('online_products', filter=Q(online_products__is_active=True))
    ).values(
        'id', 'name', 'slug', 'image', 'parent_id', 'product_count'
    ).order_by('order', 'name')
    
    # Build tree structure
    category_list = list(categories)
    
    # Convert to tree
    categories_by_id = {c['id']: {**c, 'children': []} for c in category_list}
    root_categories = []
    
    for cat in category_list:
        if cat['parent_id']:
            parent = categories_by_id.get(cat['parent_id'])
            if parent:
                parent['children'].append(categories_by_id[cat['id']])
        else:
            root_categories.append(categories_by_id[cat['id']])
    
    cache.set(cache_key, root_categories, 60 * 10)
    
    return JsonResponse({'categories': root_categories})


@require_GET
@cache_page(60 * 10)
def api_brands_list(request):
    """
    Optimized brands list
    """
    brands = Brand.objects.filter(
        is_active=True
    ).annotate(
        product_count=Count('online_products', filter=Q(online_products__is_active=True))
    ).values(
        'id', 'name', 'slug', 'logo', 'product_count'
    ).order_by('name')
    
    return JsonResponse({'brands': list(brands)})


@require_GET
def api_product_search(request):
    """
    Instant search with suggestions
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 8))
    
    if len(query) < 2:
        return JsonResponse({'products': [], 'suggestions': [], 'categories': []})
    
    # Search products
    products = OnlineProduct.objects.filter(
        is_active=True
    ).filter(
        Q(name__icontains=query) |
        Q(sku__icontains=query)
    ).select_related(
        'category', 'brand'
    ).only(
        'id', 'display_name', 'slug', 'custom_price', 'discount_price', 'main_image', 'category__name'
    )[:limit]
    
    product_results = [{
        'id': p.id,
        'name': p.display_name,
        'slug': p.slug,
        'price': float(p.discount_price if p.discount_price else p.custom_price),
        'image': p.main_image.url if p.main_image else None,
        'category_name': p.category.name if p.category else None
    } for p in products]
    
    # Search categories
    categories = Category.objects.filter(
        is_active=True,
        name__icontains=query
    ).annotate(
        product_count=Count('online_products', filter=Q(online_products__is_active=True))
    ).values(
        'id', 'name', 'slug', 'product_count'
    )[:3]
    
    # Generate suggestions (simple implementation)
    suggestions = []
    if product_results:
        # Extract common words from product names
        words = set()
        for p in product_results:
            words.update(p['name'].split()[:3])
        suggestions = [w for w in words if query.lower() in w.lower()][:5]
    
    return JsonResponse({
        'products': product_results,
        'categories': list(categories),
        'suggestions': suggestions
    })


@require_GET
@cache_page(60 * 5)
def api_product_detail(request, product_id):
    """
    Optimized product detail with related data
    """
    try:
        product = OnlineProduct.objects.select_related(
            'category', 'brand'
        ).prefetch_related(
            'images',
            Prefetch(
                'reviews',
                queryset=ProductReview.objects.select_related('user').order_by('-created_at')[:5],
                to_attr='_recent_reviews'
            )
        ).get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'المنتج غير موجود'}, status=404)
    
    # Get related products
    related_products = OnlineProduct.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(
        id=product.id
    ).only(
        'id', 'display_name', 'slug', 'custom_price', 'discount_price', 'main_image'
    )[:6]
    
    # Reviews stats
    reviews = product.reviews.all()
    reviews_count = reviews.count()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Rating breakdown
    rating_breakdown = {}
    for i in range(1, 6):
        rating_breakdown[i] = reviews.filter(rating=i).count()
    
    # Calculate discount
    product_price = product.discount_price if product.discount_price else product.custom_price
    discount = None
    if product.compare_price and product.compare_price > product_price:
        discount = int(((product.compare_price - product_price) / product.compare_price) * 100)
    
    # Get stock from inventory_item if available
    try:
        stock = product.inventory_item.current_stock if product.inventory_item else 0
    except:
        stock = 0
    
    data = {
        'id': product.id,
        'name': product.display_name,
        'slug': product.slug,
        'description': product.full_description or product.short_description,
        'price': float(product_price),
        'original_price': float(product.compare_price) if product.compare_price else None,
        'discount': discount,
        'image': product.main_image.url if product.main_image else None,
        'images': [img.image.url for img in product.images.all()],
        'in_stock': stock > 0,
        'stock': stock,
        'sku': getattr(product, 'sku', ''),
        'category': {
            'id': product.category.id,
            'name': product.category.name,
            'slug': product.category.slug
        } if product.category else None,
        'brand': {
            'id': product.brand.id,
            'name': product.brand.name,
            'slug': product.brand.slug
        } if product.brand else None,
        'rating': round(avg_rating, 1),
        'reviews_count': reviews_count,
        'rating_breakdown': rating_breakdown,
        'recent_reviews': [{
            'id': r.id,
            'user_name': r.user.get_full_name() or r.user.username if r.user else 'عميل',
            'rating': r.rating,
            'comment': r.comment,
            'created_at': r.created_at.isoformat()
        } for r in getattr(product, '_recent_reviews', [])],
        'related_products': [{
            'id': p.id,
            'name': p.display_name,
            'slug': p.slug,
            'price': float(p.discount_price if p.discount_price else p.custom_price),
            'image': p.main_image.url if p.main_image else None
        } for p in related_products],
        'is_new': product.created_at > timezone.now() - timedelta(days=30)
    }
    
    return JsonResponse(data)


@require_GET
@cache_page(60 * 15)  # Cache for 15 minutes
def api_homepage_data(request):
    """
    Aggregated homepage data for faster loading
    """
    cache_key = 'homepage_data_v2'
    cached = cache.get(cache_key)
    
    if cached:
        return JsonResponse(cached)
    
    # Featured categories
    categories = Category.objects.filter(
        is_active=True,
        parent__isnull=True
    ).annotate(
        product_count=Count('online_products', filter=Q(online_products__is_active=True))
    ).values(
        'id', 'name', 'slug', 'image'
    ).order_by('order')[:8]
    
    # Featured products
    featured_products = OnlineProduct.objects.filter(
        is_active=True,
        is_featured=True
    ).select_related('category').only(
        'id', 'display_name', 'slug', 'custom_price', 'discount_price', 'compare_price', 'main_image', 'category__name'
    )[:8]
    
    # New arrivals
    new_products = OnlineProduct.objects.filter(
        is_active=True,
        created_at__gte=timezone.now() - timedelta(days=30)
    ).select_related('category').only(
        'id', 'display_name', 'slug', 'custom_price', 'discount_price', 'compare_price', 'main_image', 'category__name'
    ).order_by('-created_at')[:8]
    
    # Best sellers (simplified - based on order count)
    bestsellers = OnlineProduct.objects.filter(
        is_active=True
    ).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count').select_related('category').only(
        'id', 'display_name', 'slug', 'custom_price', 'discount_price', 'compare_price', 'main_image', 'category__name'
    )[:8]
    
    # Flash sales
    flash_sales = OnlineProduct.objects.filter(
        is_active=True,
        compare_price__isnull=False,
        compare_price__gt=0,
        custom_price__isnull=False
    ).filter(
        custom_price__lt=models.F('compare_price') * 0.7  # At least 30% off
    ).select_related('category').only(
        'id', 'display_name', 'slug', 'custom_price', 'discount_price', 'compare_price', 'main_image', 'category__name'
    )[:6]
    
    def serialize_products(products):
        result = []
        for p in products:
            product_price = p.discount_price if p.discount_price else p.custom_price
            # Handle None values
            if product_price is None:
                product_price = 0
            if p.compare_price is None:
                p.compare_price = 0
                
            discount = None
            if p.compare_price and p.compare_price > product_price and product_price > 0:
                discount = int(((p.compare_price - product_price) / p.compare_price) * 100)
            
            # Get stock from inventory_item if available
            try:
                stock = p.inventory_item.current_stock if p.inventory_item else 0
            except Exception:
                stock = 0
            
            result.append({
                'id': p.id,
                'name': p.display_name,
                'slug': p.slug,
                'price': float(product_price) if product_price else 0.0,
                'original_price': float(p.compare_price) if p.compare_price else None,
                'discount': discount,
                'image': p.main_image.url if p.main_image else None,
                'in_stock': stock > 0,
                'category_name': p.category.name if p.category else None
            })
        return result
    
    data = {
        'categories': list(categories),
        'featured_products': serialize_products(featured_products),
        'new_products': serialize_products(new_products),
        'bestsellers': serialize_products(bestsellers),
        'flash_sales': serialize_products(flash_sales)
    }
    
    cache.set(cache_key, data, 60 * 15)
    
    return JsonResponse(data)


# =============================================
# CART API (Session-based for guests)
# =============================================

def api_cart_get(request):
    """
    Get cart for current user/session
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related('product').all()
    else:
        # Session-based cart
        cart_data = request.session.get('cart', {})
        product_ids = list(cart_data.keys())
        products = OnlineProduct.objects.filter(id__in=product_ids).only(
            'id', 'display_name', 'custom_price', 'discount_price', 'main_image', 'inventory_item_id'
        )
        
        items = []
        for product in products:
            qty = cart_data.get(str(product.id), 0)
            if qty > 0:
                # Get stock from inventory_item
                try:
                    stock = product.inventory_item.current_stock if product.inventory_item else 0
                except Exception:
                    stock = 0
                
                product_price = product.discount_price if product.discount_price else product.custom_price
                items.append({
                    'id': product.id,
                    'name': product.display_name,
                    'price': float(product_price),
                    'image': product.main_image.url if product.main_image else None,
                    'quantity': qty,
                    'in_stock': stock >= qty,
                    'subtotal': float(product_price * qty)
                })
        
        total = sum(item['subtotal'] for item in items)
        
        return JsonResponse({
            'items': items,
            'count': sum(item['quantity'] for item in items),
            'total': total
        })
    
    # Authenticated user cart
    cart_items = []
    for item in items:
        try:
            stock = item.product.inventory_item.current_stock if item.product.inventory_item else 0
        except Exception:
            stock = 0
        
        product_price = item.product.discount_price if item.product.discount_price else item.product.custom_price
        cart_items.append({
            'id': item.product.id,
            'name': item.product.display_name,
            'price': float(product_price),
            'image': item.product.main_image.url if item.product.main_image else None,
            'quantity': item.quantity,
            'in_stock': stock >= item.quantity,
            'subtotal': float(product_price * item.quantity)
        })
    
    return JsonResponse({
        'items': cart_items,
        'count': sum(item['quantity'] for item in cart_items),
        'total': sum(item['subtotal'] for item in cart_items)
    })


# =============================================
# WISHLIST API
# =============================================

def api_wishlist_get(request):
    """
    Get wishlist for current user
    """
    if not request.user.is_authenticated:
        # Session-based wishlist
        wishlist_ids = request.session.get('wishlist', [])
        products = OnlineProduct.objects.filter(
            id__in=wishlist_ids,
            is_active=True
        ).only(
            'id', 'display_name', 'slug', 'custom_price', 'discount_price', 'main_image', 'inventory_item_id'
        )
        
        return JsonResponse({
            'items': [{
                'id': p.id,
                'name': p.display_name,
                'slug': p.slug,
                'price': float(p.discount_price if p.discount_price else p.custom_price),
                'image': p.main_image.url if p.main_image else None
            } for p in products]
        })
    
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product').only(
        'product__id', 'product__display_name', 'product__slug', 
        'product__custom_price', 'product__discount_price', 'product__main_image'
    )
    
    return JsonResponse({
        'items': [{
            'id': item.product.id,
            'name': item.product.display_name,
            'slug': item.product.slug,
            'price': float(item.product.discount_price if item.product.discount_price else item.product.custom_price),
            'image': item.product.main_image.url if item.product.main_image else None
        } for item in wishlist_items]
    })
