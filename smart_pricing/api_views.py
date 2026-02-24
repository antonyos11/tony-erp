"""
Smart Pricing API Views
واجهات API للتسعير الذكي
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import PricingRule, SmartQuote
from .models_extended import (
    Competitor, CompetitorPrice, PricingStrategy, SeasonalPricing,
    PriceHistory, PricingGoal, PriceAlert, ProductPricingProfile,
    BundlePricing
)
from .serializers_extended import (
    PricingRuleSerializer, SmartQuoteSerializer, SmartQuoteCreateSerializer,
    CompetitorSerializer, CompetitorPriceSerializer, CompetitorPriceCreateSerializer,
    PricingStrategySerializer, SeasonalPricingSerializer,
    PriceHistorySerializer, PricingGoalSerializer, PriceAlertSerializer,
    ProductPricingProfileSerializer, BundlePricingSerializer,
    PriceCalculationRequestSerializer, PriceCalculationResponseSerializer,
    BulkPriceCalculationRequestSerializer, AutoPricingRequestSerializer,
    PriceSimulationRequestSerializer
)
from .pricing_engine import SmartPricingEngine, PriceOptimizer, CompetitorAnalyzer
from .services import AutoPricingService, CompetitorMonitoringService, AlertService, PricingReportService


class PricingRuleViewSet(viewsets.ModelViewSet):
    """API لقواعد التسعير"""
    queryset = PricingRule.objects.filter(is_active=True)
    serializer_class = PricingRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PricingRule.objects.filter(is_active=True)
        method = self.request.query_params.get('method')
        category = self.request.query_params.get('category')
        
        if method:
            queryset = queryset.filter(method=method)
        if category:
            queryset = queryset.filter(product_category__icontains=category)
        
        return queryset


class SmartQuoteViewSet(viewsets.ModelViewSet):
    """API لعروض الأسعار الذكية"""
    queryset = SmartQuote.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SmartQuoteCreateSerializer
        return SmartQuoteSerializer
    
    def get_queryset(self):
        queryset = SmartQuote.objects.all()
        status_filter = self.request.query_params.get('status')
        customer = self.request.query_params.get('customer')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        import uuid
        quote = serializer.save(
            quote_number=f"SQ-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
            created_by=self.request.user
        )
        quote.calculate_price()
    
    @action(detail=True, methods=['post'])
    def calculate(self, request, pk=None):
        """إعادة حساب السعر"""
        quote = self.get_object()
        quote.calculate_price()
        return Response(SmartQuoteSerializer(quote).data)
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """إرسال العرض للعميل"""
        quote = self.get_object()
        quote.status = 'sent'
        quote.save()
        return Response({'status': 'sent', 'quote_number': quote.quote_number})


class CompetitorViewSet(viewsets.ModelViewSet):
    """API للمنافسين"""
    queryset = Competitor.objects.filter(is_active=True)
    serializer_class = CompetitorSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True)
    def prices(self, request, pk=None):
        """أسعار المنافس"""
        competitor = self.get_object()
        prices = CompetitorPrice.objects.filter(competitor=competitor).order_by('-recorded_at')[:50]
        return Response(CompetitorPriceSerializer(prices, many=True).data)
    
    @action(detail=False)
    def analysis(self, request):
        """تحليل المنافسين"""
        analyzer = CompetitorAnalyzer()
        result = analyzer.analyze_market_position()
        return Response(result)


class CompetitorPriceViewSet(viewsets.ModelViewSet):
    """API لأسعار المنافسين"""
    queryset = CompetitorPrice.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CompetitorPriceCreateSerializer
        return CompetitorPriceSerializer
    
    def get_queryset(self):
        queryset = CompetitorPrice.objects.all()
        competitor = self.request.query_params.get('competitor')
        product = self.request.query_params.get('product')
        
        if competitor:
            queryset = queryset.filter(competitor_id=competitor)
        if product:
            queryset = queryset.filter(product_id=product)
        
        return queryset.order_by('-recorded_at')
    
    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class PricingStrategyViewSet(viewsets.ModelViewSet):
    """API لاستراتيجيات التسعير"""
    queryset = PricingStrategy.objects.filter(is_active=True)
    serializer_class = PricingStrategySerializer
    permission_classes = [IsAuthenticated]


class SeasonalPricingViewSet(viewsets.ModelViewSet):
    """API للتسعير الموسمي"""
    queryset = SeasonalPricing.objects.all()
    serializer_class = SeasonalPricingSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False)
    def active(self, request):
        """المواسم النشطة حالياً"""
        today = timezone.now().date()
        active = SeasonalPricing.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        )
        return Response(SeasonalPricingSerializer(active, many=True).data)


class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API لتاريخ الأسعار"""
    queryset = PriceHistory.objects.all()
    serializer_class = PriceHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PriceHistory.objects.all()
        product = self.request.query_params.get('product')
        reason = self.request.query_params.get('reason')
        
        if product:
            queryset = queryset.filter(product_id=product)
        if reason:
            queryset = queryset.filter(reason=reason)
        
        return queryset.order_by('-changed_at')


class PricingGoalViewSet(viewsets.ModelViewSet):
    """API لأهداف التسعير"""
    queryset = PricingGoal.objects.all()
    serializer_class = PricingGoalSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """تحديث تقدم الهدف"""
        goal = self.get_object()
        current_value = request.data.get('current_value')
        if current_value is not None:
            goal.current_value = current_value
            goal.save()
        return Response(PricingGoalSerializer(goal).data)


