#!/bin/bash
# Start GraphQL Gateway on port 4000
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/shared:$PWD/gateway"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
