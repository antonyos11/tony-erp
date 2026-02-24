"""
نظام تتبع اتفاقيات مستوى الخدمة للمشتريات
SLA Tracking System for Purchasing
"""

from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class PurchaseSLA(models.Model):
    """اتفاقية مستوى الخدمة للمشتريات"""
    
    SLA_TYPES = [
        ('order_approval', 'الموافقة على الطلب'),
        ('delivery', 'التسليم'),
        ('payment', 'الدفع'),
        ('quality_check', 'فحص الجودة'),
    ]
    
    STATUS_CHOICES = [
        ('on_time', 'في الوقت المحدد'),
        ('at_risk', 'معرض للتأخير'),
        ('delayed', 'متأخر'),
        ('completed', 'مكتمل'),
    ]
    
    purchase_order = models.ForeignKey('purchasing.PurchaseOrder', on_delete=models.CASCADE, related_name='slas')
    sla_type = models.CharField(max_length=20, choices=SLA_TYPES, verbose_name='نوع الاتفاقية')
    expected_completion_date = models.DateTimeField(verbose_name='تاريخ الإنجاز المتوقع')
    actual_completion_date = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الإنجاز الفعلي')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='on_time', verbose_name='الحالة')
    delay_hours = models.IntegerField(default=0, verbose_name='ساعات التأخير')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'اتفاقية مستوى الخدمة'
        verbose_name_plural = 'اتفاقيات مستوى الخدمة'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_sla_type_display()} - {self.purchase_order.order_number}"
    
    def update_status(self):
        """تحديث الحالة بناءً على الوقت"""
        now = timezone.now()
        
        if self.actual_completion_date:
            # تم الإنجاز
            self.status = 'completed'
            delay = (self.actual_completion_date - self.expected_completion_date).total_seconds() / 3600
            self.delay_hours = max(0, int(delay))
        else:
            # لم يتم الإنجاز بعد
            time_remaining = (self.expected_completion_date - now).total_seconds() / 3600
            
            if time_remaining < 0:
                # متأخر
                self.status = 'delayed'
                self.delay_hours = int(abs(time_remaining))
            elif time_remaining < 24:
                # معرض للتأخير (أقل من 24 ساعة متبقية)
                self.status = 'at_risk'
            else:
                # في الوقت المحدد
                self.status = 'on_time'
        
        self.save()
        return self.status
    
    def mark_completed(self, completion_date=None):
        """تعليم كمكتمل"""
        self.actual_completion_date = completion_date or timezone.now()
        self.update_status()
    
    def get_status_color(self):
        """الحصول على لون الحالة"""
        colors = {
            'on_time': 'success',
            'at_risk': 'warning',
            'delayed': 'danger',
            'completed': 'info'
        }
        return colors.get(self.status, 'secondary')
    
    def get_progress_percentage(self):
        """حساب نسبة التقدم"""
        if self.actual_completion_date:
            return 100
        
        now = timezone.now()
        total_duration = (self.expected_completion_date - self.created_at).total_seconds()
        elapsed = (now - self.created_at).total_seconds()
        
        if total_duration <= 0:
            return 100
        
        progress = (elapsed / total_duration) * 100
        return min(100, max(0, progress))


