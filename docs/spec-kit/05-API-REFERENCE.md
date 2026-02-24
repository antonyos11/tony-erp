# 🔌 05 - مرجع واجهات برمجة التطبيقات (API Reference)

## 📋 نظرة عامة

النظام يوفر **RESTful API** شاملة باستخدام **Django REST Framework** مع أكثر من **5,300 نقطة وصول (endpoints)**.

---

## 🔐 المصادقة (Authentication)

### JWT Authentication

```http
POST /api/token/
Content-Type: application/json

{
    "username": "admin",
    "password": "password123"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### استخدام التوكن

```http
GET /api/v1/products/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### تجديد التوكن

```http
POST /api/token/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

## 📦 Core APIs

### Products API

#### قائمة المنتجات
```http
GET /api/v1/products/
```

**Parameters:**
| المعامل | النوع | الوصف |
|---------|-------|-------|
| search | string | بحث بالاسم أو الكود |
| category | integer | فلترة بالفئة |
| is_active | boolean | المنتجات النشطة فقط |
| page | integer | رقم الصفحة |
| page_size | integer | عدد العناصر بالصفحة |

**Response:**
```json
{
    "count": 1250,
    "next": "/api/v1/products/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "منتج تجريبي",
            "sku": "PROD-001",
            "barcode": "1234567890123",
            "category": {
                "id": 1,
                "name": "إلكترونيات"
            },
            "cost_price": "100.00",
            "sale_price": "150.00",
            "stock_quantity": 50,
            "is_active": true
        }
    ]
}
```

#### إنشاء منتج
```http
POST /api/v1/products/
Content-Type: application/json

{
    "name": "منتج جديد",
    "sku": "PROD-002",
    "category": 1,
    "cost_price": "80.00",
    "sale_price": "120.00"
}
```

#### تحديث منتج
```http
PUT /api/v1/products/{id}/
PATCH /api/v1/products/{id}/
```

#### حذف منتج
```http
DELETE /api/v1/products/{id}/
```

---

### Customers API

#### قائمة العملاء
```http
GET /api/v1/customers/
```

**Parameters:**
| المعامل | النوع | الوصف |
|---------|-------|-------|
| search | string | بحث بالاسم أو الهاتف |
| customer_type | integer | نوع العميل |
| has_balance | boolean | العملاء الذين لديهم رصيد |

#### إنشاء عميل
```http
POST /api/v1/customers/
Content-Type: application/json

{
    "name": "شركة ABC",
    "email": "info@abc.com",
    "phone": "+966501234567",
    "tax_number": "300000000000003",
    "credit_limit": "50000.00"
}
```

---

### Invoices API

#### إنشاء فاتورة
```http
POST /api/v1/invoices/
Content-Type: application/json

{
    "customer": 1,
    "date": "2026-01-08",
    "due_date": "2026-02-08",
    "items": [
        {
            "product": 1,
            "quantity": 5,
            "unit_price": "150.00",
            "discount": "0.00"
        },
        {
            "product": 2,
            "quantity": 3,
            "unit_price": "200.00",
            "discount": "10.00"
        }
    ],
    "notes": "ملاحظات الفاتورة"
}
```

**Response:**
```json
{
    "id": 1001,
    "invoice_number": "INV-2026-001001",
    "customer": {
        "id": 1,
        "name": "شركة ABC"
    },
    "date": "2026-01-08",
    "subtotal": "1350.00",
    "tax_amount": "202.50",
    "discount": "10.00",
    "total": "1542.50",
    "status": "draft",
    "items": [...]
}
```

#### عمليات الفاتورة
```http
POST /api/v1/invoices/{id}/confirm/      # تأكيد
POST /api/v1/invoices/{id}/cancel/       # إلغاء
POST /api/v1/invoices/{id}/add_payment/  # إضافة دفعة
GET  /api/v1/invoices/{id}/pdf/          # تحميل PDF
```

---

### Inventory API

#### حركة المخزون
```http
GET /api/v1/stock/
GET /api/v1/stock/movements/
```

#### تحويل مخزون
```http
POST /api/v1/stock/transfers/
Content-Type: application/json

