# Subscriptions - إدارة الباقات والاشتراكات

## 🎯 نظرة عامة

نظام متكامل لإدارة الباقات والاشتراكات يوفر:
- ✅ 4 أنواع باقات: مبتدئين، أعمال، مؤسسات، مخصصة
- ✅ فترات دفع مرنة: شهري، ربع سنوي، نصف سنوي، سنوي
- ✅ حدود استخدام قابلة للتخصيص
- ✅ تجديد تلقائي
- ✅ نظام دفعات متكامل

---

## 📦 أنواع الباقات

### 1. باقة المبتدئين (Starter)
```python
SubscriptionPlan.objects.create(
    name="باقة المبتدئين",
    code="STARTER",
    plan_type="starter",
    monthly_price=99.00,
    annual_price=999.00,  # خصم 16%
    
    # الحدود
    max_users=3,
    max_products=500,
    max_invoices_per_month=50,
    max_storage_gb=5,
    
    # المميزات
    has_api_access=False,
    has_mobile_app=False,
    has_advanced_reports=False,
    has_ai_features=False,
    has_whatsapp_integration=False,
    has_ecommerce=False,
    has_multi_branch=False,
    has_priority_support=False,
)
```

### 2. باقة الأعمال (Business)
```python
SubscriptionPlan.objects.create(
    name="باقة الأعمال",
    code="BUSINESS",
    plan_type="business",
    monthly_price=299.00,
    annual_price=2999.00,  # خصم 16%
    
    # الحدود
    max_users=10,
    max_products=5000,
    max_invoices_per_month=500,
    max_storage_gb=50,
    
    # المميزات
    has_api_access=True,
    has_mobile_app=True,
    has_advanced_reports=True,
    has_ai_features=True,
    has_whatsapp_integration=True,
    has_ecommerce=True,
    has_multi_branch=False,
    has_priority_support=False,
)
```

### 3. باقة المؤسسات (Enterprise)
```python
SubscriptionPlan.objects.create(
    name="باقة المؤسسات",
    code="ENTERPRISE",
    plan_type="enterprise",
    monthly_price=999.00,
    annual_price=9999.00,  # خصم 17%
    
    # الحدود
    max_users=999,  # عملياً غير محدود
    max_products=999999,
    max_invoices_per_month=99999,
    max_storage_gb=500,
    
    # المميزات - الكل ✅
    has_api_access=True,
    has_mobile_app=True,
    has_advanced_reports=True,
    has_ai_features=True,
    has_whatsapp_integration=True,
    has_ecommerce=True,
    has_multi_branch=True,
    has_priority_support=True,
)
```

---

## 👤 اشتراك العميل

### إنشاء اشتراك جديد
```python
from subscriptions.models import CustomerSubscription
from datetime import datetime, timedelta

subscription = CustomerSubscription.objects.create(
    customer=user,
    plan=plan,
    subscription_number="SUB-2026-001",  # يُولّد تلقائياً
    billing_period='annual',  # شهري، ربع سنوي، نصف سنوي، سنوي
    
    # التواريخ
    start_date=datetime.now().date(),
    end_date=datetime.now().date() + timedelta(days=365),
    trial_ends_at=datetime.now().date() + timedelta(days=14),  # تجربة 14 يوم
    
    # التسعير
    price=plan.annual_price,
    discount=0.00,
    final_price=plan.annual_price,
    
    status='trial',  # trial, active, suspended, expired, cancelled
    auto_renew=True
)
```

### فحص حدود الاستخدام
```python
# تحديث الاستخدام الحالي
subscription.current_users = 8
subscription.current_products = 3500
subscription.current_invoices_this_month = 320
subscription.current_storage_gb = 35.5
subscription.save()

# فحص التجاوزات
limits = subscription.check_limits()

if limits['users_exceeded']:
    print("تجاوزت عدد المستخدمين المسموح!")

if limits['products_exceeded']:
    print("تجاوزت عدد المنتجات المسموح!")

if limits['invoices_exceeded']:
    print("تجاوزت عدد الفواتير هذا الشهر!")

if limits['storage_exceeded']:
    print("تجاوزت مساحة التخزين المسموح!")
```

