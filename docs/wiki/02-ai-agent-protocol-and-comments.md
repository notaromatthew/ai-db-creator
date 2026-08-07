# 02 - AI Agent Protocol & Code Improvement Comments

> **Purpose**: This document serves as a structured collaborative workspace for AI agents and human developers working on AI-DB-Creator. Agents reading or modifying the codebase should consult this protocol and log refactoring proposals or code quality findings below.

---

## 📜 Agent Guidelines for Code Improvement

1. **No Silent Fallbacks**:
   Never introduce fallback mechanisms to SQLite or unauthenticated mock endpoints. All storage must pass through PostgreSQL and all requests must validate Keycloak JWTs.

2. **Non-Blocking Asynchronous I/O**:
   When making HTTP calls to external AI providers (Ollama, Gemini, Groq, OpenRouter), always use `httpx.AsyncClient` inside `async def` FastAPI route handlers to avoid blocking Uvicorn's event loop.

3. **Rate-Limiting & Cost Protection**:
   Ensure all LLM calls respect `settings.llm_max_requests_per_minute` and global `Limiter` settings in `app/main.py`.

4. **Continuous Test Verification**:
   Keep backend `pytest` (65/65 tests) and frontend `vitest` + `npm run build` clean at all times.

---

## 💬 Agent Comment & RFC Log

Agents and developers can append structured comments below using the following template:

```markdown
### 💡 [RFC-XXX] Title of Proposal
- **Date**: YYYY-MM-DD
- **Agent/Author**: Name or Model Version
- **Target File(s)**: `path/to/file.py`
- **Observation / Problem**: Concise description of code smell, performance bottleneck, or architecture gap.
- **Proposed Solution**: Technical description of proposed refactoring.
- **Status**: Proposed | In Review | Approved | Implemented
```

---

### 💡 [RFC-001] Async Lifespan Handler Migration for FastAPI
- **Date**: 2026-08-07
- **Agent/Author**: Antigravity AI Assistant
- **Target File(s)**: [app/main.py](file:///Users/davide/Documents/repos/ai-db-creator/backend/app/main.py)
- **Observation / Problem**: FastAPI `on_event("startup")` is deprecated in current FastAPI versions in favor of `asynccontextmanager` lifespan handlers.
- **Proposed Solution**: Replace `@app.on_event("startup")` with `@asynccontextmanager async def lifespan(app: FastAPI)` to ensure forward compatibility with FastAPI 0.110+ and eliminate Pytest deprecation warnings.
- **Status**: Proposed

---

### 💡 [RFC-002] Connection Pooling Hardening for Remote PostgreSQL
- **Date**: 2026-08-07
- **Agent/Author**: Antigravity AI Assistant
- **Target File(s)**: [app/models/database.py](file:///Users/davide/Documents/repos/ai-db-creator/backend/app/models/database.py)
- **Observation / Problem**: High concurrency benchmark runs can exhaust PostgreSQL connection limits if sessions are not pooled efficiently.
- **Proposed Solution**: Configure `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, and `pool_recycle=1800` on SQLAlchemy engine initialization for remote PostgreSQL instance `89.168.29.98:12000`.
- **Status**: Implemented

---

### 💡 [RFC-003] OIDC Token Refresh Synchronization in KeycloakContext
- **Date**: 2026-08-07
- **Agent/Author**: Antigravity AI Assistant
- **Target File(s)**: [src/context/KeycloakContext.tsx](file:///Users/davide/Documents/repos/ai-db-creator/frontend/src/context/KeycloakContext.tsx)
- **Observation / Problem**: Keycloak JS tokens expire every 5 minutes; if a background fetch fires during token expiration, API requests throw 401 Unauthorized.
- **Proposed Solution**: Added `onTokenExpired` listener calling `updateToken(30)` and syncing new token immediately to `ApiClient.setToken()`.
- **Status**: Implemented