class SLATracker:
    """متتبع اتفاقيات مستوى الخدمة"""
    
    # مدد SLA الافتراضية بالساعات
    DEFAULT_DURATIONS = {
        'order_approval': 24,  # 24 ساعة للموافقة
        'delivery': 72,  # 3 أيام للتسليم
        'payment': 48,  # يومين للدفع
        'quality_check': 12,  # 12 ساعة لفحص الجودة
    }
    
    @classmethod
    def create_slas_for_order(cls, purchase_order):
        """إنشاء SLAs لطلب شراء جديد"""
        from purchasing.models import PurchaseOrder
        
        slas_created = []
        
        # SLA للموافقة
        if purchase_order.status == 'pending':
            approval_sla = PurchaseSLA.objects.create(
                purchase_order=purchase_order,
                sla_type='order_approval',
                expected_completion_date=timezone.now() + timedelta(hours=cls.DEFAULT_DURATIONS['order_approval'])
            )
            slas_created.append(approval_sla)
        
        # SLA للتسليم
        if purchase_order.expected_delivery_date:
            delivery_sla = PurchaseSLA.objects.create(
                purchase_order=purchase_order,
                sla_type='delivery',
                expected_completion_date=purchase_order.expected_delivery_date
            )
            slas_created.append(delivery_sla)
        
        return slas_created
    
    @classmethod
    def update_sla_on_approval(cls, purchase_order):
        """تحديث SLA عند الموافقة على الطلب"""
        approval_sla = PurchaseSLA.objects.filter(
            purchase_order=purchase_order,
            sla_type='order_approval',
            actual_completion_date__isnull=True
        ).first()
        
        if approval_sla:
            approval_sla.mark_completed()
        
        # إنشاء SLA لفحص الجودة إذا كان مطلوباً
        if purchase_order.requires_quality_check:
            quality_sla = PurchaseSLA.objects.create(
                purchase_order=purchase_order,
                sla_type='quality_check',
                expected_completion_date=timezone.now() + timedelta(hours=cls.DEFAULT_DURATIONS['quality_check'])
            )
    
    @classmethod
    def update_sla_on_delivery(cls, purchase_order):
        """تحديث SLA عند التسليم"""
        delivery_sla = PurchaseSLA.objects.filter(
            purchase_order=purchase_order,
            sla_type='delivery',
            actual_completion_date__isnull=True
        ).first()
        
        if delivery_sla:
            delivery_sla.mark_completed()
        
        # إنشاء SLA للدفع
        payment_sla = PurchaseSLA.objects.create(
            purchase_order=purchase_order,
            sla_type='payment',
            expected_completion_date=timezone.now() + timedelta(hours=cls.DEFAULT_DURATIONS['payment'])
        )
    
    @classmethod
    def get_delayed_orders(cls):
        """الحصول على الطلبات المتأخرة"""
        delayed_slas = PurchaseSLA.objects.filter(
            status='delayed',
            actual_completion_date__isnull=True
        ).select_related('purchase_order')
        
        return delayed_slas
    
    @classmethod
    def get_at_risk_orders(cls):
        """الحصول على الطلبات المعرضة للتأخير"""
        at_risk_slas = PurchaseSLA.objects.filter(
            status='at_risk',
            actual_completion_date__isnull=True
        ).select_related('purchase_order')
        
        return at_risk_slas
    
    @classmethod
    def get_sla_statistics(cls, start_date=None, end_date=None):
        """إحصائيات SLA"""
        from django.db.models import Count, Avg, Q
        
        slas = PurchaseSLA.objects.all()
        
        if start_date:
            slas = slas.filter(created_at__gte=start_date)
        if end_date:
            slas = slas.filter(created_at__lte=end_date)
        
        stats = {
            'total': slas.count(),
            'completed': slas.filter(status='completed').count(),
            'on_time': slas.filter(status='on_time').count(),
            'at_risk': slas.filter(status='at_risk').count(),
            'delayed': slas.filter(status='delayed').count(),
            'avg_delay_hours': slas.filter(delay_hours__gt=0).aggregate(avg=Avg('delay_hours'))['avg'] or 0,
        }
        
        # نسبة الإنجاز في الوقت المحدد
        if stats['completed'] > 0:
            on_time_completed = slas.filter(
                status='completed',
                delay_hours=0
            ).count()
            stats['on_time_percentage'] = (on_time_completed / stats['completed']) * 100
        else:
            stats['on_time_percentage'] = 0
        
        # إحصائيات حسب النوع
        stats['by_type'] = slas.values('sla_type').annotate(
            total=Count('id'),
            delayed=Count('id', filter=Q(status='delayed')),
            avg_delay=Avg('delay_hours')
        )
        
        return stats
    
    @classmethod
    def send_sla_alerts(cls):
        """إرسال تنبيهات SLA"""
        from notifications.enhanced_service import NotificationService
        
        # التنبيه بالطلبات المتأخرة
        delayed = cls.get_delayed_orders()
        for sla in delayed:
            NotificationService.send_notification(
                user=sla.purchase_order.created_by,
                title='تأخير في طلب الشراء',
                message=f'الطلب {sla.purchase_order.order_number} متأخر {sla.delay_hours} ساعة',
                notification_type='warning',
                link=f'/purchasing/orders/{sla.purchase_order.id}/'
            )
        
        # التنبيه بالطلبات المعرضة للتأخير
        at_risk = cls.get_at_risk_orders()
        for sla in at_risk:
            time_remaining = (sla.expected_completion_date - timezone.now()).total_seconds() / 3600
            NotificationService.send_notification(
                user=sla.purchase_order.created_by,
                title='تحذير: طلب شراء معرض للتأخير',
                message=f'الطلب {sla.purchase_order.order_number} يجب إنجازه خلال {int(time_remaining)} ساعة',
                notification_type='info',
                link=f'/purchasing/orders/{sla.purchase_order.id}/'
            )


# ===== Celery Tasks =====
import logging
logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    
    @shared_task(name='purchasing.sla_tracker.send_sla_alerts')
    def send_sla_alerts():
        """مهمة Celery لإرسال تنبيهات SLA"""
        try:
            SLATracker.send_sla_alerts()
            
            # تحديث حالات جميع SLAs
            from purchasing.models import PurchaseOrder
            slas = PurchaseSLA.objects.filter(actual_completion_date__isnull=True)
            updated_count = 0
            
            for sla in slas:
                old_status = sla.status
                sla.update_status()
                if sla.status != old_status:
                    updated_count += 1
            
            stats = SLATracker.get_sla_statistics()
            logger.info(f"تم تحديث {updated_count} SLA. الإحصائيات: {stats}")
            
            return {'status': 'success', 'updated': updated_count, 'stats': stats}
            
        except Exception as e:
            logger.error(f"خطأ في تحديث SLA: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
except ImportError:
    pass

