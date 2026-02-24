# دليل استخدام Autosave و Conflict Detection
## الحفظ التلقائي وكشف التعارضات

---

## 📚 المحتويات
1. [نظرة عامة](#نظرة-عامة)
2. [كيفية الاستخدام](#كيفية-الاستخدام)
3. [أمثلة عملية](#أمثلة-عملية)
4. [API Reference](#api-reference)
5. [استكشاف الأخطاء](#استكشاف-الأخطاء)

---

## نظرة عامة

نظام Autosave يوفر:
- ✅ حفظ تلقائي للمسودات كل 30 ثانية
- ✅ استرجاع المسودات عند فتح النموذج
- ✅ كشف التعارضات عند التحرير المتزامن
- ✅ قفل التحرير لمنع التعديلات المتضاربة
- ✅ مؤشرات بصرية للحفظ

---

## كيفية الاستخدام

### 1. إضافة إلى القالب HTML

```html
{% extends "base.html" %}
{% load static %}

{% block extra_js %}
<script src="{% static 'js/autosave.js' %}"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    // تفعيل autosave للنموذج
    const autosave = new AutosaveManager({
        model: 'invoice',                           // اسم النموذج
        instanceId: '{{ invoice.id|default:"new" }}', // ID السجل أو "new"
        formSelector: '#invoice-form',              // معرف النموذج
        interval: 30000,                            // الحفظ كل 30 ثانية
        
        // callbacks اختيارية
        onSaved: function() {
            console.log('✓ تم الحفظ التلقائي');
        },
        onError: function(error) {
            console.error('خطأ في الحفظ:', error);
        },
        onConflict: function(userName) {
            alert(`تحذير: ${userName} يقوم بتحرير هذا السجل الآن`);
        }
    });
    
    // حفظ المرجع لاستخدامه لاحقاً
    window.autosaveManager = autosave;
});
</script>
{% endblock %}
```

### 2. هيكل النموذج المطلوب

```html
<form id="invoice-form" method="post">
    {% csrf_token %}
    
    <!-- حقول النموذج -->
    {{ form.as_p }}
    
    <button type="submit">حفظ</button>
</form>
```

---

## أمثلة عملية

### مثال 1: نموذج فاتورة

**Template: sales/invoice_form.html**
```html
{% extends "base.html" %}
{% load static %}

{% block content %}
<h2>{% if invoice.id %}تعديل{% else %}إنشاء{% endif %} فاتورة</h2>

<form id="invoice-form" method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">حفظ الفاتورة</button>
</form>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/autosave.js' %}"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    new AutosaveManager({
        model: 'invoice',
        instanceId: '{{ invoice.id|default:"new" }}',
        formSelector: '#invoice-form',
        interval: 30000,
        onSaved: function() {
            // إظهار رسالة نجاح (اختياري - المكتبة تعرض مؤشر تلقائي)
            console.log('Invoice autosaved');
        }
    });
});
</script>
{% endblock %}
```

### مثال 2: عرض أسعار CRM

**Template: crm/quotation_form.html**
```html
{% extends "base.html" %}
{% load static %}

{% block content %}
<h2>عرض أسعار جديد</h2>

<form id="quotation-form" method="post">
    {% csrf_token %}
    {{ form.as_p }}
    
    <!-- نموذج فرعي للعناصر -->
    <div id="quotation-items">
        {{ formset.management_form }}
        {% for item_form in formset %}
            <div class="quotation-item">
                {{ item_form.as_p }}
            </div>
        {% endfor %}
    </div>
    
    <button type="submit">حفظ العرض</button>
</form>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/autosave.js' %}"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const autosave = new AutosaveManager({
        model: 'quotation',
        instanceId: '{{ quotation.id|default:"new" }}',
        formSelector: '#quotation-form',
        interval: 30000,
        onConflict: function(userName) {
            // إظهار modal تحذيري
            $('#conflict-modal')
                .find('.conflict-user').text(userName).end()
                .modal('show');
        }
    });
});
</script>
{% endblock %}
```

### مثال 3: فرصة بيع CRM

**Template: crm/opportunity_form.html**
```html
{% extends "base.html" %}
{% load static %}

{% block content %}
<div class="card">
    <div class="card-header">
        <h3>فرصة بيع جديدة</h3>
        <span id="autosave-status" class="badge badge-secondary">
            جاري التحميل...
        </span>
    </div>
    <div class="card-body">
        <form id="opportunity-form" method="post">
            {% csrf_token %}
            {{ form.as_p }}
            <button type="submit" class="btn btn-success">حفظ الفرصة</button>
        </form>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/autosave.js' %}"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const statusBadge = document.getElementById('autosave-status');
    
    new AutosaveManager({
        model: 'opportunity',
        instanceId: '{{ opportunity.id|default:"new" }}',
        formSelector: '#opportunity-form',
        interval: 30000,
        onSaved: function() {
            statusBadge.className = 'badge badge-success';
            statusBadge.textContent = '✓ محفوظ تلقائياً';
            setTimeout(() => {
                statusBadge.className = 'badge badge-secondary';
                statusBadge.textContent = 'جاهز';
            }, 2000);
        },
        onError: function(error) {
            statusBadge.className = 'badge badge-danger';
            statusBadge.textContent = '✗ خطأ في الحفظ';
        }
    });
});
</script>
{% endblock %}
```

---

## API Reference

### AutosaveManager Class

#### Constructor Options

```javascript
new AutosaveManager({
    model: String,          // REQUIRED: اسم النموذج (invoice, quotation, opportunity)
    instanceId: String,     // ID السجل أو "new" للسجلات الجديدة
    formSelector: String,   // REQUIRED: CSS selector للنموذج
    interval: Number,       // مدة الحفظ بالميلي ثانية (default: 30000 = 30s)
    onSaved: Function,      // callback عند الحفظ الناجح
    onError: Function,      // callback عند حدوث خطأ
    onConflict: Function    // callback عند اكتشاف تعارض
})
```

#### Methods

```javascript
// الحفظ اليدوي
autosave.save()

// مسح المسودة
autosave.clearDraft()

// إيقاف الحفظ التلقائي
autosave.stopAutosave()

// بدء الحفظ التلقائي
autosave.startAutosave()

// إطلاق القفل
autosave.releaseLock()

// تدمير المدير (cleanup)
autosave.destroy()
```

### REST API Endpoints

#### 1. حفظ المسودة
```http
POST /api/autosave/draft/
Content-Type: application/json

{
    "model": "invoice",
    "instance_id": "123",
    "data": {
        "customer": "1",
        "total": "1000",
        "notes": "ملاحظات..."
    }
}

Response 200:
{
    "success": true,
    "message": "تم الحفظ التلقائي بنجاح"
}
```

#### 2. استرجاع المسودة
```http
GET /api/autosave/draft/load/?model=invoice&instance_id=123

Response 200:
{
    "success": true,
    "data": {
        "customer": "1",
        "total": "1000",
        "notes": "ملاحظات..."
    },
    "saved_at": "2026-01-18 10:30:45"
}
```

#### 3. مسح المسودة
```http
DELETE /api/autosave/draft/clear/?model=invoice&instance_id=123

Response 200:
{
    "success": true,
    "message": "تم حذف المسودة"
}
```

#### 4. الحصول على قفل التحرير
```http
POST /api/autosave/lock/
Content-Type: application/json

{
    "model": "invoice",
    "instance_id": "123"
}

Response 200 (نجح):
{
    "success": true,
    "message": "تم الحصول على قفل التحرير"
}

Response 409 (تعارض):
{
    "success": false,
    "locked_by": "أحمد محمد",
    "message": "السجل قيد التحرير من قبل مستخدم آخر"
}
```

#### 5. تحرير القفل
```http
DELETE /api/autosave/lock/release/?model=invoice&instance_id=123

Response 200:
{
    "success": true,
    "message": "تم تحرير القفل"
}
```

---

## استكشاف الأخطاء

### المشكلة: الحفظ التلقائي لا يعمل

**الحلول:**
1. تحقق من تضمين `autosave.js`:
```html
<script src="{% static 'js/autosave.js' %}"></script>
```

2. تحقق من CSRF token:
```html
{% csrf_token %}
```

3. تحقق من console للأخطاء:
```javascript
console.log('AutosaveManager loaded:', window.AutosaveManager);
```

### المشكلة: لا تظهر المسودات المحفوظة

**الحلول:**
1. تحقق من Django cache:
```bash
python3 manage.py shell
>>> from django.core.cache import cache
>>> cache.get('autosave:1:invoice:123')
```

2. تأكد من تكوين cache في settings.py:
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```

### المشكلة: تعارضات لا تُكتشف

**الحلول:**
1. تحقق من timeout القفل (5 دقائق):
```python
# في autosave_service.py
timeout = 300  # 5 minutes
```

2. تأكد من تحرير القفل عند الخروج:
```javascript
window.addEventListener('beforeunload', () => {
    autosave.releaseLock();
});
```

### المشكلة: رسالة "Permission Denied"

**الحلول:**
1. تأكد من تسجيل دخول المستخدم
2. تحقق من decorators:
```python
@permission_classes([IsAuthenticated])
```

---

## أمثلة متقدمة

### مثال 4: نموذج مع Formsets

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const autosave = new AutosaveManager({
        model: 'invoice',
        instanceId: '{{ invoice.id|default:"new" }}',
        formSelector: '#invoice-form',
        interval: 30000
    });
    
    // حفظ عند إضافة/حذف صف من formset
    document.querySelectorAll('.add-row, .delete-row').forEach(btn => {
        btn.addEventListener('click', function() {
            setTimeout(() => autosave.save(), 500);
        });
    });
});
```

### مثال 5: تكامل مع Modal

```javascript
// عند فتح modal التعديل
$('#editModal').on('show.bs.modal', function() {
    window.modalAutosave = new AutosaveManager({
        model: 'quotation',
        instanceId: $(this).data('quotation-id'),
        formSelector: '#modal-form',
        onConflict: function(userName) {
            $('#editModal').modal('hide');
            alert(`السجل قيد التحرير بواسطة: ${userName}`);
        }
    });
});

// عند إغلاق modal
$('#editModal').on('hide.bs.modal', function() {
    if (window.modalAutosave) {
        window.modalAutosave.destroy();
        window.modalAutosave = null;
    }
});
```

---

## الخلاصة

نظام Autosave يوفر:
- ✅ حماية من فقدان البيانات
- ✅ تجربة مستخدم أفضل
- ✅ كشف وحل التعارضات
- ✅ سهولة التكامل
- ✅ دعم كامل للعربية RTL

للمزيد من المعلومات، راجع:
- `core/services/autosave_service.py` - Backend service
- `core/api/autosave_views.py` - API endpoints
- `static/js/autosave.js` - Frontend implementation

---

**تم بحمد الله ✨**
