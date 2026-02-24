"""
نظام الإشعارات الذكي المحسّن
Smart Notifications Enhancement
"""
from notifications.models import Notification
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta


class SmartNotificationManager:
    """مدير الإشعارات الذكي"""
    
    @staticmethod
    def create_smart_notification(user, title, message, notification_type='info', 
                                   priority='normal', action_url=None, 
                                   auto_dismiss_hours=None, tags=None):
        """
        إنشاء إشعار ذكي
        
        Args:
            user: المستخدم المستهدف
            title: عنوان الإشعار
            message: نص الإشعار
            notification_type: نوع الإشعار (info, success, warning, error, urgent)
            priority: الأولوية (low, normal, high, urgent)
            action_url: رابط الإجراء المطلوب
            auto_dismiss_hours: عدد الساعات للإخفاء التلقائي
            tags: وسوم للتصنيف
        """
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            level=notification_type if notification_type in ['info', 'success', 'warning', 'error'] else 'info',
            is_read=False
        )
        
        # إضافة بيانات إضافية
        extra_data = {
            'priority': priority,
            'tags': tags or [],
            'created_by_system': 'smart_notification',
        }
        
        if auto_dismiss_hours:
            extra_data['auto_dismiss_at'] = (
                timezone.now() + timedelta(hours=auto_dismiss_hours)
            ).isoformat()
        
        # يمكن حفظ extra_data في حقل JSON إذا كان موجود
        
        return notification
    
    @staticmethod
    def notify_low_stock_products(threshold=10):
        """إشعار بالمنتجات منخفضة المخزون"""
        from inventory.models import Stock
        from django.contrib.auth.models import Permission
        
        # المنتجات منخفضة المخزون
        low_stock = Stock.objects.filter(
            quantity__lte=threshold
        ).select_related('product', 'location')
        
        if not low_stock.exists():
            return
        
        # المستخدمون الذين لديهم صلاحية عرض المخزون
        users_with_perm = User.objects.filter(
            Q(is_superuser=True) |
            Q(user_permissions__codename='view_stock') |
            Q(groups__permissions__codename='view_stock')
        ).distinct()
        
        message = f"⚠️ يوجد {low_stock.count()} منتج منخفض المخزون يحتاج لإعادة طلب"
        
        for user in users_with_perm:
            SmartNotificationManager.create_smart_notification(
                user=user,
                title='تنبيه: مخزون منخفض',
                message=message,
                notification_type='warning',
                priority='high',
                action_url='/inventory/reports/low-stock/',
                auto_dismiss_hours=24,
                tags=['inventory', 'stock', 'alert']
            )
    
    @staticmethod
    def notify_pending_approvals(user):
        """إشعار بالموافقات المعلقة"""
        try:
            from approvals.models import ApprovalRequest
            
            pending = ApprovalRequest.objects.filter(
                approver=user,
                status='pending'
            ).count()
            
            if pending > 0:
                SmartNotificationManager.create_smart_notification(
                    user=user,
                    title='موافقات معلقة',
                    message=f'لديك {pending} طلب موافقة في انتظار اتخاذ قرار',
                    notification_type='info',
                    priority='normal',
                    action_url='/approvals/',
                    tags=['approvals', 'pending']
                )
        except:
            pass
    
    @staticmethod
    def notify_overdue_invoices():
        """إشعار بالفواتير المتأخرة"""
        from sales.models import Invoice
        from django.contrib.auth.models import Permission
        
        # الفواتير المتأخرة
        overdue = Invoice.objects.filter(
            payment_status='partial',
            due_date__lt=timezone.now().date()
        )
        
        if not overdue.exists():
            return
        
        # المستخدمون المعنيون
        users = User.objects.filter(
            Q(is_superuser=True) |
            Q(user_permissions__codename='view_invoice') |
            Q(groups__permissions__codename='view_invoice')
        ).distinct()
        
        total_amount = sum([inv.remaining_amount for inv in overdue])
        
        for user in users:
            SmartNotificationManager.create_smart_notification(
                user=user,
                title='⏰ فواتير متأخرة السداد',
                message=f'يوجد {overdue.count()} فاتورة متأخرة بإجمالي {total_amount:.2f}',
                notification_type='urgent',
                priority='high',
                action_url='/sales/invoices/?status=overdue',
                tags=['sales', 'invoices', 'overdue', 'urgent']
            )
    
    @staticmethod
    def notify_birthday_today():
        """إشعار بأعياد ميلاد الموظفين اليوم"""
        try:
            from hr.models import Employee
            
            today = timezone.now().date()
            birthdays = Employee.objects.filter(
                date_of_birth__month=today.month,
                date_of_birth__day=today.day
            )
            
            if birthdays.exists():
                # إشعار لإدارة الموارد البشرية
                hr_users = User.objects.filter(
                    Q(is_superuser=True) |
                    Q(groups__name__icontains='hr') |
                    Q(groups__name__icontains='موارد')
                ).distinct()
                
                for user in hr_users:
                    for emp in birthdays:
                        SmartNotificationManager.create_smart_notification(
                            user=user,
                            title='🎂 عيد ميلاد سعيد!',
                            message=f'اليوم عيد ميلاد {emp.user.get_full_name()}',
                            notification_type='success',
                            priority='low',
                            action_url=f'/hr/employees/{emp.id}/',
                            auto_dismiss_hours=24,
                            tags=['hr', 'birthday', 'celebration']
                        )
        except:
            pass
    
    @staticmethod
    def notify_scheduled_report_ready(user, report_name, report_url):
        """إشعار باكتمال تقرير مجدول"""
        SmartNotificationManager.create_smart_notification(
            user=user,
            title='📊 تقرير جاهز',
            message=f'تم إنشاء تقرير "{report_name}" بنجاح',
            notification_type='success',
            priority='normal',
            action_url=report_url,
            auto_dismiss_hours=48,
            tags=['reports', 'scheduled', 'ready']
        )
    
    @staticmethod
    def batch_notify_users(users, title, message, **kwargs):
        """إرسال إشعار جماعي لمجموعة مستخدمين"""
        notifications = []
        for user in users:
            notif = SmartNotificationManager.create_smart_notification(
                user=user,
                title=title,
                message=message,
                **kwargs
            )
            notifications.append(notif)
        
        return notifications


class NotificationScheduler:
    """جدولة الإشعارات التلقائية"""
    
    @staticmethod
    def run_daily_notifications():
        """تشغيل الإشعارات اليومية"""
        SmartNotificationManager.notify_low_stock_products()
        SmartNotificationManager.notify_overdue_invoices()
        SmartNotificationManager.notify_birthday_today()
    
    @staticmethod
    def run_hourly_notifications():
        """تشغيل الإشعارات الساعية"""
        # إشعارات الموافقات المعلقة
        users = User.objects.filter(is_active=True)
        for user in users:
            SmartNotificationManager.notify_pending_approvals(user)
