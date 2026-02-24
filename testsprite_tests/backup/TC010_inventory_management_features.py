import requests
import json
import random

BASE_URL = "http://localhost:8000"
AUTH = ("boss", "Mm02022006")
HEADERS_JSON = {"Content-Type": "application/json"}
TIMEOUT = 30

def test_inventory_management_features():
    print("Starting TC010: Inventory Management Features Test")
    
    suffix = random.randint(10000, 99999)
    created_resources = {"products": [], "locations": [], "stocks": []}

    try:
        # 1. Create Product
        print("\n1. Creating Product...")
        product_payload = {
            "name": f"TC10 Product {suffix}",
            "sku": f"TC10-SKU-{suffix}",
            "description": "Inventory Management Test Product",
            "price": 25.00,
            "cost": 15.00,
            "product_type": "finished"
        }
        r = requests.post(f"{BASE_URL}/api/products/", auth=AUTH, headers=HEADERS_JSON, json=product_payload, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to create product: {r.status_code} {r.text}"
        product_id = r.json()["id"]
        created_resources["products"].append(product_id)
        print(f"   Created Product ID: {product_id}")

        # 2. Create Location (Warehouse)
        print("\n2. Creating Location (Warehouse)...")
        location_payload = {
            "name": f"TC10 Warehouse {suffix}",
            "code": f"LOC-TC10-{suffix}",
            "type": "store",
            "address": "Test Address"
        }
        r = requests.post(f"{BASE_URL}/api/locations/", auth=AUTH, headers=HEADERS_JSON, json=location_payload, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to create location: {r.status_code} {r.text}"
        location_id = r.json()["id"]
        created_resources["locations"].append(location_id)
        print(f"   Created Location ID: {location_id}")

        # 3. Create Stock Record (Assign Stock)
        print("\n3. Creating Stock Record...")
        stock_payload = {
            "product": product_id,
            "location": location_id,
            "quantity": 50
        }
        r = requests.post(f"{BASE_URL}/api/stock/", auth=AUTH, headers=HEADERS_JSON, json=stock_payload, timeout=TIMEOUT)
        assert r.status_code == 201, f"Failed to create stock: {r.status_code} {r.text}"
        stock_id = r.json()["id"]
        created_resources["stocks"].append(stock_id)
        print(f"   Created Stock ID: {stock_id} with Quantity 50")

        # 4. Verify Stock via Product Details
        print("\n4. Verifying Stock in Product Details...")
        r = requests.get(f"{BASE_URL}/api/products/{product_id}/", auth=AUTH, timeout=TIMEOUT)
        assert r.status_code == 200, f"Failed to get product details: {r.status_code}"
        product_data = r.json()
        current_stock = product_data.get("current_stock")
        print(f"   Product Current Stock: {current_stock}")
        # Note: current_stock might be sum of all stocks.
        # Since this is a fresh product, it should be 50.
        assert float(current_stock) == 50.0, f"Expected stock 50, got {current_stock}"

        # 5. Update Stock Quantity
        print("\n5. Updating Stock Quantity...")
        update_payload = {"quantity": 75}
        r = requests.patch(f"{BASE_URL}/api/stock/{stock_id}/", auth=AUTH, headers=HEADERS_JSON, json=update_payload, timeout=TIMEOUT)
        assert r.status_code == 200, f"Failed to update stock: {r.status_code} {r.text}"
        print(f"   Stock updated to 75")
        
        # Verify update
        r = requests.get(f"{BASE_URL}/api/products/{product_id}/", auth=AUTH, timeout=TIMEOUT)
        current_stock = r.json().get("current_stock")
        print(f"   Product Current Stock after update: {current_stock}")
        assert float(current_stock) == 75.0, f"Expected stock 75, got {current_stock}"

        print("\nTC010 PASSED: Inventory Management Workflow Verified")

    except Exception as e:
        print(f"\nTC010 FAILED: {e}")
        raise e

    finally:
        print("\nCleaning up resources...")
        # Delete stocks first
        for sid in created_resources["stocks"]:
            requests.delete(f"{BASE_URL}/api/stock/{sid}/", auth=AUTH, timeout=TIMEOUT)
        
        # Delete products
        for pid in created_resources["products"]:
            requests.delete(f"{BASE_URL}/api/products/{pid}/", auth=AUTH, timeout=TIMEOUT)
            
        # Delete locations
        for lid in created_resources["locations"]:
            requests.delete(f"{BASE_URL}/api/locations/{lid}/", auth=AUTH, timeout=TIMEOUT)

if __name__ == "__main__":
    test_inventory_management_features()