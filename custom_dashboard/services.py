"""
خدمات لوحة التحكم المخصصة
Custom Dashboard Services
"""

from django.utils import timezone
from datetime import timedelta
from .models import Widget, DashboardLayout, DashboardWidget, WidgetData


class WidgetDataService:
    """خدمة بيانات الويدجتس"""
    
    @staticmethod
    def get_widget_data(widget, user=None):
        """الحصول على بيانات الويدجت"""
        # التحقق من الكاش
        cached = WidgetData.objects.filter(
            widget=widget,
            user=user,
            expires_at__gt=timezone.now()
        ).first()
        
        if cached:
            return cached.data
        
        # جلب البيانات الجديدة
        data = WidgetDataService._fetch_widget_data(widget, user)
        
        # حفظ في الكاش
        WidgetData.objects.update_or_create(
            widget=widget,
            user=user,
            defaults={
                'data': data,
                'expires_at': timezone.now() + timedelta(seconds=widget.refresh_interval)
            }
        )
        
        return data
    
    @staticmethod
    def _fetch_widget_data(widget, user):
        """جلب بيانات الويدجت"""
        data_source = widget.data_source
        
        if not data_source:
            return {}
        
        # معالجة مصادر البيانات المختلفة
        if data_source == 'sales_summary':
            return WidgetDataService._get_sales_summary()
        
        elif data_source == 'inventory_summary':
            return WidgetDataService._get_inventory_summary()
        
        elif data_source == 'recent_invoices':
            return WidgetDataService._get_recent_invoices()
        
        elif data_source == 'low_stock_items':
            return WidgetDataService._get_low_stock_items()
        
        elif data_source == 'pending_approvals':
            return WidgetDataService._get_pending_approvals(user)
        
        elif data_source == 'sales_chart':
            return WidgetDataService._get_sales_chart()
        
        elif data_source == 'top_customers':
            return WidgetDataService._get_top_customers()
        
        elif data_source == 'top_products':
            return WidgetDataService._get_top_products()
        
        elif data_source == 'calendar_events':
            return WidgetDataService._get_calendar_events(user)
        
        elif data_source == 'tasks':
            return WidgetDataService._get_tasks(user)
        
        return {}
    
    @staticmethod
    def _get_sales_summary():
        """ملخص المبيعات"""
        try:
            from sales.models import Invoice
            from django.db.models import Sum, Count
            from datetime import date, timedelta
            
            today = date.today()
            
            # مبيعات اليوم
            today_sales = Invoice.objects.filter(
                date__date=today
            ).aggregate(
                total=Sum('total'),
                count=Count('id')
            )
            
            # مبيعات الأمس
            yesterday = today - timedelta(days=1)
            yesterday_sales = Invoice.objects.filter(
                date__date=yesterday
            ).aggregate(total=Sum('total'))['total'] or 0
            
            # النسبة المئوية للتغيير
            today_total = today_sales['total'] or 0
            if yesterday_sales > 0:
                change = ((today_total - yesterday_sales) / yesterday_sales) * 100
            else:
                change = 100 if today_total > 0 else 0
            
            return {
                'today_total': float(today_total),
                'today_count': today_sales['count'] or 0,
                'yesterday_total': float(yesterday_sales),
                'change_percent': round(change, 1)
            }
        except:
            return {'today_total': 0, 'today_count': 0, 'yesterday_total': 0, 'change_percent': 0}
    
    @staticmethod
    def _get_inventory_summary():
        """ملخص المخزون"""
        try:
            from inventory.models import Product
            from django.db.models import Sum, Count, F
            
            total_products = Product.objects.count()
            total_value = Product.objects.aggregate(
                value=Sum(F('quantity') * F('cost_price'))
            )['value'] or 0
            
            low_stock = Product.objects.filter(
                quantity__lte=F('min_quantity')
            ).count()
            
            out_of_stock = Product.objects.filter(quantity=0).count()
            
            return {
                'total_products': total_products,
                'total_value': float(total_value),
                'low_stock': low_stock,
                'out_of_stock': out_of_stock
            }
        except:
            return {'total_products': 0, 'total_value': 0, 'low_stock': 0, 'out_of_stock': 0}
    
    @staticmethod
    def _get_recent_invoices():
        """آخر الفواتير"""
        try:
            from sales.models import Invoice
            
            invoices = Invoice.objects.select_related('customer').order_by('-date')[:10]
            
            return {
                'invoices': [
                    {
                        'id': inv.id,
                        'number': inv.invoice_number,
                        'customer': str(inv.customer) if inv.customer else 'غير محدد',
                        'total': float(inv.total),
                        'date': inv.date.strftime('%Y-%m-%d %H:%M'),
                        'status': inv.status
                    }
                    for inv in invoices
                ]
            }
        except:
            return {'invoices': []}
    
    @staticmethod
    def _get_low_stock_items():
        """المنتجات منخفضة المخزون"""
        try:
            from inventory.models import Product
            from django.db.models import F
            
            products = Product.objects.filter(
                quantity__lte=F('min_quantity')
            ).order_by('quantity')[:10]
            
            return {
                'items': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'quantity': p.quantity,
                        'min_quantity': p.min_quantity,
                        'unit': p.unit
                    }
                    for p in products
                ]
            }
        except:
            return {'items': []}
    
    @staticmethod
    def _get_pending_approvals(user):
        """الموافقات المعلقة"""
        try:
            from approvals.models import ApprovalRequest
            
            approvals = ApprovalRequest.objects.filter(
                status='pending',
                approvers=user
            ).order_by('-created_at')[:10]
            
            return {
                'count': approvals.count(),
                'approvals': [
                    {
                        'id': a.id,
                        'title': a.title,
                        'type': a.request_type,
                        'requester': str(a.requester),
                        'date': a.created_at.strftime('%Y-%m-%d')
                    }
                    for a in approvals
                ]
            }
        except:
            return {'count': 0, 'approvals': []}
    
    @staticmethod
    def _get_sales_chart():
        """بيانات رسم المبيعات"""
        try:
            from sales.models import Invoice
            from django.db.models import Sum
            from django.db.models.functions import TruncDate
            from datetime import date, timedelta
            
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            sales_by_day = Invoice.objects.filter(
                date__date__gte=start_date,
                date__date__lte=end_date
            ).annotate(
                day=TruncDate('date')
            ).values('day').annotate(
                total=Sum('total')
            ).order_by('day')
            
            return {
                'labels': [s['day'].strftime('%m/%d') for s in sales_by_day],
                'data': [float(s['total']) for s in sales_by_day]
            }
        except:
            return {'labels': [], 'data': []}
    
    @staticmethod
    def _get_top_customers():
        """أفضل العملاء"""
        try:
            from crm.models import Customer
            from django.db.models import Sum
            
            customers = Customer.objects.annotate(
                total_purchases=Sum('invoices__total')
            ).order_by('-total_purchases')[:5]
            
            return {
                'customers': [
                    {
                        'id': c.id,
                        'name': c.name,
                        'total': float(c.total_purchases or 0)
                    }
                    for c in customers
                ]
            }
        except:
            return {'customers': []}
    
    @staticmethod
    def _get_top_products():
        """أفضل المنتجات"""
        try:
            from inventory.models import Product
            from django.db.models import Sum
            
            products = Product.objects.annotate(
                total_sold=Sum('invoice_items__quantity')
            ).order_by('-total_sold')[:5]
            
            return {
                'products': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'sold': p.total_sold or 0
                    }
                    for p in products
                ]
            }
        except:
            return {'products': []}
    
    @staticmethod
    def _get_calendar_events(user):
        """أحداث التقويم"""
        try:
            from datetime import date, timedelta
            
            today = date.today()
            end_date = today + timedelta(days=7)
            
            events = []
            
            # محاولة جلب المواعيد
            try:
                from crm.models import Appointment
                appointments = Appointment.objects.filter(
                    date__gte=today,
                    date__lte=end_date,
                    user=user
                )
                for a in appointments:
                    events.append({
                        'title': a.title,
                        'date': a.date.strftime('%Y-%m-%d'),
                        'type': 'appointment'
                    })
            except:
                pass
            
            # محاولة جلب المهام
            try:
                from tasks.models import Task
                tasks = Task.objects.filter(
                    due_date__gte=today,
                    due_date__lte=end_date,
                    assigned_to=user
                )
                for t in tasks:
                    events.append({
                        'title': t.title,
                        'date': t.due_date.strftime('%Y-%m-%d'),
                        'type': 'task'
                    })
            except:
                pass
            
            return {'events': events[:10]}
        except:
            return {'events': []}
    
    @staticmethod
    def _get_tasks(user):
        """مهام المستخدم"""
        try:
            from tasks.models import Task
            
            tasks = Task.objects.filter(
                assigned_to=user,
                status__in=['pending', 'in_progress']
            ).order_by('due_date')[:10]
            
            return {
                'tasks': [
                    {
                        'id': t.id,
                        'title': t.title,
                        'status': t.status,
                        'priority': t.priority,
                        'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else None
                    }
                    for t in tasks
                ]
            }
        except:
            return {'tasks': []}


