"""
Smart Pricing Services
خدمات التسعير الذكي

يشمل:
- خدمة التسعير التلقائي
- خدمة مراقبة المنافسين
- خدمة التنبيهات
- خدمة التقارير
"""

from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Avg, Sum, Count, F, Q
from django.utils import timezone
from django.contrib.auth.models import User


class AutoPricingService:
    """خدمة التسعير التلقائي"""
    
    def __init__(self):
        from .pricing_engine import SmartPricingEngine
        self.engine = SmartPricingEngine()
    
    def auto_update_prices(
        self,
        products=None,
        category=None,
        strategy: str = 'balanced',
        apply_immediately: bool = False,
        requires_approval: bool = True,
        updated_by: User = None
    ) -> Dict:
        """
        تحديث الأسعار تلقائياً
        
        المعاملات:
        - products: قائمة المنتجات (أو None للكل)
        - category: فئة المنتجات
        - strategy: استراتيجية التسعير
        - apply_immediately: تطبيق فوري
        - requires_approval: يحتاج موافقة
        """
        
        from inventory.models import Product
        from .models_extended import PriceHistory
        
        if products is None:
            if category:
                products = Product.objects.filter(category=category, is_active=True)
            else:
                # المنتجات التي لها ملف تسعير مفعل
                products = Product.objects.filter(
                    is_active=True,
                    pricing_profile__enable_dynamic_pricing=True
                )
        
        results = {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'updates': [],
            'errors_list': [],
        }
        
        for product in products:
            try:
                # حساب السعر الأمثل
                recommendation = self.engine.calculate_optimal_price(
                    product,
                    strategy=strategy,
                    include_competitor_analysis=True,
                    include_demand_analysis=True,
                    include_seasonality=True
                )
                
                results['processed'] += 1
                
                # التحقق من الثقة والتغيير
                if recommendation['confidence_score'] < 0.5:
                    results['skipped'] += 1
                    continue
                
                price_change = abs(recommendation['price_change'])
                if price_change < 1:  # أقل من 1% تغيير
                    results['skipped'] += 1
                    continue
                
                old_price = product.price
                new_price = Decimal(str(recommendation['recommended_price']))
                
                update_record = {
                    'product_id': product.id,
                    'product_name': product.name,
                    'old_price': float(old_price),
                    'new_price': float(new_price),
                    'change_percentage': recommendation['price_change'],
                    'confidence': recommendation['confidence_score'],
                    'applied': False,
                }
                
                if apply_immediately:
                    with transaction.atomic():
                        # حفظ التاريخ
                        PriceHistory.objects.create(
                            product=product,
                            old_price=old_price,
                            new_price=new_price,
                            old_cost=product.cost_price if hasattr(product, 'cost_price') else None,
                            reason='ai_recommendation',
                            reason_details=f"توصية AI بثقة {recommendation['confidence_score']:.2f}",
                            changed_by=updated_by,
                            requires_approval=requires_approval,
                            approved=not requires_approval,
                        )
                        
                        if not requires_approval:
                            product.price = new_price
                            product.save(update_fields=['price'])
                            update_record['applied'] = True
                
                results['updates'].append(update_record)
                results['updated'] += 1
                
            except Exception as e:
                results['errors'] += 1
                results['errors_list'].append({
                    'product_id': product.id,
                    'error': str(e),
                })
        
        return results
    
    def apply_seasonal_pricing(self) -> Dict:
        """تطبيق التسعير الموسمي"""
        
        from .models_extended import SeasonalPricing
        from inventory.models import Product
        
        today = timezone.now().date()
        
        # الحصول على المواسم النشطة
        active_seasons = SeasonalPricing.objects.filter(
            is_active=True,
            auto_activate=True,
            start_date__lte=today,
            end_date__gte=today
        )
        
        results = {
            'active_seasons': [],
            'products_affected': 0,
        }
        
        for season in active_seasons:
            results['active_seasons'].append({
                'name': season.name,
                'adjustment_type': season.adjustment_type,
                'adjustment_value': float(season.adjustment_value),
            })
            
            # تطبيق على المنتجات
            if season.applies_to_all:
                products = Product.objects.filter(is_active=True)
            else:
                categories = season.product_categories.split(',')
                products = Product.objects.filter(
                    is_active=True,
                    category__name__in=categories
                )
            
            results['products_affected'] += products.count()
        
        return results
    
    def calculate_bulk_prices(self, quote_data: Dict) -> Dict:
        """حساب أسعار الكميات الكبيرة"""
        
        from .models import PricingRule
        
        quantity = quote_data.get('quantity', 1)
        base_price = Decimal(str(quote_data.get('base_price', 0)))
        category = quote_data.get('category', '')
        
        # البحث عن قاعدة التسعير المناسبة
        rule = PricingRule.objects.filter(
            is_active=True,
            product_category__icontains=category
        ).first()
        
        if not rule:
            rule = PricingRule.objects.filter(is_active=True).first()
        
        # حساب الخصومات
        discounts = []
        total_discount = Decimal('0')
        
        # خصم الكمية
        if rule and quantity >= rule.quantity_discount_threshold:
            qty_discount = rule.quantity_discount_rate
            discounts.append({
                'type': 'quantity',
                'description': f'خصم كمية ({quantity} وحدة)',
                'percentage': float(qty_discount),
            })
            total_discount += qty_discount
        
        # خصم إضافي للكميات الكبيرة جداً
        if quantity >= 500:
            extra_discount = Decimal('5')
            discounts.append({
                'type': 'bulk',
                'description': 'خصم كميات كبيرة جداً',
                'percentage': float(extra_discount),
            })
            total_discount += extra_discount
        
        # الحساب النهائي
        unit_price = base_price * (1 - total_discount / 100)
        total_price = unit_price * quantity
        
        return {
            'quantity': quantity,
            'base_price': float(base_price),
            'unit_price': float(unit_price),
            'total_price': float(total_price),
            'discounts': discounts,
            'total_discount_percentage': float(total_discount),
            'savings': float(base_price * quantity - total_price),
        }


