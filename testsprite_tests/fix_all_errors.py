#!/usr/bin/env python3
"""
إصلاح شامل لجميع الأخطاء المكتشفة في الاختبارات
"""
import os
import re

print("🔧 بدء إصلاح جميع الأخطاء المكتشفة...\n")

fixes_applied = []
errors = []

# ==========================================
# 1. إصلاح TC002 - المخزون (Pagination)
# ==========================================
print("1️⃣ إصلاح TC002 - المخزون (Pagination)...")
try:
    tc002_file = 'TC002_validate_inventory_product_listing_and_stock_management.py'
    with open(tc002_file, 'r') as f:
        content = f.read()
    
    # إصلاح الاستجابة للتعامل مع Pagination
    if 'assert isinstance(products_data, list)' in content:
        content = re.sub(
            r'assert isinstance\(products_data, list\), "Products response should be a list"',
            '''# Handle paginated response
        if isinstance(products_data, dict):
            products_data = products_data.get("results", [])
        assert isinstance(products_data, list), "Products should be a list"''',
            content
        )
        
        # إصلاح البحث في جميع الصفحات
        old_search = r'found_product = next\(\(p for p in products_data if p\.get\("id"\) == product_id\), None\)'
        new_search = '''# Search in all pages
        found_product = None
        current_page_products = products_data
        while current_page_products:
            found_product = next((p for p in current_page_products if p.get("id") == product_id), None)
            if found_product:
                break
            # Get next page if exists
            if isinstance(products_resp.json(), dict) and products_resp.json().get("next"):
                products_resp = requests.get(products_resp.json()["next"], auth=AUTH, headers=headers, timeout=TIMEOUT)
                current_page_products = products_resp.json().get("results", [])
            else:
                break'''
        
        if re.search(r'found_product = next\(\(p for p in', content):
            content = re.sub(old_search, new_search, content)
        
        with open(tc002_file, 'w') as f:
            f.write(content)
        
        fixes_applied.append("✅ TC002 - إصلاح Pagination")
        print("   ✅ تم إصلاح TC002\n")
except Exception as e:
    errors.append(f"❌ TC002: {e}")
    print(f"   ❌ خطأ: {e}\n")

# ==========================================
# 2. إصلاح TC009 - التجارة الإلكترونية
# ==========================================
print("2️⃣ إصلاح TC009 - التجارة الإلكترونية...")
try:
    tc009_file = 'TC009_ecommerce_product_catalog_and_order_management.py'
    if os.path.exists(tc009_file):
        with open(tc009_file, 'r') as f:
            content = f.read()
        
        # تصحيح مسار categories
        content = re.sub(
            r'/store/api/categories/',
            '/store/api/product-categories/',
            content
        )
        
        with open(tc009_file, 'w') as f:
            f.write(content)
        
        fixes_applied.append("✅ TC009 - إصلاح مسار Categories")
        print("   ✅ تم إصلاح TC009\n")
except Exception as e:
    errors.append(f"❌ TC009: {e}")
    print(f"   ❌ خطأ: {e}\n")

# ==========================================
# 3. إصلاح TC001 - المبيعات
# ==========================================
print("3️⃣ إصلاح TC001 - المبيعات (خطأ 500)...")
try:
    tc001_file = 'TC001_verify_sales_invoice_creation_and_approval.py'
    if os.path.exists(tc001_file):
        with open(tc001_file, 'r') as f:
            content = f.read()
        
        # إضافة الحقول المطلوبة للفاتورة
        # البحث عن invoice_payload وإضافة الحقول الناقصة
        if 'invoice_payload' in content and 'customer' in content:
            # إضافة company إذا كانت مطلوبة
            if '"company":' not in content:
                content = re.sub(
                    r'("customer":\s*\d+,)',
                    r'\1\n            "company": 1,  # Added required company field',
                    content
                )
            
            # التأكد من وجود location
            if '"location":' not in content:
                content = re.sub(
                    r'("customer":\s*\d+,)',
                    r'\1\n            "location": 1,  # Added required location field',
                    content
                )
        
        with open(tc001_file, 'w') as f:
            f.write(content)
        
        fixes_applied.append("✅ TC001 - إضافة حقول مطلوبة")
        print("   ✅ تم إصلاح TC001\n")
except Exception as e:
    errors.append(f"❌ TC001: {e}")
    print(f"   ❌ خطأ: {e}\n")

# ==========================================
# إنشاء ملف إعدادات لـ CSRF
# ==========================================
print("4️⃣ إنشاء ملف إعدادات CSRF للاختبارات...")
try:
    csrf_helper = '''#!/usr/bin/env python3
"""
مساعد CSRF للاختبارات التي تحتاج CSRF token
"""
import requests
from requests.auth import HTTPBasicAuth

def get_csrf_token(base_url, auth):
    """الحصول على CSRF token من الخادم"""
    session = requests.Session()
    session.auth = auth
    
    # الحصول على الصفحة الرئيسية للحصول على CSRF token
    response = session.get(f"{base_url}/dashboard/dashboard")
    
    if response.status_code == 200:
        # استخراج CSRF token من cookies
        csrf_token = session.cookies.get('csrftoken')
        return csrf_token, session
    
    return None, None

# مثال على الاستخدام:
# csrf_token, session = get_csrf_token("http://localhost:8000", HTTPBasicAuth("boss", "Mm02022006"))
# headers = {"X-CSRFToken": csrf_token}
# response = session.post(url, data=data, headers=headers)
'''
    
    with open('csrf_helper.py', 'w') as f:
        f.write(csrf_helper)
    
    fixes_applied.append("✅ إنشاء csrf_helper.py")
    print("   ✅ تم إنشاء csrf_helper.py\n")
except Exception as e:
    errors.append(f"❌ CSRF Helper: {e}")
    print(f"   ❌ خطأ: {e}\n")

# ==========================================
# النتيجة النهائية
# ==========================================
print("\n" + "="*60)
print("📊 ملخص الإصلاحات:")
print("="*60)
print(f"✅ تم تطبيق: {len(fixes_applied)} إصلاح")
for fix in fixes_applied:
    print(f"   {fix}")

if errors:
    print(f"\n❌ أخطاء: {len(errors)}")
    for error in errors:
        print(f"   {error}")

print("\n" + "="*60)
print("✅ انتهى إصلاح الأخطاء!")
print("="*60)
