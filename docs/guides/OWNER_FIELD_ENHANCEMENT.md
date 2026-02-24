# ✅ تحسين حقل "صاحب العملية" في تسجيل القيود

## 📋 الملخص

تم تطوير نظام تسجيل القيود المحاسبية (إيرادات ومنصرفات) ليدعم اختيار "صاحب العملية" من مصادر متعددة بدلاً من الموردين فقط.

## 🎯 الميزات الجديدة

### 1. دعم مصادر متعددة لصاحب العملية

الآن يمكن اختيار صاحب العملية من:
- **موردين** (Suppliers)
- **عملاء** (Customers)
- **سائقين** (Drivers)
- **موظفين** (Employees)

### 2. واجهة مستخدم محسّنة

- قائمة منسدلة لاختيار نوع صاحب العملية
- قائمة ثانية تتحدث ديناميكياً بناءً على النوع المختار
- تحميل البيانات عبر AJAX لسرعة الأداء

### 3. التوافق مع البيانات القديمة

- تم الحفاظ على حقل المورد القديم للتوافق
- يعمل النظام مع القيود القديمة والجديدة
- لا حاجة لتحديث البيانات القديمة

## 🔧 التعديلات التقنية

### 1. النماذج (Models)

**ملف**: `accounting/models.py`

```python
# إضافة حقول GenericForeignKey
owner_content_type = models.ForeignKey(ContentType, ...)
owner_object_id = models.PositiveIntegerField(...)
owner = GenericForeignKey('owner_content_type', 'owner_object_id')

# خاصية للحصول على اسم صاحب العملية
@property
def owner_name(self):
    if self.owner:
        return getattr(self.owner, 'name', None) or getattr(self.owner, 'full_name', str(self.owner))
    elif self.supplier:  # التوافق مع الحقل القديم
        return self.supplier.name
    return None
```

### 2. العروض (Views)

**ملف**: `accounting/views.py`

#### تحديث `revenue_create` و `expense_create`

```python
# معالجة صاحب العملية
owner_type = request.POST.get('owner_type')
owner_id = request.POST.get('owner_id')

model_map = {
    'supplier': ('partners', 'Supplier'),
    'customer': ('crm', 'Customer'),
    'driver': ('fleet', 'Driver'),
    'employee': ('hr', 'Employee'),
}

if owner_type in model_map:
    app_label, model_name = model_map[owner_type]
    owner_content_type = ContentType.objects.get(app_label=app_label, model=model_name.lower())
    owner_object_id = int(owner_id)
```

#### إضافة `get_owner_options` (AJAX Endpoint)

```python
@login_required
def get_owner_options(request):
    """جلب خيارات صاحب العملية بناءً على النوع"""
    owner_type = request.GET.get('type', '')
    
    if owner_type == 'supplier':
        suppliers = Supplier.objects.all().order_by('name')[:500]
        options = [{'id': s.id, 'name': s.name} for s in suppliers]
    
    # ... وهكذا لباقي الأنواع
    
    return JsonResponse({'success': True, 'options': options})
```

### 3. القوالب (Templates)

**ملف**: `accounting/templates/accounting/account_entry_form.html`

```html
<!-- صاحب العملية (مورد، عميل، سائق، إلخ) -->
<div class="col-md-12">
    <label class="form-label fw-bold">صاحب العملية</label>
    <div class="row g-2">
        <div class="col-md-4">
            <select name="owner_type" id="ownerTypeSelect" class="form-select">
                <option value="">-- اختر النوع --</option>
                <option value="supplier">مورد</option>
                <option value="customer">عميل</option>
                <option value="driver">سائق</option>
                <option value="employee">موظف</option>
            </select>
        </div>
        <div class="col-md-8">
            <select name="owner_id" id="ownerIdSelect" class="form-select" disabled>
                <option value="">-- اختر النوع أولاً --</option>
            </select>
        </div>
    </div>
</div>
```

### 4. JavaScript للتفاعل

```javascript
ownerTypeSelect.addEventListener('change', function() {
    const selectedType = this.value;
    
    fetch(`{% url 'accounting:get_owner_options' %}?type=${selectedType}`)
        .then(response => response.json())
        .then(data => {
            ownerIdSelect.innerHTML = '<option value="">-- اختياري --</option>';
            data.options.forEach(option => {
                const opt = document.createElement('option');
                opt.value = option.id;
                opt.textContent = option.name;
                ownerIdSelect.appendChild(opt);
            });
            ownerIdSelect.disabled = false;
        });
});
```

### 5. التقارير

