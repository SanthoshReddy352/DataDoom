# syntax=docker/dockerfile:1
#
# Runnable DataDoom server image (REST + WebSocket + bundled web Canvas).
# The web Canvas is compiled in a Node stage and copied into the Python image,
# so the final image carries no Node toolchain. Build & run:
#   docker build -t datadoom:local .
#   docker run --rm -p 8000:8000 -v datadoom-data:/data datadoom:local
# See docs_v2/22_Release_and_Publishing_Runbook.md §3 for publishing to GHCR.

# --- Stage 1: compile the web Canvas into src/datadoom/webdist ---
FROM node:20-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# vite outDir is ../src/datadoom/webdist -> /app/src/datadoom/webdist
RUN npm run build

# --- Stage 2: runtime ---
FROM python:3.11-slim AS runtime
LABEL org.opencontainers.image.source="https://github.com/SanthoshReddy352/datadoom"
LABEL org.opencontainers.image.description="DataDoom — local-first engine for controllable, reproducible synthetic data, with a web Canvas."
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATADOOM_HOME=/data \
    DATADOOM_HOST=0.0.0.0 \
    DATADOOM_PORT=8000 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app
COPY . /app
# Overwrite any source/gitignored webdist with the freshly compiled Canvas.
COPY --from=web /app/src/datadoom/webdist /app/src/datadoom/webdist

RUN pip install --upgrade pip && pip install ".[server,parquet]"

# Run as non-root; generated datasets persist under the /data volume.
RUN useradd --create-home --uid 1000 datadoom \
    && mkdir -p /data \
    && chown -R datadoom /data /app
USER datadoom

EXPOSE 8000
VOLUME ["/data"]
CMD ["datadoom", "serve", "--host", "0.0.0.0", "--port", "8000"]
