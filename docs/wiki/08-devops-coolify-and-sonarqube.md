# 08 - DevOps, Coolify Deployment & Quality Gates

> **Source Documents**: `docs/04-deployment-guide.md`, `docs/17-technical-review-dossier.md`

---

## 1. Coolify PaaS Production Infrastructure

AI-DB-Creator is configured for containerized deployment on Coolify PaaS using `docker-compose.coolify.yml`.

```
[ Coolify PaaS Reverse Proxy (Traefik / Nginx) ]
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
[ Frontend Container ]      [ Backend Container ]
(React / Nginx :80)         (FastAPI / Uvicorn :8000)
```

---

## 2. Docker Multi-Stage Builds

### Frontend Dockerfile (`frontend/Dockerfile`)
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production Serving
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Backend Dockerfile (`backend/Dockerfile`)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 3. SonarQube Code Quality Gates

- **Instance Endpoint**: `http://o4sn9bs961jvxn32hs18a81p.89.168.29.98:9000`
- **Configuration**: `sonar-project.properties`
- **Quality Criteria**:
  1. Zero critical security vulnerabilities or exposed secrets.
  2. Maintainability Rating: **A**.
  3. Test Coverage: > 80% on backend Python modules (`pytest`).
