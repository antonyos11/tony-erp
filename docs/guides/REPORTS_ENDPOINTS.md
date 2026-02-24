# REST Reporting Endpoints

يوضح هذا الملف جميع واجهات التقارير الحالية (READ‑only) مع الصلاحيات وخيارات التصدير.

## صلاحيات الوصول
- العرض (قراءة التقارير): requires permission: `reports.view_reports` (أو superuser)
- التصدير (CSV/XLSX): requires permission: `reports.export_reports` (أو superuser)

إذا طُلب التصدير دون امتلاك صلاحية التصدير يتم إرجاع 403.

## ملاحظات عامة
- جميع الطرق: `GET`
- وسيطات التواريخ: تنسيق `YYYY-MM-DD`
- وسيطة التصدير: `?export=csv` أو `?export=xlsx`
- وسيطة بديلة مقبولة: `?format=csv` (للانسجام مع بعض العملاء)
- التخزين المؤقت (cache) داخلي لكل تقرير، مفاتيح تبدأ بـ `reports:`.
- في حال تحديد نطاق تاريخ معكوس (date_to < date_from) يعود 400.

## قائمة التقارير

### 1. Overview
`/api/reports/overview/`
- لا يوجد بارامترات إجبارية.
- الاستجابة: إحصائيات عامة (منتجات، عملاء، ...)، أفضل المنتجات، مخططات.
- التصدير: يعيد قائمة top_products فقط (ملف واحد) إذا استُخدم export.

### 2. Full System Snapshot
`/api/reports/full/`
- التجميع العام متعدد الوحدات (overview + inventory slice + sales/purchases slices + accounting + crm + hr)
- التصدير: أفضل المنتجات من قسم overview.

### 3. Sales Report
`/api/reports/sales/?date_from=...&date_to=...&customer=<id>&product=<id>`
- date_from/date_to (افتراضي آخر 30 يومًا).
- customer, product (اختياري أرقام صحيحة).
- التصدير: قائمة top_products.

### 4. Inventory Report
`/api/reports/inventory/`
- يعرض تحليلات المخزون، المنتجات منخفضة المخزون، إلخ.
- التصدير: قائمة low_stock_products.

### 5. Purchases Report
`/api/reports/purchases/?date_from=...&date_to=...&supplier=<id>`
- date_from/date_to (افتراضي آخر 30 يومًا).
- supplier (اختياري).
- التصدير: قائمة top_suppliers.

### 6. Profit & Loss
`/api/reports/profit-loss/?date_from=...&date_to=...&cogs_method=fifo|approx`
- الحقول الحالية:
	- `revenue`, `discounts`, `net_revenue`
	- `cogs` (تقريبي اعتماداً على product.cost الحالي)
	- `cogs_fifo` (دقة أعلى باستخدام طبقات المخزون FIFO إن توفرت StockBatch)
	- `cogs_method`: يوضح المنهج المستخدم فعلياً (`fifo` أو `approx` عند الفشل)
	- `gross_profit`, `operating_profit`, `margin_percent` (مبني على COGS التقريبي)
	- `gross_profit_fifo`, `operating_profit_fifo`, `margin_percent_fifo` (مبني على COGS FIFO)
	- `expenses`
- في حال عدم توفر بيانات كافية أو حدوث استثناء أثناء حساب FIFO يتم الرجوع تلقائياً إلى الطريقة التقريبية بدون فشل.
- التصدير: صف واحد يلخص القيم الأساسية (قد لا يتضمن كل الحقول الثانوية حسب محول التصدير الحالي).

### 7. Accounts Receivable Aging (AR)
`/api/reports/ar-aging/?as_of=YYYY-MM-DD`
- as_of (افتراضي اليوم).
- التصدير: قائمة customers مع توزيع الأعمار.

### 8. Accounts Payable Aging (AP)
`/api/reports/ap-aging/?as_of=YYYY-MM-DD`
- as_of (افتراضي اليوم).
- التصدير: قائمة suppliers.

### 9. CRM Pipeline
`/api/reports/crm-pipeline/`
- يعرض المراحل، القيم المفتوحة، القيم الرابحة والخاسرة، معدل الفوز.
- التصدير: قائمة stages.

### 10. Balance Sheet (مبسّط)
`/api/reports/balance-sheet/?as_of=YYYY-MM-DD`
- إذا لم تكن تطبيقات الحسابات مفعّلة: returns {'enabled': False}.
- الحقول الإضافية: `is_balanced` (قيمة منطقية) و `difference` (الفرق) مع بقاء `check` للتوافق.
- لا يوجد تصدير (مخرجات مركبة متعددة القوائم).

### 11. Cash Flow (مجزأ)
`/api/reports/cash-flow/?date_from=...&date_to=...`
- تقسيم إلى: `operating`, `investing`, `financing` مع احتفاظ بالمفاتيح القديمة `inflows`, `outflows`, `net_cash_flow`.
- تم دمج قروض (Loan) مبدئياً: صرف القرض ضمن تدفقات تمويلية داخلة، وسداد أصل القرض (LoanPayment.principal_portion) تدفقات تمويلية خارجة.
- التصدير: صف واحد (summary) يعتمد الشكل القديم.

