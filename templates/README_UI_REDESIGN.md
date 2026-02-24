# UI Redesign / نظام التصميم الجديد

هذه الوثيقة تشرح عناصر نظام التصميم وخطة الترحيل.

## 1. Design System Tokens
- الألوان الأساسية: primary, secondary, accent, success, info, warning, danger, neutral.
- المسافات: 4 / 8 / 16 / 24 / 32 px عبر المتغيرات (--space-1 .. --space-5)
- التايبوغرافيا: أحجام مخصّصة معتمدة على Bootstrap.
- الأيقونات: Bootstrap Icons.

## 2. هيكلة القوالب
```
templates/
  base.html               # يبقى امتداد لـ base_v2
  base_v2.html            # القالب الأساسي (Bootstrap 5 + RTL)
  includes/
    navbar.html
    sidebar.html          # يستدعي partials/_sidebar.html (من النظام السابق)
    footer.html
    toasts.html
  components/
    card.html
    form_field.html
    table.html
  dashboard.html
  auth_base.html
  registration/
    login.html
    password_reset_form.html
```

## 3. مكوّنات UI
- Card: `components/card.html`
- Form Field: `components/form_field.html`
- Table Wrapper: `components/table.html`
- Toasts: `includes/toasts.html`
- Tabs: `components/tabs.html`
- Modal: `components/modal.html`
- Pagination: `includes/pagination.html`

## 4. دعم RTL/LTR
- الكشف التلقائي من `LANGUAGE_CODE`.
- زر تبديل الاتجاه (dirToggle) يخزن القيمة في localStorage ويحدث رابط Bootstrap (rtl / ltr).

## 5. خطة الترحيل (Phased Migration)
1. استبدال base + إدراج navbar / sidebar / footer (تم).
2. توحيد النماذج: استعمال form_field.html داخل حلقات الحقول.
3. توحيد الجداول: استعمال table.html أو تعديل القوائم التقارير.
4. إدراج المكونات الثانوية (modals, toasts, alerts) وتنظيف CSS قديم.
5. إزالة أي ملفات CSS قديمة متقادمة بعد التأكد من عدم استخدامها.

## 6. إمكانية الوصول
- أزرار التحكم مزودة بـ aria-label.
- عناصر تباين مناسب عبر ألوان Bootstrap.
- دعم لوحة المفاتيح في البحث العالمي والقائمة الجانبية.

## 7. ملاحظات تنفيذية
- لا تغييرات في منطق السيرفر أو البلوكات القديمة، blocks الأساسية بقيت.
- يمكن استدعاء المكوّنات بـ `{% include %}` وتمرير context.
- ينصح بإضافة فحص لحقول النماذج: إذا كان `field.errors` أضف `is-invalid` ديناميكياً (تحسين قادم).

## 8. المستجدات المضافة حديثاً
- إضافة Tabs و Modal و Pagination إلى مجموعة المكوّنات.

## 9. الخطوات التالية (قائمة مختصرة)
1. توحيد شارات الحالات (Status Badges) في include أو فلتر.
2. نقل حساب الإجماليات (JS) إلى ملف مشترك أو سكربت مركزي.
3. تدقيق A11y شامل (aria-label لكل زر حرج، focus states واضحة، تباين عالي).
4. ترقية باقي الوحدات (hr, accounting, maintenance, partners...).
5. دعم Skeleton Loading للبطاقات والجداول (تحسين تجربة المستخدم).

انتهى.
