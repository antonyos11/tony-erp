"""
Anomaly Detection & Proactive Alerts System
نظام الكشف عن الشذوذات والتنبيهات الاستباقية

يكتشف الأنماط غير العادية تلقائياً ويرسل تنبيهات قبل حدوث المشاكل
"""

from django.db import models
from django.db.models import Avg, Sum, Count, F, Q
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta, datetime
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import statistics


# ========================
# Models
# ========================

class AnomalyAlert(models.Model):
    """
    تنبيه الشذوذ
    
    تنبيه يتم إنشاؤه عند اكتشاف نمط غير طبيعي
    """
    
    SEVERITY_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('critical', 'حرج'),
    ]
    
    CATEGORY_CHOICES = [
        ('sales', 'المبيعات'),
        ('inventory', 'المخزون'),
        ('production', 'الإنتاج'),
        ('financial', 'مالي'),
        ('quality', 'الجودة'),
        ('performance', 'الأداء'),
        ('security', 'الأمان'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'جديد'),
        ('investigating', 'قيد التحقيق'),
        ('acknowledged', 'تم الاطلاع'),
        ('resolved', 'تم الحل'),
        ('false_positive', 'إنذار خاطئ'),
    ]
    
    # التصنيف
    category = models.CharField('الفئة', max_length=50, choices=CATEGORY_CHOICES)
    severity = models.CharField('الخطورة', max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='new')
    
    # التفاصيل
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف')
    anomaly_type = models.CharField('نوع الشذوذ', max_length=100)
    
    # البيانات
    detected_value = models.DecimalField('القيمة المكتشفة', max_digits=15, decimal_places=2, null=True)
    expected_value = models.DecimalField('القيمة المتوقعة', max_digits=15, decimal_places=2, null=True)
    deviation_percentage = models.DecimalField('نسبة الانحراف', max_digits=5, decimal_places=2, null=True)
    
    # الإجراءات الموصى بها
    recommended_actions = models.JSONField('الإجراءات الموصى بها', default=list)
    
    # المراجع
    related_model = models.CharField('النموذج المرتبط', max_length=100, null=True, blank=True)
    related_id = models.IntegerField('معرف السجل', null=True, blank=True)
    
    # المسؤول
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_anomalies',
        verbose_name='مسند إلى'
    )
    
    # التواريخ
    detected_at = models.DateTimeField('وقت الاكتشاف', auto_now_add=True)
    resolved_at = models.DateTimeField('وقت الحل', null=True, blank=True)
    
    # الملاحظات
    notes = models.TextField('ملاحظات', blank=True)
    
    class Meta:
        db_table = 'anomaly_alerts'
        verbose_name = 'تنبيه شذوذ'
        verbose_name_plural = 'تنبيهات الشذوذ'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['category', 'severity', 'status']),
            models.Index(fields=['detected_at']),
        ]
    
    def __str__(self):
        return f'{self.get_severity_display()} - {self.title}'
    
    def mark_as_resolved(self, user=None, notes=''):
        """تعيين كمحلول"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        if notes:
            self.notes = notes
        self.save()


class ProactiveWarning(models.Model):
    """
    تحذير استباقي
    
    تحذير يتم إرساله قبل حدوث مشكلة متوقعة
    """
    
    WARNING_TYPE_CHOICES = [
        ('stock_out', 'نفاد مخزون متوقع'),
        ('capacity_overload', 'حمل زائد متوقع'),
        ('cash_flow', 'مشكلة تدفق نقدي متوقعة'),
        ('deadline_risk', 'خطر فوات موعد'),
        ('quality_trend', 'اتجاه جودة سلبي'),
        ('cost_overrun', 'تجاوز تكلفة متوقع'),
    ]
    
    warning_type = models.CharField('نوع التحذير', max_length=50, choices=WARNING_TYPE_CHOICES)
    
    # التفاصيل
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف')
    
    # التوقعات
    predicted_date = models.DateField('التاريخ المتوقع', null=True)
    confidence_level = models.DecimalField('مستوى الثقة', max_digits=5, decimal_places=2)  # 0-100
    
    # البيانات
    current_value = models.DecimalField('القيمة الحالية', max_digits=15, decimal_places=2, null=True)
    threshold_value = models.DecimalField('قيمة الحد', max_digits=15, decimal_places=2, null=True)
    predicted_value = models.DecimalField('القيمة المتوقعة', max_digits=15, decimal_places=2, null=True)
    
    # الإجراءات الوقائية
    preventive_actions = models.JSONField('الإجراءات الوقائية', default=list)
    
    # الحالة
    is_active = models.BooleanField('نشط', default=True)
    is_dismissed = models.BooleanField('تم التجاهل', default=False)
    
    # التواريخ
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        db_table = 'proactive_warnings'
        verbose_name = 'تحذير استباقي'
        verbose_name_plural = 'التحذيرات الاستباقية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.get_warning_type_display()} - {self.title}'


# ========================
# Anomaly Detection Service
# ========================

class AnomalyDetectionService:
    """
    خدمة الكشف عن الشذوذات
    
    تكتشف الأنماط غير العادية في البيانات
    """
    
    def __init__(self):
        self.threshold_std_devs = 2.5  # عدد الانحرافات المعيارية للشذوذ
    
    # ============ Sales Anomalies ============
    
    def detect_sales_anomalies(self) -> List[AnomalyAlert]:
        """كشف شذوذات المبيعات"""
        from sales.models import Invoice
        
        alerts = []
        today = timezone.now().date()
        
        # 1. انخفاض مفاجئ في المبيعات
        alert = self._detect_sales_drop()
        if alert:
            alerts.append(alert)
        
        # 2. مبيعات غير عادية لمنتج معين
        alerts.extend(self._detect_unusual_product_sales())
        
        # 3. نمط غير عادي في التوقيت
        alert = self._detect_unusual_sales_timing()
        if alert:
            alerts.append(alert)
        
        # 4. تركز المبيعات على عميل واحد (مخاطرة)
        alert = self._detect_sales_concentration()
        if alert:
            alerts.append(alert)
        
        return alerts
    
    def _detect_sales_drop(self) -> Optional[AnomalyAlert]:
        """كشف انخفاض المبيعات"""
        from sales.models import Invoice
        
        today = timezone.now().date()
        
        # مبيعات آخر 7 أيام
        recent = Invoice.objects.filter(
            invoice_date__gte=today - timedelta(days=7)
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # متوسط مبيعات آخر 4 أسابيع
        weeks_ago = today - timedelta(days=28)
        historical = []
        for week in range(4):
            start = weeks_ago + timedelta(days=week * 7)
            end = start + timedelta(days=7)
            week_total = Invoice.objects.filter(
                invoice_date__range=[start, end]
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            historical.append(float(week_total))
        
        if not historical or len(historical) < 2:
            return None
        
        avg = statistics.mean(historical)
        std = statistics.stdev(historical)
        
        # إذا كانت المبيعات الأخيرة أقل بكثير
        if float(recent) < (avg - self.threshold_std_devs * std):
            deviation = ((avg - float(recent)) / avg * 100) if avg > 0 else 0
            
            return AnomalyAlert.objects.create(
                category='sales',
                severity='high',
                title='انخفاض حاد في المبيعات',
                description=f'انخفضت المبيعات بنسبة {deviation:.1f}% عن المتوسط',
                anomaly_type='sales_drop',
                detected_value=recent,
                expected_value=Decimal(str(avg)),
                deviation_percentage=Decimal(str(deviation)),
                recommended_actions=[
                    'مراجعة استراتيجية التسويق',
                    'التحقق من رضا العملاء',
                    'تحليل المنافسة',
                    'مراجعة الأسعار'
                ]
            )
        
        return None
    
    def _detect_unusual_product_sales(self) -> List[AnomalyAlert]:
        """كشف مبيعات غير عادية لمنتجات"""
        from sales.models import InvoiceItem
        from inventory.models import Product
        
        alerts = []
        today = timezone.now().date()
        
        # آخر 7 أيام مقابل 4 أسابيع سابقة
        recent_start = today - timedelta(days=7)
        historical_start = today - timedelta(days=35)
        historical_end = today - timedelta(days=7)
        
        products = Product.objects.filter(is_active=True)
        
        for product in products[:50]:  # فحص أول 50 منتج
            # مبيعات حديثة
            recent_qty = InvoiceItem.objects.filter(
                product=product,
                invoice__invoice_date__gte=recent_start
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            # مبيعات تاريخية
            historical_data = []
            for week in range(4):
                start = historical_start + timedelta(days=week * 7)
                end = start + timedelta(days=7)
                qty = InvoiceItem.objects.filter(
                    product=product,
                    invoice__invoice_date__range=[start, end]
                ).aggregate(total=Sum('quantity'))['total'] or 0
                historical_data.append(float(qty))
            
            if len(historical_data) < 2:
                continue
            
            avg = statistics.mean(historical_data)
            if avg == 0:
                continue
            
            std = statistics.stdev(historical_data) if len(historical_data) > 1 else 0
            
            # زيادة غير عادية
            if float(recent_qty) > (avg + self.threshold_std_devs * std):
                deviation = ((float(recent_qty) - avg) / avg * 100)
                
                alerts.append(AnomalyAlert.objects.create(
                    category='sales',
                    severity='medium',
                    title=f'زيادة غير عادية في مبيعات: {product.name}',
                    description=f'ارتفعت المبيعات بنسبة {deviation:.1f}% عن المتوسط',
                    anomaly_type='unusual_product_sales',
                    detected_value=Decimal(str(recent_qty)),
                    expected_value=Decimal(str(avg)),
                    deviation_percentage=Decimal(str(deviation)),
                    related_model='Product',
                    related_id=product.id,
                    recommended_actions=[
                        'التحقق من المخزون',
                        'مراجعة سبب الزيادة',
                        'تحديث خطة الإنتاج',
                        'التأكد من جودة المنتج'
                    ]
                ))
        
        return alerts
    
    def _detect_unusual_sales_timing(self) -> Optional[AnomalyAlert]:
        """كشف توقيت غير عادي للمبيعات"""
        from sales.models import Invoice
        
        # مبيعات في وقت غير معتاد (منتصف الليل مثلاً)
        today = timezone.now().date()
        unusual_hours = Invoice.objects.filter(
            created_at__date=today,
            created_at__hour__range=[0, 5]  # من 12 صباحاً إلى 5 صباحاً
        ).count()
        
        if unusual_hours > 5:  # أكثر من 5 فواتير في وقت غير معتاد
            return AnomalyAlert.objects.create(
                category='security',
                severity='medium',
                title='نشاط غير عادي في وقت متأخر',
                description=f'تم إنشاء {unusual_hours} فواتير بين منتصف الليل و5 صباحاً',
                anomaly_type='unusual_timing',
                detected_value=Decimal(str(unusual_hours)),
                recommended_actions=[
                    'مراجعة الفواتير المنشأة',
                    'التحقق من هوية المستخدمين',
                    'فحص نشاط تسجيل الدخول'
                ]
            )
        
        return None
    
    def _detect_sales_concentration(self) -> Optional[AnomalyAlert]:
        """كشف تركز المبيعات"""
        from sales.models import Invoice
        
        today = timezone.now().date()
        last_month = today - timedelta(days=30)
        
        # إجمالي المبيعات
        total_sales = Invoice.objects.filter(
            invoice_date__gte=last_month
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        if total_sales == 0:
            return None
        
        # أكبر عميل
        top_customer = Invoice.objects.filter(
            invoice_date__gte=last_month
        ).values('customer').annotate(
            total=Sum('total_amount')
        ).order_by('-total').first()
        
        if not top_customer:
            return None
        
        concentration = (top_customer['total'] / total_sales * 100)
        
        # إذا كان عميل واحد يمثل أكثر من 40% من المبيعات
        if concentration > 40:
            return AnomalyAlert.objects.create(
                category='financial',
                severity='high',
                title='تركز عالي في المبيعات',
                description=f'عميل واحد يمثل {concentration:.1f}% من المبيعات',
                anomaly_type='sales_concentration',
                detected_value=Decimal(str(concentration)),
                expected_value=Decimal('25'),
                deviation_percentage=Decimal(str(concentration - 25)),
                recommended_actions=[
                    'تنويع قاعدة العملاء',
                    'تطوير استراتيجية تسويق جديدة',
                    'تقليل الاعتماد على عميل واحد',
                    'تقييم مخاطر فقدان العميل'
                ]
            )
        
        return None
    
    # ============ Inventory Anomalies ============
    
    def detect_inventory_anomalies(self) -> List[AnomalyAlert]:
        """كشف شذوذات المخزون"""
        alerts = []
        
        # 1. تغيرات مخزون غير مبررة
        alerts.extend(self._detect_unexplained_stock_changes())
        
        # 2. معدل دوران غير طبيعي
        alerts.extend(self._detect_abnormal_turnover())
        
        # 3. فروقات جرد كبيرة
        alert = self._detect_large_count_differences()
        if alert:
            alerts.append(alert)
        
        return alerts
    
    def _detect_unexplained_stock_changes(self) -> List[AnomalyAlert]:
        """كشف تغيرات مخزون غير مبررة"""
        from inventory.models import StockMovement
        
        alerts = []
        today = timezone.now().date()
        
        # حركات تعديل كبيرة في آخر 7 أيام
        adjustments = StockMovement.objects.filter(
            movement_type='adjustment',
            created_at__date__gte=today - timedelta(days=7)
        ).values('product').annotate(
            total_qty=Sum('quantity')
        ).filter(total_qty__gte=100)  # تعديلات أكبر من 100 وحدة
        
        for adj in adjustments:
            alerts.append(AnomalyAlert.objects.create(
                category='inventory',
                severity='medium',
                title='تعديل مخزون كبير غير مبرر',
                description=f'تم تعديل {adj["total_qty"]} وحدة في آخر 7 أيام',
                anomaly_type='large_adjustment',
                detected_value=Decimal(str(adj['total_qty'])),
                related_model='Product',
                related_id=adj['product'],
                recommended_actions=[
                    'مراجعة سبب التعديل',
                    'التحقق من دقة الجرد',
                    'فحص الأذونات',
                    'تحسين نظام التتبع'
                ]
            ))
        
        return alerts
    
    def _detect_abnormal_turnover(self) -> List[AnomalyAlert]:
        """كشف معدل دوران غير طبيعي"""
        from inventory.models import Product, Stock
        from sales.models import InvoiceItem
        
        alerts = []
        today = timezone.now().date()
        last_month = today - timedelta(days=30)
        
        products = Product.objects.filter(is_active=True)
        
        for product in products[:50]:
            # المبيعات الشهرية
            monthly_sales = InvoiceItem.objects.filter(
                product=product,
                invoice__invoice_date__gte=last_month
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            # المخزون الحالي
            current_stock = Stock.objects.filter(
                product=product
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            if current_stock == 0:
                continue
            
            # معدل الدوران (شهري)
            turnover = float(monthly_sales) / float(current_stock) if current_stock > 0 else 0
            
            # دوران بطيء جداً (أقل من 0.1 = يحتاج 10 أشهر لبيع المخزون)
            if turnover < 0.1 and current_stock > 10:
                alerts.append(AnomalyAlert.objects.create(
                    category='inventory',
                    severity='medium',
                    title=f'دوران مخزون بطيء: {product.name}',
                    description=f'معدل الدوران {turnover:.2f} - يحتاج {1/turnover if turnover > 0 else 999:.0f} شهر لبيع المخزون',
                    anomaly_type='slow_turnover',
                    detected_value=Decimal(str(turnover)),
                    expected_value=Decimal('1.0'),
                    related_model='Product',
                    related_id=product.id,
                    recommended_actions=[
                        'تقليل كمية المخزون',
                        'عمل تخفيضات',
                        'مراجعة استراتيجية المنتج',
                        'إيقاف الشراء المؤقت'
                    ]
                ))
        
        return alerts
    
    def _detect_large_count_differences(self) -> Optional[AnomalyAlert]:
        """كشف فروقات جرد كبيرة"""
        # يمكن ربطه بنموذج PhysicalCount عند إنشائه
        # هنا مثال بسيط
        return None
    
    # ============ Production Anomalies ============
    
    def detect_production_anomalies(self) -> List[AnomalyAlert]:
        """كشف شذوذات الإنتاج"""
        alerts = []
        
        # 1. تأخيرات متكررة
        alert = self._detect_recurring_delays()
        if alert:
            alerts.append(alert)
        
        # 2. معدل عيوب مرتفع
        alerts.extend(self._detect_high_defect_rate())
        
        # 3. كفاءة منخفضة
        alert = self._detect_low_efficiency()
        if alert:
            alerts.append(alert)
        
        return alerts
    
    def _detect_recurring_delays(self) -> Optional[AnomalyAlert]:
        """كشف تأخيرات متكررة"""
        from production.models import ProductionOrder
        
        # أوامر متأخرة
        delayed = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress'],
            scheduled_end_date__lt=timezone.now().date()
        ).count()
        
        if delayed > 5:
            return AnomalyAlert.objects.create(
                category='production',
                severity='high',
                title='تأخيرات متكررة في الإنتاج',
                description=f'{delayed} أمر إنتاج متأخر عن الموعد',
                anomaly_type='recurring_delays',
                detected_value=Decimal(str(delayed)),
                expected_value=Decimal('0'),
                recommended_actions=[
                    'مراجعة سعة الإنتاج',
                    'تحسين التخطيط',
                    'فحص المعدات',
                    'زيادة الموارد'
                ]
            )
        
        return None
    
    def _detect_high_defect_rate(self) -> List[AnomalyAlert]:
        """كشف معدل عيوب مرتفع"""
        from production.models import ProductionOrder
        
        alerts = []
        today = timezone.now().date()
        last_week = today - timedelta(days=7)
        
        # الأوامر المكتملة حديثاً
        orders = ProductionOrder.objects.filter(
            status='completed',
            actual_end_date__gte=last_week
        )
        
        for order in orders:
            if order.quantity_produced == 0:
                continue
            
            # حساب معدل العيوب (افتراضاً أن هناك حقل defects)
            # defect_rate = (order.defects / order.quantity_produced) * 100
            # if defect_rate > 5:  # أكثر من 5%
            #     alerts.append(...)
            pass
        
        return alerts
    
    def _detect_low_efficiency(self) -> Optional[AnomalyAlert]:
        """كشف كفاءة منخفضة"""
        from production.models import ProductionOrder
        
        today = timezone.now().date()
        last_week = today - timedelta(days=7)
        
        # متوسط الكفاءة
        orders = ProductionOrder.objects.filter(
            status='completed',
            actual_end_date__gte=last_week,
            quantity__gt=0
        )
        
        if orders.count() == 0:
            return None
        
        efficiencies = []
        for order in orders:
            efficiency = (float(order.quantity_produced) / float(order.quantity)) * 100
            efficiencies.append(efficiency)
        
        avg_efficiency = statistics.mean(efficiencies)
        
        if avg_efficiency < 80:  # أقل من 80%
            return AnomalyAlert.objects.create(
                category='production',
                severity='high',
                title='كفاءة إنتاج منخفضة',
                description=f'متوسط الكفاءة {avg_efficiency:.1f}% في آخر أسبوع',
                anomaly_type='low_efficiency',
                detected_value=Decimal(str(avg_efficiency)),
                expected_value=Decimal('95'),
                deviation_percentage=Decimal(str(95 - avg_efficiency)),
                recommended_actions=[
                    'تدريب العمال',
                    'صيانة المعدات',
                    'مراجعة العمليات',
                    'تحسين بيئة العمل'
                ]
            )
        
        return None
    
    # ============ Financial Anomalies ============
    
    def detect_financial_anomalies(self) -> List[AnomalyAlert]:
        """كشف شذوذات مالية"""
        alerts = []
        
        # 1. نفقات غير عادية
        alert = self._detect_unusual_expenses()
        if alert:
            alerts.append(alert)
        
        # 2. تدفق نقدي سلبي
        alert = self._detect_negative_cash_flow()
        if alert:
            alerts.append(alert)
        
        return alerts
    
    def _detect_unusual_expenses(self) -> Optional[AnomalyAlert]:
        """كشف نفقات غير عادية"""
        from accounting.models import JournalEntryLine, Account
        
        today = timezone.now().date()
        
        # نفقات اليوم
        today_expenses = JournalEntryLine.objects.filter(
            journal_entry__date=today,
            account__account_type='expense',
            debit__gt=0
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
        
        # متوسط النفقات اليومية (آخر 30 يوم)
        days_ago_30 = today - timedelta(days=30)
        historical = []
        for i in range(30):
            day = days_ago_30 + timedelta(days=i)
            day_exp = JournalEntryLine.objects.filter(
                journal_entry__date=day,
                account__account_type='expense',
                debit__gt=0
            ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
            historical.append(float(day_exp))
        
        if len(historical) < 10:
            return None
        
        avg = statistics.mean(historical)
        std = statistics.stdev(historical)
        
        if float(today_expenses) > (avg + self.threshold_std_devs * std):
            deviation = ((float(today_expenses) - avg) / avg * 100) if avg > 0 else 0
            
            return AnomalyAlert.objects.create(
                category='financial',
                severity='high',
                title='نفقات غير عادية اليوم',
                description=f'النفقات أعلى بنسبة {deviation:.1f}% من المتوسط',
                anomaly_type='unusual_expenses',
                detected_value=today_expenses,
                expected_value=Decimal(str(avg)),
                deviation_percentage=Decimal(str(deviation)),
                recommended_actions=[
                    'مراجعة القيود اليومية',
                    'التحقق من الأذونات',
                    'فحص الفواتير',
                    'تحليل سبب الزيادة'
                ]
            )
        
        return None
    
    def _detect_negative_cash_flow(self) -> Optional[AnomalyAlert]:
        """كشف تدفق نقدي سلبي"""
        # يمكن تطويره حسب نموذج التدفق النقدي
        return None
    
    # ============ Master Detection ============
    
    def run_all_detections(self) -> Dict[str, List[AnomalyAlert]]:
        """تشغيل جميع عمليات الكشف"""
        results = {
            'sales': self.detect_sales_anomalies(),
            'inventory': self.detect_inventory_anomalies(),
            'production': self.detect_production_anomalies(),
            'financial': self.detect_financial_anomalies(),
        }
        
        return results


# Singleton instance
anomaly_detector = AnomalyDetectionService()


# ========================
# Proactive Warning Service
# ========================

class ProactiveWarningService:
    """
    خدمة التحذيرات الاستباقية
    
    تتنبأ بالمشاكل قبل حدوثها
    """
    
    def predict_stock_outs(self) -> List[ProactiveWarning]:
        """التنبؤ بنفاد المخزون"""
        from inventory.models import Product, Stock
        from sales.models import InvoiceItem
        
        warnings = []
        today = timezone.now().date()
        
        products = Product.objects.filter(is_active=True)
        
        for product in products[:100]:
            # المخزون الحالي
            current_stock = Stock.objects.filter(
                product=product
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            if current_stock == 0:
                continue
            
            # متوسط المبيعات اليومية (آخر 30 يوم)
            days_ago = today - timedelta(days=30)
            total_sold = InvoiceItem.objects.filter(
                product=product,
                invoice__invoice_date__gte=days_ago
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            daily_avg = float(total_sold) / 30
            
            if daily_avg == 0:
                continue
            
            # عدد الأيام حتى النفاد
            days_until_out = float(current_stock) / daily_avg
            
            # تحذير إذا كان أقل من 7 أيام
            if days_until_out < 7:
                predicted_date = today + timedelta(days=int(days_until_out))
                confidence = min(95, 60 + (7 - days_until_out) * 5)  # الثقة تزيد كلما اقترب
                
                warnings.append(ProactiveWarning.objects.create(
                    warning_type='stock_out',
                    title=f'نفاد مخزون متوقع: {product.name}',
                    description=f'المخزون سينفد في حوالي {int(days_until_out)} يوم',
                    predicted_date=predicted_date,
                    confidence_level=Decimal(str(confidence)),
                    current_value=Decimal(str(current_stock)),
                    threshold_value=Decimal(str(product.min_stock)),
                    predicted_value=Decimal('0'),
                    preventive_actions=[
                        f'طلب {int(daily_avg * 30)} وحدة',
                        'التواصل مع المورد فوراً',
                        'البحث عن موردين بديلين',
                        'التحقق من الإنتاج الداخلي'
                    ]
                ))
        
        return warnings
    
    def predict_capacity_overload(self) -> List[ProactiveWarning]:
        """التنبؤ بالحمل الزائد"""
        from production.models import ProductionOrder, ProductionWorkCenter
        
        warnings = []
        today = timezone.now().date()
        next_week = today + timedelta(days=7)
        
        work_centers = ProductionWorkCenter.objects.all()
        
        for wc in work_centers:
            # أوامر مجدولة في الأسبوع القادم
            scheduled = ProductionOrder.objects.filter(
                work_center=wc,
                status__in=['confirmed', 'in_progress'],
                scheduled_start_date__range=[today, next_week]
            )
            
            total_hours = sum([
                float(order.quantity) * float(order.product.production_time or 1)
                for order in scheduled
            ])
            
            # سعة مركز العمل (ساعات/أسبوع)
            capacity = wc.capacity_hours * 7 if hasattr(wc, 'capacity_hours') else 40 * 7
            
            # نسبة الاستخدام
            utilization = (total_hours / capacity * 100) if capacity > 0 else 0
            
            if utilization > 90:
                warnings.append(ProactiveWarning.objects.create(
                    warning_type='capacity_overload',
                    title=f'حمل زائد متوقع: {wc.name}',
                    description=f'الاستخدام المتوقع {utilization:.0f}% من السعة',
                    predicted_date=next_week,
                    confidence_level=Decimal('85'),
                    current_value=Decimal(str(total_hours)),
                    threshold_value=Decimal(str(capacity * 0.9)),
                    predicted_value=Decimal(str(total_hours)),
                    preventive_actions=[
                        'إعادة جدولة بعض الأوامر',
                        'العمل ساعات إضافية',
                        'نقل أوامر لمركز عمل آخر',
                        'تأجيل الأوامر غير العاجلة'
                    ]
                ))
        
        return warnings
    
    def predict_quality_issues(self) -> List[ProactiveWarning]:
        """التنبؤ بمشاكل الجودة"""
        from quality_control.models import QualityInspection
        
        warnings = []
        today = timezone.now().date()
        last_month = today - timedelta(days=30)
        
        # فحوصات آخر شهر
        inspections = QualityInspection.objects.filter(
            inspection_date__gte=last_month
        ).order_by('inspection_date')
        
        if inspections.count() < 10:
            return warnings
        
        # حساب الاتجاه في نسبة الرفض
        rejection_rates = []
        for inspection in inspections:
            if inspection.quantity_inspected > 0:
                rate = (inspection.quantity_rejected / inspection.quantity_inspected) * 100
                rejection_rates.append(rate)
        
        if len(rejection_rates) < 5:
            return warnings
        
        # إذا كان الاتجاه تصاعدي (آخر 5 معدلات أعلى من أول 5)
        first_half = statistics.mean(rejection_rates[:len(rejection_rates)//2])
        second_half = statistics.mean(rejection_rates[len(rejection_rates)//2:])
        
        if second_half > first_half * 1.5:  # زيادة بنسبة 50%
            warnings.append(ProactiveWarning.objects.create(
                warning_type='quality_trend',
                title='اتجاه تصاعدي في معدل الرفض',
                description=f'معدل الرفض ارتفع من {first_half:.1f}% إلى {second_half:.1f}%',
                predicted_date=today + timedelta(days=7),
                confidence_level=Decimal('75'),
                current_value=Decimal(str(second_half)),
                threshold_value=Decimal('5'),
                predicted_value=Decimal(str(second_half * 1.2)),
                preventive_actions=[
                    'فحص المعدات فوراً',
                    'مراجعة المواد الخام',
                    'تدريب العمال',
                    'تشديد الرقابة'
                ]
            ))
        
        return warnings
    
    def run_all_predictions(self) -> Dict[str, List[ProactiveWarning]]:
        """تشغيل جميع التنبؤات"""
        results = {
            'stock_outs': self.predict_stock_outs(),
            'capacity': self.predict_capacity_overload(),
            'quality': self.predict_quality_issues(),
        }
        
        return results


# Singleton instance
proactive_warner = ProactiveWarningService()
