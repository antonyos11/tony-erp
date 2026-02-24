import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000/api/fleet"
AUTH = HTTPBasicAuth("boss", "Mm02022006")
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

def test_fleet_vehicle_and_trip_management():
    vehicle_url = f"{BASE_URL}/vehicles/"
    driver_url = f"{BASE_URL}/drivers/"
    trip_url = f"{BASE_URL}/trips/"

    vehicle_data = {
        "name": "Test Vehicle",
        "plate_number": "TEST1234",
        "make": "Toyota",
        "model": "Corolla",
        "year": 2020,
        "capacity": 5,
        "status": "available"
    }
    driver_data = {
        "name": "Test Driver",
        "license_number": "D1234567",
        "phone": "+123456789",
        "email": "testdriver@example.com",
        "status": "available"
    }
    trip_data = {
        "origin": "Warehouse A",  # Fixed: changed from 'start_location'
        "destination": "Customer B",  # Fixed: changed from 'end_location'
        "start_time": "2024-06-01T08:00:00Z",
        "end_time": "2024-06-01T10:00:00Z",
        "cost": 150.0,
        "notes": "Routine delivery trip"
    }

    vehicle_id = None
    driver_id = None
    trip_id = None

    try:
        # Create Vehicle
        res = requests.post(vehicle_url, json=vehicle_data, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert res.status_code == 201, f"Vehicle creation failed: {res.text}"
        vehicle_resp = res.json()
        vehicle_id = vehicle_resp.get("id")
        assert vehicle_id is not None, "Vehicle ID not returned"

        # Create Driver
        res = requests.post(driver_url, json=driver_data, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert res.status_code == 201, f"Driver creation failed: {res.text}"
        driver_resp = res.json()
        driver_id = driver_resp.get("id")
        assert driver_id is not None, "Driver ID not returned"

        # Assign vehicle and driver to trip_data
        trip_data.update({
            "vehicle": vehicle_id,
            "driver": driver_id
        })

        # Create Trip
        res = requests.post(trip_url, json=trip_data, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert res.status_code == 201, f"Trip creation failed: {res.text}"
        trip_resp = res.json()
        trip_id = trip_resp.get("id")
        assert trip_id is not None, "Trip ID not returned"

        # Retrieve and validate vehicle
        res = requests.get(f"{vehicle_url}{vehicle_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert res.status_code == 200, f"Failed to retrieve vehicle: {res.text}"
        vehicle_data_resp = res.json()
        assert vehicle_data_resp.get("plate_number") == vehicle_data["plate_number"]
        assert vehicle_data_resp.get("status") == "available"

        # Retrieve and validate driver
        res = requests.get(f"{driver_url}{driver_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert res.status_code == 200, f"Failed to retrieve driver: {res.text}"
        driver_data_resp = res.json()
        assert driver_data_resp.get("name") == driver_data["name"]
        
        # Retrieve and validate trip
        res = requests.get(f"{trip_url}{trip_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        assert res.status_code == 200, f"Failed to retrieve trip: {res.text}"
        trip_data_resp = res.json()
        assert trip_data_resp.get("vehicle") == vehicle_id
        assert trip_data_resp.get("driver") == driver_id

    finally:
        # Cleanup: delete trip, driver, vehicle in reverse order if created
        if trip_id:
            requests.delete(f"{trip_url}{trip_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if driver_id:
            requests.delete(f"{driver_url}{driver_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if vehicle_id:
            requests.delete(f"{vehicle_url}{vehicle_id}/", auth=AUTH, headers=HEADERS, timeout=TIMEOUT)

test_fleet_vehicle_and_trip_management()
