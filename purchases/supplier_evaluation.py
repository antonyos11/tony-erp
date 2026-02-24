"""
Supplier Evaluation & Rating System
نظام تقييم وتصنيف الموردين

يقيّم الموردين بناءً على:
- السعر
- الجودة
- الالتزام بالمواعيد
- الخدمة
"""

from django.db import models
from django.conf import settings
from decimal import Decimal
from typing import Dict, List, Optional
from django.utils import timezone
from datetime import timedelta


class SupplierEvaluation(models.Model):
    """تقييم المورد"""
    
    PERIOD_CHOICES = [
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي'),
    ]
    
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.CASCADE, related_name='evaluations', verbose_name='المورد')
    evaluation_date = models.DateField('تاريخ التقييم', default=timezone.now)
    period = models.CharField('الفترة', max_length=20, choices=PERIOD_CHOICES, default='monthly')
    
    # معايير التقييم (من 0 إلى 100)
    price_score = models.DecimalField('تقييم السعر', max_digits=5, decimal_places=2, default=Decimal('0'))
    quality_score = models.DecimalField('تقييم الجودة', max_digits=5, decimal_places=2, default=Decimal('0'))
    delivery_score = models.DecimalField('تقييم الالتزام بالمواعيد', max_digits=5, decimal_places=2, default=Decimal('0'))
    service_score = models.DecimalField('تقييم الخدمة', max_digits=5, decimal_places=2, default=Decimal('0'))
    responsiveness_score = models.DecimalField('تقييم سرعة الاستجابة', max_digits=5, decimal_places=2, default=Decimal('0'))
    
    # الأوزان (يجب أن يكون مجموعها 100%)
    price_weight = models.DecimalField('وزن السعر', max_digits=5, decimal_places=2, default=Decimal('30'))
    quality_weight = models.DecimalField('وزن الجودة', max_digits=5, decimal_places=2, default=Decimal('35'))
    delivery_weight = models.DecimalField('وزن الالتزام', max_digits=5, decimal_places=2, default=Decimal('20'))
    service_weight = models.DecimalField('وزن الخدمة', max_digits=5, decimal_places=2, default=Decimal('10'))
    responsiveness_weight = models.DecimalField('وزن الاستجابة', max_digits=5, decimal_places=2, default=Decimal('5'))
    
    # النتيجة الإجمالية
    total_score = models.DecimalField('النتيجة الإجمالية', max_digits=5, decimal_places=2, default=Decimal('0'))
    rating = models.CharField('التصنيف', max_length=1, default='C')  # A, B, C, D, F
    
    # البيانات الإحصائية
    total_orders = models.IntegerField('إجمالي الطلبات', default=0)
    total_value = models.DecimalField('إجمالي القيمة', max_digits=15, decimal_places=2, default=Decimal('0'))
    on_time_deliveries = models.IntegerField('التسليمات في الموعد', default=0)
    late_deliveries = models.IntegerField('التسليمات المتأخرة', default=0)
    quality_issues = models.IntegerField('مشاكل الجودة', default=0)
    
    # التوصية
    recommendation = models.TextField('التوصية', blank=True)
    is_approved = models.BooleanField('موافق عليه', default=True)
    
    evaluated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='قيّم بواسطة')
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تقييم مورد'
        verbose_name_plural = 'تقييمات الموردين'
        ordering = ['-evaluation_date']
        unique_together = ['supplier', 'evaluation_date', 'period']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.evaluation_date} ({self.rating})"
    
    def calculate_total_score(self):
        """حساب النتيجة الإجمالية"""
        total = (
            (self.price_score * self.price_weight / 100) +
            (self.quality_score * self.quality_weight / 100) +
            (self.delivery_score * self.delivery_weight / 100) +
            (self.service_score * self.service_weight / 100) +
            (self.responsiveness_score * self.responsiveness_weight / 100)
        )
        
        self.total_score = total
        
        # تحديد التصنيف
        if total >= 90:
            self.rating = 'A'
            self.recommendation = 'مورد ممتاز - يوصى به بشدة'
        elif total >= 80:
            self.rating = 'B'
            self.recommendation = 'مورد جيد - يوصى به'
        elif total >= 70:
            self.rating = 'C'
            self.recommendation = 'مورد مقبول - يحتاج تحسين'
        elif total >= 60:
            self.rating = 'D'
            self.recommendation = 'مورد ضعيف - يحتاج مراجعة جدية'
        else:
            self.rating = 'F'
            self.recommendation = 'مورد غير مقبول - ينصح باستبداله'
            self.is_approved = False
        
        self.save()


