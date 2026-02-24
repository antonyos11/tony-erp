# Tony ERP - API Developer Guide

## 📚 نظرة عامة

Tony ERP يوفر واجهة برمجية RESTful شاملة تغطي جميع وحدات النظام.

## 🔐 المصادقة (Authentication)

### JWT Token Authentication

```bash
# الحصول على Token
POST /api/token/
{
  "username": "admin",
  "password": "admin123"
}

# Response
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbG...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbG..."
}

# استخدام Token
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbG...
```

### تحديث Token

```bash
POST /api/token/refresh/
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbG..."
}
```

## 📍 Base URL

```
Development: http://localhost:8000
Production: https://your-domain.com
```

## 🗺️ Endpoints الرئيسية

### 1. المحاسبة (Accounting)
```
GET    /api/accounting/accounts/        # دليل الحسابات
POST   /api/accounting/accounts/        # إضافة حساب
GET    /api/accounting/entries/         # القيود اليومية
POST   /api/accounting/entries/         # إنشاء قيد
GET    /api/accounting/balance-sheet/   # الميزانية
GET    /api/accounting/income-statement/ # قائمة الدخل
```

### 2. المخزون (Inventory)
```
GET    /api/inventory/products/         # المنتجات
POST   /api/inventory/products/         # إضافة منتج
GET    /api/inventory/movements/        # حركة المخزون
GET    /api/inventory/locations/        # المواقع
GET    /api/inventory/valuation/        # تقييم المخزون
```

### 3. المبيعات (Sales)
```
GET    /api/sales/invoices/             # الفواتير
POST   /api/sales/invoices/             # إنشاء فاتورة
GET    /api/sales/customers/            # العملاء
GET    /api/sales/reports/              # تقارير المبيعات
```

### 4. المشتريات (Purchases)
```
GET    /api/purchases/bills/            # فواتير المشتريات
POST   /api/purchases/bills/            # إنشاء فاتورة شراء
GET    /api/purchases/suppliers/        # الموردين
```

### 5. الموارد البشرية (HR)
```
GET    /api/hr/employees/               # الموظفين
GET    /api/hr/departments/             # الأقسام
GET    /api/hr/attendance/              # الحضور والانصراف
GET    /api/hr/payroll/                 # الرواتب
```

### 6. CRM
```
GET    /api/crm/customers/              # العملاء
GET    /api/crm/opportunities/          # الفرص التجارية
GET    /api/crm/activities/             # الأنشطة
GET    /api/crm/tickets/                # تذاكر الدعم
```

### 7. الإنتاج (Production)
```
GET    /api/production/orders/          # أوامر الإنتاج
GET    /api/production/work-centers/    # مراكز العمل
GET    /api/production/bom/             # قوائم المواد
```

### 8. الأسطول (Fleet)
```
GET    /api/fleet/vehicles/             # المركبات
GET    /api/fleet/drivers/              # السائقون
GET    /api/fleet/trips/                # الرحلات
```

### 9. الشحن (Shipping) 🆕
```
GET    /api/shipping/companies/         # شركات الشحن
GET    /api/shipping/zones/             # مناطق الشحن
GET    /api/shipping/rates/             # تعريفات الشحن
POST   /api/shipping/rates/calculate/   # حساب تكلفة الشحن
GET    /api/shipping/shipments/         # الشحنات
POST   /api/shipping/shipments/         # إنشاء شحنة
GET    /api/shipping/shipments/{id}/track/ # تتبع شحنة
```

### 10. الجودة (Quality Control) 🆕
```
GET    /api/quality-control/standards/  # معايير الجودة
GET    /api/quality-control/inspection-types/ # أنواع الفحص
GET    /api/quality-control/inspections/ # الفحوصات
POST   /api/quality-control/inspections/ # إنشاء فحص
GET    /api/quality-control/issues/     # مشاكل الجودة
GET    /api/quality-control/corrective-actions/ # الإجراءات التصحيحية
```

### 11. التقارير (Reports)
```
GET    /api/reports/overview/           # نظرة عامة
GET    /api/reports/sales/              # تقرير المبيعات
GET    /api/reports/inventory/          # تقرير المخزون
GET    /api/reports/profit-loss/        # الأرباح والخسائر
GET    /api/reports/cash-flow/          # التدفقات النقدية
GET    /api/reports/balance-sheet/      # الميزانية العمومية
```

