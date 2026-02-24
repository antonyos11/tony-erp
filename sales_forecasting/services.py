"""
خدمات التنبؤ بالمبيعات والطلب
Sales & Demand Forecasting Services
"""
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Avg, Count, F, Q
from django.utils import timezone
import statistics
import math
from typing import Dict, List, Tuple, Optional

from .models import (
    ForecastPeriod, SalesForecast, DemandPattern, 
    InventoryRecommendation, ForecastAccuracyMetrics
)


class ForecastingService:
    """خدمة التنبؤ بالمبيعات"""
    
    @staticmethod
    def moving_average_forecast(product, periods: int = 3) -> Dict:
        """
        التنبؤ بالمتوسط المتحرك
        Moving Average Forecast
        """
        from sales.models import SaleOrderLine
        
        # الحصول على بيانات المبيعات التاريخية
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=periods * 30)
        
        sales_data = SaleOrderLine.objects.filter(
            product=product,
            order__order_date__gte=start_date,
            order__order_date__lte=end_date,
            order__status='completed'
        ).values('order__order_date').annotate(
            quantity=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price'))
        ).order_by('order__order_date')
        
        if not sales_data:
            return {
                'forecasted_quantity': Decimal('0'),
                'forecasted_revenue': Decimal('0'),
                'confidence_level': Decimal('0'),
                'method': 'moving_average',
                'historical_data': []
            }
        
        # حساب المتوسط المتحرك
        quantities = [item['quantity'] for item in sales_data]
        revenues = [item['revenue'] for item in sales_data]
        
        avg_quantity = sum(quantities) / len(quantities) if quantities else 0
        avg_revenue = sum(revenues) / len(revenues) if revenues else 0
        
        # حساب مستوى الثقة (بناءً على الانحراف المعياري)
        if len(quantities) > 1:
            std_dev = statistics.stdev(quantities)
            cv = (std_dev / avg_quantity * 100) if avg_quantity > 0 else 100
            confidence = max(0, 100 - cv)
        else:
            confidence = 50
        
        return {
            'forecasted_quantity': Decimal(str(avg_quantity)),
            'forecasted_revenue': Decimal(str(avg_revenue)),
            'confidence_level': Decimal(str(confidence)),
            'method': 'moving_average',
            'historical_data': list(sales_data)
        }
    
    @staticmethod
    def exponential_smoothing_forecast(product, alpha: float = 0.3) -> Dict:
        """
        التنبؤ بالتمهيد الأسي
        Exponential Smoothing Forecast
        """
        from sales.models import SaleOrderLine
        
        # الحصول على بيانات المبيعات
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        sales_data = list(SaleOrderLine.objects.filter(
            product=product,
            order__order_date__gte=start_date,
            order__order_date__lte=end_date,
            order__status='completed'
        ).values('order__order_date').annotate(
            quantity=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price'))
        ).order_by('order__order_date'))
        
        if not sales_data:
            return {
                'forecasted_quantity': Decimal('0'),
                'forecasted_revenue': Decimal('0'),
                'confidence_level': Decimal('0'),
                'method': 'exponential_smoothing'
            }
        
        # التمهيد الأسي
        forecast_qty = float(sales_data[0]['quantity'])
        forecast_rev = float(sales_data[0]['revenue'])
        
        for data in sales_data[1:]:
            forecast_qty = alpha * float(data['quantity']) + (1 - alpha) * forecast_qty
            forecast_rev = alpha * float(data['revenue']) + (1 - alpha) * forecast_rev
        
        # حساب مستوى الثقة
        quantities = [float(item['quantity']) for item in sales_data]
        if len(quantities) > 1:
            errors = [abs(quantities[i] - forecast_qty) for i in range(len(quantities))]
            mean_error = sum(errors) / len(errors)
            confidence = max(0, 100 - (mean_error / forecast_qty * 100)) if forecast_qty > 0 else 50
        else:
            confidence = 50
        
        return {
            'forecasted_quantity': Decimal(str(forecast_qty)),
            'forecasted_revenue': Decimal(str(forecast_rev)),
            'confidence_level': Decimal(str(confidence)),
            'method': 'exponential_smoothing',
            'historical_data': sales_data
        }
    
    @staticmethod
    def seasonal_forecast(product, period_type: str = 'monthly') -> Dict:
        """
        التنبؤ الموسمي
        Seasonal Forecast
        """
        from sales.models import SaleOrderLine
        
        # الحصول على بيانات سنة كاملة
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)
        
        sales_data = SaleOrderLine.objects.filter(
            product=product,
            order__order_date__gte=start_date,
            order__order_date__lte=end_date,
            order__status='completed'
        ).values('order__order_date').annotate(
            quantity=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price'))
        )
        
        if not sales_data:
            return {
                'forecasted_quantity': Decimal('0'),
                'forecasted_revenue': Decimal('0'),
                'confidence_level': Decimal('0'),
                'method': 'seasonal'
            }
        
        # تجميع حسب الشهر
        monthly_sales = {}
        for item in sales_data:
            month = item['order__order_date'].month
            if month not in monthly_sales:
                monthly_sales[month] = {'quantity': 0, 'revenue': 0, 'count': 0}
            monthly_sales[month]['quantity'] += float(item['quantity'])
            monthly_sales[month]['revenue'] += float(item['revenue'])
            monthly_sales[month]['count'] += 1
        
        # حساب متوسط كل شهر
        current_month = timezone.now().month
        next_month = (current_month % 12) + 1
        
        if next_month in monthly_sales:
            forecast_qty = monthly_sales[next_month]['quantity'] / monthly_sales[next_month]['count']
            forecast_rev = monthly_sales[next_month]['revenue'] / monthly_sales[next_month]['count']
            confidence = 75  # مستوى ثقة جيد للتنبؤ الموسمي
        else:
            # استخدام المتوسط العام
            total_qty = sum(m['quantity'] for m in monthly_sales.values())
            total_rev = sum(m['revenue'] for m in monthly_sales.values())
            total_count = sum(m['count'] for m in monthly_sales.values())
            forecast_qty = total_qty / total_count if total_count > 0 else 0
            forecast_rev = total_rev / total_count if total_count > 0 else 0
            confidence = 50
        
        return {
            'forecasted_quantity': Decimal(str(forecast_qty)),
            'forecasted_revenue': Decimal(str(forecast_rev)),
            'confidence_level': Decimal(str(confidence)),
            'method': 'seasonal',
            'seasonality_factors': monthly_sales
        }
    
    @staticmethod
    def generate_forecast(product, period, method: str = 'moving_average') -> SalesForecast:
        """
        إنشاء تنبؤ جديد
        Generate New Forecast
        """
        forecast_methods = {
            'moving_average': ForecastingService.moving_average_forecast,
            'exponential_smoothing': ForecastingService.exponential_smoothing_forecast,
            'seasonal': ForecastingService.seasonal_forecast,
        }
        
        forecast_func = forecast_methods.get(method, ForecastingService.moving_average_forecast)
        forecast_data = forecast_func(product)
        
        forecast = SalesForecast.objects.create(
            period=period,
            product=product,
            forecasted_quantity=forecast_data['forecasted_quantity'],
            forecasted_revenue=forecast_data['forecasted_revenue'],
            confidence_level=forecast_data['confidence_level'],
            method=method,
            historical_data=forecast_data.get('historical_data', {}),
            seasonality_factors=forecast_data.get('seasonality_factors', {})
        )
        
        return forecast


