# 🗺️ AI Navigation Map - خريطة التنقل للذكاء الاصطناعي

> **الغرض:** خريطة سريعة للتنقل في النظام - أين تجد ماذا

---

## 📍 الخريطة السريعة

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Tony ERP Structure                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  🔧 SETTINGS & CONFIG                                               │
│  └── accountant_pro/settings.py                                     │
│  └── .env (متغيرات البيئة)                                          │
│                                                                      │
│  🌐 URLS & ROUTING                                                  │
│  └── accountant_pro/urls.py (الرئيسي)                               │
│  └── [app]/urls.py (لكل تطبيق)                                      │
│                                                                      │
│  📦 CORE MODULES                                                    │
│  ├── inventory/    → المخزون والمنتجات                              │
│  ├── sales/        → المبيعات والفواتير                             │
│  ├── purchases/    → المشتريات                                      │
│  ├── accounting/   → المحاسبة والقيود                               │
│  ├── hr/           → الموارد البشرية                                │
│  ├── crm/          → علاقات العملاء                                 │
│  ├── pos/          → نقاط البيع                                     │
│  └── partners/     → العملاء والموردين                              │
│                                                                      │
│  🔐 AUTH & USERS                                                    │
│  ├── users/        → الصلاحيات والأدوار                             │
│  └── accounts/     → المصادقة الثنائية                              │
│                                                                      │
│  🛠️ UTILITIES                                                       │
│  ├── core/         → أدوات مشتركة                                   │
│  ├── notifications/→ الإشعارات                                      │
│  └── reports/      → التقارير                                       │
│                                                                      │
│  📄 TEMPLATES                                                       │
│  └── templates/base.html (القالب الأساسي)                           │
│  └── [app]/templates/[app]/ (لكل تطبيق)                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 أين أجد؟

### أريد تعديل/إضافة...

| ما أريده | الملف/المسار |
|----------|--------------|
| **منتج جديد** | `inventory/models.py` → `Product` |
| **فاتورة مبيعات** | `sales/models.py` → `Invoice` |
| **فاتورة مشتريات** | `purchases/models.py` → `PurchaseBill` |
| **عميل** | `partners/models.py` → `Customer` |
| **مورد** | `partners/models.py` → `Supplier` |
| **موظف** | `hr/models.py` → `Employee` |
| **حساب محاسبي** | `accounting/models.py` → `Account` |
| **قيد يومية** | `accounting/models.py` → `JournalEntry` |
| **طلب POS** | `pos/models.py` → `POSOrder` |
| **فرع** | `branches/models.py` → `Branch` |
| **مستخدم** | `users/models.py` → `UserProfile` |
| **إشعار** | `notifications/models.py` → `Notification` |

---

## 🔗 العلاقات بين الموديلات

```
                    ┌──────────────┐
                    │    User      │
                    │  (auth_user) │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │ UserProfile│   │  Employee  │   │ POSSession │
   │  (users)   │   │   (hr)     │   │   (pos)    │
   └────────────┘   └────────────┘   └─────┬──────┘
                                           │
                                           ▼
                                    ┌────────────┐
   ┌──────────────────────────────▶│  POSOrder  │
   │                                └────────────┘
   │
   │        ┌──────────────┐
   │        │   Customer   │◀──────────────────────┐
   │        │  (partners)  │                       │
   │        └──────┬───────┘                       │
   │               │                               │
   │               ▼                               │
   │        ┌──────────────┐                ┌──────┴───────┐
   │        │   Invoice    │                │ Opportunity  │
   │        │   (sales)    │                │    (crm)     │
   │        └──────┬───────┘                └──────────────┘
   │               │
   │               ▼
   │        ┌──────────────┐
   │        │ InvoiceItem  │
   │        └──────┬───────┘
   │               │
   │               ▼
   │        ┌──────────────┐         ┌──────────────┐
   └────────│   Product    │────────▶│    Stock     │
            │ (inventory)  │         │ (inventory)  │
            └──────┬───────┘         └──────┬───────┘
                   │                        │
                   ▼                        ▼
            ┌──────────────┐         ┌──────────────┐
            │   Category   │         │   Location   │
            │ (inventory)  │         │ (inventory)  │
            └──────────────┘         └──────────────┘
```

---

## 📂 هيكل كل تطبيق

