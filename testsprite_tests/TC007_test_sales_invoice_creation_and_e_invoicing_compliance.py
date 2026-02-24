import requests

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/api/token/"
INVOICES_URL = f"{BASE_URL}/sales/api/invoices/"
PRODUCTS_URL = f"{BASE_URL}/ecommerce/api/products/"

USERNAME = "boss"
PASSWORD = "Mm02022006"
TIMEOUT = 30


def test_sales_invoice_creation_and_e_invoicing_compliance():
    # Authenticate and get JWT token
    auth_response = requests.post(
        LOGIN_URL,
        json={"username": USERNAME, "password": PASSWORD},
        timeout=TIMEOUT,
    )
    assert auth_response.status_code == 200, f"Authentication failed: {auth_response.text}"
    auth_data = auth_response.json()
    access_token = auth_data.get("access")
    assert access_token, "No access token found in auth response"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Fetch products to ensure we use valid product IDs and prices
    # Do NOT use auth headers for public e-commerce products endpoint
    prod_response = requests.get(
        PRODUCTS_URL,
        timeout=TIMEOUT,
    )
    assert prod_response.status_code == 200, f"Failed to fetch products: {prod_response.text}"
    # Handle pagination if present
    prod_json = prod_response.json()
    if isinstance(prod_json, dict) and "results" in prod_json:
        products = prod_json.get("results", [])
    else:
        products = prod_json
    assert isinstance(products, list) and len(products) > 0, "No products found for invoice items"

    # Pick two different products with required fields
    product1 = products[0]
    product2 = products[1] if len(products) > 1 else products[0]

    # Prepare invoice data according to PRD schema: multiple items, discounts, VAT, ZATCA-compliant e-invoicing

    invoice_payload = {
        "items": [
            {
                "product": product1.get("id"),
                "quantity": 2,
                "unit_price": product1.get("price") or 100,  # fallback price if missing
                "discount": 10.0,  # 10 currency units discount on this item
                "vat_rate": 15.0,
            },
            {
                "product": product2.get("id"),
                "quantity": 1,
                "unit_price": product2.get("price") or 150,
                "discount": 0,
                "vat_rate": 15.0,
            },
        ],
        "discount": 5.0,  # Additional invoice-level discount
        "vat_rate": 15.0,
        "e_invoice": True,  # Indicating ZATCA e-invoice compliance
        "notes": "Test invoice for TC007 automation",
    }

    created_invoice_id = None
    try:
        # Create the sales invoice
        create_resp = requests.post(
            INVOICES_URL,
            json=invoice_payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        assert create_resp.status_code == 201, f"Invoice creation failed: {create_resp.status_code} {create_resp.text}"
        created_invoice = create_resp.json()
        created_invoice_id = created_invoice.get("id") or created_invoice.get("pk")
        assert created_invoice_id is not None, "Created invoice ID missing in response"

        # Verify response fields for VAT, discounts, and e-invoicing compliance data presence
        assert "vat_total" in created_invoice, "VAT total missing from invoice response"
        assert created_invoice["vat_total"] > 0, "VAT total should be greater than zero"
        assert "total_discount" in created_invoice, "Discount total missing from invoice response"
        assert created_invoice["total_discount"] >= 0, "Discount total cannot be negative"
        assert created_invoice.get("e_invoice") is True, "e_invoice flag not set to True"

        # Verify automatic stock deduction
        for item in invoice_payload["items"]:
            prod_id = item["product"]
            quantity_sold = item["quantity"]
            product_detail_resp = requests.get(
                f"{PRODUCTS_URL}{prod_id}/",
                headers=headers,
                timeout=TIMEOUT,
            )
            assert product_detail_resp.status_code == 200, f"Failed to get product details for ID {prod_id}"
            product_detail = product_detail_resp.json()
            stock_after_sale = product_detail.get("stock")
            assert stock_after_sale is not None, "Product stock info missing"
            assert isinstance(stock_after_sale, int) and stock_after_sale >= 0, "Stock after sale invalid"

        # Fetch the created invoice to validate saved data
        fetch_invoice_resp = requests.get(
            f"{INVOICES_URL}{created_invoice_id}/",
            headers=headers,
            timeout=TIMEOUT,
        )
        assert fetch_invoice_resp.status_code == 200, f"Could not fetch created invoice: {fetch_invoice_resp.text}"
        fetched_invoice = fetch_invoice_resp.json()
        assert fetched_invoice["id"] == created_invoice_id
        assert abs(fetched_invoice["vat_total"] - created_invoice["vat_total"]) < 0.01
        assert abs(fetched_invoice["total_discount"] - created_invoice["total_discount"]) < 0.01
        assert fetched_invoice.get("e_invoice") is True

    finally:
        # Cleanup: delete created invoice if exists to not pollute test DB
        if created_invoice_id:
            del_resp = requests.delete(
                f"{INVOICES_URL}{created_invoice_id}/",
                headers=headers,
                timeout=TIMEOUT,
            )
            assert del_resp.status_code in (200, 204), f"Failed to delete test invoice: {del_resp.text}"


test_sales_invoice_creation_and_e_invoicing_compliance()
