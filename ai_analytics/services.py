"""
خدمات تحليلات الذكاء الاصطناعي
AI Analytics Services
"""

from django.db.models import Sum, Count, Avg, F
from django.utils import timezone
from datetime import timedelta
import json


class SalesForecastService:
    """خدمة توقع المبيعات"""
    
    def __init__(self, days_ahead=30):
        self.days_ahead = days_ahead
    
    def predict(self):
        """توقع المبيعات"""
        try:
            from sales.models import Sale
            from django.db.models.functions import TruncDate
            
            # الحصول على بيانات المبيعات السابقة
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=90)
            
            historical_data = Sale.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('date')
            
            # حساب المتوسط والاتجاه
            totals = [d['total'] for d in historical_data]
            if not totals:
                return {'predictions': [], 'confidence': 0}
            
            avg_daily = sum(totals) / len(totals)
            
            # توقع بسيط (يمكن استبداله بنموذج ML)
            predictions = []
            for i in range(self.days_ahead):
                date = end_date + timedelta(days=i+1)
                # إضافة تقلبات عشوائية
                predicted_value = avg_daily * (1 + (i * 0.01))
                predictions.append({
                    'date': date.isoformat(),
                    'predicted_value': float(predicted_value),
                    'lower_bound': float(predicted_value * 0.9),
                    'upper_bound': float(predicted_value * 1.1),
                })
            
            return {
                'predictions': predictions,
                'confidence': 75,
                'avg_daily': float(avg_daily),
            }
            
        except Exception as e:
            return {'error': str(e), 'predictions': [], 'confidence': 0}


class CustomerChurnService:
    """خدمة توقع فقدان العملاء"""
    
    def predict_churn(self, customer_id=None):
        """توقع احتمال فقدان العميل"""
        try:
            from crm.models import Customer
            from sales.models import Sale
            
            if customer_id:
                customers = Customer.objects.filter(id=customer_id)
            else:
                customers = Customer.objects.all()[:100]
            
            results = []
            
            for customer in customers:
                # حساب عوامل الخطر
                last_sale = Sale.objects.filter(customer=customer).order_by('-created_at').first()
                
                days_since_last = 0
                if last_sale:
                    days_since_last = (timezone.now() - last_sale.created_at).days
                
                total_sales = Sale.objects.filter(customer=customer).count()
                
                # حساب احتمال الفقدان (مبسط)
                churn_probability = min(100, (days_since_last / 30) * 20)
                
                if total_sales < 3:
                    churn_probability += 20
                
                results.append({
                    'customer_id': customer.id,
                    'customer_name': str(customer),
                    'churn_probability': min(100, churn_probability),
                    'days_since_last_purchase': days_since_last,
                    'total_purchases': total_sales,
                    'risk_level': 'high' if churn_probability > 60 else 'medium' if churn_probability > 30 else 'low'
                })
            
            return sorted(results, key=lambda x: -x['churn_probability'])
            
        except Exception as e:
            return {'error': str(e)}


class InventoryOptimizationService:
    """خدمة تحسين المخزون"""
    
    def analyze(self):
        """تحليل وتحسين المخزون"""
        try:
            from inventory.models import Product
            
            products = Product.objects.all()
            
            recommendations = []
            
            for product in products:
                stock = getattr(product, 'stock', 0)
                reorder_level = getattr(product, 'reorder_level', 10)
                
                if stock < reorder_level:
                    recommendations.append({
                        'product_id': product.id,
                        'product_name': str(product),
                        'current_stock': stock,
                        'reorder_level': reorder_level,
                        'action': 'reorder',
                        'urgency': 'high' if stock == 0 else 'medium'
                    })
            
            return {
                'total_products': products.count(),
                'needs_reorder': len(recommendations),
                'recommendations': recommendations
            }
            
        except Exception as e:
            return {'error': str(e)}


class InsightGenerator:
    """مولد الرؤى الذكية"""
    
    def generate_insights(self):
        """توليد رؤى ذكية"""
        from .models import AIInsight
        
        insights = []
        
        # تحليل المبيعات
        sales_insight = self._analyze_sales_trend()
        if sales_insight:
            insights.append(sales_insight)
        
        # تحليل العملاء
        customer_insight = self._analyze_customer_activity()
        if customer_insight:
            insights.append(customer_insight)
        
        # تحليل المخزون
        inventory_insight = self._analyze_inventory()
        if inventory_insight:
            insights.append(inventory_insight)
        
        # حفظ الرؤى
        for insight_data in insights:
            AIInsight.objects.create(**insight_data)
        
        return insights
    
    def _analyze_sales_trend(self):
        """تحليل اتجاه المبيعات"""
        try:
            from sales.models import Sale
            
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            two_weeks_ago = today - timedelta(days=14)
            
            this_week = Sale.objects.filter(
                created_at__date__gte=week_ago
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            last_week = Sale.objects.filter(
                created_at__date__gte=two_weeks_ago,
                created_at__date__lt=week_ago
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            if last_week > 0:
                change = ((this_week - last_week) / last_week) * 100
                
                if abs(change) > 10:
                    return {
                        'title': f"{'ارتفاع' if change > 0 else 'انخفاض'} المبيعات بنسبة {abs(change):.1f}%",
                        'description': f"المبيعات هذا الأسبوع: {this_week:,.2f} مقارنة بـ {last_week:,.2f} الأسبوع الماضي",
                        'insight_type': 'trend',
                        'priority': 'high' if abs(change) > 20 else 'medium',
                        'data': {
                            'this_week': float(this_week),
                            'last_week': float(last_week),
                            'change_percent': float(change)
                        },
                        'suggested_actions': [
                            'مراجعة العوامل المؤثرة',
                            'تحليل المنتجات الأكثر مبيعاً'
                        ]
                    }
            return None
            
        except Exception:
            return None
    
    def _analyze_customer_activity(self):
        """تحليل نشاط العملاء"""
        try:
            from crm.models import Customer
            
            inactive_count = Customer.objects.filter(
                sales__isnull=True
            ).count()
            
            if inactive_count > 10:
                return {
                    'title': f"{inactive_count} عميل بدون نشاط",
                    'description': 'يوجد عملاء مسجلون لم يقوموا بأي عملية شراء',
                    'insight_type': 'opportunity',
                    'priority': 'medium',
                    'data': {'inactive_customers': inactive_count},
                    'suggested_actions': [
                        'إرسال عروض ترويجية',
                        'التواصل المباشر'
                    ]
                }
            return None
            
        except Exception:
            return None
    
    def _analyze_inventory(self):
        """تحليل المخزون"""
        try:
            from inventory.models import Product
            
            low_stock = Product.objects.filter(
                stock__lte=F('reorder_level')
            ).count()
            
            if low_stock > 0:
                return {
                    'title': f"{low_stock} منتج بمخزون منخفض",
                    'description': 'منتجات تحتاج إلى إعادة طلب',
                    'insight_type': 'risk',
                    'priority': 'high',
                    'data': {'low_stock_products': low_stock},
                    'suggested_actions': [
                        'مراجعة طلبات الموردين',
                        'تحديث مستويات إعادة الطلب'
                    ]
                }
            return None
            
        except Exception:
            return None
