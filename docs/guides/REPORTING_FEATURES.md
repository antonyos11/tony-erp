# دليل واجهات التقارير (Reporting API Guide)

توفر هذه الوثيقة ملخصاً لجميع واجهات التقارير، المعاملات (Query Params) الرئيسية، وخيارات التصدير والضبط الجديدة.

## عام
جميع النقاط تتطلب مستخدماً مصرحاً له بصلاحية `reports.view_reports`، والتصدير يتطلب أيضاً صلاحية `reports.export_reports`.

المعاملات المشتركة:
- `export=csv|xlsx` تصدير البيانات (قوائم) في CSV أو XLSX عند توفرها.
- `stats=1` إرجاع إحصائيات الكاش (hits/misses) ووقت التنفيذ `timing_ms`.
- `force_compress=1` إجبار ضغط gzip لملفات CSV (حتى لو صغيرة)؛ الناتج يحتوي ترويسة `Content-Encoding: gzip`.
- `no_compress=1` تعطيل الضغط التلقائي (للحجم الكبير) عند الحاجة.

## نظرة عامة / المنتجات / المشتريات / النظام الكامل
| Endpoint | وصف | ملاحظات |
|----------|------|---------|
| `/api/reports/overview/` | نظرة عامة (إحصائيات + أفضل المنتجات) | يدعم التصدير لقائمة `top_products` |
| `/api/reports/inventory/` | تقرير المخزون | تصدير `low_stock_products` |
| `/api/reports/sales/` | المبيعات خلال فترة | Params: `date_from`,`date_to`,`customer`,`product` |
| `/api/reports/purchases/` | المشتريات خلال فترة | Params: `date_from`,`date_to`,`supplier` |
| `/api/reports/full/` | لقطة شاملة متعددة الوحدات | خفيفة ووقائية ضد الأخطاء |

## الأرباح والخسائر (P&L)
Endpoint: `/api/reports/profit-loss/`

المعاملات:
- `date_from`,`date_to` نطاق زمني (افتراضي 30 يوم). 
- `cogs_method=approx|fifo|weighted|auto` اختيار طريقة تكلفة البضاعة المباعة (افتراضي auto يحاول FIFO ثم Weighted). 
- `compare=1` حساب الطرق المتاحة كلها لإظهار الفروقات (variance). 
- `warn_threshold=رقم` نسبة مئوية لتفعيل تحذير الانحراف (افتراضي 5%).

حقول إضافية عند تفعيل المقارنة:
- `cogs_fifo`, `cogs_weighted`, `gross_profit_fifo`, `gross_profit_weighted`, `fifo_vs_weighted_cogs_diff`, `fifo_vs_weighted_cogs_percent`, `variance_warning`.

عند وصول الانحراف (absolute percent) إلى مستوى `high` (>=15% افتراضياً) و متجاوز للـ `warn_threshold` يتم إطلاق تنبيه مركزي (سجل + بريد/ويب هوك) عبر `reports.alerts`.

## دوران المخزون (Inventory Turnover)
Endpoint: `/api/reports/inventory-turnover/`

المعاملات مشابهة لـ P&L: `date_from`,`date_to`,`cogs_method`,`compare`,`warn_threshold`.
حقول المقارنة تضيف: `cogs_fifo`, `cogs_weighted`, `turnover_ratio_fifo`, `turnover_ratio_weighted`, الفروقات والنسبة، و `variance_warning`.

## التدفقات النقدية (Cash Flow)
Endpoint: `/api/reports/cash-flow/`
Params: `date_from`,`date_to`,`series=1` (للتسلسل الشهري). يعاد بناء هيكل مقسم (operating/investing/financing) مع الحفاظ على المفاتيح القديمة (`inflows`,`outflows`,`net_cash_flow`).

## أعمار الذمم المدينة / الدائنة
Endpoints:
- `/api/reports/ar-aging/?as_of=YYYY-MM-DD&compare=1`
- `/api/reports/ap-aging/?as_of=YYYY-MM-DD&compare=1`
`compare=1` يضيف فترة سابقة (30 يوم) ويحسب الفروق (`total_outstanding_delta`).

## الميزانية (Balance Sheet)
Endpoint: `/api/reports/balance-sheet/?as_of=YYYY-MM-DD`
قد يعيد `enabled=False` إن كانت حسابات المحاسبة غير مفعلة.

## تآكل المخزون (Stock Aging)
Endpoint: `/api/reports/stock-aging/?as_of=YYYY-MM-DD`
المعاملات:
- `limit=عدد` تحديد أعلى عدد أولي (للأداء). 
- `all=1&export=csv` تصدير كل المنتجات. 
- `page` و `page_size` تفعيل ترقيم الصفحات (لا يُستخدم مع التصدير الكامل).

