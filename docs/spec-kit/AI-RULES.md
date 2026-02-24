# 🚦 AI Rules & Constraints - قواعد وقيود الذكاء الاصطناعي

> **الغرض:** قواعد صارمة يجب على أي AI Agent اتباعها عند التعامل مع النظام

---

## 🔴 قواعد حمراء (لا تكسرها أبداً)

### 1. ❌ لا تحذف أي ملف migration
```bash
# ❌ محظور تماماً
rm */migrations/*.py
git rm */migrations/*.py
```

### 2. ❌ لا تغير أسماء الحقول الموجودة في الموديلات
```python
# ❌ خطأ - هذا سيكسر البيانات
# كان: name = models.CharField()
# أصبح: title = models.CharField()  # ❌ لا!
```

### 3. ❌ لا تحذف بيانات بدون تأكيد
```python
# ❌ محظور
Model.objects.all().delete()
Model.objects.filter(...).delete()  # بدون limit
```

### 4. ❌ لا تضع credentials في الكود
```python
# ❌ محظور تماماً
API_KEY = "sk-abc123..."
PASSWORD = "secret"
SECRET_KEY = "..."

# ✅ الصحيح
API_KEY = os.getenv('API_KEY')
```

### 5. ❌ لا تعدل settings.py مباشرة للإنتاج
```python
# ❌ محظور
DEBUG = True  # في الإنتاج

# ✅ الصحيح - استخدم .env
DEBUG = os.getenv('DEBUG', '0') == '1'
```

---

## 🟡 قواعد صفراء (تحذيرات مهمة)

### 1. ⚠️ اختبر محلياً أولاً
```bash
# قبل أي تعديل
python manage.py check
python manage.py makemigrations --dry-run
```

### 2. ⚠️ استخدم transactions للعمليات المتعددة
```python
from django.db import transaction

with transaction.atomic():
    obj1.save()
    obj2.save()
    # إذا فشل أي شيء، يتم التراجع عن الكل
```

### 3. ⚠️ أضف verbose_name بالعربية
```python
# ⚠️ ناقص
name = models.CharField(max_length=255)

# ✅ كامل
name = models.CharField(max_length=255, verbose_name="الاسم")
```

### 4. ⚠️ استخدم related_name
```python
# ⚠️ قد يسبب تعارض
customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

# ✅ أفضل
customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
```

### 5. ⚠️ لا تستخدم `*` imports
```python
# ⚠️ خطر
from models import *

# ✅ صحيح
from models import Product, Category, Stock
```

---

## 🟢 قواعد خضراء (أفضل الممارسات)

### 1. ✅ اتبع نمط التسمية
```python
# الموديلات: PascalCase
class ProductCategory(models.Model):

# الدوال والمتغيرات: snake_case
def calculate_total_price():
    unit_price = 100

# الثوابت: UPPER_CASE
MAX_QUANTITY = 1000
STATUS_CHOICES = [...]
```

### 2. ✅ استخدم الـ Mixins الموجودة
```python
from core.mixins import AuditMixin, BranchMixin

class MyModel(AuditMixin, BranchMixin, models.Model):
    # يرث created_at, updated_at, created_by, branch
```

### 3. ✅ وثّق الكود
```python
class Invoice(models.Model):
    """
    فاتورة المبيعات
    
    تحتوي على:
    - بيانات العميل
    - بنود الفاتورة
    - معلومات الضريبة
    """
    
    def calculate_total(self):
        """حساب إجمالي الفاتورة شامل الضريبة"""
        pass
```

### 4. ✅ استخدم Select Related / Prefetch
```python
# ⚠️ بطيء (N+1 queries)
invoices = Invoice.objects.all()
for inv in invoices:
    print(inv.customer.name)  # query لكل invoice

# ✅ سريع (2 queries فقط)
invoices = Invoice.objects.select_related('customer').all()
```

### 5. ✅ استخدم Pagination
```python
from django.core.paginator import Paginator

paginator = Paginator(queryset, 25)  # 25 per page
page = paginator.get_page(page_number)
```

---

## 📋 قائمة التحقق قبل التعديل

```
□ هل قرأت الكود الموجود أولاً؟
□ هل النمط الذي سأستخدمه موجود في المشروع؟
□ هل أضفت verbose_name بالعربية؟
□ هل استخدمت الموديلات الموجودة بدل إنشاء جديدة؟
□ هل أضفت related_name للـ ForeignKey؟
□ هل اختبرت الكود محلياً؟
□ هل تحققت من عدم وجود أخطاء؟
□ هل الـ migration صحيح؟
```

---

## 📋 قائمة التحقق بعد التعديل

```
□ python manage.py check
□ python manage.py makemigrations
□ python manage.py migrate
□ اختبار الصفحة/API
□ التحقق من logs/error.log
□ التأكد من عدم كسر وظائف موجودة
```

---

## 🔒 الأمان

### ما يجب فحصه
```python
# 1. التحقق من الصلاحيات
@login_required
def my_view(request):
    if not request.user.has_perm('app.can_do_action'):
        raise PermissionDenied

# 2. التحقق من الإدخال
from django.core.validators import validate_email
validate_email(user_input)

# 3. منع SQL Injection
# ❌ خطر
cursor.execute(f"SELECT * FROM table WHERE id = {user_id}")
# ✅ آمن
cursor.execute("SELECT * FROM table WHERE id = %s", [user_id])

# 4. منع XSS
# ❌ خطر
{{ user_input|safe }}
# ✅ آمن (افتراضي)
{{ user_input }}
```

---

## 🗂️ ترتيب الأولويات

### عند إضافة ميزة جديدة
1. ابحث عن ميزة مشابهة موجودة
2. افهم كيف تم تنفيذها
3. استخدم نفس النمط
4. اختبر محلياً
5. تأكد من عدم كسر شيء موجود

### عند إصلاح خطأ
1. افهم سبب الخطأ أولاً
2. ابحث عن حالات مشابهة
3. أصلح السبب الجذري (لا الأعراض)
4. أضف اختبار لمنع تكرار الخطأ
5. وثّق الإصلاح

---

## 🎯 سيناريوهات شائعة

### "أريد إضافة حقل جديد لموديل"
```python
# 1. أضف الحقل في models.py
new_field = models.CharField(max_length=100, null=True, blank=True)

# 2. أنشئ migration
python manage.py makemigrations

# 3. طبّق
python manage.py migrate

# 4. أضف في admin.py إن لزم
# 5. أضف في serializer إن لزم
# 6. أضف في form إن لزم
```

### "أريد إضافة صفحة جديدة"
```python
# 1. أضف View في views.py
class MyView(LoginRequiredMixin, TemplateView):
    template_name = 'app/my_template.html'

# 2. أضف URL في urls.py
path('my-page/', views.MyView.as_view(), name='my-page'),

# 3. أنشئ Template
# app/templates/app/my_template.html
{% extends 'base.html' %}
{% block content %}...{% endblock %}
```

### "أريد إضافة API endpoint"
```python
# 1. أضف Serializer
class MySerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = '__all__'

# 2. أضف ViewSet
class MyViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer

# 3. سجّل في router
router.register('my-endpoint', MyViewSet)
```

---

## 📞 عند الشك

1. **اقرأ الكود الموجود** - الإجابة غالباً موجودة
2. **ابحث عن نمط مشابه** - لا تخترع جديد
3. **اختبر أولاً** - قبل تطبيق أي تغيير
4. **اسأل** - إذا لم تكن متأكداً 100%

---

*هذه القواعد موجودة لحماية النظام والبيانات*

*آخر تحديث: يناير 2026*