### التجديد
```python
# تجديد يدوي
subscription.renew(periods=1)  # تجديد لفترة واحدة

# تجديد تلقائي (Cron Job)
from subscriptions.models import CustomerSubscription

# كل يوم، فحص الاشتراكات القريبة من الانتهاء
expiring_soon = CustomerSubscription.objects.filter(
    auto_renew=True,
    status='active',
    end_date__lte=datetime.now().date() + timedelta(days=7)
)

for sub in expiring_soon:
    # إنشاء فاتورة تجديد
    invoice = create_renewal_invoice(sub)
    
    # إرسال إشعار
    send_renewal_notification(sub.customer, invoice)
```

---

## 💳 نظام الدفعات

### تسجيل دفعة
```python
from subscriptions.models import SubscriptionPayment

payment = SubscriptionPayment.objects.create(
    subscription=subscription,
    payment_number="PAY-2026-001",  # يُولّد تلقائياً
    amount=subscription.final_price,
    payment_method='credit_card',  # credit_card, bank_transfer, cash, mada, apple_pay, stc_pay
    status='pending',  # pending, completed, failed, refunded
)

# عند نجاح الدفع
payment.status = 'completed'
payment.transaction_id = "TXN-123456789"
payment.payment_date = timezone.now()
payment.save()

# تفعيل الاشتراك
subscription.status = 'active'
subscription.save()
```

---

## 🔌 REST API

### Endpoints

```
# الباقات
GET    /api/subscriptions/plans/              # قائمة الباقات
GET    /api/subscriptions/plans/:id/          # تفاصيل باقة
GET    /api/subscriptions/plans/featured/     # الباقات المميزة

# الاشتراكات
GET    /api/subscriptions/                    # اشتراكات العميل الحالي
POST   /api/subscriptions/                    # إنشاء اشتراك
GET    /api/subscriptions/:id/                # تفاصيل اشتراك
POST   /api/subscriptions/:id/renew/          # تجديد
POST   /api/subscriptions/:id/cancel/         # إلغاء
GET    /api/subscriptions/:id/usage/          # استخدام الحالي

# الدفعات
GET    /api/subscriptions/:id/payments/       # دفعات الاشتراك
POST   /api/subscriptions/:id/payments/       # تسجيل دفعة جديدة
GET    /api/subscriptions/payments/:id/       # تفاصيل دفعة
```

### أمثلة API

```bash
# الحصول على جميع الباقات
curl http://localhost:8000/api/subscriptions/plans/

# إنشاء اشتراك
curl -X POST http://localhost:8000/api/subscriptions/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": 2,
    "billing_period": "annual"
  }'

# فحص الاستخدام
curl http://localhost:8000/api/subscriptions/1/usage/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# تجديد
curl -X POST http://localhost:8000/api/subscriptions/1/renew/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"periods": 1}'
```

---

## 🎨 لوحة الإدارة

### الوصول
```
http://localhost:8000/admin/subscriptions/
```

### الإجراءات المتاحة (Bulk Actions)
1. **تفعيل الاشتراكات** - تغيير الحالة إلى active
2. **إيقاف الاشتراكات** - تغيير الحالة إلى suspended
3. **تجديد الاشتراكات** - تجديد تلقائي

---

## ⚙️ الإعداد

### 1. إضافة للـ INSTALLED_APPS
```python
# settings.py
INSTALLED_APPS = [
    # ...
    'subscriptions',
]
```

### 2. تشغيل Migrations
```bash
python manage.py makemigrations subscriptions
python manage.py migrate subscriptions
```

### 3. إنشاء الباقات الافتراضية
```bash
python manage.py shell
```