class DemandAnalysisService:
    """خدمة تحليل الطلب"""
    
    @staticmethod
    def analyze_demand_pattern(product) -> DemandPattern:
        """
        تحليل نمط الطلب
        Analyze Demand Pattern
        """
        from sales.models import SaleOrderLine
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=180)  # 6 أشهر
        
        # الحصول على البيانات اليومية
        daily_sales = list(SaleOrderLine.objects.filter(
            product=product,
            order__order_date__gte=start_date,
            order__order_date__lte=end_date,
            order__status='completed'
        ).values('order__order_date').annotate(
            quantity=Sum('quantity')
        ).order_by('order__order_date'))
        
        if not daily_sales:
            return None
        
        quantities = [float(item['quantity']) for item in daily_sales]
        
        # حساب الإحصائيات
        avg_demand = statistics.mean(quantities)
        std_dev = statistics.stdev(quantities) if len(quantities) > 1 else 0
        cv = (std_dev / avg_demand * 100) if avg_demand > 0 else 0
        
        # تحديد نوع النمط
        if cv < 20:
            pattern_type = 'stable'
        elif cv > 50:
            pattern_type = 'volatile'
        else:
            # فحص الاتجاه
            first_half = quantities[:len(quantities)//2]
            second_half = quantities[len(quantities)//2:]
            avg_first = statistics.mean(first_half) if first_half else 0
            avg_second = statistics.mean(second_half) if second_half else 0
            
            if avg_second > avg_first * 1.1:
                pattern_type = 'growing'
            elif avg_second < avg_first * 0.9:
                pattern_type = 'declining'
            else:
                pattern_type = 'stable'
        
        # تحليل الموسمية
        monthly_sales = {}
        for item in daily_sales:
            month = item['order__order_date'].month
            if month not in monthly_sales:
                monthly_sales[month] = []
            monthly_sales[month].append(float(item['quantity']))
        
        has_seasonality = len(monthly_sales) >= 3
        peak_months = []
        low_months = []
        
        if has_seasonality:
            monthly_avg = {month: statistics.mean(sales) for month, sales in monthly_sales.items()}
            overall_avg = statistics.mean(quantities)
            
            for month, avg in monthly_avg.items():
                if avg > overall_avg * 1.2:
                    peak_months.append(month)
                elif avg < overall_avg * 0.8:
                    low_months.append(month)
        
        # حساب التوصيات
        lead_time = 7  # أسبوع افتراضي
        service_level = 0.95  # 95% مستوى خدمة
        z_score = 1.65  # لمستوى خدمة 95%
        
        safety_stock = z_score * std_dev * math.sqrt(lead_time)
        reorder_point = (avg_demand * lead_time) + safety_stock
        
        # كمية الطلب الاقتصادية (EOQ)
        # مبسطة - يمكن تحسينها لاحقاً
        eoq = avg_demand * 30  # شهر من الطلب
        
        # إنشاء أو تحديث نمط الطلب
        demand_pattern, created = DemandPattern.objects.update_or_create(
            product=product,
            is_active=True,
            defaults={
                'pattern_type': pattern_type,
                'average_daily_demand': Decimal(str(avg_demand)),
                'standard_deviation': Decimal(str(std_dev)),
                'coefficient_of_variation': Decimal(str(cv)),
                'has_seasonality': has_seasonality,
                'peak_months': peak_months,
                'low_months': low_months,
                'analysis_start_date': start_date,
                'analysis_end_date': end_date,
                'data_points_count': len(daily_sales),
                'recommended_reorder_point': Decimal(str(reorder_point)),
                'recommended_safety_stock': Decimal(str(safety_stock)),
                'recommended_order_quantity': Decimal(str(eoq)),
            }
        )
        
        return demand_pattern
    
    @staticmethod
    def generate_inventory_recommendations(product) -> List[InventoryRecommendation]:
        """
        إنشاء توصيات المخزون
        Generate Inventory Recommendations
        """
        recommendations = []
        
        # تحليل نمط الطلب
        demand_pattern = DemandAnalysisService.analyze_demand_pattern(product)
        if not demand_pattern:
            return recommendations
        
        # الحصول على المخزون الحالي
        try:
            from inventory.models import Stock
            current_stock = Stock.objects.filter(product=product).aggregate(
                total=Sum('quantity')
            )['total'] or Decimal('0')
        except:
            current_stock = Decimal('0')
        
        # توصيات بناءً على النمط
        if current_stock < demand_pattern.recommended_reorder_point:
            # مخزون منخفض - طلب عاجل
            recommendation = InventoryRecommendation.objects.create(
                product=product,
                recommendation_type='urgent_order',
                priority='critical' if current_stock < demand_pattern.recommended_safety_stock else 'high',
                current_stock=current_stock,
                current_reorder_point=demand_pattern.recommended_reorder_point,
                recommended_stock_level=demand_pattern.recommended_reorder_point + demand_pattern.recommended_safety_stock,
                recommended_order_quantity=demand_pattern.recommended_order_quantity,
                reason=f"المخزون الحالي ({current_stock}) أقل من نقطة إعادة الطلب ({demand_pattern.recommended_reorder_point}). "
                       f"متوسط الطلب اليومي: {demand_pattern.average_daily_demand}",
                demand_pattern=demand_pattern
            )
            recommendations.append(recommendation)
        
        elif demand_pattern.pattern_type == 'growing':
            # طلب نامي - زيادة المخزون
            recommended_increase = current_stock * Decimal('0.2')  # زيادة 20%
            recommendation = InventoryRecommendation.objects.create(
                product=product,
                recommendation_type='stock_up',
                priority='medium',
                current_stock=current_stock,
                current_reorder_point=demand_pattern.recommended_reorder_point,
                recommended_stock_level=current_stock + recommended_increase,
                recommended_order_quantity=recommended_increase,
                reason=f"الطلب في ازدياد. متوسط الطلب اليومي: {demand_pattern.average_daily_demand}. "
                       f"يُوصى بزيادة المخزون بنسبة 20%",
                demand_pattern=demand_pattern
            )
            recommendations.append(recommendation)
        
        elif demand_pattern.pattern_type == 'declining':
            # طلب متراجع - تقليل المخزون
            recommendation = InventoryRecommendation.objects.create(
                product=product,
                recommendation_type='slow_moving',
                priority='low',
                current_stock=current_stock,
                current_reorder_point=demand_pattern.recommended_reorder_point,
                recommended_stock_level=demand_pattern.recommended_safety_stock * 2,
                recommended_order_quantity=Decimal('0'),
                reason=f"الطلب في تراجع. متوسط الطلب اليومي: {demand_pattern.average_daily_demand}. "
                       f"يُوصى بتقليل المخزون وإيقاف الطلبات مؤقتاً",
                demand_pattern=demand_pattern
            )
            recommendations.append(recommendation)
        
        return recommendations


class ForecastAccuracyService:
    """خدمة قياس دقة التنبؤ"""
    
    @staticmethod
    def calculate_accuracy_metrics(period: ForecastPeriod, product=None) -> ForecastAccuracyMetrics:
        """
        حساب مقاييس دقة التنبؤ
        Calculate Forecast Accuracy Metrics
        """
        # الحصول على التنبؤات
        forecasts = SalesForecast.objects.filter(
            period=period,
            actual_quantity__isnull=False
        )
        
        if product:
            forecasts = forecasts.filter(product=product)
        
        if not forecasts.exists():
            return None
        
        # حساب المقاييس
        total_forecasts = forecasts.count()
        errors = []
        percentage_errors = []
        squared_errors = []
        
        for forecast in forecasts:
            error = float(forecast.actual_quantity - forecast.forecasted_quantity)
            abs_error = abs(error)
            squared_error = error ** 2
            
            errors.append(abs_error)
            squared_errors.append(squared_error)
            
            if forecast.forecasted_quantity > 0:
                percentage_error = (abs_error / float(forecast.forecasted_quantity)) * 100
                percentage_errors.append(percentage_error)
        
        # حساب المتوسطات
        mae = sum(errors) / len(errors) if errors else 0
        mse = sum(squared_errors) / len(squared_errors) if squared_errors else 0
        rmse = math.sqrt(mse) if mse > 0 else 0
        mape = sum(percentage_errors) / len(percentage_errors) if percentage_errors else 0
        
        # الدقة الإجمالية (100% - MAPE)
        overall_accuracy = max(0, 100 - mape)
        
        # عدد التنبؤات الدقيقة (ضمن 10% من الفعلي)
        accurate_forecasts = sum(1 for pe in percentage_errors if pe <= 10)
        
        # إنشاء أو تحديث المقاييس
        metrics, created = ForecastAccuracyMetrics.objects.update_or_create(
            period=period,
            product=product,
            defaults={
                'total_forecasts': total_forecasts,
                'accurate_forecasts': accurate_forecasts,
                'overall_accuracy': Decimal(str(overall_accuracy)),
                'mean_absolute_error': Decimal(str(mae)),
                'mean_squared_error': Decimal(str(mse)),
                'root_mean_squared_error': Decimal(str(rmse)),
                'mean_absolute_percentage_error': Decimal(str(mape)),
            }
        )
        
        return metrics