### 12. Inventory Turnover
`/api/reports/inventory-turnover/?date_from=...&date_to=...&cogs_method=fifo|approx`
- الحقول:
	- `cogs_approx`: COGS تقريبي (product.cost الحالي)
	- `cogs_fifo`: COGS تاريخي باستخدام FIFO (إن أمكن)
	- `cogs_method`: المنهج النشط (`fifo` أو `approx`)
	- `average_inventory_value_proxy`: القيمة الحالية كممثل تقريبي (الحل القديم)
	- `opening_inventory_estimate`: تقدير افتتاحي مشتق: closing + cogs_fifo - purchases_value خلال الفترة
	- `average_inventory_fifo_based`: متوسط محسوب (opening_est + closing)/2 لتحسين دقة معدل الدوران
	- `turnover_ratio`: المعدل التقريبي (يعتمد على cogs_approx)
	- `turnover_ratio_fifo`: المعدل الأدق باستخدام FIFO + متوسط جديد
	- `days_in_period`, `days_per_turn`, `days_per_turn_fifo`
	- `notes`
- في حالة عدم وجود مبيعات/مشتريات يعاد معظم القيم بصفر و`days_per_turn*` تكون `null`.
- التصدير: صف واحد (قد يركز على الحقول الأساسية؛ يمكن توسيعه مستقبلاً).

### 13. Stock Aging
`/api/reports/stock-aging/?as_of=YYYY-MM-DD&limit=<n>&all=1`
- تجميع حسب آخر حركة (بيع أو شراء) باستخدام Subquery وتقسيم سلال: 0-30 / 31-60 / 61-90 / 90+ / بدون حركة.
- `limit`: اختياري لتقييد عدد المنتجات (الافتراضي 300 داخلياً).
- عند التصدير مع `all=1` وغياب limit يتم إرجاع كل النتائج بدون قص (قد يكون كبيراً) ويوسَم `limit_applied: "all"`.
- التصدير: قائمة products بعد تطبيق limit أو كاملة إذا all=1.

## أكواد الأخطاء الشائعة
- 400: تنسيق تاريخ غير صالح أو نطاق مقلوب.
- 403: نقص صلاحية (عرض أو تصدير).
- 404 / 406: لم تعد متوقعة في بيئة مستقرة؛ أزيل التسامح في الاختبارات وتم توحيد السلوك.

## تحسينات مستقبلية مقترحة
- دقة COGS تاريخية (طبقات تكلفة FIFO / Weighted Average من StockBatch).
- متوسط مخزون تاريخي (لقطات افتتاح/إقفال) بدل القيمة الحالية.
- معاملات أصول ثابتة في قسم الاستثمار (شراء/بيع) + فائدة القرض في قسم التمويل.
- فلاتر إضافية (موقع، فئة، مركز تكلفة، نطاق قيمة).
- تحسين تصدير stock-aging للسماح بتقسيم دفعات (pagination export) عند البيانات الكبيرة.

---
English summary available on request.
---

## English Summary

### Permissions
| Action | Permission | Notes |
|--------|------------|-------|
| View reports | `reports.view_reports` | Superusers bypass |
| Export CSV/XLSX | `reports.export_reports` | Requires view + export |

If export is requested without export permission: HTTP 403.

### General
All endpoints are GET. Date params use `YYYY-MM-DD`. Export via `?export=csv` or `?export=xlsx` (alias: `?format=csv`). Per‑report caching under key prefix `reports:`. `400` for invalid date ranges.

### Endpoints
1. Overview: `/api/reports/overview/` – dashboard stats; export: top_products list.
2. Full snapshot: `/api/reports/full/` – combined multi‑module; export: overview top products.
3. Sales: `/api/reports/sales/?date_from&date_to&customer&product` – export: top_products.
4. Inventory: `/api/reports/inventory/` – export: low_stock_products.
5. Purchases: `/api/reports/purchases/?date_from&date_to&supplier` – export: top_suppliers.
6. Profit & Loss: `/api/reports/profit-loss/?date_from&date_to&cogs_method=` – يشمل حقول FIFO (`cogs_fifo`, `gross_profit_fifo`, ...) و `cogs_method`; export: single summary row.
7. AR Aging: `/api/reports/ar-aging/?as_of=` – export: customers aging rows.
8. AP Aging: `/api/reports/ap-aging/?as_of=` – export: suppliers aging rows.
9. CRM Pipeline: `/api/reports/crm-pipeline/` – export: stages.
10. Balance Sheet: `/api/reports/balance-sheet/?as_of=` – adds is_balanced & difference; no export.
11. Cash Flow: `/api/reports/cash-flow/?date_from&date_to` – segmented (operating/investing/financing) + legacy keys; export: legacy single summary row.
12. Inventory Turnover: `/api/reports/inventory-turnover/?date_from&date_to&cogs_method=` – يحتوي أيضاً على حقول FIFO المحسّنة (`cogs_fifo`, `opening_inventory_estimate`, `average_inventory_fifo_based`, `turnover_ratio_fifo`, `days_per_turn_fifo`); export: single summary row.
13. Stock Aging: `/api/reports/stock-aging/?as_of=&limit=&all=1` – export: products (cap ~300 unless limit or all=1 for full list).

### Common Error Codes
400 invalid dates; 403 missing permission; 404/406 no longer expected post‑stabilization.

### Future Improvements
- Historical COGS layer costing.
- True average inventory snapshots.
- Fixed asset & financing enrichment for segmented cash flow (beyond loans principal currently captured).
- Extended filters (location, category, cost center).

