"""
محرك الإشعارات الذكية
يفحص النظام ويولد إشعارات تلقائية
"""
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from apps.notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationEngine:
    """محرك الإشعارات"""

    @classmethod
    def notify(cls, user, title, message, notification_type='info', category='general',
               action_url='', source_model='', source_id='', branch=None):
        """إنشاء إشعار"""
        # تجنب التكرار — لا تنشئ إشعار مكرر في نفس اليوم
        existing = Notification.objects.filter(
            user=user, category=category, source_model=source_model,
            source_id=source_id, created_at__date=timezone.now().date(),
        ).exists()

        if existing:
            return None

        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            action_url=action_url,
            source_model=source_model,
            source_id=source_id,
            branch=branch,
        )

    @classmethod
    def notify_group(cls, users, title, message, **kwargs):
        """إرسال إشعار لمجموعة مستخدمين"""
        notifications = []
        for user in users:
            n = cls.notify(user, title, message, **kwargs)
            if n:
                notifications.append(n)
        return notifications

    @classmethod
    def check_low_stock(cls):
        """فحص المخزون المنخفض"""
        try:
            from apps.inventory.services.stock_engine import StockEngine
            low_stock = StockEngine.get_low_stock_products()
        except Exception:
            return

        # أرسل لأمناء المخازن والمديرين
        storekeepers = User.objects.filter(
            is_active=True,
        ).filter(
            Q(is_superuser=True) | Q(is_staff=True)
        )

        for item in low_stock:
            for user in storekeepers:
                cls.notify(
                    user=user,
                    title=f'⚠️ مخزون منخفض: {item["product"].name}',
                    message=f'الرصيد الحالي: {item["current_stock"]} — حد إعادة الطلب: {item["reorder_level"]} — النقص: {item["deficit"]}',
                    notification_type='warning',
                    category='stock_low',
                    action_url=f'/inventory/products/{item["product"].id}/',
                    source_model='Product',
                    source_id=str(item["product"].id),
                )

    @classmethod
    def check_overdue_invoices(cls):
        """فحص الفواتير المتأخرة"""
        try:
            from apps.sales.models import SalesInvoice
        except Exception:
            return

        overdue = SalesInvoice.objects.filter(
            status__in=['confirmed', 'partial_paid'],
            remaining_amount__gt=0,
            date__lte=timezone.now() - timedelta(days=30),
        )

        managers = User.objects.filter(is_superuser=True)

        for invoice in overdue:
            days_overdue = (timezone.now().date() - invoice.date.date()).days
            for user in managers:
                cls.notify(
                    user=user,
                    title=f'🔴 فاتورة متأخرة: {invoice.invoice_number}',
                    message=f'العميل: {invoice.customer.name} — المتبقي: {invoice.remaining_amount} ج.م — متأخرة {days_overdue} يوم',
                    notification_type='danger',
                    category='invoice_overdue',
                    action_url=f'/sales/invoices/{invoice.id}/',
                    source_model='SalesInvoice',
                    source_id=str(invoice.id),
                    branch=invoice.branch,
                )

    @classmethod
    def check_expiring_contracts(cls):
        """فحص العقود القريبة من الانتهاء"""
        try:
            from apps.core.models import Branch
        except Exception:
            return

        expiring = Branch.objects.filter(
            branch_type__in=['franchise', 'distributor'],
            is_active=True,
            contract_end__lte=timezone.now().date() + timedelta(days=30),
            contract_end__gte=timezone.now().date(),
        )

        managers = User.objects.filter(is_superuser=True)

        for branch in expiring:
            days_left = (branch.contract_end - timezone.now().date()).days
            for user in managers:
                cls.notify(
                    user=user,
                    title=f'⚠️ عقد قارب على الانتهاء: {branch.name}',
                    message=f'ينتهي في {branch.contract_end} — متبقي {days_left} يوم',
                    notification_type='warning',
                    category='contract_expiring',
                    action_url=f'/branches/{branch.id}/',
                    source_model='Branch',
                    source_id=str(branch.id),
                )

    @classmethod
    def check_overdue_installments(cls):
        """فحص الأقساط المتأخرة"""
        try:
            from apps.installments.models import Installment
        except Exception:
            return

        overdue = Installment.objects.filter(
            status='pending',
            due_date__lt=timezone.now().date(),
        ).select_related('plan__customer')

        managers = User.objects.filter(is_superuser=True)

        for inst in overdue:
            days_overdue = (timezone.now().date() - inst.due_date).days
            for user in managers:
                cls.notify(
                    user=user,
                    title=f'🔴 قسط متأخر: {inst.plan.customer.name}',
                    message=f'القسط رقم {inst.installment_number} — المبلغ: {inst.amount} ج.م — متأخر {days_overdue} يوم',
                    notification_type='danger',
                    category='installment_overdue',
                    source_model='Installment',
                    source_id=str(inst.id),
                )

    @classmethod
    def check_expiring_quotations(cls):
        """فحص عروض الأسعار القريبة من الانتهاء"""
        try:
            from apps.quotations.models import Quotation
        except Exception:
            return

        expiring = Quotation.objects.filter(
            status__in=['draft', 'sent', 'negotiation'],
            valid_until__lte=timezone.now().date() + timedelta(days=3),
            valid_until__gte=timezone.now().date(),
        )

        for qt in expiring:
            if qt.salesperson:
                days_left = (qt.valid_until - timezone.now().date()).days
                cls.notify(
                    user=qt.salesperson,
                    title=f'⏰ عرض سعر يقارب على الانتهاء: {qt.quotation_number}',
                    message=f'العميل: {qt.customer_display_name} — ينتهي خلال {days_left} يوم — القيمة: {qt.total} ج.م',
                    notification_type='warning',
                    category='quotation_expiring',
                    action_url=f'/quotations/{qt.id}/',
                    source_model='Quotation',
                    source_id=str(qt.id),
                )

    @classmethod
    def check_delayed_production(cls):
        """فحص أوامر الإنتاج المتأخرة"""
        try:
            from apps.production.models import ProductionOrder
        except Exception:
            return

        delayed = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress'],
            expected_date__lt=timezone.now().date(),
        )

        managers = User.objects.filter(is_superuser=True)

        for order in delayed:
            days_late = (timezone.now().date() - order.expected_date).days
            for user in managers:
                cls.notify(
                    user=user,
                    title=f'🔴 أمر إنتاج متأخر: {order.order_number}',
                    message=f'{order.product.name} — متأخر {days_late} يوم',
                    notification_type='danger',
                    category='production_delayed',
                    action_url=f'/production/orders/{order.id}/',
                    source_model='ProductionOrder',
                    source_id=str(order.id),
                )

    @classmethod
    def check_due_checks(cls):
        """فحص الشيكات المستحقة"""
        try:
            from apps.treasury.models import Check
        except Exception:
            return

        due_checks = Check.objects.filter(
            status='pending',
            due_date__lte=timezone.now().date() + timedelta(days=3),
            due_date__gte=timezone.now().date(),
        )

        managers = User.objects.filter(is_superuser=True)

        for check in due_checks:
            days_left = (check.due_date - timezone.now().date()).days
            for user in managers:
                cls.notify(
                    user=user,
                    title=f'📋 شيك مستحق: {check.check_number}',
                    message=f'{check.partner_name} — {check.amount} ج.م — يستحق خلال {days_left} يوم',
                    notification_type='warning',
                    category='check_due',
                    source_model='Check',
                    source_id=str(check.id),
                )

    @classmethod
    def check_follow_ups(cls):
        """فحص المتابعات المتأخرة"""
        from apps.crm.models import Interaction

        overdue = Interaction.objects.filter(
            follow_up_required=True,
            is_follow_up_done=False,
            follow_up_date__lt=timezone.now().date(),
        )

        for interaction in overdue:
            if interaction.handled_by:
                cls.notify(
                    user=interaction.handled_by,
                    title='⚠️ متابعة متأخرة',
                    message=f'متابعة متأخرة مع {interaction.customer or interaction.lead}',
                    notification_type='warning',
                    category='general',
                )

    @classmethod
    def check_complaints(cls):
        """فحص الشكاوى المفتوحة أكثر من 3 أيام"""
        from apps.crm.models import Complaint

        old_complaints = Complaint.objects.filter(
            status__in=['open', 'in_progress'],
            date__lte=timezone.now() - timedelta(days=3),
        )

        managers = User.objects.filter(is_superuser=True)
        for complaint in old_complaints:
            days = (timezone.now() - complaint.date).days
            for user in managers:
                cls.notify(
                    user=user,
                    title=f'🔴 شكوى مفتوحة منذ {days} يوم',
                    message=f'{complaint.complaint_number} - {complaint.customer.name}: {complaint.subject}',
                    notification_type='danger',
                    category='general',
                )

    @classmethod
    def run_all_checks(cls):
        """تشغيل كل الفحوصات — يُستدعى يومياً"""
        cls.check_low_stock()
        cls.check_overdue_invoices()
        cls.check_expiring_contracts()
        cls.check_overdue_installments()
        cls.check_expiring_quotations()
        cls.check_delayed_production()
        cls.check_due_checks()
        cls.check_follow_ups()
        cls.check_complaints()
