# 🚀 Tony ERP - REST API Quick Reference

**Base URL:** `http://localhost:8000/api/`  
**Authentication:** JWT Bearer Token

---

## 🔐 Authentication Endpoints

### 1. Obtain Token Pair
```http
POST /api/token/
Content-Type: application/json

{
  "username": "boss",
  "password": "Mm02022006"
}

Response 200:
{
  "access": "eyJhbGc...",
  "refresh": "eyJhbGc..."
}
```

### 2. Refresh Access Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJhbGc..."
}

Response 200:
{
  "access": "eyJhbGc..."
}
```

### 3. Logout (Blacklist Token)
```http
POST /api/logout/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "refresh": "eyJhbGc..."
}

Response 200:
{
  "success": true,
  "message": "تم تسجيل الخروج بنجاح"
}
```

---

## 📦 Product Management

### 1. List Products
```http
GET /api/products/
Authorization: Bearer {access_token}

Query Parameters:
- page=1
- page_size=10
- search=keyword
- sku=PRODUCT-001
- name=Product Name

Response 200:
{
  "count": 100,
  "next": "http://localhost:8000/api/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "sku": "PRODUCT-001",
      "name": "Product Name",
      "price": "99.99",
      "cost": "50.00",
      "product_type": "finished",
      "showroom": 1
    }
  ]
}
```

### 2. Create Product
```http
POST /api/products/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "sku": "PRODUCT-001",
  "name": "Product Name",
  "description": "Product description",
  "price": "99.99",
  "cost": "50.00",
  "product_type": "finished",
  "purchase_uom": "unit",
  "usage_uom": "unit",
  "conversion_factor": "1.0"
}

Response 201:
{
  "id": 1,
  "sku": "PRODUCT-001",
  "name": "Product Name",
  "price": "99.99",
  "showroom": 1
}
```

### 3. Get Product Details
```http
GET /api/products/{id}/
Authorization: Bearer {access_token}

Response 200:
{
  "id": 1,
  "sku": "PRODUCT-001",
  "name": "Product Name",
  ...
}
```

### 4. Update Product
```http
PUT /api/products/{id}/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Updated Name",
  "price": "109.99"
}

Response 200:
{
  "id": 1,
  "name": "Updated Name",
  ...
}
```

### 5. Delete Product
```http
DELETE /api/products/{id}/
Authorization: Bearer {access_token}

Response 204 No Content
```

---

## 📄 Invoice Management

### 1. Create Invoice with Nested Items
```http
POST /api/invoices/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "customer": 123,
  "date": "2026-01-23",
  "due_date": "2026-02-23",
  "items": [
    {
      "product": 456,
      "location": 789,
      "quantity": 2,
      "price": "100.00"
    }
  ],
  "discount": "0.00"
}

Response 201:
{
  "id": 1,
  "number": "INV-202601-000001",
  "customer": 123,
  "date": "2026-01-23",
  "is_approved": false,
  "items": [
    {
      "product": 456,
      "quantity": 2,
      "price": "100.00"
    }
  ]
}
```

### 2. Approve Invoice
```http
POST /api/invoices/{id}/approve/
Authorization: Bearer {access_token}

Response 200:
{
  "success": true,
  "message": "تم اعتماد الفاتورة بنجاح",
  "data": {
    "id": 1,
    "is_approved": true,
    "approved_by": 3,
    "approved_at": "2026-01-23T12:34:56Z"
  }
}
```

### 3. List Invoices
```http
GET /api/invoices/
Authorization: Bearer {access_token}

Query Parameters:
- customer=123
- date=2026-01-23
- is_approved=true
- search=INV-202601

Response 200:
{
  "count": 50,
  "results": [...]
}
```

---

## 🏢 Branch Management

### 1. List Branches
```http
GET /api/branches/
Authorization: Bearer {access_token}

Query Parameters:
- name=Branch Name
- code=BR-001
- is_active=true

Response 200:
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "code": "BR-001",
      "name": "Main Branch",
      "branch_type": "main",
      "address": "123 Main St",
      "phone": "1234567890",
      "email": "branch@example.com",
      "is_active": true
    }
  ]
}
```

### 2. Create Branch
```http
POST /api/branches/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "code": "BR-002",
  "name": "New Branch",
  "branch_type": "branch",
  "address": "456 Second St",
  "phone": "0987654321",
  "email": "newbranch@example.com"
}

Response 201:
{
  "id": 2,
  "code": "BR-002",
  "name": "New Branch",
  ...
}
```

---

## 🔔 Notification Management

### 1. List User Notifications
```http
GET /api/notifications/
Authorization: Bearer {access_token}

Query Parameters:
- is_read=false
- level=warning  # info, success, warning, error

Response 200:
{
  "count": 25,
  "results": [
    {
      "id": 1,
      "title": "إشعار جديد",
      "message": "رسالة الإشعار",
      "level": "info",
      "is_read": false,
      "created_at": "2026-01-23T10:00:00Z"
    }
  ]
}
```

### 2. Mark Notification as Read
```http
PATCH /api/notifications/{id}/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "is_read": true
}

Response 200:
{
  "id": 1,
  "is_read": true,
  ...
}
```

---

## 👥 Customer Management

### 1. List Customers (Partners)
```http
GET /api/customers/
Authorization: Bearer {access_token}

Response 200:
{
  "count": 100,
  "results": [
    {
      "id": 1,
      "name": "Customer Name",
      "phone": "1234567890",
      "email": "customer@example.com"
    }
  ]
}
```

### 2. Create Customer
```http
POST /api/customers/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "New Customer",
  "phone": "1234567890",
  "email": "customer@example.com"
}

Response 201:
{
  "id": 2,
  "name": "New Customer",
  ...
}
```

---

## 📍 Location Management

### 1. List Locations
```http
GET /api/locations/
Authorization: Bearer {access_token}

Response 200:
{
  "count": 20,
  "results": [
    {
      "id": 54,
      "code": "1",
      "name": "مخزن المراتب بالمصنع"
    }
  ]
}
```

**Note:** Locations are scoped by user's showroom. Superusers see all locations.

---

## 🎯 Common Patterns

### Authorization Header
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Error Response Format
```json
{
  "error": true,
  "status_code": 400,
  "message": "Error message in Arabic",
  "details": {
    "field_name": ["Error details"]
  }
}
```

### Pagination
All list endpoints support:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10)

Response includes:
- `count`: Total items
- `next`: Next page URL
- `previous`: Previous page URL
- `results`: Array of items

### Filtering
Use query parameters:
- Exact match: `?field=value`
- Search: `?search=keyword`
- Multiple filters: `?field1=value1&field2=value2`

---

## 🛠️ Testing with cURL

### Get Token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"Mm02022006"}' | \
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access"])')
```

### Create Product
```bash
curl -X POST http://localhost:8000/api/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TEST-001",
    "name": "Test Product",
    "price": "99.99",
    "cost": "50.00",
    "product_type": "finished"
  }'
```

### List Products
```bash
curl -X GET http://localhost:8000/api/products/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📚 Additional Resources

- **Full API Documentation:** [FINAL_API_TESTING_REPORT.md](FINAL_API_TESTING_REPORT.md)
- **Implementation Details:** [TESTSPRITE_API_FIX_COMPLETE_REPORT.md](TESTSPRITE_API_FIX_COMPLETE_REPORT.md)
- **Django Admin:** http://localhost:8000/admin/
- **API Root:** http://localhost:8000/api/

---

**Last Updated:** January 23, 2026  
**API Version:** 1.0  
**Status:** ✅ Production Ready