```
[app_name]/
├── __init__.py
├── admin.py          # ← تسجيل في لوحة الإدارة
├── apps.py           # ← إعدادات التطبيق
├── models.py         # ← ⭐ الموديلات (الأهم)
├── views.py          # ← ⭐ العرض (الأهم)
├── urls.py           # ← ⭐ المسارات (الأهم)
├── forms.py          # ← نماذج الإدخال
├── serializers.py    # ← محولات API
├── api_views.py      # ← واجهات API
├── signals.py        # ← الإشارات
├── tasks.py          # ← مهام Celery
├── tests.py          # ← الاختبارات
├── migrations/       # ← لا تعدل يدوياً!
│   ├── __init__.py
│   └── 0001_initial.py
└── templates/
    └── [app_name]/
        ├── list.html
        ├── detail.html
        ├── form.html
        └── ...
```

---

## 🔍 البحث السريع

### البحث عن موديل معين
```bash
# في المشروع كامل
grep -rn "class ProductName" --include="models.py"

# في تطبيق محدد
grep -n "class" inventory/models.py
```

### البحث عن view
```bash
grep -rn "def view_name\|class ViewName" --include="views.py"
```

### البحث عن URL pattern
```bash
grep -rn "path\|url" --include="urls.py" | grep "name="
```

### عرض جميع URLs
```bash
python manage.py show_urls 2>/dev/null | head -50
```

### عرض جميع الموديلات
```bash
python -c "
import os; os.environ['DJANGO_SETTINGS_MODULE']='accountant_pro.settings'
import django; django.setup()
from django.apps import apps
for m in apps.get_models():
    if not m._meta.app_label.startswith('django'):
        print(f'{m._meta.app_label}.{m.__name__}')
" | head -30
```

---

## ⚡ أوامر سريعة

| الهدف | الأمر |
|-------|-------|
| فحص النظام | `python manage.py check` |
| تشغيل الخادم | `python manage.py runserver` |
| Shell تفاعلي | `python manage.py shell` |
| إنشاء migration | `python manage.py makemigrations` |
| تطبيق migrations | `python manage.py migrate` |
| إنشاء superuser | `python manage.py createsuperuser` |
| جمع static | `python manage.py collectstatic` |
| عرض SQL | `python manage.py sqlmigrate app 0001` |

---

## 🔐 نقاط المصادقة

| النقطة | المسار | الوصف |
|--------|--------|-------|
| تسجيل الدخول | `/accounts/login/` | صفحة الدخول |
| تسجيل الخروج | `/accounts/logout/` | تسجيل خروج |
| API Token | `/api/token/` | الحصول على JWT |
| Refresh Token | `/api/token/refresh/` | تجديد JWT |

---

## 📊 APIs الرئيسية

| المسار | الوصف |
|--------|-------|
| `/api/v1/products/` | المنتجات |
| `/api/v1/customers/` | العملاء |
| `/api/v1/suppliers/` | الموردين |
| `/api/v1/invoices/` | الفواتير |
| `/api/v1/stock/` | المخزون |
| `/api/v1/pos/orders/` | طلبات POS |

---

## 📝 Templates الأساسية

| الملف | الغرض |
|-------|-------|
| `templates/base.html` | القالب الرئيسي |
| `templates/base_auth.html` | صفحات المصادقة |
| `templates/components/` | مكونات مشتركة |
| `templates/includes/` | أجزاء قابلة للتضمين |

### وراثة Templates
```django
{% extends 'base.html' %}

{% block title %}عنوان الصفحة{% endblock %}

{% block content %}
    <!-- المحتوى -->
{% endblock %}

{% block extra_js %}
    <!-- JavaScript إضافي -->
{% endblock %}
```

---

## 🎨 CSS & JS

```
static/
├── css/
│   ├── style.css        # الأنماط الرئيسية
│   └── rtl.css          # دعم RTL
├── js/
│   ├── main.js          # JavaScript الرئيسي
│   └── ajax-utils.js    # أدوات AJAX
└── vendor/
    ├── bootstrap/
    └── jquery/
```

---

## 🚨 ملفات حرجة (لا تعدل!)

```
❌ manage.py
❌ accountant_pro/__init__.py
❌ */migrations/*.py (لا تحذف)
❌ venv/*
❌ .git/*
❌ db.sqlite3 (مباشرة)
```

---

## ✅ ملفات آمنة للتعديل

```
✅ [app]/models.py      → إضافة موديلات
✅ [app]/views.py       → إضافة views
✅ [app]/urls.py        → إضافة URLs
✅ [app]/forms.py       → إضافة forms
✅ [app]/admin.py       → تخصيص Admin
✅ [app]/templates/*    → إضافة/تعديل templates
✅ .env                 → متغيرات البيئة
```

---

*آخر تحديث: يناير 2026*
