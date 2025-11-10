# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system build deps only if needed (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application source
COPY . .

# Expose default port
EXPOSE 8000

# Environment variables (configure via deployment)
ENV AMAP_WEB_KEY="" \
    AMAP_SECURITY_JS_CODE="" \
    SESSION_SECRET="change-me-please" \
    SUPABASE_URL="" \
    SUPABASE_ANON_KEY=""

# Run the FastAPI app
CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]