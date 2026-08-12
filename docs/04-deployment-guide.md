# Deployment Guide

## 1. Local Development Setup

### Prerequisites

- **Python 3.10–3.13** (Python 3.14 is not supported by the currently pinned Pydantic/PyO3 dependency chain)
- **Node.js 20.19+ or 22.12+** (tested with 24.x; required by Vite 8)
- **npm** (comes with Node.js)
- **Git** (for cloning the repository)

### 1.1 Clone the Repository

```bash
git clone <repository-url> ai-db-creator
cd ai-db-creator
```

### 1.2 Backend Setup

```bash
cd backend

# Create and activate a virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Edit .env or copy from .env.example:
cp .env.example .env
```

Edit `.env` with at least one LLM provider API key:

```ini
# Required: at least one provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# Optional providers
GOOGLE_API_KEY=your-google-gemini-key
GROQ_API_KEY=your-groq-key
OPENROUTER_API_KEY=your-openrouter-key

# Optional: local LLM
USE_OLLAMA=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Optional: Celery (for async tasks)
# Install Redis separately and configure:
# REDIS_URL=redis://:URL_SAFE_PASSWORD@localhost:6379/0
LLM_MAX_REQUESTS_PER_MINUTE=8
```

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

### 1.3 Frontend Setup

Open a second terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend is now available at `http://localhost:5173` (Vite default).

### 1.4 Verify Installation

1. Open `http://localhost:5173` in a browser.
2. You should see the Dashboard page.
3. Check the LLM status indicator in the bottom-right corner — it should show your configured provider.
4. Create a test project and generate a schema to verify end-to-end functionality.

---

## 2. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | No | `openai` | One of: `openai`, `google`, `groq`, `openrouter`, `ollama` |
| `OPENAI_API_KEY` | Conditional | — | Required if provider is `openai` or as fallback |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model name |
| `GOOGLE_API_KEY` | Conditional | — | Required if provider is `google` |
| `GOOGLE_MODEL` | No | `gemini-2.0-flash` | Google Gemini model name |
| `GROQ_API_KEY` | Conditional | — | Required if provider is `groq` |
| `GROQ_MODEL` | No | `llama3-70b-8192` | Groq model name |
| `OPENROUTER_API_KEY` | Conditional | — | Required if provider is `openrouter` |
| `OPENROUTER_MODEL` | No | `openai/gpt-4o-mini` | OpenRouter model path |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama3` | Ollama model name |
| `USE_OLLAMA` | No | `false` | Force Ollama provider regardless of `LLM_PROVIDER` |
| `REDIS_URL` | No | — | Authenticated Redis URL for Celery (omit for sync-only operation) |
| `LLM_MAX_REQUESTS_PER_MINUTE` | No | `8` | Global provider throttle; keep at 8 for the test API capped at 10/min |
| `LOG_LEVEL` | No | `DEBUG` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `EXPERIMENT_MODE` | No | `false` | Enable experiment-specific features |

---

## 3. Backend Launch (Production)

For production-like local testing:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

- `--host 0.0.0.0` makes the server accessible on the network.
- `--workers 4` runs 4 Uvicorn worker processes.
- Remove `--reload` for production.

### Celery Workers (Optional, for Async Tasks)

```bash
# Start Redis (Docker recommended)
docker run -d -p 127.0.0.1:6379:6379 redis:7-alpine redis-server --requirepass URL_SAFE_PASSWORD

# Start the Celery worker
cd backend
celery -A app.tasks worker --loglevel=info
```

Without Redis/Celery, the `/generate-async`, `/populate-async`, and `/export-async` endpoints will not work, but all synchronous endpoints function normally.

---

## 4. Docker Deployment

The project includes a `docker-compose.yml` for full-stack deployment with all services:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Services

| Service | Image | Port | Description |
|---|---|---|---|
| `redis` | redis:7-alpine | 6379 | Celery message broker |
| `backend` | ./backend/Dockerfile | 8000 | FastAPI + Uvicorn |
| `worker` | ./backend/Dockerfile | — | Celery worker (same image, different command) |
| `frontend` | ./frontend/Dockerfile | 3000 | Nginx-served React build |
| `nginx` | nginx:alpine | 80 | Reverse proxy (optional) |

### Environment Variables for Docker

Create a `.env` file in the project root (used by docker-compose):

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
POSTGRES_PASSWORD=<from-secret-store>
REDIS_PASSWORD=<long-url-safe-value-from-secret-store>
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=<from-secret-store>
LLM_MAX_REQUESTS_PER_MINUTE=8
```

Or pass them inline:

```bash
LLM_PROVIDER=google GOOGLE_API_KEY=... docker-compose up -d
```

### Building Individual Containers

```bash
# Backend only
docker build -t ai-db-creator-backend ./backend

# Frontend only
docker build -t ai-db-creator-frontend ./frontend
```

---

## 5. Production Considerations

### 5.1 Security

- **API Keys** — Never commit `.env` files to version control. Use secrets management or environment variables in production.
- **CORS** — The current configuration allows all origins (`allow_origins=["*"]`). Restrict this in production.
- **Rate Limiting** — The API has a default limit of 1000 requests/hour. Adjust in `app/main.py` as needed.
- **File Uploads** — Uploaded files are stored in `backend/uploads/` and `backend/projects/`. Ensure these directories are not publicly accessible.

### 5.2 Data Persistence

- **Application state** (`app.db`) — Contains project metadata, schemas, document references. Must be backed up regularly.
- **Project databases** (`projects/{id}/database.sqlite`) — Each project's generated database. These can be large.
- **Uploaded files** (`uploads/`) — Original uploaded documents. Can be deleted after processing (but are retained for reproducibility).
- **Interaction logs** (`projects/interactions_store.json`) — Research data. Must be preserved for the duration of the study.

### 5.3 Scalability

- The system is designed for **single-user research use**. It is not horizontally scalable.
- SQLite supports only one writer at a time. For multi-user scenarios, replace with PostgreSQL.
- LLM API calls are the primary bottleneck. Celery workers help by offloading to background processes.

### 5.4 Monitoring

- Logs are written via Loguru to stdout. Configure file logging in `app/utils/logger.py` for production.
- The `/health` endpoint provides basic health monitoring.
- Celery task results are transient (stored in Redis). Enable a result backend for production monitoring.

### 5.5 File System Layout

```
backend/
├── app/                    # Application code
├── uploads/                # Uploaded documents
├── projects/               # Per-project directories
│   ├── {project_id}/
│   │   ├── database.sqlite # Generated database
│   │   ├── backups/        # Snapshot backups
│   │   └── interactions.json # Per-project export
│   ├── surveys/            # NASA-TLX / SUS responses
│   └── interactions_store.json # Global interaction log
├── logs/                   # Application logs
├── app.db                  # Application state database
├── .env                    # Configuration
└── requirements.txt
```
