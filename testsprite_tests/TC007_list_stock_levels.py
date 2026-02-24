from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

def test_list_stock_levels():
    # Create a test user
    username = "testuser_tc007"
    password = "strongpassword123"
    user = User.objects.create_user(username=username, password=password)
    user.is_active = True
    user.save()

    # Get JWT token for authentication
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    client = Client(HTTP_AUTHORIZATION=f'Bearer {access_token}', SERVER_PORT=8000)

    # Perform GET request to /api/stock/
    response = client.get('/api/stock/', content_type='application/json')

    # Validate response
    assert response.status_code == 200
    data = response.json()
    # Assert that data is a list (stock levels)
    assert isinstance(data, list)

test_list_stock_levels()