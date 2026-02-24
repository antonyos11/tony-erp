import requests

BASE_URL = "http://localhost:8000/dashboard/dashboard/"
CONVERSATIONS_ENDPOINT = "/api/whatsapp-ai/conversations/"
TEMPLATES_ENDPOINT = "/api/whatsapp-ai/templates/"

USERNAME = "boss"
PASSWORD = "Mm02022006"

TIMEOUT = 30


def safe_text(response):
    try:
        return response.text
    except AttributeError:
        # Fallback to str of response object if '.text' is missing
        return repr(response)


def get_jwt_token(username, password):
    token_url = BASE_URL.rstrip('/') + "/api/token/"
    resp = requests.post(token_url, json={"username": username, "password": password}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Token retrieval failed: {safe_text(resp)}"
    data = resp.json()
    assert "access" in data, "JWT access token missing in response"
    return data["access"]


def test_whatsapp_ai_conversation_and_template_management():
    token = get_jwt_token(USERNAME, PASSWORD)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    # Sample payload for creating a conversation
    conversation_payload = {
        "customer_id": "test-customer-001",
        "messages": [
            {"from": "customer", "text": "Hello, I need support with my order."}
        ],
        "status": "open"
    }

    # Sample payload for creating a template
    template_payload = {
        "name": "support_acknowledgement",
        "category": "customer_support",
        "language": "en",
        "components": [
            {
                "type": "body",
                "text": "Thank you for reaching out. Our AI assistant is processing your request."
            }
        ]
    }

    conversation_id = None
    template_id = None

    try:
        # Create a new conversation
        response = requests.post(
            url=BASE_URL.rstrip('/') + CONVERSATIONS_ENDPOINT,
            json=conversation_payload,
            headers=headers,
            timeout=TIMEOUT
        )
        assert response.status_code == 201, f"Create conversation failed: {safe_text(response)}"
        conversation_data = response.json()
        assert "id" in conversation_data, "Created conversation response missing 'id'"
        conversation_id = conversation_data["id"]

        # Verify conversation retrieval
        get_conv_resp = requests.get(
            url=f"{BASE_URL.rstrip('/')}{CONVERSATIONS_ENDPOINT}{conversation_id}/",
            headers=headers,
            timeout=TIMEOUT
        )
        assert get_conv_resp.status_code == 200, f"Retrieve conversation failed: {safe_text(get_conv_resp)}"
        conv_detail = get_conv_resp.json()
        assert conv_detail.get("id") == conversation_id, "Retrieved conversation ID mismatch"
        assert conv_detail.get("status") == "open", "Conversation status mismatch"

        # Create a new template
        response = requests.post(
            url=BASE_URL.rstrip('/') + TEMPLATES_ENDPOINT,
            json=template_payload,
            headers=headers,
            timeout=TIMEOUT
        )
        assert response.status_code == 201, f"Create template failed: {safe_text(response)}"
        template_data = response.json()
        assert "id" in template_data, "Created template response missing 'id'"
        template_id = template_data["id"]

        # Verify template retrieval
        get_template_resp = requests.get(
            url=f"{BASE_URL.rstrip('/')}{TEMPLATES_ENDPOINT}{template_id}/",
            headers=headers,
            timeout=TIMEOUT
        )
        assert get_template_resp.status_code == 200, f"Retrieve template failed: {safe_text(get_template_resp)}"
        template_detail = get_template_resp.json()
        assert template_detail.get("id") == template_id, "Retrieved template ID mismatch"
        assert template_detail.get("name") == template_payload["name"], "Template name mismatch"
        assert template_detail.get("category") == template_payload["category"], "Template category mismatch"

        # Test AI-powered response simulation by adding a reply message to the conversation
        ai_reply_payload = {
            "messages": [
                {"from": "ai_assistant", "text": "We are processing your request and will get back shortly."}
            ],
            "status": "open"
        }
        update_conv_resp = requests.put(
            url=f"{BASE_URL.rstrip('/')}{CONVERSATIONS_ENDPOINT}{conversation_id}/",
            json=ai_reply_payload,
            headers=headers,
            timeout=TIMEOUT
        )
        assert update_conv_resp.status_code in (200, 202), f"Update conversation failed: {safe_text(update_conv_resp)}"
        updated_conv = update_conv_resp.json()
        # Check that AI message is included
        messages = updated_conv.get("messages", [])
        assert any(m.get("from") == "ai_assistant" for m in messages), "AI response message missing in conversation"

    finally:
        # Cleanup: Delete created conversation if exists
        if conversation_id:
            requests.delete(
                url=f"{BASE_URL.rstrip('/')}{CONVERSATIONS_ENDPOINT}{conversation_id}/",
                headers=headers,
                timeout=TIMEOUT
            )
        # Cleanup: Delete created template if exists
        if template_id:
            requests.delete(
                url=f"{BASE_URL.rstrip('/')}{TEMPLATES_ENDPOINT}{template_id}/",
                headers=headers,
                timeout=TIMEOUT
            )


test_whatsapp_ai_conversation_and_template_management()
