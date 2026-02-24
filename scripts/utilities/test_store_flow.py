
import os
import requests
import json
from urllib.parse import urljoin

BASE_URL = "http://localhost:8000/store/"
PRODUCTS_URL = urljoin(BASE_URL, "products/")
CART_URL = urljoin(BASE_URL, "cart/")
CART_ADD_URL = urljoin(BASE_URL, "cart/add/")

def test_store():
    session = requests.Session()
    
    # 1. Home Page
    print(f"1. Fetching Store Home: {BASE_URL}")
    r = session.get(BASE_URL)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print("   PASS: Home page loaded.")
    else:
        print(f"   FAIL: Home page error ({r.status_code})")

    # 2. Products List
    print(f"2. Fetching Products List: {PRODUCTS_URL}")
    r = session.get(PRODUCTS_URL)
    print(f"   Status: {r.status_code}")
    
    product_url = None
    product_id = None
    
    if r.status_code == 200:
        print("   PASS: Products list loaded.")
        # Try to find a product link in HTML (simple string search for href="/store/product/")
        if '/store/product/' in r.text:
            # Extract first product ID roughly
            import re
            match = re.search(r'/store/product/(\d+)/', r.text)
            if match:
                product_id = match.group(1)
                product_url = urljoin(BASE_URL, f"product/{product_id}/")
                print(f"   found product ID: {product_id}")
    else:
        print(f"   FAIL: Products list error ({r.status_code})")

    # 3. Product Detail
    if product_url:
        print(f"3. Fetching Product Detail: {product_url}")
        r = session.get(product_url)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print("   PASS: Product detail loaded.")
        else:
            print(f"   FAIL: Product detail error")
    else:
        print("   SKIP: No product found to test detail view.")

    # 4. Add to Cart (CSRF needed)
    if product_id:
        print(f"4. Adding Product {product_id} to Cart")
        # Get CSRF from previous request cookies
        csrf = session.cookies.get('csrftoken')
        headers = {'Referer': product_url, 'X-CSRFToken': csrf}
        data = {'product_id': product_id, 'quantity': 1, 'csrfmiddlewaretoken': csrf}
        
        # Determine if it's AJAX or Form POST. Usually stores use AJAX for cart.
        # Let's try standard POST.
        r = session.post(CART_ADD_URL, data=data, headers=headers)
        print(f"   Status: {r.status_code}")
        try:
            print(f"   Response: {r.json()}")
        except:
            print(f"   Response length: {len(r.text)}")
            
        # Check Cart
        print(f"5. Checking Cart Page: {CART_URL}")
        r = session.get(CART_URL)
        print(f"   Status: {r.status_code}")
        if "items" in r.text or "السلة" in r.text or "cart" in r.text.lower():
             print("   PASS: Cart page loaded.")
        else:
             print("   WARN: Cart page might be empty or broken.")

if __name__ == "__main__":
    test_store()
