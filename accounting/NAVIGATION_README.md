# دمج قائمة المحاسبة الجديدة

## 1. التضمين في القالب الأساسي
ضع في `base.html` (أو القالب الذي يحتوي الـ layout):
```django
{% include 'partials/navigation.html' %}
```

يفضل وضعها داخل عنصر جانبي:
```html
<aside class="sidebar sidebar--accounting">
  {% include 'partials/navigation.html' %}
</aside>
```

## 2. تنشيط الأيقونات
استعمل نظام الأيقونات لديك. النموذج الحالي يضيف `icon-<name>`.
مثال CSS سريع:
```css
.acc-nav__icon { width:1.2rem; display:inline-block; }
```

## 3. الشارات (Badges)
الحقل `badge` في الكائن يعرض `--` مؤقتاً. لتغذية الأرقام:

تم الآن تفعيل شارة `draft_journal_count` فعلياً عبر `navigation_context` وتحسب عدد القيود غير المرحلة (`is_posted=False`).

## 4. الاختصارات (Shortcuts)

تضمن الملف الحالي `static/js/nav.js` اختصار قيد جديد (Ctrl+Alt+J) ويمكن توسيعه.
يمكن تعريف مستمع مفاتيح عام في JS:
```js
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'j') {
    window.location.href = '/accounting/journal/new';
  }
});
```

حاليًا: القيمة تأتي مباشرة من قاعدة البيانات (`JournalEntry.objects.filter(is_posted=False).count()`).

### API ديناميكي للشارات
Endpoint: `GET /accounting/api/badges/`

القيم الحالية (قد تتوسع):
```json
{
  "draft_journal_count": 3,
  "unposted_journal_entries_count": 3,
  "pending_purchase_orders_count": 5,
  "ts": "2025-09-16T10:10:00Z"
}
```
ملاحظات:
- `unposted_journal_entries_count` مجرد اسم متوافق مع النظام القديم لنفس قيمة `draft_journal_count`.
- يوجد Cache داخلي لمدة 15 ثانية (in‑process). عدِّلها لاحقاً إلى Redis عند الحاجة.
- ملف `static/js/nav.js`:
  - يجري تحديثاً أولياً عند التحميل.
  - ينفّذ تحديثاً دورياً كل 60 ثانية (يمكن تعطيله بحذف المؤقت `__accBadgesInterval`).
  - يخفي الشارة إذا كانت القيمة رقمية <= 0.

لإضافة شارة جديدة في الواجهة:
1. أضف المفتاح في JSON الذي ترجعه `badges_view`.
2. ضع عنصر `<span class="badge ..." data-badge-key="your_key">--</span>` داخل العنصر المستهدف.
3. (اختياري) إن كانت القيمة تحتاج استعلام ثقيل استعمل caching خاص بها أو ضمها في نفس الكاش العام.

## 5. الصلاحيات
تم وضع أسماء صلاحيات تقريبية (مثل `accounting.add_journalentry`). عدّلها لتطابق الموديلات الفعلية أو استبدلها بقائمة منطقية. لو أردت تعطيل التحقق مؤقتاً أعد كتابة `is_allowed` ليعيد True دائماً.

## 6. تحسينات مستقبلية
- Cache للقائمة لكل مستخدم (Redis) مع مفتاح يعتمد على آخر تحديث صلاحيات.
- دعم تخصيص المستخدم (Pinned Items) بتخزين تفضيل في جدول.
- دعم ترجمة ديناميكية: حالياً النصوص عربية ثابتة؛ إن رغبت، مرِّرها بـ `gettext_lazy`.
 - تعليق التحديث الدوري عند عدم ظهور الصفحة (`document.hidden`) لتقليل الضغط.
 - استخدام ETag أو `If-None-Match` لاحقاً لتقليل حجم الرد (حالياً JSON صغير).

## 9. البحث الفوري
حقل البحث أعلى القائمة يقوم بفلترة العناصر (client-side) ويخفي الأقسام الفارغة. اختصار: `Ctrl+Alt+F` للتركيز السريع.

## 10. طي الأقسام
يمكن النقر على عنوان القسم أو الضغط Enter/Space لطيّه. الحالة تُخزَّن في `localStorage` المفتاح `accNav.collapsed`.

## 11. العناصر المثبّتة (Pinned)
زر نجمة (★) بجوار كل عنصر يضيف/يزيل المفتاح في `localStorage` (`accNav.pins`). يتم عرض قسم "المثبتة" تلقائياً عند وجود عناصر. اختصار: `Ctrl+Alt+P` يقفز لأول عنصر مثبت (في حالة وجوده).

## 12. الشارات الجديدة
أضيفت مفاتيح:
- `aging_receivables_count`: عدد العملاء بذمم متأخرة (>30 يوم) (تقدير مبني على نموذج الفواتير إن توفّر).
- `aging_payables_pending`: عدد الموردين بفواتير متأخرة.
- `bank_reconcile_pending`: عدد الحسابات البنكية بها معاملات غير مسوّاة.
تظهر تلقائياً إن وُضعت كـ `badge` في العنصر داخل `navigation.py`.

## 13. الاختصارات الحالية
- `Ctrl+Alt+J`: قيد جديد.
- `Ctrl+Alt+D`: صفحة قيود مسودة.
- `Ctrl+Alt+F`: تركيز البحث.
- `Ctrl+Alt+P`: التركيز على أول عنصر مثبت.

## 14. ملاحظات أداء
- استعلامات الشارات تعتمد كاش 15 ثانية. في حال ثِقَل استعلامات aging يُنصح بنقلها لـ Materialized View أو جدول تلخيص محدث دوريّاً.
- يمكن استخراج جزء الشارات إلى خدمة خفيفة (API micro endpoint) أو Celery task تُحدّث جدولا وسيطاً.

## 7. اختبار سريع
1. أنشئ مستخدم بصلاحيات محدودة.
2. تأكد من إخفاء العناصر غير المصرح بها.
3. أضف قيمة اختبار: في view:
```python
request.draft_journal_count = 3
```
وشاهد الشارة تتغير (بعد تعديل القالب لجلب القيمة من request).

## 8. ملاحظات
القائمة حالياً مستقلة داخل تطبيق `accounting`. إذا رغبت في دمج بقية الوحدات أنشئ ملف مركزي في `core/navigation.py` واستورد Sections إضافية.
