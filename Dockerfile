# ── Stage 1: system libs + Python deps ──────────────────────────────────────
FROM python:3.11-slim-bookworm AS base

# libgdal-dev is required by rasterio; build-essential for any C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        gdal-bin \
        libgdal-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Tell GDAL Python bindings where the config lives
ENV GDAL_CONFIG=/usr/bin/gdal-config

WORKDIR /app

# Install Python deps first (separate layer so rebuilds are fast)
COPY requirements-serve.txt .
RUN pip install --no-cache-dir \
        "GDAL==$(gdal-config --version)" \
    && pip install --no-cache-dir -r requirements-serve.txt

# ── Stage 2: application code ────────────────────────────────────────────────
COPY backend/   backend/
COPY dashboard/ dashboard/
COPY pipeline/  pipeline/

# data/ is mounted at runtime via docker-compose volume — not baked into image
ENV PYTHONUNBUFFERED=1
