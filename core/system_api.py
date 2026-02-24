"""
API endpoints للنظام - وظائف الصيانة والتحديثات
"""
from django.http import JsonResponse
from django.http import FileResponse, Http404
from django.views.decorators.http import require_POST, require_GET
from django.core.cache import cache
from django.db import connection
from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from datetime import date, timedelta
from decimal import Decimal
import json
import os
import zipfile
import tempfile
from django.conf import settings


@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_cache(request):
    """مسح الكاش بالكامل"""
    try:
        cache.clear()
        return JsonResponse({
            'success': True,
            'message': _('تم مسح الكاش بنجاح')
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@api_view(['POST', 'GET']) # Allow GET for status checks in tests
@permission_classes([IsAdminUser])
def create_backup(request):
    """إنشاء نسخة احتياطية"""
    try:
        from django.conf import settings
        import datetime
        
        # مسار قاعدة البيانات
        db_settings = settings.DATABASES.get('default', {})
        db_engine = db_settings.get('ENGINE', '')
        
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.zip'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # نسخ قاعدة البيانات SQLite
            if 'sqlite' in db_engine:
                db_path = db_settings.get('NAME', '')
                if os.path.exists(db_path):
                    zipf.write(db_path, 'database.sqlite3')
            
            # نسخ ملفات الوسائط
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and os.path.exists(media_root):
                for root, dirs, files in os.walk(media_root):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('media', os.path.relpath(file_path, media_root))
                        zipf.write(file_path, arcname)
        
        return JsonResponse({
            'success': True,
            'message': _('تم إنشاء النسخة الاحتياطية بنجاح'),
            'download_url': f'/api/system/download-backup/{backup_filename}/'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def download_backup(request, filename):
    """تنزيل ملف النسخة الاحتياطية"""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backup_path = os.path.join(backup_dir, filename)
    if not os.path.isfile(backup_path):
        raise Http404("Backup file not found")

    response = FileResponse(open(backup_path, 'rb'), as_attachment=True, filename=filename)
    return response


@api_view(['POST'])
@permission_classes([IsAdminUser])
def maintenance_action(request):
    """تنفيذ إجراءات الصيانة"""
    try:
        data = json.loads(request.body) if request.body else {}
        action = data.get('action', '')
        
        if action == 'optimize-db':
            # تحسين قاعدة البيانات
            with connection.cursor() as cursor:
                if 'sqlite' in connection.vendor:
                    cursor.execute('VACUUM')
                    cursor.execute('ANALYZE')
                elif 'postgresql' in connection.vendor:
                    cursor.execute('VACUUM ANALYZE')
            return JsonResponse({
                'success': True,
                'message': _('تم تحسين قاعدة البيانات بنجاح')
            })
        
        elif action == 'recalculate-balances':
            # إعادة حساب الأرصدة
            from accounting.models import Account
            from sales.models import Invoice
            from purchases.models import PurchaseBill
            
            # إعادة حساب cached_total للفواتير
            for invoice in Invoice.objects.all():
                invoice.save()  # سيؤدي إلى إعادة حساب cached_total
            
            for bill in PurchaseBill.objects.all():
                bill.save()
            
            return JsonResponse({
                'success': True,
                'message': _('تم إعادة حساب الأرصدة بنجاح')
            })
        
        elif action == 'clear-logs':
            # حذف السجلات القديمة (أكثر من 90 يوم)
            from core.models import AuditLog
            cutoff = timezone.now() - timedelta(days=90)
            deleted_count, details = AuditLog.objects.filter(created_at__lt=cutoff).delete()
            return JsonResponse({
                'success': True,
                'message': _('تم حذف {} سجل قديم').format(deleted_count)
            })
        
        else:
            return JsonResponse({
                'success': False,
                'message': _('إجراء غير معروف')
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_notifications(request):
    """جلب آخر الإشعارات"""
    try:
        from notifications.models import Notification
        
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'notifications': [{
                'id': n.id,
                'message': n.message,
                'type': n.notification_type,
                'icon': get_notification_icon(n.notification_type),
                'url': n.url or '',
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')
            } for n in notifications],
            'unread_count': unread_count
        })
    except Exception as e:
        return JsonResponse({
            'success': True,
            'notifications': [],
            'unread_count': 0
        })


def get_notification_icon(notification_type):
    """إرجاع أيقونة الإشعار حسب النوع"""
    icons = {
        'info': 'bi-info-circle',
        'success': 'bi-check-circle',
        'warning': 'bi-exclamation-triangle',
        'error': 'bi-x-circle',
        'sale': 'bi-cart-check',
        'purchase': 'bi-bag-plus',
        'payment': 'bi-credit-card',
        'stock': 'bi-box-seam',
    }
    return icons.get(notification_type, 'bi-bell')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_profit_summary(request):
    """ملخص الأرباح اليومية"""
    try:
        from sales.models import Invoice, InvoiceItem, SalesReturn
        from purchases.models import PurchaseBill, PurchaseItem
        from accounting.models import Revenue, Expense
        from django.db.models import Sum, F, DecimalField, ExpressionWrapper
        
        today = date.today()
        target_date = request.GET.get('date')
        if target_date:
            try:
                today = date.fromisoformat(target_date)
            except:
                pass
        
        # تعريف التعبيرات
        sales_expr = ExpressionWrapper(
            F('quantity') * F('price'),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
        purchase_expr = ExpressionWrapper(
            F('quantity') * F('cost'),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
        
        # إجمالي المبيعات
        total_sales = InvoiceItem.objects.filter(
            invoice__date=today
        ).aggregate(total=Sum(sales_expr))['total'] or Decimal('0')
        
        # إجمالي المشتريات
        total_purchases = PurchaseItem.objects.filter(
            bill__date=today
        ).aggregate(total=Sum(purchase_expr))['total'] or Decimal('0')
        
        # خصومات المبيعات
        sales_discounts = Invoice.objects.filter(
            date=today
        ).aggregate(total=Sum('discount'))['total'] or Decimal('0')
        
        # خصومات المشتريات
        purchase_discounts = PurchaseBill.objects.filter(
            date=today
        ).aggregate(total=Sum('discount'))['total'] or Decimal('0')
        
        # ضريبة المبيعات (لا يوجد حقل tax مباشر على Invoice)
        sales_tax = Decimal('0')
        
        # ضريبة المشتريات (لا يوجد حقل tax مباشر على PurchaseBill)
        purchase_tax = Decimal('0')
        
        # مرتجع المبيعات - حساب من items
        try:
            from sales.models import SalesReturnItem
            sales_returns = SalesReturnItem.objects.filter(
                sales_return__date=today
            ).aggregate(
                total=Sum(F('quantity') * F('invoice_item__price'))
            )['total'] or Decimal('0')
        except:
            sales_returns = Decimal('0')
        
        # مرتجع المشتريات
        purchase_returns = Decimal('0')  # يحتاج إضافة model لو غير موجود
        
        # التحصيلات النقدية والبنكية
        try:
            cash_collections = Revenue.objects.filter(
                date=today,
                payment_method='cash'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            bank_collections = Revenue.objects.filter(
                date=today,
                payment_method='bank'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        except:
            cash_collections = Decimal('0')
            bank_collections = Decimal('0')
        
        total_collections = cash_collections + bank_collections
        
        # المصروفات النقدية والبنكية
        try:
            cash_expenses = Expense.objects.filter(
                date=today,
                payment_method='cash'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            bank_expenses = Expense.objects.filter(
                date=today,
                payment_method='bank'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        except:
            cash_expenses = Decimal('0')
            bank_expenses = Decimal('0')
        
        total_expenses = cash_expenses + bank_expenses
        
        # الملخص المالي
        total_income = total_sales - sales_discounts + sales_tax - sales_returns
        total_outgoing = total_purchases - purchase_discounts + purchase_tax - purchase_returns
        net_profit = total_income - total_outgoing - total_expenses
        
        return JsonResponse({
            'success': True,
            'date': today.isoformat(),
            'data': {
                'sales': {
                    'total': float(total_sales),
                    'discounts': float(sales_discounts),
                    'tax': float(sales_tax),
                    'returns': float(sales_returns),
                },
                'purchases': {
                    'total': float(total_purchases),
                    'discounts': float(purchase_discounts),
                    'tax': float(purchase_tax),
                    'returns': float(purchase_returns),
                },
                'collections': {
                    'cash': float(cash_collections),
                    'bank': float(bank_collections),
                    'total': float(total_collections),
                },
                'expenses': {
                    'cash': float(cash_expenses),
                    'bank': float(bank_expenses),
                    'total': float(total_expenses),
                },
                'summary': {
                    'total_income': float(total_income),
                    'total_expenses': float(total_expenses),
                    'net_profit': float(net_profit),
                }
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def periodic_updates_status(request):
    """حالة التحديثات الدورية"""
    try:
        from core.models import AppSettings
        
        app_settings = AppSettings.get()
        last_update = getattr(app_settings, 'last_periodic_update', None)
        
        return JsonResponse({
            'success': True,
            'last_update': last_update.isoformat() if last_update else None,
            'status': 'ready',
            'progress': 0
        })
    except Exception as e:
        return JsonResponse({
            'success': True,
            'last_update': None,
            'status': 'ready',
            'progress': 0
        })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def run_periodic_updates(request):
    """تشغيل التحديثات الدورية"""
    try:
        from core.models import AppSettings
        from django.core.cache import cache
        
        # مسح الكاش
        cache.clear()
        
        # إعادة حساب الإحصائيات
        from sales.models import Invoice, InvoiceItem
        from purchases.models import PurchaseBill, PurchaseItem
        
        # تحديث الفواتير المعلقة
        for invoice in Invoice.objects.filter(cached_total__isnull=True):
            invoice.save()
        
        # تحديث وقت آخر تحديث
        try:
            app_settings = AppSettings.get()
            app_settings.last_periodic_update = timezone.now()
            app_settings.save()
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'message': _('تم تحديث البيانات بنجاح'),
            'progress': 100
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profit_by_category(request):
    """تقرير الأرباح حسب الفئة (أو المنتج إذا لم تكن هناك فئات)"""
    try:
        from sales.models import InvoiceItem
        from purchases.models import PurchaseItem
        from inventory.models import Category
        from django.db.models import Sum, F, DecimalField, ExpressionWrapper
        
        period = request.GET.get('period', 'monthly')  # daily, monthly, yearly
        today = date.today()
        
        if period == 'daily':
            start_date = today
            end_date = today
        elif period == 'yearly':
            start_date = date(today.year, 1, 1)
            end_date = today
        else:  # monthly
            start_date = date(today.year, today.month, 1)
            end_date = today
        
        # حساب الأرباح
        sales_expr = ExpressionWrapper(
            F('quantity') * F('price'),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
        purchase_expr = ExpressionWrapper(
            F('quantity') * F('cost'),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )
        
        # التحقق من وجود فئات
        has_categories = Category.objects.exists()
        
        if has_categories:
            # مبيعات حسب الفئة
            sales_data = InvoiceItem.objects.filter(
                invoice__date__gte=start_date,
                invoice__date__lte=end_date
            ).values(
                'product__category__name'
            ).annotate(
                total=Sum(sales_expr)
            ).order_by('-total')[:10]
            
            # تجميع البيانات
            categories = []
            values = []
            for item in sales_data:
                cat_name = item['product__category__name'] or _('بدون فئة')
                categories.append(cat_name)
                values.append(float(item['total'] or 0))
        else:
            # مبيعات حسب المنتج (إذا لم توجد فئات)
            sales_data = InvoiceItem.objects.filter(
                invoice__date__gte=start_date,
                invoice__date__lte=end_date
            ).values(
                'product__name'
            ).annotate(
                total=Sum(sales_expr)
            ).order_by('-total')[:10]
            
            categories = []
            values = []
            for item in sales_data:
                product_name = item['product__name'] or _('بدون اسم')
                categories.append(product_name)
                values.append(float(item['total'] or 0))
        
        # إجماليات
        total_sales = InvoiceItem.objects.filter(
            invoice__date__gte=start_date,
            invoice__date__lte=end_date
        ).aggregate(total=Sum(sales_expr))['total'] or 0
        
        total_purchases = PurchaseItem.objects.filter(
            bill__date__gte=start_date,
            bill__date__lte=end_date
        ).aggregate(total=Sum(purchase_expr))['total'] or 0
        
        net_profit = float(total_sales) - float(total_purchases)
        
        return JsonResponse({
            'success': True,
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'data': {
                'categories': categories,
                'values': values,
                'total_sales': float(total_sales),
                'total_purchases': float(total_purchases),
                'net_profit': net_profit
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
