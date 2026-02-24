import requests

def test_list_customers():
    # Obtain JWT token for authentication
    login_response = requests.post('http://localhost/api/token/', json={'username': 'testuser', 'password': 'testpassword'})
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert 'access' in login_data
    token = login_data['access']

    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get('http://localhost/api/customers/', headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) or hasattr(data, '__iter__')
    if len(data) > 0:
        customer = data[0]
        assert isinstance(customer, dict)
        assert 'id' in customer
        assert 'name' in customer or 'full_name' in customer or 'customer_name' in customer


test_list_customers()