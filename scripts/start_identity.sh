#!/bin/bash
# Start Identity Service on port 8001
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/shared:$PWD/services/identity-service"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