class PriceAlertViewSet(viewsets.ModelViewSet):
    """API لتنبيهات الأسعار"""
    queryset = PriceAlert.objects.all()
    serializer_class = PriceAlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PriceAlert.objects.all()
        is_actioned = self.request.query_params.get('is_actioned')
        priority = self.request.query_params.get('priority')
        alert_type = self.request.query_params.get('type')
        
        if is_actioned is not None:
            queryset = queryset.filter(is_actioned=is_actioned.lower() == 'true')
        if priority:
            queryset = queryset.filter(priority=priority)
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """تحديد كمقروء"""
        alert = self.get_object()
        alert.is_read = True
        alert.save()
        return Response({'status': 'read'})
    
    @action(detail=True, methods=['post'])
    def mark_actioned(self, request, pk=None):
        """تحديد كمعالج"""
        alert = self.get_object()
        alert.is_actioned = True
        alert.actioned_by = request.user
        alert.actioned_at = timezone.now()
        alert.save()
        return Response({'status': 'actioned'})
    
    @action(detail=False)
    def pending(self, request):
        """التنبيهات المعلقة"""
        service = AlertService()
        alerts = service.get_pending_alerts()
        return Response(alerts)


class ProductPricingProfileViewSet(viewsets.ModelViewSet):
    """API لملفات تسعير المنتجات"""
    queryset = ProductPricingProfile.objects.all()
    serializer_class = ProductPricingProfileSerializer
    permission_classes = [IsAuthenticated]


class BundlePricingViewSet(viewsets.ModelViewSet):
    """API لتسعير الحزم"""
    queryset = BundlePricing.objects.filter(is_active=True)
    serializer_class = BundlePricingSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """إعادة حساب أسعار الحزمة"""
        bundle = self.get_object()
        bundle.calculate_prices()
        return Response(BundlePricingSerializer(bundle).data)


# ============ Smart Pricing API Endpoints ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_optimal_price(request):
    """
    حساب السعر الأمثل للمنتج
    
    POST /api/smart-pricing/calculate/
    {
        "product_id": 1,
        "strategy": "balanced",
        "include_competitor_analysis": true,
        "include_demand_analysis": true,
        "include_seasonality": true
    }
    """
    serializer = PriceCalculationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    from inventory.models import Product
    product = get_object_or_404(Product, id=serializer.validated_data['product_id'])
    
    engine = SmartPricingEngine()
    result = engine.calculate_optimal_price(
        product,
        strategy=serializer.validated_data['strategy'],
        include_competitor_analysis=serializer.validated_data['include_competitor_analysis'],
        include_demand_analysis=serializer.validated_data['include_demand_analysis'],
        include_seasonality=serializer.validated_data['include_seasonality']
    )
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_calculate_prices(request):
    """
    حساب الأسعار لعدة منتجات
    
    POST /api/smart-pricing/bulk-calculate/
    {
        "product_ids": [1, 2, 3],
        "strategy": "balanced"
    }
    """
    serializer = BulkPriceCalculationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    from inventory.models import Product
    
    engine = SmartPricingEngine()
    results = []
    
    for product_id in serializer.validated_data['product_ids']:
        try:
            product = Product.objects.get(id=product_id)
            result = engine.calculate_optimal_price(
                product,
                strategy=serializer.validated_data['strategy']
            )
            results.append({
                'product_id': product_id,
                'success': True,
                'result': result
            })
        except Product.DoesNotExist:
            results.append({
                'product_id': product_id,
                'success': False,
                'error': 'Product not found'
            })
    
    return Response({
        'count': len(results),
        'results': results
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_auto_pricing(request):
    """
    تشغيل التسعير التلقائي
    
    POST /api/smart-pricing/auto-pricing/
    {
        "strategy": "balanced",
        "category_id": null,
        "apply_immediately": false,
        "requires_approval": true
    }
    """
    serializer = AutoPricingRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    service = AutoPricingService()
    result = service.auto_update_prices(
        category=serializer.validated_data.get('category_id'),
        strategy=serializer.validated_data['strategy'],
        apply_immediately=serializer.validated_data['apply_immediately'],
        requires_approval=serializer.validated_data['requires_approval'],
        updated_by=request.user
    )
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_price_simulation(request):
    """
    محاكاة تغيير السعر
    
    POST /api/smart-pricing/simulate/
    {
        "product_id": 1,
        "price_changes": [-20, -10, 0, 10, 20],
        "demand_elasticity": -1.5
    }
    """
    serializer = PriceSimulationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    from inventory.models import Product
    product = get_object_or_404(Product, id=serializer.validated_data['product_id'])
    
    optimizer = PriceOptimizer()
    result = optimizer.run_price_simulation(
        product,
        price_changes=serializer.validated_data['price_changes'],
        demand_elasticity=serializer.validated_data['demand_elasticity']
    )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_stats(request):
    """
    إحصائيات لوحة التحكم
    
    GET /api/smart-pricing/dashboard/
    """
    service = PricingReportService()
    data = service.get_pricing_dashboard_data()
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_price_comparison(request, product_id):
    """
    مقارنة السعر مع المنافسين
    
    GET /api/smart-pricing/compare/<product_id>/
    """
    from inventory.models import Product
    product = get_object_or_404(Product, id=product_id)
    
    analyzer = CompetitorAnalyzer()
    result = analyzer.get_price_comparison(product)
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pricing_reports(request):
    """
    تقارير التسعير
    
    GET /api/smart-pricing/reports/?type=history&days=90
    """
    report_type = request.query_params.get('type', 'history')
    days = int(request.query_params.get('days', 90))
    
    service = PricingReportService()
    
    if report_type == 'history':
        data = service.get_price_history_report(days=days)
    elif report_type == 'competitor':
        data = service.get_competitor_analysis_report()
    elif report_type == 'profitability':
        data = service.get_profitability_report()
    else:
        data = {'error': 'Invalid report type'}
    
    return Response(data)
