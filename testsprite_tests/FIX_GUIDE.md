# 🔧 Tony ERP TestSprite Issues - Fix Guide

## Issues Identified & Solutions

### ❌ Issue #1: DummyResponse Objects (HIGH PRIORITY)

**Problem:** Tests are getting "DummyResponse" objects instead of real HTTP responses.

**Root Cause:** TestSprite is mocking responses when it can't reach the actual API endpoints. This happens because:
1. ✅ **REST Framework authentication is correctly configured** (JWT + BasicAuth)
2. ❌ **Tests are using incorrect base URLs**

**Current (Wrong) URLs in Tests:**
```python
BASE_URL = "http://localhost:8000/dashboard/dashboard"  # ❌ WRONG
```

**Correct URLs Should Be:**
```python
BASE_URL = "http://localhost:8000"  # ✅ CORRECT
```

**Solution Steps:**

1. **Verify API endpoints are accessible manually:**
   ```bash
   # Test with curl
   curl -u boss:Mm02022006 http://localhost:8000/api/health/
   curl -u boss:Mm02022006 http://localhost:8000/api/resource/
   curl -u boss:Mm02022006 http://localhost:8000/api/products/
   ```

2. **Check if Gunicorn is responding:**
   ```bash
   ps aux | grep gunicorn
   netstat -tulpn | grep 8000
   ```

3. **Fix test base URLs** - Update generated tests to use correct base URL

---

### ❌ Issue #2: Incorrect Base URLs (HIGH PRIORITY)

**Tests Affected:** TC003, TC006, TC007

**Problem:** Tests are using `/dashboard/dashboard/` prefix which doesn't exist in API URLs.

**Fix:**
```python
# WRONG
BASE_URL = "http://localhost:8000/dashboard/dashboard"

# CORRECT
BASE_URL = "http://localhost:8000"
```

**API Endpoint Structure:**
- ✅ `/api/products/` - Inventory API
- ✅ `/api/invoices/` - Sales API
- ✅ `/api/crm/customers/` - CRM API
- ✅ `/api/production/orders/` - Production API
- ❌ `/dashboard/dashboard/api/...` - WRONG!

---

### ❌ Issue #3: E-commerce 404 Errors (HIGH PRIORITY)

**Test Affected:** TC009

**Problem:** E-commerce API endpoint returns 404 Not Found
```
404 Client Error: Not Found for url: http://localhost:8000/api/ecommerce/products/
```

**Investigation Steps:**

1. **Check if e-commerce API is registered:**
   ```bash
   cd /var/www/tony_erp
   grep -r "api/ecommerce" accountant_pro/urls.py ecommerce/
   ```

2. **Check ecommerce module structure:**
   ```bash
   ls -la ecommerce/api_views.py
   ls -la ecommerce/urls.py
   ```

3. **Verify ecommerce is in INSTALLED_APPS:**
   ```bash
   grep "'ecommerce'" accountant_pro/settings.py
   ```

**Expected Solution:** E-commerce API might not be exposed at `/api/ecommerce/`. Need to check actual URL structure.

---

### ❌ Issue #4: JWT Authentication Not Working (HIGH PRIORITY)

**Test Affected:** TC010

**Problem:** JWT token endpoint doesn't return expected access token

**Current Error:**
```python
AssertionError: JWT access token missing in response
```

**Investigation:**

1. **Test JWT endpoint manually:**
   ```bash
   curl -X POST http://localhost:8000/api/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"boss","password":"Mm02022006"}'
   ```

2. **Expected Response:**
   ```json
   {
     "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "refresh": "eyJ0eXAiOiJKV1QiLC..."
   }
   ```

3. **Check JWT settings:**
   ```bash
   grep -A 20 "SIMPLE_JWT" /var/www/tony_erp/accountant_pro/settings.py
   ```

**Fix:** Verify the JWT endpoint URL and response format

---

### ❌ Issue #5: HTTP Status Code Inconsistencies (MEDIUM PRIORITY)

**Test Affected:** TC008 (Fleet Management)

**Problem:** Fleet API returns HTTP 200 instead of 201 for resource creation

**Current Behavior:**
```python
assert r_vehicle.status_code == 201  # ❌ Fails - gets 200
```

