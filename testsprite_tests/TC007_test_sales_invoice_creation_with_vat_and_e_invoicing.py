import requests
import json

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/api/token/"
SALES_INVOICE_URL = f"{BASE_URL}/sales/api/invoices/"
HEADERS_JSON = {"Content-Type": "application/json"}
USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30


def get_jwt_token():
    payload = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(AUTH_URL, json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    tokens = response.json()
    access_token = tokens.get("access")
    if not access_token:
        raise Exception("Failed to obtain access token.")
    return access_token


def create_sample_customer(token):
    # Create a customer required for sales invoice if needed
    # Assuming endpoint /sales/api/customers/ with minimal required fields
    url = f"{BASE_URL}/sales/api/customers/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    customer_data = {
        "name": "Test Customer VAT E-Invoice",
        "customer_type": "retail",
        "email": "testcustomer@example.com",
        "phone": "1234567890"
    }
    response = requests.post(url, json=customer_data, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["id"]


def create_sample_product(token, sku, name, price, stock_qty):
    # Create a product required for invoice items
    url = f"{BASE_URL}/inventory/api/products/"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    product_data = {
        "sku": sku,
        "name": name,
        "price": price,
        "product_type": "finished",  # Assuming finished good
        "uom": "pcs",
        "stock": stock_qty
    }
    response = requests.post(url, json=product_data, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["id"]


def get_product_stock(token, product_id):
    url = f"{BASE_URL}/inventory/api/products/{product_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json().get("stock", 0)


def delete_resource(token, url):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(url, headers=headers, timeout=TIMEOUT)
    # Accept 204 No Content or 200 OK
    if response.status_code not in (200, 204):
        raise Exception(f"Failed to delete resource at {url}, status code {response.status_code}")


def test_sales_invoice_creation_with_vat_and_einvoicing():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Setup: Create customer and products
    customer_id = create_sample_customer(token)
    product1_id = create_sample_product(token, "SKU-001", "Mattress Model A", 1500.00, 50)
    product2_id = create_sample_product(token, "SKU-002", "Bed Frame Model X", 800.00, 30)

    invoice_url = SALES_INVOICE_URL
    created_invoice_id = None

    try:
        # Retrieve stock before invoice creation
        stock_p1_before = get_product_stock(token, product1_id)
        stock_p2_before = get_product_stock(token, product2_id)

        invoice_payload = {
            "customer": customer_id,
            "invoice_date": "2026-02-12",
            "due_date": "2026-03-12",
            "discount": 100.00,
            "vat_rate": 0.15,  # 15% VAT
            "items": [
                {
                    "product": product1_id,
                    "description": "Mattress Model A - Queen size",
                    "quantity": 2,
                    "unit_price": 1500.00,
                    "discount": 50.00
                },
                {
                    "product": product2_id,
                    "description": "Bed Frame Model X - King size",
                    "quantity": 1,
                    "unit_price": 800.00,
                    "discount": 0.00
                }
            ],
            "e_invoicing": True  # Request ZATCA-compliant e-invoice generation
        }

        response = requests.post(invoice_url, headers=headers, json=invoice_payload, timeout=TIMEOUT)
        assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}"
        invoice_data = response.json()

        created_invoice_id = invoice_data.get("id")
        assert created_invoice_id is not None, "Invoice ID missing in response"

        # Validate VAT calculation
        total_before_discount = (2 * 1500.00) + (1 * 800.00)
        total_item_discounts = 50.00 + 0.00
        subtotal_after_item_discount = total_before_discount - total_item_discounts
        subtotal_after_invoice_discount = subtotal_after_item_discount - 100.00
        expected_vat = round(subtotal_after_invoice_discount * 0.15, 2)
        returned_vat = round(invoice_data.get("vat_amount", 0), 2)
        assert expected_vat == returned_vat, f"Expected VAT {expected_vat}, got {returned_vat}"

        # Validate total amount including VAT
        expected_total = round(subtotal_after_invoice_discount + expected_vat, 2)
        returned_total = round(invoice_data.get("total_amount", 0), 2)
        assert expected_total == returned_total, f"Expected total {expected_total}, got {returned_total}"

        # Validate e-invoicing fields presence (ZATCA compliance)
        einvoice_data = invoice_data.get("e_invoice_data")
        assert einvoice_data is not None, "E-Invoicing data missing in response"
        assert "qr_code" in einvoice_data, "QR code missing in e-invoice data"
        assert "signed_invoice" in einvoice_data, "Signed invoice missing in e-invoice data"

        # Validate automatic stock deduction
        stock_p1_after = get_product_stock(token, product1_id)
        stock_p2_after = get_product_stock(token, product2_id)

        assert stock_p1_after == stock_p1_before - 2, f"Product1 stock should deduct by 2. Before: {stock_p1_before}, After: {stock_p1_after}"
        assert stock_p2_after == stock_p2_before - 1, f"Product2 stock should deduct by 1. Before: {stock_p2_before}, After: {stock_p2_after}"

    finally:
        # Cleanup: Delete invoice and created products, customer
        if created_invoice_id:
            delete_resource(token, f"{SALES_INVOICE_URL}{created_invoice_id}/")
        try:
            delete_resource(token, f"{BASE_URL}/sales/api/customers/{customer_id}/")
        except Exception:
            pass
        try:
            delete_resource(token, f"{BASE_URL}/inventory/api/products/{product1_id}/")
        except Exception:
            pass
        try:
            delete_resource(token, f"{BASE_URL}/inventory/api/products/{product2_id}/")
        except Exception:
            pass


test_sales_invoice_creation_with_vat_and_einvoicing()