class CompetitorMonitoringService:
    """خدمة مراقبة المنافسين"""
    
    def add_competitor_price(
        self,
        competitor_id: int,
        product_name: str,
        price: Decimal,
        source: str,
        recorded_by: User = None,
        product_id: int = None,
        source_url: str = ''
    ) -> Dict:
        """إضافة سعر منافس جديد"""
        
        from .models_extended import Competitor, CompetitorPrice
        from inventory.models import Product
        
        competitor = Competitor.objects.get(id=competitor_id)
        
        product = None
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                pass
        
        price_record = CompetitorPrice.objects.create(
            competitor=competitor,
            product=product,
            product_name=product_name,
            price=price,
            source=source,
            source_url=source_url,
            recorded_by=recorded_by,
        )
        
        # التحقق من التنبيهات
        self._check_price_alerts(product, price, competitor)
        
        return {
            'id': price_record.id,
            'competitor': competitor.name,
            'product_name': product_name,
            'price': float(price),
            'recorded_at': price_record.recorded_at.isoformat(),
        }
    
    def _check_price_alerts(self, product, competitor_price: Decimal, competitor):
        """التحقق من الحاجة لإنشاء تنبيه"""
        
        from .models_extended import PriceAlert
        
        if not product:
            return
        
        our_price = product.price
        diff_percentage = (our_price - competitor_price) / competitor_price * 100
        
        if diff_percentage > 15:  # سعرنا أعلى بـ 15%
            PriceAlert.objects.create(
                alert_type='competitor_price_drop',
                title=f'سعر المنافس أقل بنسبة {abs(diff_percentage):.1f}%',
                message=f'سعر {competitor.name} للمنتج {product.name} هو {competitor_price} بينما سعرنا {our_price}',
                product=product,
                competitor=competitor,
                priority='high',
                recommended_action='مراجعة السعر والنظر في تخفيضه',
                recommended_price=competitor_price * Decimal('1.05'),
                data={
                    'our_price': float(our_price),
                    'competitor_price': float(competitor_price),
                    'difference': float(diff_percentage),
                }
            )
        elif diff_percentage < -15:  # سعرنا أقل بـ 15%
            PriceAlert.objects.create(
                alert_type='competitor_price_increase',
                title=f'فرصة لزيادة السعر',
                message=f'سعرنا أقل من {competitor.name} بنسبة {abs(diff_percentage):.1f}%',
                product=product,
                competitor=competitor,
                priority='medium',
                recommended_action='النظر في رفع السعر لتحسين الهامش',
                recommended_price=competitor_price * Decimal('0.95'),
                data={
                    'our_price': float(our_price),
                    'competitor_price': float(competitor_price),
                    'difference': float(diff_percentage),
                }
            )
    
    def get_competitor_trends(self, competitor_id: int = None, days: int = 90) -> Dict:
        """الحصول على اتجاهات أسعار المنافسين"""
        
        from .models_extended import CompetitorPrice, Competitor
        
        start_date = timezone.now() - timedelta(days=days)
        
        query = CompetitorPrice.objects.filter(recorded_at__gte=start_date)
        if competitor_id:
            query = query.filter(competitor_id=competitor_id)
        
        # تجميع البيانات
        trends = query.values(
            'competitor__name',
            'recorded_at__date'
        ).annotate(
            avg_price=Avg('price'),
            count=Count('id')
        ).order_by('recorded_at__date')
        
        return {
            'period_days': days,
            'trends': list(trends),
            'total_records': query.count(),
        }


