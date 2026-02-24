"""
خدمات التكامل بين الوحدات (Integration Services)
توفر خدمات مشتركة للتكامل بين المحاسبة والمخزون والمبيعات والمشتريات

الإصدار: 1.0
التاريخ: ديسمبر 2025
"""

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


# ============================================
# خدمات التكامل المحاسبي
# ============================================

class AccountingIntegrationService:
    """
    خدمة التكامل المحاسبي
    تربط العمليات المختلفة بالقيود المحاسبية
    """
    
    @staticmethod
    def get_accounting_settings():
        """الحصول على إعدادات المحاسبة"""
        from accounting.models import AccountingSettings
        return AccountingSettings.get()
    
    @staticmethod
    @transaction.atomic
    def create_sales_journal_entry(invoice, user=None):
        """
        إنشاء قيد محاسبي لفاتورة مبيعات
        
        القيد:
        مدين: العملاء (الذمم المدينة)
        دائن: المبيعات
        دائن: ضريبة المبيعات (إن وجدت)
        
        Args:
            invoice: فاتورة المبيعات
            user: المستخدم المنشئ
        
        Returns:
            JournalEntry: القيد المحاسبي
        """
        from accounting.models import JournalEntry, JournalEntryItem, AccountingSettings
        from accounting.journal_number_service import generate_journal_number
        
        settings = AccountingSettings.get()
        if not settings.ar_account or not settings.sales_account:
            logger.warning(f"لم يتم إعداد حسابات المبيعات والذمم - الفاتورة: {invoice.number}")
            return None
        
        total = invoice.total
        if total <= 0:
            return None
        
        # إنشاء القيد
        entry = JournalEntry.objects.create(
            number=generate_journal_number(),
            date=invoice.date,
            entry_type='sales',
            description=f"قيد مبيعات - فاتورة {invoice.number}",
            reference=invoice.number,
            invoice=invoice,
            created_by=user,
            is_posted=True
        )
        
        # مدين: الذمم المدينة
        JournalEntryItem.objects.create(
            journal_entry=entry,
            account=settings.ar_account,
            type='debit',
            amount=total,
            description=f"فاتورة مبيعات {invoice.number} - {invoice.customer.name}"
        )
        
        # دائن: المبيعات
        JournalEntryItem.objects.create(
            journal_entry=entry,
            account=settings.sales_account,
            type='credit',
            amount=total,
            description=f"إيراد مبيعات - فاتورة {invoice.number}"
        )
        
        logger.info(f"تم إنشاء قيد المبيعات {entry.number} للفاتورة {invoice.number}")
        return entry
    
    @staticmethod
    @transaction.atomic
    def create_purchase_journal_entry(bill, user=None):
        """
        إنشاء قيد محاسبي لفاتورة مشتريات
        
        القيد:
        مدين: المشتريات / المخزون
        دائن: الموردين (الذمم الدائنة)
        
        Args:
            bill: فاتورة المشتريات
            user: المستخدم المنشئ
        
        Returns:
            JournalEntry: القيد المحاسبي
        """
        from accounting.models import JournalEntry, JournalEntryItem, AccountingSettings
        from accounting.journal_number_service import generate_journal_number
        
        settings = AccountingSettings.get()
        if not settings.ap_account or not settings.purchases_account:
            logger.warning(f"لم يتم إعداد حسابات المشتريات والدائنين - الفاتورة: {bill.number}")
            return None
        
        total = bill.total
        if total <= 0:
            return None
        
        # إنشاء القيد
        entry = JournalEntry.objects.create(
            number=generate_journal_number(),
            date=bill.date,
            entry_type='purchase',
            description=f"قيد مشتريات - فاتورة {bill.number}",
            reference=bill.number,
            purchase_bill=bill,
            created_by=user,
            is_posted=True
        )
        
        # مدين: المشتريات
        JournalEntryItem.objects.create(
            journal_entry=entry,
            account=settings.purchases_account,
            type='debit',
            amount=total,
            description=f"مشتريات - فاتورة {bill.number}"
        )
        
        # دائن: الموردين
        JournalEntryItem.objects.create(
            journal_entry=entry,
            account=settings.ap_account,
            type='credit',
            amount=total,
            description=f"مستحقات للمورد {bill.supplier.name}"
        )
        
        logger.info(f"تم إنشاء قيد المشتريات {entry.number} للفاتورة {bill.number}")
        return entry
    
    @staticmethod
    @transaction.atomic
    def create_payment_journal_entry(payment, payment_type='customer', user=None):
        """
        إنشاء قيد محاسبي لدفعة
        
        دفعة عميل:
        مدين: الصندوق/البنك
        دائن: العملاء
        
        دفعة مورد:
        مدين: الموردين
        دائن: الصندوق/البنك
        
        Args:
            payment: الدفعة
            payment_type: 'customer' أو 'supplier'
            user: المستخدم المنشئ
        
        Returns:
            JournalEntry: القيد المحاسبي
        """
        from accounting.models import JournalEntry, JournalEntryItem, AccountingSettings
        from accounting.journal_number_service import generate_journal_number
        
        settings = AccountingSettings.get()
        
        # تحديد الحسابات بناءً على طريقة الدفع
        cash_account = None
        if payment.payment_method and hasattr(payment.payment_method, 'account'):
            cash_account = payment.payment_method.account
        if not cash_account:
            cash_account = settings.cash_account
        
        if not cash_account:
            logger.warning(f"لم يتم إعداد حساب الصندوق/البنك - الدفعة")
            return None
        
        amount = payment.amount
        if amount <= 0:
            return None
        
        # إنشاء القيد
        if payment_type == 'customer':
            partner_account = settings.ar_account
            entry_type = 'receipt'
            description = f"تحصيل من عميل - إيصال {payment.receipt_number}"
        else:
            partner_account = settings.ap_account
            entry_type = 'payment'
            description = f"دفعة لمورد - إيصال {payment.receipt_number}"
        
        if not partner_account:
            return None
        
        entry = JournalEntry.objects.create(
            number=generate_journal_number(),
            date=payment.date.date() if hasattr(payment.date, 'date') else payment.date,
            entry_type=entry_type,
            description=description,
            reference=payment.receipt_number,
            created_by=user,
            is_posted=True
        )
        
        if payment_type == 'customer':
            # مدين: الصندوق
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=cash_account,
                type='debit',
                amount=amount,
                description=description
            )
            # دائن: العملاء
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=partner_account,
                type='credit',
                amount=amount,
                description=description
            )
        else:
            # مدين: الموردين
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=partner_account,
                type='debit',
                amount=amount,
                description=description
            )
            # دائن: الصندوق
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=cash_account,
                type='credit',
                amount=amount,
                description=description
            )
        
        return entry
    
    @staticmethod
    @transaction.atomic
    def create_revenue_expense_journal_entry(entry, user=None):
        """
        إنشاء قيد محاسبي لإيراد أو مصروف
        
        للإيراد:
        مدين: الخزينة/البنك/المحفظة (حسب وجهة الدخول)
        دائن: حساب الإيراد
        
        للمصروف:
        مدين: حساب المصروف
        دائن: الخزينة/البنك/المحفظة (حسب مصدر الدفع)
        
        Args:
            entry: سجل AccountEntry
            user: المستخدم المنشئ
        
        Returns:
            JournalEntry: القيد المحاسبي
        """
        from accounting.models import (
            JournalEntry, JournalEntryItem, 
            AccountingSettings, Account
        )
        from accounting.journal_number_service import generate_journal_number
        
        # التحقق من تفعيل الميزة
        settings = AccountingSettings.get()
        if not settings.auto_create_journal_entries:
            logger.info("القيود التلقائية معطلة في الإعدادات")
            return None
        
        # التحقق من عدم إنشاء قيد مسبقاً
        if hasattr(entry, 'journal_entry') and entry.journal_entry:
            logger.warning(f"القيد المحاسبي موجود مسبقاً للإيراد/المصروف: {entry.id}")
            return entry.journal_entry
        
        amount = entry.amount
        if amount <= 0:
            logger.warning(f"المبلغ غير صالح للإيراد/المصروف: {entry.id}")
            return None
        
        # تحديد نوع العملية
        is_revenue = entry.entry_type == 'revenue'
        
        # تحديد الحساب المالي (حساب الإيراد/المصروف)
        if entry.ledger_account:
            financial_account = entry.ledger_account
        else:
            # استخدام الحساب الافتراضي
            if is_revenue:
                financial_account = settings.misc_revenue_account
            else:
                financial_account = settings.misc_expense_account
        
        if not financial_account:
            logger.error(f"لم يتم تحديد حساب للإيراد/المصروف: {entry.id}")
            return None
        
        # تحديد حساب النقدية (الخزينة/البنك/إلخ)
        cash_account = None
        destination_name = ""
        
        if entry.destination_type == 'treasury' and entry.treasury:
            # الخزينة
            if hasattr(entry.treasury, 'account') and entry.treasury.account:
                cash_account = entry.treasury.account
            else:
                cash_account = settings.default_treasury_account
            destination_name = entry.treasury.name
            
        elif entry.destination_type == 'bank' and entry.bank:
            # البنك
            if hasattr(entry.bank, 'account') and entry.bank.account:
                cash_account = entry.bank.account
            else:
                cash_account = settings.default_bank_account
            destination_name = entry.bank.name
            
        elif entry.destination_type == 'electronic' and entry.electronic_account:
            # المحفظة الإلكترونية
            if hasattr(entry.electronic_account, 'account') and entry.electronic_account.account:
                cash_account = entry.electronic_account.account
            else:
                cash_account = settings.default_electronic_account
            destination_name = entry.electronic_account.name
            
        elif entry.destination_type == 'fawry' and entry.fawry_machine:
            # جهاز فوري
            if hasattr(entry.fawry_machine, 'account') and entry.fawry_machine.account:
                cash_account = entry.fawry_machine.account
            else:
                cash_account = settings.default_electronic_account
            destination_name = entry.fawry_machine.name
            
        elif entry.destination_type == 'visa' and entry.visa_machine:
            # جهاز فيزا
            if hasattr(entry.visa_machine, 'account') and entry.visa_machine.account:
                cash_account = entry.visa_machine.account
            elif hasattr(entry.visa_machine, 'bank') and entry.visa_machine.bank:
                cash_account = settings.default_bank_account
            else:
                cash_account = settings.default_bank_account
            destination_name = f"{entry.visa_machine.name}"
            if hasattr(entry.visa_machine, 'bank') and entry.visa_machine.bank:
                destination_name += f" - {entry.visa_machine.bank.name}"
        
        # إذا لم يتم تحديد وجهة، استخدام الخزينة الافتراضية
        if not cash_account:
            cash_account = settings.default_treasury_account
            destination_name = "الخزينة الافتراضية"
        
        if not cash_account:
            logger.error(f"لم يتم تحديد حساب نقدي للإيراد/المصروف: {entry.id}")
            return None
        
        # إنشاء القيد المحاسبي (بدون ترحيل أولاً)
        journal_entry = JournalEntry.objects.create(
            number=generate_journal_number(),
            date=entry.date,
            entry_type='revenue' if is_revenue else 'expense',
            description=f"{'قيد إيراد' if is_revenue else 'قيد مصروف'} تلقائي - {entry.description}",
            reference=f"{'REV' if is_revenue else 'EXP'}-{entry.id}",
            created_by=user or entry.created_by,
            is_posted=False,  # لا ترحيل حتى إضافة البنود
            auto_generated=True
        )
        
        # إنشاء البنود
        if is_revenue:
            # إيراد: مدين النقدية، دائن الإيراد
            
            # مدين: النقدية (الخزينة/البنك/إلخ)
            JournalEntryItem.objects.create(
                journal_entry=journal_entry,
                account=cash_account,
                type='debit',
                amount=amount,
                description=f"إيراد - {destination_name}",
                cost_center=entry.cost_center if hasattr(entry, 'cost_center') else None
            )
            
            # دائن: الإيراد
            JournalEntryItem.objects.create(
                journal_entry=journal_entry,
                account=financial_account,
                type='credit',
                amount=amount,
                description=f"إيراد - {entry.description[:100]}",
                cost_center=entry.cost_center if hasattr(entry, 'cost_center') else None
            )
        else:
            # مصروف: مدين المصروف، دائن النقدية
            
            # مدين: المصروف
            JournalEntryItem.objects.create(
                journal_entry=journal_entry,
                account=financial_account,
                type='debit',
                amount=amount,
                description=f"مصروف - {entry.description[:100]}",
                cost_center=entry.cost_center if hasattr(entry, 'cost_center') else None
            )
            
            # دائن: النقدية (الخزينة/البنك/إلخ)
            JournalEntryItem.objects.create(
                journal_entry=journal_entry,
                account=cash_account,
                type='credit',
                amount=amount,
                description=f"مصروف - {destination_name}",
                cost_center=entry.cost_center if hasattr(entry, 'cost_center') else None
            )
        
        # ترحيل القيد بعد إضافة البنود
        journal_entry.is_posted = True
        journal_entry.save(update_fields=['is_posted'])
        
        # ربط القيد بسجل الإيراد/المصروف
        entry.journal_entry = journal_entry
        entry.save(update_fields=['journal_entry'])
        
        logger.info(
            f"تم إنشاء قيد {'إيراد' if is_revenue else 'مصروف'} تلقائي "
            f"{journal_entry.number} للسجل {entry.id}"
        )
        
        return journal_entry


