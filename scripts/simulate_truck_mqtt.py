"""Simulate truck position updates via MQTT."""

import json
import time
import paho.mqtt.client as mqtt

# Truck ID from Phase 2
TRUCK_ID = "1af055fa-58d9-4624-9ccf-e800580d1f11"

# Starting position (Cairo area)
BASE_LAT = 30.0444
BASE_LNG = 31.2357

# MQTT broker settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = f"naql/telemetry/v1/{TRUCK_ID}/pos"


def main():
    """Publish truck position updates every 2 seconds."""
    client = mqtt.Client(client_id="truck-simulator")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    print(f"[Simulator] Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    print(f"[Simulator] Publishing to {MQTT_TOPIC}")

    lat = BASE_LAT
    lng = BASE_LNG
    step = 0.001  # ~100m step

    try:
        while True:
            # Simulate moving truck
            lat += step
            lng += step

            payload = {
                "lat": round(lat, 6),
                "lon": round(lng, 6),
                "speed": 45.0,
                "fuel": 75.0,
                "timestamp": time.time(),
            }

            result = client.publish(MQTT_TOPIC, json.dumps(payload))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[Simulator] Published: lat={payload['lat']}, lon={payload['lon']}")
            else:
                print(f"[Simulator] Failed to publish: {result.rc}")

            time.sleep(2)

    except KeyboardInterrupt:
        print("[Simulator] Stopping...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
