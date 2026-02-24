"""
أمثلة عملية لاستخدام نظام إدارة المعارض المطور
"""

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from showrooms.models import Showroom, TemporaryWorker, ShowroomRentPayment
from showrooms.accounting_helpers import (
    create_rent_payment_entry,
    create_temporary_worker_payment_entry,
    create_showroom_asset_entry,
    auto_create_monthly_rent_payments,
    check_and_mark_overdue_payments
)
from accounting.models import Account
from inventory.models import Location

User = get_user_model()


def example_1_owned_showroom():
    """
    مثال 1: إنشاء معرض مملوك
    """
    print("=" * 50)
    print("مثال 1: معرض مملوك (تمليك)")
    print("=" * 50)
    
    # إنشاء الموقع المخزني
    location = Location.objects.create(
        code='LOC-OWNED-001',
        name='مخزن معرض التحرير'
    )
    
    # إنشاء حساب الأصول الثابتة
    asset_account = Account.objects.get_or_create(
        code='1200',
        defaults={
            'name': 'أصول ثابتة - معارض',
            'account_type': 'asset'
        }
    )[0]
    
    # إنشاء المعرض المملوك
    showroom = Showroom.objects.create(
        code='SH-OWNED-001',
        name='Tahrir Showroom',
        name_ar='معرض التحرير',
        showroom_type='showroom',
        property_type='owned',  # تمليك
        property_value=Decimal('1500000'),  # مليون ونصف جنيه
        contract_start_date=date(2025, 1, 1),
        asset_account=asset_account,
        location=location,
        address='شارع التحرير، القاهرة',
        is_active=True
    )
    
    print(f"✅ تم إنشاء المعرض: {showroom.name_ar}")
    print(f"   النوع: {showroom.get_property_type_display()}")
    print(f"   القيمة: {showroom.property_value:,.2f} جنيه")
    print(f"   مملوك: {showroom.is_owned}")
    
    # إنشاء قيد محاسبي للأصل
    user = User.objects.first()
    try:
        entry = create_showroom_asset_entry(showroom, user=user)
        print(f"✅ تم إنشاء قيد الأصل: {entry.reference}")
    except Exception as e:
        print(f"⚠️ لم يتم إنشاء القيد: {e}")
    
    return showroom


def example_2_rented_showroom():
    """
    مثال 2: معرض مستأجر مع دفعات شهرية
    """
    print("\n" + "=" * 50)
    print("مثال 2: معرض مستأجر (إيجار)")
    print("=" * 50)
    
    location = Location.objects.create(
        code='LOC-RENT-001',
        name='مخزن معرض المعادي'
    )
    
    # حساب مصروفات الإيجار
    rent_expense = Account.objects.get_or_create(
        code='5100',
        defaults={
            'name': 'مصروفات إيجار المعارض',
            'account_type': 'expense'
        }
    )[0]
    
    showroom = Showroom.objects.create(
        code='SH-RENT-001',
        name='Maadi Showroom',
        name_ar='معرض المعادي',
        showroom_type='showroom',
        property_type='rented',  # إيجار
        monthly_rent=Decimal('25000'),  # 25 ألف جنيه شهرياً
        contract_start_date=date(2026, 1, 1),
        contract_end_date=date(2026, 12, 31),
        rent_expense_account=rent_expense,
        location=location,
        address='شارع 9، المعادي',
        is_active=True
    )
    
    print(f"✅ تم إنشاء المعرض: {showroom.name_ar}")
    print(f"   النوع: {showroom.get_property_type_display()}")
    print(f"   الإيجار الشهري: {showroom.monthly_rent:,.2f} جنيه")
    print(f"   مدة العقد: من {showroom.contract_start_date} إلى {showroom.contract_end_date}")
    
    # إنشاء دفعات الإيجار الشهرية
    payments = auto_create_monthly_rent_payments(showroom, months=12)
    print(f"✅ تم إنشاء {len(payments)} دفعة إيجار")
    
    # عرض أول 3 دفعات
    for payment in payments[:3]:
        print(f"   📅 {payment.payment_date}: {payment.amount:,.2f} جنيه - {payment.get_status_display()}")
    
    # سداد أول دفعة
    first_payment = payments[0]
    user = User.objects.first()
    first_payment.mark_as_paid(user=user, payment_ref='CHQ-001')
    
    try:
        entry = create_rent_payment_entry(first_payment, user=user)
        print(f"✅ تم سداد دفعة يناير وإنشاء القيد: {entry.reference}")
    except Exception as e:
        print(f"⚠️ لم يتم إنشاء القيد: {e}")
    
    return showroom


