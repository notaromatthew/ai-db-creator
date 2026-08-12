# 02 - Multi-Agent System & Agent RFC Comment Log

> **Source Documents**: `docs/01-multi-agent-playbook.md`, `docs/15-ai-agent-changelog.md`, `AGENTS.md`

---

## 1. Multi-Agent Playbook Architecture

AI-DB-Creator utilizes specialized AI subagents and operational directives to ensure code quality, scientific reproducibility, and strict adherence to project constraints.

```
       [ Lead Architect / Coordinating Agent ]
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
[ Schema Engineer ] [ Population Spec ] [ Quality & Security ]
 (3NF Normalization) (Full-LLM & Fallback) (Keycloak / Postgres / Tests)
```

---

## 2. Operational Directives for AI Agents

1. **Strict Online & Authenticated Operation**:
   - **PostgreSQL**: Production uses an environment-managed `DATABASE_URL`; no remote fallback is embedded in code.
   - **Keycloak OIDC**: Protected routes validate JWT Bearer tokens from the environment-managed `KEYCLOAK_URL` (Realm `aidbcreator`).
   - **Zero Fallbacks**: Do not fallback to SQLite or mock unauthenticated dev users.

2. **Default AI Provider**:
   - Remote Ollama is optional and its endpoint must be supplied explicitly; no public endpoint is a built-in default.

3. **Asynchronous Non-Blocking I/O**:
   - All network calls to LLM endpoints must use `httpx.AsyncClient` inside `async def` FastAPI handlers to prevent blocking Uvicorn's event loop.

4. **Testing Suite Integrity**:
   - Maintain 100% passing status across backend `pytest` (65/65 tests) and frontend `vitest` + `npm run build`.

---

## 3. Agent Comment & RFC Log

AI Agents and developers log architectural findings, refactoring suggestions, and improvement proposals below.

```markdown
### 💡 [RFC-ID] Title
- **Date**: YYYY-MM-DD
- **Author**: Agent Name / Model Version
- **Target Component**: Path to file
- **Problem Statement**: Technical observation
- **Proposed Solution**: Refactoring strategy
- **Status**: Proposed | Implemented | Superseded
```

---

### 💡 [RFC-001] Async Lifespan Handler Migration for FastAPI
- **Date**: 2026-08-07
- **Author**: Antigravity AI Assistant
- **Target Component**: [backend/app/main.py](file:///Users/davide/Documents/repos/ai-db-creator/backend/app/main.py)
- **Problem Statement**: FastAPI `@app.on_event("startup")` is deprecated in current FastAPI versions in favor of `asynccontextmanager` lifespan handlers.
- **Proposed Solution**: Replace `@app.on_event("startup")` with `@asynccontextmanager async def lifespan(app: FastAPI)` to ensure forward compatibility with FastAPI 0.110+ and eliminate Pytest deprecation warnings.
- **Status**: Proposed

---

### 💡 [RFC-002] Connection Pooling Hardening for Remote PostgreSQL
- **Date**: 2026-08-07
- **Author**: Antigravity AI Assistant
- **Target Component**: [backend/app/models/database.py](file:///Users/davide/Documents/repos/ai-db-creator/backend/app/models/database.py)
- **Problem Statement**: High concurrency benchmark runs can exhaust PostgreSQL connection limits if sessions are not pooled efficiently.
- **Proposed Solution**: Configure `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, and `pool_recycle=1800` for the deployment-managed PostgreSQL instance.
- **Status**: Implemented

---

### 💡 [RFC-003] OIDC Token Refresh Synchronization in KeycloakContext
- **Date**: 2026-08-07
- **Author**: Antigravity AI Assistant
- **Target Component**: [frontend/src/context/KeycloakContext.tsx](file:///Users/davide/Documents/repos/ai-db-creator/frontend/src/context/KeycloakContext.tsx)
- **Problem Statement**: Keycloak JS tokens expire every 5 minutes; if a background fetch fires during token expiration, API requests throw 401 Unauthorized.
- **Proposed Solution**: Added `onTokenExpired` listener calling `updateToken(30)` and syncing new token immediately to `ApiClient.setToken()`.
- **Status**: Implemented

---

### 💡 [RFC-004] CORS Regex Origin Support for Authenticated Requests
- **Date**: 2026-08-07
- **Author**: Antigravity AI Assistant
- **Target Component**: [backend/app/main.py](file:///Users/davide/Documents/repos/ai-db-creator/backend/app/main.py)
- **Problem Statement**: `allow_origins=["*"]` with `allow_credentials=True` caused browser OPTIONS preflight failures (`TypeError: Failed to fetch`).
- **Proposed Solution**: Replaced `allow_origins=["*"]` with `allow_origin_regex=r"https?://.*"` to enable valid credentials support for local and remote dev environments.
- **Status**: Implemented
