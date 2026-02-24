# دليل استخدام الميزات الجديدة - New Features Usage Guide

## 🎯 مقدمة
هذا الدليل يوضح كيفية استخدام الـ 10 تطبيقات الجديدة التي تم تطويرها وتكاملها مع نظام Tony ERP.

---

## 📱 التطبيق الأول: التكامل البنكي (Bank Integration)

### الاستخدام الأساسي:

```python
from bank_integration.models import BankAccount, BankTransaction, BankReconciliation
from auth.models import User

# 1. إنشاء حساب بنكي
bank_account = BankAccount.objects.create(
    bank_name="البنك الأهلي",
    account_number="1234567890",
    account_holder="شركة النور",
    account_type="commercial",
    currency="EGP",
    current_balance=50000.00,
    available_balance=48000.00,
    status="active",
    linked_account=accounting_account,  # حساب محاسبي
)

# 2. تسجيل عملية بنكية
bank_transaction = BankTransaction.objects.create(
    account=bank_account,
    transaction_type="deposit",
    amount=5000.00,
    currency="EGP",
    transaction_date=now(),
    status="completed",
    reference_number="TXN001",
    description="إيداع من العميل أحمد محمد",
    counterparty_name="أحمد محمد",
)

# 3. إنشاء تسوية بنكية
reconciliation = BankReconciliation.objects.create(
    bank_account=bank_account,
    reconciliation_date=date.today(),
    opening_balance=48000.00,
    closing_balance=53000.00,
    statement_balance=53100.00,
    status="in_progress"
)
reconciliation.calculate_difference()  # حساب الفرق

# 4. استخدام Services
from bank_integration.services import bank_sync_service, reconciliation_service

# مزامنة العمليات من البنك
synced = bank_sync_service.sync_account_transactions(bank_account)

# مطابقة تلقائية
matched = reconciliation_service.auto_reconcile(bank_account)
```

---

## 🛡️ التطبيق الثاني: إدارة المخاطر (Risk Management)

### الاستخدام الأساسي:

```python
from risk_management.models import Risk, InsurancePolicy, InsuranceClaim, RiskCategory

# 1. تصنيف المخاطر
category = RiskCategory.objects.create(
    name="مخاطر مالية",
    color_code="#FF5733"
)

# 2. تسجيل مخاطرة جديدة
risk = Risk.objects.create(
    category=category,
    title="تقلبات أسعار الصرف",
    description="تأثر العمليات التسويقية بتقلبات سعر الدولار",
    probability=4,  # من 1 إلى 5
    impact=4,  # من 1 إلى 5
    owner=user,
    identified_date=date.today(),
    status="assessed",
    mitigation_plan="استخدام تحويطات الصرف"
)

# 3. إنشاء وثيقة تأمين
policy = InsurancePolicy.objects.create(
    policy_number="POL-2024-001",
    policy_type="professional",
    insurer_name="شركة الأهرام للتأمين",
    coverage_amount=1000000.00,
    premium=50000.00,
    deductible=10000.00,
    start_date=date.today(),
    end_date=date.today() + timedelta(days=365),
    status="active"
)

# 4. تقديم مطالبة تأمين
claim = InsuranceClaim.objects.create(
    policy=policy,
    claim_number="CLM-2024-001",
    claim_date=date.today(),
    incident_date=date.today() - timedelta(days=5),
    claim_amount=50000.00,
    description="حريق في المستودع الرئيسي",
    submitted_by=user,
    status="submitted"
)
```

---

## 💰 التطبيق الثالث: نظام الضرائب (Tax System)

### الاستخدام الأساسي:

```python
from tax_system.models import TaxType, TaxCalculation, TaxReport
from sales.models import Invoice

# 1. تحديد نوع الضريبة
tax_type = TaxType.objects.create(
    code="VAT",
    name="ضريبة القيمة المضافة",
    tax_rate=14.00,
    applicable_on="sales",
    active=True
)

# 2. حساب الضريبة على الفاتورة
tax_calc = TaxCalculation.objects.create(
    tax_type=tax_type,
    calculation_type="vat",
    taxable_amount=10000.00,
    tax_rate=14.00,
    tax_amount=1400.00,
    invoice=invoice,  # فاتورة المبيعات
    calculation_date=date.today()
)

# 3. إنشاء تقرير ضريبي شهري
report = TaxReport.objects.create(
    report_type="vat_return",
    period_type="monthly",
    period_start=date(2024, 1, 1),
    period_end=date(2024, 1, 31),
    total_taxable_income=100000.00,
    total_deductions=5000.00,
    taxable_profit=95000.00,
    total_tax_liability=13300.00,
    status="draft"
)
report.calculate_tax_liability()
```

---

## 📋 التطبيق الرابع: إدارة العقود (Contract Management)

### الاستخدام الأساسي:

