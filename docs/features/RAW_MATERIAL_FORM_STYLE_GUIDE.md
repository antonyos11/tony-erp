# 🎨 دليل الألوان والأنماط - صفحة المواد الخام

## 🎨 لوحة الألوان الرئيسية

### ألوان التدرج (Gradients)

#### 1. البنفسجي (للموردين والمواد)
```css
background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
```
- **الاستخدام**: عنوان قسم المواد المتاحة، badges الوحدات
- **الألوان البديلة للتركيز**: `#4338ca`, `#6d28d9`

#### 2. الأخضر (للنجاح والاختيار)
```css
background: linear-gradient(135deg, #10b981 0%, #059669 100%);
```
- **الاستخدام**: المادة المختارة، زر النجاح، السعر
- **اللون الفاتح**: `#d1fae5`, `#a7f3d0`

#### 3. الأزرق السماوي (للحسابات)
```css
background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
```
- **الاستخدام**: حاسبة التحويل البصرية
- **اللون الداكن**: `#0ea5e9`

#### 4. الأصفر (للتسعير)
```css
background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
```
- **الاستخدام**: قسم التسعير والتكلفة
- **اللون الرئيسي**: `#fbbf24`

---

## 🔤 أحجام الخطوط

### حقول الإدخال
```css
.input-group-lg .form-control {
  font-size: 1.1rem;    /* الحقول الكبيرة */
  font-weight: 500;     /* وزن متوسط */
}

#usageUnitCostDisplay {
  font-size: 1.5rem;    /* الحقل الأكبر (التكلفة) */
  font-weight: bold;
  color: #10b981;
}
```

### العناوين
```css
h4 {
  font-weight: 700;
  color: #1f2937;
}

h5 {
  font-weight: bold;
}
```

### النصوص المساعدة
```css
small {
  font-size: 0.875rem;
  color: #6b7280;
}
```

---

## 📐 المسافات والأحجام

### Border Radius
```css
.form-section { border-radius: 16px; }      /* الأقسام */
.material-item { border-radius: 12px; }     /* بطاقات المواد */
.badge { border-radius: 8px; }              /* الشارات */
.btn { border-radius: 0.375rem; }           /* الأزرار */
```

### Shadows
```css
/* خفيف */
box-shadow: 0 2px 12px rgba(0,0,0,0.08);

/* متوسط */
box-shadow: 0 4px 20px rgba(0,0,0,0.12);

/* قوي */
box-shadow: 0 8px 32px rgba(16, 185, 129, 0.3);

/* مع اللون */
box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
```

### Padding
```css
.form-section { padding: 24px; }
.material-item { padding: 16px 20px; }
.badge { padding: 0.4em 0.8em; }
```

---

## ⚡ التأثيرات والانتقالات

### Hover Effects
```css
.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.material-item:hover {
  transform: translateX(-8px) translateY(-2px);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.2);
}
```

### Transitions
```css
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

### Animations
```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
```

---

## 🎯 أنماط خاصة بالعناصر

### Material Items (بطاقات المواد)
```css
.material-item {
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.material-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  background: linear-gradient(180deg, #4f46e5 0%, #7c3aed 100%);
}

.material-item:hover {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
}

.material-item.selected {
  border-color: #10b981;
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}
```

### Scrollbar
```css
#supplierMaterialsList::-webkit-scrollbar {
  width: 10px;
}

#supplierMaterialsList::-webkit-scrollbar-track {
  background: #f3f4f6;
  border-radius: 10px;
}

#supplierMaterialsList::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #4f46e5 0%, #7c3aed 100%);
  border-radius: 10px;
  border: 2px solid #f3f4f6;
}
```

---

## 🎭 أيقونات Bootstrap

### الأيقونات المستخدمة
```html
<!-- الموردين -->
<i class="bi bi-truck-front-fill"></i>
<i class="bi bi-building"></i>
<i class="bi bi-star-fill"></i>

<!-- المواد -->
<i class="bi bi-box-seam-fill"></i>
<i class="bi bi-box-fill"></i>
<i class="bi bi-check-circle-fill"></i>

<!-- الباركود -->
<i class="bi bi-upc-scan"></i>
<i class="bi bi-barcode"></i>
<i class="bi bi-printer"></i>

<!-- التسعير -->
<i class="bi bi-calculator-fill"></i>
<i class="bi bi-cash-stack"></i>
<i class="bi bi-arrow-left-right"></i>

<!-- أنواع المواد -->
<i class="bi bi-box-fill"></i>        <!-- إسفنج -->
<i class="bi bi-layers-fill"></i>     <!-- باد -->
<i class="bi bi-droplet-fill"></i>    <!-- غراء -->
<i class="bi bi-grid-3x3-gap-fill"></i> <!-- أقمشة -->
<i class="bi bi-cloud-fill"></i>      <!-- فيبر -->
<i class="bi bi-bezier2"></i>         <!-- خيوط -->
```

---

## 📱 التجاوب (Responsive)

### Grid Classes المستخدمة
```html
<!-- 4 أعمدة في الشاشات الكبيرة -->
<div class="col-lg-3 col-md-4 col-6">

<!-- 3 أعمدة في الشاشات المتوسطة -->
<div class="col-md-4 col-6">

<!-- عمودين في الموبايل -->
<div class="col-6">
```

---

## 🎨 Backdrop Filter
```css
.element {
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(10px);
}
```
**الاستخدام**: البطاقات الشفافة في قسم المادة المختارة

---

## 🔍 نصائح التطوير

### 1. إضافة عنصر جديد قابل للنقر
```css
.clickable-element {
  cursor: pointer;
  transition: all 0.3s ease;
}

.clickable-element:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
```

### 2. إضافة تدرج لوني جديد
```css
background: linear-gradient(135deg, #startColor 0%, #endColor 100%);
```

### 3. إضافة حدود ملونة
```css
border: 2px solid #color;
border-left: 4px solid #accentColor;
```

---

## 📊 CSS Variables (للمستقبل)
يمكن تحويل الألوان إلى متغيرات:

```css
:root {
  --primary: #4f46e5;
  --primary-dark: #4338ca;
  --success: #10b981;
  --success-light: #d1fae5;
  --warning: #fbbf24;
  --info: #3b82f6;
  
  --shadow-sm: 0 2px 12px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 20px rgba(0,0,0,0.12);
  --shadow-lg: 0 8px 32px rgba(0,0,0,0.2);
  
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
}
```

---

تم إعداد هذا الدليل للتسهيل على المطورين 🚀
