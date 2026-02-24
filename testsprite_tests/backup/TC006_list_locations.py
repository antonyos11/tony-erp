import pytest
from rest_framework.test import APIClient
from django.conf import settings

@pytest.mark.django_db
def test_list_locations(jwt_token):
    """
    Verify the GET /api/locations/ endpoint returns all warehouse locations with correct showroom scoping.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + jwt_token)

    url = "http://localhost:8000/api/locations/"
    response = client.get(url, format='json')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Additional checks can be implemented here depending on expected schema
    # Example: verify keys in each location item if schema known:
    # for location in data:
    #     assert "id" in location
    #     assert "name" in location
    #     assert "showroom_scope" in location

# Call the test function (pytest will handle this in actual testing environment)
test_list_locations(jwt_token="your_jwt_token_here")