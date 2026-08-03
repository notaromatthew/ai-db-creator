# Technical Manual

## 1. Backend API Endpoints

All endpoints are served from `http://localhost:8000/api/` unless noted. All request and response bodies are JSON (`Content-Type: application/json`) except document upload (`multipart/form-data`). The backend auto-generates OpenAPI documentation at `http://localhost:8000/docs`.

### 1.1 Project CRUD

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/projects` | Create project. Body: `{name: str, prompt?: str}`. Returns project object with UUID. |
| `GET` | `/api/projects` | List all projects. Returns array. |
| `GET` | `/api/projects/{id}` | Get single project. Returns `{id, name, prompt, schema_json, db_path, created_at, updated_at}`. |
| `DELETE` | `/api/projects/{id}` | Delete project and its database. |

### 1.2 Document Management

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/projects/{id}/documents` | Upload file (multipart). Supported: `.pdf`, `.xlsx`, `.xls`, `.csv`, `.txt`, `.sql`. |
| `GET` | `/api/projects/{id}/documents` | List documents for project. |
| `DELETE` | `/api/projects/{id}/documents/{doc_id}` | Delete a document. |

### 1.3 Schema Generation

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/projects/{id}/generate` | Quick generate schema. Body: `{prompt: str, document_ids: list[str]}`. Returns `NormalizedSchema`. |
| `POST` | `/api/projects/{id}/chat` | Interactive chat for schema generation. Body: `{message: str, document_ids: list[str]}`. Returns `{response: str, schema: object|null}`. |
| `POST` | `/api/projects/{id}/chat-accept` | Accept the last chat-generated schema. Body: full `NormalizedSchema`. |
| `GET` | `/api/projects/{id}/schema` | Get current schema. Returns `NormalizedSchema` or `null`. |
| `PUT` | `/api/projects/{id}/schema` | Update schema (user edits). Body: full `NormalizedSchema`. Triggers DB migration. |
| `POST` | `/api/projects/{id}/generate-async` | Start async schema generation (Celery). Returns `{task_id, status}`. |

### 1.4 Data Population

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/projects/{id}/populate` | Populate database from documents. Body: `{document_ids: list[str]}`. Returns `{table_name: {inserted: int, skipped: int}}`. |
| `POST` | `/api/projects/{id}/populate-async` | Async population (Celery). Returns `{task_id, status}`. |

### 1.5 Data CRUD Operations

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/projects/{id}/data/stats` | Row counts per table. Returns `{table_name: count}`. |
| `GET` | `/api/projects/{id}/data/{table}` | Get rows (max 100). Returns array of dicts. |
| `PUT` | `/api/projects/{id}/data/{table}` | Update a row. Body: full row dict with primary key values. |
| `DELETE` | `/api/projects/{id}/data/{table}` | Delete a row. Body: `{pks: {pk_col: value}}`. |
| `POST` | `/api/projects/{id}/data/{table}` | Insert a new row. Body: `{col: value, ...}`. |

### 1.6 Query Execution

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/projects/{id}/query` | Generate SQL from natural language. Body: `{prompt: str, dialect?: str}`. Returns `{sql: str}`. |
| `POST` | `/api/projects/{id}/execute-query` | Execute arbitrary SQL. Body: `{sql: str}`. Returns `{columns, rows, affected}`. |

### 1.7 Import / Export

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/projects/{id}/import-sql` | Import from SQL dump. Body: multipart file + `?dialect=`. Returns `{tables: int, schema: NormalizedSchema}`. |
| `GET` | `/api/projects/{id}/export` | Export schema (format: `sql`, `json`, `csv`). |
| `GET` | `/api/projects/{id}/export-full` | Export full DB (DDL + INSERT). Query: `?dialect=sqlite|postgresql|mysql|mssql`. Returns `{format, content, extension}`. |
| `POST` | `/api/projects/{id}/export-async` | Async export (Celery). Returns `{task_id, status}`. |

### 1.8 Backup and Restore

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/projects/{id}/backup` | Create manual backup. Body: `{label?: str}`. Returns `{timestamp, label, file, size}`. |
| `GET` | `/api/projects/{id}/backups` | List backups. Returns array of metadata objects. |
| `POST` | `/api/projects/{id}/restore` | Restore from backup. Body: `{backup_name: str}`. Returns `{status, backup}`. |

