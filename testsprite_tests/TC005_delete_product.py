import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, '/var/www/tony_erp')
django.setup()

import pytest
from django.test import Client
import json

@pytest.mark.django_db
def test_delete_product():
    client = Client()
    # Obtain JWT token for authentication - replace with valid credentials or token setup method
    # Example placeholder login to get token (adjust as per actual auth API):
    auth_response = client.post(
        '/api/token/',  # assuming standard JWT auth endpoint; adjust if needed
        data=json.dumps({'username': 'testuser', 'password': 'testpass'}),
        content_type='application/json',
        SERVER_NAME='localhost',
        SERVER_PORT=8000,
    )
    assert auth_response.status_code == 200
    tokens = auth_response.json()
    access_token = tokens.get('access')
    assert access_token is not None

    headers = {
        'HTTP_AUTHORIZATION': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    product_data = {
        "name": "Test Product For Deletion",
        "description": "Temporary product to test deletion",
        "price": 10.0,
        "quantity": 5
    }

    # Create a product to delete
    create_response = client.post(
        '/api/products/',
        data=json.dumps(product_data),
        content_type='application/json',
        **headers
    )
    assert create_response.status_code == 201
    product = create_response.json()
    product_id = product.get('id')
    assert product_id is not None

    try:
        # Delete the created product
        delete_response = client.delete(
            f'/api/products/{product_id}/',
            **headers,
        )
        assert delete_response.status_code == 204

        # Confirm product is no longer retrievable
        get_response = client.get(
            f'/api/products/{product_id}/',
            **headers,
        )
        assert get_response.status_code == 404
    finally:
        # Cleanup: Ensure deletion if test failed before delete operation
        client.delete(f'/api/products/{product_id}/', **headers)

test_delete_product()