class AlertService:
    """خدمة التنبيهات"""
    
    def create_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        product=None,
        competitor=None,
        priority: str = 'medium',
        recommended_action: str = '',
        recommended_price: Decimal = None,
        data: Dict = None
    ):
        """إنشاء تنبيه جديد"""
        
        from .models_extended import PriceAlert
        
        return PriceAlert.objects.create(
            alert_type=alert_type,
            title=title,
            message=message,
            product=product,
            competitor=competitor,
            priority=priority,
            recommended_action=recommended_action,
            recommended_price=recommended_price,
            data=data or {},
        )
    
    def get_pending_alerts(self, priority: str = None) -> List[Dict]:
        """الحصول على التنبيهات المعلقة"""
        
        from .models_extended import PriceAlert
        
        query = PriceAlert.objects.filter(
            is_actioned=False,
            is_read=False
        )
        
        if priority:
            query = query.filter(priority=priority)
        
        alerts = []
        for alert in query.order_by('-created_at')[:50]:
            alerts.append({
                'id': alert.id,
                'type': alert.alert_type,
                'title': alert.title,
                'message': alert.message,
                'priority': alert.priority,
                'product': alert.product.name if alert.product else None,
                'recommended_price': float(alert.recommended_price) if alert.recommended_price else None,
                'created_at': alert.created_at.isoformat(),
            })
        
        return alerts
    
    def mark_as_actioned(self, alert_id: int, user: User) -> bool:
        """تحديد التنبيه كمعالج"""
        
        from .models_extended import PriceAlert
        
        try:
            alert = PriceAlert.objects.get(id=alert_id)
            alert.is_actioned = True
            alert.actioned_by = user
            alert.actioned_at = timezone.now()
            alert.save()
            return True
        except PriceAlert.DoesNotExist:
            return False
    
    def check_margin_alerts(self) -> int:
        """فحص وإنشاء تنبيهات الهامش"""
        
        from inventory.models import Product
        from .models_extended import PriceAlert, ProductPricingProfile
        
        alerts_created = 0
        
        # المنتجات التي لها ملف تسعير
        profiles = ProductPricingProfile.objects.filter(
            product__is_active=True
        ).select_related('product')
        
        for profile in profiles:
            product = profile.product
            
            if not product.cost_price or product.cost_price == 0:
                continue
            
            current_margin = (product.price - product.cost_price) / product.cost_price * 100
            
            if current_margin < profile.target_margin * Decimal('0.7'):  # أقل من 70% من الهدف
                # التحقق من عدم وجود تنبيه مشابه
                existing = PriceAlert.objects.filter(
                    product=product,
                    alert_type='margin_below_threshold',
                    is_actioned=False,
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).exists()
                
                if not existing:
                    PriceAlert.objects.create(
                        alert_type='margin_below_threshold',
                        title=f'هامش ربح منخفض: {product.name}',
                        message=f'الهامش الحالي {current_margin:.1f}% أقل من الهدف {profile.target_margin}%',
                        product=product,
                        priority='high',
                        recommended_action='مراجعة تكلفة المنتج أو رفع السعر',
                        recommended_price=product.cost_price * (1 + profile.target_margin / 100),
                        data={
                            'current_margin': float(current_margin),
                            'target_margin': float(profile.target_margin),
                            'cost': float(product.cost_price),
                        }
                    )
                    alerts_created += 1
        
        return alerts_created