# ============================================
# خدمات تكامل المخزون
# ============================================

class InventoryIntegrationService:
    """
    خدمة تكامل المخزون
    تربط حركات المخزون بالعمليات المختلفة
    """
    
    @staticmethod
    @transaction.atomic
    def deduct_stock(product, location, quantity, reason='', user=None):
        """
        خصم من المخزون
        
        Args:
            product: المنتج
            location: الموقع
            quantity: الكمية
            reason: السبب
            user: المستخدم
        
        Returns:
            Stock: سجل المخزون المحدث
        """
        from inventory.models import Stock
        
        stock, created = Stock.objects.get_or_create(
            product=product,
            location=location
        )
        
        if stock.quantity < quantity:
            raise ValueError(f"الكمية غير كافية للمنتج {product.name} في {location.name}")
        
        stock.quantity -= quantity
        stock.save(update_fields=['quantity'])
        
        logger.info(f"تم خصم {quantity} من المنتج {product.name} في {location.name}")
        return stock
    
    @staticmethod
    @transaction.atomic
    def add_stock(product, location, quantity, cost=None, reason='', user=None):
        """
        إضافة للمخزون
        
        Args:
            product: المنتج
            location: الموقع
            quantity: الكمية
            cost: التكلفة (لتحديث المتوسط)
            reason: السبب
            user: المستخدم
        
        Returns:
            Stock: سجل المخزون المحدث
        """
        from inventory.models import Stock
        
        stock, created = Stock.objects.get_or_create(
            product=product,
            location=location
        )
        
        # تحديث متوسط التكلفة إذا تم تحديد تكلفة جديدة
        if cost is not None and cost > 0:
            if stock.quantity > 0:
                current_value = stock.quantity * product.cost
                new_value = quantity * cost
                new_total_qty = stock.quantity + quantity
                new_avg_cost = (current_value + new_value) / new_total_qty
                product.cost = new_avg_cost
                product.save(update_fields=['cost'])
            else:
                product.cost = cost
                product.save(update_fields=['cost'])
        
        stock.quantity += quantity
        stock.save(update_fields=['quantity'])
        
        logger.info(f"تم إضافة {quantity} للمنتج {product.name} في {location.name}")
        return stock
    
    @staticmethod
    @transaction.atomic
    def transfer_stock(product, from_location, to_location, quantity, user=None):
        """
        تحويل مخزني
        
        Args:
            product: المنتج
            from_location: من موقع
            to_location: إلى موقع
            quantity: الكمية
            user: المستخدم
        
        Returns:
            tuple: (سجل المصدر، سجل الوجهة)
        """
        from_stock = InventoryIntegrationService.deduct_stock(
            product, from_location, quantity,
            reason=f"تحويل إلى {to_location.name}",
            user=user
        )
        
        to_stock = InventoryIntegrationService.add_stock(
            product, to_location, quantity,
            reason=f"تحويل من {from_location.name}",
            user=user
        )
        
        return from_stock, to_stock
    
    @staticmethod
    def check_stock_availability(product, location, quantity):
        """
        فحص توفر الكمية
        
        Args:
            product: المنتج
            location: الموقع
            quantity: الكمية المطلوبة
        
        Returns:
            tuple: (متوفر؟، الكمية الحالية)
        """
        from inventory.models import Stock
        
        try:
            stock = Stock.objects.get(product=product, location=location)
            return stock.quantity >= quantity, stock.quantity
        except Stock.DoesNotExist:
            return False, 0
    
    @staticmethod
    def get_total_stock(product):
        """
        إجمالي المخزون لمنتج
        
        Args:
            product: المنتج
        
        Returns:
            int: إجمالي الكمية
        """
        from inventory.models import Stock
        from django.db.models import Sum
        
        total = Stock.objects.filter(product=product).aggregate(
            total=Sum('quantity')
        )['total']
        
        return total or 0


