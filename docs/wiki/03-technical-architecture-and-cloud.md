# 03 - Technical Architecture, Cloud Maturity & AGID Compliance

> **Source Documents**: `docs/02-technical-manual.md`, `docs/05-cloud-maturity.md`, `docs/06-agid-compliance.md`

---

## 1. System Architecture & Tech Stack

AI-DB-Creator is built around an event-driven, microservices-capable, modular architecture.

```
                  ┌─────────────────────────────────┐
                  │   React 18 + Vite + Tailwind   │
                  └────────────────┬────────────────┘
                                   │ HTTP REST / OIDC JWT
                                   ▼
                  ┌─────────────────────────────────┐
                  │      FastAPI Backend Engine     │
                  └──────┬───────────────────┬──────┘
                         │                   │
             ┌───────────┴──────────┐ ┌──────┴──────────────┐
             ▼                      ▼ ▼                     ▼
  [ PostgreSQL Database ]   [ Keycloak Server ]   [ LLM Provider Engine ]
  (Relational Storage)       (OIDC Realm)          (Remote Ollama / Gemini)
```

---

## 2. Component Specifications

### 2.1 Backend Core (`backend/app/`)
- **FastAPI 0.115**: Dynamic REST API with Pydantic v2 schemas and OpenAPI 3.0 documentation.
- **SQLAlchemy 2.0 ORM**: Manages persistence for `Project`, `BenchmarkResult`, and `UserVote` entities.
- **Keycloak OIDC Validator** (`app/core/auth.py`): Fetches JWKS public keys dynamically to validate Bearer tokens.
- **LLM Abstraction Layer** (`app/core/llm.py`): Unified provider interface targeting Remote Ollama (`OLLAMA_MODE=remote`), Google Gemini (`gemini-2.0-flash`), OpenAI, Groq, and OpenRouter.

### 2.2 Frontend Application (`frontend/src/`)
- **React 18 & TypeScript**: Component-based UI with strict type checking.
- **TanStack React Query v5**: Server-state management, query caching, and instant cache invalidation upon settings updates.
- **Keycloak JS v26**: Single-Sign-On authentication state management with automatic background token refreshes (`onTokenExpired`).
- **TailwindCSS v3**: Modern glassmorphism UI styling with full dark mode support.

---

## 3. Cloud Maturity Assessment

The project adheres to the Cloud Maturity Framework across 4 key dimensions:
1. **Containerization**: Fully containerized backend and frontend via Docker multi-stage builds (`Dockerfile`).
2. **Stateless Services**: The FastAPI service retains zero session state; all persistent state is delegated to remote PostgreSQL and Keycloak.
3. **Infrastructure as Code**: Coolify orchestration configuration (`docker-compose.coolify.yml`) enables 1-click cloud deployments.
4. **Observability**: Loguru structured JSON logs with correlation IDs (`run_id`).

---

## 4. AGID (Agenzia per l'Italia Digitale) Compliance

AI-DB-Creator adheres to AGID guidelines for public sector software reuse:
- **Open Source Licensing**: Distributed under permissive open-source terms.
- **Accessibility (a11y)**: Accessible UI contrast ratios and semantic HTML elements.
- **Interoperability**: Standardized REST APIs with OpenAPI specifications and multi-dialect SQL exports (PostgreSQL, SQLite, MySQL, MSSQL).
