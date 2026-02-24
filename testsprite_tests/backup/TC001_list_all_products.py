import requests

BASE_URL = "http://localhost:8000"
# Adjust credentials if needed or fetch token first
# For public endpoints or if auth is handled differently
# This specific test seems simple.
# But usually we need a token.
# Let's see if products list is public. In TC002 it was used with auth.

def test_list_all_products():
    # Try public access first, or use basic auth/token if needed
    # TC002 uses requests.get(..., auth=HTTPBasicAuth("boss", ...))
    # Let's use the same pattern
    from requests.auth import HTTPBasicAuth
    
    auth = HTTPBasicAuth("boss", "Mm02022006")
    
    response = requests.get(f'{BASE_URL}/api/products/', auth=auth)
    
    # It might return 200 or 401 depending on perms. 
    # But for a test named "list all products", we expect 200.
    
    if response.status_code == 401:
        # Try to get token? Or just fail?
        # Let's assume basic auth works for now or standard auth pattern
        pass

    assert response.status_code == 200, f"Failed to list products: {response.text}"
    
    try:
        data = response.json()
    except Exception:
        assert False, "Response is not valid JSON"

    # data could be list or dict with results
    results = data
    if isinstance(data, dict):
        results = data.get("results", [])
        
    assert isinstance(results, list), "Products should be a list"
    
    print(f"Found {len(results)} products")

if __name__ == "__main__":
    test_list_all_products()