```python
from subscriptions.models import SubscriptionPlan

# باقة المبتدئين
SubscriptionPlan.objects.create(
    name="باقة المبتدئين",
    code="STARTER",
    plan_type="starter",
    monthly_price=99.00,
    annual_price=999.00,
    max_users=3,
    max_products=500,
    is_active=True
)

# باقة الأعمال
SubscriptionPlan.objects.create(
    name="باقة الأعمال",
    code="BUSINESS",
    plan_type="business",
    monthly_price=299.00,
    annual_price=2999.00,
    max_users=10,
    max_products=5000,
    has_ai_features=True,
    has_ecommerce=True,
    is_active=True,
    is_featured=True
)

# باقة المؤسسات
SubscriptionPlan.objects.create(
    name="باقة المؤسسات",
    code="ENTERPRISE",
    plan_type="enterprise",
    monthly_price=999.00,
    annual_price=9999.00,
    max_users=999,
    max_products=999999,
    has_api_access=True,
    has_priority_support=True,
    has_multi_branch=True,
    is_active=True
)
```

---

## 🔄 التكامل مع النظام

### فحص الصلاحيات
```python
# في الـ Views أو Middleware
def check_subscription_limits(request):
    user = request.user
    subscription = user.subscriptions.filter(status='active').first()
    
    if not subscription:
        return False, "لا يوجد اشتراك نشط"
    
    limits = subscription.check_limits()
    
    if any(limits.values()):
        # تجاوز أحد الحدود
        return False, "تجاوزت حدود الاشتراك"
    
    return True, "OK"

# في الـ View
def create_invoice(request):
    allowed, message = check_subscription_limits(request)
    if not allowed:
        return Response({'error': message}, status=403)
    
    # متابعة الإنشاء
    ...
```

### حساب الاستخدام التلقائي (Signals)
```python
# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from sales.models import Invoice

@receiver(post_save, sender=Invoice)
def update_invoice_count(sender, instance, created, **kwargs):
    if created:
        user = instance.created_by
        subscription = user.subscriptions.filter(status='active').first()
        if subscription:
            subscription.current_invoices_this_month += 1
            subscription.save()
```

---

## 📊 سيناريو كامل

```python
from subscriptions.models import SubscriptionPlan, CustomerSubscription

# 1. عميل جديد يختار باقة
user = User.objects.get(username="newcustomer")
plan = SubscriptionPlan.objects.get(code="BUSINESS")

# 2. إنشاء اشتراك تجريبي
subscription = CustomerSubscription.objects.create(
    customer=user,
    plan=plan,
    billing_period='annual',
    start_date=datetime.now().date(),
    end_date=datetime.now().date() + timedelta(days=365),
    trial_ends_at=datetime.now().date() + timedelta(days=14),
    price=plan.annual_price,
    final_price=plan.annual_price,
    status='trial',
    auto_renew=True
)

# 3. بعد انتهاء التجربة، إنشاء فاتورة
if datetime.now().date() >= subscription.trial_ends_at:
    payment = SubscriptionPayment.objects.create(
        subscription=subscription,
        amount=subscription.final_price,
        payment_method='credit_card',
        status='pending'
    )
    
    # إرسال رابط الدفع
    send_payment_link(user, payment)

# 4. عند نجاح الدفع
payment.status = 'completed'
payment.payment_date = timezone.now()
payment.save()

subscription.status = 'active'
subscription.save()

# 5. تحديث الاستخدام
subscription.current_users = 5
subscription.current_products = 1200
subscription.save()

# 6. قبل انتهاء الاشتراك بأسبوع
if subscription.days_remaining() == 7:
    send_renewal_reminder(user, subscription)

# 7. تجديد تلقائي
if subscription.auto_renew and subscription.days_remaining() == 0:
    subscription.renew(periods=1)
```

---

## 🎯 الفوائد

1. **مرونة تامة:** 4 أنواع باقات + باقات مخصصة
2. **تسعير ذكي:** خصومات تلقائية للدفع السنوي
3. **تحكم دقيق:** حدود استخدام قابلة للتخصيص
4. **أتمتة كاملة:** تجديد تلقائي + إشعارات
5. **تتبع سهل:** تقارير الاستخدام والدفعات

---

**📅 آخر تحديث:** 4 يناير 2026  
**📖 الإصدار:** 1.0.0