### 1.9 Research Metrics and Surveys

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/projects/{id}/metrics` | Compute 3NF check, relationship F1, data quality. Returns `{norm3, relationships, data_quality}`. |
| `POST` | `/api/projects/{id}/interactions` | Log a user interaction event. Body: any `{type, ...}`. |
| `GET` | `/api/projects/{id}/interactions` | Get logged interactions for project. |
| `POST` | `/api/projects/{id}/export-interactions` | Export interactions to JSON file. |
| `POST` | `/api/experiments/compare` | Compare automatic vs. human-in-the-loop (experiment endpoint). |
| `POST` | `/api/surveys/nasa-tlx` | Submit NASA-TLX survey. |
| `POST` | `/api/surveys/sus` | Submit SUS survey. |

### 1.10 System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check. Returns `{status: "ok"}`. |
| `GET` | `/api/llm/info` | Current LLM provider and model. Returns `{provider, model}`. |
| `GET` | `/api/tasks/{task_id}` | Get Celery task status. Returns `{task_id, status, result}`. |

---

## 2. Frontend Component Tree

```
App.tsx
├── ThemeToggle.tsx          -- Dark/light mode toggle
├── LLMStatus.tsx            -- Current LLM provider indicator
├── ProgressBar.tsx          -- Task progress indicator (shown on project pages)
│
├── Dashboard.tsx            -- Route: "/"
│   ├── New project form     -- Name + prompt + Create button
│   └── Project list         -- Cards with links + delete buttons
│
└── ProjectPage.tsx          -- Route: "/projects/:id"
    ├── GuidedWorkflow.tsx   -- Step indicator (upload → schema → populate → explore)
    ├── DocumentUploader.tsx  -- Drag-and-drop / click file upload
    ├── SchemaChat.tsx        -- Chat interface for iterative schema generation
    │
    ├── Tab: Schema           -- [activeTab === 'schema']
    │   ├── Quick Generate    -- Prompt input + Generate button
    │   ├── SchemaViewer.tsx  -- Table cards with column grid (edit mode: inline editing)
    │   ├── SchemaDiagram.tsx -- ER diagram using ReactFlow
    │   ├── ExportButton.tsx  -- Export dropdown (SQL/JSON/CSV + dialect selector)
    │   ├── Import SQL        -- File upload with dialect selector
    │   ├── BackupManager.tsx -- Create backup / list backups / restore
    │   ├── OperationHistory.tsx -- Interaction log viewer
    │   └── Populate Button   -- Triggers data population
    │
    ├── Tab: Data             -- [activeTab === 'data']
    │   └── DataViewer.tsx    -- Table data with:
    │       ├── Global search
    │       ├── Per-column filters
    │       ├── Inline cell editing
    │       ├── Add row / Delete row
    │       └── CSV export per table
    │
    ├── Tab: Query            -- [activeTab === 'query']
    │   └── QueryBuilder.tsx  -- Natural language input → SQL → Execute → Results
    │
    └── Survey.tsx            -- NASA-TLX / SUS forms (for experiments)
