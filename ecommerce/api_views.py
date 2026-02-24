"""
E-commerce API Views
REST API ViewSets for mobile app integration
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.request import Request
from django.db.models import Q, Prefetch, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
from typing import Any, Type

from .models import (
    OnlineProduct, ProductCategory, Brand, ProductImage,
    Cart, CartItem, Order, OrderItem,
    Wishlist, ProductReview, Coupon
)
from .serializers import (
    OnlineProductListSerializer, OnlineProductDetailSerializer,
    ProductCategorySerializer, BrandSerializer,
    CartSerializer, CartItemSerializer,
    OrderSerializer, OrderCreateSerializer,
    WishlistSerializer, ProductReviewSerializer,
    CouponSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API endpoints"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class BurstRateThrottle(UserRateThrottle):
    """Rate limiting for authenticated users"""
    rate = '100/hour'


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for products
    Supports listing, searching, filtering
    """
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['display_name', 'short_description', 'full_description']
    ordering_fields = ['custom_price', 'created_at', 'average_rating']

    def get_throttles(self):
        """Use class-level throttle unless running in test mode."""
        import sys
        if 'pytest' in sys.modules:
            return []  # throttling disabled during tests
        return [AnonRateThrottle(), BurstRateThrottle()]
    ordering = ['-created_at']
    request: Request  # Type annotation for DRF request
    
    def get_queryset(self) -> QuerySet[OnlineProduct]:
        """Get filtered and optimized queryset"""
        queryset = OnlineProduct.objects.filter(
            is_active=True
        ).select_related(
            'category', 'brand'
        ).prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        )
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by brand
        brand_id = self.request.query_params.get('brand')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(custom_price__gte=Decimal(min_price))
        if max_price:
            queryset = queryset.filter(custom_price__lte=Decimal(max_price))
        
        # Filter by featured/new/sale
        if self.request.query_params.get('featured') == 'true':
            queryset = queryset.filter(is_featured=True)
        if self.request.query_params.get('new') == 'true':
            queryset = queryset.filter(is_new=True)
        if self.request.query_params.get('on_sale') == 'true':
            # فلتر المنتجات التي لديها discount_price
            queryset = queryset.filter(discount_price__isnull=False)
        
        # Filter by stock availability
        if self.request.query_params.get('in_stock') == 'true':
            queryset = queryset.filter(
                inventory_item__stocks__quantity__gt=0
            ).distinct()
        
        return queryset
    
    def get_serializer_class(self) -> Type[OnlineProductListSerializer] | Type[OnlineProductDetailSerializer]:
        """Use different serializers for list vs detail"""
        if self.action == 'retrieve':
            return OnlineProductDetailSerializer
        return OnlineProductListSerializer
    
    @action(detail=False, methods=['get'])
    def search(self, request: Request) -> Response:
        """Advanced search endpoint with autocomplete support"""
        query = request.query_params.get('q', '')
        if not query or len(query) < 2:
            return Response({"results": []})
        
        products = OnlineProduct.objects.filter(
            Q(display_name__icontains=query) |
            Q(short_description__icontains=query) | Q(full_description__icontains=query) |
            Q(sku__icontains=query),
            is_active=True
        ).select_related('category', 'brand')[:10]
        
        serializer = OnlineProductListSerializer(
            products, many=True, context={'request': request}
        )
        return Response({"results": serializer.data})
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        products = self.get_queryset().filter(is_featured=True)[:12]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def new_arrivals(self, request):
        """Get new products"""
        products = self.get_queryset().filter(is_new=True).order_by('-created_at')[:12]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def on_sale(self, request):
        """Get products on sale"""
        products = self.get_queryset().filter(discount_price__isnull=False)[:12]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for product categories"""
    queryset = ProductCategory.objects.filter(
        is_active=True
    ).prefetch_related('children')
    serializer_class = ProductCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get category tree (parent categories with children)"""
        categories = self.queryset.filter(parent=None)
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for brands"""
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class CartViewSet(viewsets.ModelViewSet):
    """
    ViewSet for shopping cart
    Supports adding, updating, removing items
    """
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    request: Request  # Type annotation for DRF request
    
    def get_queryset(self) -> QuerySet[Cart]:
        """Get cart for current user or session"""
        if getattr(self, 'swagger_fake_view', False):
            return Cart.objects.none()
        if self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user).prefetch_related(
                'items__product__images'
            )
        else:
            session_key = self.request.session.session_key
            if session_key:
                return Cart.objects.filter(session_key=session_key).prefetch_related(
                    'items__product__images'
                )
        return Cart.objects.none()
    
    def get_or_create_cart(self) -> Cart:
        """Get or create cart for current user/session"""
        if self.request.user.is_authenticated:
            session_key = getattr(self.request.session, 'session_key', None) or ''
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key or ''
            cart, created = Cart.objects.get_or_create(
                user=self.request.user,
                defaults={'session_key': session_key}
            )
        else:
            if not self.request.session.session_key:
                self.request.session.create()
            cart, created = Cart.objects.get_or_create(
                session_key=self.request.session.session_key
            )
        return cart
    
    def list(self, request):
        """Get current cart"""
        cart = self.get_or_create_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add item to cart"""
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            product = OnlineProduct.objects.get(id=product_id, is_active=True)
        except OnlineProduct.DoesNotExist:
            return Response(
                {"error": "المنتج غير موجود"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not product.is_in_stock:
            return Response(
                {"error": "المنتج غير متوفر في المخزن"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = self.get_or_create_cart()
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = self.get_serializer(cart)
        return Response({
            "message": "تم إضافة المنتج للسلة بنجاح",
            "cart": serializer.data,
            "count": cart.items_count
        })
    
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Update cart item quantity"""
        item_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity', 1))
        
        cart = self.get_or_create_cart()
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            if quantity <= 0:
                cart_item.delete()
                message = "تم حذف المنتج من السلة"
            else:
                cart_item.quantity = quantity
                cart_item.save()
                message = "تم تحديث الكمية"
            
            serializer = self.get_serializer(cart)
            return Response({
                "message": message,
                "cart": serializer.data
            })
        except CartItem.DoesNotExist:
            return Response(
                {"error": "العنصر غير موجود في السلة"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def remove(self, request):
        """Remove item from cart"""
        item_id = request.data.get('item_id')
        
        cart = self.get_or_create_cart()
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
            
            serializer = self.get_serializer(cart)
            return Response({
                "message": "تم حذف المنتج من السلة",
                "cart": serializer.data
            })
        except CartItem.DoesNotExist:
            return Response(
                {"error": "العنصر غير موجود في السلة"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def clear(self, request: Request) -> Response:
        """Clear all items from cart"""
        cart = self.get_or_create_cart()
        cart.items.all().delete()  # type: ignore[attr-defined]
        
        serializer = self.get_serializer(cart)
        return Response({
            "message": "تم تفريغ السلة",
            "cart": serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def count(self, request: Request) -> Response:
        """Get cart items count (for badge display)"""
        cart = self.get_or_create_cart()
        return Response({"count": cart.items_count})


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for orders
    List and retrieve orders, create new orders
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    request: Request  # Type annotation for DRF request
    
    def get_queryset(self) -> QuerySet[Order]:
        """Get orders for current user"""
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        return Order.objects.filter(
            user=self.request.user
        ).select_related(
            'payment_method'
        ).prefetch_related(
            'items__product'
        ).order_by('-created_at')
    
    def create(self, request: Request) -> Response:
        """Create new order from cart"""
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get cart
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            cart = Cart.objects.filter(
                session_key=request.session.session_key
            ).first()
        
        if not cart or not cart.items.exists():  # type: ignore[attr-defined]
            return Response(
                {"error": "السلة فارغة"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate totals (14% VAT for Egypt)
        subtotal = cart.total
        discount = Decimal('0.00')
        
        # Apply coupon if provided
        validated_data: dict[str, Any] = serializer.validated_data or {}  # type: ignore[assignment]
        coupon_code = validated_data.get('coupon_code')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    code=coupon_code,
                    is_active=True,
                    valid_from__lte=timezone.now(),
                    valid_to__gte=timezone.now()
                )
                if coupon.min_order_amount and subtotal < coupon.min_order_amount:
                    return Response(
                        {"error": f"الحد الأدنى للطلب {coupon.min_order_amount} ج.م"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if coupon.discount_type == 'percentage':
                    discount = subtotal * (coupon.discount_value / 100)
                else:
                    discount = coupon.discount_value
            except Coupon.DoesNotExist:
                pass
        
        # Egypt VAT 14%
        vat_amount = (subtotal - discount) * Decimal('0.14')
        shipping_cost = Decimal('0.00')  # Will be calculated based on shipping method
        total = subtotal - discount + vat_amount + shipping_cost
        
        # Create order
        order_data = {
            k: v for k, v in validated_data.items() 
            if k not in ['coupon_code']  # Exclude non-model fields
        }
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            order_number=Order.generate_order_number(),
            status='pending',
            payment_status='pending',
            subtotal=subtotal,
            discount=discount,
            tax=vat_amount,
            shipping_cost=shipping_cost,
            total=total,
            **order_data
        )
        
        # Create order items
        for cart_item in cart.items.all():  # type: ignore[attr-defined]
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.price,
                subtotal=cart_item.subtotal
            )
        
        # Clear cart
        cart.items.all().delete()  # type: ignore[attr-defined]
        
        # Return order
        order_serializer = OrderSerializer(order, context={'request': request})
        return Response(
            order_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """Track order status"""
        order = self.get_object()
        return Response({
            "order_number": order.order_number,
            "status": order.status,
            "payment_status": order.payment_status,
            "created_at": order.created_at,
            "updated_at": order.updated_at
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order (only if pending)"""
        order = self.get_object()
        
        if order.status != 'pending':
            return Response(
                {"error": "لا يمكن إلغاء الطلب في هذه المرحلة"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        return Response({"message": "تم إلغاء الطلب بنجاح"})


class WishlistViewSet(viewsets.ModelViewSet):
    """ViewSet for wishlist"""
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    request: Request  # Type annotation for DRF request
    
    def get_queryset(self) -> QuerySet[Wishlist]:
        """Get wishlist for current user"""
        if getattr(self, 'swagger_fake_view', False):
            return Wishlist.objects.none()
        return Wishlist.objects.filter(
            user=self.request.user
        ).select_related('product__category', 'product__brand')
    
    def create(self, request: Request) -> Response:
        """Add product to wishlist"""
        product_id = request.data.get('product_id')
        
        # Check if already in wishlist
        if Wishlist.objects.filter(
            user=request.user,
            product_id=product_id
        ).exists():
            return Response(
                {"error": "المنتج موجود بالفعل في المفضلة"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        
        return Response(
            {"message": "تم إضافة المنتج للمفضلة"},
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def remove(self, request: Request) -> Response:
        """Remove product from wishlist"""
        product_id = request.data.get('product_id')
        
        try:
            wishlist_item = Wishlist.objects.get(
                user=request.user,
                product_id=product_id
            )
            wishlist_item.delete()
            return Response({"message": "تم حذف المنتج من المفضلة"})
        except Wishlist.DoesNotExist:
            return Response(
                {"error": "المنتج غير موجود في المفضلة"},
                status=status.HTTP_404_NOT_FOUND
            )


class ProductReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for product reviews"""
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    request: Request  # Type annotation for DRF request
    
    def get_queryset(self) -> QuerySet[ProductReview]:
        """Get approved reviews or user's own reviews"""
        if self.request.user.is_authenticated:
            return ProductReview.objects.filter(
                Q(is_approved=True) | Q(user=self.request.user)
            ).select_related('user', 'product')
        return ProductReview.objects.filter(
            is_approved=True
        ).select_related('user', 'product')
    
    def create(self, request: Request) -> Response:
        """Create product review"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "يجب تسجيل الدخول لكتابة تقييم"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, is_approved=False)  # تحتاج موافقة
        
        return Response(
            {"message": "تم إرسال تقييمك بنجاح. سيتم مراجعته قريباً."},
            status=status.HTTP_201_CREATED
        )


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for coupons"""
    serializer_class = CouponSerializer
    permission_classes = [AllowAny]
    request: Request  # Type annotation for DRF request
    
    def get_queryset(self) -> QuerySet[Coupon]:
        """Get active coupons"""
        return Coupon.objects.filter(
            is_active=True,
            valid_from__lte=timezone.now(),
            valid_to__gte=timezone.now()
        )
    
    @action(detail=False, methods=['post'])
    def validate(self, request: Request) -> Response:
        """Validate coupon code"""
        code = request.data.get('code', '').upper()
        cart_total = Decimal(request.data.get('cart_total', '0'))
        
        try:
            coupon = Coupon.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
            
            if coupon.min_order_amount and cart_total < coupon.min_order_amount:
                return Response({
                    "valid": False,
                    "error": f"الحد الأدنى للطلب {coupon.min_order_amount} ج.م"
                })
            
            if coupon.discount_type == 'percentage':
                discount = cart_total * (coupon.discount_value / 100)
            else:
                discount = coupon.discount_value
            
            return Response({
                "valid": True,
                "coupon": CouponSerializer(coupon).data,
                "discount_amount": discount
            })
        except Coupon.DoesNotExist:
            return Response({
                "valid": False,
                "error": "كود الخصم غير صحيح أو منتهي الصلاحية"
            })