# ============================================
# خدمات الإشعارات
# ============================================

class NotificationService:
    """
    خدمة الإشعارات
    إرسال إشعارات للمستخدمين
    """
    
    @staticmethod
    def notify_low_stock(product, location, current_qty, min_qty):
        """
        إشعار بانخفاض المخزون
        """
        from notifications.models import Notification
        from django.contrib.auth.models import User
        
        # إرسال لمديري المخزون
        managers = User.objects.filter(
            profile__role__name__in=['inventory_staff', 'warehouse_manager', 'store_supervisor']
        )
        
        for manager in managers:
            Notification.objects.create(
                user=manager,
                message=f"تنبيه: المخزون منخفض للمنتج {product.name} في {location.name} - الكمية الحالية: {current_qty}",
                notification_type='warning',
                link=f'/inventory/products/{product.id}/'
            )
    
    @staticmethod
    def notify_overdue_invoice(invoice):
        """
        إشعار بفاتورة متأخرة
        """
        from notifications.models import Notification
        from django.contrib.auth.models import User
        
        # إرسال لمسؤولي التحصيل
        collectors = User.objects.filter(
            profile__role__name__in=['accounting_staff', 'accounting_manager', 'sales_rep_internal']
        )
        
        for collector in collectors:
            Notification.objects.create(
                user=collector,
                message=f"تنبيه: فاتورة متأخرة #{invoice.number} للعميل {invoice.customer.name}",
                notification_type='alert',
                link=f'/sales/invoices/{invoice.id}/'
            )
    
    @staticmethod
    def notify_approval_required(request_type, request_obj, approver):
        """
        إشعار بطلب موافقة
        """
        from notifications.models import Notification
        
        Notification.objects.create(
            user=approver,
            message=f"طلب موافقة جديد: {request_type} - {request_obj}",
            notification_type='info',
            link=f'/approvals/'
        )