def example_3_temporary_showroom_with_workers():
    """
    مثال 3: معرض مؤقت مع عمالة موسمية
    """
    print("\n" + "=" * 50)
    print("مثال 3: معرض مؤقت مع عمالة")
    print("=" * 50)
    
    location = Location.objects.create(
        code='LOC-TEMP-001',
        name='مخزن معرض رمضان'
    )
    
    # معرض موسمي لمدة 15 يوم
    today = timezone.now().date()
    start_date = today
    end_date = today + timedelta(days=15)
    
    showroom = Showroom.objects.create(
        code='SH-TEMP-001',
        name='Ramadan Seasonal Showroom',
        name_ar='معرض رمضان الموسمي 2026',
        showroom_type='showroom',
        property_type='temporary',  # مؤقت
        monthly_rent=Decimal('18000'),  # إجمالي مدة المعرض
        contract_start_date=start_date,
        contract_end_date=end_date,
        location=location,
        address='ميدان المحطة، طنطا',
        is_active=True
    )
    
    print(f"✅ تم إنشاء المعرض المؤقت: {showroom.name_ar}")
    print(f"   النوع: {showroom.get_property_type_display()}")
    print(f"   المدة: {showroom.contract_days_remaining} يوم")
    print(f"   التكلفة: {showroom.monthly_rent:,.2f} جنيه")
    
    # إضافة عمالة مؤقتة
    workers_data = [
        {'name': 'أحمد محمد علي', 'job': 'حامل', 'daily': 150},
        {'name': 'محمود حسن', 'job': 'عامل تنظيف', 'daily': 120},
        {'name': 'خالد عبد الله', 'job': 'موزع دعاية', 'daily': 100},
        {'name': 'علي أحمد', 'job': 'أمن', 'daily': 200},
    ]
    
    # حساب مصروفات العمالة
    labor_expense = Account.objects.get_or_create(
        code='5200',
        defaults={
            'name': 'مصروفات عمالة مؤقتة',
            'account_type': 'expense'
        }
    )[0]
    
    workers = []
    for data in workers_data:
        worker = TemporaryWorker.objects.create(
            showroom=showroom,
            worker_name=data['name'],
            job_title=data['job'],
            worker_type='daily',
            daily_wage=Decimal(str(data['daily'])),
            start_date=start_date,
            end_date=end_date,
            days_worked=15,
            expense_account=labor_expense,
            is_active=True
        )
        workers.append(worker)
        print(f"   👷 {worker.worker_name} - {worker.job_title}: {worker.total_amount:,.2f} جنيه")
    
    total_labor = sum(w.total_amount for w in workers)
    total_cost = showroom.monthly_rent + total_labor
    
    print(f"\n📊 تكلفة المعرض المؤقت:")
    print(f"   إيجار: {showroom.monthly_rent:,.2f} جنيه")
    print(f"   عمالة: {total_labor:,.2f} جنيه")
    print(f"   ━━━━━━━━━━━━━━━━━━")
    print(f"   الإجمالي: {total_cost:,.2f} جنيه")
    
    # سداد أجر أول عامل
    user = User.objects.first()
    first_worker = workers[0]
    first_worker.is_paid = True
    first_worker.payment_date = timezone.now().date()
    first_worker.payment_reference = 'CASH-001'
    first_worker.save()
    
    try:
        entry = create_temporary_worker_payment_entry(first_worker, user=user)
        print(f"\n✅ تم سداد أجر {first_worker.worker_name}")
        print(f"   القيد المحاسبي: {entry.reference}")
    except Exception as e:
        print(f"⚠️ لم يتم إنشاء القيد: {e}")
    
    return showroom, workers


