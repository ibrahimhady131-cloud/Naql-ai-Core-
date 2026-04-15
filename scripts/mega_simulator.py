"""
Mega Simulator - 100 Trucks with MQTT + AI Agent Trigger
"""
import asyncio
import random
import uuid
import json
import time
import httpx
from datetime import datetime

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
FLEET_URL = "http://localhost:8002/api/v1"
MATCHING_URL = "http://localhost:8003/api/v1"
TELEMETRY_URL = "http://localhost:8006/api/v1"

EGYPTIAN_CITIES = {
    "cairo": (30.0444, 31.2357),
    "alexandria": (31.2001, 29.9187),
    "suez": (29.9668, 32.5498),
    "port_said": (31.2653, 32.3019),
    "giza": (30.0131, 31.2089),
    "mansoura": (31.0375, 31.3805),
    "tanta": (30.7865, 31.0004),
    "zagazig": (30.5876, 31.5017),
    "ismailia": (30.6043, 32.2713),
    "fayoum": (29.3099, 30.8418),
}

TRUCK_TYPES = ["flatbed", "box_truck", "tanker", "dump_truck", " refrigerated"]
STATUSES = ["available", "en_route", "loading", "offline"]

class MegaSimulator:
    def __init__(self):
        self.truck_ids = []
        self.shipment_ids = []
        self.telemetry_client = None
        self.mqtt_client = None

    async def start(self):
        print("=" * 60)
        print("MEGA SIMULATOR - 100 TRUCKS FLOOD")
        print("=" * 60)
        
        self.telemetry_client = httpx.AsyncClient(timeout=30.0)
        
        try:
            await self.register_100_trucks()
            print(f"\n[OK] Registered {len(self.truck_ids)} trucks")
            
            await self.start_mqtt_telemetry()
            print("[OK] MQTT telemetry started")
            
            await self.start_shipment_generator()
            print("[OK] Shipment generator started")
            
            print("\n" + "=" * 60)
            print("SIMULATION RUNNING - 100 trucks + AI Agent")
            print("=" * 60)
            print(f" Trucks: {len(self.truck_ids)}")
            print(f" MQTT: {MQTT_BROKER}:{MQTT_PORT}")
            print(f" Shipment interval: 15 seconds")
            print(f" Telemetry interval: 2 seconds")
            print("\nPress Ctrl+C to stop")
            print("=" * 60)
            
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n[STOPPED] Mega simulator stopped")
        finally:
            await self.telemetry_client.aclose()

    async def register_100_trucks(self):
        print("\n[1/4] Registering 100 trucks...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(100):
                truck_id = str(uuid.uuid4())
                city_name = random.choice(list(EGYPTIAN_CITIES.keys()))
                base_lat, base_lng = EGYPTIAN_CITIES[city_name]
                
                truck_data = {
                    "license_plate": f"EG-{1000 + i:03d}",
                    "truck_type": random.choice(TRUCK_TYPES),
                    "load_capacity_kg": random.randint(5000, 25000),
                    "fuel_level": random.randint(20, 100),
                    "status": "available",
                    "current_latitude": base_lat + random.uniform(-0.1, 0.1),
                    "current_longitude": base_lng + random.uniform(-0.1, 0.1),
                    "owner_id": str(uuid.uuid4()),
                }
                
                try:
                    resp = await client.post(f"{FLEET_URL}/trucks", json=truck_data)
                    if resp.status_code in (200, 201):
                        self.truck_ids.append(truck_id)
                except Exception as e:
                    pass
                
                if (i + 1) % 20 == 0:
                    print(f"  Registered {i + 1}/100 trucks...")

    async def start_mqtt_telemetry(self):
        print("\n[2/4] Starting MQTT telemetry publisher...")
        
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("  Installing paho-mqtt...")
            import subprocess
            subprocess.run(["pip", "install", "paho-mqtt"], check=True)
            import paho.mqtt.client as mqtt
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt_client.loop_start()
        
        asyncio.create_task(self.publish_telemetry_loop())

    async def publish_telemetry_loop(self):
        while True:
            for truck_id in self.truck_ids:
                city_name = random.choice(list(EGYPTIAN_CITIES.keys()))
                base_lat, base_lng = EGYPTIAN_CITIES[city_name]
                
                lat = base_lat + random.uniform(-0.15, 0.15)
                lng = base_lng + random.uniform(-0.15, 0.15)
                speed = random.uniform(0, 90)
                fuel = max(10, random.uniform(10, 100))
                
                payload = {
                    "truck_id": truck_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "latitude": lat,
                    "longitude": lng,
                    "speed_kmh": speed,
                    "fuel_level": fuel,
                    "heading": random.uniform(0, 360),
                    "engine_temp": random.uniform(80, 105),
                    "tire_pressure": [random.uniform(30, 35) for _ in range(6)],
                }
                
                try:
                    self.mqtt_client.publish(
                        f"naql/telemetry/{truck_id}",
                        json.dumps(payload),
                        qos=1
                    )
                except:
                    pass
                
                try:
                    await self.telemetry_client.post(
                        f"{TELEMETRY_URL}/telemetry",
                        json=payload
                    )
                except:
                    pass
            
            await asyncio.sleep(2)

    async def start_shipment_generator(self):
        print("\n[3/4] Starting shipment generator (every 15s)...")
        asyncio.create_task(self.create_shipments_loop())

    async def create_shipments_loop(self):
        shipment_counter = 1
        while True:
            await asyncio.sleep(15)
            
            origin_city = random.choice(list(EGYPTIAN_CITIES.keys()))
            dest_city = random.choice(list(EGYPTIAN_CITIES.keys()))
            while dest_city == origin_city:
                dest_city = random.choice(list(EGYPTIAN_CITIES.keys()))
            
            origin = EGYPTIAN_CITIES[origin_city]
            dest = EGYPTIAN_CITIES[dest_city]
            
            shipment_data = {
                "shipper_id": str(uuid.uuid4()),
                "origin_lat": origin[0],
                "origin_lng": origin[1],
                "destination_lat": dest[0],
                "destination_lng": dest[1],
                "cargo_type": random.choice(["electronics", "food", "construction", "textiles", "machinery"]),
                "weight_kg": random.randint(1000, 15000),
                "pickup_deadline": datetime.utcnow().isoformat(),
                "delivery_deadline": datetime.utcnow().isoformat(),
            }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(f"{MATCHING_URL}/shipments", json=shipment_data)
                    if resp.status_code in (200, 201):
                        shipment_id = resp.json().get("id", "unknown")
                        self.shipment_ids.append(shipment_id)
                        print(f"\n[SHIPMENT #{shipment_counter}] {origin_city} -> {dest_city} | ID: {shipment_id[:8]}...")
                        shipment_counter += 1
            except Exception as e:
                pass

if __name__ == "__main__":
    simulator = MegaSimulator()
    asyncio.run(simulator.start())
