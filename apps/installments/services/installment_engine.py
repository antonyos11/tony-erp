"""
محرك الأقساط — إنشاء خطة + جدولة تلقائية + تسجيل دفعات + متابعة متأخرات
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
import calendar

from django.db import transaction
from django.utils import timezone

from apps.installments.models import InstallmentPlan, Installment


def _add_months(source_date, months):
    """إضافة عدد من الأشهر لتاريخ معين"""
    month = source_date.month - 1 + months
    year  = source_date.year + month // 12
    month = month % 12 + 1
    day   = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class InstallmentEngine:
    """محرك إدارة الأقساط"""

    # ── إنشاء خطة أقساط مع جدولة تلقائية ─────────────────────────
    @classmethod
    @transaction.atomic
    def create_plan(cls, invoice, customer, total_amount, down_payment,
                    number_of_installments, interest_rate, start_date,
                    user=None):
        """
        إنشاء خطة أقساط وجدولة الأقساط تلقائياً

        يتم احتساب قيمة كل قسط بالتساوي على أساس شهري.
        """
        total_amount    = Decimal(str(total_amount))
        down_payment    = Decimal(str(down_payment))
        interest_rate   = Decimal(str(interest_rate))
        n               = int(number_of_installments)

        if n <= 0:
            raise ValueError("عدد الأقساط يجب أن يكون أكبر من صفر")
        if down_payment > total_amount:
            raise ValueError("المقدم أكبر من المبلغ الإجمالي")

        principal = total_amount - down_payment
        # احتساب الفائدة البسيطة
        interest = (principal * interest_rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_with_interest = principal + interest
        installment_amount = (total_with_interest / n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # تعديل آخر قسط لتغطية أي فارق تقريب
        last_installment_amount = total_with_interest - (installment_amount * (n - 1))

        plan = InstallmentPlan.objects.create(
            invoice=invoice,
            customer=customer,
            total_amount=total_amount,
            down_payment=down_payment,
            number_of_installments=n,
            installment_amount=installment_amount,
            interest_rate=interest_rate,
            start_date=start_date,
            status='active',
            created_by=user,
            updated_by=user,
        )

        # جدولة الأقساط شهرياً
        for i in range(1, n + 1):
            due = _add_months(start_date, i - 1)
            amt = last_installment_amount if i == n else installment_amount
            Installment.objects.create(
                plan=plan,
                installment_number=i,
                due_date=due,
                amount=amt,
                status='pending',
                created_by=user,
                updated_by=user,
            )

        return plan

    # ── تسجيل دفعة قسط ─────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def pay_installment(cls, installment, paid_amount, payment_date=None, user=None):
        """تسجيل دفعة لقسط معين (كاملة أو جزئية)"""
        paid_amount  = Decimal(str(paid_amount))
        payment_date = payment_date or timezone.now().date()

        if paid_amount <= 0:
            raise ValueError("المبلغ المدفوع يجب أن يكون أكبر من صفر")
        if installment.status == 'paid':
            raise ValueError("هذا القسط مدفوع بالفعل")

        installment.paid_amount += paid_amount
        installment.paid_date   = payment_date
        installment.updated_by  = user

        if installment.paid_amount >= installment.amount:
            installment.status = 'paid'
        else:
            installment.status = 'partial'

        installment.save()

        # تحقق من اكتمال الخطة بالكامل
        plan = installment.plan
        all_paid = not plan.installments.exclude(status='paid').exists()
        if all_paid:
            plan.status = 'completed'
            plan.updated_by = user
            plan.save(update_fields=['status', 'updated_at', 'updated_by'])

        return installment

    # ── تحديث حالة المتأخرات ───────────────────────────────────────
    @classmethod
    @transaction.atomic
    def update_overdue_statuses(cls):
        """
        تحديث حالة الأقساط المتأخرة (يُستدعى بـ cron job يومياً)
        """
        today = date.today()
        updated = Installment.objects.filter(
            status='pending',
            due_date__lt=today,
        ).update(status='overdue')

        # تمييل الخطط ذات أقساط متأخرة
        from django.db.models import Q
        plans_with_overdue = InstallmentPlan.objects.filter(
            status='active',
            installments__status='overdue',
        ).distinct()
        plans_with_overdue.update(status='defaulted')

        return updated

    # ── جدول السداد (للعرض) ────────────────────────────────────────
    @staticmethod
    def get_schedule(plan):
        """إرجاع جدول السداد مع معلومات إضافية"""
        return plan.installments.all().order_by('installment_number')