```

---

## 3. Database Schema

### 3.1 Application State Database (`app.db`)

SQLite database at the project root, managed by SQLAlchemy.

**`projects` table:**

| Column | Type | Notes |
|---|---|---|
| `id` | String (PK, UUID4) | Auto-generated |
| `name` | String(255), NOT NULL | User-provided |
| `prompt` | Text, nullable | Initial user description |
| `schema_json` | JSON, nullable | Serialized `NormalizedSchema` + embedded metrics (`_metrics`) |
| `db_path` | String(512), nullable | Path to the generated SQLite database |
| `created_at` | DateTime (UTC) | Auto-set on creation |
| `updated_at` | DateTime (UTC) | Auto-updated on modification |

**`documents` table:**

| Column | Type | Notes |
|---|---|---|
| `id` | String (PK, UUID4) | Auto-generated |
| `project_id` | String, FK → projects.id | Cascade delete |
| `filename` | String(255) | Original upload filename |
| `file_type` | String(10) | Extension: pdf, xlsx, csv, txt, sql |
| `file_path` | String(512) | Uploaded file location |
| `content_summary` | Text, nullable | Bounded extracted text for LLM consumption (maximum 5,000 characters per document) |
| `created_at` | DateTime (UTC) | Auto-set |

### 3.2 Generated Database (`projects/{id}/database.sqlite`)

Each project gets its own SQLite database created dynamically by SQLAlchemy `metadata.create_all()` based on the `NormalizedSchema`. Tables, columns, types, constraints, and foreign keys are all defined at runtime with no migration framework — the DB is recreated or altered via `ALTER TABLE ADD COLUMN` when the schema changes.

### 3.3 Backup Storage (`projects/{id}/backups/`)

Timestamped `.db` files with companion `.json` metadata files containing `{timestamp, label, project_id, file, size}`.

### 3.4 Interaction Log Store (`projects/interactions_store.json`)

A persistent JSON array of all `{timestamp, event_type, project_id, data}` events, loaded at startup and appended/saved on each interaction. This is not a database table because it is append-only research data that should not interfere with application migrations.

### 3.5 Migration Strategy

Schema migrations are handled by `migrate_database()` in `app/core/db_generator.py`:

- **New tables** are created via `Table(..., metadata).create_all()`.
- **New columns** are added via `ALTER TABLE ADD COLUMN`. NOT NULL columns get `DEFAULT ''`.
- **Removed columns/tables** are NOT dropped. Data is preserved in the SQLite file.
- **Removed constraints** are NOT changed (SQLite does not support DROP CONSTRAINT without table recreation).
- **Backup** is created before any migration via `BackupService.auto_backup()`.

This is a conservative, additive-only strategy designed to prevent data loss during the research phase.

---

## 4. LLM Integration

### 4.1 Provider Configuration

The LLM provider is configured via environment variables in `.env`:

```
LLM_PROVIDER=openai|groq|openrouter|google|ollama
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-2.0-flash
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
USE_OLLAMA=false
```

The `_get_llm()` function in `app/core/llm.py` selects the provider and returns a LangChain `ChatModel` instance. All providers use the same LangChain interfaces, so prompt templates and output parsers are provider-agnostic.

### 4.2 Prompt Templates

**Schema Generation Prompt** (`SCHEMA_PROMPT`):

```
System: You are a database normalization expert. Generate a 3NF normalized database schema.
Rules:
- All tables must be in 3NF (no transitive dependencies)
- Use snake_case for names, plural for tables
- Every table must have a primary key
- Foreign keys must reference existing tables
- Choose appropriate SQL data types (INTEGER, TEXT, REAL, DATE, BOOLEAN)

User: User description: {prompt}
Document context: {document_context}
{format_instructions}
```

**Query Generation Prompt** (`QUERY_PROMPT`):

```
System: You are a SQL expert. Generate valid {dialect} SQL queries from natural language descriptions.
CRITICAL: Output ONLY the raw SQL query. Do NOT use markdown code blocks, backticks, or any formatting.

User: Database schema: {schema}
User request: {prompt}
Generate only the SQL query, no explanation.
```

**Population SQL Prompt** (`POPULATE_SQL_PROMPT`):

```
System: You are a SQL database population expert. Generate valid SQLite INSERT OR IGNORE statements.
Rules:
1. Output ONLY valid SQLite INSERT statements
2. Insert ALL data from documents into ALL relevant tables
3. Maintain PK/FK consistency across related tables
4. Correctly map document columns to schema columns
5. Format dates as ISO strings, escape single quotes
6. For NOT NULL columns, NEVER use NULL; use '' or 0 as default
7. CRITICAL: No markdown, no backticks, no explanation.

