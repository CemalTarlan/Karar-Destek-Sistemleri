#!/usr/bin/env bash
set -euo pipefail

# Run the MedSim Triage FastAPI server.
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"

echo "Starting MedSim Triage API on http://${HOST}:${PORT} ..."
exec uvicorn medsim.api.main:app --reload --host "${HOST}" --port "${PORT}"
