# Tony ERP E-Commerce API Documentation
# مرجع API للمتجر الإلكتروني

## 🔗 Base URL

```
Production: https://yourdomain.com/api/v1
Development: http://localhost:8000/api/v1
```

## 🔐 Authentication

### Token Authentication

```bash
# Get Token
POST /api/token/
{
  "username": "user@example.com",
  "password": "your-password"
}

# Response
{
  "access": "eyJ0eXAiOiJKV1...",
  "refresh": "eyJ0eXAiOiJKV1..."
}
```

### Using Token

```bash
Authorization: Bearer eyJ0eXAiOiJKV1...
```

---

## 📦 Products API

### List Products

```http
GET /ecommerce/products/
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `per_page` | int | Items per page (default: 20, max: 100) |
| `category` | int | Filter by category ID |
| `brand` | int | Filter by brand ID |
| `min_price` | float | Minimum price filter |
| `max_price` | float | Maximum price filter |
| `in_stock` | bool | Only in-stock items |
| `featured` | bool | Only featured items |
| `q` | string | Search query |
| `sort` | string | Sort: price_asc, price_desc, newest, popular |

**Response:**
```json
{
  "success": true,
  "data": {
    "products": [
      {
        "id": 1,
        "sku": "PRD-001",
        "name": "Product Name",
        "name_ar": "اسم المنتج",
        "slug": "product-name",
        "description": "...",
        "price": "199.99",
        "sale_price": "149.99",
        "currency": "EGP",
        "stock_quantity": 50,
        "in_stock": true,
        "category": {
          "id": 1,
          "name": "Electronics",
          "slug": "electronics"
        },
        "brand": {
          "id": 1,
          "name": "Samsung"
        },
        "images": [
          {
            "url": "/media/products/img1.jpg",
            "alt": "Product Image",
            "is_primary": true
          }
        ],
        "rating": 4.5,
        "reviews_count": 25,
        "is_featured": true,
        "created_at": "2026-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "total": 150,
      "page": 1,
      "per_page": 20,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### Get Product Detail

```http
GET /ecommerce/products/{id}/
GET /ecommerce/products/by-slug/{slug}/
```

### Get Related Products

```http
GET /ecommerce/products/{id}/related/
```

---

## 🛒 Cart API

### Get Cart

```http
GET /ecommerce/cart/
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "cart_abc123",
    "items": [
      {
        "id": 1,
        "product": {
          "id": 1,
          "name": "Product",
          "price": "199.99",
          "image": "/media/products/img.jpg"
        },
        "quantity": 2,
        "subtotal": "399.98"
      }
    ],
    "items_count": 2,
    "subtotal": "399.98",
    "shipping": "50.00",
    "tax": "55.99",
    "total": "505.97",
    "currency": "EGP"
  }
}
```

### Add to Cart

```http
POST /ecommerce/cart/add/
Content-Type: application/json

{
  "product_id": 1,
  "quantity": 2
}
```

### Update Cart Item

```http
PUT /ecommerce/cart/update/
Content-Type: application/json

{
  "item_id": 1,
  "quantity": 3
}
```

### Remove from Cart

```http
DELETE /ecommerce/cart/remove/
Content-Type: application/json

{
  "item_id": 1
}
```

### Apply Coupon

```http
POST /ecommerce/cart/apply-coupon/
Content-Type: application/json

{
  "code": "SAVE20"
}
```

---

## 🧾 Orders API

### Create Order

```http
POST /ecommerce/orders/
Content-Type: application/json

{
  "shipping_address": {
    "first_name": "أحمد",
    "last_name": "محمد",
    "phone": "+201234567890",
    "address_line1": "123 شارع التحرير",
    "address_line2": "الدور الثالث",
    "city": "القاهرة",
    "governorate": "cairo",
    "postal_code": "11511"
  },
  "billing_same_as_shipping": true,
  "payment_method": "paymob_card",
  "notes": "Please call before delivery"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "order": {
      "id": 1,
      "order_number": "ORD-20260115-0001",
      "status": "pending_payment",
      "items": [...],
      "subtotal": "399.98",
      "shipping_cost": "50.00",
      "tax_amount": "55.99",
      "total": "505.97"
    },
    "payment": {
      "method": "paymob_card",
      "iframe_url": "https://accept.paymob.com/api/acceptance/iframes/...",
      "payment_key": "ZXlKaGJHY..."
    }
  }
}
```

### List Orders

```http
GET /ecommerce/orders/
```

### Get Order Detail

```http
GET /ecommerce/orders/{order_number}/
```

### Track Order

```http
GET /ecommerce/orders/{order_number}/track/
```

---

## 💳 Payment API

### Payment Methods

```http
GET /ecommerce/payment/methods/
```

**Response:**
```json
{
  "success": true,
  "data": {
    "methods": [
      {
        "id": "paymob_card",
        "name": "Credit/Debit Card",
        "name_ar": "بطاقة ائتمان",
        "icon": "/static/icons/card.svg",
        "min_amount": 10,
        "max_amount": 100000,
        "fee_type": "percentage",
        "fee_value": 2.5
      },
      {
        "id": "paymob_wallet",
        "name": "Mobile Wallet",
        "name_ar": "المحفظة الإلكترونية",
        "icon": "/static/icons/wallet.svg"
      },
      {
        "id": "fawry",
        "name": "Fawry",
        "name_ar": "فوري",
        "icon": "/static/icons/fawry.svg"
      },
      {
        "id": "instapay",
        "name": "InstaPay",
        "name_ar": "انستاباي",
        "icon": "/static/icons/instapay.svg"
      },
      {
        "id": "cod",
        "name": "Cash on Delivery",
        "name_ar": "الدفع عند الاستلام",
        "fee_type": "fixed",
        "fee_value": 20
      }
    ]
  }
}
```

### Initiate Payment

```http
POST /ecommerce/payment/initiate/
Content-Type: application/json

{
  "order_id": 1,
  "method": "paymob_card",
  "return_url": "https://yourdomain.com/checkout/complete"
}
```

### Verify Payment (Webhook)

```http
POST /ecommerce/payment/webhook/paymob/
X-Paymob-Signature: abc123...

{
  "obj": {...},
  "type": "TRANSACTION"
}
```

---

## 👤 Customer API

### Register

```http
POST /ecommerce/customers/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "أحمد",
  "last_name": "محمد",
  "phone": "+201234567890"
}
```

### Login

```http
POST /ecommerce/customers/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

### Profile

```http
GET /ecommerce/customers/profile/
PUT /ecommerce/customers/profile/
```

### Addresses

```http
GET /ecommerce/customers/addresses/
POST /ecommerce/customers/addresses/
PUT /ecommerce/customers/addresses/{id}/
DELETE /ecommerce/customers/addresses/{id}/
```

### Wishlist

```http
GET /ecommerce/customers/wishlist/
POST /ecommerce/customers/wishlist/add/
DELETE /ecommerce/customers/wishlist/remove/{product_id}/
```

---

## 📂 Categories API

### List Categories

```http
GET /ecommerce/categories/
```

### Category Tree

```http
GET /ecommerce/categories/tree/
```

### Category Products

```http
GET /ecommerce/categories/{slug}/products/
```

---

## ⭐ Reviews API

### List Reviews

```http
GET /ecommerce/products/{product_id}/reviews/
```

### Create Review

```http
POST /ecommerce/products/{product_id}/reviews/
Content-Type: application/json

{
  "rating": 5,
  "title": "منتج ممتاز",
  "comment": "جودة عالية وتوصيل سريع"
}
```

---

## 🔍 Search API

### Search Products

```http
GET /ecommerce/search/?q=laptop
```

### Autocomplete

```http
GET /ecommerce/search/autocomplete/?q=lap
```

**Response:**
```json
{
  "suggestions": [
    {"text": "Laptop", "type": "product"},
    {"text": "Laptop Accessories", "type": "category"},
    {"text": "Laptop Bags", "type": "product"}
  ]
}
```

---

## 📍 Shipping API

### Get Shipping Rates

```http
POST /ecommerce/shipping/rates/
Content-Type: application/json

{
  "governorate": "cairo",
  "cart_total": 500.00,
  "weight": 2.5
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "rates": [
      {
        "method": "standard",
        "name": "Standard Delivery",
        "name_ar": "توصيل عادي",
        "cost": "50.00",
        "estimated_days": "3-5"
      },
      {
        "method": "express",
        "name": "Express Delivery",
        "name_ar": "توصيل سريع",
        "cost": "100.00",
        "estimated_days": "1-2"
      }
    ],
    "free_shipping_threshold": 500.00,
    "eligible_for_free_shipping": true
  }
}
```

### Governorates List

```http
GET /ecommerce/shipping/governorates/
```

---

## 🎟️ Coupons API

### Validate Coupon

```http
POST /ecommerce/coupons/validate/
Content-Type: application/json

{
  "code": "SAVE20",
  "cart_total": 500.00
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "code": "SAVE20",
    "discount_type": "percentage",
    "discount_value": 20,
    "discount_amount": "100.00",
    "message": "تم تطبيق كوبون خصم 20%"
  }
}
```

---

## 🌐 Internationalization

### Currency

```http
GET /ecommerce/currencies/
POST /ecommerce/currencies/set/

{
  "currency": "USD"
}
```

### Language

Set via `Accept-Language` header:
```http
Accept-Language: ar
```

---

## 📊 Error Responses

### Standard Error Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "email": ["This field is required"],
      "phone": ["Invalid phone number format"]
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `AUTHENTICATION_REQUIRED` | 401 | Login required |
| `PERMISSION_DENIED` | 403 | Not authorized |
| `NOT_FOUND` | 404 | Resource not found |
| `OUT_OF_STOCK` | 409 | Product not available |
| `PAYMENT_FAILED` | 402 | Payment processing failed |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal error |

---

## 🔒 Rate Limiting

| Endpoint | Limit |
|----------|-------|
| General API | 100 requests/minute |
| Search | 30 requests/minute |
| Payment | 10 requests/minute |
| Login | 5 requests/minute |

**Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642000000
```

---

## 📱 Webhooks

### Payment Webhook

```
POST https://yourdomain.com/api/v1/ecommerce/webhooks/payment/
```

### Order Status Webhook

Configure in admin to receive order status updates to your systems.

---

**API Version:** 1.0  
**Last Updated:** January 2026