# ============================================
# خدمات الكاش والأداء
# ============================================

class CacheService:
    """
    خدمة التخزين المؤقت
    """
    
    # مدد التخزين
    CACHE_SHORT = 60  # دقيقة
    CACHE_MEDIUM = 300  # 5 دقائق
    CACHE_LONG = 3600  # ساعة
    
    @staticmethod
    def get_or_set(key, callback, timeout=300):
        """
        الحصول من الكاش أو تنفيذ الدالة وتخزين النتيجة
        """
        result = cache.get(key)
        if result is None:
            result = callback()
            cache.set(key, result, timeout)
        return result
    
    @staticmethod
    def invalidate_pattern(pattern):
        """
        حذف مجموعة من المفاتيح بناءً على نمط
        """
        # للاستخدام مع Redis
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection("default")
            keys = redis.keys(pattern)
            if keys:
                redis.delete(*keys)
        except Exception:
            # fallback للكاش المحلي
            pass
    
    @staticmethod
    def get_dashboard_stats():
        """
        إحصائيات لوحة التحكم مع كاش
        """
        def fetch_stats():
            from sales.models import Invoice
            from purchases.models import PurchaseBill
            from inventory.models import Product, Stock
            from hr.models import Employee
            from datetime import date
            from django.db.models import Sum, Count
            
            today = date.today()
            this_month = today.replace(day=1)
            
            return {
                'total_products': Product.objects.count(),
                'total_employees': Employee.objects.filter(status='active').count(),
                'sales_today': Invoice.objects.filter(
                    date=today, is_deleted=False
                ).aggregate(total=Sum('cached_total'))['total'] or 0,
                'sales_month': Invoice.objects.filter(
                    date__gte=this_month, is_deleted=False
                ).aggregate(total=Sum('cached_total'))['total'] or 0,
                'purchases_month': PurchaseBill.objects.filter(
                    date__gte=this_month, is_deleted=False
                ).aggregate(total=Sum('items__quantity') * Sum('items__cost'))['total'] or 0,
                'low_stock_count': Stock.objects.filter(
                    quantity__lte=models.F('product__min_stock')
                ).count(),
            }
        
        return CacheService.get_or_set('dashboard_stats', fetch_stats, CacheService.CACHE_SHORT)


