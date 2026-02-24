# 🤖 AI Agent Guide - دليل الذكاء الاصطناعي للنظام

> **الغرض:** هذا الملف دليل إرشادي لأي نموذج ذكاء اصطناعي (AI Agent) للتعامل مع نظام Tony ERP بشكل صحيح ودقيق.

---

## 📋 فهرس سريع

1. [معلومات النظام الأساسية](#-معلومات-النظام-الأساسية)
2. [البنية المعمارية](#-البنية-المعمارية)
3. [قواعد التعديل](#-قواعد-التعديل-الذهبية)
4. [أين تضيف الكود](#-أين-تضيف-الكود)
5. [المحظورات](#-المحظورات)
6. [أنماط الكود](#-أنماط-الكود-المستخدمة)
7. [قاعدة البيانات](#-قاعدة-البيانات)
8. [الاختبار](#-الاختبار)

---

## 🎯 معلومات النظام الأساسية

```yaml
اسم_المشروع: Tony ERP
إطار_العمل: Django 5.2.x
لغة_البرمجة: Python 3.11+
قاعدة_البيانات: PostgreSQL (إنتاج) / SQLite (تطوير)
الكاش: Redis
المهام: Celery
API: Django REST Framework
المسار_الرئيسي: /var/www/tony_erp
ملف_الإعدادات: accountant_pro/settings.py
```

### الأرقام المهمة (يناير 2026)
| المكون | العدد |
|--------|-------|
| التطبيقات | 79-86 |
| الموديلات | 629 |
| URLs | 5,839 |
| Migrations | 349 |
| Middleware | 26 |

---

## 🏗️ البنية المعمارية

### هيكل المجلدات الرئيسي
```
/var/www/tony_erp/
├── accountant_pro/          # ⚙️ الإعدادات الرئيسية (لا تعدل إلا للضرورة)
│   ├── settings.py          # الإعدادات الأساسية
│   ├── urls.py               # URLs الرئيسية
│   └── wsgi.py / asgi.py
│
├── core/                     # 🔧 الأدوات المشتركة
│   ├── middleware/           # Middleware مخصص
│   ├── templatetags/         # Template Tags
│   ├── utils/                # دوال مساعدة
│   └── mixins.py             # Mixins مشتركة
│
├── templates/                # 📄 القوالب العامة
│   ├── base.html             # القالب الأساسي
│   └── components/           # مكونات مشتركة
│
├── static/                   # 📁 الملفات الثابتة
├── media/                    # 📁 ملفات المستخدمين
├── logs/                     # 📁 السجلات
│
└── [app_name]/               # 📦 كل تطبيق
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── forms.py
    ├── serializers.py
    ├── api_views.py
    ├── signals.py
    ├── tasks.py
    └── templates/[app_name]/
```

### التطبيقات الأساسية (لا تحذف!)
```python
CORE_APPS = [
    'core',           # الأساسيات
    'users',          # المستخدمين والصلاحيات
    'accounts',       # المصادقة
    'inventory',      # المخزون
    'sales',          # المبيعات
    'purchases',      # المشتريات
    'accounting',     # المحاسبة
    'partners',       # الشركاء (عملاء/موردين)
    'hr',             # الموارد البشرية
    'crm',            # علاقات العملاء
    'pos',            # نقاط البيع
    'branches',       # الفروع
    'notifications',  # الإشعارات
]
```

---

## ⚠️ قواعد التعديل الذهبية

### ✅ افعل (DO)

```python
# 1. استخدم الموديلات الموجودة بدل إنشاء جديدة
from inventory.models import Product  # ✅ صحيح

# 2. استخدم الـ Mixins المشتركة
from core.mixins import AuditMixin, BranchMixin  # ✅

# 3. اتبع نمط التسمية العربي/إنجليزي
name = models.CharField(verbose_name="الاسم")
name_en = models.CharField(verbose_name="Name (EN)")  # ✅

# 4. أضف verbose_name بالعربية دائماً
class Meta:
    verbose_name = "المنتج"
    verbose_name_plural = "المنتجات"  # ✅

# 5. استخدم DecimalField للأموال
price = models.DecimalField(max_digits=14, decimal_places=2)  # ✅

# 6. أضف related_name للعلاقات
customer = models.ForeignKey(Customer, related_name='invoices')  # ✅

# 7. استخدم signals للعمليات المرتبطة
from django.db.models.signals import post_save  # ✅
```

### ❌ لا تفعل (DON'T)

```python
# 1. لا تعدل core/models.py مباشرة
# 2. لا تحذف migrations موجودة
# 3. لا تغير أسماء الحقول الموجودة
# 4. لا تستخدم FloatField للأموال
price = models.FloatField()  # ❌ خطأ!

# 5. لا تكتب SQL مباشر
cursor.execute("DELETE FROM...")  # ❌ خطأ!

# 6. لا تستخدم global imports
from module import *  # ❌ خطأ!

# 7. لا تضع منطق الأعمال في templates
{% if user.calculate_complex_logic %}  # ❌ خطأ!
```

---

## 📍 أين تضيف الكود

### إضافة موديل جديد
```
الملف: [app_name]/models.py

القالب:
class NewModel(models.Model):
    """وصف الموديل بالعربية"""
    
    name = models.CharField(max_length=255, verbose_name="الاسم")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "الاسم"
        verbose_name_plural = "الأسماء"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
```

### إضافة View جديد
```
الملف: [app_name]/views.py

للـ Class-Based Views:
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin

class MyListView(LoginRequiredMixin, ListView):
    model = MyModel
    template_name = 'app_name/my_list.html'
    context_object_name = 'items'
```

### إضافة API Endpoint
```
الملف: [app_name]/api_views.py أو [app_name]/serializers.py

from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated

class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = '__all__'

class MyModelViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    permission_classes = [IsAuthenticated]
```

### إضافة URL
```
الملف: [app_name]/urls.py

ثم أضف في accountant_pro/urls.py:
path('app_name/', include('app_name.urls')),
```

### إضافة Template
```
المسار: [app_name]/templates/[app_name]/template_name.html

يجب أن يرث من base.html:
{% extends 'base.html' %}
{% load static %}

{% block content %}
<!-- المحتوى هنا -->
{% endblock %}
```

### إضافة Celery Task
```
الملف: [app_name]/tasks.py

from celery import shared_task

@shared_task
def my_background_task(param):
    # العملية هنا
    pass
```

---

## 🚫 المحظورات

### ملفات لا تعدلها أبداً (إلا للضرورة القصوى)
```
❌ accountant_pro/settings.py  → استخدم .env بدلاً
❌ manage.py
❌ أي ملف في venv/
❌ db.sqlite3 مباشرة
❌ migrations/*  → لا تحذف أو تعدل
```

### أنماط خطيرة تجنبها
```python
# ❌ حذف جميع السجلات
Model.objects.all().delete()

# ❌ تحديث بدون فلتر
Model.objects.update(field=value)

# ❌ استعلام بدون limit
Model.objects.all()  # في views فقط

# ❌ كلمات مرور في الكود
password = "12345"

# ❌ DEBUG=True في الإنتاج
```

---

## 📝 أنماط الكود المستخدمة

### 1. نمط الموديل الأساسي
```python
from django.db import models
from django.utils.translation import gettext_lazy as _

class BaseModel(models.Model):
    """موديل أساسي مع حقول مشتركة"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    
    class Meta:
        abstract = True
```

### 2. نمط الفاتورة/المستند
```python
class Document(models.Model):
    """نمط المستند (فاتورة، أمر، إلخ)"""
    number = models.CharField(unique=True)  # رقم تسلسلي
    date = models.DateField()
    customer/supplier = models.ForeignKey(...)
    subtotal = models.DecimalField(...)
    tax_amount = models.DecimalField(...)
    discount = models.DecimalField(...)
    total = models.DecimalField(...)
    status = models.CharField(choices=STATUS_CHOICES)
    notes = models.TextField(blank=True)
    
class DocumentItem(models.Model):
    """بند المستند"""
    document = models.ForeignKey(Document, related_name='items')
    product = models.ForeignKey(Product)
    quantity = models.DecimalField(...)
    unit_price = models.DecimalField(...)
    total = models.DecimalField(...)
```

### 3. نمط الحالات (Status)
```python
class StatusChoices(models.TextChoices):
    DRAFT = 'draft', _('مسودة')
    PENDING = 'pending', _('قيد الانتظار')
    APPROVED = 'approved', _('معتمد')
    CANCELLED = 'cancelled', _('ملغي')
```

### 4. نمط الـ Manager المخصص
```python
class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class MyModel(models.Model):
    objects = models.Manager()  # الافتراضي
    active = ActiveManager()    # المخصص
```

---

## 🗄️ قاعدة البيانات

### الجداول الرئيسية للرجوع إليها
```
partners_customer     → العملاء
partners_supplier     → الموردين
inventory_product     → المنتجات
inventory_stock       → المخزون
sales_invoice         → فواتير المبيعات
sales_saleorder       → أوامر البيع
purchases_purchasebill → فواتير المشتريات
accounting_account    → الحسابات
accounting_journalentry → القيود
hr_employee           → الموظفين
pos_posorder          → طلبات POS
branches_branch       → الفروع
```

### العلاقات الشائعة
```python
# العميل
customer = models.ForeignKey(
    'partners.Customer',
    on_delete=models.PROTECT,
    related_name='%(class)ss'
)

# المنتج
product = models.ForeignKey(
    'inventory.Product',
    on_delete=models.PROTECT
)

# الفرع
branch = models.ForeignKey(
    'branches.Branch',
    on_delete=models.PROTECT,
    null=True, blank=True
)

# المستخدم
created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True
)
```

### أوامر Migration
```bash
# إنشاء migration
python manage.py makemigrations app_name

# تطبيق migrations
python manage.py migrate

# عرض SQL
python manage.py sqlmigrate app_name 0001
```

---

## 🧪 الاختبار

### قبل أي تعديل
```bash
# 1. تحقق من النظام
python manage.py check

# 2. تحقق من URLs
python manage.py show_urls | head -20

# 3. اختبر الاتصال
curl -s http://127.0.0.1:8000/ -o /dev/null -w "%{http_code}"
```

### بعد التعديل
```bash
# 1. تحقق من الأخطاء
python manage.py check

# 2. اختبر migrations
python manage.py makemigrations --dry-run

# 3. شغّل الاختبارات
python manage.py test app_name

# 4. تحقق من الصفحة
curl -s http://127.0.0.1:8000/app_name/
```

---

## 🔍 كيف تبحث في الكود

### البحث عن موديل
```bash
grep -r "class ModelName" --include="models.py"
```

### البحث عن view
```bash
grep -r "def view_name\|class ViewName" --include="views.py"
```

### البحث عن URL
```bash
grep -r "path.*name" --include="urls.py"
```

### البحث عن template
```bash
find . -name "*.html" | xargs grep "search_term"
```

---

## 📞 مراجع سريعة

### الإعدادات المهمة
```python
# قراءة إعداد
from django.conf import settings
value = getattr(settings, 'SETTING_NAME', default_value)

# المستخدم الحالي (في View)
self.request.user

# الفرع الحالي (إن وجد)
self.request.session.get('active_branch_id')
```

### Template Tags المتاحة
```django
{% load static %}
{% load i18n %}
{% load money_tags %}      # |money filter
{% load currency_tags %}   # |currency filter
{% load tony_erb_tags %}   # Tags مخصصة
{% load user_extras %}     # |has_perm filter
```

### الـ Context Processors المتاحة
```python
# متاحة في جميع Templates:
request          # الطلب الحالي
user             # المستخدم
messages         # رسائل النظام
STATIC_URL       # مسار الملفات الثابتة
unread_count     # عدد الإشعارات غير المقروءة
```

---

## ⚡ أوامر مفيدة

```bash
# إعادة تشغيل الخادم
sudo systemctl restart tony-erp

# عرض السجلات
tail -f logs/error.log

# دخول Django shell
python manage.py shell

# إنشاء superuser
python manage.py createsuperuser

# تجميع static files
python manage.py collectstatic --noinput

# تنظيف sessions
python manage.py clearsessions

# تشغيل Spec-Kit tests
python docs/spec-kit/tests/test_spec_kit.py
```

---

## 📌 ملاحظات ختامية

1. **اقرأ الكود الموجود أولاً** قبل إضافة كود جديد
2. **استخدم الأنماط الموجودة** بدل اختراع أنماط جديدة
3. **اختبر محلياً** قبل أي تعديل على الإنتاج
4. **وثّق التغييرات** في commit messages واضحة
5. **اسأل عن الشك** - إذا لم تكن متأكداً، اسأل

---

*آخر تحديث: يناير 2026*
*الإصدار: 1.0*
