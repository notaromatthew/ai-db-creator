# AI DB Creator // Piattaforma di ricerca per la generazione di database con LLM — Bilingual README

## Italiano

### Panoramica

AI-DB-Creator è una piattaforma di ricerca che consente a utenti non esperti di creare database relazionali normalizzati e popolati a partire da descrizioni in linguaggio naturale e documenti eterogenei (PDF, Excel, CSV, TXT). Il sistema combina un frontend React + TailwindCSS con un backend FastAPI e usa un LLM configurabile (OpenAI, Google Gemini, Groq, OpenRouter, Ollama) per progettazione dello schema, estrazione dati e traduzione da linguaggio naturale a SQL.

Il database risultante può essere esplorato tramite un'interfaccia CRUD interattiva, interrogato in linguaggio naturale ed esportato come DDL + INSERT per SQLite, PostgreSQL, MySQL e SQL Server.

### Domande di ricerca

- **RQ0:** come si confronta il flusso completo AI + Interfaccia con un processo interamente manuale per utenti non esperti?
- **RQ1:** come si confronta la qualità degli schemi generati via LLM con schemi gold-standard creati a mano, giudicata da esperti di database?
- **RQ2:** quanto è accurata la generazione automatica dei dati al livello di cella, rispetto a dati di ground truth?
- **RQ3:** un'interfaccia visuale human-in-the-loop migliora la qualità dello schema rispetto a un approccio solo automatico?
- **RQ4:** quali pattern di interazione emergono quando utenti non esperti progettano database tramite un'interfaccia LLM?

Il software include una modalità sperimentale **draft** a tre bracci: **Manuale**, **AI-Only** e **AI + Interfaccia**. I contrasti pianificati sono Manuale vs AI + Interfaccia per RQ0 e AI-Only vs AI + Interfaccia per RQ3; protocollo, allocazione stratificata e analisi confermativa non sono ancora congelati o approvati.

### Avvio

Backend:

```bash
cd backend
# Python supportato: 3.10–3.13 (ancorato a 3.13 via backend/.python-version)
py -3.13 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
# Modifica .env con la chiave del provider LLM (vedi backend/.env.example)
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

### Verifiche automatiche

```bash
cd backend
python -m pytest

cd ../frontend
npm run test
npm run build
```

Python 3.14 non è attualmente supportato dalla catena di dipendenze Pydantic/PyO3 a versioni fisse.

### Avvio con Docker Compose

L'intera pila (Redis, API, frontend, worker Celery e reverse proxy) si avvia con un solo comando:

```bash
docker compose up --build
```

I servizi definiti in `docker-compose.yml`:

| Servizio | Esposizione | Ruolo |
|---|---|---|
| `redis` | `6379` | Broker dei messaggi per Celery |
| `backend` | `8000` | API FastAPI (uvicorn) |
| `frontend` | `3000` | UI React (nginx interno) |
| `worker` | — | Celery worker (`celery -A app.tasks worker`) |
| `nginx` | `80` | Proxy non richiesto per lo sviluppo locale |

### Celery / task asincroni

Gli endpoint sincroni (CRUD, schema, populate) non richiedono alcuna infrastruttura esterna. Celery + Redis servono **solo** per le operazioni asincrone:

- `POST /api/projects/{id}/generate-async` — generazione schema asincrona
- `POST /api/projects/{id}/populate-async` — popolamento asincrono
- `POST /api/projects/{id}/export-async` — export asincrono
- `GET /api/tasks/{id}` — polling dello stato del task

Ogni task viene associato all'utente e al progetto che lo ha creato. Il polling restituisce `404` per task sconosciuti o appartenenti a un altro utente. Il registro usa Redis con TTL (`TASK_REGISTRY_TTL_SECONDS`, default 3600); il fallback in memoria è destinato al solo sviluppo su processo singolo.

Per lo sviluppo locale puoi avviare un worker a parte:

```bash
cd backend
celery -A app.tasks worker --loglevel=info
```

---

## English

### Overview

AI DB-Creator is a research platform that lets non-expert users create **normalized, populated databases** from natural-language descriptions and heterogeneous documents (PDF, Excel, CSV, TXT). It combines a React + TailwindCSS frontend with a FastAPI backend and a configurable LLM (OpenAI, Google Gemini, Groq, OpenRouter, Ollama) for schema design, data extraction, and natural-language-to-SQL translation.

The resulting database can be explored through an interactive CRUD interface, queried in natural language, and exported as DDL + INSERT for SQLite, PostgreSQL, MySQL, and SQL Server.

### Research questions

- **RQ0**: How does a complete AI + Interface workflow compare with a fully manual process for non-expert users?
- **RQ1**: How does the quality of LLM-generated schemas compare with hand-made gold-standard schemas, judged by database experts?
- **RQ2**: How accurate is automatic data population at the cell level, measured against ground-truth data?
- **RQ3**: Does a human-in-the-loop visual interface improve schema quality compared to an automatic-only approach?
- **RQ4**: What interaction patterns emerge when non-expert users design databases through an LLM-powered interface?

The system includes a **draft, proposed** three-arm between-subjects experiment mode: **Manual, AI-Only, and AI + Interface**. Manual vs AI + Interface is the planned RQ0 contrast; AI-Only vs AI + Interface is the planned RQ3 contrast. The protocol is not yet preregistered or ethics-approved, and its sample-size assumption remains to be validated through power analysis. See `docs/RESEARCH-READINESS-DRAFTS.md`.

### Running the system

Backend:

```bash
cd backend
# Supported Python: 3.10–3.13 (pinned to 3.13 via backend/.python-version)
py -3.13 -m venv .venv
.\.venv\Scripts\activate        # PowerShell
pip install -r requirements.txt
# Edit .env with your chosen LLM provider key (see backend/.env.example)
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Never commit `backend/.env`. Copy `backend/.env.example`, keep the real key local, and rotate any key that may have entered repository history.

