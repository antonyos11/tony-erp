# دليل التقارير المالية والتشغيلية

هذا الدليل يشرح أهم واجهات (API) وطرق حساب تكلفة البضاعة (COGS) بعد إضافة الطريقة الجديدة weighted.

## 1. طرق حساب تكلفة البضاعة المباعة (COGS)

| الطريقة | قيمة `cogs_method` في الاستعلام | الوصف | الأداء | الدقة |
|---------|----------------------------------|-------|--------|-------|
| تقريبية | approx | تعتمد السعر/التكلفة الحالية (بدون محاكاة تاريخية) | عالي جدًا | أقل |
| المتوسط المرجح | weighted | (Opening Value + Purchases Value) / (Opening Qty + Purchased Qty) ثم تضرب في الكمية المباعة | عالي | متوسطة - جيدة |
| وارد أولاً | fifo | يحاكي تفريغ الدُفعات تاريخيًا (أول دفعة أولاً) | أبطأ | عالية |
| تلقائي | (فارغ / auto) | يختار أفضل المتاح (يفضل fifo ثم weighted ثم approx) | يعتمد | يعتمد |

مثال طلب:
```
/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&cogs_method=weighted
```
القيمة الفارغة أو `auto` تعني دع النظام يقرر.

## 2. حقول المخرجات حسب الطريقة

P&L:
- Approx: `cogs`, `gross_profit`, `operating_profit`, `margin_percent`
- FIFO: `cogs_fifo`, `gross_profit_fifo`, `operating_profit_fifo`, `margin_percent_fifo`
- Weighted: `cogs_weighted`, `gross_profit_weighted`, `operating_profit_weighted`, `margin_percent_weighted`
- دائمًا: `cogs_method` لبيان الطريقة المستخدمة.

Inventory Turnover:
- مشتركة: `turnover_ratio`, `days_per_turn`
- FIFO إضافية: `turnover_ratio_fifo`, `days_per_turn_fifo`
- Weighted إضافية: `turnover_ratio_weighted`, `days_per_turn_weighted`

### المقارنة بين الطرق (Compare)
عند إضافة `&compare=1` إلى طلب P&L أو Inventory Turnover في وضع (auto أو أي وضع) سيقوم النظام بمحاولة حساب الطريقتين FIFO و Weighted معًا (إن أمكن) وإرجاع فروقات:

حقول الفروقات في P&L:
`fifo_vs_weighted_cogs_diff`, `fifo_vs_weighted_cogs_percent`, `fifo_vs_weighted_gross_profit_diff`

حقول الفروقات في Inventory Turnover:
`fifo_vs_weighted_cogs_diff`, `fifo_vs_weighted_cogs_percent`

مثال:
```
/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&compare=1
```

## 3. مثال JSON مختصر (Weighted)
```json
{
  "cogs_method": "weighted",
  "net_revenue": 125000.0,
  "cogs_weighted": 72000.0,
  "gross_profit_weighted": 53000.0,
  "operating_profit_weighted": 48000.0,
  "margin_percent_weighted": 42.4
}
```

## 4. اختيار تلقائي (Auto Selection)
الاختيار التلقائي يحاول:
1. FIFO إن توفرت بيانات دفعات كافية.
2. وإلا Weighted إذا توافرت مشتريات ضمن الفترة أو قيمة افتتاحية معتبرة.
3. وإلا Approx كحل أسرع افتراضي.

## 5. التصدير
أضف `?export=csv` أو `?format=xlsx` (إن توفر openpyxl) لمعظم التقارير. يلزم صلاحية التصدير.

عند استخدام `compare=1` مع التصدير ستتضمن الصفوف (إن وُجدت) أعمدة الفروقات المذكورة أعلاه تلقائيًا.

## 6. حدود الأداء
- استخدم نطاقات تاريخ أصغر للتجارب الأولى عند تفعيل fifo.
- الكاش مفعل لكل تقرير بمفتاح يعتمد على (الفترة + الطريقة).
- يمكن تمرير `stats=1` لعرض عدادات hits/misses للكاش.

### إحصائيات زمن التنفيذ (Timing)
عند تمرير `stats=1` تتم إضافة حقلين:
```json
"cache_stats": {"hits": 3, "misses": 1},
"timing_ms": 12.47
```
timing_ms هو الزمن الكلي (تقريبي) لتنفيذ الطلب داخل طبقة الـ View بالـ milliseconds ويشمل الحسابات قبل الإرسال. مفيد للمقارنة بين الطرق (fifo vs weighted) مع نفس نطاق التاريخ.

ملاحظات:
- العدادات تراكمية لكل نوع تقرير (prefix) داخل الكاش.
- reset يتم فقط بانتهاء صلاحية الكاش أو مسحه يدويًا.
- يستحسن تجاهل timing_ms في البيئات ذات الحمل المنخفض عند التحليل، لأنها قد تتذبذب.

## 7. إضافة طرق مستقبلية
يمكن لاحقًا إضافة LIFO أو Standard Cost بمكان واضح داخل `reports/services.py` في فروع اختيار COGS.

---
آخر تحديث: 2025-08-16

## 8. قائمة التقارير في الواجهة (Unified Reports Navigation)

تم توحيد جميع التقارير التشغيلية والمالية تحت وحدة واحدة (التقارير) في الشريط الجانبي مع التقسيم التالي:

1. تقارير عامة:
  - تقرير المبيعات (تحليل العملاء والمنتجات واتجاه المبيعات)
  - تقرير المخزون (حالة ومستويات وقيمة وتحركات حديثة)
  - تقرير المشتريات (أفضل الموردين والمنتجات المشتراة)
2. التقارير المالية (محاسبة):
  - دفتر الأستاذ العام
  - ميزان المراجعة
  - الميزانية العمومية
  - قائمة الدخل
  - قائمة التدفقات النقدية
3. تقارير المخزون المتخصصة:
  - ملخص المخزون
  - تقييم المخزون
  - أقدمية المخزون
4. تقارير CRM والمبيعات المتقدمة:
  - تقرير العمولات
  - اتجاه العمولات (شهري)
  - اتجاه قبول العروض (شهري)
5. تقارير الأسطول:
  - أداء السائقين

كل صفحة تقرير تعرض الآن كتلة أزرار قياسية (جزئي `reports/partials/report_actions.html`) تشمل:
`CSV`، `Excel`، و زر الطباعة. يمكن إعادة استخدام الجزئي في أي تقرير جديد.

للاستخدام في قالب جديد:
```django
{% include 'reports/partials/report_actions.html' %}
```

ولعرض جدول بسيط ديناميكي:
```django
{% include 'reports/partials/report_table.html' with columns=cols rows=rows %}
```

حيث `cols` قائمة عناوين و `rows` قائمة صفوف (قوائم أو tuples).

