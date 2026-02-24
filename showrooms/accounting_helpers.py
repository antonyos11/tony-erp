"""
Helper functions لربط مصروفات المعارض بنظام المحاسبة والأصول
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from accounting.models import JournalEntry, JournalEntryItem, Account


def create_rent_payment_entry(rent_payment, user=None):
    """
    إنشاء قيد محاسبي لدفعة إيجار المعرض
    """
    showroom = rent_payment.showroom
    
    # التحقق من وجود حساب مصروفات الإيجار
    if not showroom.rent_expense_account:
        raise ValueError(f'لم يتم تحديد حساب مصروفات الإيجار للمعرض {showroom.name}')
    
    # الحصول على حساب النقدية أو البنك (يمكن تخصيصه حسب الحاجة)
    cash_account = Account.objects.filter(
        account_type='asset',
        name__icontains='نقدية'
    ).first()
    
    if not cash_account:
        cash_account = Account.objects.filter(account_type='asset').first()
    
    if not cash_account:
        raise ValueError('لا يوجد حساب نقدية متاح')
    
    with transaction.atomic():
        # إنشاء القيد المحاسبي
        entry = JournalEntry.objects.create(
            date=rent_payment.actual_payment_date or rent_payment.payment_date,
            description=f'دفعة إيجار {showroom.name} - {rent_payment.payment_date}',
            reference=rent_payment.payment_reference or f'RENT-{rent_payment.id}',
            created_by=user,
            is_posted=True,
            showroom=showroom
        )
        
        # مدين: مصروفات الإيجار
        JournalEntryItem.objects.create(
            entry=entry,
            account=showroom.rent_expense_account,
            debit=rent_payment.amount,
            credit=Decimal('0'),
            description=f'إيجار {showroom.name}'
        )
        
        # دائن: النقدية
        JournalEntryItem.objects.create(
            entry=entry,
            account=cash_account,
            debit=Decimal('0'),
            credit=rent_payment.amount,
            description=f'سداد إيجار {showroom.name}'
        )
        
        # ربط القيد بالدفعة
        rent_payment.journal_entry = entry
        rent_payment.save(update_fields=['journal_entry'])
        
        return entry


def create_temporary_worker_payment_entry(worker, user=None):
    """
    إنشاء قيد محاسبي لسداد أجر عامل مؤقت
    """
    showroom = worker.showroom
    
    # التحقق من وجود حساب المصروفات
    if not worker.expense_account:
        # محاولة الحصول على حساب مصروفات عمالة عام
        worker.expense_account = Account.objects.filter(
            account_type='expense',
            name__icontains='عمالة'
        ).first()
        
        if not worker.expense_account:
            raise ValueError('لم يتم تحديد حساب مصروفات العمالة')
    
    # الحصول على حساب النقدية
    cash_account = Account.objects.filter(
        account_type='asset',
        name__icontains='نقدية'
    ).first()
    
    if not cash_account:
        cash_account = Account.objects.filter(account_type='asset').first()
    
    if not cash_account:
        raise ValueError('لا يوجد حساب نقدية متاح')
    
    with transaction.atomic():
        # إنشاء القيد المحاسبي
        entry = JournalEntry.objects.create(
            date=worker.payment_date or timezone.now().date(),
            description=f'أجر عامل مؤقت: {worker.worker_name} - {showroom.name}',
            reference=worker.payment_reference or f'TEMP-WORKER-{worker.id}',
            created_by=user,
            is_posted=True,
            showroom=showroom
        )
        
        # مدين: مصروفات العمالة
        JournalEntryItem.objects.create(
            entry=entry,
            account=worker.expense_account,
            debit=worker.total_amount,
            credit=Decimal('0'),
            description=f'أجر {worker.worker_name} ({worker.job_title})'
        )
        
        # دائن: النقدية
        JournalEntryItem.objects.create(
            entry=entry,
            account=cash_account,
            debit=Decimal('0'),
            credit=worker.total_amount,
            description=f'سداد أجر {worker.worker_name}'
        )
        
        # ربط القيد بالعامل
        worker.journal_entry = entry
        worker.save(update_fields=['journal_entry'])
        
        return entry


def create_showroom_asset_entry(showroom, user=None):
    """
    إنشاء قيد محاسبي لإضافة معرض مملوك كأصل ثابت
    """
    if not showroom.is_owned:
        raise ValueError('هذه الدالة للمعارض المملوكة فقط')
    
    if not showroom.property_value or showroom.property_value <= 0:
        raise ValueError('يجب تحديد قيمة المعرض')
    
    if not showroom.asset_account:
        # محاولة الحصول على حساب أصول ثابتة
        showroom.asset_account = Account.objects.filter(
            account_type='asset',
            name__icontains='أصول ثابتة'
        ).first()
        
        if not showroom.asset_account:
            raise ValueError('لم يتم تحديد حساب الأصول الثابتة')
    
    # الحصول على حساب رأس المال أو البنك
    capital_account = Account.objects.filter(
        account_type='equity',
        name__icontains='رأس المال'
    ).first()
    
    if not capital_account:
        capital_account = Account.objects.filter(account_type='equity').first()
    
    if not capital_account:
        raise ValueError('لا يوجد حساب رأس مال متاح')
    
    with transaction.atomic():
        # إنشاء القيد المحاسبي
        entry = JournalEntry.objects.create(
            date=showroom.contract_start_date or showroom.opening_date or timezone.now().date(),
            description=f'شراء معرض: {showroom.name}',
            reference=f'ASSET-{showroom.code}',
            created_by=user,
            is_posted=True,
            showroom=showroom
        )
        
        # مدين: الأصول الثابتة (المعرض)
        JournalEntryItem.objects.create(
            entry=entry,
            account=showroom.asset_account,
            debit=showroom.property_value,
            credit=Decimal('0'),
            description=f'معرض {showroom.name}'
        )
        
        # دائن: رأس المال أو البنك
        JournalEntryItem.objects.create(
            entry=entry,
            account=capital_account,
            debit=Decimal('0'),
            credit=showroom.property_value,
            description=f'شراء معرض {showroom.name}'
        )
        
        return entry


def auto_create_monthly_rent_payments(showroom, months=12):
    """
    إنشاء دفعات إيجار شهرية تلقائية للمعرض
    """
    from .models import ShowroomRentPayment
    from dateutil.relativedelta import relativedelta
    
    if not showroom.is_rented and not showroom.is_temporary:
        raise ValueError('هذه الدالة للمعارض المستأجرة أو المؤقتة فقط')
    
    if not showroom.monthly_rent or showroom.monthly_rent <= 0:
        raise ValueError('يجب تحديد قيمة الإيجار الشهري')
    
    if not showroom.contract_start_date:
        raise ValueError('يجب تحديد تاريخ بداية العقد')
    
    payments = []
    current_date = showroom.contract_start_date
    
    for i in range(months):
        payment_date = current_date + relativedelta(months=i)
        
        # إيقاف عند تاريخ نهاية العقد إذا كان محدد
        if showroom.contract_end_date and payment_date > showroom.contract_end_date:
            break
        
        # التحقق من عدم وجود دفعة بنفس التاريخ
        existing = ShowroomRentPayment.objects.filter(
            showroom=showroom,
            payment_date=payment_date
        ).exists()
        
        if not existing:
            payment = ShowroomRentPayment.objects.create(
                showroom=showroom,
                payment_date=payment_date,
                amount=showroom.monthly_rent,
                status=ShowroomRentPayment.PaymentStatus.PENDING
            )
            payments.append(payment)
    
    return payments


def check_and_mark_overdue_payments():
    """
    فحص جميع دفعات الإيجار المعلقة وتحديد المتأخرة
    """
    from .models import ShowroomRentPayment
    from django.utils import timezone
    
    pending_payments = ShowroomRentPayment.objects.filter(
        status=ShowroomRentPayment.PaymentStatus.PENDING
    )
    
    today = timezone.now().date()
    overdue_count = 0
    
    for payment in pending_payments:
        if payment.payment_date < today:
            payment.status = ShowroomRentPayment.PaymentStatus.OVERDUE
            payment.save(update_fields=['status'])
            overdue_count += 1
    
    return overdue_count
