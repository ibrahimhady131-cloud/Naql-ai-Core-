#!/bin/bash
# Start Fleet Service on port 8002
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/shared:$PWD/services/fleet-service"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
