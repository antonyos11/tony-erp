# 🏢 إدارة الفروع والمعارض - التحديثات الجديدة

## ✨ ما تم إضافته

### 1️⃣ نوع الملكية للمعارض
- ✅ **تمليك**: معرض مملوك للشركة
- ✅ **إيجار**: معرض مستأجر شهرياً
- ✅ **مؤقت**: معرض موسمي لفترة محددة

### 2️⃣ إدارة العقود
- 📄 رفع عقد الشراء أو الإيجار (PDF)
- 📅 تواريخ بداية ونهاية العقد
- 💰 قيمة المعرض أو الإيجار الشهري
- 📝 ملاحظات العقد
- ⚠️ تنبيه تلقائي لقرب انتهاء العقد (30 يوم)

### 3️⃣ دفعات الإيجار
نموذج جديد: `ShowroomRentPayment`
- 📊 إنشاء دفعات شهرية تلقائياً
- ✅ تتبع حالة الدفع (معلق / مدفوع / متأخر)
- 🔔 تنبيه تلقائي للدفعات المتأخرة
- 💳 ربط بالقيود المحاسبية

### 4️⃣ العمالة المؤقتة
نموذج جديد: `TemporaryWorker`
- 👷 عمال يوميين / بالساعة / عقود مؤقتة
- 💵 حساب الأجور تلقائياً
- 📅 تتبع فترة العمل وساعات العمل
- ✅ إدارة السداد والمرجع
- 🧾 ربط بالقيود المحاسبية

### 5️⃣ الربط بالمحاسبة والأصول
- 🏦 المعارض المملوكة → أصول ثابتة
- 💸 الإيجار الشهري → مصروفات إيجار
- 👨‍🔧 أجور العمالة → مصروفات عمالة مؤقتة
- 📊 قيود محاسبية تلقائية عند السداد

---

## 📋 الحقول الجديدة في Showroom

```python
property_type = 'owned' | 'rented' | 'temporary'
property_value = Decimal  # للتمليك
monthly_rent = Decimal  # للإيجار والمؤقت
contract_start_date = Date
contract_end_date = Date
contract_document = FileField
contract_notes = TextField
asset_account = ForeignKey  # حساب الأصول
rent_expense_account = ForeignKey  # حساب مصروفات الإيجار
```

## 🆕 النماذج الجديدة

### TemporaryWorker
- معلومات العامل (الاسم، الهاتف، الهوية)
- نوع العمل والأجر
- تواريخ البداية والنهاية
- الأيام والساعات المشتغلة
- الإجمالي المستحق والسداد

### ShowroomRentPayment
- المعرض والمبلغ
- تاريخ الدفعة المقرر
- الحالة (معلق / مدفوع / متأخر)
- تاريخ الدفع الفعلي
- القيد المحاسبي المرتبط

---

## 🔧 الدوال المساعدة

### accounting_helpers.py

```python
# إنشاء قيد محاسبي لدفعة إيجار
create_rent_payment_entry(rent_payment, user)

# إنشاء قيد محاسبي لأجر عامل مؤقت
create_temporary_worker_payment_entry(worker, user)

# إضافة معرض مملوك كأصل ثابت
create_showroom_asset_entry(showroom, user)

# إنشاء دفعات إيجار شهرية تلقائياً
auto_create_monthly_rent_payments(showroom, months=12)

# فحص الدفعات المتأخرة
check_and_mark_overdue_payments()
```

---

## 🎯 كيفية الاستخدام

### 1. إضافة معرض مستأجر
```python
showroom = Showroom.objects.create(
    code='SH-001',
    name='معرض مدينة نصر',
    property_type='rented',
    monthly_rent=20000,
    contract_start_date='2026-01-01',
    contract_end_date='2026-12-31',
    rent_expense_account=expense_account,
    location=location
)

# إنشاء دفعات السنة
payments = auto_create_monthly_rent_payments(showroom, 12)
```

### 2. سداد دفعة إيجار
```python
payment = ShowroomRentPayment.objects.get(id=1)
payment.mark_as_paid(user=request.user, payment_ref='CHQ-001')

# إنشاء القيد المحاسبي
entry = create_rent_payment_entry(payment, user=request.user)
```

