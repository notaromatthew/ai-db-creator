# 04 - Coolify PaaS & DevOps Deployment Guide

> **Production Deployment Infrastructure**: AI-DB-Creator is packaged for automatic deployment via Coolify PaaS, Docker multi-stage builds, and SonarQube quality enforcement.

---

## 🐳 Docker Stack & Coolify Configuration

- **`docker-compose.coolify.yml`**: Defines production orchestration for backend FastAPI and frontend React services.
- **Frontend Dockerfile**: Multi-stage build (`node:20-alpine` build -> `nginx:alpine` runtime).
- **Backend Dockerfile**: `python:3.12-slim` image with PostgreSQL drivers (`psycopg2-binary`) and Uvicorn server.

---

## 🛡️ SonarQube Quality Gate

- **Instance URL**: supplied via `SONAR_HOST_URL` by the deployment operator.
- **Config**: `sonar-project.properties`
- **Quality Gates**:
  - Zero critical security vulnerabilities
  - Automated test coverage > 80%
  - Maintainability rating 'A'

---

## ⚙️ Environment Variables Verification Checklist

| Variable Name | Required Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `<required deployment secret>` | Production PostgreSQL Connection String |
| `KEYCLOAK_URL` | `<required HTTPS URL>` | OIDC Keycloak Realm Server |
| `LLM_PROVIDER` | `ollama` | System Default AI Provider |
| `OLLAMA_MODE` | `remote` | Ollama Server Location Mode |
| `OLLAMA_BASE_URL`| `<required URL when Ollama is used>` | Remote Ollama Inference Host |
| `OLLAMA_API_KEY` | `<OLLAMA_API_KEY>` | Remote Ollama Bearer Token |

