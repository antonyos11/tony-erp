"""
نظام تنبيهات المخزون الملونة
Stock Alert Color System
"""

from django.db.models import F, Q, Case, When, CharField


class StockAlertSystem:
    """نظام تنبيهات المخزون مع الألوان"""
    
    # ألوان التنبيهات
    COLORS = {
        'critical': {
            'bg': '#fee2e2',      # أحمر فاتح
            'text': '#991b1b',    # أحمر غامق
            'border': '#dc2626',  # أحمر
            'icon': 'fas fa-exclamation-triangle',
            'label': 'نفذ'
        },
        'low': {
            'bg': '#fed7aa',      # برتقالي فاتح
            'text': '#9a3412',    # برتقالي غامق
            'border': '#ea580c',  # برتقالي
            'icon': 'fas fa-exclamation-circle',
            'label': 'منخفض جداً'
        },
        'warning': {
            'bg': '#fef3c7',      # أصفر فاتح
            'text': '#92400e',    # أصفر غامق
            'border': '#f59e0b',  # أصفر
            'icon': 'fas fa-info-circle',
            'label': 'تحذير'
        },
        'ok': {
            'bg': '#d1fae5',      # أخضر فاتح
            'text': '#065f46',    # أخضر غامق
            'border': '#10b981',  # أخضر
            'icon': 'fas fa-check-circle',
            'label': 'جيد'
        },
        'excess': {
            'bg': '#dbeafe',      # أزرق فاتح
            'text': '#1e40af',    # أزرق غامق
            'border': '#3b82f6',  # أزرق
            'icon': 'fas fa-arrow-up',
            'label': 'زائد'
        }
    }
    
    @staticmethod
    def get_stock_status(product):
        """
        الحصول على حالة المخزون للمنتج
        
        Args:
            product: كائن المنتج
        
        Returns:
            str: حالة المخزون (critical, low, warning, ok, excess)
        """
        if product.stock_quantity == 0:
            return 'critical'
        elif product.stock_quantity <= product.min_stock_level * 0.5:
            return 'low'
        elif product.stock_quantity <= product.min_stock_level:
            return 'warning'
        elif product.stock_quantity > product.min_stock_level * 3:
            return 'excess'
        return 'ok'
    
    @staticmethod
    def get_status_info(status):
        """الحصول على معلومات الحالة بما في ذلك الألوان"""
        return StockAlertSystem.COLORS.get(status, StockAlertSystem.COLORS['ok'])
    
    @staticmethod
    def get_product_with_status(product):
        """الحصول على المنتج مع معلومات الحالة"""
        status = StockAlertSystem.get_stock_status(product)
        status_info = StockAlertSystem.get_status_info(status)
        
        return {
            'product': product,
            'status': status,
            'status_info': status_info,
            'percentage': (product.stock_quantity / product.min_stock_level * 100) if product.min_stock_level > 0 else 0
        }
    
    @staticmethod
    def get_alert_summary():
        """
        الحصول على ملخص التنبيهات
        
        Returns:
            dict مع عدد المنتجات في كل حالة
        """
        from inventory.models import Product
        
        # استعلام محسّن للحصول على الأعداد
        products = Product.objects.filter(is_active=True)
        
        summary = {
            'critical': products.filter(stock_quantity=0).count(),
            'low': products.filter(
                stock_quantity__gt=0,
                stock_quantity__lte=F('min_stock_level') * 0.5
            ).count(),
            'warning': products.filter(
                stock_quantity__gt=F('min_stock_level') * 0.5,
                stock_quantity__lte=F('min_stock_level')
            ).count(),
            'ok': products.filter(
                stock_quantity__gt=F('min_stock_level'),
                stock_quantity__lte=F('min_stock_level') * 3
            ).count(),
            'excess': products.filter(
                stock_quantity__gt=F('min_stock_level') * 3
            ).count()
        }
        
        summary['total'] = sum(summary.values())
        
        return summary
    
    @staticmethod
    def get_daily_report():
        """
        تقرير يومي عن المنتجات التي تحتاج انتباه
        
        Returns:
            dict مع قوائم المنتجات حسب الحالة
        """
        from inventory.models import Product
        
        report = {
            'critical': [],
            'low': [],
            'warning': []
        }
        
        products = Product.objects.filter(
            is_active=True
        ).select_related('category')
        
        for product in products:
            status = StockAlertSystem.get_stock_status(product)
            if status in ['critical', 'low', 'warning']:
                report[status].append({
                    'product': product,
                    'status': status,
                    'status_info': StockAlertSystem.get_status_info(status),
                    'quantity': product.stock_quantity,
                    'min_level': product.min_stock_level,
                    'deficit': product.min_stock_level - product.stock_quantity
                })
        
        return report
    
    @staticmethod
    def send_daily_alert_email():
        """إرسال بريد إلكتروني يومي بالتنبيهات"""
        from django.core.mail import send_mail
        from django.conf import settings
        from core.models import User
        
        report = StockAlertSystem.get_daily_report()
        
        # التحقق من وجود تنبيهات
        total_alerts = sum(len(report[key]) for key in ['critical', 'low', 'warning'])
        
        if total_alerts == 0:
            return
        
        # إنشاء محتوى البريد
        message = f"""
        تقرير المخزون اليومي
        
        المنتجات النافذة: {len(report['critical'])}
        المنتجات المنخفضة جداً: {len(report['low'])}
        المنتجات التحذيرية: {len(report['warning'])}
        
        الإجمالي: {total_alerts} منتج يحتاج انتباه
        """
        
        # إرسال إلى مدراء المخزون
        managers = User.objects.filter(
            role__in=['INVENTORY_MANAGER', 'SUPER_ADMIN'],
            is_active=True,
            email__isnull=False
        )
        
        for manager in managers:
            send_mail(
                subject='تقرير المخزون اليومي',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[manager.email],
                fail_silently=True
            )


def annotate_products_with_status(queryset):
    """
    إضافة حالة المخزون إلى استعلام المنتجات
    
    Args:
        queryset: QuerySet للمنتجات
    
    Returns:
        QuerySet مع حقل status_label
    """
    return queryset.annotate(
        status_label=Case(
            When(stock_quantity=0, then='critical'),
            When(stock_quantity__lte=F('min_stock_level') * 0.5, then='low'),
            When(stock_quantity__lte=F('min_stock_level'), then='warning'),
            When(stock_quantity__gt=F('min_stock_level') * 3, then='excess'),
            default='ok',
            output_field=CharField()
        )
    )


# ===== Celery Tasks =====
import logging
logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    
    @shared_task(name='inventory.stock_alerts.send_stock_alerts')
    def send_stock_alerts():
        """مهمة Celery لإرسال تنبيهات المخزون"""
        try:
            StockAlertSystem.send_daily_alert_email()
            summary = StockAlertSystem.get_alert_summary()
            
            logger.info(f"تم إرسال تنبيهات المخزون: {summary}")
            return {'status': 'success', 'summary': summary}
            
        except Exception as e:
            logger.error(f"خطأ في إرسال تنبيهات المخزون: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
except ImportError:
    pass
