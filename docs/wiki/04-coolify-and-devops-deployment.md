# 04 - Coolify PaaS & DevOps Deployment Guide

> **Production Deployment Infrastructure**: AI-DB-Creator is packaged for automatic deployment via Coolify PaaS, Docker multi-stage builds, and SonarQube quality enforcement.

---

## 🐳 Docker Stack & Coolify Configuration

- **`docker-compose.coolify.yml`**: Defines production orchestration for backend FastAPI and frontend React services.
- **Frontend Dockerfile**: Multi-stage build (`node:20-alpine` build -> `nginx:alpine` runtime).
- **Backend Dockerfile**: `python:3.12-slim` image with PostgreSQL drivers (`psycopg2-binary`) and Uvicorn server.

---

## 🛡️ SonarQube Quality Gate

- **Instance URL**: `http://o4sn9bs961jvxn32hs18a81p.89.168.29.98:9000`
- **Config**: `sonar-project.properties`
- **Quality Gates**:
  - Zero critical security vulnerabilities
  - Automated test coverage > 80%
  - Maintainability rating 'A'

---

## ⚙️ Environment Variables Verification Checklist

| Variable Name | Required Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://postgres:<POSTGRES_PASSWORD>@89.168.29.98:12000/postgres` | Production PostgreSQL Connection String |
| `KEYCLOAK_URL` | `https://keycloak-pw9ut4s1h3aodstrsw1gd84o.89.168.29.98.sslip.io` | OIDC Keycloak Realm Server |
| `LLM_PROVIDER` | `ollama` | System Default AI Provider |
| `OLLAMA_MODE` | `remote` | Ollama Server Location Mode |
| `OLLAMA_BASE_URL`| `https://ollamaapi-u11fj34m2h9druz26hamz3xb.89.168.29.98.sslip.io` | Remote Ollama Inference Host |
| `OLLAMA_API_KEY` | `<OLLAMA_API_KEY>` | Remote Ollama Bearer Token |

