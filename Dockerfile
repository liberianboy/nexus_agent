# syntax=docker/dockerfile:1.6
# Works on Apple Silicon (arm64) and Intel (amd64) Macs.
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for matplotlib's font rendering.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        gcc \
        libfreetype6 \
        libpng16-16 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY src ./src
COPY data ./data
COPY scripts ./scripts

# Persisted output volume.
RUN mkdir -p /app/reports
VOLUME ["/app/reports"]

# Default to running the data-center / water demo with the heat map.
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--scenario", "data_center_water", "--heatmap"]
