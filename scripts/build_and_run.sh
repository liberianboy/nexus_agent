#!/usr/bin/env bash
# Build the Docker image and run the demo end-to-end on a Mac.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[i] Created .env from .env.example - edit it to add API keys (optional)."
fi

docker compose build
docker compose run --rm nexus-agent --scenario data_center_water --heatmap
docker compose run --rm nexus-agent --scenario grid_cyberattack --heatmap

echo
echo "[ok] Reports written to ./reports/"
ls -lh reports/
