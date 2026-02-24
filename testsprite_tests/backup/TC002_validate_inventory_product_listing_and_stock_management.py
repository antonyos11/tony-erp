import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30

def test_validate_inventory_product_listing_and_stock_management():
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    product = None
    stock_move_id = None
    stock_addition_id = None
    location_id = None

    try:
        # 1. List products and confirm structure including stock per location
        products_resp = requests.get(f"{BASE_URL}/api/products/", auth=AUTH, headers=headers, timeout=TIMEOUT)
        assert products_resp.status_code == 200, f"Failed to list products: {products_resp.text}"
        products_data = products_resp.json()
        assert isinstance(products_data, list), "Products response should be a list"

        # If no products, create one to test stock behaviors
        if not products_data:
            # Create a product (minimal fields assumed)
            product_payload = {
                "name": "Test Product TC002",
                "sku": "TC002-SKU-001",
                "description": "Test product for TC002",
                "price": 10.0,
                "category": None  # If category is required, it can be created or adjusted
            }
            create_product_resp = requests.post(f"{BASE_URL}/api/products/", auth=AUTH, json=product_payload, headers=headers, timeout=TIMEOUT)
            assert create_product_resp.status_code in (200,201), f"Failed to create a product for testing: {create_product_resp.text}"
            product = create_product_resp.json()
        else:
            product = products_data[0]

        product_id = product["id"] if "id" in product else product.get("pk") or product.get("ID")
        assert product_id, "Product ID not found"

        # 2. List locations to get a valid location for stock operations
        locations_resp = requests.get(f"{BASE_URL}/api/locations/", auth=AUTH, headers=headers, timeout=TIMEOUT)
        assert locations_resp.status_code == 200, f"Failed to list locations: {locations_resp.text}"
        locations_data = locations_resp.json()
        assert isinstance(locations_data, list) and len(locations_data) > 0, "At least one location should exist"
        location = locations_data[0]
        location_id = location.get("id") or location.get("pk") or location.get("ID")
        assert location_id, "Location ID not found"

        # 3. Check stock details on product
        # Assume product stock details include stock quantities by location or a stock field (field names may vary)
        # Confirm stock details structure if possible
        product_detail_resp = requests.get(f"{BASE_URL}/api/products/{product_id}/", auth=AUTH, headers=headers, timeout=TIMEOUT)
        assert product_detail_resp.status_code == 200, f"Failed to get product details: {product_detail_resp.text}"
        product_detail = product_detail_resp.json()
        assert ("stock_by_location" in product_detail or "stocks" in product_detail or "stock" in product_detail), 
            "Product detail should include stock information by location"

        # 4. Perform a stock movement via /api/stock/ endpoint (stock transfer or adjustment)
        stock_move_payload = {
            "product": product_id,
            "from_location": location_id,
            "to_location": location_id,
            "quantity": 1,
            "reason": "Test stock movement for TC002"
        }
        stock_move_resp = requests.post(f"{BASE_URL}/api/stock/", auth=AUTH, json=stock_move_payload, headers=headers, timeout=TIMEOUT)
        assert stock_move_resp.status_code in (200, 201), f"Failed to create stock movement: {stock_move_resp.text}"
        stock_move = stock_move_resp.json()
        stock_move_id = stock_move.get("id") or stock_move.get("pk") or stock_move.get("ID")
        assert stock_move_id, "Stock movement ID not found"

        # 5. Perform a stock addition via /api/inventory/additions/
        stock_add_payload = {
            "product": product_id,
            "location": location_id,
            "quantity": 5,
            "reference": "TC002 Stock Addition",
            "notes": "Adding stock for test case TC002"
        }
        stock_add_resp = requests.post(f"{BASE_URL}/api/inventory/additions/", auth=AUTH, json=stock_add_payload, headers=headers, timeout=TIMEOUT)
        assert stock_add_resp.status_code in (200, 201), f"Failed to create stock addition: {stock_add_resp.text}"
        stock_addition = stock_add_resp.json()
        stock_addition_id = stock_addition.get("id") or stock_addition.get("pk") or stock_addition.get("ID")
        assert stock_addition_id, "Stock addition ID not found"

        # 6. Verify product stock updated correctly after addition
        product_after_add_resp = requests.get(f"{BASE_URL}/api/products/{product_id}/", auth=AUTH, headers=headers, timeout=TIMEOUT)
        assert product_after_add_resp.status_code == 200, f"Failed to get product details after stock addition: {product_after_add_resp.text}"
        product_after_add = product_after_add_resp.json()
        # Check stock increased by at least the addition quantity at the location
        # Extract stock info
        stocks_info = product_after_add.get("stock_by_location") or product_after_add.get("stocks") or product_after_add.get("stock")
        assert stocks_info, "No stock info found after addition"
        stock_qty = 0
        if isinstance(stocks_info, list):
            for s in stocks_info:
                loc = s.get("location") if isinstance(s, dict) else None
                if loc == location_id or (loc and (loc == location.get("id") or loc == location.get("pk"))):
                    stock_qty = s.get("quantity") or s.get("qty") or 0
                    break
        elif isinstance(stocks_info, dict):
            stock_qty = stocks_info.get(str(location_id)) or stocks_info.get("quantity") or 0
        else:
            stock_qty = stocks_info or 0
        assert stock_qty >= 5, f"Expected stock quantity >= 5 after addition, got {stock_qty}"

        # 7. Verify low-stock alerts if any field or endpoint for alerts is present (optional)
        # Since no direct endpoint is given for low-stock alerts, check product field named low_stock or alert flags
        low_stock_flag = product_after_add.get("low_stock") or product_after_add.get("is_low_stock") or False
        assert isinstance(low_stock_flag, bool), "Low stock flag should be boolean if present"

    finally:
        # Cleanup: delete stock movements and additions if possible, then product if created here
        if stock_move_id:
            requests.delete(f"{BASE_URL}/api/stock/{stock_move_id}/", auth=AUTH, headers=headers, timeout=TIMEOUT)

        if stock_addition_id:
            requests.delete(f"{BASE_URL}/api/inventory/additions/{stock_addition_id}/", auth=AUTH, headers=headers, timeout=TIMEOUT)

        if product and "name" in product and product["name"] == "Test Product TC002":
            pid = product.get("id") or product.get("pk") or product.get("ID")
            if pid:
                requests.delete(f"{BASE_URL}/api/products/{pid}/", auth=AUTH, headers=headers, timeout=TIMEOUT)

test_validate_inventory_product_listing_and_stock_management()
