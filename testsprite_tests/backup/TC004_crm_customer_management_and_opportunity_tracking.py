import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}

def test_crm_customer_management_and_opportunity_tracking():
    customer_id = None
    opportunity_id = None
    quotation_id = None
    ticket_id = None

    try:
        # 1. Create a new customer
        customer_payload = {
            "name": "Test Customer",
            "email": "testcustomer@example.com",
            "phone": "1234567890",
            "address": "123 Test St, Test City",
            "notes": "Test customer notes"
        }
        r_customer = requests.post(
            f"{BASE_URL}/api/crm/customers/",
            json=customer_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_customer.status_code == 201, f"Customer creation failed: {str(r_customer)}"
        customer = r_customer.json()
        customer_id = customer.get("id")
        assert customer_id is not None, "Customer ID not returned"

        # 2. Update the customer
        update_payload = {
            "phone": "0987654321",
            "notes": "Updated notes"
        }
        r_update_customer = requests.put(
            f"{BASE_URL}/api/crm/customers/{customer_id}/",
            json=update_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_update_customer.status_code == 200, f"Customer update failed: {str(r_update_customer)}"
        updated_customer = r_update_customer.json()
        assert updated_customer.get("phone") == "0987654321"
        assert updated_customer.get("notes") == "Updated notes"

        # 3. Create an opportunity linked to the customer
        opportunity_payload = {
            "customer": customer_id,
            "title": "Test Opportunity",
            "description": "Opportunity for testing",
            "stage": "lead",
            "expected_value": 10000.0
        }
        r_opportunity = requests.post(
            f"{BASE_URL}/api/crm/opportunities/",
            json=opportunity_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_opportunity.status_code == 201, f"Opportunity creation failed: {str(r_opportunity)}"
        opportunity = r_opportunity.json()
        opportunity_id = opportunity.get("id")
        assert opportunity_id is not None, "Opportunity ID not returned"
        assert opportunity.get("customer") == customer_id

        # 4. Update the opportunity stage
        opp_update_payload = {"stage": "qualified"}
        r_update_opportunity = requests.put(
            f"{BASE_URL}/api/crm/opportunities/{opportunity_id}/",
            json=opp_update_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_update_opportunity.status_code == 200, f"Opportunity update failed: {str(r_update_opportunity)}"
        updated_opportunity = r_update_opportunity.json()
        assert updated_opportunity.get("stage") == "qualified"

        # 5. Create a quotation linked to the customer and opportunity
        quotation_payload = {
            "customer": customer_id,
            "opportunity": opportunity_id,
            "title": "Test Quotation",
            "amount": 9500.0,
            "status": "draft"
        }
        r_quotation = requests.post(
            f"{BASE_URL}/api/crm/quotations/",
            json=quotation_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_quotation.status_code == 201, f"Quotation creation failed: {str(r_quotation)}"
        quotation = r_quotation.json()
        quotation_id = quotation.get("id")
        assert quotation_id is not None, "Quotation ID not returned"
        assert quotation.get("customer") == customer_id
        assert quotation.get("opportunity") == opportunity_id

        # 6. Update the quotation status
        quotation_update_payload = {"status": "sent"}
        r_update_quotation = requests.put(
            f"{BASE_URL}/api/crm/quotations/{quotation_id}/",
            json=quotation_update_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_update_quotation.status_code == 200, f"Quotation update failed: {str(r_update_quotation)}"
        updated_quotation = r_update_quotation.json()
        assert updated_quotation.get("status") == "sent"

        # 7. Create a support ticket for the customer
        ticket_payload = {
            "customer": customer_id,
            "subject": "Test support ticket",
            "description": "Issue reported during testing",
            "status": "open",
            "priority": "medium"
        }
        r_ticket = requests.post(
            f"{BASE_URL}/api/crm/tickets/",
            json=ticket_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_ticket.status_code == 201, f"Support ticket creation failed: {str(r_ticket)}"
        ticket = r_ticket.json()
        ticket_id = ticket.get("id")
        assert ticket_id is not None, "Ticket ID not returned"
        assert ticket.get("customer") == customer_id

        # 8. Update the support ticket status
        ticket_update_payload = {"status": "closed"}
        r_update_ticket = requests.put(
            f"{BASE_URL}/api/crm/tickets/{ticket_id}/",
            json=ticket_update_payload,
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_update_ticket.status_code == 200, f"Support ticket update failed: {str(r_update_ticket)}"
        updated_ticket = r_update_ticket.json()
        assert updated_ticket.get("status") == "closed"

        # 9. List customers to verify presence of created customer
        r_list_customers = requests.get(
            f"{BASE_URL}/api/crm/customers/",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_list_customers.status_code == 200, f"Listing customers failed: {str(r_list_customers)}"
        customers_list = r_list_customers.json()
        assert any(c.get("id") == customer_id for c in customers_list), "Created customer not in customers list"

        # 10. List opportunities for the customer to verify
        r_list_opportunities = requests.get(
            f"{BASE_URL}/api/crm/opportunities/?customer={customer_id}",
            auth=AUTH,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        assert r_list_opportunities.status_code == 200, f"Listing opportunities failed: {str(r_list_opportunities)}"
        opportunities_list = r_list_opportunities.json()
        assert any(o.get("id") == opportunity_id for o in opportunities_list), "Created opportunity not in opportunities list"

    finally:
        # Cleanup: Delete the support ticket
        if ticket_id is not None:
            try:
                requests.delete(
                    f"{BASE_URL}/api/crm/tickets/{ticket_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT
                )
            except Exception:
                pass
        # Cleanup: Delete the quotation
        if quotation_id is not None:
            try:
                requests.delete(
                    f"{BASE_URL}/api/crm/quotations/{quotation_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT
                )
            except Exception:
                pass
        # Cleanup: Delete the opportunity
        if opportunity_id is not None:
            try:
                requests.delete(
                    f"{BASE_URL}/api/crm/opportunities/{opportunity_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT
                )
            except Exception:
                pass
        # Cleanup: Delete the customer
        if customer_id is not None:
            try:
                requests.delete(
                    f"{BASE_URL}/api/crm/customers/{customer_id}/",
                    auth=AUTH,
                    headers=HEADERS,
                    timeout=TIMEOUT
                )
            except Exception:
                pass

test_crm_customer_management_and_opportunity_tracking()
