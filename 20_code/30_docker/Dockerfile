# syntax=docker/dockerfile:1
#
# Multi-stage build producing a single image that serves the React SPA and the
# FastAPI backend together.
#
# Build context is 20_code/ (so paths below are relative to 20_code):
#   docker build -f 30_docker/Dockerfile -t semesterthesis:latest .

# ---- Stage 1: build the React frontend ---------------------------------------
FROM node:24-alpine AS frontend
WORKDIR /frontend
COPY 50_frontend/package*.json ./
RUN npm install
COPY 50_frontend/ ./
# SPA is served same-origin by the backend, so no API base URL is needed.
RUN npm run build

# ---- Stage 2: Python runtime serving API + static SPA ------------------------
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend application package
COPY 40_backend/app ./app
# Built frontend, served by FastAPI as static files (see app/main.py)
COPY --from=frontend /frontend/dist ./app/static

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