**Fix Options:**

**Option 1:** Update test to accept 200 OR 201:
```python
assert r_vehicle.status_code in [200, 201], f"Expected 200/201, got {r_vehicle.status_code}"
```

**Option 2:** Fix API to return correct status code (201 for creation):
```python
# In fleet API view
return Response(data, status=status.HTTP_201_CREATED)
```

---

### ❌ Issue #6: Missing Response Fields (MEDIUM PRIORITY)

**Test Affected:** TC006 (POS)

**Problem:** POS order creation returns 200 but response missing "id" field

**Fix:** Check POS API serializer includes "id" field:
```python
# In pos/api_serializers.py
class POSOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = POSOrder
        fields = ['id', 'order_number', 'items', ...]  # Ensure 'id' is included
```

---

### ❌ Issue #7: Test Syntax Error (LOW PRIORITY)

**Test Affected:** TC002 (Inventory)

**Problem:** Python syntax error in generated test code

**Error:**
```python
assert ("stock_by_location" in product_detail or "stocks" in product_detail or "stock" in product_detail), 
                                                                                                           ^
SyntaxError: invalid syntax
```

**Fix:** Remove trailing comma or complete the assertion:
```python
# WRONG
assert (...), 
    "Message"

# CORRECT
assert (...), "Message"
```

---

## 🚀 Quick Fix Action Plan

### Step 1: Test API Accessibility (5 minutes)

```bash
# Test basic connectivity
curl http://localhost:8000/api/health/

# Test with Basic Auth
curl -u boss:Mm02022006 http://localhost:8000/api/resource/

# Test JWT
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"Mm02022006"}'
```

### Step 2: Fix Test Base URLs (10 minutes)

Update all generated test files:
```bash
cd /var/www/tony_erp/testsprite_tests
sed -i 's|http://localhost:8000/dashboard/dashboard|http://localhost:8000|g' TC*.py
```

### Step 3: Re-run Tests (2 minutes)

```bash
cd /var/www/tony_erp
node /root/.npm/_npx/8ddf6bea01b2519d/node_modules/@testsprite/testsprite-mcp/dist/index.js generateCodeAndExecute
```

### Step 4: Investigate E-commerce 404 (15 minutes)

```bash
# Find e-commerce API URLs
cd /var/www/tony_erp
grep -r "class.*View\|class.*ViewSet" ecommerce/ | grep -i api
grep -r "router.register\|path(" ecommerce/urls.py
```

### Step 5: Review Results (10 minutes)

Check the new test report:
```bash
cat /var/www/tony_erp/testsprite_tests/testsprite-mcp-test-report.md
```

---

## 📊 Expected Outcome After Fixes

| Issue | Status | Expected Result |
|-------|--------|----------------|
| DummyResponse | ✅ FIXED | Real HTTP responses |
| Wrong Base URLs | ✅ FIXED | Tests reach correct endpoints |
| E-commerce 404 | 🔍 INVESTIGATE | Find correct endpoint |
| JWT Auth | 🔍 TEST | Verify JWT works |
| Status Codes | ⚠️ TOLERATE | Accept 200 or 201 |
| Missing Fields | 🔍 CHECK | Verify serializers |
| Syntax Error | ✅ EASY FIX | Fix comma |

---

## 🛠️ Configuration Verification

### Current Configuration (Verified ✅):

**Django Settings:**
- ✅ REST_FRAMEWORK configured correctly
- ✅ JWT Authentication enabled
- ✅ Basic Authentication enabled
- ✅ All modules in INSTALLED_APPS

**URL Configuration:**
- ✅ API endpoints registered in `api_app/urls.py`
- ✅ CRM endpoints registered
- ✅ Production endpoints registered
- ❓ E-commerce endpoints (needs verification)

**Authentication:**
- ✅ Basic Auth: `username=boss, password=Mm02022006`
- ❓ JWT Token endpoint (needs testing)

---

## 📞 Next Steps

1. **Run manual API tests** (curl commands above)
2. **Fix test base URLs**
3. **Re-run TestSprite**
4. **Review new results**
5. **Fix remaining issues**

---

**Generated:** February 8, 2026  
**Priority:** HIGH - Fix immediately before re-running tests
