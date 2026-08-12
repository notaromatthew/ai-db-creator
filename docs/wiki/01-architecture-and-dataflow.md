# 01 - Architecture and Dataflow Map

## 🏗️ Core Architecture Overview

AI-DB-Creator is an AI research platform for automated relational database schema generation, normalization (3NF), structured population, and experimental evaluation.

```
[ Frontend: React / Vite / Tailwind ]
       │
       │ HTTP / OIDC Bearer JWT
       ▼
[ FastAPI Backend (Uvicorn :8000) ] ── (OIDC JWKS) ──► [ Keycloak Server ]
       │                                              (environment-managed URL)
       ├──► [ PostgreSQL Database ]
       │    (environment-managed DATABASE_URL)
       │
       └──► [ LLM Orchestration Engine ]
            ├── Optional local/remote Ollama (explicit URL)
            ├── Google Gemini (gemini-2.0-flash)
            ├── OpenAI / Groq / OpenRouter
```

---

## 🔒 Keycloak OIDC Authentication Layer

- **Realm**: `aidbcreator`
- **Client**: `aidbcreator-app` (Public client, PKCE enabled)
- **Token Verification**: `app/core/auth.py` fetches public JWKS keys directly from `{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs`.
- **User Scoping**: Every `Project` in the PostgreSQL database stores a `user_id` string extracted from the JWT `sub` claim. Users only query and modify projects owned by their identity.

---

## 🗄️ Database & Domain Models (`app/models/database.py`)

1. **`Project`**:
   - `id`: UUID (Primary Key)
   - `user_id`: Keycloak Subject ID (`sub`)
   - `name`, `description`, `prompt`, `created_at`, `updated_at`

2. **`BenchmarkResult`**:
   - `id`: Integer PK
   - `scenario_name`, `provider`, `model`
   - `nf3_percentage`, `relationship_f1`, `cell_precision`
   - `latency_seconds`, `cost_usd`, `timestamp`

3. **`UserVote`**:
   - `id`: Integer PK
   - `benchmark_id`: Foreign Key to `BenchmarkResult`
   - `user_id`: Keycloak Subject ID
   - `likert_score`: 1 (Scarso) to 5 (Eccellente)
   - `comments`, `created_at`

---

## 🤖 LLM Orchestration Engine (`app/core/llm.py`)

- **Provider selection**: configured through environment variables; local Ollama defaults to `http://localhost:11434`.
- **Remote Ollama API Endpoint**: must be supplied explicitly by the deployment operator.
- **Authentication**: `Authorization: Bearer <OLLAMA_API_KEY>`

- **Model Discovery**: `GET /api/settings/ollama-models` queries `/api/tags` asynchronously via `httpx.AsyncClient` to populate available models (`gemma2:9b`, `qwen3:0.6b`, `llama3.2:1b`, `gemma3:270m`).
- **Configuration Persistence**: `PUT /api/settings` changes runtime settings only; secrets are write-only and `.env` is never rewritten.
