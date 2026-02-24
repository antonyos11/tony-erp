# 🎨 نظام التصميم العصري - Tony ERP v2.0

## نظرة عامة

تم إنشاء نظام قوالب عصري ومتجاوب بالكامل لجميع صفحات النظام. يتضمن:

- ✅ **تصميم Glassmorphism** حديث
- ✅ **تجاوب كامل** للموبايل والتابلت
- ✅ **ألوان متدرجة** لكل وحدة
- ✅ **انتقالات سلسة** وميكرو-تفاعلات
- ✅ **وضع ليلي/نهاري** تلقائي
- ✅ **RTL/LTR** دعم كامل

---

## 📁 الملفات الجديدة

```
static/css/
├── modern_pages.css          # ملف التصميم الرئيسي

templates/base_templates/
├── modern_list.html          # قالب صفحات القوائم
├── modern_detail.html        # قالب صفحات التفاصيل
├── modern_form.html          # قالب صفحات النماذج
├── modern_dashboard.html     # قالب لوحات المعلومات
└── _list_professional.html   # (محدث) للتوافقية
```

---

## 🚀 كيفية استخدام القوالب

### 1️⃣ صفحة قائمة (List Page)

```django
{% extends 'base_templates/modern_list.html' %}
{% load i18n %}

{% block page_module %}partners{% endblock %}
{% block page_icon %}bi-people-fill{% endblock %}
{% block page_title %}{% trans 'إدارة الشركاء' %}{% endblock %}
{% block page_subtitle %}{% trans 'العملاء والموردين' %}{% endblock %}

{% block hero_actions %}
<a href="{% url 'partners:create' %}" class="mp-btn mp-btn--primary mp-btn--lg">
    <i class="bi bi-plus-lg"></i> {% trans 'إضافة' %}
</a>
{% endblock %}

{% block hero_stats %}
<div class="mp-hero-stats">
    <div class="mp-hero-stat">
        <div class="mp-hero-stat-value">{{ total }}</div>
        <div class="mp-hero-stat-label">{% trans 'الإجمالي' %}</div>
    </div>
</div>
{% endblock %}

{% block table_headers %}
<th>#</th>
<th>{% trans 'الاسم' %}</th>
<th>{% trans 'الحالة' %}</th>
<th>{% trans 'الإجراءات' %}</th>
{% endblock %}

{% block table_body %}
{% for item in items %}
<tr>
    <td>{{ forloop.counter }}</td>
    <td>
        <div class="mp-entity">
            <div class="mp-avatar mp-avatar--sm">{{ item.name|slice:":1" }}</div>
            <div class="mp-entity-info">
                <a href="{{ item.get_absolute_url }}" class="mp-entity-name">{{ item.name }}</a>
            </div>
        </div>
    </td>
    <td>
        <span class="mp-badge mp-badge--success mp-badge--dot">{% trans 'نشط' %}</span>
    </td>
    <td>
        <div class="mp-actions">
            <a href="#" class="mp-action-btn mp-action-btn--view"><i class="bi bi-eye"></i></a>
            <a href="#" class="mp-action-btn mp-action-btn--edit"><i class="bi bi-pencil"></i></a>
        </div>
    </td>
</tr>
{% endfor %}
{% endblock %}
```

### 2️⃣ صفحة تفاصيل (Detail Page)

```django
{% extends 'base_templates/modern_detail.html' %}
{% load i18n %}

{% block page_module %}partners{% endblock %}
{% block page_icon %}bi-person{% endblock %}
{% block page_title %}{% trans 'تفاصيل الشريك' %}{% endblock %}

{% block hero_actions %}
<a href="{% url 'partners:edit' object.pk %}" class="mp-btn mp-btn--outline" style="color:white;">
    <i class="bi bi-pencil"></i> {% trans 'تعديل' %}
</a>
{% endblock %}

{% block detail_title %}{{ object.name }}{% endblock %}
{% block detail_subtitle %}{{ object.code }}{% endblock %}

{% block detail_badges %}
<span class="mp-badge mp-badge--info">{% trans 'عميل' %}</span>
{% endblock %}

{% block detail_fields %}
<div class="mp-detail-field">
    <span class="mp-detail-field-label">{% trans 'الهاتف' %}</span>
    <span class="mp-detail-field-value">{{ object.phone }}</span>
</div>
<div class="mp-detail-field">
    <span class="mp-detail-field-label">{% trans 'البريد' %}</span>
    <span class="mp-detail-field-value">{{ object.email }}</span>
</div>
{% endblock %}
```

### 3️⃣ صفحة نموذج (Form Page)

