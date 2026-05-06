#!/usr/bin/env bash
# Convenience wrapper for running the agent natively on macOS without Docker.
# Usage:
#   ./scripts/run_local.sh                      # data center water demo
#   ./scripts/run_local.sh grid_cyberattack
#   ./scripts/run_local.sh data_center_water --question "Custom Q?"
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

SCENARIO="${1:-data_center_water}"
shift || true

python -m src.cli --scenario "$SCENARIO" --heatmap "$@"
