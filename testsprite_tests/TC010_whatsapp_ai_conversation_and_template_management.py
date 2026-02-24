import requests
from requests.auth import HTTPBasicAuth
from csrf_helper import CSRFHelper

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30
AUTH = HTTPBasicAuth("boss", "Mm02022006")


def get_jwt_token():
    url = f"{BASE_URL}/api/token/"
    auth_data = {"username": "boss", "password": "Mm02022006"}
    resp = requests.post(url, json=auth_data, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Failed to obtain JWT token: {resp.text}"
    data = resp.json()
    access = data.get("access")
    assert access is not None, "No access token in response"
    return access


def test_whatsapp_ai_conversation_and_template_management():
    # ✅ استخدام CSRF Helper المحسّن
    csrf = CSRFHelper(BASE_URL, "boss", "Mm02022006")
    access_token = get_jwt_token()
    
    conversation_url = f"{BASE_URL}/api/whatsapp-ai/conversations/"
    template_url = f"{BASE_URL}/api/whatsapp-ai/templates/"

    # Payloads for create conversation and template
    conversation_payload = {
        "customer_id": "test_customer_001",
        "messages": [
            {"from": "customer", "text": "Hello, I need help with my order."}
        ],
    }
    template_payload = {
        "name": "Test Template",
        "content": "Dear {{customer_name}}, your request is being processed.",
        "language": "en",
        "category": "customer_support",
    }

    conversation_id = None
    template_id = None

    try:
        # Create a WhatsApp AI conversation (using CSRF)
        resp_conv_create = csrf.post(
            conversation_url,
            json=conversation_payload,
            timeout=TIMEOUT,
        )
        assert resp_conv_create.status_code == 201, f"Conversation creation failed: {resp_conv_create.text}"
        conversation_data = resp_conv_create.json()
        conversation_id = conversation_data.get("id")
        assert conversation_id is not None, "Conversation id not returned"

        # Verify the conversation can be retrieved and AI responses are available
        resp_conv_get = csrf.get(
            f"{conversation_url}{conversation_id}/",
            timeout=TIMEOUT,
        )
        assert resp_conv_get.status_code == 200, f"Failed to get conversation: {resp_conv_get.text}"
        conv_content = resp_conv_get.json()
        assert "messages" in conv_content, "No messages in conversation data"
        # Check that AI generated response is part of messages (if any response message from AI)
        messages = conv_content.get("messages", [])
        ai_responses = [m for m in messages if m.get("from") == "ai"]
        assert ai_responses, "No AI response messages found in conversation"

        # Create a WhatsApp template
        resp_tpl_create = csrf.post(
            template_url,
            json=template_payload,
            timeout=TIMEOUT,
        )
        assert resp_tpl_create.status_code == 201, f"Template creation failed: {resp_tpl_create.text}"
        template_data = resp_tpl_create.json()
        template_id = template_data.get("id")
        assert template_id is not None, "Template id not returned"

        # Verify the template can be retrieved to confirm it is saved correctly
        resp_tpl_get = requests.get(
            template_url + f"{template_id}/",
            headers=auth_headers,
            timeout=TIMEOUT,
        )
        assert resp_tpl_get.status_code == 200, f"Failed to get template: {resp_tpl_get.text}"
        tpl_content = resp_tpl_get.json()
        assert tpl_content.get("name") == template_payload["name"], "Template name mismatch"
        assert tpl_content.get("content") == template_payload["content"], "Template content mismatch"
        assert tpl_content.get("category") == template_payload["category"], "Template category mismatch"

    finally:
        # Cleanup: delete the created conversation and template if created
        if conversation_id:
            requests.delete(
                conversation_url + f"{conversation_id}/",
                headers=auth_headers,
                timeout=TIMEOUT,
            )
        if template_id:
            requests.delete(
                template_url + f"{template_id}/",
                headers=auth_headers,
                timeout=TIMEOUT,
            )


test_whatsapp_ai_conversation_and_template_management()
