"""
Views ونقاط النهاية API لنظام بناء المراتب المخصصة
مع دعم الإحساس واقتراحات الذكاء الاصطناعي
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.utils import timezone
from decimal import Decimal

from .models import (
    MattressFeelingType,
    AIRecommendationConfig,
    MattressSize,
    MattressComponentCategory,
    MattressComponent,
    MattressRecommendationRule,
    CustomMattressDesign,
    DesignComponent,
    MattressTemplate,
    BuilderSettings,
    MattressOrder,
    DesignerCommission,
)
from .serializers import (
    MattressFeelingTypeSerializer,
    AIRecommendationSerializer,
    MattressSizeSerializer,
    MattressComponentCategorySerializer,
    MattressComponentSerializer,
    CustomMattressDesignSerializer,
    DesignComponentSerializer,
    MattressTemplateSerializer,
    BuilderSettingsSerializer,
    CalculatePriceSerializer,
    GetRecommendationsSerializer,
    MattressOrderSerializer,
    DesignerCommissionSerializer,
    CommunityDesignSerializer,
)


class MattressSizeViewSet(viewsets.ReadOnlyModelViewSet):
    """API لأحجام المراتب"""
    queryset = MattressSize.objects.filter(is_active=True).order_by('sort_order')
    serializer_class = MattressSizeSerializer
    permission_classes = [AllowAny]


class MattressFeelingTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API لأنواع إحساس المرتبة"""
    queryset = MattressFeelingType.objects.filter(is_active=True).order_by('firmness_score')
    serializer_class = MattressFeelingTypeSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def detect(self, request):
        """كشف الإحساس تلقائياً بناءً على المكونات المختارة"""
        component_ids = request.data.get('component_ids', [])
        if not component_ids:
            return Response({'feeling': None, 'message': 'لم يتم اختيار مكونات'})
        
        components = MattressComponent.objects.filter(
            id__in=component_ids, is_active=True
        ).select_related('category')
        
        total_density = Decimal('0')
        density_count = 0
        category_types = set()
        quality_scores = {'basic': 1, 'standard': 2, 'premium': 3, 'luxury': 4}
        total_quality = 0
        quality_count = 0
        
        for comp in components:
            if comp.density:
                total_density += comp.density
                density_count += 1
            category_types.add(comp.category.category_type)
            total_quality += quality_scores.get(comp.quality_level, 2)
            quality_count += 1
        
        avg_density = float(total_density / density_count) if density_count > 0 else 40
        
        # حساب درجة الصلابة
        if avg_density < 25:
            firmness = 2
        elif avg_density < 35:
            firmness = 3
        elif avg_density < 45:
            firmness = 5
        elif avg_density < 55:
            firmness = 7
        elif avg_density < 65:
            firmness = 8
        else:
            firmness = 9
        
        if 'springs' in category_types:
            firmness = min(10, firmness + 1)
        
        # البحث عن أقرب إحساس
        feelings = MattressFeelingType.objects.filter(is_active=True)
        closest = None
        min_diff = 11
        for f in feelings:
            diff = abs(f.firmness_score - firmness)
            if diff < min_diff:
                min_diff = diff
                closest = f
        
        if closest:
            serializer = MattressFeelingTypeSerializer(closest)
            return Response({
                'feeling': serializer.data,
                'calculated_score': firmness,
                'message': f'بناءً على المكونات المختارة، إحساس المرتبة: {closest.name}'
            })
        
        return Response({'feeling': None, 'calculated_score': firmness, 'message': 'لم يتم العثور على إحساس مناسب'})


class AIRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """API لاقتراحات الذكاء الاصطناعي"""
    queryset = AIRecommendationConfig.objects.filter(is_active=True).order_by('-priority')
    serializer_class = AIRecommendationSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def get_suggestions(self, request):
        """الحصول على اقتراحات ذكية بناءً على سياق التصميم"""
        settings = BuilderSettings.get_settings()
        if not settings.enable_ai_suggestions:
            return Response({'suggestions': [], 'message': 'الاقتراحات معطلة'})
        
        # بناء سياق التصميم
        design_context = {
            'size_id': request.data.get('size_id'),
            'selected_components': request.data.get('component_ids', []),
            'selected_categories': request.data.get('category_types', []),
            'total_price': float(request.data.get('total_price', 0)),
            'total_thickness': float(request.data.get('total_thickness', 0)),
            'feeling_score': request.data.get('feeling_score', 5),
            'trigger': request.data.get('trigger', 'always'),
        }
        
        # جلب الاقتراحات المطابقة
        all_configs = AIRecommendationConfig.objects.filter(
            is_active=True
        ).select_related(
            'suggested_component', 'suggested_feeling'
        ).order_by('-priority')
        
        # تصفية حسب المحفز
        trigger = design_context.get('trigger', 'always')
        matching = []
        for config in all_configs:
            # فحص المحفز
            if config.trigger_type != 'always' and config.trigger_type != trigger:
                continue
            
            # تقييم الشروط
            if config.evaluate(design_context):
                suggestion = {
                    'id': config.id,
                    'name': config.name,
                    'message': config.message_ar,
                    'icon': config.icon,
                    'style': config.message_style,
                    'type': config.suggestion_type,
                    'data': config.suggestion_data,
                    'priority': config.priority,
                }
                
                if config.suggested_component:
                    suggestion['suggested_component'] = {
                        'id': config.suggested_component.id,
                        'name': config.suggested_component.name,
                        'price': str(config.suggested_component.base_price),
                        'category': config.suggested_component.category_id,
                    }
                
                if config.suggested_feeling:
                    suggestion['suggested_feeling'] = {
                        'id': config.suggested_feeling.id,
                        'name': config.suggested_feeling.name,
                        'firmness_score': config.suggested_feeling.firmness_score,
                    }
                
                matching.append(suggestion)
        
        # حد أقصى للاقتراحات
        max_suggestions = settings.max_ai_suggestions
        
        return Response({
            'suggestions': matching[:max_suggestions],
            'total_available': len(matching),
        })


class MattressComponentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API لفئات المكونات"""
    queryset = MattressComponentCategory.objects.filter(is_active=True).order_by('sort_order')
    serializer_class = MattressComponentCategorySerializer
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['get'])
    def components(self, request, pk=None):
        """الحصول على جميع المكونات في فئة معينة"""
        category = self.get_object()
        components = category.components.filter(is_active=True).order_by('sort_order')
        serializer = MattressComponentSerializer(components, many=True)
        return Response(serializer.data)


class MattressComponentViewSet(viewsets.ReadOnlyModelViewSet):
    """API لمكونات المراتب"""
    queryset = MattressComponent.objects.filter(is_active=True).select_related('category')
    serializer_class = MattressComponentSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category', 'quality_level', 'is_featured', 'is_popular']
    search_fields = ['name', 'name_en', 'description']
    ordering_fields = ['sort_order', 'popularity_score', 'base_price']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category type
        category_type = self.request.query_params.get('category_type', None)
        if category_type:
            queryset = queryset.filter(category__category_type=category_type)
        
        # Featured only
        featured = self.request.query_params.get('featured', None)
        if featured:
            queryset = queryset.filter(is_featured=True)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def calculate_price(self, request, pk=None):
        """حساب سعر المكون لحجم معين"""
        component = self.get_object()
        size_id = request.data.get('size_id')
        
        try:
            size = MattressSize.objects.get(id=size_id, is_active=True)
            price = component.calculate_price(size)
            return Response({
                'component_id': component.id,
                'size_id': size.id,
                'calculated_price': price
            })
        except MattressSize.DoesNotExist:
            return Response(
                {'error': 'حجم المرتبة غير موجود'},
                status=status.HTTP_404_NOT_FOUND
            )


class MattressTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """API لقوالب المراتب"""
    queryset = MattressTemplate.objects.filter(is_active=True).order_by('sort_order')
    serializer_class = MattressTemplateSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['target_audience', 'is_featured', 'is_popular']
    ordering_fields = ['sort_order', 'usage_count', 'starting_price']
    
    @action(detail=True, methods=['post'])
    def use_template(self, request, pk=None):
        """استخدام قالب لإنشاء تصميم جديد"""
        template = self.get_object()
        
        if not request.user.is_authenticated:
            return Response(
                {'error': 'يجب تسجيل الدخول أولاً'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # زيادة عداد الاستخدام
        template.increment_usage()
        
        # Create design from template
        # TODO: تنفيذ منطق إنشاء التصميم من القالب
        
        return Response({
            'message': 'تم استخدام القالب بنجاح',
            'template_id': template.id
        })


class CustomMattressDesignViewSet(viewsets.ModelViewSet):
    """API لتصميمات المراتب المخصصة"""
    serializer_class = CustomMattressDesignSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CustomMattressDesign.objects.none()
        user = self.request.user
        
        # Admins can see all designs
        if user.is_staff:
            return CustomMattressDesign.objects.all().select_related(
                'customer', 'mattress_size'
            ).prefetch_related('design_components__component')
        
        # Regular users see only their designs
        return CustomMattressDesign.objects.filter(
            customer=user
        ).select_related('mattress_size').prefetch_related('design_components__component')
    
    def perform_create(self, serializer):
        """إنشاء تصميم جديد"""
        serializer.save(
            customer=self.request.user,
            customer_name=self.request.user.get_full_name() or self.request.user.username,
            customer_email=self.request.user.email
        )
    
    @action(detail=True, methods=['post'])
    def add_component(self, request, pk=None):
        """إضافة مكون للتصميم"""
        design = self.get_object()
        
        # Check permissions
        if design.customer != request.user and not request.user.is_staff:
            return Response(
                {'error': 'ليس لديك صلاحية لتعديل هذا التصميم'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if design is still draft
        if design.status != 'draft':
            return Response(
                {'error': 'لا يمكن تعديل التصميم بعد إرساله'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        component_id = request.data.get('component_id')
        quantity = request.data.get('quantity', 1)
        layer_position = request.data.get('layer_position', 0)
        
        try:
            component = MattressComponent.objects.get(id=component_id, is_active=True)
            
            # Create design component
            design_component = DesignComponent.objects.create(
                design=design,
                component=component,
                quantity=quantity,
                layer_position=layer_position
            )
            
            # Update popularity
            component.increment_popularity()
            
            # Recalculate price
            design.calculate_total_price()
            design.save()
            
            serializer = DesignComponentSerializer(design_component)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except MattressComponent.DoesNotExist:
            return Response(
                {'error': 'المكون غير موجود'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_component(self, request, pk=None):
        """إزالة مكون من التصميم"""
        design = self.get_object()
        
        # Check permissions
        if design.customer != request.user and not request.user.is_staff:
            return Response(
                {'error': 'ليس لديك صلاحية لتعديل هذا التصميم'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        design_component_id = request.data.get('design_component_id')
        
        try:
            design_component = DesignComponent.objects.get(
                id=design_component_id,
                design=design
            )
            design_component.delete()
            
            # Recalculate price
            design.calculate_total_price()
            design.save()
            
            return Response({'message': 'تمت إزالة المكون بنجاح'})
            
        except DesignComponent.DoesNotExist:
            return Response(
                {'error': 'المكون غير موجود في التصميم'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def submit_for_approval(self, request, pk=None):
        """إرسال التصميم للموافقة"""
        design = self.get_object()
        
        # Check permissions
        if design.customer != request.user:
            return Response(
                {'error': 'ليس لديك صلاحية لإرسال هذا التصميم'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if design.status != 'draft':
            return Response(
                {'error': 'التصميم تم إرساله مسبقاً'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if design has components
        if not design.design_components.exists():
            return Response(
                {'error': 'يجب إضافة مكونات للتصميم أولاً'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        design.submit_for_approval()
        
        serializer = self.get_serializer(design)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """الموافقة على التصميم (للإدارة فقط)"""
        design = self.get_object()
        
        if design.status != 'pending_approval':
            return Response(
                {'error': 'التصميم ليس في انتظار الموافقة'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        design.approve(request.user)
        
        serializer = self.get_serializer(design)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """رفض التصميم (للإدارة فقط)"""
        design = self.get_object()
        
        if design.status != 'pending_approval':
            return Response(
                {'error': 'التصميم ليس في انتظار الموافقة'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'لم يتم تحديد سبب')
        design.reject(reason, request.user)
        
        serializer = self.get_serializer(design)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def calculate_price(self, request):
        """حساب السعر الإجمالي لتصميم"""
        serializer = CalculatePriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        size = serializer.validated_data['size']
        components = serializer.validated_data['components']
        
        # Calculate base price
        base_price = size.base_price
        
        # Calculate components price
        components_price = Decimal('0')
        for component in components:
            components_price += component.calculate_price(size)
        
        # Calculate total
        total_price = base_price + components_price
        
        return Response({
            'size_id': size.id,
            'base_price': base_price,
            'components_price': components_price,
            'total_price': total_price,
            'breakdown': [
                {
                    'component_id': comp.id,
                    'component_name': comp.name,
                    'price': comp.calculate_price(size)
                }
                for comp in components
            ]
        })
    
    @action(detail=False, methods=['post'])
    def get_recommendations(self, request):
        """الحصول على اقتراحات ذكية للتصميم (محسّنة)"""
        serializer = GetRecommendationsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        recommendations = []
        settings = BuilderSettings.get_settings()
        
        # 1. اقتراحات من قواعد الاقتراحات القديمة
        if settings.enable_recommendations:
            rules = MattressRecommendationRule.objects.filter(is_active=True).order_by('-priority')
            for rule in rules:
                recommendations.append({
                    'rule_id': rule.id,
                    'message': rule.message,
                    'message_type': rule.message_type,
                    'action_data': rule.action_data,
                    'source': 'rules'
                })
        
        # 2. اقتراحات الذكاء الاصطناعي الجديدة
        if settings.enable_ai_suggestions:
            design_data = serializer.validated_data.get('design_data', {})
            ai_configs = AIRecommendationConfig.objects.filter(
                is_active=True
            ).order_by('-priority')[:settings.max_ai_suggestions]
            
            for config in ai_configs:
                recommendations.append({
                    'rule_id': f'ai_{config.id}',
                    'message': config.message_ar,
                    'message_type': config.message_style,
                    'action_data': config.suggestion_data,
                    'source': 'ai',
                    'icon': config.icon,
                })
        
        return Response({
            'recommendations': recommendations[:10]
        })


# ============ API ViewSets for Orders & Commissions ============

class MattressOrderViewSet(viewsets.ModelViewSet):
    """API لطلبات المراتب"""
    serializer_class = MattressOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MattressOrder.objects.none()
        return MattressOrder.objects.filter(
            customer=self.request.user
        ).select_related('design', 'original_designer').order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """تأكيد الدفع"""
        order = self.get_object()
        if order.status != 'pending_payment':
            return Response({'error': 'الطلب ليس في انتظار الدفع'}, status=400)
        
        payment_method = request.data.get('payment_method', 'cash')
        payment_reference = request.data.get('payment_reference', '')
        
        order.mark_as_paid(payment_method, payment_reference)
        
        return Response({
            'success': True,
            'message': 'تم تأكيد الدفع بنجاح! سيتم بدء الإنتاج.',
            'order': MattressOrderSerializer(order).data
        })
    
    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """تتبع حالة الطلب"""
        order = self.get_object()
        return Response({
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'estimated_delivery': order.estimated_delivery_date,
            'production_order': order.production_order_id,
        })


class CommunityDesignViewSet(viewsets.ReadOnlyModelViewSet):
    """API لتصميمات المجتمع (المنشورة)"""
    serializer_class = CommunityDesignSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return CustomMattressDesign.objects.filter(
            is_public=True,
            published_name__gt='',
            status__in=['approved', 'completed', 'in_production'],
        ).select_related('customer', 'mattress_size', 'feeling_type').order_by('-sales_count', '-created_at')
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def purchase(self, request, pk=None):
        """شراء تصميم مجتمعي"""
        design = self.get_object()
        
        # بيانات العميل
        customer_name = request.data.get('customer_name', request.user.get_full_name() or request.user.username)
        customer_phone = request.data.get('customer_phone', '')
        customer_email = request.data.get('customer_email', request.user.email)
        shipping_address = request.data.get('shipping_address', '')
        shipping_city = request.data.get('shipping_city', 'القاهرة')
        customer_notes = request.data.get('customer_notes', '')
        
        if not shipping_address:
            return Response({'error': 'عنوان التسليم مطلوب'}, status=400)
        
        # إنشاء الطلب
        order = MattressOrder.objects.create(
            customer=request.user,
            design=design,
            is_community_purchase=True,
            original_designer=design.customer,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            subtotal=design.final_price,
            total=design.final_price,
            customer_notes=customer_notes,
        )
        
        return Response({
            'success': True,
            'message': f'تم إنشاء طلب شراء التصميم "{design.published_name}"',
            'order': MattressOrderSerializer(order).data
        })


class DesignerCommissionViewSet(viewsets.ReadOnlyModelViewSet):
    """API لعمولات المصمم"""
    serializer_class = DesignerCommissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DesignerCommission.objects.none()
        return DesignerCommission.objects.filter(
            designer=self.request.user
        ).select_related('order', 'design').order_by('-created_at')


# ============ Frontend Views ============

def builder_home(request):
    """الصفحة الرئيسية لنظام البناء"""
    settings = BuilderSettings.get_settings()
    templates = MattressTemplate.objects.filter(
        is_active=True,
        is_featured=True
    ).order_by('sort_order')[:6]
    
    context = {
        'settings': settings,
        'templates': templates,
    }
    return render(request, 'mattress_builder/home.html', context)


@login_required(login_url='/store/login/')
def builder_page(request):
    """صفحة البناء التفاعلية"""
    sizes = MattressSize.objects.filter(is_active=True).order_by('sort_order')
    categories = MattressComponentCategory.objects.filter(
        is_active=True
    ).order_by('sort_order').prefetch_related('components')
    settings = BuilderSettings.get_settings()
    feelings = MattressFeelingType.objects.filter(is_active=True).order_by('firmness_score')
    
    context = {
        'sizes': sizes,
        'categories': categories,
        'settings': settings,
        'feelings': feelings,
        'enable_feelings': settings.enable_feeling_selection,
        'enable_feeling_detection': settings.enable_feeling_detection,
        'enable_ai': settings.enable_ai_suggestions,
        'enable_community': settings.enable_community_designs,
        'enable_duplicate_detection': settings.enable_duplicate_detection,
    }
    return render(request, 'mattress_builder/builder.html', context)


@login_required(login_url='/store/login/')
def my_designs(request):
    """تصميماتي"""
    designs = CustomMattressDesign.objects.filter(
        customer=request.user
    ).select_related('mattress_size', 'feeling_type').order_by('-created_at')
    
    context = {
        'designs': designs,
    }
    return render(request, 'mattress_builder/my_designs.html', context)


@login_required(login_url='/store/login/')
def design_detail(request, design_id):
    """تفاصيل التصميم"""
    design = get_object_or_404(
        CustomMattressDesign.objects.select_related('mattress_size', 'feeling_type').prefetch_related(
            'design_components__component__category'
        ),
        id=design_id,
        customer=request.user
    )
    
    # Increment view count
    design.view_count += 1
    design.save(update_fields=['view_count'])
    
    # Orders for this design
    orders = MattressOrder.objects.filter(design=design).order_by('-created_at')
    
    # Commissions earned
    commissions = DesignerCommission.objects.filter(
        design=design, designer=request.user
    ).order_by('-created_at')
    
    context = {
        'design': design,
        'orders': orders,
        'commissions': commissions,
    }
    return render(request, 'mattress_builder/design_detail.html', context)


def community_designs(request):
    """صفحة تصميمات المجتمع - تصفح تصميمات عملاء آخرين"""
    designs = CustomMattressDesign.objects.filter(
        is_public=True,
        published_name__gt='',
        status__in=['approved', 'completed', 'in_production'],
    ).select_related('customer', 'mattress_size', 'feeling_type').order_by('-sales_count', '-created_at')
    
    # فلترة
    size_filter = request.GET.get('size')
    feeling_filter = request.GET.get('feeling')
    sort = request.GET.get('sort', 'popular')
    
    if size_filter:
        designs = designs.filter(mattress_size_id=size_filter)
    if feeling_filter:
        designs = designs.filter(feeling_type_id=feeling_filter)
    
    if sort == 'newest':
        designs = designs.order_by('-created_at')
    elif sort == 'price_low':
        designs = designs.order_by('final_price')
    elif sort == 'price_high':
        designs = designs.order_by('-final_price')
    else:  # popular
        designs = designs.order_by('-sales_count', '-view_count')
    
    sizes = MattressSize.objects.filter(is_active=True).order_by('sort_order')
    feelings = MattressFeelingType.objects.filter(is_active=True).order_by('firmness_score')
    
    context = {
        'designs': designs,
        'sizes': sizes,
        'feelings': feelings,
        'current_sort': sort,
        'current_size': size_filter,
        'current_feeling': feeling_filter,
    }
    return render(request, 'mattress_builder/community_designs.html', context)


def community_design_detail(request, design_id):
    """تفاصيل تصميم مجتمعي"""
    design = get_object_or_404(
        CustomMattressDesign.objects.select_related(
            'customer', 'mattress_size', 'feeling_type'
        ).prefetch_related('design_components__component__category'),
        id=design_id,
        is_public=True,
    )
    
    design.view_count += 1
    design.save(update_fields=['view_count'])
    
    context = {
        'design': design,
        'is_own': request.user == design.customer if request.user.is_authenticated else False,
    }
    return render(request, 'mattress_builder/community_design_detail.html', context)


@login_required(login_url='/store/login/')
def my_orders(request):
    """طلباتي للمراتب"""
    orders = MattressOrder.objects.filter(
        customer=request.user
    ).select_related('design', 'design__mattress_size', 'design__feeling_type', 'original_designer').order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'mattress_builder/my_orders.html', context)


@login_required(login_url='/store/login/')
def order_detail(request, order_id):
    """تفاصيل طلب مرتبة"""
    order = get_object_or_404(
        MattressOrder.objects.select_related(
            'design', 'design__mattress_size', 'design__feeling_type', 'original_designer'
        ),
        id=order_id,
        customer=request.user,
    )
    
    context = {
        'order': order,
    }
    return render(request, 'mattress_builder/order_detail.html', context)


@login_required(login_url='/store/login/')
def checkout_design(request, design_id):
    """صفحة الدفع لتصميم مرتبة"""
    design = get_object_or_404(
        CustomMattressDesign.objects.select_related('mattress_size', 'feeling_type').prefetch_related(
            'design_components__component__category'
        ),
        id=design_id,
    )
    
    # التحقق: هل هو تصميم المستخدم أو تصميم مجتمعي
    is_own = design.customer == request.user
    is_community = design.is_public and not is_own
    
    if not is_own and not is_community:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('غير مسموح')
    
    # كشف التصميمات المكررة
    settings = BuilderSettings.get_settings()
    duplicates = []
    if settings.enable_duplicate_detection and is_own:
        if not design.design_hash:
            design.design_hash = design.generate_design_hash()
            design.save(update_fields=['design_hash'])
        duplicates = design.find_duplicate_designs()[:3]
    
    context = {
        'design': design,
        'is_own': is_own,
        'is_community': is_community,
        'duplicates': duplicates,
        'original_designer': design.customer if is_community else None,
    }
    return render(request, 'mattress_builder/checkout.html', context)


@login_required(login_url='/store/login/')
def place_mattress_order(request, design_id):
    """إنشاء طلب مرتبة بعد الدفع"""
    if request.method != 'POST':
        return redirect('ecommerce:mattress_builder:checkout_design', design_id=design_id)
    
    from django.http import JsonResponse
    
    design = get_object_or_404(CustomMattressDesign, id=design_id)
    
    is_own = design.customer == request.user
    is_community = design.is_public and not is_own
    
    if not is_own and not is_community:
        return JsonResponse({'success': False, 'message': 'غير مسموح'})
    
    # بيانات المشتري
    customer_name = request.POST.get('customer_name', request.user.get_full_name() or request.user.username)
    customer_phone = request.POST.get('customer_phone', '')
    customer_email = request.POST.get('customer_email', request.user.email)
    shipping_address = request.POST.get('shipping_address', '')
    shipping_city = request.POST.get('shipping_city', 'القاهرة')
    customer_notes = request.POST.get('customer_notes', '')
    payment_method = request.POST.get('payment_method', 'cash')
    published_name = request.POST.get('published_name', '')
    make_public = request.POST.get('make_public') == 'on'
    
    if not shipping_address:
        return JsonResponse({'success': False, 'message': 'عنوان التسليم مطلوب'})
    
    # تحديث اسم النشر إذا طلب
    if is_own and published_name and not design.published_name:
        design.published_name = published_name
        if make_public:
            design.is_public = True
        design.save(update_fields=['published_name', 'is_public'])
    
    # حساب المبالغ
    design.calculate_total_price()
    design.save()
    subtotal = design.final_price
    shipping_cost = Decimal('0')
    tax = subtotal * Decimal('0.14')
    total = subtotal + shipping_cost + tax
    
    # إنشاء الطلب
    order = MattressOrder.objects.create(
        customer=request.user,
        design=design,
        is_community_purchase=is_community,
        original_designer=design.customer if is_community else None,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        shipping_address=shipping_address,
        shipping_city=shipping_city,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=tax,
        total=total,
        customer_notes=customer_notes,
    )
    
    # تأكيد الدفع مباشرة (كاش أو عند التسليم)
    order.mark_as_paid(payment_method=payment_method)
    
    return JsonResponse({
        'success': True,
        'message': f'تم إنشاء الطلب بنجاح! رقم الطلب: {order.order_number}',
        'order_id': order.id,
        'redirect': f'/store/mattress-builder/orders/{order.id}/',
    })


@login_required(login_url='/store/login/')
def my_commissions(request):
    """عمولاتي كمصمم"""
    commissions = DesignerCommission.objects.filter(
        designer=request.user
    ).select_related('order', 'design').order_by('-created_at')
    
    total_earned = sum(c.commission_amount for c in commissions if c.status in ['approved', 'paid'])
    total_pending = sum(c.commission_amount for c in commissions if c.status == 'pending')
    
    # تصميماتي المنشورة
    published_designs = CustomMattressDesign.objects.filter(
        customer=request.user,
        is_public=True,
        published_name__gt='',
    ).order_by('-sales_count')
    
    context = {
        'commissions': commissions,
        'total_earned': total_earned,
        'total_pending': total_pending,
        'published_designs': published_designs,
    }
    return render(request, 'mattress_builder/my_commissions.html', context)
