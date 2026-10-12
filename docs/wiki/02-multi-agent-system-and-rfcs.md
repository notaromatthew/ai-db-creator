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
   - **PostgreSQL**: Always use the production PostgreSQL database URL (`postgresql://postgres:...@89.168.29.98:12000/postgres`).
   - **Keycloak OIDC**: All protected routes must validate JWT Bearer tokens issued by `https://keycloak-pw9ut4s1h3aodstrsw1gd84o.89.168.29.98.sslip.io` (Realm `aidbcreator`).
   - **Zero Fallbacks**: Do not fallback to SQLite or mock unauthenticated dev users.

2. **Default AI Provider**:
   - Remote Ollama server (`https://ollamaapi-u11fj34m2h9druz26hamz3xb.89.168.29.98.sslip.io`) is the system default provider (`LLM_PROVIDER=ollama`, `OLLAMA_MODE=remote`).

3. **Asynchronous Non-Blocking I/O**:
   - All network calls to LLM endpoints must use `httpx.AsyncClient` inside `async def` FastAPI handlers to prevent blocking Uvicorn's event loop.

4. **Testing Suite Integrity**:
   - Maintain 100% passing status across backend `pytest` (91 backend tests, 28 frontend tests) and frontend `vitest` + `npm run build`.

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
- **Status**: Implemented

---

### 💡 [RFC-002] Connection Pooling Hardening for Remote PostgreSQL
- **Date**: 2026-08-07
- **Author**: Antigravity AI Assistant
- **Target Component**: [backend/app/models/database.py](file:///Users/davide/Documents/repos/ai-db-creator/backend/app/models/database.py)
- **Problem Statement**: High concurrency benchmark runs can exhaust PostgreSQL connection limits if sessions are not pooled efficiently.
- **Proposed Solution**: Configured `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, and `pool_recycle=1800` on SQLAlchemy engine initialization for remote PostgreSQL instance `89.168.29.98:12000`.
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


---

### 💡 [RFC-005] Project ownership enforcement on per-id routes
- **Date**: 2026-10-12
- **Author**: Claude (Sonnet 5.5)
- **Target File(s)**: `backend/app/api/routes.py`
- **Observation / Problem**: `GET/DELETE /api/projects/{id}` did not check `user_id`; any authenticated user could read or delete another user's project. About 30 other `/projects/{project_id}/...` routes have the same gap.
- **Proposed Solution**: `_owned_project()` now guards GET and DELETE (404 on mismatch). Extend it to the remaining routes as a router-level dependency. Legacy projects with `user_id` NULL stay visible to everyone.
- **Status**: In Review (GET/DELETE implemented, remaining routes open)

---

### 💡 [RFC-006] Benchmark token/cost estimate TypeError
- **Date**: 2026-10-12
- **Author**: Claude (Sonnet 5.5)
- **Target File(s)**: `backend/app/services/benchmark_service.py`
- **Observation / Problem**: `est_tokens` added an int to a list, so every `POST /api/benchmark/run` returned 500 and nothing was saved. No benchmark result produced before this fix exists with this metric.
- **Proposed Solution**: `est_tokens = words(prompt)*5 + words(schema dump)`; `est_cost = est_tokens * 0.000002`. Comparability note: `token_cost_estimate` is defined from this date.
- **Status**: Implemented

---

### 💡 [RFC-007] Open items handed to Codex / Antigravity
- **Date**: 2026-10-12
- **Author**: Claude (Sonnet 5.5)
- **Target File(s)**: various
- **Observation / Problem**: Codex and Antigravity could not be run headless from the Claude session; coordination is via this file.
- **Proposed Solution** (open, pick one and mark it here):
  1. Ownership check on all `/projects/{project_id}/...` routes (RFC-005).
  2. `core/auth.py`: JWKS fetched with `verify=False`, never refreshed, audience check disabled.
  3. `PUT /api/settings` writes API keys in plain text to `./.env`; `GET /api/settings` returns them in clear.
  4. `run_model_benchmark` mutates global `settings`.
  5. Docs `00-project-overview.md` and `02-technical-manual.md` describe SQLite as app DB; code uses PostgreSQL only (SQLite only for generated per-project DBs). Align docs.
  6. `config.py` default `database_url` embeds a remote host/credentials: remove and rotate.
  7. `tests/test_population_pipeline.py::test_parser_empty_is_propagated_as_warning` makes an unmocked LLM call and can hang: mock it.
  8. Cloud Run: persistent storage for `uploads/`/`projects/` (GCS volume), Redis/Celery for `*-async` endpoints.
- **Status**: Proposed