```django
{% extends 'base_templates/modern_form.html' %}
{% load i18n %}

{% block page_module %}partners{% endblock %}
{% block page_icon %}bi-person-plus{% endblock %}
{% block page_title %}{% trans 'إضافة شريك' %}{% endblock %}

{% block form_fields %}
<div class="mp-form-group">
    <label class="mp-form-label">{% trans 'الاسم' %} <span class="required">*</span></label>
    <input type="text" name="name" class="mp-form-input" required>
</div>
<div class="mp-form-group">
    <label class="mp-form-label">{% trans 'الهاتف' %}</label>
    <input type="tel" name="phone" class="mp-form-input">
</div>
{% endblock %}
```

---

## 🎨 ألوان الوحدات (Modules)

| الوحدة | الكلاس | اللون |
|--------|--------|-------|
| الشركاء | `mp-hero--partners` | بنفسجي |
| المبيعات | `mp-hero--sales` | أخضر |
| المخزون | `mp-hero--inventory` | برتقالي |
| المشتريات | `mp-hero--purchases` | أزرق |
| المحاسبة | `mp-hero--accounting` | بنفسجي داكن |
| الموارد البشرية | `mp-hero--hr` | وردي |
| الأسطول | `mp-hero--fleet` | فيروزي |
| الإنتاج | `mp-hero--production` | برتقالي داكن |
| المشاريع | `mp-hero--projects` | بنفسجي فاتح |
| CRM | `mp-hero--crm` | سماوي |
| الصيانة | `mp-hero--maintenance` | رمادي |

---

## 📱 التجاوب

### نقاط التوقف (Breakpoints)

| الحجم | العرض | التأثير |
|-------|-------|---------|
| Desktop | > 1200px | عرض كامل |
| Tablet | 768px - 1199px | تقليص الأعمدة |
| Mobile L | 576px - 767px | تحويل الجدول لبطاقات |
| Mobile S | < 576px | عرض عمود واحد |

### عرض الجدول على الموبايل

الجداول تتحول تلقائياً لبطاقات على الشاشات الصغيرة:
- أضف `data-label` لكل خلية
- أو استخدم JavaScript المضمن للتحويل التلقائي

---

## 🔧 الكلاسات المتاحة

### الأزرار

```html
<button class="mp-btn mp-btn--primary">أساسي</button>
<button class="mp-btn mp-btn--success">نجاح</button>
<button class="mp-btn mp-btn--accent">مميز</button>
<button class="mp-btn mp-btn--outline">مفرغ</button>
<button class="mp-btn mp-btn--ghost">شفاف</button>

<!-- الأحجام -->
<button class="mp-btn mp-btn--sm">صغير</button>
<button class="mp-btn mp-btn--lg">كبير</button>
```

### الشارات (Badges)

```html
<span class="mp-badge mp-badge--primary">أساسي</span>
<span class="mp-badge mp-badge--success mp-badge--dot">نجاح</span>
<span class="mp-badge mp-badge--warning">تحذير</span>
<span class="mp-badge mp-badge--danger">خطر</span>
```

### الحالات (Status)

```html
<span class="mp-status mp-status--active">نشط</span>
<span class="mp-status mp-status--inactive">غير نشط</span>
<span class="mp-status mp-status--pending">قيد الانتظار</span>
```

### الأفاتار

```html
<div class="mp-avatar">A</div>
<div class="mp-avatar mp-avatar--sm">B</div>
<div class="mp-avatar mp-avatar--lg">C</div>
<div class="mp-avatar mp-avatar--circle">D</div>
```

### أزرار الإجراءات

```html
<div class="mp-actions">
    <a class="mp-action-btn mp-action-btn--view"><i class="bi bi-eye"></i></a>
    <a class="mp-action-btn mp-action-btn--edit"><i class="bi bi-pencil"></i></a>
    <a class="mp-action-btn mp-action-btn--delete"><i class="bi bi-trash"></i></a>
</div>
```

---

## 📋 قائمة الصفحات المحدثة

### ✅ تم تحديثها

1. partners/partners_list.html
2. partners/suppliers_list.html
3. sales/invoice_list.html (via _list_professional.html)

### 🔄 تحتاج تحديث

استخدم الأمر التالي لحصر الصفحات:

```bash
find templates -name "*_list.html" -o -name "*list.html" | wc -l
```

---

## 🌙 الوضع الليلي

يتم دعم الوضع الليلي تلقائياً عبر:
```css
[data-theme="dark"] .mp-xxx { ... }
```

---

## 🖨️ الطباعة

يتم إخفاء العناصر غير الضرورية تلقائياً:
- الفلاتر
- أزرار الإجراءات
- شريط التنقل

---

## 📞 الدعم

للمزيد من المعلومات أو الاستفسارات، راجع:
- static/css/design_system.css
- static/css/modern_pages.css