## 📝 أمثلة عملية

### مثال 1: إنشاء فاتورة مبيعات

```bash
POST /api/sales/invoices/
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "customer": 5,
  "date": "2026-01-04",
  "payment_method": "cash",
  "items": [
    {
      "product": 10,
      "quantity": 2,
      "price": 100.00
    },
    {
      "product": 15,
      "quantity": 1,
      "price": 250.00
    }
  ],
  "notes": "فاتورة نقدية"
}
```

### مثال 2: تتبع شحنة

```bash
GET /api/shipping/shipments/TRACK12345/track/
Authorization: Bearer YOUR_TOKEN

Response:
{
  "tracking_number": "TRACK12345",
  "current_status": "in_transit",
  "company": "شركة DHL",
  "expected_delivery": "2026-01-10",
  "history": [
    {
      "status": "picked_up",
      "location": "الرياض - المستودع",
      "timestamp": "2026-01-04T10:00:00Z"
    },
    {
      "status": "in_transit",
      "location": "مركز الفرز - جدة",
      "timestamp": "2026-01-05T14:30:00Z"
    }
  ]
}
```

### مثال 3: إنشاء فحص جودة

```bash
POST /api/quality-control/inspections/
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "inspection_type": 2,
  "product": 50,
  "batch_number": "BATCH2024001",
  "inspection_date": "2026-01-04T08:00:00Z",
  "inspector": 3,
  "results": [
    {
      "standard": 1,
      "measured_value": 25.5,
      "is_passed": true
    },
    {
      "standard": 2,
      "measured_value": 98.2,
      "is_passed": true
    }
  ]
}
```

## 🔍 البحث والتصفية

### البحث
```bash
GET /api/inventory/products/?search=laptop
```

### التصفية
```bash
GET /api/sales/invoices/?payment_method=cash&date_from=2026-01-01
```

### الترتيب
```bash
GET /api/crm/customers/?ordering=-created_at
```

### Pagination
```bash
GET /api/inventory/products/?page=2&page_size=50
```

## 📊 إحصائيات

### إحصائيات الشحن
```bash
GET /api/shipping/shipments/statistics/

Response:
{
  "total": 1250,
  "pending": 45,
  "in_transit": 320,
  "delivered": 850,
  "total_value": 125000.00,
  "total_cost": 8500.00,
  "avg_cost": 6.80
}
```

### إحصائيات الجودة
```bash
GET /api/quality-control/inspections/statistics/

Response:
{
  "total": 500,
  "pending": 20,
  "passed": 420,
  "failed": 35,
  "success_rate": 92.31,
  "avg_score": 88.5
}
```

## 🚀 أدوات مساعدة

### Swagger UI (توثيق تفاعلي)
```
http://localhost:8000/api/docs/
```

### ReDoc (توثيق بديل)
```
http://localhost:8000/api/redoc/
```

### OpenAPI Schema
```
http://localhost:8000/api/schema/
```

## 📦 Postman Collection

تحميل Postman Collection جاهز:
```bash
# قريباً
```

## ⚠️ معالجة الأخطاء

### أكواد الأخطاء الشائعة

```json
400 Bad Request - بيانات غير صحيحة
{
  "error": "Invalid data",
  "details": {
    "quantity": ["This field is required"]
  }
}

401 Unauthorized - غير مصرح
{
  "detail": "Authentication credentials were not provided."
}

403 Forbidden - ممنوع
{
  "detail": "You do not have permission to perform this action."
}

404 Not Found - غير موجود
{
  "detail": "Not found."
}

500 Internal Server Error - خطأ في الخادم
{
  "error": "Internal server error",
  "message": "Something went wrong"
}
```

## 🔒 Rate Limiting

```
المستخدمون العاديون: 100 requests/hour
المستخدمون المميزون: 1000 requests/hour
```

## 📞 الدعم

- التوثيق الكامل: `/api/docs/`
- للمساعدة: راجع فريق التطوير

---

**تم التحديث:** يناير 2026  
**الإصدار:** 2.0.0