class DashboardService:
    """خدمة لوحة التحكم"""
    
    @staticmethod
    def get_user_dashboard(user):
        """الحصول على لوحة تحكم المستخدم"""
        layout = DashboardLayout.objects.filter(
            user=user,
            is_default=True,
            is_active=True
        ).first()
        
        if not layout:
            layout = DashboardService.create_default_layout(user)
        
        return layout
    
    @staticmethod
    def create_default_layout(user):
        """إنشاء تخطيط افتراضي"""
        layout = DashboardLayout.objects.create(
            user=user,
            name='لوحة التحكم الرئيسية',
            is_default=True,
            columns=3
        )
        
        # إضافة الويدجتس الافتراضية
        default_widgets = Widget.objects.filter(is_active=True)[:6]
        
        for i, widget in enumerate(default_widgets):
            DashboardWidget.objects.create(
                layout=layout,
                widget=widget,
                position_x=i % 3,
                position_y=i // 3,
                width=1,
                height=1,
                order=i
            )
        
        return layout
    
    @staticmethod
    def get_available_widgets(user):
        """الحصول على الويدجتس المتاحة للمستخدم"""
        widgets = Widget.objects.filter(is_active=True)
        
        # تصفية حسب الصلاحيات
        available = []
        for widget in widgets:
            if not widget.required_permission:
                available.append(widget)
            elif user.has_perm(widget.required_permission):
                available.append(widget)
        
        return available
