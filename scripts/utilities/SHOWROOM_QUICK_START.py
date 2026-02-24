"""
🚀 دليل البدء السريع - نظام إدارة المعارض المطور
"""

# ═══════════════════════════════════════════════════════════════
# 1️⃣ إنشاء معرض مستأجر
# ═══════════════════════════════════════════════════════════════

from showrooms.models import Showroom
from showrooms.accounting_helpers import auto_create_monthly_rent_payments

showroom = Showroom.objects.create(
    code='SH-001',
    name='Main Showroom',
    name_ar='المعرض الرئيسي',
    property_type='rented',        # إيجار
    monthly_rent=20000,            # 20 ألف شهرياً
    contract_start_date='2026-01-01',
    contract_end_date='2026-12-31',
    # ... باقي الحقول
)

# إنشاء دفعات السنة
payments = auto_create_monthly_rent_payments(showroom, 12)
print(f'تم إنشاء {len(payments)} دفعة')


# ═══════════════════════════════════════════════════════════════
# 2️⃣ سداد دفعة إيجار
# ═══════════════════════════════════════════════════════════════

from showrooms.models import ShowroomRentPayment
from showrooms.accounting_helpers import create_rent_payment_entry

payment = ShowroomRentPayment.objects.get(id=1)
payment.mark_as_paid(user=request.user, payment_ref='CHQ-001')

# إنشاء القيد المحاسبي
entry = create_rent_payment_entry(payment, user=request.user)
print(f'تم السداد وإنشاء القيد: {entry.reference}')


# ═══════════════════════════════════════════════════════════════
# 3️⃣ إضافة عامل مؤقت
# ═══════════════════════════════════════════════════════════════

from showrooms.models import TemporaryWorker

worker = TemporaryWorker.objects.create(
    showroom=showroom,
    worker_name='أحمد محمد',
    job_title='حامل',
    worker_type='daily',     # يومي
    daily_wage=150,          # 150 جنيه/يوم
    start_date='2026-03-01',
    end_date='2026-03-15',
    days_worked=15
)
# الإجمالي يُحسب تلقائياً: 150 × 15 = 2,250


# ═══════════════════════════════════════════════════════════════
# 4️⃣ سداد أجر العامل
# ═══════════════════════════════════════════════════════════════

from showrooms.accounting_helpers import create_temporary_worker_payment_entry

worker.is_paid = True
worker.payment_date = timezone.now().date()
worker.save()

# إنشاء القيد
entry = create_temporary_worker_payment_entry(worker, user=request.user)


# ═══════════════════════════════════════════════════════════════
# 5️⃣ معرض مملوك (أصل ثابت)
# ═══════════════════════════════════════════════════════════════

from showrooms.accounting_helpers import create_showroom_asset_entry

showroom = Showroom.objects.create(
    code='SH-OWNED-001',
    name='Owned Showroom',
    property_type='owned',        # تمليك
    property_value=1500000,       # مليون ونصف
    # ... حقول أخرى
)

# إنشاء قيد الأصل
entry = create_showroom_asset_entry(showroom, user=request.user)


# ═══════════════════════════════════════════════════════════════
# 6️⃣ فحص الدفعات المتأخرة
# ═══════════════════════════════════════════════════════════════

from showrooms.accounting_helpers import check_and_mark_overdue_payments

overdue_count = check_and_mark_overdue_payments()
print(f'{overdue_count} دفعة متأخرة')

# أو من Terminal:
# python3 manage.py check_overdue_rent


# ═══════════════════════════════════════════════════════════════
# 7️⃣ التقارير
# ═══════════════════════════════════════════════════════════════

# المعارض القريبة من انتهاء العقد
expiring = [s for s in Showroom.objects.filter(is_active=True) 
            if s.is_contract_expiring_soon]

for s in expiring:
    print(f'{s.name} - باقي {s.contract_days_remaining} يوم')


# الدفعات المتأخرة
overdue = ShowroomRentPayment.objects.filter(status='overdue')
for p in overdue:
    print(f'{p.showroom.name} - متأخر {p.days_overdue} يوم')


# العمالة النشطة
from django.utils import timezone
active_workers = TemporaryWorker.objects.filter(
    is_active=True,
    start_date__lte=timezone.now().date(),
    end_date__gte=timezone.now().date()
)

total = sum(w.total_amount for w in active_workers)
print(f'عدد العمال: {active_workers.count()}, التكلفة: {total}')


# ═══════════════════════════════════════════════════════════════
# 8️⃣ Admin Panel
# ═══════════════════════════════════════════════════════════════

"""
من المتصفح:
/admin/showrooms/showroom/
/admin/showrooms/temporaryworker/
/admin/showrooms/showroomrentpayment/
"""


# ═══════════════════════════════════════════════════════════════
# 9️⃣ API
# ═══════════════════════════════════════════════════════════════

"""
GET  /api/showrooms/
POST /api/showrooms/
GET  /api/temporary-workers/
POST /api/temporary-workers/
GET  /api/rent-payments/
POST /api/rent-payments/
"""


# ═══════════════════════════════════════════════════════════════
# 🔟 الأمثلة الكاملة
# ═══════════════════════════════════════════════════════════════

"""
تشغيل 5 أمثلة عملية كاملة:
python3 manage.py shell < showrooms/examples.py
"""


# ═══════════════════════════════════════════════════════════════
# 📚 المراجع
# ═══════════════════════════════════════════════════════════════

"""
البدء السريع:
    SHOWROOM_SYSTEM_README.md

الدليل الكامل:
    SHOWROOM_PROPERTY_MANAGEMENT_GUIDE.md

الملخص:
    SHOWROOM_ENHANCEMENTS_SUMMARY.md

تقرير الإكمال:
    SHOWROOM_COMPLETION_REPORT.md
"""
