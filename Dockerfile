# Multi-stage Dockerfile for Coolify Deployment
# Stage 1: Build Frontend React App
FROM node:24-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend FastAPI + Static Asset Service
FROM python:3.13-slim AS runner
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini backend/migrate_database.py ./
COPY --from=frontend-builder /app/frontend/dist ./static

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://127.0.0.1:8000/ready || exit 1

CMD ["sh", "-c", "python migrate_database.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
