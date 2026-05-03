#!/usr/bin/env bash
set -euo pipefail

# Run the MedSim Triage Streamlit UI.
echo "Starting MedSim Triage UI ..."
exec streamlit run src/medsim/ui/streamlit_app.py