## السلسلة التاريخية اليومية (Snapshots Series)
Endpoint: `/api/reports/snapshots/?days=N`
يعيد أحدث N (من 7 إلى 365) من `ReportDailySnapshot` مع القيم: `net_revenue`, `expenses`, `cogs_approx`, `cogs_fifo`, `cogs_weighted`, `closing_inventory_value` والفروقات الإجمالية.

تُنشأ اللقطة اليومية تلقائياً عبر مهمة Celery مجدولة (01:10)، ويمكن إنشاؤها يدوياً:
```
python manage.py snapshot_reports --date 2025-08-15  (قديم) 
python manage.py backfill_report_snapshots --days 60  # تعبئة آخر 60 يومًا
```

الاحتفاظ: تحذف اللقطات الأقدم من `REPORT_SNAPSHOT_RETENTION_DAYS` (افتراضي 365 يومًا).

## نقطة الصحة (Health)
Endpoint: `/api/reports/health/` يعيد:
- إحصاءات الكاش (overview / sales / pl).
- `variance_incidents`: عدد حوادث الانحراف العالي (High + متجاوزة العتبة الفعلية) منذ آخر إعادة تشغيل للكاش.
- آخر Snapshot وتقدم عمره (أيام).

مع `stats=1` في أي تقرير ستحصل أيضاً على `timing_ms` (زمن التنفيذ الحالي) و `avg_ms` (متوسط تراكمي تقريبي منذ بدء التشغيل) لتحليل الأداء.

إعادة ضبط العدادات تتم بمسح الكاش (flush) أو تغيير Backend. استخدمها كمؤشرات مبسطة على فعالية التحسينات وجودة دقة التكلفة.

## سجل حوادث الانحراف (Variance Incidents Log)
Endpoint: `/api/reports/variance-incidents/?limit=50`

يعرض أحدث حوادث الانحراف العالية المخزنة في قاعدة البيانات (يتم إنشاء سجل عند حدوث إنذار High متجاوز للعتبة الفعلية). الحقول لكل عنصر:
- `id`
- `created_at`
- `report` (مثال: `profit_loss`)
- `percent` نسبة الانحراف
- `threshold_used` العتبة التي تم تقييم الحادث مقابلها (قد تتأثر بالحد الأدنى العام)
- `global_min_applied` هل تم رفع العتبة بسبب الإعداد العالمي
- `date_from` / `date_to` نطاق التقرير (إن وُجد)
- `extra` بيانات إضافية (قد تتضمن مستويات أو تفاصيل أخرى مستقبلية)

المعاملات:
- `limit` من 1 إلى 500 (افتراضي 50) لتحديد عدد السجلات الراجعة.

ملاحظة: العدّاد `variance_incidents` في Health هو عدّاد ذاكرة (Cache) سريع، بينما هذه الواجهة تمنحك تاريخاً دائماً لأغراض التدقيق والتحليل.

## التصدير والضغط
- تلقائيًا: إذا تجاوزت قائمة CSV 50,000 صف يتم ضغطها (`gzip`).
- إجباري: `force_compress=1`.
- تعطيل: `no_compress=1`.

## تنبيهات الانحراف (Variance Alerts)
عند ارتفاع الفرق بين FIFO و Weighted فوق العتبة ومستوى الخطر العالي:
- يُسجل تحذير في لوجر `reports.variance`.
- يمكن إرسال بريد أو Webhook إذا تم ضبط:
  - `VARIANCE_ALERT_EMAILS=ops@example.com,finance@example.com`
  - `VARIANCE_ALERT_WEBHOOK_URL=https://hooks.example.com/variance`
  - (اختياري) `VARIANCE_ALERT_MIN_PERCENT=10` (لضبط عتبة عامة، بينما `warn_threshold` يظل لكل طلب)

## إعدادات بيئية إضافية
| المتغير | الوصف | الافتراضي |
|---------|-------|-----------|
| `REPORT_SNAPSHOT_RETENTION_DAYS` | أيام الاحتفاظ باللقطات | 365 |
| `VARIANCE_ALERT_EMAILS` | قائمة مستقبلين للتنبيهات | فارغ |
| `VARIANCE_ALERT_WEBHOOK_URL` | عنوان Webhook للتنبيه | فارغ |
| `VARIANCE_ALERT_MIN_PERCENT` | حد أدنى عام أعلى من أي `warn_threshold` طلب | فارغ |

## ملاحظات الأداء
- يتم تخزين نتائج التقارير في الكاش (Redis إن توفر) مع مفاتيح `reports:<prefix>`.
- `stats=1` يوفر نظرة سريعة على فعالية الكاش وزمن التنفيذ.

---
آخر تحديث: تم توليد هذا الدليل تلقائياً عبر المساعد لتغطية المزايا المضافة حتى تاريخه.