# ============================================
# خدمات التقارير
# ============================================

class ReportService:
    """
    خدمة التقارير
    """
    
    @staticmethod
    def sales_summary(start_date, end_date):
        """
        ملخص المبيعات
        """
        from sales.models import Invoice, InvoicePayment
        from django.db.models import Sum, Count
        
        invoices = Invoice.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            is_deleted=False
        )
        
        return {
            'total_invoices': invoices.count(),
            'total_sales': invoices.aggregate(total=Sum('cached_total'))['total'] or 0,
            'total_collected': invoices.aggregate(total=Sum('paid'))['total'] or 0,
            'total_outstanding': invoices.aggregate(
                total=Sum('cached_total') - Sum('paid') - Sum('discount')
            )['total'] or 0,
        }
    
    @staticmethod
    def inventory_summary():
        """
        ملخص المخزون
        """
        from inventory.models import Product, Stock
        from django.db.models import Sum, F
        
        return {
            'total_products': Product.objects.count(),
            'total_stock_value': Stock.objects.aggregate(
                total=Sum(F('quantity') * F('product__cost'))
            )['total'] or 0,
            'low_stock_products': Stock.objects.filter(
                quantity__lte=F('product__min_stock')
            ).values('product__name', 'quantity', 'product__min_stock'),
            'out_of_stock_count': Stock.objects.filter(quantity__lte=0).count(),
        }
    
    @staticmethod
    def customer_balance(customer):
        """
        رصيد عميل
        """
        from sales.models import Invoice, InvoicePayment
        from django.db.models import Sum
        
        invoices = Invoice.objects.filter(customer=customer, is_deleted=False)
        
        total_invoiced = invoices.aggregate(
            total=Sum('cached_total') - Sum('discount')
        )['total'] or 0
        
        total_paid = invoices.aggregate(total=Sum('paid'))['total'] or 0
        
        return {
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'balance': total_invoiced - total_paid,
        }


# Import للاستخدام المباشر
from django.db import models