```python
from contract_management.models import Contract, ContractMilestone, ContractClause

# 1. إنشاء عقد جديد
contract = Contract.objects.create(
    contract_number="CONT-2024-001",
    contract_type="service",
    title="عقد تقديم الخدمات الاستشارية",
    party_a="شركة النور",
    party_b="استشاريون الأعمال",
    contract_value=500000.00,
    currency="EGP",
    start_date=date.today(),
    end_date=date.today() + timedelta(days=365),
    status="active",
    owner=user,
    description="عقد تقديم خدمات استشارية متكاملة"
)

# 2. إضافة مراحل للعقد
milestone = ContractMilestone.objects.create(
    contract=contract,
    name="التسليم الأول",
    due_date=date.today() + timedelta(days=90),
    status="pending",
    milestone_value=125000.00
)

# 3. إضافة شروط للعقد
clause = ContractClause.objects.create(
    contract=contract,
    clause_number=1,
    title="شروط الدفع",
    content="يتم الدفع بنسبة 25% عند التوقيع و 25% عند كل مرحلة"
)

# 4. توقيع رقمي
contract.is_digitally_signed = True
contract.signature_date = now()
contract.signed_by = user
contract.save()
```

---

## 🔔 التطبيق الخامس: الإشعارات المتقدمة (Advanced Notifications)

### الاستخدام الأساسي:

```python
from advanced_notifications.models import MessageTemplate, NotificationSchedule, SentNotification

# 1. إنشاء قالب رسالة
template = MessageTemplate.objects.create(
    event_type="invoice_created",
    channel="email",
    subject="تم إنشاء فاتورة جديدة",
    body="تم إنشاء فاتورة رقم {invoice_number} بقيمة {amount}",
    is_active=True
)

# 2. جدولة إرسال رسالة
schedule = NotificationSchedule.objects.create(
    template=template,
    schedule_type="delayed",
    delay_minutes=60,  # إرسال بعد ساعة
    enabled=True
)

# 3. إرسال الرسالة
sent_notif = SentNotification.objects.create(
    template=template,
    recipient=user,
    channel="email",
    message_body="تم إنشاء فاتورة رقم INV001 بقيمة 1000 جنيه",
    status="sent",
    sent_at=now(),
    recipient_email="user@example.com"
)
```

---

## 💼 التطبيق السادس: الشؤون المالية (Treasury Management)

### الاستخدام الأساسي:

```python
from treasury_management.models import CashPosition, CashFlow, Investment

# 1. تسجيل المركز النقدي اليومي
cash_position = CashPosition.objects.create(
    date=date.today(),
    total_cash=500000.00,
    total_investments=300000.00,
    total_liabilities=100000.00,
    currency="EGP",
    notes="الموضع النقدي الحالي للشركة"
)

# 2. توقع التدفق النقدي
cash_flow = CashFlow.objects.create(
    period_start=date.today(),
    period_end=date.today() + timedelta(days=30),
    projected_inflow=200000.00,
    projected_outflow=150000.00,
    period_type="monthly"
)

# 3. تسجيل استثمار جديد
investment = Investment.objects.create(
    investment_type="fixed_deposit",
    amount=100000.00,
    currency="EGP",
    start_date=date.today(),
    maturity_date=date.today() + timedelta(days=180),
    rate_of_return=12.5,
    status="active"
)
```

---

## 🎯 التطبيق السابع: CRM متقدم (Advanced CRM)

### الاستخدام الأساسي:

```python
from advanced_crm.models import SalesStage, Opportunity, ActivityLog

# 1. تعريف مراحل البيع
stage = SalesStage.objects.create(
    name="عرض أولي",
    sequence=1,
    conversion_probability=20,
    color="#FF6B6B"
)

# 2. إنشاء فرصة بيع
opportunity = Opportunity.objects.create(
    opportunity_id="OPP-2024-001",
    title="عملية بيع منتج X للعميل الكبير",
    customer=customer,
    stage=stage,
    status="new",
    expected_value=50000.00,
    currency="EGP",
    expected_close_date=date.today() + timedelta(days=30),
    owner=user
)
opportunity.calculate_weighted_value()

# 3. تسجيل نشاط
activity = ActivityLog.objects.create(
    opportunity=opportunity,
    activity_type="meeting",
    subject="اجتماع مع العميل",
    description="تم مناقشة احتياجات العميل والأسعار",
    activity_date=now(),
    performed_by=user,
    follow_up_required=True,
    follow_up_date=date.today() + timedelta(days=3)
)
```

---

## 📊 التطبيق الثامن: الذكاء الاصطناعي والبيانات (Business Intelligence)

### الاستخدام الأساسي:

```python
from business_intelligence.models import Dashboard, Widget, Forecast, Report

# 1. إنشاء لوحة معلومات
dashboard = Dashboard.objects.create(
    name="لوحة المبيعات اليومية",
    owner=user,
    is_public=False,
    layout="grid",
    theme="light",
    auto_refresh=True,
    refresh_interval=300  # 5 دقائق
)

# 2. إضافة أداة على اللوحة
widget = Widget.objects.create(
    dashboard=dashboard,
    title="إجمالي المبيعات اليومية",
    widget_type="kpi",
    data_source="sales.Invoice",
    position_x=0,
    position_y=0,
    width=3,
    height=2
)

# 3. التنبؤ بالإيرادات
forecast = Forecast.objects.create(
    forecast_type="revenue",
    period_end=date.today() + timedelta(days=30),
    predicted_value=150000.00,
    confidence_level=85
)

# 4. إنشاء تقرير مجدول
report = Report.objects.create(
    name="تقرير المبيعات الأسبوعي",
    report_type="sales",
    frequency="weekly",
    is_active=True
)
```