class SupplierScore(models.Model):
    """درجات المورد التاريخية"""
    
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.CASCADE, related_name='scores', verbose_name='المورد')
    date = models.DateField('التاريخ', default=timezone.now)
    
    score_type = models.CharField('نوع الدرجة', max_length=50)  # price, quality, delivery, service
    score = models.DecimalField('الدرجة', max_digits=5, decimal_places=2)
    
    reference_type = models.CharField('نوع المرجع', max_length=50, blank=True)  # purchase_order, quality_inspection
    reference_id = models.IntegerField('معرف المرجع', null=True, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'درجة مورد'
        verbose_name_plural = 'درجات الموردين'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['supplier', 'score_type', 'date']),
        ]
    
    def __str__(self):
        return f"{self.supplier.name} - {self.score_type}: {self.score}"


class AlternativeSupplier(models.Model):
    """موردين بديلين للمنتج"""
    
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='alternative_suppliers', verbose_name='المنتج')
    primary_supplier = models.ForeignKey('partners.Supplier', on_delete=models.CASCADE, related_name='primary_products', verbose_name='المورد الأساسي')
    alternative_supplier = models.ForeignKey('partners.Supplier', on_delete=models.CASCADE, related_name='alternative_products', verbose_name='المورد البديل')
    
    priority = models.IntegerField('الأولوية', default=1)  # 1 = أولى، 2 = ثانية، إلخ
    
    # معلومات المورد البديل
    unit_price = models.DecimalField('سعر الوحدة', max_digits=12, decimal_places=2)
    lead_time_days = models.IntegerField('وقت التوريد بالأيام', default=7)
    minimum_order_quantity = models.IntegerField('الحد الأدنى للطلب', default=1)
    
    quality_rating = models.DecimalField('تقييم الجودة', max_digits=5, decimal_places=2, default=Decimal('0'))
    last_purchase_date = models.DateField('آخر تاريخ شراء', null=True, blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'مورد بديل'
        verbose_name_plural = 'موردين بديلين'
        ordering = ['product', 'priority']
        unique_together = ['product', 'primary_supplier', 'alternative_supplier']
    
    def __str__(self):
        return f"{self.product.name} - {self.alternative_supplier.name} (البديل {self.priority})"


class SupplierEvaluationService:
    """خدمة تقييم الموردين"""
    
    @staticmethod
    def auto_evaluate_supplier(supplier, period_days: int = 30) -> SupplierEvaluation:
        """تقييم تلقائي للمورد بناءً على البيانات الفعلية"""
        from purchases.models import PurchaseOrder, PurchaseBill
        from quality_control.models import QualityInspection, QualityIssue
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # جمع البيانات
        orders = PurchaseOrder.objects.filter(
            supplier=supplier,
            date__gte=start_date
        )
        
        total_orders = orders.count()
        
        if total_orders == 0:
            # لا توجد طلبات في هذه الفترة
            return None
        
        # 1. تقييم السعر (مقارنة بالمتوسط السوقي)
        price_score = SupplierEvaluationService._calculate_price_score(supplier, start_date)
        
        # 2. تقييم الجودة (بناءً على فحوصات الجودة)
        quality_score = SupplierEvaluationService._calculate_quality_score(supplier, start_date)
        
        # 3. تقييم الالتزام بالمواعيد
        delivery_score = SupplierEvaluationService._calculate_delivery_score(supplier, start_date)
        
        # 4. تقييم الخدمة (بناءً على تقييمات يدوية أو افتراضي)
        service_score = Decimal('75')  # يمكن تحسينه لاحقاً
        
        # 5. تقييم سرعة الاستجابة
        responsiveness_score = Decimal('75')  # يمكن تحسينه لاحقاً
        
        # إنشاء التقييم
        evaluation = SupplierEvaluation.objects.create(
            supplier=supplier,
            evaluation_date=timezone.now().date(),
            period='monthly' if period_days <= 31 else 'quarterly',
            price_score=price_score,
            quality_score=quality_score,
            delivery_score=delivery_score,
            service_score=service_score,
            responsiveness_score=responsiveness_score,
            total_orders=total_orders,
            total_value=orders.aggregate(models.Sum('items__quantity'))['items__quantity__sum'] or 0
        )
        
        evaluation.calculate_total_score()
        
        return evaluation
    
    @staticmethod
    def _calculate_price_score(supplier, start_date) -> Decimal:
        """حساب تقييم السعر"""
        from purchases.models import PurchaseItem
        from django.db.models import Avg
        
        # حساب متوسط أسعار هذا المورد
        supplier_avg = PurchaseItem.objects.filter(
            bill__supplier=supplier,
            bill__date__gte=start_date
        ).aggregate(avg_price=Avg('cost'))['avg_price'] or Decimal('0')
        
        # حساب متوسط أسعار السوق (كل الموردين)
        market_avg = PurchaseItem.objects.filter(
            bill__date__gte=start_date
        ).aggregate(avg_price=Avg('cost'))['avg_price'] or Decimal('1')
        
        if market_avg == 0:
            market_avg = Decimal('1')
        
        # كلما كان السعر أقل، كان التقييم أعلى
        if supplier_avg <= market_avg:
            # أرخص أو مساوي للسوق
            ratio = supplier_avg / market_avg
            score = 100 - ((1 - ratio) * 50)  # يعطي درجة بين 50-100
        else:
            # أغلى من السوق
            ratio = market_avg / supplier_avg
            score = ratio * 100
        
        return min(Decimal('100'), max(Decimal('0'), score))
    
    @staticmethod
    def _calculate_quality_score(supplier, start_date) -> Decimal:
        """حساب تقييم الجودة"""
        from quality_control.models import QualityInspection, QualityIssue
        from purchases.models import PurchaseBill
        
        # عدد فحوصات الجودة
        bills = PurchaseBill.objects.filter(
            supplier=supplier,
            date__gte=start_date
        )
        
        total_inspections = QualityInspection.objects.filter(
            batch_number__in=[b.number for b in bills]
        ).count()
        
        if total_inspections == 0:
            return Decimal('80')  # درجة افتراضية إذا لم يكن هناك فحوصات
        
        # عدد الفحوصات الناجحة
        passed_inspections = QualityInspection.objects.filter(
            batch_number__in=[b.number for b in bills],
            status='passed'
        ).count()
        
        # حساب النسبة المئوية
        pass_rate = (passed_inspections / total_inspections) * 100 if total_inspections > 0 else 0
        
        return Decimal(str(pass_rate))
    
    @staticmethod
    def _calculate_delivery_score(supplier, start_date) -> Decimal:
        """حساب تقييم الالتزام بالمواعيد"""
        from purchases.models import PurchaseOrder
        
        orders = PurchaseOrder.objects.filter(
            supplier=supplier,
            date__gte=start_date,
            status__in=['completed', 'partial']
        )
        
        total_orders = orders.count()
        
        if total_orders == 0:
            return Decimal('80')  # درجة افتراضية
        
        # حساب الطلبات التي تم تسليمها في الموعد
        on_time = 0
        for order in orders:
            if order.expected_date and order.bill:
                if order.bill.date <= order.expected_date:
                    on_time += 1
            else:
                on_time += 1  # إذا لم يكن هناك موعد محدد، نعتبره في الموعد
        
        on_time_rate = (on_time / total_orders) * 100
        
        return Decimal(str(on_time_rate))
    
    @staticmethod
    def suggest_alternative_supplier(product, primary_supplier) -> Optional[Dict]:
        """اقتراح مورد بديل للمنتج"""
        from partners.models import Supplier
        
        # البحث في الموردين البديلين المحفوظين
        alternatives = AlternativeSupplier.objects.filter(
            product=product,
            primary_supplier=primary_supplier,
            is_active=True
        ).order_by('priority')
        
        if alternatives.exists():
            best_alt = alternatives.first()
            
            # الحصول على آخر تقييم للمورد البديل
            latest_eval = SupplierEvaluation.objects.filter(
                supplier=best_alt.alternative_supplier
            ).order_by('-evaluation_date').first()
            
            return {
                'supplier': best_alt.alternative_supplier,
                'unit_price': float(best_alt.unit_price),
                'lead_time_days': best_alt.lead_time_days,
                'quality_rating': float(best_alt.quality_rating),
                'evaluation': {
                    'total_score': float(latest_eval.total_score) if latest_eval else 0,
                    'rating': latest_eval.rating if latest_eval else 'N/A'
                } if latest_eval else None,
                'notes': best_alt.notes
            }
        
        # إذا لم يوجد بديل محفوظ، ابحث عن موردين آخرين يوفرون نفس المنتج
        from purchases.models import PurchaseItem
        
        other_suppliers = PurchaseItem.objects.filter(
            product=product
        ).exclude(
            bill__supplier=primary_supplier
        ).values('bill__supplier').distinct()
        
        if other_suppliers.exists():
            # اختيار المورد الأعلى تقييماً
            best_supplier = None
            best_score = 0
            
            for s in other_suppliers:
                supplier = Supplier.objects.get(id=s['bill__supplier'])
                latest_eval = SupplierEvaluation.objects.filter(
                    supplier=supplier
                ).order_by('-evaluation_date').first()
                
                if latest_eval and latest_eval.total_score > best_score:
                    best_score = latest_eval.total_score
                    best_supplier = supplier
            
            if best_supplier:
                # حساب متوسط السعر
                avg_price = PurchaseItem.objects.filter(
                    product=product,
                    bill__supplier=best_supplier
                ).aggregate(models.Avg('cost'))['cost__avg'] or Decimal('0')
                
                return {
                    'supplier': best_supplier,
                    'unit_price': float(avg_price),
                    'lead_time_days': 7,  # افتراضي
                    'quality_rating': float(best_score) if best_score > 0 else 75,
                    'evaluation': {
                        'total_score': float(best_score),
                        'rating': 'B'
                    },
                    'notes': 'مورد بديل تم اقتراحه تلقائياً بناءً على التقييمات'
                }
        
        return None
    
    @staticmethod
    def get_supplier_ranking(period_days: int = 30) -> List[Dict]:
        """الحصول على ترتيب الموردين"""
        from partners.models import Supplier
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        suppliers = Supplier.objects.filter(is_active=True)
        rankings = []
        
        for supplier in suppliers:
            latest_eval = SupplierEvaluation.objects.filter(
                supplier=supplier,
                evaluation_date__gte=start_date
            ).order_by('-evaluation_date').first()
            
            if latest_eval:
                rankings.append({
                    'supplier': supplier,
                    'score': float(latest_eval.total_score),
                    'rating': latest_eval.rating,
                    'total_orders': latest_eval.total_orders,
                    'evaluation_date': latest_eval.evaluation_date.isoformat()
                })
        
        # ترتيب حسب الدرجة
        rankings.sort(key=lambda x: x['score'], reverse=True)
        
        return rankings


# Singleton instance
supplier_service = SupplierEvaluationService()
