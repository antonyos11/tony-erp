"""
Smart Pricing Views - Extended
واجهات عرض التسعير الذكي المتقدمة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from .models import PricingRule, SmartQuote, ProductionLineRecommendation, AutoMaterialRelease
from .models_extended import (
    Competitor, CompetitorPrice, PricingStrategy, SeasonalPricing,
    PriceHistory, PricingGoal, PriceAlert, PricingSimulation,
    ProductPricingProfile, BundlePricing
)
from .services import (
    AutoPricingService, CompetitorMonitoringService,
    AlertService, PricingReportService
)
from .pricing_engine import SmartPricingEngine, PriceOptimizer, CompetitorAnalyzer


@login_required
def pricing_dashboard(request):
    """لوحة تحكم التسعير الذكي"""
    
    report_service = PricingReportService()
    dashboard_data = report_service.get_pricing_dashboard_data()
    
    # أحدث التنبيهات
    alert_service = AlertService()
    pending_alerts = alert_service.get_pending_alerts()[:5]
    
    # أحدث تغييرات الأسعار
    recent_changes = PriceHistory.objects.order_by('-changed_at')[:10]
    
    # المواسم النشطة
    today = timezone.now().date()
    active_seasons = SeasonalPricing.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    )
    
    # أهداف التسعير
    goals = PricingGoal.objects.filter(
        status='active',
        period_end__gte=today
    )[:5]
    
    context = {
        'title': 'لوحة تحكم التسعير الذكي',
        'dashboard': dashboard_data,
        'pending_alerts': pending_alerts,
        'recent_changes': recent_changes,
        'active_seasons': active_seasons,
        'goals': goals,
    }
    return render(request, 'smart_pricing/dashboard.html', context)


@login_required
def pricing_rules_list(request):
    """قائمة قواعد التسعير"""
    rules = PricingRule.objects.filter(is_active=True).order_by('-created_at')
    
    # البحث والفلترة
    search = request.GET.get('search', '')
    method = request.GET.get('method', '')
    
    if search:
        rules = rules.filter(
            Q(name__icontains=search) | 
            Q(product_category__icontains=search)
        )
    if method:
        rules = rules.filter(method=method)
    
    paginator = Paginator(rules, 12)
    page = request.GET.get('page', 1)
    rules = paginator.get_page(page)
    
    context = {
        'rules': rules,
        'title': 'قواعد التسعير الذكي',
        'search': search,
        'method': method,
        'methods': PricingRule.PRICING_METHOD_CHOICES,
    }
    return render(request, 'smart_pricing/rules_list.html', context)


@login_required
def rule_detail(request, rule_id):
    """تفاصيل قاعدة التسعير"""
    rule = get_object_or_404(PricingRule, id=rule_id)
    
    # الإحصائيات
    quotes_count = SmartQuote.objects.filter(pricing_rule=rule).count()
    
    context = {
        'rule': rule,
        'title': f'قاعدة التسعير: {rule.name}',
        'quotes_count': quotes_count,
    }
    return render(request, 'smart_pricing/rule_detail.html', context)


@login_required
def rule_create(request):
    """إنشاء قاعدة تسعير جديدة"""
    
    if request.method == 'POST':
        try:
            rule = PricingRule()
            rule.name = request.POST.get('name', '')
            rule.product_category = request.POST.get('product_category', '')
            rule.method = request.POST.get('method', 'cost_plus')
            rule.is_active = request.POST.get('is_active') == 'on'
            
            # معاملات التسعير
            rule.base_cost_multiplier = Decimal(request.POST.get('base_cost_multiplier', '1.0'))
            rule.quantity_discount_threshold = int(request.POST.get('quantity_discount_threshold', '100'))
            rule.quantity_discount_rate = Decimal(request.POST.get('quantity_discount_rate', '5.0'))
            
            # هامش الربح
            rule.min_profit_margin = Decimal(request.POST.get('min_profit_margin', '15.0'))
            rule.target_profit_margin = Decimal(request.POST.get('target_profit_margin', '25.0'))
            rule.max_profit_margin = Decimal(request.POST.get('max_profit_margin', '50.0'))
            
            # معاملات الحجم
            rule.size_multiplier_small = Decimal(request.POST.get('size_multiplier_small', '0.8'))
            rule.size_multiplier_medium = Decimal(request.POST.get('size_multiplier_medium', '1.0'))
            rule.size_multiplier_large = Decimal(request.POST.get('size_multiplier_large', '1.3'))
            rule.size_multiplier_xlarge = Decimal(request.POST.get('size_multiplier_xlarge', '1.6'))
            
            # معاملات التعقيد
            rule.complexity_simple = Decimal(request.POST.get('complexity_simple', '1.0'))
            rule.complexity_medium = Decimal(request.POST.get('complexity_medium', '1.2'))
            rule.complexity_complex = Decimal(request.POST.get('complexity_complex', '1.5'))
            
            # AI
            rule.use_ai_pricing = request.POST.get('method') == 'ai_dynamic'
            
            rule.save()
            
            messages.success(request, f'تم إنشاء قاعدة التسعير "{rule.name}" بنجاح')
            return redirect('smart_pricing:rules_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء القاعدة: {str(e)}')
    
    context = {
        'title': 'إضافة قاعدة تسعير',
    }
    return render(request, 'smart_pricing/rule_create.html', context)


@login_required
def rule_edit(request, rule_id):
    """تعديل قاعدة تسعير"""
    rule = get_object_or_404(PricingRule, id=rule_id)
    
    if request.method == 'POST':
        try:
            rule.name = request.POST.get('name', rule.name)
            rule.product_category = request.POST.get('product_category', '')
            rule.method = request.POST.get('method', 'cost_plus')
            rule.is_active = request.POST.get('is_active') == 'on'
            
            # معاملات التسعير
            rule.base_cost_multiplier = Decimal(request.POST.get('base_cost_multiplier', '1.0'))
            rule.quantity_discount_threshold = int(request.POST.get('quantity_discount_threshold', '100'))
            rule.quantity_discount_rate = Decimal(request.POST.get('quantity_discount_rate', '5.0'))
            
            # هامش الربح
            rule.min_profit_margin = Decimal(request.POST.get('min_profit_margin', '15.0'))
            rule.target_profit_margin = Decimal(request.POST.get('target_profit_margin', '25.0'))
            rule.max_profit_margin = Decimal(request.POST.get('max_profit_margin', '50.0'))
            
            # معاملات الحجم
            rule.size_multiplier_small = Decimal(request.POST.get('size_multiplier_small', '0.8'))
            rule.size_multiplier_medium = Decimal(request.POST.get('size_multiplier_medium', '1.0'))
            rule.size_multiplier_large = Decimal(request.POST.get('size_multiplier_large', '1.3'))
            rule.size_multiplier_xlarge = Decimal(request.POST.get('size_multiplier_xlarge', '1.6'))
            
            # معاملات التعقيد
            rule.complexity_simple = Decimal(request.POST.get('complexity_simple', '1.0'))
            rule.complexity_medium = Decimal(request.POST.get('complexity_medium', '1.2'))
            rule.complexity_complex = Decimal(request.POST.get('complexity_complex', '1.5'))
            
            rule.use_ai_pricing = request.POST.get('method') == 'ai_dynamic'
            
            rule.save()
            
            messages.success(request, f'تم تحديث قاعدة التسعير "{rule.name}" بنجاح')
            return redirect('smart_pricing:rules_list')
            
        except Exception as e:
            messages.error(request, f'خطأ في تحديث القاعدة: {str(e)}')
    
    context = {
        'rule': rule,
        'title': f'تعديل: {rule.name}',
    }
    return render(request, 'smart_pricing/rule_edit.html', context)


@login_required
def rule_delete(request, rule_id):
    """حذف قاعدة تسعير"""
    rule = get_object_or_404(PricingRule, id=rule_id)
    
    if request.method == 'POST':
        name = rule.name
        rule.delete()
        messages.success(request, f'تم حذف قاعدة التسعير "{name}" بنجاح')
        return redirect('smart_pricing:rules_list')
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def smart_quotes_list(request):
    """قائمة عروض الأسعار الذكية"""
    quotes = SmartQuote.objects.all().order_by('-created_at')
    
    # الفلترة
    status = request.GET.get('status', '')
    if status:
        quotes = quotes.filter(status=status)
    
    paginator = Paginator(quotes, 20)
    page = request.GET.get('page', 1)
    quotes = paginator.get_page(page)
    
    context = {
        'quotes': quotes,
        'title': 'عروض الأسعار الذكية',
        'status': status,
        'statuses': SmartQuote.STATUS_CHOICES,
    }
    return render(request, 'smart_pricing/quotes_list.html', context)


@login_required
def create_smart_quote(request):
    """إنشاء عرض سعر ذكي جديد"""
    
    if request.method == 'POST':
        try:
            from crm.models import Customer
            
            quote = SmartQuote()
            quote.customer = Customer.objects.get(id=request.POST.get('customer_id'))
            quote.product_name = request.POST.get('product_name')
            quote.description = request.POST.get('description', '')
            quote.quantity = int(request.POST.get('quantity', 1))
            quote.size = request.POST.get('size', 'medium')
            quote.complexity = request.POST.get('complexity', 'medium')
            
            # الأبعاد
            if request.POST.get('width'):
                quote.width = Decimal(request.POST.get('width'))
            if request.POST.get('height'):
                quote.height = Decimal(request.POST.get('height'))
            if request.POST.get('depth'):
                quote.depth = Decimal(request.POST.get('depth'))
            
            # قاعدة التسعير
            if request.POST.get('pricing_rule_id'):
                quote.pricing_rule = PricingRule.objects.get(id=request.POST.get('pricing_rule_id'))
            
            # إنشاء رقم العرض
            import uuid
            quote.quote_number = f"SQ-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            quote.created_by = request.user
            quote.save()
            
            # حساب السعر
            quote.calculate_price()
            
            messages.success(request, f'تم إنشاء عرض السعر {quote.quote_number} بنجاح')
            return redirect('smart_pricing:quote_detail', quote_id=quote.id)
            
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء العرض: {str(e)}')
    
    from crm.models import Customer
    
    context = {
        'title': 'إنشاء عرض سعر ذكي',
        'customers': Customer.objects.all()[:100],
        'pricing_rules': PricingRule.objects.filter(is_active=True),
        'sizes': SmartQuote.SIZE_CHOICES,
        'complexities': SmartQuote.COMPLEXITY_CHOICES,
    }
    return render(request, 'smart_pricing/create_quote.html', context)


@login_required
def quote_detail(request, quote_id):
    """تفاصيل عرض السعر"""
    quote = get_object_or_404(SmartQuote, id=quote_id)
    recommendations = quote.recommendations.order_by('-recommendation_score')[:5]
    
    context = {
        'quote': quote,
        'title': f'عرض السعر: {quote.quote_number}',
        'recommendations': recommendations,
    }
    return render(request, 'smart_pricing/quote_detail.html', context)


@login_required
def competitors_list(request):
    """قائمة المنافسين"""
    competitors = Competitor.objects.filter(is_active=True).order_by('-market_share')
    
    # البحث
    search = request.GET.get('search', '')
    if search:
        competitors = competitors.filter(name__icontains=search)
    
    # إضافة إحصائيات
    for competitor in competitors:
        competitor.prices_count = CompetitorPrice.objects.filter(
            competitor=competitor,
            recorded_at__gte=timezone.now() - timedelta(days=90)
        ).count()
    
    context = {
        'competitors': competitors,
        'title': 'المنافسين',
        'search': search,
    }
    return render(request, 'smart_pricing/competitors_list.html', context)


@login_required
def competitor_detail(request, competitor_id):
    """تفاصيل منافس"""
    competitor = get_object_or_404(Competitor, id=competitor_id)
    
    # أسعار المنافس
    prices = CompetitorPrice.objects.filter(
        competitor=competitor
    ).order_by('-recorded_at')[:50]
    
    # إحصائيات
    price_stats = CompetitorPrice.objects.filter(
        competitor=competitor,
        recorded_at__gte=timezone.now() - timedelta(days=90)
    ).aggregate(
        avg_price=Avg('price'),
        total_products=Count('id')
    )
    
    context = {
        'competitor': competitor,
        'prices': prices,
        'stats': price_stats,
        'title': f'المنافس: {competitor.name}',
    }
    return render(request, 'smart_pricing/competitor_detail.html', context)


@login_required
def add_competitor_price(request):
    """إضافة سعر منافس"""
    
    if request.method == 'POST':
        try:
            service = CompetitorMonitoringService()
            result = service.add_competitor_price(
                competitor_id=int(request.POST.get('competitor_id')),
                product_name=request.POST.get('product_name'),
                price=Decimal(request.POST.get('price')),
                source=request.POST.get('source', 'website'),
                recorded_by=request.user,
                source_url=request.POST.get('source_url', ''),
            )
            messages.success(request, 'تم إضافة السعر بنجاح')
            return redirect('smart_pricing:competitor_detail', competitor_id=request.POST.get('competitor_id'))
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'title': 'إضافة سعر منافس',
        'competitors': Competitor.objects.filter(is_active=True),
        'sources': CompetitorPrice.SOURCE_CHOICES,
    }
    return render(request, 'smart_pricing/add_competitor_price.html', context)


@login_required
def price_history_list(request):
    """تاريخ الأسعار"""
    
    history = PriceHistory.objects.all().order_by('-changed_at')
    
    # الفلترة
    reason = request.GET.get('reason', '')
    if reason:
        history = history.filter(reason=reason)
    
    paginator = Paginator(history, 30)
    page = request.GET.get('page', 1)
    history = paginator.get_page(page)
    
    context = {
        'history': history,
        'title': 'تاريخ الأسعار',
        'reason': reason,
        'reasons': PriceHistory.REASON_CHOICES,
    }
    return render(request, 'smart_pricing/price_history.html', context)


@login_required
def alerts_list(request):
    """قائمة التنبيهات"""
    
    alerts = PriceAlert.objects.all().order_by('-created_at')
    
    # الفلترة
    alert_type = request.GET.get('type', '')
    priority = request.GET.get('priority', '')
    status = request.GET.get('status', 'pending')
    
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    if priority:
        alerts = alerts.filter(priority=priority)
    if status == 'pending':
        alerts = alerts.filter(is_actioned=False)
    elif status == 'actioned':
        alerts = alerts.filter(is_actioned=True)
    
    paginator = Paginator(alerts, 20)
    page = request.GET.get('page', 1)
    alerts = paginator.get_page(page)
    
    context = {
        'alerts': alerts,
        'title': 'تنبيهات الأسعار',
        'alert_type': alert_type,
        'priority': priority,
        'status': status,
        'types': PriceAlert.ALERT_TYPE_CHOICES,
        'priorities': PriceAlert.PRIORITY_CHOICES,
    }
    return render(request, 'smart_pricing/alerts_list.html', context)


@login_required
def mark_alert_actioned(request, alert_id):
    """تحديد التنبيه كمعالج"""
    
    service = AlertService()
    if service.mark_as_actioned(alert_id, request.user):
        messages.success(request, 'تم تحديد التنبيه كمعالج')
    else:
        messages.error(request, 'خطأ في تحديث التنبيه')
    
    return redirect('smart_pricing:alerts_list')


@login_required
def seasonal_pricing_list(request):
    """قائمة التسعير الموسمي"""
    
    seasons = SeasonalPricing.objects.all().order_by('-start_date')
    
    # تحديد المواسم النشطة
    today = timezone.now().date()
    for season in seasons:
        season.is_currently_active = season.is_active and season.start_date <= today <= season.end_date
    
    context = {
        'seasons': seasons,
        'title': 'التسعير الموسمي',
    }
    return render(request, 'smart_pricing/seasonal_list.html', context)


@login_required
def strategies_list(request):
    """قائمة استراتيجيات التسعير"""
    
    strategies = PricingStrategy.objects.filter(is_active=True).order_by('-priority')
    
    context = {
        'strategies': strategies,
        'title': 'استراتيجيات التسعير',
    }
    return render(request, 'smart_pricing/strategies_list.html', context)


@login_required
def goals_list(request):
    """قائمة أهداف التسعير"""
    
    goals = PricingGoal.objects.all().order_by('-period_start')
    
    # إضافة نسبة التقدم
    for goal in goals:
        goal.progress = goal.progress_percentage()
    
    context = {
        'goals': goals,
        'title': 'أهداف التسعير',
    }
    return render(request, 'smart_pricing/goals_list.html', context)


@login_required
def bundles_list(request):
    """قائمة الحزم"""
    
    bundles = BundlePricing.objects.filter(is_active=True).order_by('-created_at')
    
    context = {
        'bundles': bundles,
        'title': 'تسعير الحزم',
    }
    return render(request, 'smart_pricing/bundles_list.html', context)


@login_required
def bundle_detail(request, bundle_id):
    """تفاصيل الحزمة"""
    from .models_extended import BundlePricingItem
    
    bundle = get_object_or_404(BundlePricing, id=bundle_id)
    items = BundlePricingItem.objects.filter(bundle=bundle)
    
    context = {
        'bundle': bundle,
        'items': items,
        'title': f'الحزمة: {bundle.name}',
    }
    return render(request, 'smart_pricing/bundle_detail.html', context)


@login_required
def pricing_optimizer(request):
    """محسن الأسعار"""
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        strategy = request.POST.get('strategy', 'balanced')
        
        if product_id:
            from inventory.models import Product
            product = get_object_or_404(Product, id=product_id)
            
            engine = SmartPricingEngine()
            result = engine.calculate_optimal_price(
                product,
                strategy=strategy,
                include_competitor_analysis=True,
                include_demand_analysis=True,
                include_seasonality=True
            )
            
            return render(request, 'smart_pricing/optimizer_result.html', {
                'product': product,
                'result': result,
                'title': f'تحسين سعر: {product.name}',
            })
    
    from inventory.models import Product
    
    context = {
        'title': 'محسن الأسعار',
        'products': Product.objects.filter(is_active=True)[:100],
        'strategies': [
            ('aggressive', 'عدواني - أسعار منخفضة'),
            ('conservative', 'محافظ - أسعار عالية'),
            ('balanced', 'متوازن'),
            ('premium', 'فاخر'),
            ('penetration', 'اختراق السوق'),
        ],
    }
    return render(request, 'smart_pricing/optimizer.html', context)


@login_required
def price_simulation(request):
    """محاكاة التسعير"""
    
    result = None
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        elasticity = float(request.POST.get('elasticity', -1.5))
        
        if product_id:
            from inventory.models import Product
            product = get_object_or_404(Product, id=product_id)
            
            optimizer = PriceOptimizer()
            result = optimizer.run_price_simulation(
                product,
                price_changes=[-20, -15, -10, -5, 0, 5, 10, 15, 20],
                demand_elasticity=elasticity
            )
    
    from inventory.models import Product
    
    context = {
        'title': 'محاكاة التسعير',
        'products': Product.objects.filter(is_active=True)[:100],
        'result': result,
    }
    return render(request, 'smart_pricing/simulation.html', context)


@login_required
def auto_pricing(request):
    """التسعير التلقائي"""
    
    result = None
    
    if request.method == 'POST':
        strategy = request.POST.get('strategy', 'balanced')
        apply_now = request.POST.get('apply_now') == 'on'
        requires_approval = request.POST.get('requires_approval') == 'on'
        
        service = AutoPricingService()
        result = service.auto_update_prices(
            strategy=strategy,
            apply_immediately=apply_now,
            requires_approval=requires_approval,
            updated_by=request.user
        )
        
        if apply_now:
            messages.success(request, f'تم تحديث {result["updated"]} منتج')
        else:
            messages.info(request, f'تم تحليل {result["processed"]} منتج')
    
    context = {
        'title': 'التسعير التلقائي',
        'result': result,
        'strategies': [
            ('aggressive', 'عدواني'),
            ('conservative', 'محافظ'),
            ('balanced', 'متوازن'),
            ('premium', 'فاخر'),
            ('penetration', 'اختراق السوق'),
        ],
    }
    return render(request, 'smart_pricing/auto_pricing.html', context)


@login_required
def reports(request):
    """تقارير التسعير"""
    
    report_type = request.GET.get('type', 'history')
    
    report_service = PricingReportService()
    
    if report_type == 'history':
        data = report_service.get_price_history_report()
    elif report_type == 'competitor':
        data = report_service.get_competitor_analysis_report()
    elif report_type == 'profitability':
        data = report_service.get_profitability_report()
    else:
        data = {}
    
    context = {
        'title': 'تقارير التسعير',
        'report_type': report_type,
        'data': data,
    }
    return render(request, 'smart_pricing/reports.html', context)


@login_required
def material_releases_list(request):
    """قائمة أوامر صرف المواد"""
    releases = AutoMaterialRelease.objects.all().order_by('-created_at')
    
    paginator = Paginator(releases, 20)
    page = request.GET.get('page', 1)
    releases = paginator.get_page(page)
    
    context = {
        'releases': releases,
        'title': 'أوامر صرف المواد الآلية',
    }
    return render(request, 'smart_pricing/releases_list.html', context)



@login_required
def competition_based_calculation(request):
    """حساب السعر بناءً على المنافسة"""
    result = None
    selected_product = None
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        if product_id:
            from inventory.models import Product
            selected_product = get_object_or_404(Product, id=product_id)
            analyzer = CompetitorAnalyzer()
            result = analyzer.get_price_comparison(selected_product)
    
    from inventory.models import Product
    products = Product.objects.filter(is_active=True)[:100]
    
    context = {
        'title': 'حساب السعر التنافسي',
        'products': products,
        'result': result,
        'selected_product': selected_product,
    }
    return render(request, 'smart_pricing/competition_calculation.html', context)


@login_required
def value_based_calculation(request):
    """حساب السعر على أساس القيمة"""
    result = None
    selected_product = None
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        if product_id:
            from inventory.models import Product
            selected_product = get_object_or_404(Product, id=product_id)
            engine = SmartPricingEngine()
            result = engine.calculate_optimal_price(selected_product, strategy='premium')
    
    from inventory.models import Product
    products = Product.objects.filter(is_active=True)[:100]
    
    context = {
        'title': 'حساب السعر على أساس القيمة',
        'products': products,
        'result': result,
        'selected_product': selected_product,
    }
    return render(request, 'smart_pricing/value_calculation.html', context)


@login_required
def cost_plus_calculation(request):
    """حساب السعر بطريقة التكلفة زائد هامش"""
    result = None
    selected_product = None
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        markup = Decimal(request.POST.get('markup', '30'))
        if product_id:
            from inventory.models import Product
            selected_product = get_object_or_404(Product, id=product_id)
            cost = getattr(selected_product, 'cost', 0) or getattr(selected_product, 'purchase_price', 0) or Decimal('0')
            suggested_price = cost * (1 + markup / 100)
            result = {
                'cost': float(cost),
                'markup_percent': float(markup),
                'suggested_price': float(suggested_price),
                'profit': float(suggested_price - cost),
            }
    
    from inventory.models import Product
    products = Product.objects.filter(is_active=True)[:100]
    
    context = {
        'title': 'حساب السعر: تكلفة + هامش',
        'products': products,
        'result': result,
        'selected_product': selected_product,
    }
    return render(request, 'smart_pricing/cost_plus_calculation.html', context)


@login_required
def margin_based_calculation(request):
    """حساب السعر على أساس الهامش المستهدف"""
    result = None
    selected_product = None
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        target_margin = Decimal(request.POST.get('target_margin', '20'))
        
        if product_id:
            from inventory.models import Product
            selected_product = get_object_or_404(Product, id=product_id)
            cost = getattr(selected_product, 'cost', 0) or getattr(selected_product, 'purchase_price', 0) or Decimal('0')
            
            # Price = Cost / (1 - Margin%)
            if target_margin < 100:
                suggested_price = cost / (1 - (target_margin / 100))
            else:
                suggested_price = 0
                
            result = {
                'cost': float(cost),
                'target_margin': float(target_margin),
                'suggested_price': float(suggested_price),
                'profit': float(suggested_price - cost),
            }
    
    from inventory.models import Product
    products = Product.objects.filter(is_active=True)[:100]
    
    context = {
        'title': 'حساب السعر: الهامش المستهدف',
        'products': products,
        'result': result,
        'selected_product': selected_product,
    }
    return render(request, 'smart_pricing/margin_based_calculation.html', context)


@login_required
def cost_based_calculation(request):
    """حساب السعر بناءً على التكلفة الكلية (Cost Based)"""
    result = None
    selected_product = None
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        overhead_percent = Decimal(request.POST.get('overhead_percent', '15'))
        profit_percent = Decimal(request.POST.get('profit_percent', '20'))
        
        if product_id:
            from inventory.models import Product
            selected_product = get_object_or_404(Product, id=product_id)
            
            # Base Cost
            material_cost = getattr(selected_product, 'cost', 0) or getattr(selected_product, 'purchase_price', 0) or Decimal('0')
            
            # Overhead
            overhead_cost = material_cost * (overhead_percent / 100)
            total_cost = material_cost + overhead_cost
            
            # Profit
            profit_amount = total_cost * (profit_percent / 100)
            final_price = total_cost + profit_amount
            
            result = {
                'material_cost': float(material_cost),
                'overhead_percent': float(overhead_percent),
                'overhead_cost': float(overhead_cost),
                'total_cost': float(total_cost),
                'profit_percent': float(profit_percent),
                'profit_amount': float(profit_amount),
                'final_price': float(final_price),
                'currency': 'ج.م'
            }
            
    from inventory.models import Product
    products = Product.objects.filter(is_active=True)[:100]
    
    context = {
        'title': 'حساب السعر القائم على التكلفة',
        'products': products,
        'result': result,
        'selected_product': selected_product,
    }
    return render(request, 'smart_pricing/cost_based_calculation.html', context)


@login_required
def ai_recommendation_calculation(request):
    """توصية السعر بالذكاء الاصطناعي"""
    result = None
    selected_product = None
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        
        if product_id:
            from inventory.models import Product
            selected_product = get_object_or_404(Product, id=product_id)
            
            # محاكاة تحليل AI
            import random
            base_price = float(getattr(selected_product, 'price', 100) or 100)
            
            recommended_min = base_price * random.uniform(0.95, 1.0)
            recommended_max = base_price * random.uniform(1.05, 1.15)
            confidence = random.randint(85, 98)
            
            factors = [
                {'name': 'الطلب المتوقع', 'impact': 'positive', 'value': 'مرتفع'},
                {'name': 'أسعار المنافسين', 'impact': 'negative', 'value': 'أقل بـ 5%'},
                {'name': 'الموسمية', 'impact': 'positive', 'value': 'موسم ذروة'},
                {'name': 'تكلفة المخزون', 'impact': 'neutral', 'value': 'مستقر'},
            ]
            
            result = {
                'recommended_price': round((recommended_min + recommended_max) / 2, 2),
                'range_min': round(recommended_min, 2),
                'range_max': round(recommended_max, 2),
                'confidence': confidence,
                'factors': factors,
                'currency': 'ج.م'
            }
            
    from inventory.models import Product
    products = Product.objects.filter(is_active=True)[:100]
    
    context = {
        'title': 'توصيات الذكاء الاصطناعي',
        'products': products,
        'result': result,
        'selected_product': selected_product,
    }
    return render(request, 'smart_pricing/ai_recommendation.html', context)



@login_required
def production_line_suggestion(request):
    """ترشيح خط الإنتاج المناسب"""
    result = None
    selected_product = None
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 100))
        if product_id:
            from inventory.models import Product
            selected_product = get_object_or_404(Product, id=product_id)
            # Suggest production line based on quantity and product type
            if quantity > 1000:
                suggested_line = 'خط الإنتاج الكبير (A)'
                efficiency = 95
            elif quantity > 100:
                suggested_line = 'خط الإنتاج المتوسط (B)'
                efficiency = 85
            else:
                suggested_line = 'خط الإنتاج الصغير (C)'
                efficiency = 75
            result = {
                'product_name': selected_product.name,
                'quantity': quantity,
                'suggested_line': suggested_line,
                'efficiency': efficiency,
                'estimated_time_hours': round(quantity / (efficiency / 10), 2),
            }
    
    from inventory.models import Product
    products = Product.objects.filter(is_active=True)[:100]
    
    context = {
        'title': 'ترشيح خط الإنتاج',
        'products': products,
        'result': result,
        'selected_product': selected_product,
    }
    return render(request, 'smart_pricing/production_line_suggestion.html', context)


@login_required
def production_line_capacity(request):
    """تحليل السعة الإنتاجية لخط الإنتاج"""
    # محاكاة بيانات السعة
    import random
    
    stages = [
        {'name': 'التجهيز', 'load': random.randint(60, 90), 'capacity': 1000},
        {'name': 'التقطيع', 'load': random.randint(70, 95), 'capacity': 800},
        {'name': 'التجميع', 'load': random.randint(50, 85), 'capacity': 500},
        {'name': 'التغليف', 'load': random.randint(60, 90), 'capacity': 1200},
    ]
    
    total_load = sum(s['load'] for s in stages) / len(stages)
    bottleneck = max(stages, key=lambda x: x['load'])
    
    context = {
        'title': 'تحليل السعة الإنتاجية',
        'subtitle': 'تحليل تفصيلي لسعة خطوط الإنتاج والقدرة التشغيلية',
        'active_tab': 'capacity',
        'stages': stages,
        'overall_utilization': round(total_load, 1),
        'bottleneck': bottleneck,
        'daily_target': 5000,
        'current_output': random.randint(3500, 4800),
    }
    return render(request, 'smart_pricing/production_line_capacity.html', context)


@login_required
def production_line_efficiency(request):
    """تحليل كفاءة خط الإنتاج"""
    import random
    
    # حساب OEE (كفاءة المعدات الشاملة)
    availability = random.uniform(85, 98)
    performance = random.uniform(80, 95)
    quality = random.uniform(90, 99)
    oee = (availability * performance * quality) / 10000
    
    downtime_logs = [
        {'time': '09:15', 'duration': '15 دقيقة', 'reason': 'تغيير مواد خام', 'type': 'planned'},
        {'time': '13:40', 'duration': '10 دقائق', 'reason': 'توقف طارئ - سير النقل', 'type': 'unplanned'},
        {'time': '16:00', 'duration': '5 دقائق', 'reason': 'فحص جودة دوري', 'type': 'planned'},
    ]
    
    context = {
        'title': 'كفاءة خط الإنتاج',
        'subtitle': 'مؤشرات الأداء الرئيسية وكفاءة المعدات الشاملة (OEE)',
        'active_tab': 'efficiency',
        'oee': round(oee * 100, 1),
        'availability': round(availability, 1),
        'performance': round(performance, 1),
        'quality': round(quality, 1),
        'downtime_logs': downtime_logs,
        'mtbf': 140, # Mean Time Between Failures (hours)
        'mttr': 25,  # Mean Time To Repair (minutes)
    }
    return render(request, 'smart_pricing/production_line_efficiency.html', context)


@login_required
def production_line_ai(request):
    """اقتراحات الذكاء الاصطناعي لخط الإنتاج"""
    import random
    from datetime import datetime, timedelta
    
    predictions = [
        {'title': 'تنبؤ بالصيانة', 'message': 'احتمالية تعطل "آلة القص 3" خلال 48 ساعة بنسبة 85% بسبب ارتفاع الحرارة.', 'severity': 'high', 'icon': 'fa-wrench'},
        {'title': 'تحسين السرعة', 'message': 'يمكن زيادة سرعة خط التجميع بنسبة 12% دون التأثير على الجودة.', 'severity': 'medium', 'icon': 'fa-tachometer-alt'},
        {'title': 'توفير الطاقة', 'message': 'نمط الاستهلاك يشير إلى هدر في الطاقة خلال فترة الراحة (12:00 - 13:00).', 'severity': 'low', 'icon': 'fa-leaf'},
    ]
    
    context = {
        'title': 'اقتراحات الذكاء الاصطناعي',
        'subtitle': 'تحليل تنبؤي وتوصيات لتحسين الأداء',
        'active_tab': 'ai',
        'anomaly_score': random.randint(0, 15), # 0-100%
        'ai_confidence': random.randint(88, 99),
        'predictions': predictions,
        'next_maintenance': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
    }
    return render(request, 'smart_pricing/production_line_ai.html', context)


@login_required
def production_line_cost(request):
    """تحليل تكاليف التشغيل"""
    import random
    
    costs = {
        'raw_materials': random.randint(5000, 7000),
        'energy': random.randint(1200, 2000),
        'labor': random.randint(3000, 4000),
        'maintenance': random.randint(500, 1000),
        'overhead': random.randint(800, 1200),
    }
    total_cost = sum(costs.values())
    
    unit_cost_history = [random.uniform(12, 18) for _ in range(7)]  # Last 7 days
    
    context = {
        'title': 'تكاليف التشغيل',
        'subtitle': 'تفاصيل التكاليف التشغيلية واستهلاك الطاقة والموارد',
        'active_tab': 'cost',
        'costs': costs,
        'total_cost': total_cost,
        'cost_per_unit': round(total_cost / 500, 2), # Assuming 500 units produced
        'unit_cost_history': unit_cost_history,
        'currency': 'ج.م',
    }
    return render(request, 'smart_pricing/production_line_cost.html', context)


# ============ API Views ============

@login_required
@require_http_methods(["POST"])
def api_calculate_price(request):
    """API: حساب السعر"""
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        strategy = data.get('strategy', 'balanced')
        
        from inventory.models import Product
        product = get_object_or_404(Product, id=product_id)
        
        engine = SmartPricingEngine()
        result = engine.calculate_optimal_price(product, strategy=strategy)
        
        return JsonResponse({
            'success': True,
            'result': result
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_bulk_calculate(request):
    """API: حساب أسعار متعددة"""
    
    try:
        data = json.loads(request.body)
        product_ids = data.get('product_ids', [])
        strategy = data.get('strategy', 'balanced')
        
        from inventory.models import Product
        
        engine = SmartPricingEngine()
        results = []
        
        for product_id in product_ids[:50]:  # الحد الأقصى 50 منتج
            try:
                product = Product.objects.get(id=product_id)
                result = engine.calculate_optimal_price(product, strategy=strategy)
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
        
        return JsonResponse({
            'success': True,
            'results': results
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_get_alerts(request):
    """API: الحصول على التنبيهات"""
    
    service = AlertService()
    alerts = service.get_pending_alerts()
    
    return JsonResponse({
        'success': True,
        'alerts': alerts,
        'count': len(alerts)
    })


@login_required
def api_dashboard_stats(request):
    """API: إحصائيات لوحة التحكم"""
    
    service = PricingReportService()
    data = service.get_pricing_dashboard_data()
    
    return JsonResponse({
        'success': True,
        'data': data
    })
