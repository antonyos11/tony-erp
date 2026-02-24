# Migrations Required - الهجرات المطلوبة

## نظرة عامة
هذا الملف يوثق جميع الهجرات (Migrations) المطلوبة لتفعيل الميزات الجديدة.

---

## 1. Quality Control - Traceability Models

```bash
python manage.py makemigrations quality_control
```

### النماذج الجديدة:
- `ProductTraceability` - سجل التتبع
- `RecallOrder` - أمر الاستدعاء
- `RecallItem` - بنود الاستدعاء

### الحقول:
```python
# ProductTraceability
- product (FK)
- batch_number (CharField)
- source_type (CharField: purchase/production/adjustment)
- source_id (IntegerField)
- quantity (DecimalField)
- supplier (FK, optional)
- production_date (DateField)
- expiry_date (DateField, optional)
- location (CharField)
- notes (TextField)

# RecallOrder
- recall_number (CharField, unique)
- product (FK)
- batch_number (CharField)
- reason (TextField)
- severity (CharField: low/medium/high/critical)
- status (CharField: draft/active/completed/cancelled)
- affected_quantity (DecimalField)
- recalled_quantity (DecimalField)
- recall_date (DateField)
- completion_date (DateField, optional)

# RecallItem
- recall_order (FK)
- customer (FK, optional)
- invoice (FK, optional)
- quantity (DecimalField)
- status (CharField: pending/contacted/returned/rejected)
- contact_date (DateField, optional)
- return_date (DateField, optional)
```

---

## 2. Purchases - Supplier Evaluation Models

```bash
python manage.py makemigrations purchases
```

### النماذج الجديدة:
- `SupplierEvaluation` - تقييم المورد
- `SupplierScore` - النتائج التفصيلية
- `AlternativeSupplier` - الموردين البديلين

### الحقول:
```python
# SupplierEvaluation
- supplier (FK)
- evaluation_date (DateField)
- evaluation_period_start (DateField)
- evaluation_period_end (DateField)
- overall_score (DecimalField)
- grade (CharField: A/B/C/D/F)
- evaluator (FK User)
- notes (TextField)

# SupplierScore
- evaluation (FK)
- category (CharField: price/quality/delivery)
- score (DecimalField)
- weight (DecimalField)
- weighted_score (DecimalField)
- details (JSONField)

# AlternativeSupplier
- primary_supplier (FK)
- alternative_supplier (FK)
- product (FK)
- recommendation_date (DateField)
- reason (TextField)
- expected_improvement (DecimalField)
- status (CharField: suggested/approved/implemented/rejected)
```

---

## 3. Monitoring - Anomaly Detection Models

```bash
python manage.py makemigrations monitoring
```

### النماذج الجديدة:
- `AnomalyAlert` - تنبيه الشذوذ
- `ProactiveWarning` - التحذير الاستباقي

### الحقول:
```python
# AnomalyAlert
- category (CharField: sales/inventory/production/financial/quality/performance/security)
- severity (CharField: low/medium/high/critical)
- status (CharField: new/investigating/acknowledged/resolved/false_positive)
- title (CharField)
- description (TextField)
- anomaly_type (CharField)
- detected_value (DecimalField, optional)
- expected_value (DecimalField, optional)
- deviation_percentage (DecimalField, optional)
- recommended_actions (JSONField)
- related_model (CharField, optional)
- related_id (IntegerField, optional)
- assigned_to (FK User, optional)
- detected_at (DateTimeField)
- resolved_at (DateTimeField, optional)
- notes (TextField)

# ProactiveWarning
- warning_type (CharField: stock_out/capacity_overload/cash_flow/deadline_risk/quality_trend/cost_overrun)
- title (CharField)
- description (TextField)
- predicted_date (DateField, optional)
- confidence_level (DecimalField)
- current_value (DecimalField, optional)
- threshold_value (DecimalField, optional)
- predicted_value (DecimalField, optional)
- preventive_actions (JSONField)
- is_active (BooleanField)
- is_dismissed (BooleanField)
- created_at (DateTimeField)
- updated_at (DateTimeField)
```

### Indexes:
```python
indexes = [
    models.Index(fields=['category', 'severity', 'status']),
    models.Index(fields=['detected_at']),
]
```

---

## 4. Core - White Label Models

```bash
# إنشاء app جديد إذا لم يكن موجوداً
python manage.py startapp white_label

# ثم
python manage.py makemigrations white_label
```

### النماذج الجديدة:
- `Tenant` - المستأجر
- `TenantBranding` - العلامة التجارية
- `TenantSettings` - الإعدادات
- `TenantDomain` - النطاقات

### الحقول:
```python
# Tenant (الحقول الأساسية فقط، راجع models.py للقائمة الكاملة)
- name, slug (unique), domain (unique, optional)
- company_name, company_name_ar
- tax_id, commercial_registration
- email, phone, address, city, country
- is_active
- subscription_plan, subscription_start, subscription_end, trial_end
- max_users, max_branches, max_products, max_storage_mb
- enabled_modules (JSONField)
- custom_features (JSONField)
- timezone, language, currency
- created_at, updated_at

# TenantBranding
- tenant (OneToOne)
- logo, logo_dark, favicon (ImageField)
- primary_color, secondary_color, accent_color, background_color, text_color
- font_family, font_url
- app_title, app_title_ar, tagline, tagline_ar
- login_background (ImageField)
- login_title, login_message
- footer_text, copyright_text
- website_url, facebook_url, twitter_url, linkedin_url, instagram_url
- custom_css, custom_js (TextField)
- created_at, updated_at

# TenantSettings
- tenant (OneToOne)
- invoice_prefix, invoice_number_start, invoice_terms, invoice_footer
- tax_enabled, tax_rate, tax_number
- allow_negative_stock, auto_reorder, low_stock_threshold
- default_markup, dynamic_pricing, price_rounding
- production_auto_start, production_quality_check
- require_po_approval, po_approval_limit, require_invoice_approval
- email_notifications, sms_notifications, push_notifications
- auto_backup, backup_frequency, backup_retention_days
- password_expiry_days, max_login_attempts, session_timeout_minutes, require_2fa
- api_enabled, api_rate_limit, webhook_url
- custom_settings (JSONField)
- created_at, updated_at

# TenantDomain
- tenant (FK)
- domain (unique)
- is_primary, is_active
- ssl_enabled, ssl_certificate, ssl_expiry
- created_at, updated_at
```