def example_4_overdue_payments():
    """
    مثال 4: فحص الدفعات المتأخرة
    """
    print("\n" + "=" * 50)
    print("مثال 4: فحص الدفعات المتأخرة")
    print("=" * 50)
    
    # إنشاء دفعة متأخرة للاختبار
    past_date = timezone.now().date() - timedelta(days=10)
    
    location = Location.objects.create(
        code='LOC-TEST-001',
        name='مخزن اختبار'
    )
    
    showroom = Showroom.objects.create(
        code='SH-TEST-001',
        name='Test Showroom',
        name_ar='معرض الاختبار',
        property_type='rented',
        monthly_rent=Decimal('15000'),
        location=location
    )
    
    # دفعة متأخرة
    payment = ShowroomRentPayment.objects.create(
        showroom=showroom,
        payment_date=past_date,
        amount=showroom.monthly_rent,
        status='pending'
    )
    
    print(f"📅 دفعة مستحقة بتاريخ: {payment.payment_date}")
    print(f"   الحالة قبل الفحص: {payment.get_status_display()}")
    
    # فحص الدفعات المتأخرة
    overdue_count = check_and_mark_overdue_payments()
    
    payment.refresh_from_db()
    print(f"   الحالة بعد الفحص: {payment.get_status_display()}")
    print(f"   أيام التأخير: {payment.days_overdue}")
    print(f"\n✅ تم تحديد {overdue_count} دفعة كمتأخرة")


def example_5_contract_expiration_alerts():
    """
    مثال 5: التنبيهات لقرب انتهاء العقود
    """
    print("\n" + "=" * 50)
    print("مثال 5: تنبيهات انتهاء العقود")
    print("=" * 50)
    
    # معرض ينتهي عقده قريباً
    today = timezone.now().date()
    expiring_date = today + timedelta(days=25)  # 25 يوم
    
    location = Location.objects.create(
        code='LOC-EXP-001',
        name='مخزن معرض منتهي'
    )
    
    showroom = Showroom.objects.create(
        code='SH-EXP-001',
        name='Expiring Showroom',
        name_ar='معرض قارب على الانتهاء',
        property_type='rented',
        contract_start_date=today - timedelta(days=335),
        contract_end_date=expiring_date,
        location=location
    )
    
    print(f"📍 {showroom.name_ar}")
    print(f"   تاريخ انتهاء العقد: {showroom.contract_end_date}")
    print(f"   الأيام المتبقية: {showroom.contract_days_remaining}")
    
    if showroom.is_contract_expiring_soon:
        print(f"   ⚠️ تنبيه: العقد سينتهي خلال أقل من 30 يوم!")
    else:
        print(f"   ✅ العقد لا يزال ساري")


def run_all_examples():
    """
    تشغيل جميع الأمثلة
    """
    print("\n" + "🎯" * 25)
    print("أمثلة نظام إدارة المعارض المطور")
    print("🎯" * 25)
    
    try:
        # مثال 1: معرض مملوك
        example_1_owned_showroom()
        
        # مثال 2: معرض مستأجر
        example_2_rented_showroom()
        
        # مثال 3: معرض مؤقت مع عمالة
        example_3_temporary_showroom_with_workers()
        
        # مثال 4: الدفعات المتأخرة
        example_4_overdue_payments()
        
        # مثال 5: تنبيهات العقود
        example_5_contract_expiration_alerts()
        
        print("\n" + "=" * 50)
        print("✅ تم تنفيذ جميع الأمثلة بنجاح!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ حدث خطأ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # تشغيل الأمثلة من Django shell
    # python manage.py shell < showroom_examples.py
    run_all_examples()
