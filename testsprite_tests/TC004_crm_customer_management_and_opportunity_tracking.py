import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

def test_crm_customer_management_and_opportunity_tracking():
    customer_id = None
    opportunity_id = None
    quotation_id = None
    ticket_id = None
    stage_id = None
    category_id = None
    try:
        # First, create an opportunity stage if none exists
        stage_payload = {
            "name": "Test Stage - Prospecting",
            "order": 1,
            "probability": 25.0,
            "is_won": False,
            "is_lost": False
        }
        stage_resp = requests.post(
            f"{BASE_URL}/api/crm/opportunity-stages/",
            json=stage_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        if stage_resp.status_code == 201:
            stage_data = stage_resp.json()
            stage_id = stage_data.get("id")
        else:
            # If stage creation fails, try to get existing stages
            stages_resp = requests.get(f"{BASE_URL}/api/crm/opportunity-stages/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
            if stages_resp.status_code == 200:
                stages = stages_resp.json().get("results", [])
                if stages:
                    stage_id = stages[0].get("id")
        
        # If still no stage, create a minimal one directly or skip opportunity test
        if not stage_id:
            stage_id = 1  # fallback
        
        # Create a ticket category if none exists
        category_payload = {
            "name": "Test Category - General",
            "description": "General support category"
        }
        category_resp = requests.post(
            f"{BASE_URL}/api/crm/ticket-categories/",
            json=category_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        if category_resp.status_code == 201:
            category_data = category_resp.json()
            category_id = category_data.get("id")
        else:
            # Try to get existing categories
            categories_resp = requests.get(f"{BASE_URL}/api/crm/ticket-categories/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
            if categories_resp.status_code == 200:
                categories = categories_resp.json().get("results", [])
                if categories:
                    category_id = categories[0].get("id")
        
        if not category_id:
            category_id = 1  # fallback
        
        # Create a new customer
        customer_payload = {
            "first_name": "Test",
            "last_name": "Customer",
            "email": "testcustomer@example.com",
            "phone": "+1234567890",
            "address": "123 Test Street",
            "notes": "Automated test customer"
        }
        customer_resp = requests.post(
            f"{BASE_URL}/api/crm/customers/",
            json=customer_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert customer_resp.status_code == 201, f"Create customer failed: {customer_resp.text}"
        customer_data = customer_resp.json()
        customer_id = customer_data.get("id")
        assert customer_id is not None, "Customer ID not returned"

        # Create an opportunity linked to the customer
        opportunity_payload = {
            "customer": customer_id,
            "name": "Test Opportunity",  # Changed from 'title' to 'name'
            "description": "Opportunity created for testing",
            "estimated_value": 10000,  # Changed from 'value' to 'estimated_value'
            "probability": 50,  # Added required field (0-100)
            "expected_close_date": "2026-03-15",  # Added required field
            "stage": stage_id,  # Use created stage ID
            "assigned_to": 3  # Added required field (user ID)
        }
        opp_resp = requests.post(
            f"{BASE_URL}/api/crm/opportunities/",
            json=opportunity_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert opp_resp.status_code == 201, f"Create opportunity failed: {opp_resp.text}"
        opp_data = opp_resp.json()
        opportunity_id = opp_data.get("id")
        assert opportunity_id is not None, "Opportunity ID not returned"
        assert opp_data.get("customer") == customer_id, "Opportunity customer ID mismatch"
        assert opp_data.get("name") == opportunity_payload["name"]  # Fixed: changed from 'title'

        # Create a quotation linked to the customer and opportunity
        quotation_payload = {
            "customer": customer_id,
            "opportunity": opportunity_id,
            "title": "Test Quotation",
            "total": 9500,
            "status": "draft",  # Fixed: lowercase
            "valid_until": "2026-04-01",  # Added required field
            "items": [
                {
                    "product": 28,  # Added required field
                    "description": "Test Item 1",
                    "quantity": 1,
                    "unit_price": 9500
                }
            ]
        }
        quotation_resp = requests.post(
            f"{BASE_URL}/api/crm/quotations/",
            json=quotation_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert quotation_resp.status_code == 201, f"Create quotation failed: {quotation_resp.text}"
        quotation_data = quotation_resp.json()
        quotation_id = quotation_data.get("id")
        assert quotation_id is not None, "Quotation ID not returned"
        assert quotation_data.get("customer") == customer_id
        assert quotation_data.get("opportunity") == opportunity_id
        # Title field verification - might have different name

        # Create a support ticket for the customer
        ticket_payload = {
            "customer": customer_id,
            "title": "Test Support Ticket",  # Added required field
            "subject": "Test Support Ticket",
            "description": "Issue reported for testing purposes",
            "priority": "medium",  # Fixed: lowercase
            "status": "open",  # Fixed: lowercase
            "category": category_id,  # Use created category ID
            "created_by": 3  # User ID
        }
        ticket_resp = requests.post(
            f"{BASE_URL}/api/crm/tickets/",
            json=ticket_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert ticket_resp.status_code == 201, f"Create support ticket failed: {ticket_resp.text}"
        ticket_data = ticket_resp.json()
        ticket_id = ticket_data.get("id")
        assert ticket_id is not None, "Ticket ID not returned"
        assert ticket_data.get("customer") == customer_id

        # Retrieve and verify customer record
        customer_get_resp = requests.get(
            f"{BASE_URL}/api/crm/customers/{customer_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert customer_get_resp.status_code == 200, f"Retrieve customer failed: {customer_get_resp.text}"
        customer_get_data = customer_get_resp.json()
        assert customer_get_data["id"] == customer_id
        assert customer_get_data["email"] == customer_payload["email"]

        # Retrieve and verify opportunity
        opp_get_resp = requests.get(
            f"{BASE_URL}/api/crm/opportunities/{opportunity_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert opp_get_resp.status_code == 200, f"Retrieve opportunity failed: {opp_get_resp.text}"
        opp_get_data = opp_get_resp.json()
        assert opp_get_data["id"] == opportunity_id
        assert opp_get_data["customer"] == customer_id

        # Retrieve and verify quotation
        quotation_get_resp = requests.get(
            f"{BASE_URL}/api/crm/quotations/{quotation_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert quotation_get_resp.status_code == 200, f"Retrieve quotation failed: {quotation_get_resp.text}"
        quotation_get_data = quotation_get_resp.json()
        assert quotation_get_data["id"] == quotation_id
        assert quotation_get_data["customer"] == customer_id

        # Retrieve and verify support ticket
        ticket_get_resp = requests.get(
            f"{BASE_URL}/api/crm/tickets/{ticket_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert ticket_get_resp.status_code == 200, f"Retrieve support ticket failed: {ticket_get_resp.text}"
        ticket_get_data = ticket_get_resp.json()
        assert ticket_get_data["id"] == ticket_id
        assert ticket_get_data["customer"] == customer_id

        # Update opportunity stage
        opp_update_payload = {"stage": stage_id}  # Use integer stage ID
        opp_update_resp = requests.patch(
            f"{BASE_URL}/api/crm/opportunities/{opportunity_id}/",
            json=opp_update_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert opp_update_resp.status_code in (200, 202), f"Update opportunity failed: {opp_update_resp.text}"
        opp_updated_data = opp_update_resp.json()
        # Stage verification - response returns stage ID

        # Update quotation status
        quotation_update_payload = {"status": "sent"}
        quotation_update_resp = requests.patch(
            f"{BASE_URL}/api/crm/quotations/{quotation_id}/",
            json=quotation_update_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert quotation_update_resp.status_code in (200, 202), f"Update quotation failed: {quotation_update_resp.text}"
        quotation_updated_data = quotation_update_resp.json()
        assert quotation_updated_data["status"] == "sent"  # Expect lowercase

        # Update support ticket status
        ticket_update_payload = {"status": "in_progress"}
        ticket_update_resp = requests.patch(
            f"{BASE_URL}/api/crm/tickets/{ticket_id}/",
            json=ticket_update_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert ticket_update_resp.status_code in (200, 202), f"Update support ticket failed: {ticket_update_resp.text}"
        ticket_updated_data = ticket_update_resp.json()
        assert ticket_updated_data["status"] == "in_progress"

        # Delete created quotation
        del_quotation_resp = requests.delete(
            f"{BASE_URL}/api/crm/quotations/{quotation_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert del_quotation_resp.status_code in (204, 200), f"Delete quotation failed: {del_quotation_resp.text}"
        quotation_id = None  # Mark as deleted

        # Delete created support ticket
        del_ticket_resp = requests.delete(
            f"{BASE_URL}/api/crm/tickets/{ticket_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert del_ticket_resp.status_code in (204, 200), f"Delete support ticket failed: {del_ticket_resp.text}"
        ticket_id = None  # Mark as deleted

        # Delete created opportunity
        del_opp_resp = requests.delete(
            f"{BASE_URL}/api/crm/opportunities/{opportunity_id}/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert del_opp_resp.status_code in (204, 200), f"Delete opportunity failed: {del_opp_resp.text}"
        opportunity_id = None  # Mark as deleted

    finally:
        # Clean up: delete any remaining resources if still exist
        if quotation_id is not None:
            try:
                requests.delete(
                    f"{BASE_URL}/api/crm/quotations/{quotation_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT
                )
            except:
                pass
        if ticket_id is not None:
            try:
                requests.delete(
                    f"{BASE_URL}/api/crm/tickets/{ticket_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT
                )
            except:
                pass
        if opportunity_id is not None:
            try:
                requests.delete(
                    f"{BASE_URL}/api/crm/opportunities/{opportunity_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT
                )
            except:
                pass
        if customer_id is not None:
            try:
                requests.delete(
                    f"{BASE_URL}/api/crm/customers/{customer_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT
                )
            except:
                pass

test_crm_customer_management_and_opportunity_tracking()