User: Database Schema: {schema_info}
Document Data: {doc_content}
Generate all INSERT SQL statements:
```

### 4.3 Response Parsing

- **Schema generation** uses `PydanticOutputParser(pydantic_object=NormalizedSchema)` which automatically validates the LLM output against the Pydantic model. Parse failures raise `LLMException`.
- **Data generation** uses `JsonOutputParser()` for flexibility (the LLM returns a JSON array of objects with variable keys).
- **Column mapping** uses `JsonOutputParser()` for the `{table_name: {col_index: schema_col_name}}` format.
- **Query generation** receives raw text from `ChatModel` (no parser); stripped of markdown code blocks via regex.

---

## 5. Key Design Decisions

### 5.1 Why SQLite for Storage?

1. **Zero configuration** — No database server to install, configure, or maintain. The entire application state and all user databases are file-based.
2. **Portability** — The database is a single `.db` file that can be backed up, copied, and deleted atomically.
3. **Research suitability** — Participant data can be collected as flat files; no need for a multitenant server. Each project is self-contained in its own directory.
4. **Trade-off acknowledged** — SQLite has limited concurrent write capacity and no user management. This is acceptable for a single-user research tool but would need re-evaluation for multi-user deployment.

### 5.2 Why Google Gemini (and Provider Abstraction)?

The initial implementation used OpenAI GPT-4o-mini, but the architecture was designed for provider abstraction from the start via LangChain. Google Gemini was introduced because:
- It offers a generous free tier for research.
- Its large context window provides headroom for future controlled experiments; the application deliberately limits LLM-bound content to 5,000 characters per document for privacy, cost control, and reproducibility, and records a warning when truncation occurs.
- The LangChain `ChatGoogleGenerativeAI` integration is stable.

The `_get_llm()` function allows switching providers at runtime via environment variables, enabling direct comparison of schema quality across models (a planned experiment).

### 5.3 Why NOT NULL Enforcement in Population Prompts?

The prompt instruction "For columns marked NOT NULL, NEVER use NULL; use '' for text, 0 for numbers, or a reasonable default" was added after observing that the LLM frequently generated NULL values for NOT NULL columns, causing INSERT failures. This instruction is the highest-impact prompt engineering change, reducing population failure rates from ~40% to ~5% in testing.

### 5.3.1 Why Full-LLM Population as the Primary Route?

Population was originally deterministic-first for structured documents (exact/partial header rules first, semantic LLM mapping only for unresolved columns). Observational evidence from a denormalised multi-file dataset showed the deterministic matcher associated `id` (a substring of composite identifiers such as `ID_Scontrino`) with multiple tables at once without filling NOT NULL and foreign-key columns, leaving the database under-populated. The population route was therefore inverted: the LLM now receives the complete content of every uploaded document (CSV, Excel, PDF, TXT) and decides how to map values into the schema, discarding only duplicate rows already present in the target tables. The deterministic mapper is retained strictly as a recovery path when the LLM returns no usable SQL. This change affects experimental comparability with earlier runs (extraction path is now `llm` by default) and is recorded in the CHANGELOG.

### 5.4 Why Celery + Redis for Async Tasks?

Schema generation and data population can take 10-60 seconds for large documents. Blocking the HTTP request for this duration would cause frontend timeouts and poor UX. Celery with Redis as a message broker enables:

- **Non-blocking API responses** — the endpoint returns immediately with a `task_id`.
- **Progress polling** — the frontend polls `GET /api/tasks/{task_id}` to show progress.
- **Worker separation** — heavy LLM inference runs in a separate process, not blocking the API server.
