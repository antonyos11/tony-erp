# دليل المطور - السايدبار

## 🎯 نظرة عامة

هذا الدليل موجه للمطورين الذين يريدون تعديل أو إضافة عناصر للسايدبار.

## 📂 هيكل الملفات

```
tony_erp/
├── templates/
│   └── partials/
│       └── _sidebar.html          # الهيكل الأساسي
├── static/
│   └── css/
│       ├── sidebar_fix.css        # التنسيقات الأساسية
│       └── sidebar_enhanced.css   # التحسينات البصرية
└── docs/
    ├── SIDEBAR_ORGANIZATION.md    # التوثيق
    ├── SIDEBAR_COMPARISON.md      # المقارنة
    └── SIDEBAR_DEVELOPER_GUIDE.md # هذا الملف
```

## 🔧 إضافة عنصر جديد

### 1. رابط بسيط

```html
<li>
  <a href="{% url 'app:view_name' %}" class="sidebar-link">
    <i class="bi bi-icon-name"></i>
    <span>اسم العنصر</span>
  </a>
</li>
```

### 2. رابط مع صلاحيات

```html
{% if perms.app.permission_name %}
  <li>
    <a href="{% url 'app:view_name' %}" class="sidebar-link">
      <i class="bi bi-icon-name"></i>
      <span>اسم العنصر</span>
    </a>
  </li>
{% endif %}
```

### 3. قائمة منسدلة

```html
<li class="sidebar-group">
  <button class="sidebar-collapse-btn" 
          data-bs-toggle="collapse" 
          data-bs-target="#sectionId" 
          aria-expanded="false">
    <i class="bi bi-icon-name"></i>
    <span>اسم القسم</span>
    <i class="bi bi-chevron-down toggle-icon ms-auto"></i>
  </button>
  <ul class="sidebar-submenu collapse" id="sectionId">
    <li>
      <a href="{% url 'app:view1' %}" class="submenu-link">
        <i class="bi bi-circle-fill"></i>
        <span>عنصر فرعي 1</span>
      </a>
    </li>
    <li>
      <a href="{% url 'app:view2' %}" class="submenu-link">
        <i class="bi bi-circle-fill"></i>
        <span>عنصر فرعي 2</span>
      </a>
    </li>
  </ul>
</li>
```

## 🎨 إضافة قسم جديد

### 1. عنوان القسم

```html
<li class="sidebar-section text-uppercase small fw-semibold px-3 mt-3" 
    style="background: linear-gradient(90deg, #color1, #color2); 
           -webkit-background-clip: text; 
           -webkit-text-fill-color: transparent;">
  🎯 اسم القسم
</li>
```

### 2. اختيار الألوان

استخدم ألوان Gradient متناسقة:

```css
/* أمثلة على الألوان */
#3b82f6 → #8b5cf6  /* أزرق → بنفسجي */
#f59e0b → #f97316  /* برتقالي */
#10b981 → #06b6d4  /* أخضر → سماوي */
#ec4899 → #f43f5e  /* وردي → أحمر */
```

### 3. اختيار الأيقونة

استخدم أيقونات Bootstrap Icons:

```html
<!-- أمثلة -->
<i class="bi bi-house-door"></i>      <!-- الرئيسية -->
<i class="bi bi-lightning"></i>       <!-- سريع -->
<i class="bi bi-box"></i>             <!-- صندوق -->
<i class="bi bi-gear"></i>            <!-- إعدادات -->
<i class="bi bi-graph-up"></i>        <!-- تقارير -->
<i class="bi bi-people"></i>          <!-- مستخدمين -->
```

## 🎨 تخصيص التنسيقات

### 1. تعديل الألوان

في `sidebar_enhanced.css`:

```css
.sidebar-link.active {
  background: linear-gradient(135deg, 
    rgba(13, 110, 253, 0.15) 0%, 
    rgba(13, 202, 240, 0.1) 100%) !important;
  border-right: 3px solid var(--bs-primary, #0d6efd) !important;
}
```

### 2. تعديل التأثيرات

```css
.sidebar-link:hover {
  transform: translateX(-3px) !important;
  background: rgba(255, 255, 255, 0.08) !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
}
```

### 3. تعديل الأحجام

```css
.sidebar-link {
  padding: 0.6rem 0.9rem !important;
  font-size: 0.875rem !important;
  border-radius: 8px !important;
}
```

## 🔍 البحث والفلترة

### إضافة بحث لقسم معين

```javascript
// في نهاية _sidebar.html
const searchInput = document.getElementById('sectionSearch');
searchInput.addEventListener('input', function() {
  const query = this.value.toLowerCase();
  const items = document.querySelectorAll('.sidebar-link');
  
  items.forEach(item => {
    const text = item.textContent.toLowerCase();
    item.closest('li').style.display = 
      text.includes(query) ? '' : 'none';
  });
});
```

## 📱 الاستجابة (Responsive)

### 1. إخفاء عناصر على الموبايل

```html
<li class="d-none d-md-block">
  <!-- يظهر فقط على الشاشات المتوسطة وأكبر -->
</li>
```

### 2. تغيير الترتيب على الموبايل

```html
<li class="order-1 order-md-2">
  <!-- ترتيب مختلف على الموبايل -->
</li>
```

## 🌐 دعم RTL/LTR

### 1. محاذاة النص

```css
html[dir="rtl"] .sidebar-link {
  text-align: right !important;
}

html[dir="ltr"] .sidebar-link {
  text-align: left !important;
}
```

### 2. موضع الأيقونات

```css
html[dir="rtl"] .sidebar-link i {
  margin-left: 0.5rem !important;
  margin-right: 0 !important;
}

html[dir="ltr"] .sidebar-link i {
  margin-right: 0.5rem !important;
  margin-left: 0 !important;
}
```

## 🐛 حل المشاكل الشائعة

### 1. العنصر لا يظهر

```python
# تحقق من الصلاحيات
{% if perms.app.view_permission %}
  <!-- العنصر -->
{% endif %}
```

### 2. الألوان لا تظهر

```css
/* تأكد من استخدام !important */
color: #3b82f6 !important;
```

### 3. التأثيرات لا تعمل

```css
/* تأكد من إضافة transition */
transition: all 0.2s ease !important;
```

## 📊 أفضل الممارسات

### 1. التنظيم
- ✅ ضع العناصر المتشابهة في قسم واحد
- ✅ استخدم أسماء واضحة ومعبرة
- ✅ رتب العناصر حسب الأهمية

### 2. الأداء
- ✅ قلل عدد العناصر قدر الإمكان
- ✅ استخدم lazy loading للصور
- ✅ تجنب JavaScript الثقيل

### 3. الوصول
- ✅ استخدم aria-label للأيقونات
- ✅ استخدم aria-expanded للقوائم المنسدلة
- ✅ تأكد من إمكانية التنقل بلوحة المفاتيح

### 4. التوافق
- ✅ اختبر على متصفحات مختلفة
- ✅ اختبر على أجهزة مختلفة
- ✅ تأكد من دعم RTL/LTR

## 🔄 التحديثات المستقبلية

عند إضافة ميزات جديدة:

1. أضف العنصر في القسم المناسب
2. حدّث التوثيق
3. اختبر على جميع المتصفحات
4. تأكد من الصلاحيات
5. حدّث CHANGELOG

## 📞 الدعم

للمساعدة أو الاستفسارات:
- راجع التوثيق في `docs/`
- تحقق من الأمثلة في `_sidebar.html`
- اتصل بفريق التطوير

---

**آخر تحديث**: 2026-01-13  
**الإصدار**: 2.0.0  
**المطور**: Tony ERP Team