---

## 📧 التطبيق التاسع: إدارة المراسلات (Correspondence Management)

### الاستخدام الأساسي:

```python
from correspondence_management.models import Correspondence, CorrespondenceThread

# 1. تسجيل رسالة واردة
correspondence = Correspondence.objects.create(
    reference_number="COR-2024-001",
    correspondence_type="incoming",
    subject="استفسار عن الأسعار",
    content="استفسار من العميل عن أسعار المنتج X",
    priority="high",
    status="received",
    received_date=now(),
    sender_name="أحمد محمد",
    sender_email="ahmed@example.com"
)

# 2. رد على الرسالة
thread = CorrespondenceThread.objects.create(
    correspondence=correspondence,
    message_type="reply",
    content="تم تحديث قائمة الأسعار والتفاصيل مرفقة",
    created_by=user,
    is_resolution=False
)

# 3. إغلاق الموضوع
correspondence.status="closed"
thread.is_resolution = True
correspondence.save()
thread.save()
```

---

## 🏆 التطبيق العاشر: الملكية الفكرية (Intellectual Property)

### الاستخدام الأساسي:

```python
from intellectual_property.models import Patent, Trademark, CopyrightWork, IPLicense

# 1. تسجيل براءة اختراع
patent = Patent.objects.create(
    patent_number="PAT-2024-001",
    patent_type="utility",
    title="براءة اختراع نظام التعامل المتكامل",
    applicant="شركة النور",
    filing_date=date(2024, 1, 15),
    grant_date=date(2024, 6, 15),
    status="granted"
)

# 2. تسجيل علامة تجارية
trademark = Trademark.objects.create(
    trademark_number="TM-2024-001",
    name="لوجو النور",
    class_code="41",
    filing_date=date(2024, 1, 15),
    registration_date=date(2024, 4, 15),
    status="registered"
)

# 3. حماية محتوى مكتوب
copyright = CopyrightWork.objects.create(
    work_type="literary",
    title="كتاب إدارة الأعمال الحديثة",
    author="د. محمد علي",
    creation_date=date(2023, 1, 1),
    publication_date=date(2023, 6, 1),
    status="protected"
)

# 4. ترخيص الملكية الفكرية
license = IPLicense.objects.create(
    intellectual_property=patent,
    licensee="شركة الاتحاد",
    license_type="non_exclusive",
    start_date=date.today(),
    end_date=date.today() + timedelta(days=365),
    royalty_percentage=5.0
)
```

---

## 🔗 الربط بين التطبيقات - Integration Between Apps

### مثال متكامل: عملية بيع كاملة

```python
# 1. إنشاء فرصة بيع
opportunity = Opportunity.objects.create(...)

# 2. إنشاء عقد للفرصة
contract = Contract.objects.create(
    contract_number="CONT-001",
    party_b=opportunity.customer.name,
    contract_value=opportunity.expected_value,
)

# 3. تسجيل الدفع
payment = PaymentTransaction.objects.create(...)

# 4. ربط الدفع بعملية بنكية
bank_transaction = BankTransaction.objects.create(
    matched_payment=payment
)

# 5. حساب الضرائب على الفاتورة
tax_calc = TaxCalculation.objects.create(
    invoice=invoice,
    tax_amount=invoice.total * 0.14
)

# 6. إرسال إشعار للعميل
notification = SentNotification.objects.create(
    template=message_template,
    recipient=user,
    message_body="تم تسجيل عقدك وقبول دفعتك"
)
```

---

## 📊 استعلامات مفيدة - Useful Queries

```python
# الفرص المفتوحة
open_opportunities = Opportunity.objects.filter(status="open")

# المخاطر العالية
high_risks = Risk.objects.filter(risk_score__gte=12)

# الوثائق المنتهية الصلاحية
expiring_policies = InsurancePolicy.objects.filter(
    end_date__lte=date.today() + timedelta(days=30),
    status="active"
)

# التسويات غير المتوازنة
unbalanced = BankReconciliation.objects.exclude(difference=0)

# الرسائل غير المرسلة
unsent = SentNotification.objects.filter(status="pending")
```

---

## 🛠️ الدعم والمساعدة - Support & Help

### الأسئلة الشائعة:
1. **كيف أدرج صورة في العقد؟** - استخدم حقل `attachments` في نموذج Contract
2. **كيف أحصل على تقرير ضريبي؟** - استخدم نموذج TaxReport مع البيانات المالية
3. **هل يمكن تصدير البيانات؟** - نعم، استخدم Django export functions

### الإصلاحات الشائعة:
- تأكد من ربط `related_name` بشكل صحيح عند الاستعلام
- استخدم `select_related()` و `prefetch_related()` لتحسين الأداء
- احفظ دائماً بعد التعديل على النموذج

---

**تم إنشاء الدليل بنجاح!**
آخر تحديث: اليوم
