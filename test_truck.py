import requests

# Create a shipment first
shipment_data = {
    "client_id": "8c620951-33a8-4ef5-a282-9fba8cd8cbf4",
    "region_code": "EG-CAI",
    "origin_address": "Cairo, Egypt",
    "origin_lat": 30.0444,
    "origin_lng": 31.2357,
    "dest_address": "Alexandria, Egypt",
    "dest_lat": 31.2001,
    "dest_lng": 29.9187,
    "commodity_type": "electronics",
    "weight_kg": 500,
    "pickup_window_start": "2026-04-16T08:00:00Z",
    "pickup_window_end": "2026-04-16T12:00:00Z"
}
r = requests.post("http://127.0.0.1:8003/api/v1/shipments", json=shipment_data)
shipment_id = r.json()["id"]
print(f"Created shipment: {shipment_id}")

# Query via GraphQL
query = f'{{ shipment(shipmentId: "{shipment_id}") {{ id referenceNumber status originAddress destAddress commodityType weightKg }} }}'
r = requests.post("http://127.0.0.1:4001/graphql", json={"query": query})
print("Status:", r.status_code)
print("Response:", r.text)