class PricingReportService:
    """خدمة تقارير التسعير"""
    
    def get_pricing_dashboard_data(self) -> Dict:
        """بيانات لوحة تحكم التسعير"""
        
        from .models_extended import (
            Competitor, CompetitorPrice, PriceHistory,
            PriceAlert, SeasonalPricing, PricingGoal
        )
        from inventory.models import Product
        
        today = timezone.now().date()
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # إحصائيات عامة
        total_products = Product.objects.filter(is_active=True).count()
        
        # تغييرات الأسعار
        price_changes = PriceHistory.objects.filter(
            changed_at__gte=thirty_days_ago
        ).count()
        
        # التنبيهات
        pending_alerts = PriceAlert.objects.filter(
            is_actioned=False
        ).count()
        urgent_alerts = PriceAlert.objects.filter(
            is_actioned=False,
            priority='urgent'
        ).count()
        
        # المنافسين
        competitors_count = Competitor.objects.filter(is_active=True).count()
        competitor_prices_count = CompetitorPrice.objects.filter(
            recorded_at__gte=thirty_days_ago
        ).count()
        
        # المواسم النشطة
        active_seasons = SeasonalPricing.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).values_list('name', flat=True)
        
        # أهداف التسعير
        active_goals = PricingGoal.objects.filter(
            status='active',
            period_end__gte=today
        ).count()
        
        return {
            'total_products': total_products,
            'price_changes_30_days': price_changes,
            'pending_alerts': pending_alerts,
            'urgent_alerts': urgent_alerts,
            'competitors_count': competitors_count,
            'competitor_prices_30_days': competitor_prices_count,
            'active_seasons': list(active_seasons),
            'active_goals': active_goals,
            'last_updated': timezone.now().isoformat(),
        }
    
    def get_price_history_report(
        self,
        product_id: int = None,
        category: str = None,
        days: int = 90
    ) -> Dict:
        """تقرير تاريخ الأسعار"""
        
        from .models_extended import PriceHistory
        
        start_date = timezone.now() - timedelta(days=days)
        
        query = PriceHistory.objects.filter(changed_at__gte=start_date)
        
        if product_id:
            query = query.filter(product_id=product_id)
        if category:
            query = query.filter(product__category__name__icontains=category)
        
        # إحصائيات
        stats = query.aggregate(
            total_changes=Count('id'),
            avg_change=Avg('price_change_percentage'),
            increases=Count('id', filter=Q(price_change_percentage__gt=0)),
            decreases=Count('id', filter=Q(price_change_percentage__lt=0)),
        )
        
        # التغييرات حسب السبب
        by_reason = query.values('reason').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # أحدث التغييرات
        recent = query.order_by('-changed_at')[:20].values(
            'product__name',
            'old_price',
            'new_price',
            'price_change_percentage',
            'reason',
            'changed_at'
        )
        
        return {
            'period_days': days,
            'statistics': stats,
            'by_reason': list(by_reason),
            'recent_changes': list(recent),
        }
    
    def get_competitor_analysis_report(self) -> Dict:
        """تقرير تحليل المنافسين"""
        
        from .models_extended import Competitor, CompetitorPrice
        
        competitors = Competitor.objects.filter(is_active=True)
        
        report = {
            'competitors': [],
            'summary': {
                'total_competitors': competitors.count(),
                'total_tracked_prices': 0,
            }
        }
        
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
            
            report['competitors'].append({
                'id': competitor.id,
                'name': competitor.name,
                'type': competitor.get_competitor_type_display(),
                'market_share': float(competitor.market_share),
                'price_level': competitor.get_price_level_display(),
                'quality_rating': competitor.quality_rating,
                'tracked_prices': price_count,
                'average_price': float(avg_price) if avg_price else 0,
            })
            
            report['summary']['total_tracked_prices'] += price_count
        
        return report
    
    def get_profitability_report(self, category: str = None) -> Dict:
        """تقرير الربحية"""
        
        from inventory.models import Product
        
        query = Product.objects.filter(is_active=True)
        
        if category:
            query = query.filter(category__name__icontains=category)
        
        products = []
        total_revenue = Decimal('0')
        total_cost = Decimal('0')
        
        for product in query[:100]:
            if product.price and product.cost_price and product.cost_price > 0:
                margin = (product.price - product.cost_price) / product.cost_price * 100
                profit = product.price - product.cost_price
                
                products.append({
                    'id': product.id,
                    'name': product.name,
                    'price': float(product.price),
                    'cost_price': float(product.cost_price),
                    'profit': float(profit),
                    'margin_percentage': float(margin),
                })
                
                total_revenue += product.price
                total_cost += product.cost_price
        
        # ترتيب حسب الهامش
        products.sort(key=lambda x: x['margin_percentage'], reverse=True)
        
        overall_margin = (total_revenue - total_cost) / total_cost * 100 if total_cost > 0 else 0
        
        return {
            'products': products,
            'summary': {
                'total_products': len(products),
                'average_margin': sum(p['margin_percentage'] for p in products) / len(products) if products else 0,
                'overall_margin': float(overall_margin),
                'highest_margin': products[0] if products else None,
                'lowest_margin': products[-1] if products else None,
            }
        }
