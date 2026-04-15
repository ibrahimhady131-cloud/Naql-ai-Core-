import requests
import json

data = {
    "client_id": "8c620951-33a8-4ef5-a282-9fba8cd8cbf4",
    "region_code": "EG-CAI",
    "origin_address": "Cairo",
    "origin_lat": 30.0444,
    "origin_lng": 31.2357,
    "dest_address": "Alexandria",
    "dest_lat": 31.2001,
    "dest_lng": 29.9187,
    "commodity_type": "general",
    "weight_kg": 1000,
    "volume_cbm": 5,
    "requires_refrigeration": False,
    "pickup_window_start": "2026-04-15T19:00:00Z",
    "pickup_window_end": "2026-04-15T23:00:00Z",
    "quoted_price_egp": 1500
}

resp = requests.post("http://127.0.0.1:8003/api/v1/shipments", json=data)
print(resp.status_code)
print(resp.text)
