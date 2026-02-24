"""
AI-Powered Production Line Recommendation System
نظام ترشيح خط الإنتاج الأنسب بالذكاء الاصطناعي

يرشح خط الإنتاج الأمثل بناءً على:
- التكلفة المتوقعة
- الوقت المطلوب
- الكمية والمقاس
- السعة المتاحة
- جودة الإنتاج
"""

from typing import List, Dict
from decimal import Decimal
from django.db.models import Avg, Sum, Count
from production.models import ProductionWorkCenter, ProductionOrder
from .models import SmartQuote, ProductionLineRecommendation


class ProductionLineAI:
    """محرك الذكاء الاصطناعي لترشيح خطوط الإنتاج"""
    
    def __init__(self, smart_quote: SmartQuote):
        self.quote = smart_quote
        self.work_centers = ProductionWorkCenter.objects.filter(is_active=True)
    
    def recommend_best_lines(self, top_n: int = 3) -> List[ProductionLineRecommendation]:
        """ترشيح أفضل خطوط الإنتاج"""
        recommendations = []
        
        for work_center in self.work_centers:
            score_data = self._calculate_line_score(work_center)
            
            recommendation = ProductionLineRecommendation.objects.create(
                smart_quote=self.quote,
                work_center=work_center,
                estimated_cost=score_data['estimated_cost'],
                estimated_time=score_data['estimated_time'],
                capacity_match=score_data['capacity_match'],
                quality_score=score_data['quality_score'],
                recommendation_score=score_data['total_score'],
                is_recommended=(len(recommendations) < top_n),
                notes=score_data['notes']
            )
            
            recommendations.append(recommendation)
        
        # ترتيب حسب الدرجة
        recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)
        
        # تحديد المرشحين الأوائل
        for i, rec in enumerate(recommendations[:top_n]):
            rec.is_recommended = True
            rec.save()
        
        return recommendations[:top_n]
    
    def _calculate_line_score(self, work_center: ProductionWorkCenter) -> Dict:
        """حساب درجة خط الإنتاج"""
        
        # 1. تقدير التكلفة
        estimated_cost = self._estimate_production_cost(work_center)
        
        # 2. تقدير الوقت
        estimated_time = self._estimate_production_time(work_center)
        
        # 3. مطابقة السعة
        capacity_match = self._calculate_capacity_match(work_center)
        
        # 4. درجة الجودة (من التاريخ)
        quality_score = self._calculate_quality_score(work_center)
        
        # 5. حساب الدرجة الإجمالية (0-100)
        # الأوزان: التكلفة 40%، الوقت 30%، السعة 20%، الجودة 10%
        cost_score = max(0, 100 - (float(estimated_cost) / float(self.quote.total_cost) * 100))
        time_score = max(0, 100 - (float(estimated_time) / 10) * 10)  # 10 hours = baseline
        
        total_score = (
            cost_score * Decimal('0.40') +
            time_score * Decimal('0.30') +
            capacity_match * Decimal('0.20') +
            quality_score * Decimal('0.10')
        )
        
        notes = self._generate_recommendation_notes(
            work_center, estimated_cost, estimated_time, capacity_match, quality_score
        )
        
        return {
            'estimated_cost': estimated_cost,
            'estimated_time': estimated_time,
            'capacity_match': capacity_match,
            'quality_score': quality_score,
            'total_score': total_score,
            'notes': notes
        }
    
    def _estimate_production_cost(self, work_center: ProductionWorkCenter) -> Decimal:
        """تقدير تكلفة الإنتاج على هذا الخط"""
        
        # التكلفة الأساسية من العرض
        base_cost = self.quote.total_cost
        
        # معامل تكلفة الخط (من البيانات التاريخية)
        cost_multiplier = Decimal('1.0')
        
        # إذا كان الخط أكثر تكلفة من المتوسط
        avg_hourly_rate = work_center.hourly_rate or Decimal('50.0')
        
        if avg_hourly_rate > Decimal('75.0'):
            cost_multiplier = Decimal('1.2')
        elif avg_hourly_rate < Decimal('40.0'):
            cost_multiplier = Decimal('0.9')
        
        return base_cost * cost_multiplier
    
    def _estimate_production_time(self, work_center: ProductionWorkCenter) -> Decimal:
        """تقدير وقت الإنتاج (بالساعات)"""
        
        # الوقت الأساسي حسب الكمية والتعقيد
        base_time = Decimal('2.0')  # ساعتان للبدء
        
        # معامل الكمية
        quantity_factor = Decimal(str(self.quote.quantity)) / Decimal('10.0')
        
        # معامل التعقيد
        complexity_factors = {
            'simple': Decimal('1.0'),
            'medium': Decimal('1.5'),
            'complex': Decimal('2.0'),
        }
        complexity_factor = complexity_factors.get(self.quote.complexity, Decimal('1.0'))
        
        # معامل سرعة الخط (من البيانات التاريخية)
        line_speed_factor = Decimal('1.0')
        
        # حساب من متوسط أوامر الإنتاج السابقة
        past_orders = ProductionOrder.objects.filter(
            work_center=work_center,
            status='completed'
        ).aggregate(
            avg_duration=Avg('actual_duration')
        )
        
        if past_orders['avg_duration']:
            # الخط أسرع من المتوسط
            if past_orders['avg_duration'] < 5:
                line_speed_factor = Decimal('0.8')
            elif past_orders['avg_duration'] > 10:
                line_speed_factor = Decimal('1.2')
        
        total_time = base_time + (quantity_factor * complexity_factor * line_speed_factor)
        
        return total_time
    
    def _calculate_capacity_match(self, work_center: ProductionWorkCenter) -> Decimal:
        """حساب مطابقة السعة (0-100)"""
        
        # السعة المتاحة (افتراضية - يمكن تحسينها)
        available_capacity = Decimal('80.0')  # 80% متاح
        
        # حساب السعة المطلوبة
        required_capacity = min(Decimal('100.0'), Decimal(str(self.quote.quantity)) / Decimal('10.0'))
        
        if required_capacity <= available_capacity:
            return Decimal('100.0')
        else:
            # نسبة المطابقة
            return (available_capacity / required_capacity) * Decimal('100.0')
    
    def _calculate_quality_score(self, work_center: ProductionWorkCenter) -> Decimal:
        """حساب درجة الجودة من التاريخ (0-100)"""
        
        # احصائيات من أوامر الإنتاج السابقة
        past_orders = ProductionOrder.objects.filter(
            work_center=work_center,
            status='completed'
        )
        
        total_orders = past_orders.count()
        
        if total_orders == 0:
            return Decimal('70.0')  # درجة افتراضية
        
        # حساب معدل النجاح (الأوامر المكتملة بدون مشاكل)
        success_rate = (total_orders / (total_orders + 1)) * 100
        
        return Decimal(str(success_rate))
    
    def _generate_recommendation_notes(
        self, 
        work_center: ProductionWorkCenter,
        cost: Decimal,
        time: Decimal,
        capacity: Decimal,
        quality: Decimal
    ) -> str:
        """توليد ملاحظات الترشيح"""
        
        notes = []
        
        # ملاحظات التكلفة
        if cost < self.quote.total_cost:
            notes.append(f"✓ تكلفة منخفضة: {cost:.2f} ج.م")
        else:
            notes.append(f"⚠ تكلفة مرتفعة: {cost:.2f} ج.م")
        
        # ملاحظات الوقت
        if time < Decimal('5.0'):
            notes.append(f"✓ وقت سريع: {time:.1f} ساعة")
        else:
            notes.append(f"⏳ وقت متوسط: {time:.1f} ساعة")
        
        # ملاحظات السعة
        if capacity >= Decimal('90.0'):
            notes.append("✓ سعة ممتازة")
        elif capacity >= Decimal('70.0'):
            notes.append("○ سعة جيدة")
        else:
            notes.append("⚠ سعة محدودة")
        
        # ملاحظات الجودة
        if quality >= Decimal('85.0'):
            notes.append("✓ جودة عالية")
        elif quality >= Decimal('70.0'):
            notes.append("○ جودة جيدة")
        else:
            notes.append("⚠ يحتاج تحسين الجودة")
        
        return " | ".join(notes)


def auto_recommend_production_line(smart_quote: SmartQuote) -> List[ProductionLineRecommendation]:
    """
    واجهة سريعة لترشيح خط الإنتاج تلقائياً
    
    الاستخدام:
        recommendations = auto_recommend_production_line(quote)
        best_line = recommendations[0].work_center
    """
    ai = ProductionLineAI(smart_quote)
    return ai.recommend_best_lines(top_n=3)
