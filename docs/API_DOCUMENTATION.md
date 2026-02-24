# E-commerce API Documentation
## متجر Tony ERP - دليل API الشامل

---

## 📋 جدول المحتويات

1. [نظرة عامة](#overview)
2. [المصادقة (Authentication)](#authentication)
3. [نقاط نهاية المنتجات](#products-api)
4. [نقاط نهاية الفئات](#categories-api)
5. [نقاط نهاية السلة](#cart-api)
6. [نقاط نهاية الطلبات](#orders-api)
7. [نقاط نهاية المدفوعات](#payments-api)
8. [نقاط نهاية المراجعات](#reviews-api)
9. [نقاط نهاية القسائم](#coupons-api)
10. [Webhooks](#webhooks)
11. [معالجة الأخطاء](#error-handling)
12. [أمثلة عملية](#examples)

---

## 🌐 نظرة عامة {#overview}

### Base URL
```
https://yourdomain.com/api/ecommerce/
```

### Format
جميع الطلبات والاستجابات بصيغة JSON.

### Rate Limiting
- 100 طلب/دقيقة للمستخدمين المسجلين
- 30 طلب/دقيقة للزوار

### الترقيم (Pagination)
```json
{
  "count": 100,
  "next": "https://api.example.com/products/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## 🔐 المصادقة (Authentication) {#authentication}

### الحصول على Token

```http
POST /api/ecommerce/auth/token/
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "your_password"
}
```

**الاستجابة:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### تجديد Token

```http
POST /api/ecommerce/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### استخدام Token

```http
GET /api/ecommerce/orders/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

## 📦 نقاط نهاية المنتجات {#products-api}

### قائمة المنتجات

```http
GET /api/ecommerce/products/
```

**المعاملات:**
| المعامل | النوع | الوصف |
|---------|-------|-------|
| `page` | int | رقم الصفحة |
| `page_size` | int | عدد المنتجات (افتراضي: 20) |
| `search` | string | البحث في الاسم والوصف |
| `category` | int | معرف الفئة |
| `min_price` | decimal | الحد الأدنى للسعر |
| `max_price` | decimal | الحد الأقصى للسعر |
| `ordering` | string | الترتيب: `price`, `-price`, `created_at`, `-created_at` |
| `in_stock` | boolean | المنتجات المتوفرة فقط |

**الاستجابة:**
```json
{
  "count": 150,
  "next": "https://api.example.com/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "هاتف سامسونج جالاكسي S24",
      "slug": "samsung-galaxy-s24",
      "description": "أحدث هاتف من سامسونج",
      "price": "35000.00",
      "compare_price": "40000.00",
      "discount_percentage": 12.5,
      "stock": 25,
      "in_stock": true,
      "category": {
        "id": 1,
        "name": "هواتف",
        "slug": "phones"
      },
      "brand": {
        "id": 1,
        "name": "سامسونج"
      },
      "images": [
        {
          "id": 1,
          "image": "https://cdn.example.com/products/1.jpg",
          "is_primary": true
        }
      ],
      "rating": 4.5,
      "reviews_count": 120,
      "created_at": "2026-01-15T10:00:00Z"
    }
  ]
}
```

### تفاصيل منتج

```http
GET /api/ecommerce/products/{id}/
```

**الاستجابة:**
```json
{
  "id": 1,
  "name": "هاتف سامسونج جالاكسي S24",
  "slug": "samsung-galaxy-s24",
  "description": "أحدث هاتف من سامسونج بمواصفات متطورة",
  "specifications": {
    "الشاشة": "6.7 بوصة AMOLED",
    "المعالج": "Snapdragon 8 Gen 3",
    "الذاكرة": "12 جيجابايت",
    "التخزين": "256 جيجابايت"
  },
  "price": "35000.00",
  "compare_price": "40000.00",
  "discount_percentage": 12.5,
  "stock": 25,
  "in_stock": true,
  "category": {...},
  "brand": {...},
  "images": [...],
  "variants": [
    {
      "id": 1,
      "name": "256GB - أسود",
      "price": "35000.00",
      "stock": 15
    }
  ],
  "related_products": [...],
  "rating": 4.5,
  "reviews_count": 120,
  "reviews": [...]
}
```

---

## 📁 نقاط نهاية الفئات {#categories-api}

### قائمة الفئات

```http
GET /api/ecommerce/categories/
```

**الاستجابة:**
```json
{
  "results": [
    {
      "id": 1,
      "name": "إلكترونيات",
      "slug": "electronics",
      "description": "أجهزة إلكترونية متنوعة",
      "image": "https://cdn.example.com/categories/electronics.jpg",
      "products_count": 45,
      "children": [
        {
          "id": 2,
          "name": "هواتف",
          "slug": "phones",
          "products_count": 25
        }
      ]
    }
  ]
}
```

### منتجات فئة معينة

```http
GET /api/ecommerce/categories/{id}/products/
```

---

## 🛒 نقاط نهاية السلة {#cart-api}

> ⚠️ **ملاحظة:** جميع نقاط نهاية السلة تتطلب مصادقة

### عرض السلة

```http
GET /api/ecommerce/cart/
Authorization: Bearer {token}
```

**الاستجابة:**
```json
{
  "id": 123,
  "items": [
    {
      "id": 1,
      "product": {
        "id": 1,
        "name": "هاتف سامسونج",
        "price": "35000.00",
        "image": "https://cdn.example.com/products/1.jpg"
      },
      "quantity": 2,
      "total": "70000.00"
    }
  ],
  "subtotal": "70000.00",
  "vat": "9800.00",
  "vat_rate": 14,
  "shipping": "30.00",
  "discount": "0.00",
  "total": "79830.00"
}
```

### إضافة للسلة

```http
POST /api/ecommerce/cart/
Authorization: Bearer {token}
Content-Type: application/json

{
  "product_id": 1,
  "quantity": 2
}
```

### تحديث الكمية

```http
PATCH /api/ecommerce/cart/{item_id}/
Authorization: Bearer {token}
Content-Type: application/json

{
  "quantity": 3
}
```

### إزالة من السلة

```http
DELETE /api/ecommerce/cart/{item_id}/
Authorization: Bearer {token}
```

### مسح السلة

```http
DELETE /api/ecommerce/cart/clear/
Authorization: Bearer {token}
```

---

## 📋 نقاط نهاية الطلبات {#orders-api}

### إنشاء طلب

```http
POST /api/ecommerce/orders/
Authorization: Bearer {token}
Content-Type: application/json

{
  "shipping_address": {
    "first_name": "أحمد",
    "last_name": "محمد",
    "phone": "01012345678",
    "governorate": "cairo",
    "city": "مدينة نصر",
    "address": "شارع مصطفى النحاس، عمارة 5",
    "postal_code": "11765"
  },
  "payment_method": "paymob_card",
  "coupon_code": "SAVE10",
  "notes": "الرجاء التوصيل بعد الساعة 5 مساءً"
}
```

**الاستجابة:**
```json
{
  "id": 456,
  "order_number": "ORD-2026-00456",
  "status": "pending",
  "payment_status": "pending",
  "items": [...],
  "subtotal": "35000.00",
  "vat": "4900.00",
  "shipping": "30.00",
  "discount": "3500.00",
  "total": "36430.00",
  "shipping_address": {...},
  "payment_method": "paymob_card",
  "payment_url": "https://accept.paymob.com/api/acceptance/iframes/123?payment_token=...",
  "created_at": "2026-01-20T14:30:00Z"
}
```

### قائمة الطلبات

```http
GET /api/ecommerce/orders/
Authorization: Bearer {token}
```

**المعاملات:**
| المعامل | النوع | الوصف |
|---------|-------|-------|
| `status` | string | حالة الطلب: `pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled` |
| `from_date` | date | من تاريخ (YYYY-MM-DD) |
| `to_date` | date | إلى تاريخ (YYYY-MM-DD) |

### تفاصيل طلب

```http
GET /api/ecommerce/orders/{id}/
Authorization: Bearer {token}
```

### إلغاء طلب

```http
POST /api/ecommerce/orders/{id}/cancel/
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "غيرت رأيي"
}
```

### تتبع الطلب

```http
GET /api/ecommerce/orders/{id}/tracking/
Authorization: Bearer {token}
```

**الاستجابة:**
```json
{
  "order_number": "ORD-2026-00456",
  "status": "shipped",
  "tracking_number": "EG123456789",
  "carrier": "aramex",
  "timeline": [
    {
      "status": "pending",
      "timestamp": "2026-01-20T14:30:00Z",
      "description": "تم استلام الطلب"
    },
    {
      "status": "confirmed",
      "timestamp": "2026-01-20T14:35:00Z",
      "description": "تم تأكيد الطلب"
    },
    {
      "status": "processing",
      "timestamp": "2026-01-20T16:00:00Z",
      "description": "جاري تجهيز الطلب"
    },
    {
      "status": "shipped",
      "timestamp": "2026-01-21T09:00:00Z",
      "description": "تم شحن الطلب"
    }
  ],
  "estimated_delivery": "2026-01-23"
}
```

---

## 💳 نقاط نهاية المدفوعات {#payments-api}

### طرق الدفع المتاحة

```http
GET /api/ecommerce/payment-methods/
```

**الاستجابة:**
```json
{
  "methods": [
    {
      "id": "paymob_card",
      "name": "بطاقة ائتمان",
      "description": "Visa, Mastercard",
      "icon": "credit-card",
      "fees": "0.00",
      "is_available": true
    },
    {
      "id": "paymob_wallet",
      "name": "محفظة إلكترونية",
      "description": "فودافون كاش، أورانج كاش، اتصالات كاش",
      "icon": "wallet",
      "fees": "0.00",
      "is_available": true
    },
    {
      "id": "fawry",
      "name": "فوري",
      "description": "الدفع عند أي فرع فوري",
      "icon": "fawry",
      "fees": "5.00",
      "is_available": true
    },
    {
      "id": "valu",
      "name": "تقسيط فاليو",
      "description": "تقسيط حتى 60 شهر",
      "icon": "valu",
      "fees": "0.00",
      "is_available": true
    },
    {
      "id": "cod",
      "name": "الدفع عند الاستلام",
      "description": "ادفع نقداً عند التوصيل",
      "icon": "cash",
      "fees": "10.00",
      "max_amount": "5000.00",
      "is_available": true
    }
  ]
}
```

### بدء عملية الدفع

```http
POST /api/ecommerce/orders/{order_id}/pay/
Authorization: Bearer {token}
Content-Type: application/json

{
  "payment_method": "paymob_card",
  "return_url": "https://yourapp.com/payment/callback"
}
```

**الاستجابة:**
```json
{
  "payment_id": "PAY-2026-789",
  "payment_url": "https://accept.paymob.com/api/acceptance/iframes/123?payment_token=...",
  "expires_at": "2026-01-20T15:30:00Z"
}
```

### التحقق من حالة الدفع

```http
GET /api/ecommerce/payments/{payment_id}/status/
Authorization: Bearer {token}
```

---

## ⭐ نقاط نهاية المراجعات {#reviews-api}

### إضافة مراجعة

```http
POST /api/ecommerce/reviews/
Authorization: Bearer {token}
Content-Type: application/json

{
  "product": 1,
  "rating": 5,
  "comment": "منتج ممتاز! أنصح به بشدة"
}
```

### مراجعات منتج

```http
GET /api/ecommerce/reviews/?product={product_id}
```

**الاستجابة:**
```json
{
  "average_rating": 4.5,
  "total_reviews": 120,
  "rating_breakdown": {
    "5": 80,
    "4": 25,
    "3": 10,
    "2": 3,
    "1": 2
  },
  "results": [
    {
      "id": 1,
      "user": {
        "name": "أحمد م.",
        "avatar": null
      },
      "rating": 5,
      "comment": "منتج ممتاز!",
      "verified_purchase": true,
      "created_at": "2026-01-15T10:00:00Z",
      "helpful_count": 15
    }
  ]
}
```

---

## 🎫 نقاط نهاية القسائم {#coupons-api}

### التحقق من قسيمة

```http
POST /api/ecommerce/coupons/validate/
Authorization: Bearer {token}
Content-Type: application/json

{
  "code": "SAVE20",
  "order_total": "1000.00"
}
```

**الاستجابة (نجاح):**
```json
{
  "valid": true,
  "code": "SAVE20",
  "discount_type": "percentage",
  "discount_value": "20.00",
  "discount_amount": "200.00",
  "min_order_amount": "500.00",
  "message": "سيتم خصم 20% من قيمة طلبك"
}
```

**الاستجابة (فشل):**
```json
{
  "valid": false,
  "error": "coupon_expired",
  "message": "انتهت صلاحية هذه القسيمة"
}
```

---

## 🔗 Webhooks {#webhooks}

### Paymob Webhook

```http
POST /api/ecommerce/webhooks/paymob/
```

**Headers:**
```
HMAC: {hmac_signature}
```

**Body:**
```json
{
  "obj": {
    "id": 123456,
    "pending": false,
    "amount_cents": 350000,
    "success": true,
    "order": {
      "id": 789,
      "merchant_order_id": "ORD-2026-00456"
    },
    "source_data": {
      "type": "card",
      "pan": "1234",
      "sub_type": "MasterCard"
    }
  }
}
```

### Fawry Webhook

```http
POST /api/ecommerce/webhooks/fawry/
```

**Body:**
```json
{
  "requestId": "req123",
  "fawryRefNumber": "987654321",
  "merchantRefNumber": "ORD-2026-00456",
  "orderAmount": 3500.00,
  "paymentAmount": 3500.00,
  "orderStatus": "PAID",
  "paymentMethod": "PAYATFAWRY"
}
```

---

## ⚠️ معالجة الأخطاء {#error-handling}

### رموز الحالة

| الرمز | المعنى |
|-------|--------|
| 200 | نجاح |
| 201 | تم الإنشاء |
| 400 | طلب غير صالح |
| 401 | غير مصرح |
| 403 | ممنوع |
| 404 | غير موجود |
| 422 | خطأ في التحقق |
| 429 | تجاوز الحد المسموح |
| 500 | خطأ في الخادم |

### صيغة الخطأ

```json
{
  "error": "validation_error",
  "message": "بيانات غير صالحة",
  "details": {
    "quantity": ["يجب أن تكون الكمية رقماً موجباً"],
    "product_id": ["المنتج غير موجود"]
  }
}
```

### أخطاء شائعة

| الخطأ | الوصف | الحل |
|-------|-------|------|
| `invalid_token` | Token غير صالح | أعد تسجيل الدخول |
| `token_expired` | انتهت صلاحية Token | استخدم refresh token |
| `out_of_stock` | المنتج غير متوفر | اختر منتجاً آخر |
| `insufficient_stock` | الكمية أكبر من المتوفر | قلل الكمية |
| `coupon_expired` | القسيمة منتهية | استخدم قسيمة أخرى |
| `coupon_min_not_met` | لم يتحقق الحد الأدنى | أضف منتجات |
| `payment_failed` | فشل الدفع | حاول مرة أخرى |

---

## 💡 أمثلة عملية {#examples}

### مثال كامل: من التسجيل للشراء

```javascript
// 1. تسجيل الدخول
const loginResponse = await fetch('/api/ecommerce/auth/token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'user@example.com',
    password: 'password123'
  })
});
const { access } = await loginResponse.json();

// 2. تصفح المنتجات
const productsResponse = await fetch('/api/ecommerce/products/?category=1', {
  headers: { 'Authorization': `Bearer ${access}` }
});
const products = await productsResponse.json();

// 3. إضافة للسلة
const cartResponse = await fetch('/api/ecommerce/cart/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    product_id: products.results[0].id,
    quantity: 1
  })
});

// 4. إنشاء الطلب
const orderResponse = await fetch('/api/ecommerce/orders/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    shipping_address: {
      first_name: 'أحمد',
      last_name: 'محمد',
      phone: '01012345678',
      governorate: 'cairo',
      city: 'مدينة نصر',
      address: 'شارع النصر'
    },
    payment_method: 'paymob_card'
  })
});
const order = await orderResponse.json();

// 5. التوجيه للدفع
window.location.href = order.payment_url;
```

### مثال Python

```python
import requests

BASE_URL = 'https://yourdomain.com/api/ecommerce'

# تسجيل الدخول
auth_response = requests.post(f'{BASE_URL}/auth/token/', json={
    'username': 'user@example.com',
    'password': 'password123'
})
access_token = auth_response.json()['access']

headers = {'Authorization': f'Bearer {access_token}'}

# قائمة المنتجات
products = requests.get(
    f'{BASE_URL}/products/',
    params={'search': 'سامسونج', 'min_price': 1000},
    headers=headers
).json()

# إضافة للسلة
cart = requests.post(
    f'{BASE_URL}/cart/',
    json={'product_id': products['results'][0]['id'], 'quantity': 1},
    headers=headers
).json()

print(f"إجمالي السلة: {cart['total']} ج.م")
```

---

## 📞 الدعم الفني

للمساعدة التقنية:
- 📧 البريد الإلكتروني: api-support@tonyerp.com
- 📱 واتساب: +20 123 456 7890
- 📖 التوثيق الكامل: https://docs.tonyerp.com

---

**آخر تحديث:** يناير 2026
**الإصدار:** 2.0.0
