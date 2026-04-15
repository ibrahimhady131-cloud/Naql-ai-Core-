"""Naql.ai Master Service Orchestrator."""

from __future__ import annotations

import asyncio
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# ANSI Colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
BOLD = "\033[1m"


@dataclass
class ServiceConfig:
    name: str
    port: int
    script: str
    color: str
    depends_on: list[int]


SERVICES = [
    ServiceConfig("NATS", 4222, None, CYAN, []),
    ServiceConfig("IDENTITY", 8001, "services/identity-service/start.py", GREEN, [4222]),
    ServiceConfig("ID_GRPC", 50052, "services/identity-service/grpc_start.py", GREEN, [4222, 8001]),
    ServiceConfig("FLEET", 8002, "services/fleet-service/start.py", YELLOW, [4222, 8001]),
    ServiceConfig("MATCHING", 8003, "services/matching-engine/start.py", BLUE, [4222, 8001, 50052]),
    ServiceConfig("FINTRACK", 8004, "services/fintrack-service/start.py", MAGENTA, [4222, 8001]),
    ServiceConfig("AGENT", 8005, "services/agent-orchestrator/start.py", RED, [4222]),
    ServiceConfig("TELEMETRY", 8006, "services/telemetry-ingress/start.py", GREEN, [4222, 1883]),
]


class NaqlManager:
    def __init__(self):
        self.processes: dict[str, subprocess.Popen] = {}
        self.running = True
        self.base_path = Path(__file__).parent.parent

    def log(self, service: str, message: str, color: str = ""):
        timestamp = time.strftime("%H:%M:%S")
        color_code = color or GREEN
        print(f"{color_code}[{service}] {timestamp} | {message}{RESET}")

    def check_port(self, port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def wait_for_port(self, port: int, timeout: int = 30) -> bool:
        self.log("WAIT", f"Waiting for port {port}...", CYAN)
        start = time.time()
        while time.time() - start < timeout:
            if self.check_port(port):
                self.log("READY", f"Port {port} is open", GREEN)
                return True
            time.sleep(0.5)
        self.log("TIMEOUT", f"Port {port} not available after {timeout}s", RED)
        return False

    def kill_existing_processes(self):
        self.log("CLEANUP", "Killing existing processes...", YELLOW)
        os.system("taskkill /F /IM python.exe 2>nul")
        os.system("taskkill /F /IM nats-server.exe 2>nul")
        # Kill anything on ports 1883, 4222, 8001-8006
        os.system("for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :1883') do taskkill /F /PID %a 2>nul")
        time.sleep(3)

    def get_env(self) -> dict[str, str]:
        return {
            "DATABASE_URL": "postgresql+asyncpg://postgres.zxnmsjveiymibuuooxwv:EX6kcZ6aCdIe0vBE@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require",
            "NAQL_SSL_CA_FILE": "F:/Projects-app/BIG-DEV/prod-ca-2021.crt",
            "PYTHONPATH": "F:/Projects-app/BIG-DEV;F:/Projects-app/BIG-DEV/shared",
        }

    def start_nats(self) -> bool:
        self.log("NATS", "Starting NATS server...", CYAN)
        nats_path = r"C:\nats-temp\nats-server-v2.10.18-windows-amd64\nats-server.exe"
        config_path = str(self.base_path / "nats_mqtt.conf")

        try:
            proc = subprocess.Popen(
                [nats_path, "-c", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            self.processes["NATS"] = proc
            # Start log streaming for NATS
            thread = threading.Thread(target=self._stream_logs, args=("NATS", proc, CYAN), daemon=True)
            thread.start()
            return self.wait_for_port(4222)
        except Exception as e:
            self.log("NATS", f"Failed to start: {e}", RED)
            return False

    def _stream_logs(self, name: str, proc: subprocess.Popen, color: str):
        """Stream logs from a process with color prefix."""
        try:
            for line in iter(proc.stdout.readline, ""):
                if not self.running:
                    break
                if line.strip():
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"{color}[{name}] {timestamp} | {line.rstrip()}{RESET}")
        except Exception:
            pass

    def start_service(self, config: ServiceConfig) -> bool:
        if config.script is None:
            return True

        # Check dependencies
        for dep_port in config.depends_on:
            if not self.check_port(dep_port):
                self.log(config.name, f"Waiting for dependency on port {dep_port}...", config.color)
                if not self.wait_for_port(dep_port):
                    return False

        if self.check_port(config.port):
            self.log(config.name, f"Port {config.port} already in use - skipping", YELLOW)
            return True

        self.log(config.name, f"Starting service on port {config.port}...", config.color)

        venv_python = self.base_path / ".venv" / "Scripts" / "python.exe"
        script_path = self.base_path / config.script

        env = os.environ.copy()
        env.update(self.get_env())

        try:
            proc = subprocess.Popen(
                [str(venv_python), str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(self.base_path),
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            self.processes[config.name] = proc
            # Start log streaming
            thread = threading.Thread(target=self._stream_logs, args=(config.name, proc, config.color), daemon=True)
            thread.start()

            # Wait longer for service to fully start
            for _ in range(8):
                time.sleep(1)
                if self.check_port(config.port):
                    self.log(config.name, f"Service started successfully", config.color)
                    return True

            self.log(config.name, f"Service failed to start", RED)
            return False
        except Exception as e:
            self.log(config.name, f"Error: {e}", RED)
            return False

    def monitor_services(self):
        while self.running:
            for name, proc in list(self.processes.items()):
                if proc.poll() is not None:
                    self.log(name, "Process died!", RED)
                    del self.processes[name]
            time.sleep(5)

    def shutdown(self):
        self.running = False
        self.log("SHUTDOWN", "Stopping all services...", YELLOW)

        for name, proc in list(self.processes.items()):
            try:
                self.log(name, "Terminating...", YELLOW)
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        self.kill_existing_processes()
        self.log("SHUTDOWN", "All services stopped", GREEN)
        sys.exit(0)


def main():
    try:
        manager = NaqlManager()

        def signal_handler(sig, frame):
            print()
            manager.shutdown()

        signal.signal(signal.SIGINT, signal_handler)

        print(f"\n{BOLD}{'='*60}")
        print(f"  Naql.ai Master Orchestrator v1.0")
        print(f"{'='*60}{RESET}\n")

        print(">> Starting NATS...")

        # Start NATS first
        if not manager.start_nats():
            manager.log("ERROR", "Failed to start NATS - exiting", RED)
            sys.exit(1)

        print(">> NATS started, starting services...")

        # Start all services
        for svc in SERVICES[1:]:
            manager.start_service(svc)
            time.sleep(1)

        print(f"\n{BOLD}{'='*60}")
        print(f"  All services started!")
        print(f"  Press Ctrl+C to shutdown")
        print(f"{'='*60}{RESET}\n")

        # Keep running
        while manager.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