### Automated checks

```bash
cd backend
python -m pytest

cd ../frontend
npm run test
npm run build
```

### Docker Compose setup

The full stack (Redis, API, frontend, Celery worker, reverse proxy) starts with a single command:

```bash
docker compose up --build
```

Services defined in `docker-compose.yml`:

| Service | Exposed | Role |
|---|---|---|
| `redis` | `6379` | Message broker for Celery |
| `backend` | `8000` | FastAPI (uvicorn) |
| `frontend` | `3000` | React UI (internal nginx) |
| `worker` | — | Celery worker (`celery -A app.tasks worker`) |
| `nginx` | `80` | Reverse proxy (optional for local development) |

### Celery / async tasks

Synchronous endpoints (CRUD, schema, populate) need no external infrastructure. Celery + Redis are required **only** for async operations:

- `POST /api/projects/{id}/generate-async` — async schema generation
- `POST /api/projects/{id}/populate-async` — async population
- `POST /api/projects/{id}/export-async` — async export
- `GET /api/tasks/{id}` — task status polling

For local development you can run a worker separately:

```bash
cd backend
celery -A app.tasks worker --loglevel=info
```

Python 3.14 is not currently supported by the pinned Pydantic/PyO3 dependency chain.

---

## API Endpoints (condivise / shared)

Tutti gli endpoint relativi a un progetto richiedono autenticazione e verificano che il progetto appartenga al subject (`sub`) del token corrente. I progetti di altri utenti vengono restituiti come non trovati. I risultati automatici del benchmark sono condivisi, mentre voti, commenti e avanzamento del benchmark sono limitati all'utente autenticato.

### Projects
- `POST /api/projects` - Create / crea progetto
- `GET /api/projects` - List projects
- `GET /api/projects/{id}` - Get project
- `DELETE /api/projects/{id}` - Delete project and all its artifacts

### Schema
- `POST /api/projects/{id}/generate` - Generate schema from prompt + documents
- `GET /api/projects/{id}/schema` - Get generated schema
- `PUT /api/projects/{id}/schema` - Update schema
- `POST /api/projects/{id}/chat` - Interactive schema chat
- `POST /api/projects/{id}/chat-accept` - Accept schema from chat

### Documents
- `POST /api/projects/{id}/documents` - Upload PDF/XLS/CSV/TXT/SQL
- `GET /api/projects/{id}/documents` - List documents
- `DELETE /api/projects/{id}/documents/{doc_id}` - Delete a document
- `POST /api/projects/{id}/import-sql` - Import schema+data from SQL file

### Data Population
- `POST /api/projects/{id}/populate` - Populate tables
- `GET /api/projects/{id}/data/stats` - Per-table row statistics
- `GET /api/projects/{id}/data/{table}` - Get table data
- `POST /api/projects/{id}/data/{table}` - Insert a row
- `PUT /api/projects/{id}/data/{table}` - Update a row
- `DELETE /api/projects/{id}/data/{table}` - Delete a row

### Query Generation
- `POST /api/projects/{id}/query` - Generate SQL from text
- `POST /api/projects/{id}/execute-query` - Execute a SQL statement

### Export / Backup / Restore
- `GET /api/projects/{id}/export` - Export schema + data
- `GET /api/projects/{id}/export-full` - Full portable export
- `POST /api/projects/{id}/backup` - Create a backup
- `GET /api/projects/{id}/backups` - List backups
- `POST /api/projects/{id}/restore` - Restore a backup