### 3. إضافة عامل مؤقت
```python
worker = TemporaryWorker.objects.create(
    showroom=showroom,
    worker_name='أحمد محمد',
    job_title='حامل',
    worker_type='daily',
    daily_wage=150,
    start_date='2026-03-01',
    end_date='2026-03-15',
    days_worked=15
)
# الإجمالي سيُحسب تلقائياً: 150 × 15 = 2,250
```

### 4. سداد أجر العامل
```python
worker.is_paid = True
worker.payment_date = timezone.now().date()
worker.save()

# إنشاء القيد المحاسبي
entry = create_temporary_worker_payment_entry(worker, user=request.user)
```

---

## 🔍 التقارير والاستعلامات

### المعارض القريبة من انتهاء العقد
```python
expiring = [s for s in Showroom.objects.filter(is_active=True) 
            if s.is_contract_expiring_soon]
```

### الدفعات المتأخرة
```python
overdue = ShowroomRentPayment.objects.filter(status='overdue')
```

### العمالة النشطة حالياً
```python
active_workers = TemporaryWorker.objects.filter(
    is_active=True,
    start_date__lte=timezone.now().date(),
    end_date__gte=timezone.now().date()
)
```

---

## ⚙️ Management Commands

```bash
# فحص الدفعات المتأخرة
python3 manage.py check_overdue_rent
```

---

## 📊 Admin Panel

تم تحديث الـ Admin Panel مع:
- ✅ صفحات مخصصة لإدارة العمالة المؤقتة
- ✅ صفحات مخصصة لدفعات الإيجار
- ✅ إجراءات سريعة (تحديد كمدفوع، فحص المتأخر)
- ✅ حقول القراءة فقط للحسابات التلقائية
- ✅ تنظيم الحقول في fieldsets

---

## 🔄 Migration

تم إنشاء وتطبيق Migration:
```
showrooms/migrations/0015_showroom_asset_account_...py
```

الحقول المضافة:
- asset_account
- contract_document
- contract_end_date
- contract_notes
- contract_start_date
- monthly_rent
- property_type
- property_value
- rent_expense_account
- النماذج: TemporaryWorker, ShowroomRentPayment

---

## 📱 API

تم تحديث Serializers:
- `ShowroomSerializer`: يشمل جميع حقول الملكية والعقود
- `TemporaryWorkerSerializer`: جديد
- `ShowroomRentPaymentSerializer`: جديد

---

## 📚 الملفات المعدلة/المضافة

### معدّلة:
- ✅ `showrooms/models.py` - النماذج الجديدة
- ✅ `showrooms/admin.py` - واجهات الإدارة
- ✅ `showrooms/serializers.py` - API

### جديدة:
- ✅ `showrooms/accounting_helpers.py` - دوال الربط المحاسبي
- ✅ `showrooms/management/commands/check_overdue_rent.py`
- ✅ `SHOWROOM_PROPERTY_MANAGEMENT_GUIDE.md` - الدليل الكامل

---

## ✅ الميزات المكتملة

- [x] إضافة نوع الملكية (تمليك/إيجار/مؤقت)
- [x] إدارة العقود والمستندات
- [x] نظام دفعات الإيجار
- [x] العمالة المؤقتة
- [x] الربط بالمحاسبة
- [x] الربط بالأصول
- [x] القيود المحاسبية التلقائية
- [x] التنبيهات والمراقبة
- [x] Admin Panel
- [x] API Serializers
- [x] Migration
- [x] Documentation

---

## 🎉 جاهز للاستخدام!

النظام الآن يدعم إدارة شاملة للمعارض من جميع النواحي:
- المالية (الإيجارات والعقود)
- التشغيلية (العمالة المؤقتة)
- المحاسبية (القيود التلقائية)
- الأصول (المعارض المملوكة)

**للتفاصيل الكاملة:** راجع `SHOWROOM_PROPERTY_MANAGEMENT_GUIDE.md`
