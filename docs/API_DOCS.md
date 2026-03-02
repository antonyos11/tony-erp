# RITA ERP — توثيق API
## API_DOCS.md — v2.0

---

## نظرة عامة

RITA ERP يوفر REST API كاملاً مبنياً بـ Django REST Framework.
توثيق تفاعلي بـ Swagger UI متاح على: `GET /api/schema/swagger-ui/`

---

## المصادقة

### Session Authentication
```
POST /auth/login/
Content-Type: application/x-www-form-urlencoded

username=user&password=pass
```

### Token Authentication
```
POST /api/auth/token/
Content-Type: application/json

{"username": "user", "password": "pass"}

Response: {"token": "abc123..."}
```

استخدام الـ Token:
```
Authorization: Token abc123...
```

---

## نقاط النهاية (Endpoints)

### المخزون / Inventory

| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET    | `/api/inventory/products/` | قائمة المنتجات |
| POST   | `/api/inventory/products/` | إنشاء منتج |
| GET    | `/api/inventory/products/{id}/` | تفاصيل منتج |
| PUT    | `/api/inventory/products/{id}/` | تعديل منتج |
| DELETE | `/api/inventory/products/{id}/` | حذف منتج |
| GET    | `/api/inventory/stock/` | مستويات المخزون |
| GET    | `/api/inventory/categories/` | الفئات |

### المبيعات / Sales

| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET    | `/api/sales/invoices/` | فواتير البيع |
| POST   | `/api/sales/invoices/` | إنشاء فاتورة |
| GET    | `/api/sales/invoices/{id}/` | تفاصيل فاتورة |
| GET    | `/api/sales/customers/` | العملاء |
| POST   | `/api/sales/customers/` | إضافة عميل |

### المشتريات / Purchases

| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET    | `/api/purchases/orders/` | أوامر الشراء |
| POST   | `/api/purchases/orders/` | إنشاء أمر |
| GET    | `/api/purchases/suppliers/` | الموردون |

### الإنتاج / Production

| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET    | `/api/production/orders/` | أوامر الإنتاج |
| POST   | `/api/production/orders/` | إنشاء أمر |
| GET    | `/api/production/lines/` | خطوط الإنتاج |

### المحاسبة / Accounts

| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET    | `/api/accounts/accounts/` | دليل الحسابات |
| GET    | `/api/accounts/journals/` | القيود اليومية |
| POST   | `/api/accounts/journals/` | إنشاء قيد |
| GET    | `/api/accounts/trial-balance/` | ميزان المراجعة |

### الموارد البشرية / HR

| Method | Endpoint | الوصف |
|--------|----------|-------|
| GET    | `/api/hr/employees/` | الموظفون |
| GET    | `/api/hr/payroll/` | الرواتب |

---

## الفلترة والبحث

كل endpoint يدعم:

```
GET /api/sales/invoices/?search=محمد
GET /api/sales/invoices/?customer=5&date_from=2024-01-01
GET /api/inventory/products/?category=3&ordering=-created_at
GET /api/inventory/products/?page=2&page_size=50
```

**الحقول المدعومة:**
- `search` — بحث نصي
- `ordering` — ترتيب (يدعم `-` للترتيب التنازلي)
- `page` — رقم الصفحة
- `page_size` — حجم الصفحة (افتراضي: 20، أقصى: 100)

---

## صيغة الاستجابة

### قائمة (Paginated)
```json
{
  "count": 150,
  "next": "http://example.com/api/products/?page=3",
  "previous": "http://example.com/api/products/?page=1",
  "results": [...]
}
```

### رسالة خطأ
```json
{
  "detail": "وصف الخطأ",
  "code": "permission_denied",
  "status": 403
}
```

---

## Webhook Events (Sprint 25)

الأحداث المتاحة للاشتراك:
- `sales.invoice.created`
- `sales.invoice.approved`
- `production.order.completed`
- `inventory.stock.low`

---

## أكواد الاستجابة

| الكود | المعنى |
|-------|--------|
| 200   | نجاح |
| 201   | تم الإنشاء |
| 400   | خطأ في البيانات |
| 401   | غير مصادَق |
| 403   | لا صلاحية |
| 404   | غير موجود |
| 429   | تجاوز الحد (Brute Force) |
| 500   | خطأ في السيرفر |

---

## Swagger UI

الواجهة التفاعلية الكاملة:
```
GET /api/schema/swagger-ui/
GET /api/schema/redoc/
GET /api/schema/        # OpenAPI JSON
```

---

*RITA ERP API v2.0 — Sprint 25*
