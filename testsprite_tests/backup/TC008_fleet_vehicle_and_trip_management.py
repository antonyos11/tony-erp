import requests
from requests.auth import HTTPBasicAuth

def test_fleet_vehicle_and_trip_management():
    base_url = "http://localhost:8000/dashboard/dashboard"
    auth = HTTPBasicAuth("boss", "Mm02022006")
    headers = {"Accept": "application/json"}
    timeout = 30

    vehicle_data = {
        "license_plate": "TEST1234",
        "make": "TestMake",
        "model": "TestModel",
        "year": 2023,
        "color": "White",
        "status": "active"
    }

    driver_data = {
        "first_name": "Test",
        "last_name": "Driver",
        "license_number": "D1234567",
        "phone": "+1234567890",
        "email": "test.driver@example.com"
    }

    trip_data = {
        # To be completed after vehicle and driver created
    }

    created_vehicle_id = None
    created_driver_id = None
    created_trip_id = None

    try:
        # Create Vehicle
        r_vehicle = requests.post(
            f"{base_url}/api/fleet/vehicles/",
            json=vehicle_data,
            headers=headers,
            auth=auth,
            timeout=timeout,
        )
        vehicle_text = getattr(r_vehicle, 'text', '')
        assert r_vehicle.status_code == 201, (
            f"Vehicle creation failed: {r_vehicle.status_code}, {vehicle_text}"
        )
        vehicle_resp = r_vehicle.json()
        created_vehicle_id = vehicle_resp.get("id")
        assert created_vehicle_id is not None, "Vehicle ID not returned."

        # Create Driver
        r_driver = requests.post(
            f"{base_url}/api/fleet/drivers/",
            json=driver_data,
            headers=headers,
            auth=auth,
            timeout=timeout,
        )
        driver_text = getattr(r_driver, 'text', '')
        assert r_driver.status_code == 201, (
            f"Driver creation failed: {r_driver.status_code}, {driver_text}"
        )
        driver_resp = r_driver.json()
        created_driver_id = driver_resp.get("id")
        assert created_driver_id is not None, "Driver ID not returned."

        # Prepare trip data with vehicle and driver
        trip_data = {
            "vehicle": created_vehicle_id,
            "driver": created_driver_id,
            "start_location": "Warehouse A",
            "end_location": "Client B",
            "start_time": "2026-03-01T08:00:00Z",
            "end_time": "2026-03-01T12:00:00Z",
            "distance_km": 150,
            "cost": 75.50,
            "status": "completed"
        }

        # Create Trip
        r_trip = requests.post(
            f"{base_url}/api/fleet/trips/",
            json=trip_data,
            headers=headers,
            auth=auth,
            timeout=timeout,
        )
        trip_text = getattr(r_trip, 'text', '')
        assert r_trip.status_code == 201, (
            f"Trip creation failed: {r_trip.status_code}, {trip_text}"
        )
        trip_resp = r_trip.json()
        created_trip_id = trip_resp.get("id")
        assert created_trip_id is not None, "Trip ID not returned."
        # Verify returned trip data matches input where applicable
        assert trip_resp["vehicle"] == created_vehicle_id
        assert trip_resp["driver"] == created_driver_id
        assert trip_resp["status"] == "completed"

        # Retrieve Vehicle - verify details
        r_get_vehicle = requests.get(
            f"{base_url}/api/fleet/vehicles/{created_vehicle_id}/",
            headers=headers,
            auth=auth,
            timeout=timeout,
        )
        get_vehicle_text = getattr(r_get_vehicle, 'text', '')
        assert r_get_vehicle.status_code == 200, (
            f"Get vehicle failed: {r_get_vehicle.status_code}, {get_vehicle_text}"
        )
        vehicle_detail = r_get_vehicle.json()
        assert vehicle_detail["license_plate"] == vehicle_data["license_plate"]

        # Retrieve Driver - verify details
        r_get_driver = requests.get(
            f"{base_url}/api/fleet/drivers/{created_driver_id}/",
            headers=headers,
            auth=auth,
            timeout=timeout,
        )
        get_driver_text = getattr(r_get_driver, 'text', '')
        assert r_get_driver.status_code == 200, (
            f"Get driver failed: {r_get_driver.status_code}, {get_driver_text}"
        )
        driver_detail = r_get_driver.json()
        assert driver_detail["license_number"] == driver_data["license_number"]

        # Retrieve Trip - verify details
        r_get_trip = requests.get(
            f"{base_url}/api/fleet/trips/{created_trip_id}/",
            headers=headers,
            auth=auth,
            timeout=timeout,
        )
        get_trip_text = getattr(r_get_trip, 'text', '')
        assert r_get_trip.status_code == 200, (
            f"Get trip failed: {r_get_trip.status_code}, {get_trip_text}"
        )
        trip_detail = r_get_trip.json()
        assert trip_detail["distance_km"] == trip_data["distance_km"]
        assert trip_detail["cost"] == trip_data["cost"]

        # Optionally, test maintenance scheduling can be queried or created if endpoint exists
        # Since only trips endpoint is given, we'll just confirm trip cost is tracked.

    finally:
        # Cleanup - Delete Trip
        if created_trip_id is not None:
            requests.delete(
                f"{base_url}/api/fleet/trips/{created_trip_id}/",
                headers=headers,
                auth=auth,
                timeout=timeout,
            )
        # Cleanup - Delete Driver
        if created_driver_id is not None:
            requests.delete(
                f"{base_url}/api/fleet/drivers/{created_driver_id}/",
                headers=headers,
                auth=auth,
                timeout=timeout,
            )
        # Cleanup - Delete Vehicle
        if created_vehicle_id is not None:
            requests.delete(
                f"{base_url}/api/fleet/vehicles/{created_vehicle_id}/",
                headers=headers,
                auth=auth,
                timeout=timeout,
            )

test_fleet_vehicle_and_trip_management()
