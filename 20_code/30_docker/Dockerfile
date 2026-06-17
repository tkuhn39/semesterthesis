# syntax=docker/dockerfile:1.7
#
# Hardened multi-stage build → one image serving the React SPA + FastAPI backend.
# Build context is 20_code/ (paths below are relative to it):
#   docker build -f 30_docker/Dockerfile -t semesterthesis:latest .
#
# Hardening: non-root user, no build tools / no shell-needed in the final layer,
# venv copied from an isolated builder, pinned deps (requirements.txt /
# package-lock.json), writable state confined to /data, read-only-rootfs friendly
# (see docker-compose.yml: cap_drop ALL, no-new-privileges, read_only). For strict
# supply-chain pin the base images by digest (FROM image@sha256:…).

# ---- Stage 1: build the React frontend ---------------------------------------
FROM node:24-alpine AS frontend
WORKDIR /frontend
# Reproducible install from the lockfile (devDeps needed for the Vite/TS build).
COPY 50_frontend/package.json 50_frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY 50_frontend/ ./
# Served same-origin by the backend → no API base URL baked in.
RUN npm run build

# ---- Stage 2: build the Python virtualenv (isolated from the runtime) ---------
FROM python:3.12-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 3: hardened runtime -----------------------------------------------
FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/tmp \
    MPLCONFIGDIR=/tmp/mpl \
    # Confine all writable state to /data (mount it writable; rootfs can be read-only).
    CACHE_DIR=/data/cache \
    LOG_DIR=/data/logs \
    STORAGE_LOCAL_BASE_PATH=/data/output
WORKDIR /app

# Unprivileged user + the writable state directory (also seeds a named volume).
RUN groupadd -r -g 10001 app \
    && useradd -r -u 10001 -g app -s /usr/sbin/nologin -d /tmp app \
    && mkdir -p /data/cache /data/logs /data/output \
    && chown -R app:app /data

# Python deps (from the builder venv) — no pip-installed build tools at runtime.
COPY --from=builder /opt/venv /opt/venv
# Backend application package.
COPY --chown=app:app 40_backend/app ./app
# Built SPA, served by FastAPI as static files (see app/main.py).
COPY --from=frontend --chown=app:app /frontend/dist ./app/static

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status==200 else 1)"]

LABEL org.opencontainers.image.title="Gear Analysis (TUM/FZG)" \
      org.opencontainers.image.description="Plastic-gear tooth-root capacity tool — FastAPI + React SPA" \
      org.opencontainers.image.licenses="MIT"

# exec form → uvicorn is PID 1 and receives SIGTERM for graceful shutdown.
ENTRYPOINT ["uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000"]
