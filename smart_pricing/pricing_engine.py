"""
Advanced AI Pricing Engine
محرك التسعير الذكي المتقدم

يشمل:
- تحليل الطلب والعرض
- تحليل المنافسين
- التنبؤ بالأسعار
- التحسين الآلي
- التوصيات الذكية
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Avg, Sum, Count, F, Q
from django.utils import timezone
import math


class SmartPricingEngine:
    """محرك التسعير الذكي المتقدم"""
    
    def __init__(self):
        self.confidence_threshold = Decimal('0.7')
        self.max_price_change = Decimal('0.15')  # 15% maximum change
    
    def calculate_optimal_price(
        self,
        product,
        strategy: str = 'balanced',
        include_competitor_analysis: bool = True,
        include_demand_analysis: bool = True,
        include_seasonality: bool = True
    ) -> Dict:
        """
        حساب السعر الأمثل للمنتج
        
        المخرجات:
        - recommended_price: السعر الموصى به
        - confidence_score: درجة الثقة
        - price_range: (min, max) نطاق السعر المقترح
        - factors: العوامل المؤثرة
        - analysis: التحليل التفصيلي
        """
        
        analysis = {
            'product_id': product.id,
            'product_name': product.name,
            'current_price': float(product.price),
            'current_cost': float(product.cost_price) if hasattr(product, 'cost_price') else 0,
            'timestamp': timezone.now().isoformat(),
        }
        
        factors = []
        adjustments = []
        
        # 1. تحليل التكلفة والهامش
        cost_analysis = self._analyze_cost_margin(product)
        analysis['cost_analysis'] = cost_analysis
        factors.append(('cost', cost_analysis['weight'], cost_analysis['suggested_price']))
        
        # 2. تحليل المنافسين
        if include_competitor_analysis:
            competitor_analysis = self._analyze_competitors(product)
            analysis['competitor_analysis'] = competitor_analysis
            if competitor_analysis['has_data']:
                factors.append(('competitor', competitor_analysis['weight'], competitor_analysis['suggested_price']))
        
        # 3. تحليل الطلب
        if include_demand_analysis:
            demand_analysis = self._analyze_demand(product)
            analysis['demand_analysis'] = demand_analysis
            if demand_analysis['has_data']:
                factors.append(('demand', demand_analysis['weight'], demand_analysis['adjustment']))
                adjustments.append(demand_analysis['adjustment'])
        
        # 4. تحليل الموسمية
        if include_seasonality:
            seasonal_analysis = self._analyze_seasonality(product)
            analysis['seasonal_analysis'] = seasonal_analysis
            if seasonal_analysis['is_active']:
                adjustments.append(seasonal_analysis['adjustment'])
        
        # 5. حساب السعر الأمثل
        base_price = self._calculate_weighted_price(factors)
        
        # تطبيق التعديلات
        for adjustment in adjustments:
            base_price = base_price * (1 + adjustment / 100)
        
        # تطبيق الاستراتيجية
        strategy_adjustment = self._apply_strategy(strategy, base_price, product)
        final_price = base_price * (1 + strategy_adjustment / 100)
        
        # التحقق من الحدود
        min_price, max_price = self._get_price_bounds(product, final_price)
        final_price = max(min_price, min(max_price, final_price))
        
        # حساب درجة الثقة
        confidence = self._calculate_confidence(analysis)
        
        # التقريب لسعر نفسي جيد
        psychological_price = self._apply_psychological_pricing(final_price)
        
        return {
            'recommended_price': float(psychological_price),
            'calculated_price': float(final_price),
            'confidence_score': float(confidence),
            'price_range': {
                'min': float(min_price),
                'max': float(max_price)
            },
            'current_price': float(product.price),
            'price_change': float((psychological_price - product.price) / product.price * 100) if product.price > 0 else 0,
            'factors': [(f[0], float(f[1]), float(f[2]) if isinstance(f[2], Decimal) else f[2]) for f in factors],
            'adjustments': adjustments,
            'strategy': strategy,
            'strategy_adjustment': float(strategy_adjustment),
            'analysis': analysis,
        }
    
    def _analyze_cost_margin(self, product) -> Dict:
        """تحليل التكلفة والهامش"""
        
        cost = Decimal(str(product.cost_price)) if hasattr(product, 'cost_price') and product.cost_price else Decimal('0')
        current_price = Decimal(str(product.price)) if product.price else Decimal('0')
        
        if cost > 0:
            current_margin = (current_price - cost) / cost * 100
        else:
            current_margin = Decimal('0')
        
        # الهامش المستهدف حسب الفئة
        target_margin = self._get_target_margin(product)
        
        suggested_price = cost * (1 + target_margin / 100) if cost > 0 else current_price
        
        return {
            'cost': float(cost),
            'current_margin': float(current_margin),
            'target_margin': float(target_margin),
            'suggested_price': float(suggested_price),
            'weight': 0.4,  # وزن التكلفة في الحساب
        }
    
    def _analyze_competitors(self, product) -> Dict:
        """تحليل أسعار المنافسين"""
        
        from .models_extended import CompetitorPrice
        
        # البحث عن أسعار المنافسين لهذا المنتج أو فئته
        competitor_prices = CompetitorPrice.objects.filter(
            Q(product=product) | Q(product_name__icontains=product.name)
        ).filter(
            recorded_at__gte=timezone.now() - timedelta(days=90)
        )
        
        if not competitor_prices.exists():
            return {
                'has_data': False,
                'message': 'لا توجد بيانات منافسين',
            }
        
        prices = [p.price for p in competitor_prices]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        return {
            'has_data': True,
            'competitor_count': len(prices),
            'average_price': float(avg_price),
            'min_price': float(min_price),
            'max_price': float(max_price),
            'suggested_price': float(avg_price),
            'weight': 0.3,
            'position_recommendation': self._get_position_recommendation(product.price, avg_price),
        }
    
    def _analyze_demand(self, product) -> Dict:
        """تحليل الطلب"""
        
        from sales.models import SalesOrderLine
        
        # تحليل المبيعات في آخر 90 يوم
        ninety_days_ago = timezone.now() - timedelta(days=90)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        try:
            # مبيعات آخر 30 يوم
            recent_sales = SalesOrderLine.objects.filter(
                product=product,
                order__order_date__gte=thirty_days_ago
            ).aggregate(
                total_qty=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('unit_price'))
            )
            
            # مبيعات 30-60 يوم
            previous_sales = SalesOrderLine.objects.filter(
                product=product,
                order__order_date__gte=ninety_days_ago,
                order__order_date__lt=thirty_days_ago
            ).aggregate(
                total_qty=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('unit_price'))
            )
            
            recent_qty = recent_sales['total_qty'] or 0
            previous_qty = previous_sales['total_qty'] or 0
            
            # حساب معدل النمو
            if previous_qty > 0:
                growth_rate = (recent_qty - previous_qty) / previous_qty * 100
            else:
                growth_rate = 0 if recent_qty == 0 else 100
            
            # تحديد الطلب
            if growth_rate > 20:
                demand_level = 'high'
                adjustment = Decimal('5')  # زيادة 5%
            elif growth_rate < -20:
                demand_level = 'low'
                adjustment = Decimal('-5')  # تخفيض 5%
            else:
                demand_level = 'normal'
                adjustment = Decimal('0')
            
            return {
                'has_data': True,
                'recent_quantity': recent_qty,
                'previous_quantity': previous_qty,
                'growth_rate': float(growth_rate),
                'demand_level': demand_level,
                'adjustment': float(adjustment),
                'weight': 0.2,
            }
        except Exception:
            return {
                'has_data': False,
                'adjustment': 0,
                'weight': 0,
            }
    
    def _analyze_seasonality(self, product) -> Dict:
        """تحليل التأثير الموسمي"""
        
        from .models_extended import SeasonalPricing
        
        today = timezone.now().date()
        
        active_seasons = SeasonalPricing.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        )
        
        if not active_seasons.exists():
            return {
                'is_active': False,
            }
        
        # تجميع التعديلات
        total_adjustment = Decimal('0')
        active_promotions = []
        
        for season in active_seasons:
            if season.applies_to_all or product.category.name in season.product_categories:
                if season.adjustment_type == 'percentage':
                    total_adjustment += season.adjustment_value
                active_promotions.append(season.name)
        
        return {
            'is_active': True,
            'active_seasons': active_promotions,
            'adjustment': float(total_adjustment),
        }
    
    def _calculate_weighted_price(self, factors: List[Tuple]) -> Decimal:
        """حساب السعر المرجح"""
        
        if not factors:
            return Decimal('0')
        
        total_weight = sum(f[1] for f in factors if isinstance(f[2], (int, float, Decimal)))
        
        if total_weight == 0:
            return Decimal('0')
        
        weighted_sum = sum(
            Decimal(str(f[1])) * Decimal(str(f[2])) 
            for f in factors 
            if isinstance(f[2], (int, float, Decimal))
        )
        
        return weighted_sum / Decimal(str(total_weight))
    
    def _apply_strategy(self, strategy: str, price: Decimal, product) -> Decimal:
        """تطبيق استراتيجية التسعير"""
        
        strategies = {
            'aggressive': Decimal('-5'),    # سعر أقل للمنافسة
            'conservative': Decimal('5'),   # سعر أعلى للجودة
            'balanced': Decimal('0'),       # متوازن
            'premium': Decimal('15'),       # فاخر
            'penetration': Decimal('-10'),  # اختراق السوق
        }
        
        return strategies.get(strategy, Decimal('0'))
    
    def _get_price_bounds(self, product, calculated_price: Decimal) -> Tuple[Decimal, Decimal]:
        """الحصول على حدود السعر"""
        
        current_price = Decimal(str(product.price)) if product.price else calculated_price
        
        # لا يتجاوز 15% تغيير
        max_change = current_price * self.max_price_change
        
        min_price = current_price - max_change
        max_price = current_price + max_change
        
        # التأكد من تغطية التكلفة
        if hasattr(product, 'cost_price') and product.cost_price:
            cost = Decimal(str(product.cost_price))
            min_price = max(min_price, cost * Decimal('1.05'))  # على الأقل 5% فوق التكلفة
        
        return min_price, max_price
    
    def _calculate_confidence(self, analysis: Dict) -> Decimal:
        """حساب درجة الثقة"""
        
        confidence = Decimal('0.5')  # بداية متوسطة
        
        # زيادة الثقة مع وجود بيانات
        if analysis.get('competitor_analysis', {}).get('has_data'):
            confidence += Decimal('0.2')
        
        if analysis.get('demand_analysis', {}).get('has_data'):
            confidence += Decimal('0.2')
        
        if analysis.get('cost_analysis', {}).get('cost', 0) > 0:
            confidence += Decimal('0.1')
        
        return min(Decimal('1.0'), confidence)
    
    def _apply_psychological_pricing(self, price: Decimal) -> Decimal:
        """تطبيق التسعير النفسي"""
        
        price_float = float(price)
        
        if price_float < 10:
            # تقريب لـ .99
            return Decimal(str(math.floor(price_float) + 0.99))
        elif price_float < 100:
            # تقريب لـ .95
            return Decimal(str(math.floor(price_float / 5) * 5 + 4.95))
        elif price_float < 1000:
            # تقريب لـ 9
            return Decimal(str(math.floor(price_float / 10) * 10 + 9))
        else:
            # تقريب لـ 99
            return Decimal(str(math.floor(price_float / 100) * 100 + 99))
    
    def _get_target_margin(self, product) -> Decimal:
        """الحصول على الهامش المستهدف للفئة"""
        
        # يمكن تخصيص الهامش حسب الفئة
        default_margins = {
            'electronics': Decimal('20'),
            'furniture': Decimal('35'),
            'food': Decimal('15'),
            'luxury': Decimal('50'),
        }
        
        category = getattr(product, 'category', None)
        if category:
            category_name = category.name.lower() if hasattr(category, 'name') else ''
            for key, margin in default_margins.items():
                if key in category_name:
                    return margin
        
        return Decimal('25')  # هامش افتراضي
    
    def _get_position_recommendation(self, current_price: Decimal, competitor_avg: Decimal) -> str:
        """توصية بالموقع السعري"""
        
        if current_price > competitor_avg * Decimal('1.1'):
            return 'أعلى من السوق - فكر في تخفيض السعر أو تبرير القيمة'
        elif current_price < competitor_avg * Decimal('0.9'):
            return 'أقل من السوق - فرصة لزيادة السعر'
        else:
            return 'سعر تنافسي - حافظ على الموقع الحالي'


class DemandForecaster:
    """التنبؤ بالطلب"""
    
    def forecast_demand(self, product, days: int = 30) -> Dict:
        """التنبؤ بالطلب للأيام القادمة"""
        
        from sales.models import SalesOrderLine
        
        # جمع البيانات التاريخية
        historical_data = self._get_historical_sales(product, days * 3)
        
        if not historical_data:
            return {
                'forecast': [],
                'confidence': 0,
                'message': 'لا توجد بيانات كافية للتنبؤ'
            }
        
        # حساب المتوسط المتحرك
        avg_daily = sum(d['quantity'] for d in historical_data) / len(historical_data)
        
        # التنبؤ البسيط
        forecast = []
        for i in range(days):
            date = timezone.now().date() + timedelta(days=i)
            # تعديل للاتجاه الأسبوعي
            weekday_factor = self._get_weekday_factor(date.weekday())
            predicted = avg_daily * weekday_factor
            
            forecast.append({
                'date': date.isoformat(),
                'predicted_quantity': round(predicted, 2),
                'lower_bound': round(predicted * 0.8, 2),
                'upper_bound': round(predicted * 1.2, 2),
            })
        
        return {
            'forecast': forecast,
            'average_daily': round(avg_daily, 2),
            'total_forecast': round(sum(f['predicted_quantity'] for f in forecast), 2),
            'confidence': 0.7,
        }
    
    def _get_historical_sales(self, product, days: int) -> List[Dict]:
        """الحصول على المبيعات التاريخية"""
        
        from sales.models import SalesOrderLine
        
        start_date = timezone.now() - timedelta(days=days)
        
        try:
            sales = SalesOrderLine.objects.filter(
                product=product,
                order__order_date__gte=start_date
            ).values('order__order_date').annotate(
                quantity=Sum('quantity')
            ).order_by('order__order_date')
            
            return [{'date': s['order__order_date'], 'quantity': s['quantity']} for s in sales]
        except Exception:
            return []
    
    def _get_weekday_factor(self, weekday: int) -> float:
        """معامل اليوم في الأسبوع"""
        
        factors = {
            0: 0.9,   # الإثنين
            1: 0.95,  # الثلاثاء
            2: 1.0,   # الأربعاء
            3: 1.1,   # الخميس
            4: 0.7,   # الجمعة (عطلة)
            5: 0.8,   # السبت
            6: 1.0,   # الأحد
        }
        return factors.get(weekday, 1.0)


class PriceOptimizer:
    """محسن الأسعار"""
    
    def optimize_category_prices(self, category, strategy: str = 'maximize_profit') -> Dict:
        """تحسين أسعار فئة كاملة"""
        
        from inventory.models import Product
        
        products = Product.objects.filter(category=category, is_active=True)
        engine = SmartPricingEngine()
        
        recommendations = []
        total_current_revenue = Decimal('0')
        total_expected_revenue = Decimal('0')
        
        for product in products:
            result = engine.calculate_optimal_price(
                product,
                strategy='balanced',
                include_competitor_analysis=True,
                include_demand_analysis=True
            )
            
            current_revenue = product.price * Decimal('100')  # افتراض 100 وحدة
            expected_revenue = Decimal(str(result['recommended_price'])) * Decimal('100')
            
            recommendations.append({
                'product_id': product.id,
                'product_name': product.name,
                'current_price': float(product.price),
                'recommended_price': result['recommended_price'],
                'price_change': result['price_change'],
                'confidence': result['confidence_score'],
            })
            
            total_current_revenue += current_revenue
            total_expected_revenue += expected_revenue
        
        return {
            'category': category.name if hasattr(category, 'name') else str(category),
            'product_count': len(recommendations),
            'recommendations': recommendations,
            'total_current_revenue': float(total_current_revenue),
            'total_expected_revenue': float(total_expected_revenue),
            'revenue_change': float((total_expected_revenue - total_current_revenue) / total_current_revenue * 100) if total_current_revenue > 0 else 0,
        }
    
    def run_price_simulation(
        self,
        product,
        price_changes: List[float],
        demand_elasticity: float = -1.5
    ) -> Dict:
        """محاكاة تغييرات الأسعار"""
        
        current_price = float(product.price)
        current_quantity = 100  # افتراض الكمية الحالية
        
        simulations = []
        
        for change in price_changes:
            new_price = current_price * (1 + change / 100)
            
            # حساب تغيير الكمية باستخدام المرونة
            quantity_change = demand_elasticity * change
            new_quantity = current_quantity * (1 + quantity_change / 100)
            
            current_revenue = current_price * current_quantity
            new_revenue = new_price * new_quantity
            revenue_change = (new_revenue - current_revenue) / current_revenue * 100
            
            # الربح (افتراض هامش 30%)
            margin = 0.3
            current_profit = current_revenue * margin
            new_profit = new_revenue * margin
            profit_change = (new_profit - current_profit) / current_profit * 100 if current_profit > 0 else 0
            
            simulations.append({
                'price_change_percentage': change,
                'new_price': round(new_price, 2),
                'quantity_change_percentage': round(quantity_change, 2),
                'new_quantity': round(new_quantity, 0),
                'revenue_change_percentage': round(revenue_change, 2),
                'profit_change_percentage': round(profit_change, 2),
                'new_revenue': round(new_revenue, 2),
                'new_profit': round(new_profit, 2),
            })
        
        # إيجاد السعر الأمثل
        best_scenario = max(simulations, key=lambda x: x['new_profit'])
        
        return {
            'product_id': product.id,
            'product_name': product.name,
            'current_price': current_price,
            'demand_elasticity': demand_elasticity,
            'simulations': simulations,
            'optimal_scenario': best_scenario,
            'recommendation': f"أفضل سيناريو: تغيير السعر بنسبة {best_scenario['price_change_percentage']}%",
        }


class CompetitorAnalyzer:
    """محلل المنافسين"""
    
    def analyze_market_position(self, products=None) -> Dict:
        """تحليل الموقع في السوق"""
        
        from .models_extended import Competitor, CompetitorPrice
        from inventory.models import Product
        
        if products is None:
            products = Product.objects.filter(is_active=True)[:50]
        
        competitor_data = []
        competitors = Competitor.objects.filter(is_active=True)
        
        for competitor in competitors:
            prices = CompetitorPrice.objects.filter(
                competitor=competitor,
                recorded_at__gte=timezone.now() - timedelta(days=90)
            )
            
            if prices.exists():
                avg_price = prices.aggregate(avg=Avg('price'))['avg']
                price_count = prices.count()
            else:
                avg_price = 0
                price_count = 0
            
            competitor_data.append({
                'id': competitor.id,
                'name': competitor.name,
                'type': competitor.get_competitor_type_display(),
                'market_share': float(competitor.market_share),
                'price_level': competitor.get_price_level_display(),
                'quality_rating': competitor.quality_rating,
                'average_price': float(avg_price) if avg_price else 0,
                'tracked_products': price_count,
            })
        
        return {
            'competitors': competitor_data,
            'competitor_count': len(competitor_data),
            'analysis_date': timezone.now().isoformat(),
        }
    
    def get_price_comparison(self, product) -> Dict:
        """مقارنة السعر مع المنافسين"""
        
        from .models_extended import CompetitorPrice
        
        competitor_prices = CompetitorPrice.objects.filter(
            Q(product=product) | Q(product_name__icontains=product.name)
        ).filter(
            recorded_at__gte=timezone.now() - timedelta(days=90)
        ).select_related('competitor')
        
        if not competitor_prices.exists():
            return {
                'has_data': False,
                'message': 'لا توجد بيانات مقارنة'
            }
        
        our_price = float(product.price or 0)
        comparisons = []
        
        for cp in competitor_prices:
            cp_price = float(cp.price or 0)
            if cp_price > 0:
                diff = (our_price - cp_price) / cp_price * 100
            else:
                diff = 0
                
            comparisons.append({
                'competitor': cp.competitor.name,
                'competitor_price': cp_price,
                'our_price': our_price,
                'difference_percentage': round(diff, 2),
                'position': 'أعلى' if diff > 0 else 'أقل' if diff < 0 else 'متساوي',
                'recorded_at': cp.recorded_at.isoformat(),
            })
        
        if not comparisons:
             return {'has_data': False, 'message': 'لا توجد بيانات صالحة للمقارنة'}

        avg_competitor_price = sum(c['competitor_price'] for c in comparisons) / len(comparisons)
        
        price_gap = 0
        if avg_competitor_price > 0:
            price_gap = round((our_price - avg_competitor_price) / avg_competitor_price * 100, 2)

        return {
            'has_data': True,
            'product_name': product.name,
            'our_price': our_price,
            'average_competitor_price': round(avg_competitor_price, 2),
            'comparisons': comparisons,
            'market_position': 'فوق المتوسط' if our_price > avg_competitor_price else 'تحت المتوسط',
            'price_gap': price_gap,
        }