{
    "from_location": 1,
    "to_location": 2,
    "items": [
        {"product": 1, "quantity": 10},
        {"product": 2, "quantity": 5}
    ],
    "notes": "تحويل بين المستودعات"
}
```

---

## 💼 CRM APIs

### Opportunities API

```http
GET    /api/v1/crm/opportunities/
POST   /api/v1/crm/opportunities/
GET    /api/v1/crm/opportunities/{id}/
PUT    /api/v1/crm/opportunities/{id}/
DELETE /api/v1/crm/opportunities/{id}/
POST   /api/v1/crm/opportunities/{id}/move_stage/
POST   /api/v1/crm/opportunities/{id}/convert_to_sale/
```

### Activities API

```http
GET    /api/v1/crm/activities/
POST   /api/v1/crm/activities/
POST   /api/v1/crm/activities/{id}/complete/
```

---

## 📊 Enterprise APIs

### لوحة المعلومات
```http
GET /api/v1/enterprise/dashboard/
```

**Response:**
```json
{
    "sales": {
        "today": "15000.00",
        "this_week": "85000.00",
        "this_month": "320000.00",
        "growth_percentage": 12.5
    },
    "inventory": {
        "total_value": "1500000.00",
        "low_stock_count": 15,
        "out_of_stock_count": 3
    },
    "receivables": {
        "total": "450000.00",
        "overdue": "75000.00"
    },
    "top_products": [...],
    "recent_orders": [...]
}
```

### تقارير API

```http
GET /api/v1/reports/sales/
GET /api/v1/reports/inventory/
GET /api/v1/reports/financial/
GET /api/v1/reports/hr/
```

**Parameters:**
| المعامل | النوع | الوصف |
|---------|-------|-------|
| start_date | date | تاريخ البداية |
| end_date | date | تاريخ النهاية |
| format | string | json, csv, xlsx, pdf |
| branch | integer | الفرع |

---

## 🏪 POS APIs

### إنشاء طلب POS
```http
POST /api/v1/pos/orders/create/
Content-Type: application/json

{
    "session_id": 1,
    "customer_id": null,
    "table_id": 5,
    "items": [
        {"product_id": 1, "quantity": 2, "price": "50.00"},
        {"product_id": 2, "quantity": 1, "price": "75.00"}
    ],
    "payments": [
        {"method": "cash", "amount": "175.00"}
    ],
    "discount": "0.00"
}
```

### جلسات POS
```http
POST /api/v1/pos/sessions/open/
POST /api/v1/pos/sessions/{id}/close/
GET  /api/v1/pos/sessions/{id}/summary/
```

---

## 🤖 AI APIs

### المساعد الذكي
```http
POST /api/v1/ai/chat/
Content-Type: application/json

{
    "message": "ما هي المبيعات اليوم؟",
    "session_id": "abc123"
}
```

**Response:**
```json
{
    "response": "مبيعات اليوم بلغت 15,000 ج.م من 25 فاتورة.",
    "suggestions": [
        "عرض تفاصيل المبيعات",
        "مقارنة مع الأمس",
        "أعلى المنتجات مبيعاً"
    ]
}
```

### التنبؤ بالمبيعات
```http
GET /api/v1/ai/sales-forecast/
```

**Parameters:**
| المعامل | النوع | الوصف |
|---------|-------|-------|
| period | string | week, month, quarter |
| product | integer | منتج محدد (اختياري) |

---

## 🔔 Notifications API

### الإشعارات
```http
GET  /api/v1/notifications/
POST /api/v1/notifications/{id}/read/
POST /api/v1/notifications/read-all/
```

### WebSocket للإشعارات الفورية
```javascript
const ws = new WebSocket('wss://domain.com/ws/notifications/');

ws.onmessage = function(event) {
    const notification = JSON.parse(event.data);
    console.log(notification);
};
```

---

## 📄 API Documentation

### Swagger/OpenAPI
```
GET /api/schema/
GET /api/docs/           # Swagger UI
GET /api/redoc/          # ReDoc
```

---

## ⚡ Rate Limiting

| Endpoint Type | الحد | الفترة |
|---------------|------|--------|
| Authentication | 5 | minute |
| General API | 100 | minute |
| Reports | 10 | minute |
| Bulk Operations | 5 | minute |

---

## 🔧 Error Responses

### أكواد الأخطاء

| الكود | الوصف |
|-------|-------|
| 400 | طلب غير صالح |
| 401 | غير مصرح |
| 403 | ممنوع |
| 404 | غير موجود |
| 429 | طلبات كثيرة |
| 500 | خطأ في الخادم |

### شكل الخطأ
```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "خطأ في التحقق من البيانات",
        "details": {
            "name": ["هذا الحقل مطلوب"],
            "price": ["يجب أن يكون رقماً موجباً"]
        }
    }
}
```

---

## 📡 Endpoints Summary

| الفئة | عدد الـ Endpoints |
|-------|-------------------|
| Core (Products, Stock, etc.) | ~50 |
| Sales & Invoicing | ~80 |
| Purchases | ~60 |
| Accounting | ~100 |
| HR | ~80 |
| CRM | ~70 |
| POS | ~30 |
| Reports | ~50 |
| AI & Analytics | ~20 |
| Other Modules | ~460 |
| **المجموع** | **~1000+** |

> ملاحظة: العدد الإجمالي للـ URL patterns هو 5,300+ والذي يشمل صفحات الويب و APIs.

---

*الوثيقة التالية: [06-SECURITY.md](06-SECURITY.md)*