تم تحديث `supplier_revenue_report` لعرض جميع أنواع أصحاب العمليات:

```python
# جلب القيود التي لها صاحب عملية من النظام الجديد
entries_with_owner = AccountEntry.objects.filter(
    owner_content_type__isnull=False,
    owner_object_id__isnull=False
)

# معالجة القيود القديمة للتوافق
old_suppliers = Supplier.objects.filter(
    revenue_entries__owner_content_type__isnull=True
)
```

## 📁 الملفات المعدلة

1. ✅ `accounting/models.py` - إضافة حقول GenericForeignKey
2. ✅ `accounting/views.py` - تحديث revenue_create و expense_create و إضافة get_owner_options
3. ✅ `accounting/urls.py` - إضافة URL للـ endpoint الجديد
4. ✅ `accounting/templates/accounting/account_entry_form.html` - واجهة المستخدم الجديدة
5. ✅ `accounting/migrations/0029_add_generic_owner_to_accountentry.py` - Migration جديد

## 🔄 Migration

```bash
python manage.py makemigrations accounting
python manage.py migrate
```

## 🧪 الاختبار

### 1. إنشاء قيد إيراد جديد

1. انتقل إلى: المحاسبة > تسجيل إيراد جديد
2. اختر نوع صاحب العملية (مثلاً: عميل)
3. اختر العميل من القائمة
4. أكمل باقي البيانات واحفظ

### 2. عرض التقارير

1. انتقل إلى: المحاسبة > تقارير > تقرير الإيرادات حسب أصحاب العمليات
2. حدد نطاق التاريخ
3. شاهد التقرير الشامل لجميع أنواع أصحاب العمليات

## 📊 قاعدة البيانات

### الحقول الجديدة في `AccountEntry`

| الحقل | النوع | الوصف |
|------|------|-------|
| `owner_content_type` | ForeignKey | نوع الكيان (ContentType) |
| `owner_object_id` | PositiveIntegerField | معرف الكيان |
| `owner` | GenericForeignKey | المرجع العام للكيان |
| `supplier` | ForeignKey (قديم) | محفوظ للتوافق |

### الفهارس (Indexes)

```python
models.Index(fields=['owner_content_type', 'owner_object_id'])
```

## 🎨 مثال على الاستخدام

### في Python

```python
from accounting.models import AccountEntry
from partners.models import Supplier
from crm.models import Customer
from django.contrib.contenttypes.models import ContentType

# إنشاء قيد بمورد
supplier = Supplier.objects.first()
entry1 = AccountEntry.objects.create(
    entry_type='revenue',
    owner=supplier,
    amount=1000,
    # ... باقي الحقول
)

# إنشاء قيد بعميل
customer = Customer.objects.first()
entry2 = AccountEntry.objects.create(
    entry_type='revenue',
    owner=customer,
    amount=2000,
    # ... باقي الحقول
)

# الحصول على اسم صاحب العملية
print(entry1.owner_name)  # اسم المورد
print(entry2.owner_name)  # اسم العميل
```

### في القوالب

```django
{% for entry in entries %}
    <tr>
        <td>{{ entry.date }}</td>
        <td>{{ entry.amount }}</td>
        <td>{{ entry.owner_name|default:"--" }}</td>
        <td>{{ entry.owner_content_type.name|default:"--" }}</td>
    </tr>
{% endfor %}
```

## 🚀 المزايا

1. **مرونة أكبر**: يمكن ربط القيد بأي نوع من الكيانات
2. **تتبع أفضل**: معرفة مصدر كل قيد بدقة
3. **تقارير أشمل**: تقارير تشمل جميع أنواع أصحاب العمليات
4. **قابلية التوسع**: سهولة إضافة أنواع جديدة في المستقبل
5. **التوافق**: يعمل مع البيانات القديمة دون مشاكل

## 📝 ملاحظات

- الحقل اختياري ويمكن ترك "صاحب العملية" فارغاً
- يعمل مع الإيرادات والمنصرفات
- التقارير تدعم النظامين القديم والجديد
- سرعة التحميل محسّنة عبر AJAX

## 🔮 التطويرات المستقبلية

1. إضافة أنواع جديدة (مشاريع، عقود، إلخ)
2. تحسين واجهة التقارير لعرض نوع صاحب العملية
3. إضافة فلاتر متقدمة حسب نوع صاحب العملية
4. إنشاء لوحة معلومات تحليلية للأصحاب

---

**تاريخ التحديث**: 9 يناير 2026
**المطور**: GitHub Copilot
**الحالة**: ✅ مكتمل ومختبر
