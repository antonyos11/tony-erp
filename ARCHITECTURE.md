# RITA ERP — دليل البنية المعمارية
## ARCHITECTURE.md — النسخة النهائية v2.0

---

## 1. نظرة عامة

**RITA ERP** نظام تخطيط موارد مؤسسي (ERP) صناعي متكامل لمصانع المراتب والمفروشات.
النظام مبني بـ Django 5.2 / Python 3.12 بواجهة Bootstrap 5 RTL كاملة للعربية.

---

## 2. مكدس التقنيات (Tech Stack)

| الطبقة        | التقنية                                      |
|--------------|----------------------------------------------|
| Framework     | Django 5.2 (Python 3.12)                    |
| Database      | PostgreSQL (إنتاج) / SQLite (تطوير)         |
| Frontend      | Bootstrap 5 RTL + Vanilla JS                |
| API           | Django REST Framework + drf-spectacular     |
| Export        | openpyxl (Excel) + xhtml2pdf (PDF)         |
| Cache         | Django LocMemCache (dev) / Redis (prod)     |
| Auth          | Django Auth + 2FA (OTP عبر البريد)         |
| Barcode/QR    | python-barcode + qrcode                     |
| Deployment    | Gunicorn + Nginx + systemd                  |

---

## 3. هيكل الملفات

```
rita-erp/
├── config/
│   ├── settings/
│   │   ├── base.py           # الإعدادات المشتركة
│   │   ├── development.py    # SQLite + DEBUG=True
│   │   └── production.py     # PostgreSQL + HTTPS + CSP
│   ├── urls.py               # URLs الرئيسية
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/                 # النواة (User, Branch, Warehouse, Company)
│   ├── accounts/             # المحاسبة (Account, JournalEntry, FiscalYear)
│   ├── inventory/            # المخزون (Product, StockLevel, BOM)
│   ├── production/           # الإنتاج (ProductionOrder, ProductionLine)
│   ├── sales/                # المبيعات (SalesInvoice, Customer)
│   ├── purchases/            # المشتريات (PurchaseOrder, Supplier)
│   ├── authorization/        # الصلاحيات + AuditLog + Security (Sprint 25)
│   ├── treasury/             # الخزينة والبنوك
│   ├── expenses/             # المصروفات
│   ├── hr/                   # الموارد البشرية
│   ├── crm/                  # إدارة العملاء
│   ├── quotations/           # عروض الأسعار
│   ├── delivery/             # التوصيل
│   ├── warranty/             # الضمان
│   ├── installments/         # الأقساط
│   ├── notifications/        # الإشعارات
│   ├── printing/             # الطباعة والباركود
│   ├── reports/              # التقارير
│   └── api/                  # REST API
├── templates/
│   ├── base.html
│   ├── exports/              # قوالب PDF (Sprint 25)
│   └── help/                 # نظام المساعدة (Sprint 25)
├── static/
├── tests/                    # اختبارات التكامل
├── logs/
└── docs/
    ├── API_DOCS.md
    ├── USER_GUIDE.md
    └── ADMIN_GUIDE.md
```

---

## 4. طبقات النظام

```
┌──────────────────────────────────────────┐
│  Browser (Bootstrap 5 RTL)              │  ← طبقة العرض
├──────────────────────────────────────────┤
│  Django Views (CBV + LoginRequired)      │  ← طبقة التحكم
│  Middleware: Audit / BruteForce / CSP   │
├──────────────────────────────────────────┤
│  Service Layer (engines/*.py)            │  ← طبقة الأعمال
│  PermissionEngine / AuditService        │
│  SalesEngine / PurchaseEngine           │
│  ProductionEngine / StockEngine         │
├──────────────────────────────────────────┤
│  Django ORM + Models (AuditMixin)        │  ← طبقة البيانات
│  Cache Layer                            │
├──────────────────────────────────────────┤
│  PostgreSQL / SQLite                     │  ← قاعدة البيانات
└──────────────────────────────────────────┘
```

---

## 5. الأمان (Sprint 25)

### Brute Force Protection
- قفل الحساب بعد **5 محاولات** خاطئة
- مدة القفل: **30 دقيقة**
- مُسجَّل في AuditLog (action=failed_login)
- Implementation: `apps/authorization/security.py`

### Two-Factor Authentication (اختياري)
- OTP عبر البريد الإلكتروني (6 أرقام، 10 دقائق)
- حقول في User: `two_factor_enabled`, `two_factor_method`

### Content Security Policy
- `ContentSecurityPolicyMiddleware` في `apps/authorization/middleware.py`
- يضيف CSP + X-Frame-Options + Referrer-Policy

### HTTPS Enforcement (إنتاج)
```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 6. نظام الصلاحيات

```
User → UserRoleAssignment → SystemRole → SystemPermission(code, module, action)
```

| المستوى        | الوصف                    |
|---------------|--------------------------|
| owner         | إدارة عليا — كل الصلاحيات |
| cfo           | مدير مالي                |
| branch_manager| مدير فرع                 |
| accountant    | محاسب                   |
| salesperson   | بائع                    |
| storekeeper   | أمين مخزن               |

---

## 7. سجل التدقيق

```python
AuditLog:
  user         # من
  action       # create / update / delete / login / logout / failed_login
  module       # القسم
  model_name   # الجدول
  object_id    # رقم السجل
  ip_address   # IP
  user_agent   # المتصفح (Sprint 25)
  timestamp    # التوقيت (db_index=True)
```

---

## 8. قواعد التطوير

1. كل Model يرث من `AuditMixin`
2. كل `verbose_name` بالعربي
3. كل view محمي بـ `LoginRequiredMixin`
4. لا تعديل على migrations يدويًا
5. قيد محاسبي واحد لكل عملية
6. كل list view يدعم Export (ExportMixin)
7. Pagination في كل القوائم (PAGE_SIZE=25)

---

## 9. الـ Sprints

| Sprint | الوظيفة                                    |
|--------|---------------------------------------------|
| 1–5    | Core + Accounts + Inventory                 |
| 6–10   | Production + Sales + Purchases              |
| 11–15  | HR + Treasury + Expenses + CRM              |
| 16–20  | Authorization + Multi-branch + Notifications|
| 21–22  | Granular Permissions + SystemRole           |
| 23–24  | Approvals + Company Settings + Setup Wizard |
| **25** | **Security + Audit + Export + Help + Docs** |

---

*RITA ERP v2.0 — Enterprise Manufacturing ERP — Sprint 25 Complete*