### Research Metrics
- `GET /api/projects/{id}/metrics` - Schema quality metrics
- `POST /api/projects/{id}/interactions` - Log interaction
- `GET /api/projects/{id}/interactions` - Get interaction history
- `POST /api/projects/{id}/export-interactions` - Export interactions as JSON

### Experiment Support
- `POST /api/experiments/compare` - Compare conditions
- `POST /api/surveys/nasa-tlx` - NASA-TLX survey
- `POST /api/surveys/sus` - SUS survey

### Infrastructure
- `POST /api/projects/{id}/generate-async` - Async schema generation (Celery)
- `POST /api/projects/{id}/populate-async` - Async population
- `POST /api/projects/{id}/export-async` - Async export
- `GET /api/tasks/{task_id}` - Poll an owned task (`404` for unknown/cross-tenant IDs)
- `GET /api/progress/{project_id}` - Progress events
- `POST /api/progress/{project_id}` - Report progress
- `GET /api/progress/benchmark` - Current user's benchmark progress
- `GET /api/llm/info` - Provider/model info

---

## File Structure / Struttura

```
backend/
  app/
    api/routes.py        # REST API endpoints
    api/progress.py      # Progress events
    core/
      llm.py             # LLM provider calls
      parser.py          # Document parsers (PDF/Excel/TXT/CSV)
      db_generator.py    # DB creation from schema
      sql_importer.py    # SQL file import
    models/
      schema_models.py   # Pydantic schema
      database.py        # App state models
    services/
      schema_service.py
      document_service.py
      population_service.py  # Deterministic + LLM population
      query_service.py
      metrics_service.py
      interaction_logger.py  # Sanitized, project-isolated log
      backup_service.py
    tasks.py             # Celery async tasks
    utils/
      exceptions.py
      research.py        # hashing, manifests, provenance
      logger.py          # Loguru
    config.py
  .env
  requirements.txt
  app.db

frontend/
  src/
    api/
    pages/  (Dashboard.tsx, ProjectPage.tsx)
    components/  (SchemaViewer, DataViewer, DocumentUploader,
                 PromptInput, QueryBuilder, GuidedWorkflow)
  package.json
  vite.config.ts
  tsconfig.json
```

## Ricerca metodologica / Research Methodology

### Esperimento controllato (between-subjects) / Controlled experiment

1. **Group M (Manual)**: conventional visual relational-database tool, no generative AI
2. **Group A (AI Only)**: system generates schema and population automatically
3. **Group B (AI + Interface)**: system generates first version; users review and edit via dashboard

The proposed RQ0 comparison is Manual vs AI + Interface; the proposed RQ3 comparison is AI-Only vs AI + Interface. These draft contrasts require preregistration and ethics approval before confirmatory use. See `docs/RESEARCH-READINESS-DRAFTS.md`, `docs/08-research-notes.md`, and `docs/14-usability-pilot-protocol.md`.

Offline checks are available from `backend/`: `python validate_datasets.py --datasets ../data/datasets`, `python participant_simulator.py`, and `python validate_reproducibility.py --root .. --gate software|pilot|confirmatory`. Each selected gate returns nonzero on failure; the default software gate may pass while pilot and confirmatory gates remain blocked. No command invokes a remote LLM.

Research-review candidates can be regenerated without network or LLM calls:

```bash
python data/datasets/build_research_candidates.py
cd backend
python validate_research_candidates.py
$env:EXPERIMENT_ASSIGNMENT_SEED="local-dry-run-only"  # PowerShell; never use this value for a study
python candidate_allocation_dry_run.py --input tests/fixtures/allocation_enrolments.json --output reports/allocation-candidate.json
python locked_candidate_analysis.py --input tests/fixtures/analysis_input_v1.json --output reports/analysis-candidate
```

These artifacts are deliberately labelled `candidate_unapproved`. Successful technical validation never represents expert, governance, ethics, preregistration or freeze approval.

CI and deployment distinguish software health from research readiness: a green software pipeline does not imply pilot or confirmatory eligibility. See `docs/29-ci-deployment-readiness.md` for the versioned expected-blocker gate, secret handling, container healthchecks, retention boundary and migration policy.

### Raccolta metriche / Metrics

- Schema quality: 3NF validation, relationship F1
- Data quality: precision/recall, duplicate rate
- Interaction logs: column renames, constraint additions, ignored suggestions
- Surveys: NASA-TLX (cognitive load), SUS (usability)

## Documentazione bilingue / Bilingual documentation

Documenti principali in `docs/` (italiano) e materiali strategici bilingue in root (`AGENTS.md`, `CONTRIBUTING.md`). Vedere `CHANGELOG.md` per lo stato delle modifiche.
