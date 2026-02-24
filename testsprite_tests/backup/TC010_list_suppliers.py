import pytest
from django.test import Client
from rest_framework_simplejwt.tokens import AccessToken

@pytest.mark.django_db
def test_list_suppliers():
    """
    Verify the GET /api/suppliers/ endpoint returns a complete list of suppliers for purchase management.
    """
    # Setup Django test client on server running at port 8000
    client = Client(HTTP_HOST='localhost:8000')

    # Assuming a Django user fixture or create a user here to generate token
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Create user or get existing
    user, created = User.objects.get_or_create(username='testuser_tc010')
    if created:
        user.set_password('password123')
        user.save()

    # Generate JWT token for authentication
    access_token = str(AccessToken.for_user(user))

    # Add authorization header with JWT
    auth_headers = {
        'HTTP_AUTHORIZATION': f'Bearer {access_token}',
    }

    # Make GET request to /api/suppliers/
    response = client.get('/api/suppliers/', **auth_headers)

    # Assert the response status code is 200 OK
    assert response.status_code == 200

    # Assert the response content is JSON and list type
    try:
        suppliers = response.json()
    except Exception:
        pytest.fail("Response is not valid JSON")

    assert isinstance(suppliers, list)

    # Additional optional assertions can be made here if supplier schema is known
    # Example: Check keys if suppliers list is not empty
    if suppliers:
        assert isinstance(suppliers[0], dict)
        expected_keys = {'id', 'name'}  # Adjust keys based on actual supplier fields
        assert expected_keys.intersection(suppliers[0].keys())

test_list_suppliers()