---

## 5. Inventory - Physical Count Model (إذا لم يكن موجوداً)

```bash
python manage.py makemigrations inventory
```

### نموذج جديد (إذا لزم الأمر):
```python
class PhysicalCount(models.Model):
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE)
    count_date = models.DateTimeField()
    counted_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[
        ('draft', 'مسودة'),
        ('completed', 'مكتمل')
    ])
```

---

## 6. Production - Additional Models (إذا لم تكن موجودة)

```bash
python manage.py makemigrations production
```

### نماذج إضافية:
```python
# إذا لم تكن موجودة:

class ProductionLog(models.Model):
    production_order = models.ForeignKey('ProductionOrder', on_delete=models.CASCADE)
    log_type = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    defects = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class ProductionIssue(models.Model):
    production_order = models.ForeignKey('ProductionOrder', on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=50)
    description = models.TextField()
    severity = models.CharField(max_length=20)
    reported_by = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 7. إضافة حقول tenant لجميع النماذج (للـ Multi-Tenancy)

### إذا أردت عزل بيانات كامل:
```bash
# لكل app
python manage.py makemigrations <app_name>
```

### إضافة حقل tenant:
```python
# مثال: في inventory/models.py
from django.db import models
from core.white_label.models import Tenant

class Product(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,  # للتوافق مع البيانات الحالية
        blank=True
    )
    # ... باقي الحقول
```

**ملاحظة**: إضافة tenant لجميع النماذج عملية كبيرة. يمكن القيام بها تدريجياً أو استخدام schema-based multi-tenancy بدلاً من row-level.

---

## تنفيذ الهجرات

### الترتيب الموصى به:

```bash
# 1. Core/White Label أولاً
python manage.py makemigrations white_label
python manage.py migrate white_label

# 2. باقي التطبيقات
python manage.py makemigrations quality_control
python manage.py migrate quality_control

python manage.py makemigrations purchases
python manage.py migrate purchases

python manage.py makemigrations monitoring
python manage.py migrate monitoring

python manage.py makemigrations inventory
python manage.py migrate inventory

python manage.py makemigrations production
python manage.py migrate production

# 3. تشغيل جميع الهجرات المتبقية
python manage.py migrate
```

---

## Fake Migration (للبيانات الحالية)

إذا كانت بعض الحقول/الجداول موجودة بالفعل:

```bash
python manage.py migrate <app_name> --fake
```

---

## Rollback (في حالة المشاكل)

```bash
# العودة لهجرة سابقة
python manage.py migrate <app_name> <migration_name>

# مثال
python manage.py migrate monitoring 0001_initial
```

---

## البيانات الأولية (Initial Data)

### إنشاء tenant افتراضي:
```python
python manage.py shell

from core.white_label.models import Tenant, TenantBranding, TenantSettings

# إنشاء tenant افتراضي
tenant = Tenant.objects.create(
    name='Default Company',
    slug='default',
    company_name='شركة افتراضية',
    email='admin@example.com',
    phone='0500000000',
    is_active=True
)

# إنشاء branding افتراضي
branding = TenantBranding.objects.create(
    tenant=tenant,
    app_title='Tony ERP',
    app_title_ar='نظام تخطيط الموارد'
)

# إنشاء settings افتراضية
settings = TenantSettings.objects.create(
    tenant=tenant,
    invoice_prefix='INV',
    tax_enabled=True,
    tax_rate=15
)
```

---

## الفحص بعد الهجرة

```bash
# التحقق من الجداول
python manage.py dbshell
> \dt  # PostgreSQL
> SHOW TABLES;  # MySQL
> .tables  # SQLite

# التحقق من الأعمدة
> \d+ <table_name>  # PostgreSQL
> DESCRIBE <table_name>;  # MySQL
> .schema <table_name>  # SQLite
```

---

## النسخ الاحتياطي

**⚠️ مهم جداً: عمل نسخة احتياطية قبل الهجرة!**

```bash
# PostgreSQL
pg_dump dbname > backup_before_migration.sql

# MySQL
mysqldump dbname > backup_before_migration.sql

# SQLite
cp db.sqlite3 db.sqlite3.backup
```

---

## الأخطاء الشائعة وحلولها

### 1. Foreign Key Constraint
```
django.db.utils.IntegrityError: FOREIGN KEY constraint failed
```
**الحل**: تأكد من تشغيل migrations للنماذج المرتبطة أولاً.

### 2. Duplicate Column
```
django.db.utils.OperationalError: duplicate column name
```
**الحل**: استخدم `--fake` إذا كان العمود موجوداً.

### 3. No Changes Detected
```
No changes detected
```
**الحل**: تأكد من إضافة النماذج إلى `models.py` و imports صحيح.

---

## الخلاصة

بعد تشغيل جميع الهجرات، ستكون الميزات الجديدة جاهزة:

✅ Quality Control Traceability
✅ Supplier Evaluation
✅ Anomaly Detection
✅ White Label System

**الخطوة التالية**: تسجيل النماذج في Admin وإنشاء URLs وViews
