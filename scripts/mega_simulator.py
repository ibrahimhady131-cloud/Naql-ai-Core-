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

TRUCK_TYPES = ["flatbed", "tanker", "refrigerated", "trailer", "full"]
STATUSES = ["available", "en_route", "loading", "offline"]

class MegaSimulator:
    def __init__(self):
        self.truck_ids = []
        self.shipment_ids = []
        self.http_client = None
        self.mqtt_client = None

    def start(self):
        print("=" * 60)
        print("MEGA SIMULATOR - 100 TRUCKS FLOOD")
        print("=" * 60)
        
        self.http_client = httpx.Client(timeout=30.0)
        
        try:
            self.register_100_trucks()
            print(f"\n[OK] Registered {len(self.truck_ids)} trucks")
            
            self.start_mqtt_telemetry()
            print("[OK] MQTT telemetry started")
            
            self.start_shipment_generator()
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
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n[STOPPED] Mega simulator stopped")
        finally:
            self.http_client.close()

    def register_100_trucks(self):
        print("\n[1/4] Registering 100 trucks...")
        
        regions = ["CAI", "ALX", "SUE", "GIZ", "MAN", "TAN", "ZAG", "ISM", "FAY", "POR"]
        run_seed = int(time.time()) % 100000
        
        for i in range(100):
            region = random.choice(regions)
            initial_status = random.choices(
                population=["available", "en_route", "loading", "offline"],
                weights=[0.55, 0.25, 0.15, 0.05],
                k=1,
            )[0]
            
            truck_data = {
                "license_plate": f"EG{run_seed:05d}{i:03d}",
                "truck_type": random.choice(TRUCK_TYPES),
                "load_capacity_kg": random.randint(5000, 25000),
                "owner_id": str(uuid.uuid4()),
                "region_code": f"EG-{region}",
            }
            
            try:
                resp = self.http_client.post(f"{FLEET_URL}/trucks", json=truck_data)
                if resp.status_code in (200, 201):
                    created = resp.json() if resp.content else {}
                    created_id = str(created.get("id", "")).strip()
                    if created_id:
                        self.truck_ids.append(created_id)
                    else:
                        print(f"  [WARN] Created truck missing id: {truck_data['license_plate']}")

                    if created_id and initial_status != "offline":
                        try:
                            patch = self.http_client.patch(
                                f"{FLEET_URL}/trucks/{created_id}",
                                json={"status": initial_status},
                            )
                            if patch.status_code not in (200, 204):
                                print(f"  [WARN] Status patch failed {patch.status_code}: {patch.text[:80]}")
                        except Exception as e:
                            print(f"  [WARN] Status patch error: {e}")

                    print(f"  [OK] {truck_data['license_plate']} - {truck_data['truck_type']} - {initial_status}")
                else:
                    print(f"  [FAIL] {resp.status_code}: {resp.text[:80]}")
            except Exception as e:
                print(f"  [ERR] {e}")
            
            if (i + 1) % 20 == 0:
                print(f"  Registered {i + 1}/100 trucks...")

    def start_mqtt_telemetry(self):
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
        
        self.publish_telemetry_loop()

    def publish_telemetry_loop(self):
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
                    self.http_client.post(
                        f"{TELEMETRY_URL}/telemetry",
                        json=payload
                    )
                except:
                    pass
            
            time.sleep(2)

    def start_shipment_generator(self):
        print("\n[3/4] Starting shipment generator with auto-dispatch (every 15s)...")
        self.create_shipments_loop()

    def create_shipments_loop(self):
        shipment_counter = 1
        active_shipments = {}  # shipment_id -> {truck_id, origin, dest, status, progress}
        
        while True:
            time.sleep(15)
            
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
                resp = self.http_client.post(f"{MATCHING_URL}/shipments", json=shipment_data)
                if resp.status_code in (200, 201):
                    shipment_id = resp.json().get("id", "unknown")
                    self.shipment_ids.append(shipment_id)
                    
                    # Trigger Agent Orchestrator to run AI matching
                    try:
                        agent_resp = self.http_client.post(
                            "http://localhost:8005/api/v1/agent/trigger",
                            json={
                                "shipment_id": shipment_id,
                                "pickup_h3": "893e628e67bffff",  # Cairo H3
                                "dropoff_h3": "893f5ba66b3ffff",  # Alexandria H3
                                "cargo_type": shipment_data.get("cargo_type", "general"),
                            }
                        )
                        if agent_resp.status_code == 200:
                            print(f"[AGENT] Triggered for shipment {shipment_id[:8]}...")
                    except Exception as ae:
                        print(f"[AGENT] Warning: Could not trigger agent: {ae}")
                    
                    # Phase A: Assign a truck to this shipment
                    if self.truck_ids:
                        assigned_truck = random.choice(self.truck_ids)
                        active_shipments[shipment_id] = {
                            "truck_id": assigned_truck,
                            "origin": origin,
                            "dest": dest,
                            "status": "assigned",
                            "progress": 0.0,
                            "current_pos": list(origin),
                        }
                        
                        # Update truck status to in_transit
                        self.http_client.patch(
                            f"{FLEET_URL}/trucks/{assigned_truck}",
                            json={"status": "en_route"}
                        )
                        print(f"\n[SHIPMENT #{shipment_counter}] {origin_city} -> {dest_city} | Truck: {assigned_truck[:8]}... (ASSIGNED)")
                    
                    shipment_counter += 1
            except Exception as e:
                pass
            
            # Phase B-D: Update active shipments (trip simulation)
            completed = []
            for sid, info in active_shipments.items():
                if info["status"] == "assigned":
                    # Phase B: Start transit
                    info["status"] = "in_transit"
                    print(f"[TRIP] Shipment {sid[:8]}... now IN_TRANSIT")
                
                if info["status"] == "in_transit":
                    # Phase C: Move truck toward destination
                    dest_lat, dest_lng = info["dest"]
                    curr_lat, curr_lng = info["current_pos"]
                    
                    # Calculate distance and move 5% closer each tick
                    dist_lat = dest_lat - curr_lat
                    dist_lng = dest_lng - curr_lng
                    info["progress"] += 0.05
                    
                    info["current_pos"][0] = curr_lat + dist_lat * 0.05
                    info["current_pos"][1] = curr_lng + dist_lng * 0.05
                    
                    # Publish updated position via MQTT
                    payload = {
                        "truck_id": info["truck_id"],
                        "timestamp": datetime.utcnow().isoformat(),
                        "latitude": info["current_pos"][0],
                        "longitude": info["current_pos"][1],
                        "speed_kmh": 60,
                        "fuel_level": 70,
                        "heading": 45,
                        "engine_temp": 90,
                        "tire_pressure": [32, 32, 32, 32, 32, 32],
                    }
                    try:
                        self.mqtt_client.publish(f"naql/telemetry/{info['truck_id']}", json.dumps(payload), qos=1)
                    except:
                        pass
                    
                    # Phase D: Check for arrival (distance < 1km)
                    import math
                    remaining_dist = math.sqrt(dist_lat**2 + dist_lng**2) * 111  # rough km
                    if remaining_dist < 1 or info["progress"] >= 1.0:
                        info["status"] = "delivered"
                        completed.append(sid)
                        
                        # Update truck status back to available
                        self.http_client.patch(
                            f"{FLEET_URL}/trucks/{info['truck_id']}",
                            json={"status": "available"}
                        )
                        print(f"[DELIVERED] Shipment {sid[:8]}... completed! Truck {info['truck_id'][:8]}... now AVAILABLE")
            
            # Remove completed shipments
            for sid in completed:
                del active_shipments[sid]

if __name__ == "__main__":
    simulator = MegaSimulator()
    simulator.start()
